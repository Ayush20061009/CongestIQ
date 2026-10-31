"""
TCP Congestion Control Simulator & Network Performance Analysis
==============================================================
Main Application Entry Point.

Phase 8: Complete Integrated Application & Network Analysis Suite.
"""

from __future__ import annotations

import os
import sys
import streamlit as st

# Ensure project root is present in sys.path for robust relative imports across pages
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.helpers import render_environment_badges, render_project_sidebar


def main() -> None:
    st.set_page_config(
        page_title="CongestIQ — TCP Congestion Control & Network Intelligence",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Render persistent project sidebar
    render_project_sidebar()

    # Application Header
    st.markdown(
        """
        <div style="margin-bottom: 0.5rem;">
            <div style="display: flex; gap: 8px; margin-bottom: 0.6rem; flex-wrap: wrap;">
                <span class="tech-badge badge-cyan">CongestIQ Platform</span>
                <span class="tech-badge badge-emerald">RFC 1122 & RFC 5681</span>
                <span class="tech-badge badge-purple">Network Intelligence</span>
                <span class="tech-badge badge-amber">Windows 10 Native</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.title("⚡ CongestIQ")
    st.markdown("### *Understand. Simulate. Optimise.*")
    st.markdown(
        "**TCP Congestion Control & Network Intelligence Platform**\n\n"
        "An interactive educational and experimental engineering suite for exploring TCP congestion "
        "control mechanisms, mathematical window scaling, bottleneck emulation, and deep wire packet analysis."
    )

    st.markdown(
        """
        Welcome to **CongestIQ**. This platform provides a hands-on, mathematically rigorous environment 
        to understand how the Transmission Control Protocol (TCP) regulates data transmission rates, 
        prevents congestion collapse, and recovers from packet loss across simulated and emulated networks.
        """
    )

    st.divider()

    # Core Features & Workflow - 6 Pillars in 2 Rows
    st.subheader("🚀 Platform Features & Capabilities")
    row1_c1, row1_c2, row1_c3 = st.columns(3)

    with row1_c1:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#38bdf8;">📚 1. Learn</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    • <b>TCP Principles</b>: Flow Control vs. Congestion Control.<br>
                    • <b>State Variables</b>: Deep dive into <b>CWND</b> and <b>SSTHRESH</b>.<br>
                    • <b>Algorithmic Phases</b>: Slow Start, Congestion Avoidance, AIMD, Fast Retransmit, and Fast Recovery.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/2_TCP_Concepts.py", label="Explore TCP Concepts", icon="📚")

    with row1_c2:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#10b981;">⚙️ 2. Simulate</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    • <b>Interactive Engine</b>: Run discrete RTT simulations of <b>TCP Tahoe</b> and <b>TCP Reno</b>.<br>
                    • <b>Event Injection</b>: Trigger deterministic <b>3 Duplicate ACKs</b> or <b>Timeouts</b> at specific rounds.<br>
                    • <b>Detailed Traces</b>: Inspect round-by-round window adjustments and state transitions.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/3_Simulation.py", label="Launch Simulator", icon="⚙️")

    with row1_c3:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#f59e0b;">⚖️ 3. Compare</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    • <b>Tahoe vs. Reno</b>: Synchronized execution under identical loss conditions.<br>
                    • <b>Fast Recovery Advantage</b>: Quantify how Reno preserves throughput compared to Tahoe.<br>
                    • <b>Metrics & Tables</b>: Side-by-side comparison of peak CWND, average CWND, and retransmissions.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/4_Algorithm_Comparison.py", label="Compare Algorithms", icon="⚖️")

    row2_c1, row2_c2, row2_c3 = st.columns(3)

    with row2_c1:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#06b6d4;">🌐 4. Emulate</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    • <b>Python Network Emulator</b>: Bottleneck router link with FIFO queueing buffer.<br>
                    • <b>Link Conditioning</b>: Configure bandwidth (Mbps), propagation delay (ms), loss (%), and buffer size.<br>
                    • <b>Simulated Performance</b>: Model packet transmission, queueing delays, and throughput natively on Windows 10.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/5_Network_Experiment.py", label="Run Network Emulation", icon="🌐")

    with row2_c2:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#a855f7;">🔍 5. Dissect</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    • <b>Wire Trace Ingestion</b>: Upload and parse <code>.pcap</code> and <code>.pcapng</code> files via TShark.<br>
                    • <b>Header Extraction</b>: Inspect TCP Sequence, Acknowledgement, and Window headers.<br>
                    • <b>Loss Analysis</b>: Classify retransmissions, duplicate ACKs, and control flags.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/6_Packet_Analysis.py", label="Analyze Packet Capture", icon="🔍")

    with row2_c3:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#38bdf8;">📊 6. Analyze</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                    • <b>Executive KPIs</b>: Unified metrics across simulation, experimentation, and packet analysis.<br>
                    • <b>Automated Insights</b>: Dynamic, data-driven technical evaluations based on real results.<br>
                    • <b>Multi-Run History</b>: Parametric comparison across varying bandwidth, delay, and loss.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/1_Dashboard.py", label="Open Performance Dashboard", icon="📊")

    st.divider()

    # Multipage Directory Grid
    st.subheader("📑 Application Pages Directory")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            - **[1. Dashboard](pages/1_Dashboard.py)**: Executive performance analytics, cross-module KPI overview, and automated insights.
            - **[2. TCP Concepts](pages/2_TCP_Concepts.py)**: Comprehensive educational theory guide with formulas and comparison tables.
            - **[3. Simulation](pages/3_Simulation.py)**: Core interactive simulator for TCP Tahoe and Reno with full parameter controls.
            """
        )

    with c2:
        st.markdown(
            """
            - **[4. Algorithm Comparison](pages/4_Algorithm_Comparison.py)**: Side-by-side comparative analysis of Tahoe vs Reno under synchronized loss.
            - **[5. Network Experiment](pages/5_Network_Experiment.py)**: Virtual network emulation with Mininet, `tc/netem`, and iPerf3.
            - **[6. Packet Analysis](pages/6_Packet_Analysis.py)**: Wire packet dissection, retransmission detection, and TCP flag distribution.
            """
        )

    st.divider()

    # System Status & Diagnostics
    st.subheader("🖥️ Host System & Capability Diagnostics")
    render_environment_badges()


if __name__ == "__main__":
    main()
