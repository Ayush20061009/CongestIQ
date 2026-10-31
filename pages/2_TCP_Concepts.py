"""
TCP Concepts & Educational Theory Page
======================================
Educational guide covering the 14 core fundamentals of TCP congestion control,
mathematical formulas, state transitions, and comparative analysis.
"""

from __future__ import annotations

import os
import sys
import streamlit as st

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from utils.helpers import render_project_sidebar


def main() -> None:
    st.set_page_config(page_title="CongestIQ | TCP Concepts", page_icon="⚡", layout="wide")

    # Render sidebar
    render_project_sidebar()

    st.title("📚 CongestIQ — TCP Fundamentals & Mechanics")
    st.caption("Understand. Simulate. Optimise. • 14 Essential Concepts of TCP Congestion Control, Window Mechanics & Loss Recovery")

    st.divider()

    # Topic 1, 2, 3: The Foundations
    st.header("1. Foundations: What is TCP & Congestion?")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#38bdf8;">1. What is TCP?</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; line-height: 1.5;">
                    The <b>Transmission Control Protocol (TCP)</b> is a connection-oriented, reliable transport-layer 
                    protocol that ensures ordered, error-checked delivery of a stream of bytes between applications over an IP network.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#f59e0b;">2. What is Network Congestion?</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; line-height: 1.5;">
                    <b>Network Congestion</b> occurs when senders transmit more data packets into the network than intermediate 
                    routers and switches can buffer or forward. Router queues fill up, packet delay spikes, and packets are dropped.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            """
            <div class="eng-card">
                <h3 style="margin-top:0; color:#ef4444;">3. Why Congestion Control?</h3>
                <p style="font-size: 0.88rem; color: #cbd5e1; line-height: 1.5;">
                    Without congestion control, senders retransmit lost packets blindly, compounding router buffer exhaustion. 
                    This causes <b>Congestion Collapse</b>, where network capacity is wasted carrying packets that are ultimately dropped.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # Topic 4, 5: State Variables
    st.header("2. Core Variables: CWND & SSTHRESH")
    c4, c5 = st.columns(2)

    with c4:
        st.markdown(
            """
            <div class="concept-card concept-slowstart">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; color: #38bdf8;">4. Congestion Window (CWND)</h3>
                    <span class="tech-badge badge-cyan">Sender-Side Limit</span>
                </div>
                <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.5rem; padding-left: 1.2rem;">
                    <li><b>Definition</b>: The sender-side limit on the number of unacknowledged bytes/packets allowed in-flight.</li>
                    <li><b>Unit</b>: Measured in <b>Maximum Segment Size (MSS)</b> units (typically 1460 bytes) or raw bytes.</li>
                    <li><b>Dynamic Adjustment</b>: Dynamically increases when ACKs arrive and contracts when packet loss is detected.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.latex(r"\text{Max In-Flight Data} = \min(\text{CWND}, \text{RWND})")

    with c5:
        st.markdown(
            """
            <div class="concept-card concept-retransmit">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; color: #f59e0b;">5. Slow Start Threshold (SSTHRESH)</h3>
                    <span class="tech-badge badge-amber">Phase Demarcation</span>
                </div>
                <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.5rem; padding-left: 1.2rem;">
                    <li><b>Definition</b>: The boundary demarcation separating aggressive exponential probing from conservative linear probing.</li>
                    <li><b>Initial Value</b>: Typically set to a high default (e.g., 16 MSS, 32 MSS, or 64 KB).</li>
                    <li><b>Loss Adjustment</b>: Upon packet loss, SSTHRESH is updated to half of current flight size.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.latex(r"\text{SSTHRESH} \leftarrow \max\left(\left\lfloor \frac{\text{CWND}}{2} \right\rfloor, 2\text{ MSS}\right)")

    st.divider()

    # Topic 6, 7, 8: Probing Phases & AIMD
    st.header("3. Probing Phases: Slow Start, Congestion Avoidance & AIMD")
    c6, c7 = st.columns(2)

    with c6:
        st.markdown(
            """
            <div class="concept-card concept-slowstart">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; color: #38bdf8;">6. Slow Start Phase (CWND &lt; SSTHRESH)</h3>
                    <span class="tech-badge badge-cyan">Exponential Probing</span>
                </div>
                <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.5rem; padding-left: 1.2rem;">
                    <li><b>Purpose</b>: Rapidly probe the capacity of an unknown network pipe.</li>
                    <li><b>Behavior</b>: Starts at CWND = 1.0 MSS. Each ACK increments CWND by 1 MSS.</li>
                    <li><b>Growth</b>: Over one Round-Trip Time (RTT), <b>CWND doubles</b> (1 &rarr; 2 &rarr; 4 &rarr; 8 &rarr; 16).</li>
                    <li><b>Transition</b>: When CWND &ge; SSTHRESH, transitions into <b>Congestion Avoidance</b>.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c7:
        st.markdown(
            """
            <div class="concept-card concept-avoidance">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; color: #10b981;">7. Congestion Avoidance Phase (CWND &ge; SSTHRESH)</h3>
                    <span class="tech-badge badge-emerald">Linear Additive</span>
                </div>
                <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.5rem; padding-left: 1.2rem;">
                    <li><b>Purpose</b>: Cautiously probe for additional bandwidth once near the estimated capacity.</li>
                    <li><b>Behavior</b>: Each ACK increments CWND by 1 / &lfloor;CWND&rfloor;.</li>
                    <li><b>Growth</b>: Over one RTT, <b>CWND increases by ~1 MSS</b> linearly (16 &rarr; 17 &rarr; 18 &rarr; 19).</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="concept-card concept-aimd">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; color: #60a5fa;">8. Additive Increase Multiplicative Decrease (AIMD)</h3>
                <span class="tech-badge badge-cyan">Stability Guarantee</span>
            </div>
            <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.5rem;">
                AIMD is the foundational mathematical control algorithm that guarantees network stability and fairness:
            </p>
            <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0; padding-left: 1.2rem;">
                <li><b>Additive Increase (AI)</b>: In the absence of loss, add 1.0 MSS per RTT.</li>
                <li><b>Multiplicative Decrease (MD)</b>: When loss occurs, halve SSTHRESH (SSTHRESH = CWND / 2).</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # Topic 9, 12, 13, 14: Loss Detection & Recovery
    st.header("4. Loss Detection: Duplicate ACKs vs. Timeouts")

    col_ack, col_tmo = st.columns(2)

    with col_ack:
        st.markdown(
            """
            <div class="concept-card concept-retransmit">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; color: #f59e0b;">9. Duplicate ACKs & 12. Fast Retransmit</h3>
                    <span class="tech-badge badge-amber">Early Loss Detection</span>
                </div>
                <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0; padding-left: 1.2rem;">
                    <li><b>Why Duplicate ACKs Occur</b>: When a packet is lost in transit but subsequent packets arrive safely, the receiver sends duplicate ACKs repeating the last in-order sequence number received.</li>
                    <li><b>The 3 Duplicate ACK Rule</b>: Receiving <b>3 duplicate ACKs</b> is taken as strong heuristic proof of packet loss (as opposed to simple packet reordering).</li>
                    <li><b>Fast Retransmit</b>: The sender retransmits the missing segment <b>immediately</b>, without waiting for the retransmission timer (RTO) to expire.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_tmo:
        st.markdown(
            """
            <div class="concept-card concept-timeout">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; color: #ef4444;">14. Timeout Handling (RTO)</h3>
                    <span class="tech-badge badge-rose">Severe Congestion</span>
                </div>
                <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0; padding-left: 1.2rem;">
                    <li><b>Why Timeouts Occur</b>: If a packet and all subsequent packets are lost, or if the link stalls, no ACKs return. The Retransmission Timeout (RTO) timer expires.</li>
                    <li><b>Indication</b>: Represents <b>severe network congestion</b> or complete connection stalling.</li>
                    <li><b>Response in Both Tahoe & Reno</b>: SSTHRESH halved, CWND collapsed to 1.0 MSS, restart Slow Start.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # Topic 10, 11, 13: Tahoe vs Reno & Fast Recovery
    st.header("5. Algorithms: TCP Tahoe vs. TCP Reno")

    c_tahoe, c_reno = st.columns(2)

    with c_tahoe:
        st.markdown(
            """
            <div class="concept-card" style="border-left-color: #38bdf8;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; color: #38bdf8;">10. TCP Tahoe</h3>
                    <span class="tech-badge badge-cyan">RFC 1122 & RFC 2001</span>
                </div>
                <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0; padding-left: 1.2rem;">
                    <li><b>Philosophy</b>: Conservative and safe.</li>
                    <li><b>Reaction to 3 Duplicate ACKs</b>:
                        <ul style="margin-top: 0.25rem;">
                            <li>Triggers Fast Retransmit.</li>
                            <li>Halves SSTHRESH.</li>
                            <li><b>Drops CWND to 1.0 MSS!</b></li>
                            <li>Re-enters Slow Start.</li>
                        </ul>
                    </li>
                    <li><b>Drawback</b>: Completely empties the transmission pipeline on any single dropped packet, causing large throughput dips.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c_reno:
        st.markdown(
            """
            <div class="concept-card concept-recovery">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; color: #a855f7;">11. TCP Reno & 13. Fast Recovery</h3>
                    <span class="tech-badge badge-purple">RFC 5681</span>
                </div>
                <ul style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0; padding-left: 1.2rem;">
                    <li><b>Philosophy</b>: Keep the pipe full when packets are still flowing.</li>
                    <li><b>Reaction to 3 Duplicate ACKs</b>:
                        <ul style="margin-top: 0.25rem;">
                            <li>Triggers Fast Retransmit.</li>
                            <li>Sets SSTHRESH = max(&lfloor;CWND / 2&rfloor;, 2).</li>
                            <li><b>Enters Fast Recovery</b>: Sets CWND = SSTHRESH + 3 MSS (window inflation).</li>
                            <li>When recovery ACK arrives, <b>deflates CWND to SSTHRESH</b> and enters <b>Congestion Avoidance</b>.</li>
                        </ul>
                    </li>
                    <li><b>Benefit</b>: Bypasses the 1 MSS Slow Start penalty, maintaining high average bandwidth utilization.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # Comprehensive Comparison Table
    st.header("6. Comprehensive Comparison: Tahoe vs. Reno")
    st.markdown("Summary comparison of how TCP Tahoe and TCP Reno react to network conditions:")

    comparison_data = [
        {"Condition / Event": "Initial Connection Start", "TCP Tahoe": "CWND = 1 MSS (Slow Start)", "TCP Reno": "CWND = 1 MSS (Slow Start)"},
        {"Condition / Event": "Steady State (No Loss)", "TCP Tahoe": "Doubles in Slow Start, +1 MSS in Congestion Avoidance", "TCP Reno": "Doubles in Slow Start, +1 MSS in Congestion Avoidance"},
        {"Condition / Event": "3 Duplicate ACKs Received", "TCP Tahoe": "Fast Retransmit -> CWND drops to 1 MSS -> Slow Start", "TCP Reno": "Fast Retransmit & Fast Recovery -> CWND = SSTHRESH + 3"},
        {"Condition / Event": "Recovery ACK Received", "TCP Tahoe": "Normal Slow Start progression (CWND doubles)", "TCP Reno": "CWND deflated to SSTHRESH -> Direct entry to Congestion Avoidance"},
        {"Condition / Event": "Retransmission Timeout (RTO)", "TCP Tahoe": "SSTHRESH = CWND/2, CWND = 1 MSS, Slow Start", "TCP Reno": "SSTHRESH = CWND/2, CWND = 1 MSS, Slow Start"},
        {"Condition / Event": "Throughput Preservation", "TCP Tahoe": "Low (pipeline emptied on loss)", "TCP Reno": "High (pipe preserved via Fast Recovery)"}
    ]
    st.table(comparison_data)


if __name__ == "__main__":
    main()
