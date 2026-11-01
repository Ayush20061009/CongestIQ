"""
TCP Congestion Control Simulator & Network Performance Analysis
==============================================================
Main Application Entry Point — Unified Dashboard.

Phase 8: Complete Integrated Application & Network Analysis Suite.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional
import pandas as pd
import streamlit as st

# Ensure project root is present in sys.path for robust relative imports across pages
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.packet_analysis import PacketAnalysisSummary
from utils.helpers import (
    render_environment_badges,
    render_project_sidebar,
    format_bytes,
    format_bitrate,
    calculate_simulation_metrics,
    build_state_residency_chart,
    build_tcp_flags_chart,
    generate_automatic_performance_insights,
)


def main() -> None:
    st.set_page_config(
        page_title="CongestIQ — TCP Congestion Control & Network Intelligence",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Render persistent project sidebar
    render_project_sidebar()

    # Dashboard Header
    st.title("📊 CongestIQ — Dashboard")
    st.caption("Understand. Simulate. Optimise.")

    # Environment diagnostics
    render_environment_badges()

    st.divider()

    # =========================================================================
    # Session-Based KPI Metrics Row (3 columns)
    # =========================================================================
    latest_sim: Optional[Dict[str, Any]] = st.session_state.get("latest_simulation", None)
    comp_summary: Optional[Dict[str, Any]] = st.session_state.get("comparison_summary", None)
    latest_pkt: Optional[PacketAnalysisSummary] = st.session_state.get("latest_packet_analysis", None)
    sim_df: Optional[pd.DataFrame] = st.session_state.get("simulation_df", None)

    kpi1, kpi2, kpi3 = st.columns(3)

    with kpi1:
        if latest_sim:
            st.metric(
                "Latest Simulation",
                f"TCP {latest_sim['algorithm']}",
                f"Peak CWND: {latest_sim['peak_cwnd']:.1f} MSS"
            )
        else:
            st.metric("Simulation Engine", "0 Runs", "Awaiting Execution")

    with kpi2:
        if comp_summary:
            adv = comp_summary.get("reno_throughput_advantage_percent", 0.0)
            sign = "+" if adv >= 0 else ""
            st.metric("Reno vs Tahoe Delta", f"{sign}{adv:.1f}% Advantage", "Shared Parameter Run")
        else:
            st.metric("Tahoe vs Reno", "Not Compared", "Run Comparison")

    with kpi3:
        if latest_pkt:
            st.metric(
                "Analyzed Capture",
                f"{latest_pkt.total_tcp_packets:,} TCP Pkts",
                f"Loss Rate: {latest_pkt.retransmission_rate:.2f}%"
            )
        else:
            st.metric("Packet Analysis", "0 Captures", "Upload .pcap")

    st.divider()

    # =========================================================================
    # Simulation Performance Section
    # =========================================================================
    st.subheader("📈 Simulation Performance")

    if sim_df is not None and not sim_df.empty and latest_sim:
        sim_metrics = calculate_simulation_metrics(sim_df)

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Final CWND", f"{sim_metrics['final_cwnd']:.1f} MSS")
        m_col2.metric("Peak CWND", f"{sim_metrics['peak_cwnd']:.1f} MSS")
        m_col3.metric("Average CWND", f"{sim_metrics['average_cwnd']:.2f} MSS")
        m_col4.metric("Min CWND", f"{sim_metrics['min_cwnd']:.1f} MSS")

        m_col5, m_col6, m_col7, m_col8 = st.columns(4)
        m_col5.metric("Total Loss Events", sim_metrics["total_loss_events"])
        m_col6.metric("Retransmissions", sim_metrics["total_retransmissions"])
        m_col7.metric("Active Algorithm", f"TCP {latest_sim['algorithm']}")
        m_col8.metric("Final State", sim_metrics["final_state"])

        st.markdown("---")

        col_chart1, col_chart2 = st.columns([1, 1])
        with col_chart1:
            st.plotly_chart(
                build_state_residency_chart(sim_metrics["state_counts"]),
                use_container_width=True
            )

        with col_chart2:
            st.markdown("#### State Distribution & SSTHRESH Progression")
            st.write(f"• **Total RTT Rounds Simulated**: `{sim_metrics['total_rounds']}` rounds")
            st.write(f"• **Initial SSTHRESH**: `{sim_metrics['initial_ssthresh']:.1f} MSS`")
            st.write(f"• **Final SSTHRESH**: `{sim_metrics['final_ssthresh']:.1f} MSS`")
            st.write(f"• **SSTHRESH Reductions Logged**: `{sim_metrics['ssthresh_changes']}` events")
            st.markdown("##### Operating State Breakdown:")
            for state, pct in sim_metrics["state_percentages"].items():
                count = sim_metrics["state_counts"].get(state, 0)
                st.write(f"- **{state}**: {count} rounds ({pct:.1f}%)")

        # Comparative simulation summary table
        if comp_summary:
            st.markdown("---")
            st.markdown("#### ⚖️ Tahoe vs. Reno Comparative Simulation Summary")
            comp_table = [
                {"Metric": "Final Congestion Window", "TCP Tahoe": f"{comp_summary['tahoe_final_cwnd']:.1f} MSS", "TCP Reno": f"{comp_summary['reno_final_cwnd']:.1f} MSS"},
                {"Metric": "Average Congestion Window", "TCP Tahoe": f"{comp_summary['tahoe_average_cwnd']:.2f} MSS", "TCP Reno": f"{comp_summary['reno_average_cwnd']:.2f} MSS"},
                {"Metric": "Peak Congestion Window", "TCP Tahoe": f"{comp_summary['tahoe_peak_cwnd']:.1f} MSS", "TCP Reno": f"{comp_summary['reno_peak_cwnd']:.1f} MSS"},
                {"Metric": "Total Retransmissions", "TCP Tahoe": comp_summary["tahoe_retransmissions"], "TCP Reno": comp_summary["reno_retransmissions"]},
                {"Metric": "Reno Throughput Advantage", "TCP Tahoe": "Baseline", "TCP Reno": f"+{comp_summary['reno_throughput_advantage_percent']:.1f}%"},
            ]
            st.table(pd.DataFrame(comp_table))

    else:
        st.info(
            "ℹ️ **No simulation has been executed in the current session yet.**\n\n"
            "Navigate to **TCP Simulation** or **Algorithm Comparison** to run a simulation. "
            "Results will automatically populate here."
        )
        st.page_link("pages/2_TCP_Simulation.py", label="Run TCP Simulation", icon="📈")
        st.page_link("pages/3_Algorithm_Comparison.py", label="Run Algorithm Comparison", icon="⚖️")

    st.divider()

    # =========================================================================
    # Packet Analysis Section
    # =========================================================================
    st.subheader("🔍 Packet Analysis")

    if latest_pkt and latest_pkt.total_tcp_packets > 0:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Capture Filename", latest_pkt.filename)
        p2.metric("Total Frames", f"{latest_pkt.total_packets:,}")
        p3.metric("TCP Segments", f"{latest_pkt.total_tcp_packets:,}")
        p4.metric("Capture Duration", f"{latest_pkt.duration_seconds:.2f} s")

        p5, p6, p7, p8 = st.columns(4)
        p5.metric("Retransmissions", f"{latest_pkt.retransmission_count:,}", f"{latest_pkt.retransmission_rate:.2f}% rate")
        p6.metric("Duplicate ACKs", f"{latest_pkt.duplicate_ack_count:,}", f"{latest_pkt.duplicate_ack_rate:.2f}% rate")
        p7.metric("SYN Packets", latest_pkt.syn_count)
        p8.metric("FIN / RST Packets", f"{latest_pkt.fin_count} / {latest_pkt.rst_count}")

        st.markdown("---")

        pcol1, pcol2 = st.columns([1, 1])
        with pcol1:
            st.plotly_chart(
                build_tcp_flags_chart(latest_pkt.flag_distribution),
                use_container_width=True
            )

        with pcol2:
            st.markdown("#### Retransmission Classification Breakdown")
            st.write(f"• **Total Retransmissions**: `{latest_pkt.retransmission_count:,}`")
            st.write(f"• **Fast Retransmissions (3-Dup-ACKs)**: `{latest_pkt.fast_retransmission_count:,}`")
            st.write(f"• **Spurious Retransmissions (Late ACK)**: `{latest_pkt.spurious_retransmission_count:,}`")
            st.write(f"• **Out-of-Order Segments**: `{latest_pkt.out_of_order_count:,}`")
            st.info(
                "⚠️ **Engineering Distinction**: Retransmissions on the wire indicate loss recovery actions, "
                "but can also arise from packet reordering or premature timeouts. The sender's internal "
                "Congestion Window (CWND) is maintained inside the host OS kernel and is not present in packet headers."
            )

    else:
        st.info(
            "ℹ️ **No packet capture file has been analyzed yet in the current session.**\n\n"
            "Navigate to **Packet Analysis** and upload a `.pcap` or `.pcapng` capture file "
            "recorded with Wireshark, tcpdump, or similar tools."
        )
        st.page_link("pages/4_Packet_Analysis.py", label="Open Packet Analysis", icon="🔍")

    st.divider()

    # =========================================================================
    # Quick Navigation Cards (3 cards)
    # =========================================================================
    st.subheader("🚀 Quick Navigation")
    nav1, nav2, nav3 = st.columns(3)

    with nav1:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#10b981;">⚙️ TCP Simulation</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    Run discrete RTT simulations of <b>TCP Tahoe</b> and <b>TCP Reno</b>.<br>
                    Inject deterministic loss events and inspect window adjustments round-by-round.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/2_TCP_Simulation.py", label="Launch Simulator", icon="⚙️")

    with nav2:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#f59e0b;">⚖️ Algorithm Comparison</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    Side-by-side <b>Tahoe vs. Reno</b> under identical loss conditions.<br>
                    Quantify Fast Recovery throughput advantage and window divergence.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/3_Algorithm_Comparison.py", label="Compare Algorithms", icon="⚖️")

    with nav3:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#a855f7;">🔍 Packet Analysis</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    Upload and dissect <code>.pcap</code> / <code>.pcapng</code> capture files.<br>
                    Detect retransmissions, duplicate ACKs, and inspect TCP flag distributions.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/4_Packet_Analysis.py", label="Analyze Packet Capture", icon="🔍")


if __name__ == "__main__":
    main()
