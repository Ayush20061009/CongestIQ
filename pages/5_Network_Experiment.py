"""
Network Emulation & Link Conditioning Page — Python Network Emulator
====================================================================
Orchestrates Python-based discrete-event network emulation modeling:
- Bottleneck link bandwidth throttling.
- One-way and two-way propagation delay.
- Router queue buffer size limits and tail drop overflow.
- Channel random packet loss.
- TCP Tahoe and TCP Reno sender dynamics.
- Simulated packet delivery, RTT variation, retransmissions, and throughput.

Operates 100% natively on Windows 10 without requiring Linux, WSL2, VirtualBox,
Mininet, or Docker. All results are clearly labeled as simulated network models.
"""

from __future__ import annotations

import math
import os
import platform
import sys
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from core.network_simulation import (
    NetworkExperimentConfig,
    ExperimentResult,
    NetworkExperimentManager,
    save_experiment_history,
    load_experiment_history
)
from utils.helpers import (
    render_project_sidebar,
    format_bitrate,
    format_bytes,
    CHART_DARK_LAYOUT
)


def main() -> None:
    st.set_page_config(
        page_title="CongestIQ | Network Emulation",
        page_icon="⚡",
        layout="wide"
    )

    # Render persistent sidebar
    render_project_sidebar()

    # Load historical experiments if available
    history_file = os.path.join(PARENT_DIR, "data", "experiment_history.json")
    if "experiment_history" not in st.session_state:
        st.session_state["experiment_history"] = load_experiment_history(history_file)

    st.title("🌐 CongestIQ — Network Emulation & Link Conditioning")
    st.caption("Understand. Simulate. Optimise. • Native Windows 10 Discrete-Event Packet Transmission, Queueing & TCP Dynamics")

    st.info(
        "ℹ️ **Simulated Network Emulation**: This module uses a pure Python discrete-event emulation engine "
        "to model packet transmission, bottleneck link queueing, propagation delay, and packet loss without "
        "requiring Mininet, Linux, or root permissions. **All metrics presented here are simulated models**, "
        "providing a mathematically grounded learning environment on Windows 10."
    )

    st.divider()

    # 1. Environment Status
    st.header("1. Emulation Environment Status")
    env = NetworkExperimentManager.verify_environment()

    col_env1, col_env2, col_env3, col_env4 = st.columns(4)
    col_env1.metric("Operating System", platform.system())
    col_env2.metric("Python Version", platform.python_version())
    col_env3.metric("Emulation Engine", "Python Native Emulator")
    col_env4.metric("Platform Status", "Windows 10 Native Ready ✅")

    st.success("✅ **Native Python Network Emulator Active**: Ready to simulate on Windows 10 with zero external dependencies.")

    st.divider()

    # 2. Topology Visualization
    st.header("2. Emulated Network Topology: Bottleneck Router Link")
    st.markdown(
        """
        The emulation models a classic client-server path traversing a bottleneck intermediate router:
        """
    )

    st.code(
        """
+-------------------+               +-------------------------+               +-------------------+
|      HOST A       |               |    BOTTLENECK ROUTER    |               |      HOST B       |
|    (TCP Sender)   | ============= |  [FIFO Queue Buffer: Q] | ------------> |   (TCP Receiver)  |
|   Tahoe / Reno    |  Unrestricted |  - Buffer Size (packets)|  Conditioned  |   Cumulative ACKs |
+-------------------+     Access    +-------------------------+     Link      +-------------------+
                                                              - Bandwidth (C Mbps)
                                                              - Propagation Delay (D ms)
                                                              - Packet Loss (P %)
        """,
        language="text"
    )

    st.divider()

    # 3. Experiment Configuration Controls
    st.header("3. Network Emulation Configuration")

    with st.form("network_emulation_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            exp_id = st.text_input(
                "Experiment ID",
                value="EXP-001",
                help="Unique identifier for logging this emulation run."
            )
            bandwidth_mbps = st.number_input(
                "Bottleneck Bandwidth (Mbps)",
                min_value=0.5,
                max_value=1000.0,
                value=10.0,
                step=1.0,
                help="Transmission rate capacity of the bottleneck link in Megabits per second."
            )
            buffer_size = st.number_input(
                "Network Buffer Size (packets)",
                min_value=5,
                max_value=1000,
                value=50,
                step=5,
                help="Maximum capacity of the router queue buffer before tail-drop packet loss occurs."
            )

        with col2:
            delay_ms = st.number_input(
                "One-Way Propagation Delay (ms)",
                min_value=0.0,
                max_value=500.0,
                value=20.0,
                step=5.0,
                help="One-way physical transmission delay. Round-trip propagation time is 2 × Delay."
            )
            loss_pct = st.number_input(
                "Random Packet Loss Probability (%)",
                min_value=0.0,
                max_value=50.0,
                value=0.5,
                step=0.5,
                help="Probability of random packet drops due to channel noise or bit errors."
            )

        with col3:
            duration_sec = st.slider(
                "Simulation Duration (seconds)",
                min_value=5,
                max_value=60,
                value=10,
                step=5,
                help="Total duration of the simulated network transmission session."
            )
            tcp_algo = st.selectbox(
                "TCP Congestion Control Algorithm",
                options=["reno", "tahoe", "cubic"],
                index=0,
                format_func=lambda x: f"TCP {x.upper()}",
                help="Congestion control state machine governing sender window adaptations."
            )

        submit_btn = st.form_submit_button("🚀 Run Network Emulation Simulation", use_container_width=True)

    # 4. Simulation Execution Handling
    if submit_btn:
        try:
            config = NetworkExperimentConfig(
                experiment_id=exp_id,
                bandwidth_mbps=float(bandwidth_mbps),
                delay_ms=float(delay_ms),
                loss_percentage=float(loss_pct),
                buffer_size_packets=int(buffer_size),
                duration_seconds=int(duration_sec),
                tcp_congestion_algorithm=tcp_algo
            )

            manager = NetworkExperimentManager(config)

            with st.spinner(f"Simulating network emulation '{config.experiment_id}' ({config.duration_seconds}s TCP {config.tcp_congestion_algorithm.upper()})..."):
                result = manager.run_experiment()
                st.session_state["latest_experiment_result"] = result

            if result.status == "Completed":
                st.success(f"✅ Network emulation '{config.experiment_id}' completed successfully!")
                if "experiment_history" not in st.session_state:
                    st.session_state["experiment_history"] = []
                st.session_state["experiment_history"].append(result)

                # Persist to data/experiment_history.json
                history_file = os.path.join(PARENT_DIR, "data", "experiment_history.json")
                try:
                    save_experiment_history(st.session_state["experiment_history"], history_file)
                except Exception:
                    pass
            else:
                st.error(f"❌ Emulation failed: {result.error_message}")

        except ValueError as val_err:
            st.error(f"❌ Configuration Validation Error: {val_err}")
        except Exception as exc:
            st.error(f"❌ Execution Failure: {exc}")

    # 5. Results Display (Clearly Labeled as Simulated)
    st.divider()
    st.header("4. Simulated Performance Measurements")

    if "latest_experiment_result" in st.session_state:
        res: ExperimentResult = st.session_state["latest_experiment_result"]

        if res.status == "Completed":
            st.markdown(
                f"**Simulation Run**: `{res.experiment_id}` • Algorithm: **TCP {res.tcp_congestion_algorithm.upper()}** • "
                f"*(Simulated Python Model)*"
            )

            # Metric Cards
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Simulated Throughput", f"{res.measured_throughput_mbps:.2f} Mbps")
            r2.metric("Configured Bandwidth", f"{res.configured_bandwidth_mbps:.1f} Mbps")
            eff = (res.measured_throughput_mbps / res.configured_bandwidth_mbps * 100.0) if res.configured_bandwidth_mbps > 0 else 0.0
            r3.metric("Throughput Efficiency", f"{eff:.1f}%")
            r4.metric("Simulated Transfer", f"{res.transfer_amount_mb:.2f} MB")

            r5, r6, r7, r8 = st.columns(4)
            r5.metric("Total Retransmissions", res.measured_retransmissions)
            rtt_disp = f"{res.measured_rtt_ms:.2f} ms" if res.measured_rtt_ms is not None else "N/A"
            r6.metric("Simulated Mean RTT", rtt_disp)
            r7.metric("Buffer Tail-Drops", f"{res.buffer_drops} pkts")
            r8.metric("Random Channel Drops", f"{res.random_drops} pkts")

            # Structured Summary Table
            st.markdown("#### Structured Results Summary Table (Simulated):")
            st.dataframe(res.to_dataframe(), use_container_width=True)

            # 6. Interactive Plotly Visualizations from Simulation Output
            if res.time_series_data and len(res.time_series_data) > 0:
                st.markdown("---")
                st.subheader("📊 Interactive Emulation Visualizations")
                ts_df = pd.DataFrame(res.time_series_data)

                col_plot1, col_plot2 = st.columns(2)

                with col_plot1:
                    # Plot 1: Throughput over Time
                    fig_thr = go.Figure()
                    fig_thr.add_trace(go.Scatter(
                        x=ts_df["Time_Sec"],
                        y=ts_df["Throughput_Mbps"],
                        mode="lines+markers",
                        name="Simulated Throughput (Mbps)",
                        line=dict(color="#38bdf8", width=2.5),
                        marker=dict(size=4, color="#38bdf8")
                    ))
                    # Link Bandwidth Ceiling
                    fig_thr.add_trace(go.Scatter(
                        x=[ts_df["Time_Sec"].min(), ts_df["Time_Sec"].max()],
                        y=[res.configured_bandwidth_mbps, res.configured_bandwidth_mbps],
                        mode="lines",
                        name="Configured Bandwidth Ceiling",
                        line=dict(color="#ef4444", width=2, dash="dash")
                    ))
                    # Mathis Upper Bound if loss > 0
                    if res.configured_loss_percentage > 0 and res.measured_rtt_ms:
                        p = res.configured_loss_percentage / 100.0
                        rtt_s = res.measured_rtt_ms / 1000.0
                        mathis_mbps = min(
                            res.configured_bandwidth_mbps,
                            round(((1460.0 * 8.0) / (rtt_s * math.sqrt(p))) / 1e6, 2)
                        )
                        fig_thr.add_trace(go.Scatter(
                            x=[ts_df["Time_Sec"].min(), ts_df["Time_Sec"].max()],
                            y=[mathis_mbps, mathis_mbps],
                            mode="lines",
                            name="Mathis Theoretical Bound",
                            line=dict(color="#10b981", width=1.5, dash="dot")
                        ))

                    thr_layout = dict(CHART_DARK_LAYOUT)
                    fig_thr.update_layout(
                        **thr_layout,
                        title="<b>Simulated Throughput vs. Link Capacity over Time</b>",
                        xaxis_title="Simulation Time (seconds)",
                        yaxis_title="Throughput (Mbps)",
                        hovermode="x unified",
                        height=360
                    )
                    st.plotly_chart(fig_thr, use_container_width=True)

                with col_plot2:
                    # Plot 2: CWND & SSTHRESH Evolution
                    fig_cwnd = go.Figure()
                    fig_cwnd.add_trace(go.Scatter(
                        x=ts_df["Time_Sec"],
                        y=ts_df["CWND"],
                        mode="lines+markers",
                        name="Congestion Window (CWND)",
                        line=dict(color="#f59e0b", width=2.5),
                        marker=dict(size=4, color="#f59e0b")
                    ))
                    fig_cwnd.add_trace(go.Scatter(
                        x=ts_df["Time_Sec"],
                        y=ts_df["SSTHRESH"],
                        mode="lines",
                        name="Slow Start Threshold (SSTHRESH)",
                        line=dict(color="#a855f7", width=2, dash="dash")
                    ))
                    cwnd_layout = dict(CHART_DARK_LAYOUT)
                    fig_cwnd.update_layout(
                        **cwnd_layout,
                        title="<b>CWND & SSTHRESH Dynamics over Simulation Time</b>",
                        xaxis_title="Simulation Time (seconds)",
                        yaxis_title="Window Size (MSS)",
                        hovermode="x unified",
                        height=360
                    )
                    st.plotly_chart(fig_cwnd, use_container_width=True)

                col_plot3, col_plot4 = st.columns(2)

                with col_plot3:
                    # Plot 3: Router Buffer Queue Occupancy & Drops
                    fig_buf = go.Figure()
                    fig_buf.add_trace(go.Scatter(
                        x=ts_df["Time_Sec"],
                        y=ts_df["Buffer_Occupancy"],
                        mode="lines",
                        fill="tozeroy",
                        name="Buffer Queue Occupancy",
                        line=dict(color="#06b6d4", width=2),
                        fillcolor="rgba(6, 182, 212, 0.15)"
                    ))
                    fig_buf.add_trace(go.Scatter(
                        x=[ts_df["Time_Sec"].min(), ts_df["Time_Sec"].max()],
                        y=[res.configured_buffer_size, res.configured_buffer_size],
                        mode="lines",
                        name="Router Buffer Capacity",
                        line=dict(color="#ef4444", width=2, dash="dot")
                    ))
                    # Mark drop events
                    drop_steps = ts_df[ts_df["Packets_Dropped"] > 0]
                    if not drop_steps.empty:
                        fig_buf.add_trace(go.Scatter(
                            x=drop_steps["Time_Sec"],
                            y=drop_steps["Buffer_Occupancy"],
                            mode="markers",
                            name="Packet Drop Event",
                            marker=dict(color="#f43f5e", size=9, symbol="x", line=dict(color="#ffffff", width=1))
                        ))

                    buf_layout = dict(CHART_DARK_LAYOUT)
                    fig_buf.update_layout(
                        **buf_layout,
                        title="<b>Router Buffer Queue Occupancy & Overflow Drops</b>",
                        xaxis_title="Simulation Time (seconds)",
                        yaxis_title="Buffer Depth (packets)",
                        hovermode="x unified",
                        height=360
                    )
                    st.plotly_chart(fig_buf, use_container_width=True)

                with col_plot4:
                    # Plot 4: Dynamic RTT Progression
                    base_rtt = 2.0 * res.configured_delay_ms
                    fig_rtt = go.Figure()
                    fig_rtt.add_trace(go.Scatter(
                        x=ts_df["Time_Sec"],
                        y=ts_df["RTT_Ms"],
                        mode="lines+markers",
                        name="Observed RTT (Base + Queueing)",
                        line=dict(color="#60a5fa", width=2),
                        marker=dict(size=4, color="#60a5fa")
                    ))
                    fig_rtt.add_trace(go.Scatter(
                        x=[ts_df["Time_Sec"].min(), ts_df["Time_Sec"].max()],
                        y=[base_rtt, base_rtt],
                        mode="lines",
                        name="Base Propagation RTT (2 × Delay)",
                        line=dict(color="#94a3b8", width=1.5, dash="dash")
                    ))
                    rtt_layout = dict(CHART_DARK_LAYOUT)
                    fig_rtt.update_layout(
                        **rtt_layout,
                        title="<b>Observed Round-Trip Time (RTT) Dynamics</b>",
                        xaxis_title="Simulation Time (seconds)",
                        yaxis_title="RTT (ms)",
                        hovermode="x unified",
                        height=360
                    )
                    st.plotly_chart(fig_rtt, use_container_width=True)

        else:
            st.error(f"Last emulation run failed with error: {res.error_message}")

    else:
        st.info(
            "ℹ️ **No network emulation has been executed yet in this session.**\n\n"
            "Configure link parameters above and click **Run Network Emulation Simulation**. "
            "Simulated packet queueing, RTT, throughput, and Plotly graphs will appear here immediately."
        )

    st.divider()

    # 7. Theoretical Principles & Analysis
    st.header("5. Technical Analysis: Network Parameters vs. TCP Performance")
    st.markdown(
        """
        The simulated network emulation models four core transport and queueing phenomena:
        
        ### 1. Bandwidth-Delay Product (BDP)
        The Bandwidth-Delay Product determines the capacity of the unacknowledged data pipeline:
        """
    )
    st.latex(r"\text{BDP} = \text{Bandwidth (bps)} \times \text{Base RTT (seconds)}")
    st.markdown(
        """
        If the sender's congestion window ($CWND$) is smaller than the BDP, the pipe is under-utilized, 
        and the connection cannot saturate the available link capacity.
        
        ### 2. Router Buffer Sizing & Queueing Delay
        When packets arrive at the router faster than the link can serialize them, packets accumulate in 
        the buffer queue. This introduces queueing delay:
        """
    )
    st.latex(r"D_{\text{queue}} = \frac{\text{Queue Depth (packets)}}{\text{Link Service Rate (pkts/sec)}}")
    st.markdown(
        """
        - **Buffer Tail Drop**: When queue depth exceeds the configured **Buffer Size**, arriving packets 
          are dropped, provoking TCP loss recovery (Fast Retransmit or Timeout).
        - **Bufferbloat**: An excessively large buffer prevents packet loss but causes severe latency inflation.
        
        ### 3. Impact of Packet Loss (The Mathis Formula)
        Under periodic packet loss probability ($p$), TCP Reno/Tahoe throughput is mathematically bounded by:
        """
    )
    st.latex(r"\text{Throughput} \le \frac{\text{MSS}}{\text{RTT} \times \sqrt{p}} \times C")
    st.markdown(
        """
        Because every packet loss triggers multiplicative decrease ($SSTHRESH = CWND / 2$), even small loss 
        rates (e.g. 1–2%) dramatically reduce TCP throughput.
        """
    )


if __name__ == "__main__":
    main()
