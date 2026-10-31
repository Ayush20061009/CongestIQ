"""
Interactive Simulation Page
===========================
Interactive simulation interface for TCP Tahoe and TCP Reno algorithms.
Features Plotly interactive visualizations, SSTHRESH tracking, state transition timelines,
and dynamic algorithmic explanations.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List
import pandas as pd
import streamlit as st

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from core.congestion_control import (
    SimulationParameters,
    LossEventType,
    simulate_tcp
)
from utils.helpers import (
    render_project_sidebar,
    build_cwnd_progression_chart,
    build_ssthresh_chart,
    build_tcp_state_timeline_chart
)


def generate_simulation_explanation(df: pd.DataFrame, metrics: Dict[str, Any]) -> List[str]:
    """
    Generate dynamic, intelligent educational explanations derived directly
    from the actual simulation results rather than static text.
    """
    explanations: List[str] = []
    algo = metrics["algorithm"]

    # 1. Slow Start Analysis
    ss_rounds = df[df["TCP_State"] == "Slow Start"]["RTT_Round"].tolist()
    if ss_rounds:
        first_ss_streak = []
        for r in ss_rounds:
            if not first_ss_streak or r == first_ss_streak[-1] + 1:
                first_ss_streak.append(r)
            else:
                break
        explanations.append(
            f"**Slow Start Exponential Growth**: The simulation operated in Slow Start across "
            f"Rounds {first_ss_streak[0]} to {first_ss_streak[-1]}. During this phase, CWND doubled each RTT "
            f"as ACKs arrived, exponentially probing network capacity."
        )

    # 2. Congestion Avoidance Transition
    ca_rounds = df[df["TCP_State"] == "Congestion Avoidance"]["RTT_Round"].tolist()
    if ca_rounds:
        first_ca = ca_rounds[0]
        ssthresh_val = df[df["RTT_Round"] == first_ca]["SSTHRESH"].iloc[0]
        explanations.append(
            f"**Transition to Congestion Avoidance**: At Round {first_ca}, CWND reached or exceeded SSTHRESH "
            f"({ssthresh_val:.1f} MSS). TCP shifted from exponential growth to conservative Additive Increase "
            f"(AIMD), adding approximately +1.0 MSS per RTT."
        )

    # 3. Loss Event Analysis
    loss_steps = df[df["Loss_Event"] != "None"]
    if not loss_steps.empty:
        for _, row in loss_steps.iterrows():
            r_num = int(row["RTT_Round"])
            event_type = row["Loss_Event"]
            post_cwnd = row["CWND"]
            post_ssthresh = row["SSTHRESH"]

            if "Triple Duplicate" in event_type:
                if algo == "Tahoe":
                    explanations.append(
                        f"**Packet Loss at Round {r_num} (3 Duplicate ACKs)**: TCP Tahoe invoked Fast Retransmit. "
                        f"Because Tahoe does not implement Fast Recovery, SSTHRESH was halved to "
                        f"{post_ssthresh:.1f} MSS, and CWND collapsed to {post_cwnd:.1f} MSS, forcing TCP to restart Slow Start from scratch."
                    )
                else:  # Reno
                    explanations.append(
                        f"**Packet Loss at Round {r_num} (3 Duplicate ACKs)**: TCP Reno entered **Fast Recovery**. "
                        f"SSTHRESH was halved to {post_ssthresh:.1f} MSS, and CWND was inflated to "
                        f"{post_cwnd:.1f} MSS (SSTHRESH + 3). Upon receiving the recovery ACK in the subsequent round, "
                        f"CWND deflated back to SSTHRESH and resumed Congestion Avoidance without dropping to 1 MSS."
                    )
            elif "Timeout" in event_type:
                explanations.append(
                    f"**Retransmission Timeout (RTO) at Round {r_num}**: An RTO timer expired, signaling severe congestion. "
                    f"SSTHRESH was halved to {post_ssthresh:.1f} MSS, CWND was reset to {post_cwnd:.1f} MSS, and Slow Start resumed."
                )
    else:
        explanations.append(
            "**Uncongested Transmission**: No packet loss events occurred in this simulation run. "
            "CWND expanded monotonically through Slow Start into Congestion Avoidance."
        )

    # 4. Final Summary
    explanations.append(
        f"**Aggregate Performance**: Across {metrics['total_rounds']} RTT rounds, TCP {algo} reached a peak window of "
        f"{metrics['peak_cwnd']:.1f} MSS and sustained an average throughput window of {metrics['average_cwnd']:.2f} MSS with "
        f"{metrics['total_retransmissions']} retransmissions."
    )

    return explanations


def main() -> None:
    st.set_page_config(page_title="CongestIQ | Simulation Engine", page_icon="⚡", layout="wide")

    # Render persistent sidebar
    render_project_sidebar()

    st.title("⚙️ CongestIQ — TCP Simulation Engine")
    st.caption("Understand. Simulate. Optimise. • Interactive Discrete RTT Simulation for TCP Tahoe & Reno")

    st.divider()

    # 1. Parameter Configuration Form
    st.header("1. Simulation Parameter Configuration")

    with st.form("simulation_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            algorithm = st.selectbox(
                "Congestion Control Algorithm",
                options=["Tahoe", "Reno"],
                index=0,
                help="Select between TCP Tahoe (RFC 1122) and TCP Reno (RFC 5681)."
            )
            initial_cwnd = st.number_input(
                "Initial CWND (MSS)",
                min_value=1.0,
                max_value=20.0,
                value=1.0,
                step=1.0,
                help="Initial Congestion Window size in MSS units (standard: 1.0 MSS)."
            )
            mss_bytes = st.number_input(
                "Maximum Segment Size (bytes)",
                min_value=256,
                max_value=9000,
                value=1460,
                step=100,
                help="Standard Ethernet MSS is 1460 bytes (1500 byte MTU - 40 byte headers)."
            )

        with col2:
            initial_ssthresh = st.number_input(
                "Initial SSTHRESH (MSS)",
                min_value=2.0,
                max_value=128.0,
                value=16.0,
                step=2.0,
                help="Slow Start Threshold separating Slow Start and Congestion Avoidance."
            )
            max_cwnd = st.number_input(
                "Maximum CWND Limit (MSS)",
                min_value=4.0,
                max_value=256.0,
                value=64.0,
                step=4.0,
                help="Upper bound ceiling representing receiver buffer (RWND) or network bandwidth-delay product."
            )

        with col3:
            num_rounds = st.slider(
                "Simulation Duration (RTT Rounds)",
                min_value=5,
                max_value=60,
                value=30,
                step=5,
                help="Number of discrete Round-Trip Time transmission cycles."
            )

        st.markdown("#### Deterministic Loss Event Injection")
        st.caption("Inject specific loss events at chosen RTT rounds to inspect exact algorithmic reactions.")

        loss_c1, loss_c2 = st.columns(2)
        with loss_c1:
            ev1_round = st.number_input("Event 1 at RTT Round (0 to disable)", min_value=0, max_value=num_rounds, value=6)
            ev1_type = st.selectbox(
                "Event 1 Loss Type",
                options=[LossEventType.NONE.value, LossEventType.TRIPLE_DUPLICATE_ACK.value, LossEventType.TIMEOUT.value],
                index=1
            )

        with loss_c2:
            ev2_round = st.number_input("Event 2 at RTT Round (0 to disable)", min_value=0, max_value=num_rounds, value=18)
            ev2_type = st.selectbox(
                "Event 2 Loss Type",
                options=[LossEventType.NONE.value, LossEventType.TRIPLE_DUPLICATE_ACK.value, LossEventType.TIMEOUT.value],
                index=2
            )

        st.markdown("#### Optional Random Packet Loss")
        enable_random = st.checkbox("Enable Probabilistic Random Packet Loss", value=False)
        if enable_random:
            rc1, rc2 = st.columns(2)
            with rc1:
                random_prob = st.slider("Random Loss Probability per Round", min_value=0.01, max_value=0.50, value=0.05, step=0.01)
            with rc2:
                random_seed = st.number_input("Random Seed (for reproducible traces)", min_value=1, max_value=999999, value=42)
        else:
            random_prob = 0.0
            random_seed = None

        submit_btn = st.form_submit_button("🚀 Run Simulation & Generate Visualizations", use_container_width=True)

    # 2. Execution Logic
    if submit_btn:
        loss_events_dict: Dict[int, LossEventType] = {}
        if ev1_type != LossEventType.NONE.value and ev1_round > 0:
            loss_events_dict[int(ev1_round)] = LossEventType(ev1_type)
        if ev2_type != LossEventType.NONE.value and ev2_round > 0:
            loss_events_dict[int(ev2_round)] = LossEventType(ev2_type)

        try:
            params = SimulationParameters(
                algorithm=algorithm,
                initial_cwnd=float(initial_cwnd),
                initial_ssthresh=float(initial_ssthresh),
                mss=int(mss_bytes),
                max_cwnd=float(max_cwnd),
                num_rounds=int(num_rounds),
                loss_probability=float(random_prob),
                loss_events=loss_events_dict,
                random_seed=int(random_seed) if random_seed else None
            )

            # Run simulation
            df, metrics = simulate_tcp(params)

            # Store in session state
            st.session_state["simulation_df"] = df
            st.session_state["latest_simulation"] = metrics
            st.session_state["simulation_params"] = params

            st.success(f"✅ TCP {algorithm} simulation completed successfully across {num_rounds} RTT rounds!")

        except ValueError as err:
            st.error(f"❌ Parameter Validation Error: {err}")
        except Exception as e:
            st.error(f"❌ Simulation Execution Error: {e}")

    # 3. Interactive Visualization and Results Display
    if "simulation_df" in st.session_state and "latest_simulation" in st.session_state:
        st.divider()

        df = st.session_state["simulation_df"]
        metrics = st.session_state["latest_simulation"]
        algo_name = metrics["algorithm"]

        st.header(f"2. Simulation Performance Metrics: TCP {algo_name}")

        # Metrics Row
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Selected Algorithm", f"TCP {algo_name}")
        m_col2.metric("Rounds Simulated", metrics["total_rounds"])
        m_col3.metric("Final CWND", f"{metrics['final_cwnd']:.1f} MSS")
        m_col4.metric("Final SSTHRESH", f"{metrics['final_ssthresh']:.1f} MSS")

        m_col5, m_col6, m_col7, m_col8 = st.columns(4)
        m_col5.metric("Peak CWND Reached", f"{metrics['peak_cwnd']:.1f} MSS")
        m_col6.metric("Average CWND", f"{metrics['average_cwnd']:.2f} MSS")
        m_col7.metric("Retransmissions", metrics["total_retransmissions"])
        m_col8.metric("Loss Events (Timeouts/DupACKs)", f"{metrics['timeout_count']} / {metrics['fast_retransmit_count']}")

        st.divider()

        st.header("3. Interactive Visualizations & Analysis Tabs")

        tab_cwnd, tab_ssthresh, tab_state, tab_trace, tab_explain = st.tabs([
            "📈 CWND & SSTHRESH Progression",
            "📉 SSTHRESH Evolution",
            "🔄 TCP State Transitions",
            "📋 Detailed Transmission Trace",
            "💡 Algorithmic Explanation"
        ])

        with tab_cwnd:
            st.subheader(f"TCP {algo_name} — CWND & SSTHRESH Progression Chart")
            st.caption(
                "Interactive Plotly chart. Hover over data points to inspect detailed round mechanics. "
                "Orange triangles denote 3 Duplicate ACKs; red crosses denote Timeouts. Use top-right toolbar to zoom or reset."
            )
            fig_cwnd = build_cwnd_progression_chart(df, algo_name)
            st.plotly_chart(fig_cwnd, use_container_width=True)

        with tab_ssthresh:
            st.subheader(f"TCP {algo_name} — Slow Start Threshold (SSTHRESH) Tracking")
            st.caption(
                "Stepped progression showing threshold plateaus and halving points following packet loss. "
                "Red diamonds mark exact rounds where SSTHRESH was recalculated (SSTHRESH = max(CWND/2, 2 MSS))."
            )
            fig_ssthresh = build_ssthresh_chart(df, algo_name)
            st.plotly_chart(fig_ssthresh, use_container_width=True)

        with tab_state:
            st.subheader(f"TCP {algo_name} — State Machine Transitions Timeline")
            st.caption(
                "Categorical timeline tracking transitions between Slow Start (exponential probing), "
                "Congestion Avoidance (AIMD linear growth), and Fast Recovery (Reno window inflation)."
            )
            fig_state = build_tcp_state_timeline_chart(df, algo_name)
            st.plotly_chart(fig_state, use_container_width=True)

        with tab_trace:
            st.subheader("Round-by-Round Transmission Log")
            display_columns = [
                "RTT_Round", "Algorithm", "CWND", "SSTHRESH", "TCP_State",
                "Loss_Event", "Retransmission", "Action", "Explanation"
            ]
            st.dataframe(df[display_columns], use_container_width=True, height=450)

        with tab_explain:
            st.subheader("Dynamic Simulation Analysis & Narrative")
            explanations = generate_simulation_explanation(df, metrics)
            for exp in explanations:
                st.markdown(f"- {exp}")


if __name__ == "__main__":
    main()
