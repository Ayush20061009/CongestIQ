"""
Integrated Performance Dashboard — Phase 7
===========================================
Holistic performance analytics and executive overview integrating results from:
1. TCP Tahoe and Reno discrete-event simulation engine.
2. Mininet virtual network experiments and iPerf3 traffic generation.
3. Wireshark / TShark packet capture dissection.

Maintains strict scientific data integrity across all components without
substituting simulated models for empirical measurements.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from core.network_simulation import (
    ExperimentResult,
    load_experiment_history
)
from core.packet_analysis import PacketAnalysisSummary
from utils.helpers import (
    render_project_sidebar,
    render_environment_badges,
    format_bytes,
    format_bitrate,
    calculate_simulation_metrics,
    build_state_residency_chart,
    build_multi_experiment_chart,
    build_tcp_flags_chart,
    generate_automatic_performance_insights
)


def main() -> None:
    st.set_page_config(
        page_title="CongestIQ | Executive Dashboard",
        page_icon="⚡",
        layout="wide"
    )

    # Render global sidebar
    render_project_sidebar()

    st.title("📊 CongestIQ Executive Dashboard")
    st.caption("Understand. Simulate. Optimise. • Unified Performance Analytics Across Simulation, Network Emulation & Packet Captures")

    # Environmental Health & Tool Availability
    render_environment_badges()

    st.divider()

    # Retrieve data from session state & disk persistence
    sim_df: Optional[pd.DataFrame] = st.session_state.get("simulation_df", None)
    latest_sim: Optional[Dict[str, Any]] = st.session_state.get("latest_simulation", None)
    comp_summary: Optional[Dict[str, Any]] = st.session_state.get("comparison_summary", None)
    latest_exp: Optional[ExperimentResult] = st.session_state.get("latest_experiment_result", None)

    # Load experiment history from disk if not already in session state
    history_file = os.path.join(PARENT_DIR, "data", "experiment_history.json")
    if "experiment_history" not in st.session_state:
        st.session_state["experiment_history"] = load_experiment_history(history_file)
    exp_history: List[ExperimentResult] = st.session_state.get("experiment_history", [])

    latest_pkt: Optional[PacketAnalysisSummary] = st.session_state.get("latest_packet_analysis", None)

    # Calculate detailed simulation metrics if DataFrame is available
    sim_metrics: Dict[str, Any] = calculate_simulation_metrics(sim_df) if sim_df is not None else {}

    # 1. Executive Cross-Component KPI Overview
    st.header("1. Executive Cross-Component Status")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

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
        if latest_exp and latest_exp.status == "Completed":
            st.metric(
                "Emulation Throughput (Sim)",
                f"{latest_exp.measured_throughput_mbps:.2f} Mbps",
                f"Link: {latest_exp.configured_bandwidth_mbps:.1f} Mbps"
            )
        else:
            st.metric("Network Emulation", "0 Completed", "Run Emulation")

    with kpi4:
        if latest_pkt:
            st.metric(
                "Analyzed Capture",
                f"{latest_pkt.total_tcp_packets:,} TCP Pkts",
                f"Loss Rate: {latest_pkt.retransmission_rate:.2f}%"
            )
        else:
            st.metric("Packet Analysis", "0 Captures", "Upload .pcap")

    st.divider()

    # 2. Structured Drill-Down Tabs
    tab_sim, tab_exp, tab_pkt, tab_synthesis = st.tabs([
        "📈 Simulation Performance Analytics",
        "🌐 Network Emulation Analytics (Simulated)",
        "🔍 Packet Capture Analysis Analytics",
        "⚖️ Cross-Module Performance Synthesis & Insights"
    ])

    # =========================================================================
    # TAB 1: Simulation Performance Analytics (Section A)
    # =========================================================================
    with tab_sim:
        st.subheader("A. Discrete-Event Simulation Performance (TCP Tahoe & Reno)")
        st.markdown(
            "Analyzes mathematical window scaling, state residency, and loss recovery characteristics "
            "generated by the educational discrete-event simulation engine (`core/congestion_control.py`)."
        )

        if latest_sim and sim_df is not None and not sim_df.empty:
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Active Algorithm", f"TCP {latest_sim['algorithm']}")
            m_col2.metric("Final CWND", f"{sim_metrics['final_cwnd']:.1f} MSS")
            m_col3.metric("Peak CWND", f"{sim_metrics['peak_cwnd']:.1f} MSS")
            m_col4.metric("Average CWND", f"{sim_metrics['average_cwnd']:.2f} MSS")

            m_col5, m_col6, m_col7, m_col8 = st.columns(4)
            m_col5.metric("Minimum CWND", f"{sim_metrics['min_cwnd']:.1f} MSS")
            m_col6.metric("Total Loss Events", sim_metrics["total_loss_events"])
            m_col7.metric("Retransmissions", sim_metrics["total_retransmissions"])
            m_col8.metric("Final TCP State", sim_metrics["final_state"])

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

            # Comparative Simulation Preview if Available
            if comp_summary:
                st.markdown("---")
                st.markdown("#### ⚖️ Tahoe vs. Reno Comparative Simulation Summary")
                st.markdown(
                    "Both algorithms were executed simultaneously under identical initial windows and loss conditions:"
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Tahoe Final CWND", f"{comp_summary['tahoe_final_cwnd']:.1f} MSS")
                c2.metric("Reno Final CWND", f"{comp_summary['reno_final_cwnd']:.1f} MSS")
                c3.metric("Tahoe Average CWND", f"{comp_summary['tahoe_average_cwnd']:.2f} MSS")
                c4.metric("Reno Average CWND", f"{comp_summary['reno_average_cwnd']:.2f} MSS")

                comp_table = [
                    {"Metric": "Final Congestion Window", "TCP Tahoe": f"{comp_summary['tahoe_final_cwnd']:.1f} MSS", "TCP Reno": f"{comp_summary['reno_final_cwnd']:.1f} MSS"},
                    {"Metric": "Average Congestion Window", "TCP Tahoe": f"{comp_summary['tahoe_average_cwnd']:.2f} MSS", "TCP Reno": f"{comp_summary['reno_average_cwnd']:.2f} MSS"},
                    {"Metric": "Peak Congestion Window", "TCP Tahoe": f"{comp_summary['tahoe_peak_cwnd']:.1f} MSS", "TCP Reno": f"{comp_summary['reno_peak_cwnd']:.1f} MSS"},
                    {"Metric": "Total Retransmissions", "TCP Tahoe": comp_summary["tahoe_retransmissions"], "TCP Reno": comp_summary["reno_retransmissions"]},
                    {"Metric": "Reno Throughput Advantage", "TCP Tahoe": "Baseline", "TCP Reno": f"+{comp_summary['reno_throughput_advantage_percent']:.1f}%"}
                ]
                st.table(pd.DataFrame(comp_table))

        else:
            st.info(
                "ℹ️ **No simulation has been executed in the current session yet.**\n\n"
                "To generate simulation performance analytics, navigate to **[3. Simulation](pages/3_Simulation.py)** "
                "or **[4. Algorithm Comparison](pages/4_Algorithm_Comparison.py)**, configure your parameters, "
                "and run a test. Real mathematical time-series metrics will be automatically integrated here."
            )
            st.page_link("pages/3_Simulation.py", label="Run Single Algorithm Simulation", icon="📈")
            st.page_link("pages/4_Algorithm_Comparison.py", label="Run Tahoe vs. Reno Comparison", icon="⚖️")

    # =========================================================================
    # TAB 2: Network Emulation Analytics (Section B)
    # =========================================================================
    with tab_exp:
        st.subheader("B. Network Emulation Analytics (Simulated Bottleneck Link)")
        st.markdown(
            "Analyzes simulated network performance measurements gathered from the Python network emulation engine "
            "(`core/network_simulation.py`). All results reflect simulated packet queueing, delay, and TCP transmission."
        )

        if latest_exp and latest_exp.status == "Completed":
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Measured Throughput", f"{latest_exp.measured_throughput_mbps:.2f} Mbps")
            e2.metric("Configured Bottleneck", f"{latest_exp.configured_bandwidth_mbps:.1f} Mbps")
            eff = (latest_exp.measured_throughput_mbps / latest_exp.configured_bandwidth_mbps * 100.0) if latest_exp.configured_bandwidth_mbps > 0 else 0.0
            e3.metric("Throughput Efficiency", f"{eff:.1f}%")
            e4.metric("Data Transferred", f"{latest_exp.transfer_amount_mb:.2f} MB")

            e5, e6, e7, e8 = st.columns(4)
            e5.metric("Sender Retransmissions", latest_exp.measured_retransmissions)
            rtt_val = f"{latest_exp.measured_rtt_ms:.2f} ms" if latest_exp.measured_rtt_ms is not None else "N/A"
            e6.metric("Measured Mean RTT", rtt_val)
            e7.metric("Configured Delay", f"{latest_exp.configured_delay_ms:.1f} ms")
            e8.metric("Configured Loss Rate", f"{latest_exp.configured_loss_percentage:.1f}%")

            st.markdown("---")

            # Multi-Run Experiment History
            st.markdown("#### 📊 Multi-Experiment Historical Analysis")
            if exp_history:
                history_df = pd.concat([res.to_dataframe() for res in exp_history], ignore_index=True)
                st.dataframe(
                    history_df[[
                        "Experiment_ID", "Algorithm", "Configured_Bandwidth_Mbps",
                        "Measured_Throughput_Mbps", "Throughput_Efficiency_Pct",
                        "Configured_Delay_Ms", "Configured_Loss_Pct",
                        "Retransmissions", "Duration_Sec"
                    ]],
                    use_container_width=True
                )

                if len(exp_history) >= 2:
                    st.markdown("##### Parametric Sensitivity Visualisation:")
                    chart_col = st.selectbox(
                        "Select Independent Variable for Comparison",
                        options=["Configured_Bandwidth_Mbps", "Configured_Delay_Ms", "Configured_Loss_Pct"],
                        format_func=lambda x: {
                            "Configured_Bandwidth_Mbps": "Configured Bandwidth (Mbps)",
                            "Configured_Delay_Ms": "Configured Delay (ms)",
                            "Configured_Loss_Pct": "Configured Packet Loss (%)"
                        }.get(x, x)
                    )
                    titles = {
                        "Configured_Bandwidth_Mbps": "Throughput vs. Link Capacity",
                        "Configured_Delay_Ms": "Throughput vs. Propagation Delay",
                        "Configured_Loss_Pct": "Throughput vs. Packet Loss Percentage"
                    }
                    st.plotly_chart(
                        build_multi_experiment_chart(history_df, chart_col, chart_col.replace("_", " "), titles[chart_col]),
                        use_container_width=True
                    )
                else:
                    st.caption("ℹ️ Execute at least 2 experiments with different settings in Page 5 to view comparative parametric charts.")

        else:
            st.info(
                "ℹ️ **No network emulation simulation has been executed in the current session yet.**\n\n"
                "To simulate bottleneck bandwidth, propagation delay, packet loss, and router buffer queueing, "
                "navigate to **[5. Network Experiment](pages/5_Network_Experiment.py)**.\n\n"
                "*Note: All network emulation metrics are produced by the native Python simulation engine on Windows 10.*"
            )
            st.page_link("pages/5_Network_Experiment.py", label="Open Network Emulation Page", icon="🌐")

    # =========================================================================
    # TAB 3: Packet Analysis Analytics (Section C)
    # =========================================================================
    with tab_pkt:
        st.subheader("C. Wire Packet Capture Analytics (Wireshark & TShark)")
        st.markdown(
            "Analyzes packet header fields, retransmission events, duplicate ACKs, and control flags "
            "extracted from uploaded `.pcap` or `.pcapng` network trace files (`core/packet_analysis.py`)."
        )

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
                    "Congestion Window ($CWND$) is maintained inside the host OS kernel and is not present in packet headers."
                )

        else:
            st.info(
                "ℹ️ **No packet capture file has been analyzed yet in the current session.**\n\n"
                "To analyze real packet-level traffic, navigate to **[6. Packet Analysis](pages/6_Packet_Analysis.py)** "
                "and upload a `.pcap` or `.pcapng` capture file recorded with Wireshark, tcpdump, or Mininet."
            )
            st.page_link("pages/6_Packet_Analysis.py", label="Open Packet Analysis Page", icon="🔍")

    # =========================================================================
    # TAB 4: Cross-Module Performance Synthesis & Insights
    # =========================================================================
    with tab_synthesis:
        st.subheader("⚖️ Cross-Module Performance Synthesis & Data-Driven Insights")
        st.markdown(
            "Synthesizes theoretical models, kernel network measurements, and wire capture observations "
            "while maintaining strict separation of concerns."
        )

        # Dynamic, Data-Driven Performance Insights
        insights = generate_automatic_performance_insights(
            sim_metrics=sim_metrics if latest_sim else None,
            comp_summary=comp_summary,
            exp_result=latest_exp,
            pkt_summary=latest_pkt
        )

        st.markdown("### 💡 Automated Dynamic Performance Insights")
        if insights:
            for item in insights:
                with st.expander(f"📌 [{item['category']}] {item['title']}", expanded=True):
                    st.write(item["body"])
        else:
            st.info("Execute a simulation, experiment, or packet analysis to generate dynamic, automated insights.")

        st.markdown("---")

        # Scientific Segregation & Methodology Matrix
        st.markdown("### 🔬 Scientific Data Segregation & Methodological Comparison")
        st.markdown(
            "A critical educational goal of this project is understanding the boundary between theoretical modeling, "
            "emulated kernel networking, and passive wire dissection:"
        )

        comparison_matrix = [
            {
                "Dimension": "Primary Data Source",
                "Educational Algorithm Model": "Discrete round-based RFC models in Python",
                "Python Network Emulation": "Simulated bottleneck link with buffer queueing (Python)",
                "Wireshark / TShark Analysis": "Passive wire capture (.pcap / .pcapng)"
            },
            {
                "Dimension": "CWND Visibility",
                "Educational Algorithm Model": "Exact algorithmic variable in MSS units",
                "Python Network Emulation": "Explicitly simulated sender CWND variable",
                "Wireshark / TShark Analysis": "Hidden inside OS kernel (not in packet headers)"
            },
            {
                "Dimension": "Time Granularity",
                "Educational Algorithm Model": "Discrete RTT rounds (Round 1, 2, ..., N)",
                "Python Network Emulation": "Continuous simulation timeline (seconds / RTT)",
                "Wireshark / TShark Analysis": "Microsecond / Nanosecond packet arrival timestamps"
            },
            {
                "Dimension": "Congestion Signals",
                "Educational Algorithm Model": "Deterministic loss triggers & random events",
                "Python Network Emulation": "Router buffer overflow (tail drops) & link loss",
                "Wireshark / TShark Analysis": "Observed Duplicate ACKs & sequence number gaps"
            },
            {
                "Dimension": "Primary Objective",
                "Educational Algorithm Model": "Algorithm mechanics & state transitions",
                "Python Network Emulation": "Link bandwidth, queueing delay & buffer sizing",
                "Wireshark / TShark Analysis": "Protocol verification & packet debugging"
            }
        ]
        st.table(pd.DataFrame(comparison_matrix))

        st.markdown("---")
        st.markdown(
            """
            #### ❓ Why does Throughput diverge from theoretical peak $C$?
            In physical and simulated networking, measured goodput diverges from configured bandwidth capacity due to:
            1. **Packet Header Overhead**: TCP/IP headers (40 bytes per segment) consume channel capacity beyond payload data.
            2. **Buffer Queueing & Propagation Delay**: Round-trip time (RTT) governs how fast the sender receives ACKs and increases CWND.
            3. **Multiplicative Decrease on Loss**: Any packet drop (from buffer tail-drop or channel errors) halves SSTHRESH and shrinks CWND.
            4. **Router Buffer Sizing Limits**: If the buffer is smaller than the Bandwidth-Delay Product (BDP), buffer overflow prevents the sender from saturating the pipe.
            """
        )


if __name__ == "__main__":
    main()
