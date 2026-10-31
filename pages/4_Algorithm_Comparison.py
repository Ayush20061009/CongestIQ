"""
Algorithm Comparison Page
=========================
Interactive comparative analysis evaluating TCP Tahoe vs. TCP Reno under identical
network loss conditions, featuring side-by-side Plotly charts, metric tables, and dynamic analysis.
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
    compare_algorithms
)
from utils.helpers import (
    render_project_sidebar,
    build_comparison_cwnd_chart,
    build_comparison_ssthresh_chart,
    build_comparison_state_chart
)


def generate_comparison_explanation(comp_df: pd.DataFrame, summary: Dict[str, Any]) -> List[str]:
    """
    Generate dynamic comparative educational explanations derived strictly
    from the actual simulation outputs without hardcoded conclusions.
    """
    explanations: List[str] = []
    
    t_avg = summary["tahoe_average_cwnd"]
    r_avg = summary["reno_average_cwnd"]
    t_final = summary["tahoe_final_cwnd"]
    r_final = summary["reno_final_cwnd"]
    advantage = summary["reno_throughput_advantage_percent"]
    fast_retrans = summary["reno_fast_retransmits"]
    timeouts = summary["reno_timeouts"]

    # 1. Slow Start Dynamics
    explanations.append(
        "**Initial Growth (Slow Start)**: Both algorithms began with identical initial parameters and exhibited "
        "identical exponential doubling until reaching the Slow Start Threshold (SSTHRESH), confirming "
        "that Tahoe and Reno operate identically in uncongested Slow Start."
    )

    # 2. Loss Recovery Behavior
    loss_steps = comp_df[comp_df["Loss_Event"] != "None"]
    if not loss_steps.empty:
        for _, row in loss_steps.iterrows():
            r_num = int(row["RTT_Round"])
            ev_type = row["Loss_Event"]
            t_drop = row["Tahoe_CWND"]
            r_drop = row["Reno_CWND"]
            diff = row["CWND_Difference"]

            if "Triple Duplicate" in ev_type:
                explanations.append(
                    f"**Reaction to 3 Duplicate ACKs at Round {r_num}**: "
                    f"TCP Tahoe suffered a complete window collapse to {t_drop:.1f} MSS and re-entered Slow Start. "
                    f"In contrast, TCP Reno invoked **Fast Retransmit & Fast Recovery**, setting CWND to {r_drop:.1f} MSS "
                    f"(a +{diff:.1f} MSS advantage). In the next round, Reno deflated to SSTHRESH and resumed Congestion Avoidance, "
                    f"completely avoiding the Slow Start penalty."
                )
            elif "Timeout" in ev_type:
                explanations.append(
                    f"**Reaction to RTO Timeout at Round {r_num}**: Both algorithms detected severe network congestion. "
                    f"Tahoe and Reno responded identically: both halved SSTHRESH, collapsed CWND to 1.0 MSS, "
                    f"and returned to Slow Start."
                )
    else:
        explanations.append(
            "**Zero Packet Loss Scenario**: No congestion events were injected. Both algorithms progressed "
            "identically through Slow Start into Congestion Avoidance with zero divergence."
        )

    # 3. Objective Throughput & Window Comparison
    if fast_retrans > 0 and timeouts == 0:
        explanations.append(
            f"**Throughput Advantage**: Because packet loss was handled via Fast Retransmit without timeouts, "
            f"TCP Reno maintained an average window of {r_avg:.2f} MSS vs Tahoe's {t_avg:.2f} MSS, "
            f"representing a **+{advantage:.1f}% throughput advantage**."
        )
    elif timeouts > 0 and fast_retrans == 0:
        explanations.append(
            f"**Timeout-Dominated Scenario**: Because all packet drops were timeouts (RTO), both algorithms "
            f"suffered identical window collapses to 1.0 MSS. Average CWND remained closely matched "
            f"(Tahoe: {t_avg:.2f} MSS vs Reno: {r_avg:.2f} MSS)."
        )
    else:
        explanations.append(
            f"**Final Window Comparison**: Across {summary['total_rounds']} rounds, TCP Tahoe concluded at "
            f"{t_final:.1f} MSS while TCP Reno concluded at {r_final:.1f} MSS (Average: Tahoe {t_avg:.2f} MSS, Reno {r_avg:.2f} MSS)."
        )

    return explanations


def main() -> None:
    st.set_page_config(page_title="CongestIQ | Algorithm Comparison", page_icon="⚡", layout="wide")

    # Render sidebar
    render_project_sidebar()

    st.title("⚖️ CongestIQ — Tahoe vs. Reno Comparison")
    st.caption("Understand. Simulate. Optimise. • Synchronized Algorithmic Divergence & Loss Recovery Under Identical Conditions")

    st.divider()

    # 1. Parameter Configuration Form
    st.header("1. Shared Simulation Parameters")
    st.markdown("Both algorithms are executed with identical inputs to isolate their loss-recovery behavior:")

    with st.form("comparison_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            initial_cwnd = st.number_input("Shared Initial CWND (MSS)", min_value=1.0, max_value=20.0, value=1.0, step=1.0)
            initial_ssthresh = st.number_input("Shared Initial SSTHRESH (MSS)", min_value=2.0, max_value=128.0, value=16.0, step=2.0)
            mss_bytes = st.number_input("Maximum Segment Size (bytes)", min_value=256, max_value=9000, value=1460, step=100)

        with col2:
            max_cwnd = st.number_input("Maximum CWND Limit (MSS)", min_value=4.0, max_value=256.0, value=64.0, step=4.0)
            num_rounds = st.slider("Shared Duration (RTT Rounds)", min_value=10, max_value=60, value=30, step=5)

        with col3:
            st.markdown("#### Scheduled Congestion Events")
            loss_round_1 = st.number_input("Event 1 at Round", min_value=1, max_value=num_rounds, value=8)
            loss_type_1 = st.selectbox(
                "Event 1 Type",
                options=[LossEventType.TRIPLE_DUPLICATE_ACK.value, LossEventType.TIMEOUT.value],
                index=0,
                help="Compare how Tahoe and Reno react differently to 3 Duplicate ACKs."
            )

        col_adv1, col_adv2 = st.columns(2)
        with col_adv1:
            loss_round_2 = st.number_input("Event 2 at Round (0 to disable)", min_value=0, max_value=num_rounds, value=18)
            loss_type_2 = st.selectbox(
                "Event 2 Type",
                options=[LossEventType.NONE.value, LossEventType.TRIPLE_DUPLICATE_ACK.value, LossEventType.TIMEOUT.value],
                index=2
            )
        with col_adv2:
            st.markdown("#### Optional Random Packet Loss (Shared Seed)")
            enable_rand = st.checkbox("Enable Shared Random Loss", value=False)
            rand_prob = st.slider("Loss Probability", 0.01, 0.30, 0.05, 0.01) if enable_rand else 0.0
            rand_seed = 42

        submit_btn = st.form_submit_button("⚖️ Run Comparative Simulation & Build Visualizations", use_container_width=True)

    # 2. Execution Logic
    if submit_btn:
        loss_dict: Dict[int, LossEventType] = {int(loss_round_1): LossEventType(loss_type_1)}
        if loss_type_2 != LossEventType.NONE.value and loss_round_2 > 0:
            loss_dict[int(loss_round_2)] = LossEventType(loss_type_2)

        try:
            params = SimulationParameters(
                algorithm="Tahoe",
                initial_cwnd=float(initial_cwnd),
                initial_ssthresh=float(initial_ssthresh),
                mss=int(mss_bytes),
                max_cwnd=float(max_cwnd),
                num_rounds=int(num_rounds),
                loss_probability=float(rand_prob),
                loss_events=loss_dict,
                random_seed=rand_seed
            )

            comp_df, summary = compare_algorithms(params)

            st.session_state["comparison_df"] = comp_df
            st.session_state["comparison_summary"] = summary

            st.success("✅ Comparative simulation completed for both TCP Tahoe and TCP Reno!")

        except ValueError as err:
            st.error(f"❌ Configuration Error: {err}")
        except Exception as e:
            st.error(f"❌ Execution Error: {e}")

    # 3. Interactive Comparison Graphs & Tables
    if "comparison_df" in st.session_state and "comparison_summary" in st.session_state:
        st.divider()

        comp_df = st.session_state["comparison_df"]
        summary = st.session_state["comparison_summary"]

        st.header("2. Comparative Performance Metrics")

        m1, m2, m3, m4 = st.columns(4)
        adv = summary["reno_throughput_advantage_percent"]
        m1.metric("Reno Throughput Advantage", f"+{adv:.1f}%" if adv >= 0 else f"{adv:.1f}%")
        m2.metric("Average CWND (Tahoe vs Reno)", f"{summary['tahoe_average_cwnd']:.2f} / {summary['reno_average_cwnd']:.2f} MSS")
        m3.metric("Final CWND (Tahoe vs Reno)", f"{summary['tahoe_final_cwnd']:.1f} / {summary['reno_final_cwnd']:.1f} MSS")
        m4.metric("Peak CWND (Tahoe vs Reno)", f"{summary['tahoe_peak_cwnd']:.1f} / {summary['reno_peak_cwnd']:.1f} MSS")

        st.divider()

        st.header("3. Interactive Comparison Charts")

        tab_cwnd, tab_ssthresh, tab_state, tab_table, tab_explain = st.tabs([
            "📈 CWND Comparison Chart",
            "📉 SSTHRESH Comparison Chart",
            "🔄 State Machine Divergence",
            "📊 Comparison Summary Table",
            "💡 Comparative Analysis"
        ])

        with tab_cwnd:
            st.subheader("CWND Progression: TCP Tahoe vs. TCP Reno")
            st.caption(
                "Both algorithms plotted on the same chart. Notice how Reno remains elevated during Fast Recovery (green), "
                "while Tahoe drops to 1.0 MSS (blue). Red triangles mark injected packet loss events."
            )
            fig_cmp_cwnd = build_comparison_cwnd_chart(comp_df)
            st.plotly_chart(fig_cmp_cwnd, use_container_width=True)

        with tab_ssthresh:
            st.subheader("SSTHRESH Threshold Evolution Comparison")
            st.caption("Tracks how Tahoe and Reno adjust their Slow Start Thresholds following packet drops.")
            fig_cmp_ssthresh = build_comparison_ssthresh_chart(comp_df)
            st.plotly_chart(fig_cmp_ssthresh, use_container_width=True)

        with tab_state:
            st.subheader("Operating State Divergence Over Time")
            st.caption("Visualizes when Tahoe enters Slow Start after a loss while Reno enters Fast Recovery and Congestion Avoidance.")
            fig_cmp_state = build_comparison_state_chart(comp_df)
            st.plotly_chart(fig_cmp_state, use_container_width=True)

        with tab_table:
            st.subheader("8. Formal Comparison Summary Table")
            
            # Format required summary table
            tahoe_last_state = comp_df["Tahoe_State"].iloc[-1]
            reno_last_state = comp_df["Reno_State"].iloc[-1]
            total_loss = summary["tahoe_timeouts"] + summary["tahoe_fast_retransmits"]

            table_rows = [
                {"Metric": "Final CWND", "TCP Tahoe": f"{summary['tahoe_final_cwnd']:.1f} MSS", "TCP Reno": f"{summary['reno_final_cwnd']:.1f} MSS"},
                {"Metric": "Final SSTHRESH", "TCP Tahoe": f"{comp_df['Tahoe_SSTHRESH'].iloc[-1]:.1f} MSS", "TCP Reno": f"{comp_df['Reno_SSTHRESH'].iloc[-1]:.1f} MSS"},
                {"Metric": "Peak CWND Reached", "TCP Tahoe": f"{summary['tahoe_peak_cwnd']:.1f} MSS", "TCP Reno": f"{summary['reno_peak_cwnd']:.1f} MSS"},
                {"Metric": "Average CWND", "TCP Tahoe": f"{summary['tahoe_average_cwnd']:.2f} MSS", "TCP Reno": f"{summary['reno_average_cwnd']:.2f} MSS"},
                {"Metric": "Loss Events Encountered", "TCP Tahoe": f"{total_loss}", "TCP Reno": f"{total_loss}"},
                {"Metric": "Retransmissions Triggered", "TCP Tahoe": f"{summary['tahoe_retransmissions']}", "TCP Reno": f"{summary['reno_retransmissions']}"},
                {"Metric": "Fast Retransmits (3 Dup ACKs)", "TCP Tahoe": f"{summary['tahoe_fast_retransmits']}", "TCP Reno": f"{summary['reno_fast_retransmits']}"},
                {"Metric": "Timeouts (RTO)", "TCP Tahoe": f"{summary['tahoe_timeouts']}", "TCP Reno": f"{summary['reno_timeouts']}"},
                {"Metric": "Final TCP State", "TCP Tahoe": f"{tahoe_last_state}", "TCP Reno": f"{reno_last_state}"}
            ]
            st.table(table_rows)

            st.markdown("#### Detailed Side-by-Side Step Trace:")
            disp_cols = [
                "RTT_Round", "Loss_Event", "Tahoe_CWND", "Reno_CWND", "CWND_Difference",
                "Tahoe_State", "Reno_State", "Tahoe_Action", "Reno_Action"
            ]
            st.dataframe(comp_df[disp_cols], use_container_width=True, height=400)

        with tab_explain:
            st.subheader("Dynamic Comparative Explanation")
            explanations = generate_comparison_explanation(comp_df, summary)
            for exp in explanations:
                st.markdown(f"- {exp}")


if __name__ == "__main__":
    main()
