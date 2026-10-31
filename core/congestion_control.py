"""
Core Congestion Control Module
==============================
Defines the mathematical architecture, state representations, and execution
simulation engines for TCP Tahoe and TCP Reno congestion control algorithms.

Algorithms covered:
- TCP Tahoe: Slow Start, Congestion Avoidance, Fast Retransmit, Timeout Handling.
- TCP Reno: Slow Start, Congestion Avoidance, Fast Retransmit, Fast Recovery, Timeout Handling.

Educational Model Assumptions:
- Time is discretized into Round-Trip Time (RTT) rounds.
- CWND is measured in units of Maximum Segment Size (MSS).
- In Slow Start, each acknowledged segment increments CWND by 1 MSS; across one RTT,
  CWND approximately doubles (exponential growth).
- In Congestion Avoidance, CWND increases additively by approximately 1 MSS per RTT (AIMD).
- Minimum SSTHRESH is clamped at 2.0 MSS in compliance with RFC 5681.
- Random packet loss generation is strictly segregated from scheduled deterministic events.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import math
import random
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


class TCPState(str, Enum):
    """TCP Congestion Control State Machine States."""
    SLOW_START = "Slow Start"
    CONGESTION_AVOIDANCE = "Congestion Avoidance"
    FAST_RECOVERY = "Fast Recovery"


class LossEventType(str, Enum):
    """Types of congestion events detected by TCP."""
    NONE = "None"
    TRIPLE_DUPLICATE_ACK = "Triple Duplicate ACK (Fast Retransmit)"
    TIMEOUT = "Retransmission Timeout (RTO)"


def normalize_loss_event(val: Any) -> LossEventType:
    """Normalize user input string or enum into a canonical LossEventType."""
    if isinstance(val, LossEventType):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if "dup" in v or "triple" in v or "fast" in v or "3" in v:
            return LossEventType.TRIPLE_DUPLICATE_ACK
        elif "time" in v or "rto" in v:
            return LossEventType.TIMEOUT
        elif "none" in v or v == "":
            return LossEventType.NONE
    return LossEventType.NONE


@dataclass(frozen=True)
class SimulationParameters:
    """
    Input configuration parameters for a TCP simulation run.

    Attributes
    ----------
    algorithm : str
        Algorithm name ('Tahoe' or 'Reno').
    initial_cwnd : float
        Initial Congestion Window in MSS units (default 1.0).
    initial_ssthresh : float
        Initial Slow Start Threshold in MSS units (default 16.0).
    mss : int
        Maximum Segment Size in bytes (default 1460).
    max_cwnd : Optional[float]
        Maximum permissible Congestion Window in MSS units (default 64.0).
    num_rounds : int
        Total number of discrete Round-Trip Time (RTT) simulation rounds.
    loss_probability : float
        Uniform probability of random packet loss occurring in any round [0.0, 1.0].
    loss_events : Dict[int, LossEventType]
        Explicit scheduled loss events keyed by RTT round number.
    random_seed : Optional[int]
        Random seed for reproducible packet loss generation.
    """
    algorithm: str = "Tahoe"
    initial_cwnd: float = 1.0
    initial_ssthresh: float = 16.0
    mss: int = 1460
    max_cwnd: Optional[float] = 64.0
    num_rounds: int = 30
    loss_probability: float = 0.0
    loss_events: Dict[int, LossEventType] = field(default_factory=dict)
    random_seed: Optional[int] = None

    def validate(self) -> None:
        """Validate input parameter bounds and sanity."""
        if self.algorithm not in ("Tahoe", "Reno"):
            raise ValueError(f"Unsupported algorithm '{self.algorithm}'. Choose 'Tahoe' or 'Reno'.")
        if self.initial_cwnd <= 0:
            raise ValueError(f"initial_cwnd must be greater than 0, got {self.initial_cwnd}.")
        if self.initial_ssthresh <= 0:
            raise ValueError(f"initial_ssthresh must be greater than 0, got {self.initial_ssthresh}.")
        if self.mss <= 0:
            raise ValueError(f"mss must be a positive integer, got {self.mss}.")
        if self.num_rounds <= 0:
            raise ValueError(f"num_rounds must be a positive integer, got {self.num_rounds}.")
        if not (0.0 <= self.loss_probability <= 1.0):
            raise ValueError(f"loss_probability must be between 0.0 and 1.0 inclusive, got {self.loss_probability}.")
        if self.max_cwnd is not None:
            if self.max_cwnd <= 0:
                raise ValueError(f"max_cwnd must be positive, got {self.max_cwnd}.")
            if self.max_cwnd < self.initial_cwnd:
                raise ValueError(
                    f"max_cwnd ({self.max_cwnd}) cannot be less than initial_cwnd ({self.initial_cwnd})."
                )


@dataclass
class SimulationStep:
    """
    State recorded for a single RTT round in the congestion control simulation.

    Attributes
    ----------
    round_number : int
        Current RTT round index (1-based).
    algorithm : str
        Algorithm active during this step ('Tahoe' or 'Reno').
    cwnd : float
        Congestion window size in MSS units at the completion of this round.
    ssthresh : float
        Slow start threshold in MSS units at the completion of this round.
    tcp_state : TCPState
        Operating TCP phase (Slow Start, Congestion Avoidance, Fast Recovery).
    congestion_event : LossEventType
        Congestion indication observed during this round (if any).
    retransmission_event : bool
        Whether a retransmission was triggered in this round.
    algorithm_action : str
        Human-readable summary of window adjustment taken by the algorithm.
    explanation : str
        Educational rationale describing the state transition and mathematical calculations.
    """
    round_number: int
    algorithm: str
    cwnd: float
    ssthresh: float
    tcp_state: TCPState
    congestion_event: LossEventType = LossEventType.NONE
    retransmission_event: bool = False
    algorithm_action: str = ""
    explanation: str = ""


@dataclass
class SimulationResult:
    """
    Complete dataset resulting from an executed simulation run.

    Attributes
    ----------
    parameters : SimulationParameters
        Configuration used to generate these results.
    steps : List[SimulationStep]
        Round-by-round time-series data of TCP states.
    """
    parameters: SimulationParameters
    steps: List[SimulationStep] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert the simulation steps into a structured Pandas DataFrame.
        Provides both Phase 2 canonical columns and backward-compatible aliases.
        """
        columns = [
            "RTT_Round", "Algorithm", "CWND", "SSTHRESH", "TCP_State",
            "Loss_Event", "Retransmission", "Action", "Explanation",
            # Backward-compatibility aliases
            "round", "cwnd", "ssthresh", "tcp_state",
            "congestion_event", "retransmission_event", "algorithm_action"
        ]
        if not self.steps:
            return pd.DataFrame(columns=columns)

        records = []
        for step in self.steps:
            state_str = step.tcp_state.value if isinstance(step.tcp_state, TCPState) else str(step.tcp_state)
            event_str = step.congestion_event.value if isinstance(step.congestion_event, LossEventType) else str(step.congestion_event)

            record = {
                "RTT_Round": step.round_number,
                "Algorithm": step.algorithm,
                "CWND": step.cwnd,
                "SSTHRESH": step.ssthresh,
                "TCP_State": state_str,
                "Loss_Event": event_str,
                "Retransmission": step.retransmission_event,
                "Action": step.algorithm_action,
                "Explanation": step.explanation,
                # Aliases
                "round": step.round_number,
                "cwnd": step.cwnd,
                "ssthresh": step.ssthresh,
                "tcp_state": state_str,
                "congestion_event": event_str,
                "retransmission_event": step.retransmission_event,
                "algorithm_action": step.algorithm_action,
            }
            records.append(record)

        return pd.DataFrame.from_records(records)

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Compute aggregate performance statistics for this simulation run."""
        if not self.steps:
            return {
                "algorithm": self.parameters.algorithm,
                "total_rounds": 0,
                "final_cwnd": 0.0,
                "final_ssthresh": 0.0,
                "peak_cwnd": 0.0,
                "average_cwnd": 0.0,
                "total_retransmissions": 0,
                "timeout_count": 0,
                "fast_retransmit_count": 0,
                "slow_start_rounds": 0,
                "congestion_avoidance_rounds": 0,
                "fast_recovery_rounds": 0,
            }

        cwnds = [s.cwnd for s in self.steps]
        retrans = sum(1 for s in self.steps if s.retransmission_event)
        timeouts = sum(1 for s in self.steps if s.congestion_event == LossEventType.TIMEOUT)
        fast_retrans = sum(1 for s in self.steps if s.congestion_event == LossEventType.TRIPLE_DUPLICATE_ACK)
        slow_start_count = sum(1 for s in self.steps if s.tcp_state == TCPState.SLOW_START)
        ca_count = sum(1 for s in self.steps if s.tcp_state == TCPState.CONGESTION_AVOIDANCE)
        fr_count = sum(1 for s in self.steps if s.tcp_state == TCPState.FAST_RECOVERY)

        return {
            "algorithm": self.parameters.algorithm,
            "total_rounds": len(self.steps),
            "final_cwnd": cwnds[-1],
            "final_ssthresh": self.steps[-1].ssthresh,
            "peak_cwnd": max(cwnds),
            "average_cwnd": round(sum(cwnds) / len(cwnds), 2),
            "total_retransmissions": retrans,
            "timeout_count": timeouts,
            "fast_retransmit_count": fast_retrans,
            "slow_start_rounds": slow_start_count,
            "congestion_avoidance_rounds": ca_count,
            "fast_recovery_rounds": fr_count,
        }


class BaseTCPCongestionControl(ABC):
    """
    Abstract base class for TCP congestion control simulation engines.
    Encapsulates state variables, random loss generators, and round progression.
    """

    def __init__(self, parameters: SimulationParameters) -> None:
        parameters.validate()
        self.parameters = parameters
        self.cwnd: float = float(parameters.initial_cwnd)
        self.ssthresh: float = float(parameters.initial_ssthresh)
        self.state: TCPState = TCPState.CONGESTION_AVOIDANCE if self.cwnd >= self.ssthresh else TCPState.SLOW_START
        self.history: List[SimulationStep] = []

        # Normalize scheduled loss events dictionary
        self.scheduled_losses: Dict[int, LossEventType] = {
            int(k): normalize_loss_event(v)
            for k, v in parameters.loss_events.items()
        }

        # Initialize dedicated random generator for reproducibility
        self.rng = random.Random(parameters.random_seed)

    def calculate_ssthresh(self, current_flight: float) -> float:
        """
        Calculate new SSTHRESH upon packet loss.
        Per RFC 5681: SSTHRESH = max(floor(flight_size / 2), 2 MSS).
        """
        return max(math.floor(current_flight / 2.0), 2.0)

    def clamp_cwnd(self, value: float) -> float:
        """Enforce lower bound of 1.0 MSS and optional upper bound max_cwnd."""
        val = max(value, 1.0)
        if self.parameters.max_cwnd is not None:
            val = min(val, self.parameters.max_cwnd)
        return val

    def determine_round_loss(self, round_num: int) -> LossEventType:
        """
        Determine whether a loss event occurs in round_num.
        Deterministic loss takes precedence. If absent, evaluate random loss.
        """
        if round_num in self.scheduled_losses:
            return self.scheduled_losses[round_num]

        if self.parameters.loss_probability > 0.0:
            if self.rng.random() < self.parameters.loss_probability:
                # By default, random drops in TCP are treated as Triple Duplicate ACKs
                return LossEventType.TRIPLE_DUPLICATE_ACK

        return LossEventType.NONE

    @abstractmethod
    def step(self, round_num: int) -> SimulationStep:
        """Execute one discrete RTT round and return the recorded state."""
        pass

    def run_simulation(self) -> SimulationResult:
        """Execute the full discrete-event simulation across all rounds."""
        self.history.clear()
        self.cwnd = float(self.parameters.initial_cwnd)
        self.ssthresh = float(self.parameters.initial_ssthresh)
        self.state = TCPState.CONGESTION_AVOIDANCE if self.cwnd >= self.ssthresh else TCPState.SLOW_START

        for round_idx in range(1, self.parameters.num_rounds + 1):
            step_record = self.step(round_idx)
            self.history.append(step_record)

        return SimulationResult(parameters=self.parameters, steps=list(self.history))


class TCPTahoe(BaseTCPCongestionControl):
    """
    TCP Tahoe (RFC 1122, RFC 2001) Congestion Control Engine.

    Key Principles:
    1. Slow Start:
       - Begins at configured initial CWND (typically 1.0 MSS).
       - Doubles CWND every RTT round until CWND >= SSTHRESH.
    2. Congestion Avoidance:
       - Entered when CWND >= SSTHRESH.
       - Additive Increase: CWND increases linearly by approximately 1.0 MSS per RTT.
    3. Packet Loss Handling (Both Timeout AND Triple Duplicate ACKs):
       - SSTHRESH is updated to max(floor(CWND / 2), 2).
       - CWND is reset to 1.0 MSS.
       - Re-enters Slow Start.
       - Tahoe does NOT implement Fast Recovery.
    """

    def handle_ack(self) -> None:
        """Adjust CWND in absence of loss according to current state."""
        if self.state == TCPState.SLOW_START:
            # Exponential growth: CWND doubles across one RTT round
            next_cwnd = self.clamp_cwnd(self.cwnd * 2.0)
            if next_cwnd >= self.ssthresh:
                self.cwnd = next_cwnd
                self.state = TCPState.CONGESTION_AVOIDANCE
            else:
                self.cwnd = next_cwnd
        elif self.state == TCPState.CONGESTION_AVOIDANCE:
            # Linear growth (AIMD Additive Increase): +1 MSS per RTT
            self.cwnd = self.clamp_cwnd(self.cwnd + 1.0)

    def handle_loss(self, loss_type: LossEventType) -> Tuple[bool, str, str]:
        """
        Handle congestion events in TCP Tahoe.
        Both Timeout and 3 Duplicate ACKs reset CWND to 1.0 MSS and enter Slow Start.
        """
        retransmission = True
        new_ssthresh = self.calculate_ssthresh(self.cwnd)
        self.ssthresh = new_ssthresh
        self.cwnd = 1.0
        self.state = TCPState.SLOW_START

        if loss_type == LossEventType.TIMEOUT:
            action = "Timeout: CWND reset to 1 MSS, enter Slow Start"
            explanation = (
                f"Retransmission Timeout (RTO) expired. SSTHRESH halved to {new_ssthresh:.1f} MSS. "
                f"CWND dropped to 1.0 MSS. Slow Start resumed."
            )
        elif loss_type == LossEventType.TRIPLE_DUPLICATE_ACK:
            action = "Fast Retransmit: CWND reset to 1 MSS, enter Slow Start"
            explanation = (
                f"3 duplicate ACKs detected. Fast Retransmit triggered. "
                f"SSTHRESH halved to {new_ssthresh:.1f} MSS. CWND reset to 1.0 MSS (Tahoe lacks Fast Recovery)."
            )
        else:
            action = "No congestion event"
            explanation = "Normal transmission."
            retransmission = False

        return retransmission, action, explanation

    def step(self, round_num: int) -> SimulationStep:
        loss_event = self.determine_round_loss(round_num)

        if loss_event != LossEventType.NONE:
            retransmission, action, explanation = self.handle_loss(loss_event)
        else:
            retransmission = False
            prev_state = self.state
            prev_cwnd = self.cwnd
            self.handle_ack()

            if prev_state == TCPState.SLOW_START and self.state == TCPState.CONGESTION_AVOIDANCE:
                action = "Slow Start -> Congestion Avoidance transition"
                explanation = (
                    f"CWND reached SSTHRESH ({self.ssthresh:.1f} MSS). "
                    f"Transitioned from exponential growth to linear Congestion Avoidance (CWND = {self.cwnd:.1f} MSS)."
                )
            elif self.state == TCPState.SLOW_START:
                action = "Slow Start: Exponential CWND growth"
                explanation = f"CWND doubled from {prev_cwnd:.1f} to {self.cwnd:.1f} MSS (below SSTHRESH {self.ssthresh:.1f} MSS)."
            else:
                action = "Congestion Avoidance: Linear CWND growth (AIMD)"
                explanation = f"Additive increase: CWND increased by 1 MSS from {prev_cwnd:.1f} to {self.cwnd:.1f} MSS."

        return SimulationStep(
            round_number=round_num,
            algorithm="Tahoe",
            cwnd=self.cwnd,
            ssthresh=self.ssthresh,
            tcp_state=self.state,
            congestion_event=loss_event,
            retransmission_event=retransmission,
            algorithm_action=action,
            explanation=explanation,
        )


class TCPReno(BaseTCPCongestionControl):
    """
    TCP Reno (RFC 2581, RFC 5681) Congestion Control Engine.

    Key Principles:
    1. Slow Start:
       - Identical to Tahoe: exponential growth up to SSTHRESH.
    2. Congestion Avoidance:
       - Identical to Tahoe: Additive Increase (+1 MSS per RTT).
    3. Fast Retransmit:
       - Triggered upon receiving 3 duplicate ACKs.
       - Retransmits missing segment immediately without waiting for RTO.
    4. Fast Recovery:
       - Upon 3 Duplicate ACKs:
         * SSTHRESH = max(floor(CWND / 2), 2 MSS).
         * CWND is set to SSTHRESH + 3.0 MSS (window inflation).
         * State becomes Fast Recovery.
       - When a new recovery ACK arrives:
         * CWND is deflated back to SSTHRESH.
         * Enters Congestion Avoidance directly (avoids pipeline draining).
    5. Timeout Handling:
       - RTO timer expiration resets CWND to 1.0 MSS and returns to Slow Start.
    """

    def __init__(self, parameters: SimulationParameters) -> None:
        super().__init__(parameters)
        self.in_fast_recovery: bool = False

    def handle_ack(self) -> Tuple[str, str]:
        """Adjust CWND when acknowledgements are received without packet loss."""
        if self.in_fast_recovery:
            # Recovery ACK received: deflate window back to SSTHRESH and enter Congestion Avoidance
            self.in_fast_recovery = False
            self.state = TCPState.CONGESTION_AVOIDANCE
            self.cwnd = self.clamp_cwnd(self.ssthresh)
            action = "Fast Recovery Exit: Deflate CWND to SSTHRESH"
            explanation = (
                f"Recovery ACK received acknowledging retransmitted segment. "
                f"CWND deflated from inflated recovery state to SSTHRESH ({self.ssthresh:.1f} MSS). "
                f"Congestion Avoidance resumed."
            )
            return action, explanation

        if self.state == TCPState.SLOW_START:
            next_cwnd = self.clamp_cwnd(self.cwnd * 2.0)
            if next_cwnd >= self.ssthresh:
                self.cwnd = next_cwnd
                self.state = TCPState.CONGESTION_AVOIDANCE
                action = "Slow Start -> Congestion Avoidance transition"
                explanation = (
                    f"CWND reached SSTHRESH ({self.ssthresh:.1f} MSS). "
                    f"Transitioned from Slow Start to Congestion Avoidance (CWND = {self.cwnd:.1f} MSS)."
                )
            else:
                prev_cwnd = self.cwnd
                self.cwnd = next_cwnd
                action = "Slow Start: Exponential CWND growth"
                explanation = f"CWND doubled from {prev_cwnd:.1f} to {self.cwnd:.1f} MSS (below SSTHRESH {self.ssthresh:.1f} MSS)."
            return action, explanation

        # Congestion Avoidance (AIMD Additive Increase)
        prev_cwnd = self.cwnd
        self.cwnd = self.clamp_cwnd(self.cwnd + 1.0)
        action = "Congestion Avoidance: Linear CWND growth (AIMD)"
        explanation = f"Additive increase: CWND increased by 1 MSS from {prev_cwnd:.1f} to {self.cwnd:.1f} MSS."
        return action, explanation

    def handle_loss(self, loss_type: LossEventType) -> Tuple[bool, str, str]:
        """
        Handle congestion events in TCP Reno.
        Triple Duplicate ACK triggers Fast Retransmit & Fast Recovery.
        Timeout resets CWND to 1.0 MSS and returns to Slow Start.
        """
        retransmission = True
        new_ssthresh = self.calculate_ssthresh(self.cwnd)
        self.ssthresh = new_ssthresh

        if loss_type == LossEventType.TRIPLE_DUPLICATE_ACK:
            # Fast Retransmit + Fast Recovery
            self.in_fast_recovery = True
            self.state = TCPState.FAST_RECOVERY
            # Inflate window by 3 MSS for the 3 duplicate ACKs
            self.cwnd = self.clamp_cwnd(new_ssthresh + 3.0)
            action = "Fast Retransmit & Fast Recovery: Inflate CWND"
            explanation = (
                f"3 duplicate ACKs received. Missing segment retransmitted immediately. "
                f"SSTHRESH halved to {new_ssthresh:.1f} MSS. "
                f"CWND set to SSTHRESH + 3 = {self.cwnd:.1f} MSS (Fast Recovery entered)."
            )
        elif loss_type == LossEventType.TIMEOUT:
            # RTO Timeout: Severe congestion, reset to 1 MSS
            self.in_fast_recovery = False
            self.state = TCPState.SLOW_START
            self.cwnd = 1.0
            action = "Timeout: CWND reset to 1 MSS, enter Slow Start"
            explanation = (
                f"Retransmission Timeout (RTO) expired. SSTHRESH halved to {new_ssthresh:.1f} MSS. "
                f"CWND reset to 1.0 MSS. Slow Start resumed."
            )
        else:
            retransmission = False
            action = "No congestion event"
            explanation = "Normal transmission."

        return retransmission, action, explanation

    def step(self, round_num: int) -> SimulationStep:
        loss_event = self.determine_round_loss(round_num)

        if loss_event != LossEventType.NONE:
            retransmission, action, explanation = self.handle_loss(loss_event)
        else:
            retransmission = False
            action, explanation = self.handle_ack()

        return SimulationStep(
            round_number=round_num,
            algorithm="Reno",
            cwnd=self.cwnd,
            ssthresh=self.ssthresh,
            tcp_state=self.state,
            congestion_event=loss_event,
            retransmission_event=retransmission,
            algorithm_action=action,
            explanation=explanation,
        )


def simulate_tcp(
    params: Optional[SimulationParameters] = None,
    **kwargs: Any
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Execute a TCP congestion control simulation and return results.

    Parameters
    ----------
    params : Optional[SimulationParameters]
        Pre-constructed parameter configuration. If omitted, constructed from kwargs.
    **kwargs : Any
        Keyword arguments passed to SimulationParameters if params is None.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, Any]]
        1. pd.DataFrame: Formatted time-series DataFrame of the simulation rounds.
        2. Dict[str, Any]: Summary metrics (peak CWND, average CWND, retransmissions, etc.).
    """
    if params is None:
        params = SimulationParameters(**kwargs)

    engine: BaseTCPCongestionControl
    if params.algorithm.lower() == "tahoe":
        engine = TCPTahoe(params)
    elif params.algorithm.lower() == "reno":
        engine = TCPReno(params)
    else:
        raise ValueError(f"Unknown algorithm '{params.algorithm}'. Choose 'Tahoe' or 'Reno'.")

    result = engine.run_simulation()
    return result.to_dataframe(), result.get_summary_metrics()


def compare_algorithms(
    params: Optional[SimulationParameters] = None,
    **kwargs: Any
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Run identical simulations for both TCP Tahoe and TCP Reno and generate a comparative dataset.

    Parameters
    ----------
    params : Optional[SimulationParameters]
        Base parameter configuration applied to both engines.
    **kwargs : Any
        Keyword arguments passed to SimulationParameters if params is None.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, Any]]
        1. pd.DataFrame: Combined comparison DataFrame with Tahoe vs Reno metrics.
        2. Dict[str, Any]: Comparative summary dictionary comparing peak, average, and final CWND.
    """
    if params is None:
        params = SimulationParameters(**kwargs)

    # Instantiate Tahoe configuration
    tahoe_params = SimulationParameters(
        algorithm="Tahoe",
        initial_cwnd=params.initial_cwnd,
        initial_ssthresh=params.initial_ssthresh,
        mss=params.mss,
        max_cwnd=params.max_cwnd,
        num_rounds=params.num_rounds,
        loss_probability=params.loss_probability,
        loss_events=dict(params.loss_events),
        random_seed=params.random_seed,
    )

    # Instantiate Reno configuration
    reno_params = SimulationParameters(
        algorithm="Reno",
        initial_cwnd=params.initial_cwnd,
        initial_ssthresh=params.initial_ssthresh,
        mss=params.mss,
        max_cwnd=params.max_cwnd,
        num_rounds=params.num_rounds,
        loss_probability=params.loss_probability,
        loss_events=dict(params.loss_events),
        random_seed=params.random_seed,
    )

    tahoe_res = TCPTahoe(tahoe_params).run_simulation()
    reno_res = TCPReno(reno_params).run_simulation()

    df_tahoe = tahoe_res.to_dataframe()
    df_reno = reno_res.to_dataframe()

    # Construct combined comparison DataFrame
    comparison_rows = []
    for idx in range(len(tahoe_res.steps)):
        s_t = tahoe_res.steps[idx]
        s_r = reno_res.steps[idx]
        comparison_rows.append({
            "RTT_Round": s_t.round_number,
            "Loss_Event": s_t.congestion_event.value,
            "Tahoe_CWND": s_t.cwnd,
            "Reno_CWND": s_r.cwnd,
            "Tahoe_SSTHRESH": s_t.ssthresh,
            "Reno_SSTHRESH": s_r.ssthresh,
            "Tahoe_State": s_t.tcp_state.value,
            "Reno_State": s_r.tcp_state.value,
            "Tahoe_Retransmission": s_t.retransmission_event,
            "Reno_Retransmission": s_r.retransmission_event,
            "Tahoe_Action": s_t.algorithm_action,
            "Reno_Action": s_r.algorithm_action,
            "CWND_Difference": round(s_r.cwnd - s_t.cwnd, 2),
        })

    comp_df = pd.DataFrame.from_records(comparison_rows)

    m_t = tahoe_res.get_summary_metrics()
    m_r = reno_res.get_summary_metrics()

    tahoe_avg = m_t["average_cwnd"]
    reno_avg = m_r["average_cwnd"]
    advantage = round(((reno_avg - tahoe_avg) / tahoe_avg) * 100.0, 2) if tahoe_avg > 0 else 0.0

    summary_comparison = {
        "total_rounds": len(tahoe_res.steps),
        "tahoe_final_cwnd": m_t["final_cwnd"],
        "reno_final_cwnd": m_r["final_cwnd"],
        "tahoe_average_cwnd": tahoe_avg,
        "reno_average_cwnd": reno_avg,
        "tahoe_peak_cwnd": m_t["peak_cwnd"],
        "reno_peak_cwnd": m_r["peak_cwnd"],
        "tahoe_retransmissions": m_t["total_retransmissions"],
        "reno_retransmissions": m_r["total_retransmissions"],
        "tahoe_timeouts": m_t["timeout_count"],
        "reno_timeouts": m_r["timeout_count"],
        "tahoe_fast_retransmits": m_t["fast_retransmit_count"],
        "reno_fast_retransmits": m_r["fast_retransmit_count"],
        "reno_throughput_advantage_percent": advantage,
    }

    return comp_df, summary_comparison
