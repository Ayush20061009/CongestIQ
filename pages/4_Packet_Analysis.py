"""
Packet Analysis Page — Phase 6
==============================
Deep inspection of PCAP and PCAPNG packet captures using Wireshark / TShark.
Provides header extraction, retransmission classification, duplicate ACK tracing,
TCP flag distribution, and packet-level congestion dynamics analysis.
"""

from __future__ import annotations

import os
import sys
import tempfile
import pandas as pd
import streamlit as st

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from core.packet_analysis import (
    PacketAnalyzer,
    PacketAnalysisSummary,
    validate_capture_file,
    MAX_CAPTURE_FILE_SIZE
)
from utils.helpers import (
    render_project_sidebar,
    is_tshark_available,
    get_tshark_path,
    format_bytes,
    build_tcp_flags_chart,
    build_packet_timeline_chart,
    build_retransmission_timeline_chart,
    build_seq_timeline_chart
)


def render_tshark_instructions() -> None:
    """Render comprehensive installation instructions for TShark across platforms."""
    st.warning(
        "⚠️ **TShark CLI Not Detected on Host System**\n\n"
        "Wireshark / TShark is required to execute deep packet header extraction. "
        "The application remains fully functional, and files will be verified for valid PCAP/PCAPNG headers. "
        "Follow the instructions below to install TShark on your machine."
    )

    t1, t2 = st.tabs(["🪟 Windows Setup", "🐧 Linux / Ubuntu Setup"])

    with t1:
        st.markdown(
            r"""
            #### Installing TShark on Windows
            1. Download the official installer from [Wireshark.org](https://www.wireshark.org/download.html).
            2. Run the installer and ensure the following components are selected:
               - **Wireshark** & **TShark**
               - **Npcap** packet capture driver
            3. By default, TShark installs to:
               `C:\Program Files\Wireshark\tshark.exe`
            4. *(Recommended)* Add `C:\Program Files\Wireshark` to your Windows System `PATH` environment variable:
               - Press `Win + R`, type `sysdm.cpl`, hit Enter.
               - Go to **Advanced** > **Environment Variables**.
               - Under System Variables, select **Path** > **Edit** > **New** > `C:\Program Files\Wireshark`.
            5. Restart your terminal or Streamlit application.
            """
        )

    with t2:
        st.markdown(
            """
            #### Installing TShark on Linux / Ubuntu / WSL2
            1. Update packages and install TShark via `apt`:
               ```bash
               sudo apt update
               sudo apt install -y tshark
               ```
            2. Allow non-root packet dissection:
               ```bash
               sudo dpkg-reconfigure wireshark-common
               sudo usermod -aG wireshark $USER
               ```
            3. Verify installation:
               ```bash
               which tshark
               tshark --version
               ```
            4. Launch Streamlit:
               ```bash
               streamlit run app.py
               ```
            """
        )


def main() -> None:
    st.set_page_config(page_title="CongestIQ | Packet Dissection", page_icon="⚡", layout="wide")
    render_project_sidebar()

    st.title("🔍 CongestIQ — Packet Dissection & Wire Analysis")
    st.caption("Understand. Simulate. Optimise. • Automated PCAP / PCAPNG Dissection, Retransmission Detection & Flag Analysis")

    st.markdown(
        """
        Analyze live or recorded network traffic captured using **Wireshark**, **tcpdump**, or **Mininet experiments**.
        Inspect TCP sequence numbers, observe acknowledgements, detect retransmissions, trace duplicate ACKs,
        and assess packet-level congestion dynamics.
        """
    )

    # Scientific Data Integrity Notice
    st.info(
        "🔬 **Data Integrity Standard**: In accordance with our scientific methodology, this module only "
        "analyzes **real uploaded packet capture data**. No dummy or fabricated packet records are generated. "
        "Packet analysis observes traffic as transmitted on the wire; the sender's internal Congestion Window ($CWND$) "
        "is managed inside the operating system kernel and cannot be directly extracted from packet headers unless explicitly measured."
    )

    st.divider()

    # Pre-flight Tool Status
    tshark_present = is_tshark_available()
    tshark_path = get_tshark_path()

    col_stat1, col_stat2 = st.columns([2, 1])
    with col_stat1:
        if tshark_present:
            st.success(f"✅ **TShark Dissection Engine Available**: `{tshark_path}`")
        else:
            render_tshark_instructions()

    with col_stat2:
        st.markdown(
            """
            **Supported Capture Formats**:
            - `.pcap`: Standard libpcap trace format
            - `.pcapng`: Wireshark Next Generation format
            
            **Maximum File Size**: 50 MB
            """
        )

    st.divider()

    # File Ingestion Section
    st.header("1. Upload Packet Capture File")
    uploaded_file = st.file_uploader(
        "Upload a .pcap or .pcapng network capture file",
        type=["pcap", "pcapng"],
        help="Upload a capture file recorded via Wireshark or tcpdump."
    )

    summary: Optional[PacketAnalysisSummary] = None

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_size = len(file_bytes)
        file_name = uploaded_file.name

        st.write(f"📁 **File Received**: `{file_name}` ({format_bytes(file_size)})")

        if file_size == 0:
            st.error("❌ The uploaded capture file is empty (0 bytes). Please upload a valid capture file.")
            return

        if file_size > MAX_CAPTURE_FILE_SIZE:
            st.error(f"❌ File exceeds the 50 MB size limit ({format_bytes(file_size)}). Please upload a smaller capture.")
            return

        # Check header magic bytes safely
        _, ext = os.path.splitext(file_name)
        temp_file_path: Optional[str] = None

        try:
            # Write to a secure temporary file for processing
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(file_bytes)
                temp_file_path = tmp.name

            # Pre-validate file format and magic bytes
            validate_capture_file(temp_file_path)
            st.success("✅ Capture file format and header magic bytes verified.")

            if not tshark_present:
                st.warning(
                    "⚠️ Capture file is valid, but TShark CLI is required on this host to extract packet headers. "
                    "Please install Wireshark / TShark using the instructions above to view packet details."
                )
            else:
                with st.spinner("Dissecting TCP packets with TShark..."):
                    analyzer = PacketAnalyzer(temp_file_path, tshark_path=tshark_path)
                    summary = analyzer.analyze()
                    st.session_state["latest_packet_analysis"] = summary
                    st.success(f"✅ Extracted **{summary.total_tcp_packets:,}** TCP packets successfully!")

        except ValueError as ve:
            st.error(f"❌ **Validation Error**: {ve}")
            return
        except EnvironmentError as ee:
            st.error(f"❌ **Environment Error**: {ee}")
            return
        except TimeoutError as te:
            st.error(f"⏱️ **Timeout Error**: {te}")
            return
        except Exception as ex:
            st.error(f"❌ **Processing Error**: {ex}")
            return
        finally:
            # Strictly clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass

    # Retrieve from session state if available and not re-analyzed
    if summary is None and "latest_packet_analysis" in st.session_state:
        summary = st.session_state["latest_packet_analysis"]

    if summary is None:
        st.info("💡 Upload a `.pcap` or `.pcapng` capture file above to begin packet analysis.")
        return

    st.divider()

    # A. Capture Information
    st.header("2. Capture Information")
    ci1, ci2, ci3, ci4, ci5 = st.columns(5)
    ci1.metric("Filename", summary.filename)
    ci2.metric("File Size", format_bytes(summary.file_size_bytes))
    ci3.metric("Total Frames", f"{summary.total_packets:,}")
    ci4.metric("TCP Segments", f"{summary.total_tcp_packets:,}")
    ci5.metric("Capture Duration", f"{summary.duration_seconds:.2f} s")

    st.divider()

    # B. TCP Packet Summary Cards
    st.header("3. TCP Traffic & Loss Summary")
    sb1, sb2, sb3, sb4, sb5, sb6 = st.columns(6)
    sb1.metric("Total TCP Packets", f"{summary.total_tcp_packets:,}")
    sb2.metric("Retransmissions", f"{summary.retransmission_count:,}", f"{summary.retransmission_rate:.2f}% rate")
    sb3.metric("Duplicate ACKs", f"{summary.duplicate_ack_count:,}", f"{summary.duplicate_ack_rate:.2f}% rate")
    sb4.metric("SYN Packets", f"{summary.syn_count:,}")
    sb5.metric("FIN Packets", f"{summary.fin_count:,}")
    sb6.metric("RST Packets", f"{summary.rst_count:,}")

    df = summary.to_dataframe()

    if df.empty:
        st.warning("⚠️ No TCP packets were found in the uploaded capture file.")
        return

    st.divider()

    # Main Analysis Tabs
    tab_packets, tab_retrans, tab_dupacks, tab_flags, tab_visuals, tab_edu = st.tabs([
        "📋 Packet Table & Inspection",
        "🔄 Retransmission Analysis",
        "⚡ Duplicate ACK Analysis",
        "🚩 TCP Flags Distribution",
        "📈 Interactive Visualisations",
        "🎓 Educational Insights"
    ])

    # TAB 1: Packet Table & Inspection (Section C & Filtering)
    with tab_packets:
        st.subheader("Extracted TCP Packets Table")
        st.markdown("Filter and inspect individual packet records extracted from the capture.")

        # Filter controls
        with st.expander("🔍 Filter Packets", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns(4)
            src_ips = ["All"] + sorted(list(df["source_ip"].dropna().unique()))
            dst_ips = ["All"] + sorted(list(df["destination_ip"].dropna().unique()))

            selected_src_ip = fc1.selectbox("Source IP", src_ips)
            selected_dst_ip = fc2.selectbox("Destination IP", dst_ips)
            selected_flag = fc3.selectbox("TCP Flag", ["All", "SYN", "ACK", "FIN", "RST", "PSH", "ECE", "CWR"])

            show_retrans_only = fc4.checkbox("Retransmissions Only", value=False)
            show_dupacks_only = fc4.checkbox("Duplicate ACKs Only", value=False)

        # Apply filtering
        filtered_df = PacketAnalyzer.filter_dataframe(
            df,
            source_ip=None if selected_src_ip == "All" else selected_src_ip,
            destination_ip=None if selected_dst_ip == "All" else selected_dst_ip,
            flag_filter=selected_flag,
            retransmissions_only=show_retrans_only,
            duplicate_acks_only=show_dupacks_only
        )

        st.caption(f"Displaying **{len(filtered_df):,}** of **{len(df):,}** packets.")

        display_cols = [
            "packet_id", "timestamp", "source_ip", "source_port",
            "destination_ip", "destination_port", "seq_number", "ack_number",
            "tcp_flags", "window_size", "payload_len", "is_retransmission", "is_duplicate_ack"
        ]
        available_display_cols = [c for c in display_cols if c in filtered_df.columns]
        st.dataframe(filtered_df[available_display_cols], use_container_width=True, height=350)

        # Packet Inspector
        st.subheader("🔬 Single Packet Inspector")
        if not filtered_df.empty:
            pkt_ids = filtered_df["packet_id"].tolist()
            selected_pkt_id = st.selectbox("Select Packet ID to Inspect", pkt_ids[:500])
            pkt_match = filtered_df[filtered_df["packet_id"] == selected_pkt_id]

            if not pkt_match.empty:
                pkt = pkt_match.iloc[0]
                pi1, pi2, pi3 = st.columns(3)
                with pi1:
                    st.markdown("**Endpoint Identification**")
                    st.write(f"• **Frame ID**: {pkt['packet_id']}")
                    st.write(f"• **Timestamp**: {pkt['timestamp']:.6f} s")
                    st.write(f"• **Source**: `{pkt['source_ip']}:{pkt['source_port']}`")
                    st.write(f"• **Destination**: `{pkt['destination_ip']}:{pkt['destination_port']}`")
                with pi2:
                    st.markdown("**TCP Header Sequence Info**")
                    st.write(f"• **Sequence Number**: `{pkt['seq_number']:,}`")
                    st.write(f"• **Acknowledgement Number**: `{pkt['ack_number']:,}`")
                    st.write(f"• **Payload Length**: {pkt['payload_len']} bytes")
                    st.write(f"• **Advertised Window**: {pkt['window_size']:,} bytes")
                with pi3:
                    st.markdown("**Congestion & Analysis Status**")
                    st.write(f"• **Active Flags**: `{pkt['tcp_flags']}`")
                    st.write(f"• **Retransmission**: {'🔴 Yes' if pkt['is_retransmission'] else '🟢 No'}")
                    st.write(f"• **Duplicate ACK**: {'🟠 Yes' if pkt['is_duplicate_ack'] else '🟢 No'}")
                    if pkt.get("rtt_sec") is not None and pd.notna(pkt["rtt_sec"]):
                        st.write(f"• **Measured RTT**: {pkt['rtt_sec']*1000:.2f} ms")

    # TAB 2: Retransmission Analysis (Section D)
    with tab_retrans:
        st.subheader("Retransmission Breakdown & Engineering Context")

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Total Retransmissions", f"{summary.retransmission_count:,}")
        rc2.metric("Fast Retransmissions", f"{summary.fast_retransmission_count:,}")
        rc3.metric("Spurious Retransmissions", f"{summary.spurious_retransmission_count:,}")
        rc4.metric("Out-of-Order Segments", f"{summary.out_of_order_count:,}")

        st.markdown(
            r"""
            $$\text{Retransmission Rate} = \frac{\text{Total Retransmissions}}{\text{Total TCP Packets}} \times 100\% 
            = \frac{""" + f"{summary.retransmission_count:,}" + r"""}{""" + f"{summary.total_tcp_packets:,}" + r"""} \times 100\% 
            = """ + f"{summary.retransmission_rate:.2f}\\%" + r"""$$
            """
        )

        st.info(
            "⚠️ **Engineering Distinction**: Do not automatically classify every retransmission as network congestion loss. "
            "Retransmissions in production TCP traffic occur due to three distinct phenomena:\n\n"
            "1. **True Congestion Drop**: An intermediate router buffer overflowed, causing tail drop. Detected by 3-Dup-ACKs or RTO.\n"
            "2. **Packet Reordering**: Segments take asymmetric routing paths; late segments arrive intact after a retransmission.\n"
            "3. **Spurious Timeout**: The sender's RTO timer fired prematurely before an ACK delayed by bufferbloat could arrive."
        )

        retrans_df = df[df["is_retransmission"]]
        if not retrans_df.empty:
            st.write("#### Detected Retransmission Events")
            st.dataframe(
                retrans_df[[
                    "packet_id", "timestamp", "source_ip", "source_port",
                    "destination_ip", "destination_port", "seq_number", "payload_len",
                    "is_fast_retransmission", "is_spurious_retransmission"
                ]],
                use_container_width=True
            )
        else:
            st.success("🟢 No TCP retransmission events were detected in this capture file.")

    # TAB 3: Duplicate ACK Analysis (Section E)
    with tab_dupacks:
        st.subheader("Duplicate Acknowledgement Dynamics")

        da1, da2 = st.columns(2)
        da1.metric("Total Duplicate ACKs", f"{summary.duplicate_ack_count:,}")
        da2.metric("Duplicate ACK Frequency", f"{summary.duplicate_ack_rate:.2f}%")

        st.markdown(
            r"""
            #### Fast Retransmit Trigger (3 Duplicate ACKs Rule)
            In standard TCP (RFC 2001 / RFC 5681):
            - When an out-of-order segment arrives at the receiver, the receiver immediately generates an ACK repeating the expected sequence number.
            - **1st & 2nd Duplicate ACKs**: May indicate minor packet reordering along multipath routes. The sender takes no corrective action.
            - **3rd Duplicate ACK**: Serves as a strong heuristic that the segment was dropped rather than delayed.
            - **Tahoe Reaction**: Sets $SSTHRESH \leftarrow \max(\lfloor CWND/2 \rfloor, 2)$, resets $CWND \leftarrow 1\text{ MSS}$, and enters Slow Start.
            - **Reno Reaction**: Sets $SSTHRESH \leftarrow \max(\lfloor CWND/2 \rfloor, 2)$, retransmits the missing packet immediately (**Fast Retransmit**), inflates $CWND \leftarrow SSTHRESH + 3\text{ MSS}$, and enters **Fast Recovery**.
            """
        )

        dup_df = df[df["is_duplicate_ack"]]
        if not dup_df.empty:
            st.write("#### Detected Duplicate ACK Packets")
            st.dataframe(
                dup_df[[
                    "packet_id", "timestamp", "source_ip", "source_port",
                    "destination_ip", "destination_port", "ack_number", "duplicate_ack_num"
                ]],
                use_container_width=True
            )
        else:
            st.success("🟢 No duplicate ACK events were detected in this capture.")

    # TAB 4: TCP Flags Distribution (Section F)
    with tab_flags:
        st.subheader("TCP Control Flags Breakdown")

        flag_counts = summary.flag_distribution
        st.plotly_chart(build_tcp_flags_chart(flag_counts), use_container_width=True)

        st.markdown("#### TCP Header Flag Reference & Role in Protocol Operation")
        flags_info = [
            {"Flag": "SYN (Synchronize)", "Occurrences": flag_counts.get("SYN", 0), "Role": "Establishes connection state during 3-way handshake; exchanges Initial Sequence Numbers (ISN)."},
            {"Flag": "ACK (Acknowledge)", "Occurrences": flag_counts.get("ACK", 0), "Role": "Acknowledges received bytes; drives the ACK clock that triggers CWND expansion."},
            {"Flag": "FIN (Finish)", "Occurrences": flag_counts.get("FIN", 0), "Role": "Graceful connection termination indicating the sender has finished transmitting data."},
            {"Flag": "RST (Reset)", "Occurrences": flag_counts.get("RST", 0), "Role": "Immediate abortive teardown of connection; indicates rejected port or unrecoverable error."},
            {"Flag": "PSH (Push)", "Occurrences": flag_counts.get("PSH", 0), "Role": "Instructs receiver to push buffered bytes to the application without waiting for buffer to fill."},
            {"Flag": "URG (Urgent)", "Occurrences": flag_counts.get("URG", 0), "Role": "Indicates that urgent pointer field contains high-priority out-of-band data."},
            {"Flag": "ECE (ECN-Echo)", "Occurrences": flag_counts.get("ECE", 0), "Role": "Explicit Congestion Notification: Receiver echoes router-marked congestion signal (RFC 3168)."},
            {"Flag": "CWR (Window Reduced)", "Occurrences": flag_counts.get("CWR", 0), "Role": "Congestion Window Reduced: Sender acknowledges receipt of ECE and throttles CWND."}
        ]
        st.table(pd.DataFrame(flags_info))

    # TAB 5: Interactive Visualisations (Section 11)
    with tab_visuals:
        st.subheader("Packet Capture Time-Series Graphs")

        # 1. Packet Density Timeline
        st.plotly_chart(build_packet_timeline_chart(df), use_container_width=True)

        # 2. Retransmissions & Duplicate ACKs Timeline
        st.plotly_chart(build_retransmission_timeline_chart(df), use_container_width=True)

        # 3. Time-Sequence (tcptrace) Graph
        st.plotly_chart(build_seq_timeline_chart(df), use_container_width=True)

    # TAB 6: Educational Insights (Section G)
    with tab_edu:
        st.subheader("Educational Diagnosis of Captured Trace")

        st.markdown("### Findings from Uploaded Capture Analysis")

        # Dynamic findings based on actual metrics
        findings = []

        if summary.total_tcp_packets > 0:
            findings.append(f"• **Traffic Volume**: Dissected **{summary.total_tcp_packets:,}** TCP packets spanning **{summary.duration_seconds:.2f} seconds**.")

        if summary.retransmission_rate == 0.0:
            findings.append("• **Zero Packet Loss**: No retransmissions were observed. The TCP connection operated smoothly in Congestion Avoidance with optimal throughput.")
        elif summary.retransmission_rate < 2.0:
            findings.append(f"• **Mild Packet Loss ({summary.retransmission_rate:.2f}%)**: Low retransmission rate consistent with occasional queue drops or minor path latency variance.")
        else:
            findings.append(f"• **Severe Congestion Loss ({summary.retransmission_rate:.2f}%)**: Elevated retransmission rate indicates bottleneck link saturation. Under AIMD, each loss event halves the transmission rate.")

        if summary.duplicate_ack_count > 0:
            findings.append(f"• **Duplicate ACKs ({summary.duplicate_ack_count:,} events)**: The receiver observed sequence number gaps. If 3 consecutive duplicate ACKs occurred, TCP Reno triggered Fast Retransmit.")
        else:
            findings.append("• **Sequential Delivery**: ACKs progressed monotonically without duplicate ACK sequences, indicating in-order delivery.")

        for f in findings:
            st.markdown(f)

        st.markdown("---")
        st.markdown(
            r"""
            ### Relationship to Congestion Control Theory
            1. **Window Flow vs. Congestion**:
               - The `window_size` field indicates the receiver's available buffer space ($RWND$).
               - True flow constraint is given by:
                 $$\text{Allowed In-Flight Data} = \min(CWND, RWND)$$
            2. **ACK Clocking**:
               - In Congestion Avoidance, each non-duplicate ACK advances the window by approximately $1 / CWND$, totaling $+1\text{ MSS}$ per RTT.
            3. **Retransmission Penalty**:
               - A single retransmission timeout (RTO) freezes transmission for at least $1.0\text{ second}$, resets $CWND \leftarrow 1\text{ MSS}$, and forces Slow Start recovery.
            """
        )


if __name__ == "__main__":
    main()
