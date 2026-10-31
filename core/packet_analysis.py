"""
Core Packet Analysis Module
===========================
Processes PCAP and PCAPNG packet capture files to inspect TCP conversations,
trace Sequence and Acknowledgement numbers, and identify retransmissions,
duplicate ACKs, TCP flags, and Round-Trip Time dynamics.

Tools Supported:
- Wireshark / TShark CLI integration (primary high-performance extraction).
- Pre-flight binary and environment verification.
- Safe tempfile handling and strict input validation.

Scientific Data Integrity:
- Real captures from Wireshark, tcpdump, or Mininet are analyzed directly.
- No synthetic or fabricated packet records are generated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from utils.helpers import (
    is_tshark_available,
    get_tshark_path,
    get_capinfos_path,
    run_safe_command
)

# Standard PCAP and PCAPNG magic numbers (4 bytes)
VALID_PCAP_MAGICS = {
    b"\xd4\xc3\xb2\xa1",  # Standard PCAP (Little-endian, microsecond)
    b"\xa1\xb2\xc3\xd4",  # Standard PCAP (Big-endian, microsecond)
    b"\x4d\x3c\xb2\xa1",  # Nanosecond PCAP (Little-endian)
    b"\xa1\xb2\x3c\x4d",  # Nanosecond PCAP (Big-endian)
    b"\x0a\x0d\x0d\x0a",  # PCAPNG Section Header Block (SHB)
}

# Maximum supported upload size (50 MB default)
MAX_CAPTURE_FILE_SIZE = 50 * 1024 * 1024


def validate_capture_file(filepath: str, max_size_bytes: int = MAX_CAPTURE_FILE_SIZE) -> None:
    """
    Validate that a given capture file exists, has a valid extension, is non-empty,
    does not exceed size limits, and contains valid PCAP or PCAPNG header magic bytes.

    Raises
    ------
    FileNotFoundError: If the file does not exist on disk.
    ValueError: If extension, size, or header magic bytes are invalid.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Packet capture file '{filepath}' does not exist.")

    # Extension check
    _, ext = os.path.splitext(filepath)
    ext_lower = ext.lower()
    if ext_lower not in [".pcap", ".pcapng"]:
        raise ValueError(
            f"Unsupported file format '{ext}'. Only .pcap and .pcapng files are supported."
        )

    # Size check
    file_size = os.path.getsize(filepath)
    if file_size == 0:
        raise ValueError("Capture file is empty (0 bytes).")

    if file_size > max_size_bytes:
        limit_mb = max_size_bytes / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"Capture file size ({actual_mb:.1f} MB) exceeds maximum allowed limit ({limit_mb:.1f} MB)."
        )

    if file_size < 4:
        raise ValueError("Capture file is corrupted or too short (< 4 bytes) to contain a valid header.")

    # Magic bytes check
    try:
        with open(filepath, "rb") as f:
            header = f.read(4)
            if header not in VALID_PCAP_MAGICS:
                raise ValueError(
                    "Invalid or corrupted capture file: Header does not match standard PCAP or PCAPNG magic bytes."
                )
    except PermissionError as pe:
        raise PermissionError(f"Permission denied while reading capture file: {pe}") from pe


@dataclass
class PacketRecord:
    """
    Standardized schema for an individual extracted TCP packet.

    Attributes
    ----------
    packet_id : int
        Frame sequence number in the capture file.
    timestamp : float
        Packet capture timestamp relative to capture start (seconds).
    source_ip : str
        Source IPv4 or IPv6 address.
    destination_ip : str
        Destination IPv4 or IPv6 address.
    source_port : int
        Source TCP port number.
    destination_port : int
        Destination TCP port number.
    seq_number : int
        TCP sequence number.
    ack_number : int
        TCP acknowledgement number.
    tcp_flags : str
        Human-readable representation of active flags (e.g., '[SYN, ACK]').
    window_size : int
        Advertised receive window size in bytes.
    payload_len : int
        TCP segment data payload length in bytes.
    is_retransmission : bool
        Flag indicating if packet was flagged as a TCP retransmission.
    is_duplicate_ack : bool
        Flag indicating if packet is a duplicate ACK.
    rtt_sec : Optional[float]
        Round-Trip Time measured for the ACK-Seq pair (if determinable).
    is_fast_retransmission : bool
        Flag indicating Fast Retransmit (typically triggered by 3 duplicate ACKs).
    is_spurious_retransmission : bool
        Flag indicating spurious retransmission (ACK arrived after retransmission timer).
    is_out_of_order : bool
        Flag indicating out-of-order segment arrival.
    duplicate_ack_num : Optional[int]
        Sequential duplicate ACK index (1, 2, 3, ...).
    raw_seq : Optional[int]
        Raw 32-bit TCP sequence number.
    raw_ack : Optional[int]
        Raw 32-bit TCP acknowledgement number.
    flag_syn : bool
        True if SYN flag is set.
    flag_ack : bool
        True if ACK flag is set.
    flag_fin : bool
        True if FIN flag is set.
    flag_rst : bool
        True if RST flag is set.
    flag_psh : bool
        True if PSH flag is set.
    flag_urg : bool
        True if URG flag is set.
    flag_ece : bool
        True if ECE flag is set (ECN Echo).
    flag_cwr : bool
        True if CWR flag is set (Congestion Window Reduced).
    """
    packet_id: int
    timestamp: float
    source_ip: str
    destination_ip: str
    source_port: int
    destination_port: int
    seq_number: int
    ack_number: int
    tcp_flags: str
    window_size: int
    payload_len: int
    is_retransmission: bool = False
    is_duplicate_ack: bool = False
    rtt_sec: Optional[float] = None
    is_fast_retransmission: bool = False
    is_spurious_retransmission: bool = False
    is_out_of_order: bool = False
    duplicate_ack_num: Optional[int] = None
    raw_seq: Optional[int] = None
    raw_ack: Optional[int] = None
    flag_syn: bool = False
    flag_ack: bool = False
    flag_fin: bool = False
    flag_rst: bool = False
    flag_psh: bool = False
    flag_urg: bool = False
    flag_ece: bool = False
    flag_cwr: bool = False


@dataclass
class PacketAnalysisSummary:
    """
    Aggregated statistical summary of an analysed TCP packet capture.
    """
    filename: str
    total_packets: int = 0
    total_tcp_packets: int = 0
    retransmission_count: int = 0
    fast_retransmission_count: int = 0
    spurious_retransmission_count: int = 0
    out_of_order_count: int = 0
    duplicate_ack_count: int = 0
    syn_count: int = 0
    fin_count: int = 0
    rst_count: int = 0
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    packets: List[PacketRecord] = field(default_factory=list)

    @property
    def retransmission_rate(self) -> float:
        """
        Retransmission percentage with clearly documented denominator:
        (Total Retransmissions / Total TCP Packets) * 100%.
        """
        if self.total_tcp_packets == 0:
            return 0.0
        return (self.retransmission_count / self.total_tcp_packets) * 100.0

    @property
    def duplicate_ack_rate(self) -> float:
        """
        Duplicate ACK percentage:
        (Total Duplicate ACKs / Total TCP Packets) * 100%.
        """
        if self.total_tcp_packets == 0:
            return 0.0
        return (self.duplicate_ack_count / self.total_tcp_packets) * 100.0

    @property
    def flag_distribution(self) -> Dict[str, int]:
        """Distribution dictionary of TCP control flags across extracted TCP packets."""
        counts = {
            "SYN": self.syn_count,
            "ACK": 0,
            "FIN": self.fin_count,
            "RST": self.rst_count,
            "PSH": 0,
            "URG": 0,
            "ECE": 0,
            "CWR": 0,
        }
        for p in self.packets:
            if p.flag_ack:
                counts["ACK"] += 1
            if p.flag_psh:
                counts["PSH"] += 1
            if p.flag_urg:
                counts["URG"] += 1
            if p.flag_ece:
                counts["ECE"] += 1
            if p.flag_cwr:
                counts["CWR"] += 1
        return counts

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert detailed packet records into a structured Pandas DataFrame.
        """
        columns = [
            "packet_id", "timestamp", "source_ip", "destination_ip",
            "source_port", "destination_port", "seq_number", "ack_number",
            "tcp_flags", "window_size", "payload_len", "is_retransmission",
            "is_duplicate_ack", "rtt_sec", "is_fast_retransmission",
            "is_spurious_retransmission", "is_out_of_order", "duplicate_ack_num",
            "raw_seq", "raw_ack", "flag_syn", "flag_ack", "flag_fin",
            "flag_rst", "flag_psh", "flag_urg", "flag_ece", "flag_cwr"
        ]

        if not self.packets:
            return pd.DataFrame(columns=columns)

        records = [
            {
                "packet_id": p.packet_id,
                "timestamp": p.timestamp,
                "source_ip": p.source_ip,
                "destination_ip": p.destination_ip,
                "source_port": p.source_port,
                "destination_port": p.destination_port,
                "seq_number": p.seq_number,
                "ack_number": p.ack_number,
                "tcp_flags": p.tcp_flags,
                "window_size": p.window_size,
                "payload_len": p.payload_len,
                "is_retransmission": p.is_retransmission,
                "is_duplicate_ack": p.is_duplicate_ack,
                "rtt_sec": p.rtt_sec,
                "is_fast_retransmission": p.is_fast_retransmission,
                "is_spurious_retransmission": p.is_spurious_retransmission,
                "is_out_of_order": p.is_out_of_order,
                "duplicate_ack_num": p.duplicate_ack_num,
                "raw_seq": p.raw_seq,
                "raw_ack": p.raw_ack,
                "flag_syn": p.flag_syn,
                "flag_ack": p.flag_ack,
                "flag_fin": p.flag_fin,
                "flag_rst": p.flag_rst,
                "flag_psh": p.flag_psh,
                "flag_urg": p.flag_urg,
                "flag_ece": p.flag_ece,
                "flag_cwr": p.flag_cwr,
            }
            for p in self.packets
        ]
        return pd.DataFrame.from_records(records)


class PacketAnalyzer:
    """
    Engine for ingesting, validating, and dissecting PCAP/PCAPNG capture files
    using TShark CLI subprocess execution.
    """

    TSHARK_FIELDS = [
        "-e", "frame.number",
        "-e", "frame.time_relative",
        "-e", "ip.src",
        "-e", "ipv6.src",
        "-e", "ip.dst",
        "-e", "ipv6.dst",
        "-e", "tcp.srcport",
        "-e", "tcp.dstport",
        "-e", "tcp.seq",
        "-e", "tcp.ack",
        "-e", "tcp.seq_raw",
        "-e", "tcp.ack_raw",
        "-e", "tcp.len",
        "-e", "tcp.flags",
        "-e", "tcp.flags.syn",
        "-e", "tcp.flags.ack",
        "-e", "tcp.flags.fin",
        "-e", "tcp.flags.reset",
        "-e", "tcp.flags.push",
        "-e", "tcp.flags.urg",
        "-e", "tcp.flags.ece",
        "-e", "tcp.flags.cwr",
        "-e", "tcp.window_size_value",
        "-e", "tcp.analysis.retransmission",
        "-e", "tcp.analysis.fast_retransmission",
        "-e", "tcp.analysis.spurious_retransmission",
        "-e", "tcp.analysis.out_of_order",
        "-e", "tcp.analysis.duplicate_ack",
        "-e", "tcp.analysis.duplicate_ack_num",
        "-e", "tcp.analysis.ack_rtt",
    ]

    def __init__(self, filepath: str, tshark_path: Optional[str] = None) -> None:
        """
        Initialize PacketAnalyzer with a validated capture file path.

        Parameters
        ----------
        filepath : str
            Path to .pcap or .pcapng file.
        tshark_path : Optional[str]
            Explicit path to tshark binary (default auto-detected).
        """
        validate_capture_file(filepath)
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.file_size = os.path.getsize(filepath)
        self.tshark_path = tshark_path or get_tshark_path()

    @staticmethod
    def get_analysis_engine() -> str:
        """Identify available analysis engine."""
        if is_tshark_available():
            path = get_tshark_path()
            return f"TShark ({path})"
        return "TShark (Not Detected — Installation Required)"

    def build_tshark_command(self) -> List[str]:
        """Construct the safe argument list for invoking TShark."""
        bin_path = self.tshark_path or "tshark"
        return [
            bin_path,
            "-r", self.filepath,
            "-Y", "tcp",
            "-T", "fields",
            "-E", "header=y",
            "-E", "separator=\t",
            "-E", "occurrence=f",
            *self.TSHARK_FIELDS
        ]

    def parse_tshark_output(
        self,
        output_text: str,
        total_packets: Optional[int] = None,
        duration_seconds: Optional[float] = None
    ) -> PacketAnalysisSummary:
        """
        Parse raw tab-separated output generated by TShark.
        Robustly handles missing columns, empty files, and varied flag formats.

        Parameters
        ----------
        output_text : str
            Standard output text from TShark execution.
        total_packets : Optional[int]
            Total frame count across all protocols if determined via capinfos/tshark.
        duration_seconds : Optional[float]
            Total capture duration if determined from metadata.
        """
        lines = [line.strip("\r\n") for line in output_text.strip().split("\n") if line.strip()]

        if not lines:
            return PacketAnalysisSummary(
                filename=self.filename,
                total_packets=total_packets or 0,
                total_tcp_packets=0,
                file_size_bytes=self.file_size,
                duration_seconds=duration_seconds or 0.0,
                packets=[]
            )

        # Detect header line
        header_idx = -1
        col_map: Dict[str, int] = {}

        for idx, line in enumerate(lines):
            parts = line.split("\t")
            if "frame.number" in parts or any(col.startswith("tcp.") or col.startswith("frame.") for col in parts):
                header_idx = idx
                col_map = {col.strip(): i for i, col in enumerate(parts)}
                break

        data_lines = lines[header_idx + 1:] if header_idx != -1 else lines

        packets: List[PacketRecord] = []
        timestamps: List[float] = []

        syn_count = 0
        fin_count = 0
        rst_count = 0
        retransmission_count = 0
        fast_retransmission_count = 0
        spurious_retransmission_count = 0
        out_of_order_count = 0
        duplicate_ack_count = 0

        for line_no, line in enumerate(data_lines, start=1):
            parts = line.split("\t")
            if not parts or all(p == "" for p in parts):
                continue

            def get_val(key: str, default: str = "") -> str:
                if key in col_map:
                    idx = col_map[key]
                    return parts[idx].strip() if idx < len(parts) else default
                return default

            # If header mapping wasn't found, fall back to index matching based on TSHARK_FIELDS
            if not col_map:
                field_names = [
                    "frame.number", "frame.time_relative", "ip.src", "ipv6.src",
                    "ip.dst", "ipv6.dst", "tcp.srcport", "tcp.dstport", "tcp.seq",
                    "tcp.ack", "tcp.seq_raw", "tcp.ack_raw", "tcp.len", "tcp.flags",
                    "tcp.flags.syn", "tcp.flags.ack", "tcp.flags.fin", "tcp.flags.reset",
                    "tcp.flags.push", "tcp.flags.urg", "tcp.flags.ece", "tcp.flags.cwr",
                    "tcp.window_size_value", "tcp.analysis.retransmission",
                    "tcp.analysis.fast_retransmission", "tcp.analysis.spurious_retransmission",
                    "tcp.analysis.out_of_order", "tcp.analysis.duplicate_ack",
                    "tcp.analysis.duplicate_ack_num", "tcp.analysis.ack_rtt"
                ]
                col_map = {name: i for i, name in enumerate(field_names)}

            # Frame ID
            try:
                packet_id = int(get_val("frame.number", str(line_no)))
            except ValueError:
                packet_id = line_no

            # Relative timestamp
            try:
                timestamp = float(get_val("frame.time_relative", "0.0"))
            except ValueError:
                timestamp = 0.0
            timestamps.append(timestamp)

            # Endpoints
            src_ip = get_val("ip.src") or get_val("ipv6.src") or "0.0.0.0"
            dst_ip = get_val("ip.dst") or get_val("ipv6.dst") or "0.0.0.0"

            try:
                src_port = int(get_val("tcp.srcport", "0"))
            except ValueError:
                src_port = 0

            try:
                dst_port = int(get_val("tcp.dstport", "0"))
            except ValueError:
                dst_port = 0

            # Sequence and ACK numbers
            try:
                seq_num = int(get_val("tcp.seq", "0"))
            except ValueError:
                seq_num = 0

            try:
                ack_num = int(get_val("tcp.ack", "0"))
            except ValueError:
                ack_num = 0

            try:
                raw_seq = int(get_val("tcp.seq_raw")) if get_val("tcp.seq_raw") else None
            except ValueError:
                raw_seq = None

            try:
                raw_ack = int(get_val("tcp.ack_raw")) if get_val("tcp.ack_raw") else None
            except ValueError:
                raw_ack = None

            try:
                payload_len = int(get_val("tcp.len", "0"))
            except ValueError:
                payload_len = 0

            try:
                window_size = int(get_val("tcp.window_size_value", "0"))
            except ValueError:
                window_size = 0

            # Flag parsing
            raw_flags_hex = get_val("tcp.flags", "")
            syn_str = get_val("tcp.flags.syn")
            ack_str = get_val("tcp.flags.ack")
            fin_str = get_val("tcp.flags.fin")
            rst_str = get_val("tcp.flags.reset")
            psh_str = get_val("tcp.flags.push")
            urg_str = get_val("tcp.flags.urg")
            ece_str = get_val("tcp.flags.ece")
            cwr_str = get_val("tcp.flags.cwr")

            flag_syn = syn_str == "1"
            flag_ack = ack_str == "1"
            flag_fin = fin_str == "1"
            flag_rst = rst_str == "1"
            flag_psh = psh_str == "1"
            flag_urg = urg_str == "1"
            flag_ece = ece_str == "1"
            flag_cwr = cwr_str == "1"

            # Parse hex flag bitmask if explicit fields were empty
            if raw_flags_hex and not any([flag_syn, flag_ack, flag_fin, flag_rst, flag_psh, flag_urg, flag_ece, flag_cwr]):
                try:
                    val = int(raw_flags_hex, 16) if raw_flags_hex.startswith("0x") else int(raw_flags_hex)
                    flag_fin = bool(val & 0x0001)
                    flag_syn = bool(val & 0x0002)
                    flag_rst = bool(val & 0x0004)
                    flag_psh = bool(val & 0x0008)
                    flag_ack = bool(val & 0x0010)
                    flag_urg = bool(val & 0x0020)
                    flag_ece = bool(val & 0x0040)
                    flag_cwr = bool(val & 0x0080)
                except ValueError:
                    pass

            if flag_syn:
                syn_count += 1
            if flag_fin:
                fin_count += 1
            if flag_rst:
                rst_count += 1

            active_flags = []
            if flag_syn:
                active_flags.append("SYN")
            if flag_ack:
                active_flags.append("ACK")
            if flag_psh:
                active_flags.append("PSH")
            if flag_fin:
                active_flags.append("FIN")
            if flag_rst:
                active_flags.append("RST")
            if flag_urg:
                active_flags.append("URG")
            if flag_ece:
                active_flags.append("ECE")
            if flag_cwr:
                active_flags.append("CWR")

            flag_display = "[" + ", ".join(active_flags) + "]" if active_flags else "None"

            # Retransmissions
            retrans_val = get_val("tcp.analysis.retransmission")
            fast_retrans_val = get_val("tcp.analysis.fast_retransmission")
            spurious_val = get_val("tcp.analysis.spurious_retransmission")
            ooo_val = get_val("tcp.analysis.out_of_order")

            is_fast = bool(fast_retrans_val) and fast_retrans_val not in ("0", "False")
            is_spurious = bool(spurious_val) and spurious_val not in ("0", "False")
            is_ooo = bool(ooo_val) and ooo_val not in ("0", "False")
            is_retrans = (bool(retrans_val) and retrans_val not in ("0", "False")) or is_fast or is_spurious

            if is_retrans:
                retransmission_count += 1
            if is_fast:
                fast_retransmission_count += 1
            if is_spurious:
                spurious_retransmission_count += 1
            if is_ooo:
                out_of_order_count += 1

            # Duplicate ACKs
            dup_ack_val = get_val("tcp.analysis.duplicate_ack")
            is_dup_ack = bool(dup_ack_val) and dup_ack_val not in ("0", "False")
            if is_dup_ack:
                duplicate_ack_count += 1

            dup_num_val = get_val("tcp.analysis.duplicate_ack_num")
            try:
                dup_ack_num = int(dup_num_val) if dup_num_val else None
            except ValueError:
                dup_ack_num = None

            # RTT
            rtt_val = get_val("tcp.analysis.ack_rtt")
            try:
                rtt_sec = float(rtt_val) if rtt_val else None
            except ValueError:
                rtt_sec = None

            packet = PacketRecord(
                packet_id=packet_id,
                timestamp=timestamp,
                source_ip=src_ip,
                destination_ip=dst_ip,
                source_port=src_port,
                destination_port=dst_port,
                seq_number=seq_num,
                ack_number=ack_num,
                tcp_flags=flag_display,
                window_size=window_size,
                payload_len=payload_len,
                is_retransmission=is_retrans,
                is_duplicate_ack=is_dup_ack,
                rtt_sec=rtt_sec,
                is_fast_retransmission=is_fast,
                is_spurious_retransmission=is_spurious,
                is_out_of_order=is_ooo,
                duplicate_ack_num=dup_ack_num,
                raw_seq=raw_seq,
                raw_ack=raw_ack,
                flag_syn=flag_syn,
                flag_ack=flag_ack,
                flag_fin=flag_fin,
                flag_rst=flag_rst,
                flag_psh=flag_psh,
                flag_urg=flag_urg,
                flag_ece=flag_ece,
                flag_cwr=flag_cwr,
            )
            packets.append(packet)

        # Compute duration from timestamps if not explicitly provided
        if duration_seconds is None or duration_seconds <= 0.0:
            if timestamps:
                duration_seconds = max(0.0, max(timestamps) - min(timestamps))
            else:
                duration_seconds = 0.0

        total_tcp = len(packets)
        total_frames = total_packets if total_packets is not None and total_packets >= total_tcp else total_tcp

        return PacketAnalysisSummary(
            filename=self.filename,
            total_packets=total_frames,
            total_tcp_packets=total_tcp,
            retransmission_count=retransmission_count,
            fast_retransmission_count=fast_retransmission_count,
            spurious_retransmission_count=spurious_retransmission_count,
            out_of_order_count=out_of_order_count,
            duplicate_ack_count=duplicate_ack_count,
            syn_count=syn_count,
            fin_count=fin_count,
            rst_count=rst_count,
            duration_seconds=duration_seconds,
            file_size_bytes=self.file_size,
            packets=packets
        )

    def _query_capture_metadata(self) -> Tuple[Optional[int], Optional[float]]:
        """
        Query capinfos (if available) to retrieve total frame count and capture duration.
        Returns (total_packet_count, duration_seconds).
        """
        capinfos_path = get_capinfos_path()
        if not capinfos_path:
            return None, None

        try:
            res = run_safe_command([capinfos_path, "-c", "-u", self.filepath], timeout=10)
            if res.returncode == 0:
                pkt_count = None
                duration = None
                for line in res.stdout.splitlines():
                    lower = line.lower()
                    if "number of packets" in lower:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            digits = "".join(ch for ch in parts[1] if ch.isdigit())
                            if digits:
                                pkt_count = int(digits)
                    elif "capture duration" in lower:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            val_str = parts[1].replace("seconds", "").strip()
                            try:
                                duration = float(val_str)
                            except ValueError:
                                pass
                return pkt_count, duration
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        return None, None

    def analyze(self, timeout: int = 45) -> PacketAnalysisSummary:
        """
        Execute TShark packet extraction and parse TCP metrics.

        Parameters
        ----------
        timeout : int
            Subprocess timeout in seconds (default 45).

        Returns
        -------
        PacketAnalysisSummary
            Structured analysis summary with full packet records.

        Raises
        ------
        EnvironmentError: If TShark CLI is not available.
        TimeoutError: If execution exceeds the timeout limit.
        RuntimeError: If TShark reports a processing error.
        """
        if not is_tshark_available():
            raise EnvironmentError(
                "TShark CLI was not found on PATH or in standard Wireshark installation directories. "
                "Please install Wireshark and TShark to enable packet capture inspection."
            )

        cmd = self.build_tshark_command()

        try:
            proc = run_safe_command(cmd, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"TShark packet extraction timed out after {timeout} seconds on '{self.filename}'."
            ) from exc

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or f"TShark exited with return code {proc.returncode}"
            # Check for corrupted or unsupported file error from TShark
            if "not a capture file" in err_msg.lower() or "damaged" in err_msg.lower() or "truncated" in err_msg.lower():
                raise ValueError(f"Corrupted or unrecognized capture file: {err_msg}")
            raise RuntimeError(f"TShark packet analysis failed: {err_msg}")

        total_pkts, duration = self._query_capture_metadata()
        return self.parse_tshark_output(proc.stdout, total_packets=total_pkts, duration_seconds=duration)

    @staticmethod
    def filter_dataframe(
        df: pd.DataFrame,
        source_ip: Optional[str] = None,
        destination_ip: Optional[str] = None,
        source_port: Optional[int] = None,
        destination_port: Optional[int] = None,
        flag_filter: Optional[str] = None,
        retransmissions_only: bool = False,
        duplicate_acks_only: bool = False,
    ) -> pd.DataFrame:
        """
        Filter an extracted packet DataFrame by IP addresses, ports, flags, or loss events.
        """
        if df is None or df.empty:
            return df

        filtered = df.copy()

        if source_ip and source_ip.strip():
            filtered = filtered[filtered["source_ip"] == source_ip.strip()]

        if destination_ip and destination_ip.strip():
            filtered = filtered[filtered["destination_ip"] == destination_ip.strip()]

        if source_port is not None and source_port > 0:
            filtered = filtered[filtered["source_port"] == source_port]

        if destination_port is not None and destination_port > 0:
            filtered = filtered[filtered["destination_port"] == destination_port]

        if flag_filter and flag_filter != "All":
            flag_col_map = {
                "SYN": "flag_syn",
                "ACK": "flag_ack",
                "FIN": "flag_fin",
                "RST": "flag_rst",
                "PSH": "flag_psh",
                "URG": "flag_urg",
                "ECE": "flag_ece",
                "CWR": "flag_cwr"
            }
            target_col = flag_col_map.get(flag_filter.upper())
            if target_col and target_col in filtered.columns:
                filtered = filtered[filtered[target_col] == True]

        if retransmissions_only and "is_retransmission" in filtered.columns:
            filtered = filtered[filtered["is_retransmission"] == True]

        if duplicate_acks_only and "is_duplicate_ack" in filtered.columns:
            filtered = filtered[filtered["is_duplicate_ack"] == True]

        return filtered
