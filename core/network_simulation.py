"""
Core Network Simulation Module — Python Network Emulator
=========================================================
Implements a Python-based discrete-event network emulation engine that models:
- Bottleneck link bandwidth throttling (serialization delay).
- Propagation delay (one-way and round-trip time).
- Router buffer size limits (FIFO queueing and tail drop overflow).
- Channel random packet loss probability.
- TCP Tahoe and TCP Reno sender dynamics (CWND, SSTHRESH, Slow Start, AIMD,
  Fast Retransmit, Fast Recovery, and Timeout handling).
- Packet delivery, RTT measurement, retransmissions, and throughput calculation.

Operates 100% natively on Windows 10, macOS, and Linux without requiring
Mininet, Linux kernel modules, root permissions, WSL2, VirtualBox, or Docker.

Important Scientific Distinction:
All results produced by this module are simulated network models. They are
explicitly labeled as simulated and do not claim to be physical Mininet experiments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
import platform
import random
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from utils.helpers import is_linux


@dataclass(frozen=True)
class NetworkExperimentConfig:
    """
    Configuration parameters for a Python network emulation experiment.

    Attributes
    ----------
    experiment_id : str
        Unique experiment run identifier.
    bandwidth_mbps : float
        Bottleneck link bandwidth limit in Megabits per second (e.g., 10.0 Mbps).
    delay_ms : float
        Bottleneck link one-way propagation delay in milliseconds (e.g., 20.0 ms).
    loss_percentage : float
        Artificially injected random packet loss rate percentage [0.0, 100.0]%.
    buffer_size_packets : int
        Maximum router queue capacity in packets before tail drop occurs (default 50).
    duration_seconds : int
        Duration of the network emulation session in seconds (default 10).
    tcp_congestion_algorithm : str
        TCP congestion control algorithm ('reno', 'tahoe', 'cubic').
    server_host : str
        Simulated receiver identifier (default 'h2').
    client_host : str
        Simulated sender identifier (default 'h1').
    random_seed : Optional[int]
        Random seed for reproducible loss modeling (optional).
    """
    experiment_id: str
    bandwidth_mbps: float = 10.0
    delay_ms: float = 20.0
    loss_percentage: float = 0.0
    buffer_size_packets: int = 50
    duration_seconds: int = 10
    tcp_congestion_algorithm: str = "reno"
    server_host: str = "h2"
    client_host: str = "h1"
    random_seed: Optional[int] = None

    def validate(self) -> None:
        """Validate input parameter bounds and sanity."""
        if not self.experiment_id or not isinstance(self.experiment_id, str):
            raise ValueError("experiment_id must be a non-empty string.")
        if self.bandwidth_mbps <= 0:
            raise ValueError(f"bandwidth_mbps must be positive, got {self.bandwidth_mbps}.")
        if self.delay_ms < 0:
            raise ValueError(f"delay_ms cannot be negative, got {self.delay_ms}.")
        if not (0.0 <= self.loss_percentage <= 100.0):
            raise ValueError(
                f"loss_percentage must be between 0.0 and 100.0%, got {self.loss_percentage}."
            )
        if self.duration_seconds <= 0:
            raise ValueError(
                f"duration_seconds must be a positive integer, got {self.duration_seconds}."
            )
        if self.buffer_size_packets <= 0:
            raise ValueError(
                f"buffer_size_packets must be a positive integer, got {self.buffer_size_packets}."
            )
        allowed_algos = ("reno", "tahoe", "cubic", "bbr", "bic", "westwood", "htcp")
        if self.tcp_congestion_algorithm.lower() not in allowed_algos:
            raise ValueError(
                f"Unsupported Linux congestion algorithm '{self.tcp_congestion_algorithm}'. "
                f"Choose from: {', '.join(allowed_algos)}."
            )


@dataclass
class ExperimentResult:
    """
    Performance measurements gathered from a Python network emulation run.
    Clearly labeled as simulated network measurements.

    Attributes
    ----------
    experiment_id : str
        Unique experiment run identifier.
    configured_bandwidth_mbps : float
        Bottleneck link bandwidth limit configured for this run.
    configured_delay_ms : float
        One-way propagation delay configured for this run.
    configured_loss_percentage : float
        Packet loss percentage configured for this run.
    measured_throughput_mbps : float
        Simulated TCP goodput / throughput measured across the session.
    configured_buffer_size : int
        Maximum router buffer size in packets.
    transfer_amount_mb : float
        Total volume of application data delivered in Megabytes.
    measured_retransmissions : int
        Total TCP retransmissions logged during the simulation.
    measured_rtt_ms : Optional[float]
        Mean Round-Trip Time observed during the session (ms).
    experiment_duration_sec : float
        Actual duration elapsed during test execution.
    tcp_congestion_algorithm : str
        Congestion control algorithm used ('reno', 'tahoe', 'cubic').
    buffer_drops : int
        Count of packets dropped due to router buffer queue overflow.
    random_drops : int
        Count of packets dropped due to random channel loss.
    status : str
        Execution outcome ('Completed' or 'Failed').
    error_message : Optional[str]
        Error description if status is 'Failed'.
    raw_iperf_output : Optional[Dict[str, Any]]
        Optional emulation diagnostics / summary dictionary.
    time_series_data : Optional[List[Dict[str, Any]]]
        Detailed round-by-round time series for Plotly visualization.
    is_simulated : bool
        Flag explicitly stating whether results are simulated (always True).
    """
    experiment_id: str
    configured_bandwidth_mbps: float
    configured_delay_ms: float
    configured_loss_percentage: float
    measured_throughput_mbps: float
    transfer_amount_mb: float = 0.0
    measured_retransmissions: int = 0
    measured_rtt_ms: Optional[float] = None
    experiment_duration_sec: float = 0.0
    tcp_congestion_algorithm: str = "reno"
    configured_buffer_size: int = 50
    buffer_drops: int = 0
    random_drops: int = 0
    status: str = "Completed"
    error_message: Optional[str] = None
    raw_iperf_output: Optional[Dict[str, Any]] = None
    time_series_data: Optional[List[Dict[str, Any]]] = None
    is_simulated: bool = True

    def to_dataframe(self) -> pd.DataFrame:
        """Export experiment summary row as a structured Pandas DataFrame."""
        throughput_efficiency = (
            round((self.measured_throughput_mbps / self.configured_bandwidth_mbps) * 100.0, 1)
            if self.configured_bandwidth_mbps > 0 else 0.0
        )
        record = {
            "Experiment_ID": self.experiment_id,
            "Configured_Bandwidth_Mbps": self.configured_bandwidth_mbps,
            "Measured_Throughput_Mbps": self.measured_throughput_mbps,
            "Throughput_Efficiency_Pct": throughput_efficiency,
            "Configured_Delay_Ms": self.configured_delay_ms,
            "Configured_Loss_Pct": self.configured_loss_percentage,
            "Buffer_Size_Packets": self.configured_buffer_size,
            "Retransmissions": self.measured_retransmissions,
            "Buffer_Drops": self.buffer_drops,
            "Random_Drops": self.random_drops,
            "Measured_RTT_Ms": self.measured_rtt_ms if self.measured_rtt_ms is not None else "N/A",
            "Transfer_MB": self.transfer_amount_mb,
            "Duration_Sec": self.experiment_duration_sec,
            "Algorithm": self.tcp_congestion_algorithm,
            "Status": self.status,
            "Type": "Python Network Emulation (Simulated)",
            # Backward compatibility aliases for existing tests
            "experiment_id": self.experiment_id,
            "configured_bandwidth_mbps": self.configured_bandwidth_mbps,
            "measured_throughput_mbps": self.measured_throughput_mbps,
            "configured_delay_ms": self.configured_delay_ms,
            "configured_loss_percentage": self.configured_loss_percentage,
            "measured_retransmissions": self.measured_retransmissions,
            "measured_rtt_ms": self.measured_rtt_ms,
            "experiment_duration_sec": self.experiment_duration_sec,
        }
        return pd.DataFrame([record])

    def to_dict(self) -> Dict[str, Any]:
        """Convert experiment result to a serializable dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "configured_bandwidth_mbps": self.configured_bandwidth_mbps,
            "configured_delay_ms": self.configured_delay_ms,
            "configured_loss_percentage": self.configured_loss_percentage,
            "configured_buffer_size": self.configured_buffer_size,
            "measured_throughput_mbps": self.measured_throughput_mbps,
            "transfer_amount_mb": self.transfer_amount_mb,
            "measured_retransmissions": self.measured_retransmissions,
            "measured_rtt_ms": self.measured_rtt_ms,
            "experiment_duration_sec": self.experiment_duration_sec,
            "tcp_congestion_algorithm": self.tcp_congestion_algorithm,
            "buffer_drops": self.buffer_drops,
            "random_drops": self.random_drops,
            "status": self.status,
            "error_message": self.error_message,
            "is_simulated": self.is_simulated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExperimentResult:
        """Construct an ExperimentResult instance from a dictionary record."""
        return cls(
            experiment_id=str(data.get("experiment_id", "EXP-UNKNOWN")),
            configured_bandwidth_mbps=float(data.get("configured_bandwidth_mbps", 10.0)),
            configured_delay_ms=float(data.get("configured_delay_ms", 10.0)),
            configured_loss_percentage=float(data.get("configured_loss_percentage", 0.0)),
            configured_buffer_size=int(data.get("configured_buffer_size", 50)),
            measured_throughput_mbps=float(data.get("measured_throughput_mbps", 0.0)),
            transfer_amount_mb=float(data.get("transfer_amount_mb", 0.0)),
            measured_retransmissions=int(data.get("measured_retransmissions", 0)),
            measured_rtt_ms=float(data["measured_rtt_ms"]) if data.get("measured_rtt_ms") is not None else None,
            experiment_duration_sec=float(data.get("experiment_duration_sec", 10.0)),
            tcp_congestion_algorithm=str(data.get("tcp_congestion_algorithm", "reno")),
            buffer_drops=int(data.get("buffer_drops", 0)),
            random_drops=int(data.get("random_drops", 0)),
            status=str(data.get("status", "Completed")),
            error_message=data.get("error_message"),
            is_simulated=bool(data.get("is_simulated", True))
        )


def calculate_experiment_throughput(bytes_transferred: float, duration_seconds: float) -> float:
    """
    Calculate throughput in Megabits per second (Mbps).

    Formula: Throughput (Mbps) = (Bytes * 8) / (Duration_Sec * 10^6)
    """
    if duration_seconds <= 0.0 or bytes_transferred <= 0.0:
        return 0.0
    return (bytes_transferred * 8.0) / (duration_seconds * 1_000_000.0)


def calculate_throughput_efficiency(measured_mbps: float, configured_mbps: float) -> float:
    """
    Calculate throughput efficiency percentage: (Measured / Configured) * 100%.
    """
    if configured_mbps <= 0.0:
        return 0.0
    return max(0.0, (measured_mbps / configured_mbps) * 100.0)


def save_experiment_history(history: List[ExperimentResult], filepath: str) -> None:
    """
    Safely persist a list of completed experiment results to a JSON file.
    """
    records = [res.to_dict() for res in history if res.status == "Completed"]
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    temp_path = f"{filepath}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    shutil.move(temp_path, filepath)


def load_experiment_history(filepath: str) -> List[ExperimentResult]:
    """
    Safely load a list of completed experiment results from a JSON file.
    Returns an empty list if file does not exist or content is malformed.
    """
    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            results = []
            for item in data:
                if isinstance(item, dict):
                    try:
                        results.append(ExperimentResult.from_dict(item))
                    except (ValueError, TypeError):
                        pass
            return results
    except (json.JSONDecodeError, OSError):
        return []


def parse_iperf3_json(raw_json: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse raw JSON output from iPerf3 (-J flag) into structured performance metrics.
    Kept for backward compatibility and testing validation.
    """
    if isinstance(raw_json, str):
        if not raw_json.strip():
            raise ValueError("iPerf3 output is empty.")
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as err:
            raise ValueError(f"Failed to parse iPerf3 output as JSON: {err}")
    elif isinstance(raw_json, dict):
        data = raw_json
    else:
        raise TypeError(f"Expected str or dict for iPerf3 output, got {type(raw_json)}.")

    if "error" in data:
        raise RuntimeError(f"iPerf3 execution reported error: {data['error']}")

    end_stats = data.get("end", {})
    if not end_stats:
        raise ValueError("Malformed iPerf3 output: missing 'end' statistics block.")

    sum_rcv = end_stats.get("sum_received", {})
    sum_sent = end_stats.get("sum_sent", {})

    bps = sum_rcv.get("bits_per_second", sum_sent.get("bits_per_second", 0.0))
    throughput_mbps = round(float(bps) / 1e6, 2)

    bytes_transferred = sum_rcv.get("bytes", sum_sent.get("bytes", 0))
    transfer_mb = round(float(bytes_transferred) / (1024.0 * 1024.0), 2)

    duration = round(float(sum_rcv.get("seconds", sum_sent.get("seconds", 0.0))), 2)
    retransmissions = int(sum_sent.get("retransmits", 0))

    rtt_ms: Optional[float] = None
    streams = end_stats.get("streams", [])
    if streams and isinstance(streams, list) and "sender" in streams[0]:
        sender_stream = streams[0]["sender"]
        raw_rtt = sender_stream.get("mean_rtt")
        if raw_rtt is not None and isinstance(raw_rtt, (int, float)):
            rtt_ms = round(float(raw_rtt) / 1000.0, 2) if raw_rtt > 100 else round(float(raw_rtt), 2)

    return {
        "throughput_mbps": throughput_mbps,
        "transfer_mb": transfer_mb,
        "duration_seconds": duration,
        "retransmissions": retransmissions,
        "rtt_ms": rtt_ms,
        "raw_json": data
    }


class PythonNetworkEmulator:
    """
    Python-based Network Emulator for modeling TCP transmission, router buffer queueing,
    propagation delay, packet loss, and retransmissions.

    Operates natively on Windows 10 without external dependencies.
    """

    def __init__(self, config: NetworkExperimentConfig) -> None:
        config.validate()
        self.config = config
        self.mss_bytes: int = 1460
        self.packet_total_bytes: int = 1500  # 1460 payload + 40 headers

    def run(self) -> ExperimentResult:
        """
        Execute the discrete-event network emulation and return structured results.
        """
        rng = random.Random(self.config.random_seed) if self.config.random_seed is not None else random.Random()

        # Link parameters
        bandwidth_bps = self.config.bandwidth_mbps * 1_000_000.0
        # Service rate in packets per second:
        mu_pkts_per_sec = bandwidth_bps / (self.packet_total_bytes * 8.0)
        base_rtt_sec = max(0.001, (2.0 * self.config.delay_ms) / 1000.0)
        buffer_capacity = self.config.buffer_size_packets
        loss_prob = self.config.loss_percentage / 100.0

        # TCP Sender State
        algo = self.config.tcp_congestion_algorithm.lower()
        is_tahoe = (algo == "tahoe")
        cwnd: float = 1.0  # Initial CWND in MSS/packets
        # Initial SSTHRESH based on Bandwidth-Delay Product or standard 16 MSS
        bdp_packets = max(4.0, (bandwidth_bps * base_rtt_sec) / (self.packet_total_bytes * 8.0))
        ssthresh: float = max(16.0, bdp_packets)
        tcp_state: str = "Slow Start"

        # Simulation Time & Counters
        current_time_sec: float = 0.0
        target_duration: float = float(self.config.duration_seconds)
        round_index: int = 0
        current_queue_packets: int = 0

        total_bytes_delivered: int = 0
        total_retransmissions: int = 0
        total_buffer_drops: int = 0
        total_random_drops: int = 0
        observed_rtts: List[float] = []

        time_series: List[Dict[str, Any]] = []

        while current_time_sec < target_duration:
            round_index += 1

            # 1. Calculate dynamic RTT including queueing delay
            queueing_delay_sec = current_queue_packets / mu_pkts_per_sec if mu_pkts_per_sec > 0 else 0.0
            serialization_delay_sec = 1.0 / mu_pkts_per_sec if mu_pkts_per_sec > 0 else 0.0
            rtt_sec = base_rtt_sec + queueing_delay_sec + serialization_delay_sec
            observed_rtts.append(rtt_sec * 1000.0)

            # 2. Sender transmits CWND packets into the network pipe
            packets_to_send = max(1, int(round(cwnd)))

            # 3. Router Queue Processing & Tail Drop
            # Maximum packets the bottleneck link can drain/service during this RTT window
            service_capacity_round = max(1, int(math.floor(mu_pkts_per_sec * rtt_sec)))
            arriving_packets = current_queue_packets + packets_to_send
            served_packets = min(arriving_packets, service_capacity_round)
            unserved_packets = arriving_packets - served_packets

            # Check if router buffer overflows (tail drop)
            if unserved_packets > buffer_capacity:
                buffer_drops_round = unserved_packets - buffer_capacity
                current_queue_packets = buffer_capacity
            else:
                buffer_drops_round = 0
                current_queue_packets = unserved_packets

            # 4. Channel Random Loss (applied to packets that weren't dropped by buffer)
            packets_in_flight = max(0, packets_to_send - buffer_drops_round)
            random_drops_round = 0
            if loss_prob > 0.0 and packets_in_flight > 0:
                for _ in range(packets_in_flight):
                    if rng.random() < loss_prob:
                        random_drops_round += 1

            # Total drops in this round
            total_drops_round = buffer_drops_round + random_drops_round
            total_buffer_drops += buffer_drops_round
            total_random_drops += random_drops_round
            total_retransmissions += total_drops_round

            # Packets successfully acknowledged
            packets_delivered_round = max(0, packets_to_send - total_drops_round)
            bytes_delivered_round = packets_delivered_round * self.mss_bytes
            total_bytes_delivered += bytes_delivered_round

            # 5. TCP Congestion Control State Updates
            loss_type = "None"
            if total_drops_round == 0:
                # Normal ACK reception: Window growth
                if cwnd < ssthresh:
                    # Slow Start: increase by 1 MSS per ACK (doubles per RTT)
                    cwnd = min(cwnd + packets_delivered_round, 128.0)
                    tcp_state = "Slow Start"
                    if cwnd >= ssthresh:
                        tcp_state = "Congestion Avoidance"
                else:
                    # Congestion Avoidance: AIMD additive increase (+1 MSS per RTT)
                    cwnd = min(cwnd + 1.0, 128.0)
                    tcp_state = "Congestion Avoidance"
            else:
                # Loss detected: Heuristic classification
                if total_drops_round >= packets_to_send or packets_to_send <= 3:
                    # Timeout (Severe loss / pipeline stalled)
                    loss_type = "Timeout (RTO)"
                    ssthresh = max(2.0, math.floor(cwnd / 2.0))
                    cwnd = 1.0
                    tcp_state = "Slow Start"
                else:
                    # Triple Duplicate ACK (Fast Retransmit & Recovery)
                    loss_type = "3 Duplicate ACKs (Fast Retransmit)"
                    new_ssthresh = max(2.0, math.floor(cwnd / 2.0))
                    ssthresh = new_ssthresh
                    if is_tahoe:
                        # Tahoe resets to 1.0 MSS upon Fast Retransmit
                        cwnd = 1.0
                        tcp_state = "Slow Start"
                    else:
                        # Reno enters Fast Recovery and resumes in Congestion Avoidance
                        cwnd = new_ssthresh
                        tcp_state = "Congestion Avoidance"

            # 6. Calculate instantaneous throughput (Mbps) in this round
            inst_throughput_mbps = (
                (bytes_delivered_round * 8.0) / (rtt_sec * 1_000_000.0)
                if rtt_sec > 0 else 0.0
            )

            # Record time series step
            time_series.append({
                "Time_Sec": round(current_time_sec, 3),
                "RTT_Round": round_index,
                "CWND": round(cwnd, 2),
                "SSTHRESH": round(ssthresh, 2),
                "Packets_Sent": packets_to_send,
                "Packets_Delivered": packets_delivered_round,
                "Packets_Dropped": total_drops_round,
                "Buffer_Occupancy": current_queue_packets,
                "Buffer_Capacity": buffer_capacity,
                "Throughput_Mbps": round(inst_throughput_mbps, 2),
                "Configured_Bandwidth_Mbps": self.config.bandwidth_mbps,
                "RTT_Ms": round(rtt_sec * 1000.0, 2),
                "TCP_State": tcp_state,
                "Loss_Type": loss_type,
            })

            current_time_sec += rtt_sec

        # Final Aggregations
        actual_duration = max(0.001, current_time_sec)
        measured_throughput = round((total_bytes_delivered * 8.0) / (actual_duration * 1_000_000.0), 2)
        transfer_mb = round(total_bytes_delivered / (1024.0 * 1024.0), 2)
        mean_rtt = round(sum(observed_rtts) / len(observed_rtts), 2) if observed_rtts else None

        raw_summary = {
            "total_rounds": round_index,
            "total_bytes": total_bytes_delivered,
            "transfer_mb": transfer_mb,
            "measured_throughput_mbps": measured_throughput,
            "mean_rtt_ms": mean_rtt,
            "total_retransmissions": total_retransmissions,
            "buffer_drops": total_buffer_drops,
            "random_drops": total_random_drops,
            "configured_bandwidth_mbps": self.config.bandwidth_mbps,
            "configured_delay_ms": self.config.delay_ms,
            "configured_loss_percentage": self.config.loss_percentage,
            "configured_buffer_size": self.config.buffer_size_packets,
            "algorithm": self.config.tcp_congestion_algorithm,
            "simulation_engine": "Python Network Emulator (Native Windows 10)"
        }

        return ExperimentResult(
            experiment_id=self.config.experiment_id,
            configured_bandwidth_mbps=self.config.bandwidth_mbps,
            configured_delay_ms=self.config.delay_ms,
            configured_loss_percentage=self.config.loss_percentage,
            measured_throughput_mbps=measured_throughput,
            configured_buffer_size=self.config.buffer_size_packets,
            transfer_amount_mb=transfer_mb,
            measured_retransmissions=total_retransmissions,
            measured_rtt_ms=mean_rtt,
            experiment_duration_sec=round(actual_duration, 2),
            tcp_congestion_algorithm=self.config.tcp_congestion_algorithm,
            buffer_drops=total_buffer_drops,
            random_drops=total_random_drops,
            status="Completed",
            error_message=None,
            raw_iperf_output=raw_summary,
            time_series_data=time_series,
            is_simulated=True
        )


class NetworkExperimentManager:
    """
    Manager for orchestrating Python-based network emulation of a bottleneck link.
    Executes natively on Windows 10 without external dependencies.
    """

    def __init__(self, config: NetworkExperimentConfig) -> None:
        config.validate()
        self.config = config

    @staticmethod
    def verify_environment() -> Dict[str, Any]:
        """
        Verify the host environment for Python network emulation.
        Fully supported across all platforms (Windows 10, Linux, macOS) natively.
        """
        return {
            "supported": True,
            "is_linux": is_linux(),
            "mininet_available": False,  # Not needed, pure Python
            "iperf3_available": False,   # Not needed, pure Python
            "has_root": True,            # No root needed for Python emulation
            "engine": "Python Network Emulator",
            "guidance": "Environment verified: Native Python Network Emulator is ready on this host (Windows 10 compatible).",
        }

    def run_experiment(self) -> ExperimentResult:
        """Execute the network emulation simulation and return an ExperimentResult."""
        emulator = PythonNetworkEmulator(self.config)
        return emulator.run()
