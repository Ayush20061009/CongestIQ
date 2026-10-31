"""
Helper Utilities Module
=======================
Provides common utility functions for platform inspection, safe external command
execution, data formatting, UI components, and Plotly chart generators.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def is_windows() -> bool:
    """Return True if running on a Windows host."""
    return platform.system() == "Windows"


def is_linux() -> bool:
    """Return True if running on a Linux host."""
    return platform.system() == "Linux"


def is_wsl() -> bool:
    """Return True if running inside Windows Subsystem for Linux (WSL)."""
    if not is_linux():
        return False
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            version_info = f.read().lower()
            return "microsoft" in version_info or "wsl" in version_info
    except (FileNotFoundError, PermissionError):
        return False


def check_tool_installed(tool_name: str) -> bool:
    """Check if a command-line tool exists in the current system PATH."""
    return shutil.which(tool_name) is not None


def is_mininet_available() -> bool:
    """Check if Mininet ('mn') is available on the system."""
    return is_linux() and check_tool_installed("mn")


def get_tshark_path() -> Optional[str]:
    """
    Find the TShark binary on the system PATH or standard installation directories.
    Supports Windows standard Program Files locations as well as Unix standard PATH.
    """
    path = shutil.which("tshark")
    if path:
        return path
    if is_windows():
        candidates = [
            r"C:\Program Files\Wireshark\tshark.exe",
            r"C:\Program Files (x86)\Wireshark\tshark.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
    return None


def get_capinfos_path() -> Optional[str]:
    """
    Find the Capinfos binary on the system PATH or standard installation directories.
    """
    path = shutil.which("capinfos")
    if path:
        return path
    if is_windows():
        candidates = [
            r"C:\Program Files\Wireshark\capinfos.exe",
            r"C:\Program Files (x86)\Wireshark\capinfos.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
    return None


def is_tshark_available() -> bool:
    """Check if TShark is installed and accessible in the system PATH or standard locations."""
    return get_tshark_path() is not None


def is_iperf3_available() -> bool:
    """Check if iPerf3 is installed and accessible in the system PATH."""
    return check_tool_installed("iperf3")


def run_safe_command(
    cmd_args: List[str],
    timeout: int = 30,
    check: bool = False
) -> subprocess.CompletedProcess[str]:
    """Safely execute an external command without invoking a shell."""
    if not cmd_args:
        raise ValueError("Command arguments list cannot be empty.")

    return subprocess.run(
        cmd_args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
        shell=False
    )


def format_bitrate(bps: float) -> str:
    """Format bits per second into human-readable metric units."""
    if bps >= 1e9:
        return f"{bps / 1e9:.2f} Gbps"
    elif bps >= 1e6:
        return f"{bps / 1e6:.2f} Mbps"
    elif bps >= 1e3:
        return f"{bps / 1e3:.2f} Kbps"
    return f"{bps:.0f} bps"


def format_bytes(byte_count: int) -> str:
    """Format raw byte counts into human-readable KB, MB, or GB units."""
    if byte_count >= 1024**3:
        return f"{byte_count / (1024**3):.2f} GB"
    elif byte_count >= 1024**2:
        return f"{byte_count / (1024**2):.2f} MB"
    elif byte_count >= 1024:
        return f"{byte_count / 1024:.2f} KB"
    return f"{byte_count} B"


def inject_custom_theme() -> None:
    """
    Inject professional dark engineering UI styles across the Streamlit application.
    Provides glassmorphic cards, crisp technical typography, telemetry status pills,
    modern tabs, and styled inputs.
    """
    st.markdown(
        """
        <style>
        /* Base Dark Background & Typography */
        .stApp {
            background-color: #0b0f19;
            color: #e2e8f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0d1322 !important;
            border-right: 1px solid rgba(148, 163, 184, 0.12) !important;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.25rem !important;
            padding-bottom: 2rem !important;
        }

        /* Technical Headings */
        h1 {
            color: #f8fafc !important;
            font-weight: 700 !important;
            font-size: 1.75rem !important;
            letter-spacing: -0.025em !important;
            line-height: 1.25 !important;
        }
        h2 {
            color: #f1f5f9 !important;
            font-weight: 600 !important;
            font-size: 1.3rem !important;
            letter-spacing: -0.02em !important;
            margin-top: 1.2rem !important;
            margin-bottom: 0.6rem !important;
        }
        h3 {
            color: #e2e8f0 !important;
            font-weight: 600 !important;
            font-size: 1.05rem !important;
            letter-spacing: -0.01em !important;
        }

        /* Metric Cards Styling */
        [data-testid="stMetric"] {
            background: rgba(17, 24, 39, 0.75) !important;
            border: 1px solid rgba(148, 163, 184, 0.15) !important;
            border-radius: 8px !important;
            padding: 0.85rem 1rem !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.25) !important;
            transition: border-color 0.2s ease, transform 0.2s ease;
        }
        [data-testid="stMetric"]:hover {
            border-color: rgba(56, 189, 248, 0.45) !important;
            transform: translateY(-1px);
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.78rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
            color: #94a3b8 !important;
            font-weight: 600 !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
            color: #f8fafc !important;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.8rem !important;
            font-weight: 500 !important;
        }

        /* Form Container */
        [data-testid="stForm"] {
            background: rgba(17, 24, 39, 0.65) !important;
            border: 1px solid rgba(148, 163, 184, 0.16) !important;
            border-radius: 8px !important;
            padding: 1.25rem !important;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25) !important;
        }

        /* Modern Action Buttons */
        .stButton > button {
            background: linear-gradient(180deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            border: 1px solid rgba(56, 189, 248, 0.4) !important;
            border-radius: 6px !important;
            padding: 0.5rem 1.25rem !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2) !important;
        }
        .stButton > button:hover {
            background: linear-gradient(180deg, #0ea5e9 0%, #0284c7 100%) !important;
            border-color: #38bdf8 !important;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.4) !important;
        }
        .stButton > button:active {
            transform: scale(0.99) !important;
        }

        /* Tabs Styling */
        div[data-baseweb="tab-list"] {
            background: rgba(15, 23, 42, 0.75) !important;
            border-radius: 8px !important;
            padding: 4px !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            gap: 4px !important;
        }
        div[data-baseweb="tab"] {
            border-radius: 6px !important;
            color: #94a3b8 !important;
            font-weight: 500 !important;
            font-size: 0.88rem !important;
            padding: 7px 14px !important;
            border: none !important;
            transition: all 0.15s ease !important;
        }
        div[data-baseweb="tab"]:hover {
            color: #f1f5f9 !important;
            background: rgba(255, 255, 255, 0.04) !important;
        }
        div[data-baseweb="tab"][aria-selected="true"] {
            background: rgba(56, 189, 248, 0.15) !important;
            color: #38bdf8 !important;
            font-weight: 600 !important;
            border-bottom: 2px solid #38bdf8 !important;
        }

        /* Dataframe / Table Container */
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }

        /* Expander Styling */
        [data-testid="stExpander"] {
            background: rgba(17, 24, 39, 0.5) !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            border-radius: 8px !important;
            margin-bottom: 0.5rem !important;
        }
        [data-testid="stExpander"] summary {
            font-weight: 600 !important;
            color: #f1f5f9 !important;
        }

        /* File Uploader Dropzone */
        [data-testid="stFileUploaderDropzone"] {
            background: rgba(15, 23, 42, 0.6) !important;
            border: 1px dashed rgba(56, 189, 248, 0.4) !important;
            border-radius: 8px !important;
            padding: 1.5rem !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stFileUploaderDropzone"]:hover {
            border-color: #38bdf8 !important;
            background: rgba(56, 189, 248, 0.06) !important;
        }

        /* Dividers */
        hr {
            border-color: rgba(148, 163, 184, 0.12) !important;
            margin: 1.25rem 0 !important;
        }

        /* Glassmorphic Technical Card */
        .eng-card {
            background: rgba(17, 24, 39, 0.7);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 8px;
            padding: 1.1rem 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: border-color 0.2s ease, transform 0.2s ease;
        }
        .eng-card:hover {
            border-color: rgba(56, 189, 248, 0.35);
        }

        /* Concept Callout Cards */
        .concept-card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(148, 163, 184, 0.12);
            border-left: 4px solid #38bdf8;
            border-radius: 6px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
        }
        .concept-slowstart { border-left-color: #38bdf8; }
        .concept-avoidance { border-left-color: #10b981; }
        .concept-aimd { border-left-color: #60a5fa; }
        .concept-retransmit { border-left-color: #f59e0b; }
        .concept-recovery { border-left-color: #a855f7; }
        .concept-timeout { border-left-color: #ef4444; }

        /* Status Badge Pills */
        .tech-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-right: 4px;
        }
        .badge-cyan { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .badge-emerald { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-amber { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-rose { background: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.3); }
        .badge-purple { background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_project_sidebar() -> None:
    """Render a clean, professional project sidebar across all Streamlit pages."""
    # Inject application-wide custom engineering styling
    inject_custom_theme()

    with st.sidebar:
        # st.markdown(
        #     """
        #     <div style="padding: 0.25rem 0 0.5rem 0;">
        #         <div style="display: flex; align-items: center; gap: 10px;">
        #             <span style="font-size: 1.75rem;">⚡</span>
        #             <div>
        #                 <div style="font-weight: 800; font-size: 1.3rem; color: #f8fafc; letter-spacing: -0.02em; line-height: 1.1;">
        #                     Congest<span style="color: #38bdf8;">IQ</span>
        #                 </div>
        #                 <div style="font-size: 0.68rem; color: #38bdf8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px;">
        #                     Understand • Simulate • Optimise
        #                 </div>
        #             </div>
        #         </div>
        #         <div style="font-size: 0.72rem; color: #94a3b8; font-weight: 400; margin-top: 6px; line-height: 1.3;">
        #             TCP Congestion Control & Network Intelligence Platform
        #         </div>
        #     </div>
        #     """,
        #     unsafe_allow_html=True
        # )

        # st.divider()


        # Session State Status
        st.markdown("#### ⚡ Active Telemetry")
        has_state = False

        if "latest_simulation" in st.session_state:
            latest = st.session_state["latest_simulation"]
            st.success(f"**Simulation**: TCP {latest['algorithm']}")
            st.caption(f"Peak: `{latest['peak_cwnd']:.1f} MSS` | Avg: `{latest['average_cwnd']:.2f} MSS`")
            has_state = True

        if "latest_experiment_result" in st.session_state:
            exp = st.session_state["latest_experiment_result"]
            if getattr(exp, "status", "") == "Completed":
                st.info(f"**Emulation**: `{exp.measured_throughput_mbps:.2f} Mbps`")
                st.caption(f"Cap: `{exp.configured_bandwidth_mbps:.1f} Mbps` | Loss: `{exp.configured_loss_percentage:.1f}%`")
                has_state = True

        if "latest_packet_analysis" in st.session_state:
            pkt = st.session_state["latest_packet_analysis"]
            if getattr(pkt, "total_tcp_packets", 0) > 0:
                st.warning(f"**Capture**: `{pkt.total_tcp_packets:,}` TCP Pkts")
                st.caption(f"Retrans: `{pkt.retransmission_rate:.1f}%` | Dup ACK: `{pkt.duplicate_ack_rate:.1f}%`")
                has_state = True

        if not has_state:
            st.caption("No session data logged yet. Run a simulation or network emulation.")

        st.divider()
        

def render_phase_status_banner(
    phase_number: int,
    phase_title: str,
    description: str
) -> None:
    """Render a clean informational banner indicating page status."""
    st.info(
        f"**Phase {phase_number}: {phase_title}**\n\n"
        f"{description}"
    )


def render_environment_badges() -> None:
    """Render a status card showing platform diagnostics and tool availability."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        os_name = platform.system()
        wsl_badge = " (WSL)" if is_wsl() else ""
        st.metric("Operating System", f"{os_name}{wsl_badge}")

    with col2:
        python_ver = platform.python_version()
        st.metric("Python Version", python_ver)

    with col3:
        st.metric("Network Emulator", "Python Native (Windows 10 Ready)")

    with col4:
        tshark_status = "Installed" if is_tshark_available() else "Not on PATH"
        st.metric("TShark / Wireshark", tshark_status)


# ==============================================================================
# PLOTLY INTERACTIVE CHART BUILDERS (PHASE 4)
# ==============================================================================

# Common Dark Theme Layout Template
CHART_DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(13, 19, 34, 0.95)",
    plot_bgcolor="rgba(17, 24, 39, 0.65)",
    font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", size=12, color="#cbd5e1"),
    margin=dict(l=50, r=40, t=50, b=50),
    xaxis=dict(
        showgrid=True,
        gridcolor="rgba(148, 163, 184, 0.10)",
        zeroline=False,
        dtick=5,
        title_font=dict(size=12, color="#94a3b8")
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="rgba(148, 163, 184, 0.10)",
        zeroline=False,
        title_font=dict(size=12, color="#94a3b8")
    ),
    legend=dict(
        bgcolor="rgba(17, 24, 39, 0.85)",
        bordercolor="rgba(148, 163, 184, 0.18)",
        borderwidth=1,
        font=dict(size=11, color="#cbd5e1")
    ),
    hoverlabel=dict(
        bgcolor="rgba(15, 23, 42, 0.95)",
        bordercolor="rgba(56, 189, 248, 0.4)",
        font_size=12,
        font_family="-apple-system, BlinkMacSystemFont, sans-serif"
    )
)


def build_cwnd_progression_chart(df: pd.DataFrame, algorithm: str) -> go.Figure:
    """
    Build an interactive Plotly line chart displaying CWND progression and SSTHRESH.
    Includes custom tooltips, loss markers, and zoom/hover support.
    """
    if df is None or df.empty:
        return go.Figure()

    fig = go.Figure()

    # 1. Congestion Window (CWND) Line Trace
    custom_data = list(zip(df["TCP_State"], df["Loss_Event"], df["Action"], df["SSTHRESH"]))
    fig.add_trace(go.Scatter(
        x=df["RTT_Round"],
        y=df["CWND"],
        mode="lines+markers",
        name=f"TCP {algorithm} CWND",
        line=dict(color="#38bdf8", width=3),
        marker=dict(size=7, color="#38bdf8", symbol="circle"),
        customdata=custom_data,
        hovertemplate=(
            "<b>RTT Round: %{x}</b><br>"
            "CWND: <b>%{y:.1f} MSS</b><br>"
            "SSTHRESH: %{customdata[3]:.1f} MSS<br>"
            "State: %{customdata[0]}<br>"
            "Event: %{customdata[1]}<br>"
            "Action: %{customdata[2]}<extra></extra>"
        )
    ))

    # 2. SSTHRESH Threshold Line Trace
    fig.add_trace(go.Scatter(
        x=df["RTT_Round"],
        y=df["SSTHRESH"],
        mode="lines",
        name="SSTHRESH Threshold",
        line=dict(color="#f59e0b", width=2, dash="dash"),
        hovertemplate="Round %{x}: SSTHRESH = %{y:.1f} MSS<extra></extra>"
    ))

    # 3. Loss Event Markers (Triple Dup ACKs and Timeouts)
    loss_steps = df[df["Loss_Event"] != "None"]
    if not loss_steps.empty:
        # Separate Triple Duplicate ACKs vs Timeouts
        dup_acks = loss_steps[loss_steps["Loss_Event"].str.contains("Duplicate", case=False, na=False)]
        timeouts = loss_steps[loss_steps["Loss_Event"].str.contains("Timeout", case=False, na=False)]

        if not dup_acks.empty:
            fig.add_trace(go.Scatter(
                x=dup_acks["RTT_Round"],
                y=dup_acks["CWND"],
                mode="markers",
                name="3 Duplicate ACKs Event",
                marker=dict(symbol="triangle-down", size=14, color="#f97316", line=dict(color="#ffffff", width=1.5)),
                hovertemplate="<b>[LOSS] 3 Duplicate ACKs</b><br>Round: %{x}<br>Resulting CWND: %{y:.1f} MSS<extra></extra>"
            ))

        if not timeouts.empty:
            fig.add_trace(go.Scatter(
                x=timeouts["RTT_Round"],
                y=timeouts["CWND"],
                mode="markers",
                name="RTO Timeout Event",
                marker=dict(symbol="x", size=14, color="#ef4444", line=dict(color="#ffffff", width=2)),
                hovertemplate="<b>[LOSS] Timeout (RTO)</b><br>Round: %{x}<br>CWND Reset: %{y:.1f} MSS<extra></extra>"
            ))

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title=f"<b>TCP {algorithm} — Congestion Window (CWND) & SSTHRESH Progression</b>",
        xaxis_title="Simulation Round (RTT)",
        yaxis_title="Window Size (MSS)"
    )

    return fig


def build_ssthresh_chart(df: pd.DataFrame, algorithm: str) -> go.Figure:
    """
    Build a dedicated Plotly line chart displaying SSTHRESH progression over time.
    Shows threshold plateaus and halving points following packet loss.
    """
    if df is None or df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["RTT_Round"],
        y=df["SSTHRESH"],
        mode="lines+markers",
        name="SSTHRESH Level",
        line=dict(color="#fbbf24", width=3, shape="hv"),  # stepped shape for threshold plateaus
        marker=dict(size=6, color="#fbbf24"),
        fill="tozeroy",
        fillcolor="rgba(251, 191, 36, 0.08)",
        hovertemplate="Round %{x}: SSTHRESH = <b>%{y:.1f} MSS</b><extra></extra>"
    ))

    # Add markers for rounds where SSTHRESH changed
    ssthresh_changes = []
    prev_thresh = None
    for _, row in df.iterrows():
        cur_thresh = row["SSTHRESH"]
        if prev_thresh is not None and cur_thresh != prev_thresh:
            ssthresh_changes.append(row)
        prev_thresh = cur_thresh

    if ssthresh_changes:
        ch_df = pd.DataFrame(ssthresh_changes)
        fig.add_trace(go.Scatter(
            x=ch_df["RTT_Round"],
            y=ch_df["SSTHRESH"],
            mode="markers",
            name="Threshold Reduction Point",
            marker=dict(size=12, color="#ef4444", symbol="diamond"),
            hovertemplate="<b>SSTHRESH Halved</b><br>Round: %{x}<br>New Threshold: %{y:.1f} MSS<extra></extra>"
        ))

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title=f"<b>TCP {algorithm} — Slow Start Threshold (SSTHRESH) Evolution</b>",
        xaxis_title="Simulation Round (RTT)",
        yaxis_title="SSTHRESH (MSS)"
    )

    return fig


def build_tcp_state_timeline_chart(df: pd.DataFrame, algorithm: str) -> go.Figure:
    """
    Build a visual state transition timeline over RTT rounds.
    Color codes Slow Start, Congestion Avoidance, and Fast Recovery.
    """
    if df is None or df.empty:
        return go.Figure()

    fig = go.Figure()

    state_colors = {
        "Slow Start": "#38bdf8",           # Cyan
        "Congestion Avoidance": "#34d399", # Emerald Green
        "Fast Recovery": "#f59e0b"         # Amber
    }

    # Plot step lines for each state group
    for state_name, color in state_colors.items():
        subset = df[df["TCP_State"] == state_name]
        if not subset.empty:
            fig.add_trace(go.Scatter(
                x=subset["RTT_Round"],
                y=subset["TCP_State"],
                mode="markers",
                name=state_name,
                marker=dict(size=10, color=color, symbol="circle"),
                hovertemplate="Round %{x}: <b>%{y}</b><extra></extra>"
            ))

    # Add connecting line across all rounds
    fig.add_trace(go.Scatter(
        x=df["RTT_Round"],
        y=df["TCP_State"],
        mode="lines",
        name="State Path",
        line=dict(color="rgba(148, 163, 184, 0.4)", width=2, shape="hv"),
        hoverinfo="skip"
    ))

    layout = dict(CHART_DARK_LAYOUT)
    layout["yaxis"] = {
        **CHART_DARK_LAYOUT.get("yaxis", {}),
        "categoryorder": "array",
        "categoryarray": ["Slow Start", "Congestion Avoidance", "Fast Recovery"],
        "showgrid": True,
        "gridcolor": "rgba(148, 163, 184, 0.15)"
    }

    fig.update_layout(
        **layout,
        title=f"<b>TCP {algorithm} — State Machine Transitions Timeline</b>",
        xaxis_title="Simulation Round (RTT)",
        yaxis_title="TCP State"
    )

    return fig


def build_comparison_cwnd_chart(comp_df: pd.DataFrame) -> go.Figure:
    """
    Build a dual-line comparative Plotly chart comparing TCP Tahoe and TCP Reno CWND.
    Clearly shows Reno's Fast Recovery throughput preservation over Tahoe's 1.0 MSS reset.
    """
    if comp_df is None or comp_df.empty:
        return go.Figure()

    fig = go.Figure()

    # Tahoe CWND Trace
    fig.add_trace(go.Scatter(
        x=comp_df["RTT_Round"],
        y=comp_df["Tahoe_CWND"],
        mode="lines+markers",
        name="TCP Tahoe CWND",
        line=dict(color="#60a5fa", width=3),
        marker=dict(size=6, color="#60a5fa"),
        customdata=list(zip(comp_df["Tahoe_State"], comp_df["Tahoe_Action"])),
        hovertemplate=(
            "<b>Round %{x} (Tahoe)</b><br>"
            "CWND: <b>%{y:.1f} MSS</b><br>"
            "State: %{customdata[0]}<br>"
            "Action: %{customdata[1]}<extra></extra>"
        )
    ))

    # Reno CWND Trace
    fig.add_trace(go.Scatter(
        x=comp_df["RTT_Round"],
        y=comp_df["Reno_CWND"],
        mode="lines+markers",
        name="TCP Reno CWND",
        line=dict(color="#34d399", width=3),
        marker=dict(size=6, color="#34d399"),
        customdata=list(zip(comp_df["Reno_State"], comp_df["Reno_Action"], comp_df["CWND_Difference"])),
        hovertemplate=(
            "<b>Round %{x} (Reno)</b><br>"
            "CWND: <b>%{y:.1f} MSS</b><br>"
            "State: %{customdata[0]}<br>"
            "Reno Lead: +%{customdata[2]:.1f} MSS<br>"
            "Action: %{customdata[1]}<extra></extra>"
        )
    ))

    # Loss Event Injected Points
    loss_steps = comp_df[comp_df["Loss_Event"] != "None"]
    if not loss_steps.empty:
        fig.add_trace(go.Scatter(
            x=loss_steps["RTT_Round"],
            y=loss_steps["Reno_CWND"],
            mode="markers",
            name="Injected Loss Event",
            marker=dict(symbol="triangle-down", size=14, color="#ef4444", line=dict(color="#ffffff", width=1.5)),
            customdata=list(zip(loss_steps["Loss_Event"], loss_steps["Tahoe_CWND"])),
            hovertemplate=(
                "<b>[LOSS EVENT] %{customdata[0]}</b><br>"
                "Round %{x}<br>"
                "Tahoe Dropped to: %{customdata[1]:.1f} MSS<br>"
                "Reno Reacted to: %{y:.1f} MSS<extra></extra>"
            )
        ))

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title="<b>TCP Tahoe vs. TCP Reno — Congestion Window (CWND) Side-by-Side</b>",
        xaxis_title="Simulation Round (RTT)",
        yaxis_title="Congestion Window (MSS)"
    )

    return fig


def build_comparison_ssthresh_chart(comp_df: pd.DataFrame) -> go.Figure:
    """Build comparative SSTHRESH chart comparing Tahoe and Reno threshold changes."""
    if comp_df is None or comp_df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=comp_df["RTT_Round"],
        y=comp_df["Tahoe_SSTHRESH"],
        mode="lines+markers",
        name="Tahoe SSTHRESH",
        line=dict(color="#93c5fd", width=2.5, dash="dash", shape="hv"),
        marker=dict(size=5),
        hovertemplate="Round %{x} (Tahoe SSTHRESH): %{y:.1f} MSS<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=comp_df["RTT_Round"],
        y=comp_df["Reno_SSTHRESH"],
        mode="lines+markers",
        name="Reno SSTHRESH",
        line=dict(color="#a7f3d0", width=2.5, dash="dot", shape="hv"),
        marker=dict(size=5),
        hovertemplate="Round %{x} (Reno SSTHRESH): %{y:.1f} MSS<extra></extra>"
    ))

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title="<b>TCP Tahoe vs. TCP Reno — SSTHRESH Progression Comparison</b>",
        xaxis_title="Simulation Round (RTT)",
        yaxis_title="SSTHRESH (MSS)"
    )

    return fig


def build_comparison_state_chart(comp_df: pd.DataFrame) -> go.Figure:
    """Build side-by-side state comparison chart showing state divergence after loss."""
    if comp_df is None or comp_df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=comp_df["RTT_Round"],
        y=comp_df["Tahoe_State"],
        mode="lines+markers",
        name="TCP Tahoe State",
        line=dict(color="#60a5fa", width=2.5, shape="hv"),
        marker=dict(size=8, symbol="circle"),
        hovertemplate="Round %{x}: Tahoe in <b>%{y}</b><extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=comp_df["RTT_Round"],
        y=comp_df["Reno_State"],
        mode="lines+markers",
        name="TCP Reno State",
        line=dict(color="#34d399", width=2.5, shape="hv"),
        marker=dict(size=8, symbol="square"),
        hovertemplate="Round %{x}: Reno in <b>%{y}</b><extra></extra>"
    ))

    layout = dict(CHART_DARK_LAYOUT)
    layout["yaxis"] = {
        **CHART_DARK_LAYOUT.get("yaxis", {}),
        "categoryorder": "array",
        "categoryarray": ["Slow Start", "Congestion Avoidance", "Fast Recovery"],
        "showgrid": True,
        "gridcolor": "rgba(148, 163, 184, 0.15)"
    }

    fig.update_layout(
        **layout,
        title="<b>TCP Tahoe vs. TCP Reno — State Machine Divergence</b>",
        xaxis_title="Simulation Round (RTT)",
        yaxis_title="Operating TCP State"
    )

    return fig


def build_tcp_flags_chart(flag_counts: Dict[str, int]) -> go.Figure:
    """
    Build a Plotly bar chart displaying the frequency of each TCP control flag.
    Includes custom color-coding for standard TCP flags (SYN, ACK, FIN, RST, PSH, URG, ECE, CWR).
    """
    if not flag_counts or all(v == 0 for v in flag_counts.values()):
        fig = go.Figure()
        fig.update_layout(
            **CHART_DARK_LAYOUT,
            title="<b>TCP Control Flags Distribution (No Active Flags Detected)</b>",
            xaxis_title="TCP Control Flag",
            yaxis_title="Packet Count"
        )
        return fig

    flags = list(flag_counts.keys())
    counts = [flag_counts[f] for f in flags]

    # Semantic flag palette
    palette = {
        "SYN": "#38bdf8",  # Sky blue (Connection establishment)
        "ACK": "#10b981",  # Emerald green (Acknowledgement)
        "FIN": "#a855f7",  # Purple (Orderly connection teardown)
        "RST": "#ef4444",  # Crimson red (Abortive reset)
        "PSH": "#f59e0b",  # Amber (Immediate push to application)
        "URG": "#ec4899",  # Pink (Urgent pointer)
        "ECE": "#6366f1",  # Indigo (ECN Echo - Explicit Congestion)
        "CWR": "#14b8a6"   # Teal (Congestion Window Reduced)
    }
    bar_colors = [palette.get(f, "#94a3b8") for f in flags]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=flags,
        y=counts,
        marker=dict(color=bar_colors, line=dict(color="#ffffff", width=1)),
        text=counts,
        textposition="outside",
        hovertemplate="Flag: <b>%{x}</b><br>Occurrences: <b>%{y} packets</b><extra></extra>"
    ))

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title="<b>TCP Control Flags Distribution in Capture</b>",
        xaxis_title="TCP Control Flag",
        yaxis_title="Number of Packets Containing Flag",
        showlegend=False
    )
    return fig


def build_packet_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """
    Build a Plotly time-series histogram displaying packet arrival density over capture duration.
    """
    if df is None or df.empty or "timestamp" not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            **CHART_DARK_LAYOUT,
            title="<b>Packet Activity Over Time (No Data Available)</b>",
            xaxis_title="Time (seconds)",
            yaxis_title="Packet Count"
        )
        return fig

    nbins = max(10, min(60, len(df) // 10)) if len(df) > 10 else 10

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df["timestamp"],
        nbinsx=nbins,
        marker=dict(
            color="#38bdf8",
            line=dict(color="rgba(148, 163, 184, 0.4)", width=1)
        ),
        hovertemplate="Time Interval: <b>%{x}s</b><br>Packets: <b>%{y}</b><extra></extra>"
    ))

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title="<b>Packet Transmission Rate Over Time</b>",
        xaxis_title="Relative Capture Timestamp (seconds)",
        yaxis_title="Packets per Bin",
        showlegend=False
    )
    return fig


def build_retransmission_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """
    Build a Plotly scatter timeline highlighting Retransmission and Duplicate ACK events.
    """
    if df is None or df.empty or "timestamp" not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            **CHART_DARK_LAYOUT,
            title="<b>Congestion & Loss Timeline (No Data Available)</b>",
            xaxis_title="Time (seconds)",
            yaxis_title="Packet Frame #"
        )
        return fig

    fig = go.Figure()

    # 1. Normal packets background
    normal_df = df[~(df["is_retransmission"]) & ~(df["is_duplicate_ack"])]
    if not normal_df.empty:
        fig.add_trace(go.Scatter(
            x=normal_df["timestamp"],
            y=normal_df["packet_id"],
            mode="markers",
            name="Normal Segment",
            marker=dict(size=4, color="rgba(148, 163, 184, 0.35)"),
            hovertemplate="Frame: <b>%{y}</b><br>Time: %{x:.4f}s<extra></extra>"
        ))

    # 2. Duplicate ACK markers
    dup_acks = df[df["is_duplicate_ack"]]
    if not dup_acks.empty:
        fig.add_trace(go.Scatter(
            x=dup_acks["timestamp"],
            y=dup_acks["packet_id"],
            mode="markers",
            name="Duplicate ACK",
            marker=dict(size=9, color="#f59e0b", symbol="triangle-up", line=dict(color="#ffffff", width=1)),
            hovertemplate="<b>[EVENT] Duplicate ACK</b><br>Frame: %{y}<br>Time: %{x:.4f}s<br>Ack: %{text}<extra></extra>",
            text=dup_acks["ack_number"]
        ))

    # 3. Retransmission markers
    retrans = df[df["is_retransmission"]]
    if not retrans.empty:
        fig.add_trace(go.Scatter(
            x=retrans["timestamp"],
            y=retrans["packet_id"],
            mode="markers",
            name="Retransmission",
            marker=dict(size=11, color="#ef4444", symbol="diamond", line=dict(color="#ffffff", width=1.5)),
            hovertemplate="<b>[LOSS] Retransmission</b><br>Frame: %{y}<br>Time: %{x:.4f}s<br>Seq: %{text}<extra></extra>",
            text=retrans["seq_number"]
        ))

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title="<b>Packet Timeline with Retransmissions & Duplicate ACKs</b>",
        xaxis_title="Relative Capture Timestamp (seconds)",
        yaxis_title="Frame Number"
    )
    return fig


def build_seq_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """
    Build a Time-Sequence (tcptrace style) plot tracing TCP Sequence progression.
    Highlights packet retransmissions and demonstrates transmission slope (throughput).
    """
    if df is None or df.empty or "seq_number" not in df.columns or "timestamp" not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            **CHART_DARK_LAYOUT,
            title="<b>Time-Sequence (tcptrace) Graph (No Data Available)</b>",
            xaxis_title="Time (seconds)",
            yaxis_title="Sequence Number"
        )
        return fig

    # Filter for segments carrying payload or sequence tracking
    fig = go.Figure()

    normal = df[~df["is_retransmission"]]
    retrans = df[df["is_retransmission"]]

    if not normal.empty:
        fig.add_trace(go.Scatter(
            x=normal["timestamp"],
            y=normal["seq_number"],
            mode="markers",
            name="Transmitted Segments",
            marker=dict(size=5, color="#38bdf8", opacity=0.7),
            hovertemplate="Frame: %{customdata}<br>Time: %{x:.4f}s<br>Seq: <b>%{y}</b><extra></extra>",
            customdata=normal["packet_id"]
        ))

    if not retrans.empty:
        fig.add_trace(go.Scatter(
            x=retrans["timestamp"],
            y=retrans["seq_number"],
            mode="markers",
            name="Retransmitted Segments",
            marker=dict(size=9, color="#ef4444", symbol="x", line=dict(color="#ffffff", width=1.5)),
            hovertemplate="<b>[RETRANSMISSION]</b><br>Frame: %{customdata}<br>Time: %{x:.4f}s<br>Seq: <b>%{y}</b><extra></extra>",
            customdata=retrans["packet_id"]
        ))

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title="<b>TCP Time-Sequence Graph (Progression & Retransmissions)</b>",
        xaxis_title="Relative Capture Timestamp (seconds)",
        yaxis_title="TCP Sequence Number (Bytes / Relative)"
    )
    return fig


def calculate_simulation_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate comprehensive performance analytics from a completed TCP simulation DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Simulation rounds trace DataFrame with columns:
        ['RTT_Round', 'CWND', 'SSTHRESH', 'TCP_State', 'Loss_Event', 'Retransmission']

    Returns
    -------
    Dict[str, Any]
        Dictionary of key metrics: avg_cwnd, peak_cwnd, min_cwnd, final_cwnd,
        state_counts, state_percentages, loss_event_count, retransmissions, etc.
    """
    if df is None or df.empty:
        return {
            "total_rounds": 0,
            "average_cwnd": 0.0,
            "peak_cwnd": 0.0,
            "min_cwnd": 0.0,
            "final_cwnd": 0.0,
            "initial_ssthresh": 0.0,
            "final_ssthresh": 0.0,
            "total_loss_events": 0,
            "total_retransmissions": 0,
            "final_state": "N/A",
            "state_counts": {},
            "state_percentages": {},
            "ssthresh_changes": 0
        }

    total_rounds = len(df)
    avg_cwnd = round(float(df["CWND"].mean()), 2)
    peak_cwnd = round(float(df["CWND"].max()), 1)
    min_cwnd = round(float(df["CWND"].min()), 1)
    final_cwnd = round(float(df.iloc[-1]["CWND"]), 1)
    initial_ssthresh = round(float(df.iloc[0]["SSTHRESH"]), 1)
    final_ssthresh = round(float(df.iloc[-1]["SSTHRESH"]), 1)

    loss_events = int(len(df[df["Loss_Event"] != "None"])) if "Loss_Event" in df.columns else 0
    retransmissions = int(df["Retransmission"].sum()) if "Retransmission" in df.columns else 0
    final_state = str(df.iloc[-1]["TCP_State"]) if "TCP_State" in df.columns else "Unknown"

    state_counts = df["TCP_State"].value_counts().to_dict() if "TCP_State" in df.columns else {}
    state_percentages = {
        state: round((count / total_rounds) * 100.0, 1)
        for state, count in state_counts.items()
    }

    # Count rounds where SSTHRESH changed
    ssthresh_changes = 0
    if "SSTHRESH" in df.columns and len(df) > 1:
        diffs = df["SSTHRESH"].diff().fillna(0)
        ssthresh_changes = int((diffs != 0).sum())

    return {
        "total_rounds": total_rounds,
        "average_cwnd": avg_cwnd,
        "peak_cwnd": peak_cwnd,
        "min_cwnd": min_cwnd,
        "final_cwnd": final_cwnd,
        "initial_ssthresh": initial_ssthresh,
        "final_ssthresh": final_ssthresh,
        "total_loss_events": loss_events,
        "total_retransmissions": retransmissions,
        "final_state": final_state,
        "state_counts": state_counts,
        "state_percentages": state_percentages,
        "ssthresh_changes": ssthresh_changes
    }


def build_state_residency_chart(state_counts: Dict[str, int]) -> go.Figure:
    """
    Build a Plotly donut chart displaying the distribution of RTT rounds spent in each TCP state.
    """
    if not state_counts or all(v == 0 for v in state_counts.values()):
        fig = go.Figure()
        fig.update_layout(
            **CHART_DARK_LAYOUT,
            title="<b>TCP State Residency (No Data)</b>"
        )
        return fig

    labels = list(state_counts.keys())
    values = [state_counts[k] for k in labels]

    color_map = {
        "Slow Start": "#38bdf8",
        "Congestion Avoidance": "#10b981",
        "Fast Recovery": "#f59e0b"
    }
    colors = [color_map.get(lbl, "#94a3b8") for lbl in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(colors=colors, line=dict(color="#0f172a", width=2)),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Rounds: %{value} (%{percent})<extra></extra>"
    )])

    fig.update_layout(
        **CHART_DARK_LAYOUT,
        title="<b>TCP State Machine Residency (RTT Rounds)</b>",
        showlegend=True
    )
    return fig


def build_multi_experiment_chart(
    history_df: pd.DataFrame,
    x_axis_col: str,
    x_title: str,
    chart_title: str
) -> go.Figure:
    """
    Build a Plotly comparative chart across multiple Mininet / iPerf3 experimental runs.
    Correlates an independent link variable (Bandwidth, Delay, Loss) against measured throughput.
    """
    if history_df is None or history_df.empty or x_axis_col not in history_df.columns:
        fig = go.Figure()
        fig.update_layout(
            **CHART_DARK_LAYOUT,
            title=f"<b>{chart_title} (No Experiments Recorded)</b>"
        )
        return fig

    df_sorted = history_df.sort_values(by=x_axis_col)

    fig = go.Figure()

    # Measured Throughput Bar
    fig.add_trace(go.Bar(
        x=df_sorted[x_axis_col].astype(str),
        y=df_sorted["Measured_Throughput_Mbps"],
        name="Measured Throughput",
        marker=dict(color="#38bdf8", line=dict(color="#ffffff", width=1)),
        text=df_sorted["Measured_Throughput_Mbps"].round(1),
        textposition="outside",
        hovertemplate=(
            f"<b>{x_title}: %{{x}}</b><br>"
            "Measured Throughput: <b>%{y:.2f} Mbps</b><extra></extra>"
        )
    ))

    # If x-axis is not bandwidth, also plot Configured Bandwidth as a reference line
    if x_axis_col != "Configured_Bandwidth_Mbps" and "Configured_Bandwidth_Mbps" in df_sorted.columns:
        fig.add_trace(go.Scatter(
            x=df_sorted[x_axis_col].astype(str),
            y=df_sorted["Configured_Bandwidth_Mbps"],
            mode="lines+markers",
            name="Configured Bottleneck Bandwidth",
            line=dict(color="#f59e0b", width=2, dash="dash"),
            hovertemplate="Link Capacity: %{y:.1f} Mbps<extra></extra>"
        ))

    layout = dict(CHART_DARK_LAYOUT)
    layout["legend"] = {
        **CHART_DARK_LAYOUT.get("legend", {}),
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "right",
        "x": 1
    }

    fig.update_layout(
        **layout,
        title=f"<b>{chart_title}</b>",
        xaxis_title=x_title,
        yaxis_title="Throughput (Mbps)"
    )
    return fig


def generate_automatic_performance_insights(
    sim_metrics: Optional[Dict[str, Any]] = None,
    comp_summary: Optional[Dict[str, Any]] = None,
    exp_result: Optional[Any] = None,
    pkt_summary: Optional[Any] = None
) -> List[Dict[str, str]]:
    """
    Generate dynamic, data-driven technical insights based on completed simulation,
    network experiment, and packet analysis runs.
    Strictly avoids hardcoded assumptions and adheres to scientific data integrity.
    """
    insights: List[Dict[str, str]] = []

    # 1. Simulation Insights
    if sim_metrics and sim_metrics.get("total_rounds", 0) > 0:
        rounds = sim_metrics["total_rounds"]
        avg_cwnd = sim_metrics["average_cwnd"]
        peak_cwnd = sim_metrics["peak_cwnd"]
        final_cwnd = sim_metrics["final_cwnd"]
        losses = sim_metrics["total_loss_events"]
        state_pcts = sim_metrics.get("state_percentages", {})
        ca_pct = state_pcts.get("Congestion Avoidance", 0.0)
        ss_pct = state_pcts.get("Slow Start", 0.0)

        loss_str = (
            f"Encountered {losses} congestion event(s), triggering window reductions. "
            f"The window concluded at {final_cwnd:.1f} MSS."
            if losses > 0 else
            "No packet loss events occurred; the window grew continuously without reduction."
        )

        insights.append({
            "category": "Simulation Dynamics",
            "title": f"Window Evolution over {rounds} RTT Rounds",
            "body": (
                f"The simulation reached a peak window of {peak_cwnd:.1f} MSS with an average of {avg_cwnd:.2f} MSS. "
                f"The protocol spent {ca_pct:.1f}% of execution time in Congestion Avoidance and {ss_pct:.1f}% in Slow Start. "
                f"{loss_str}"
            )
        })

    # 2. Tahoe vs Reno Comparison Insights
    if comp_summary:
        tahoe_avg = comp_summary.get("tahoe_average_cwnd", 0.0)
        reno_avg = comp_summary.get("reno_average_cwnd", 0.0)
        reno_adv = comp_summary.get("reno_throughput_advantage_percent", 0.0)

        if reno_adv > 0:
            comp_body = (
                f"TCP Reno achieved a {reno_adv:.1f}% higher average CWND ({reno_avg:.2f} MSS vs {tahoe_avg:.2f} MSS) "
                f"by leveraging Fast Retransmit and Fast Recovery to maintain pipeline transmission during packet loss, "
                f"whereas TCP Tahoe suffered pipeline-draining penalties by dropping to 1 MSS."
            )
        elif reno_adv < 0:
            comp_body = (
                f"Under this specific configuration, TCP Tahoe achieved a higher average window ({tahoe_avg:.2f} MSS vs {reno_avg:.2f} MSS). "
                f"This can occur when timeouts dominate over duplicate ACKs or when window limits constrain recovery."
            )
        else:
            comp_body = f"Both algorithms achieved equivalent average window sizes ({tahoe_avg:.2f} MSS)."

        insights.append({
            "category": "Comparative Analysis",
            "title": "Tahoe vs. Reno Algorithmic Divergence",
            "body": comp_body
        })

    # 3. Real Network Experiment Insights
    if exp_result and getattr(exp_result, "status", "") == "Completed":
        meas_tp = exp_result.measured_throughput_mbps
        cfg_bw = exp_result.configured_bandwidth_mbps
        cfg_loss = exp_result.configured_loss_percentage
        retrans = exp_result.measured_retransmissions
        eff = (meas_tp / cfg_bw * 100.0) if cfg_bw > 0 else 0.0

        loss_note = (
            f"Under {cfg_loss:.1f}% synthetic link packet loss, the sender logged {retrans} retransmissions."
            if cfg_loss > 0 else
            "Under zero artificial packet loss, the connection achieved stable throughput."
        )

        insights.append({
            "category": "Empirical Network Performance",
            "title": f"Simulated Link Utilization ({eff:.1f}%)",
            "body": (
                f"The network emulation transfer achieved a simulated goodput of {meas_tp:.2f} Mbps across a {cfg_bw:.1f} Mbps link. "
                f"{loss_note} "
                f"Note: Results are generated by the Python network emulator simulating packet transmission, queueing, and TCP {exp_result.tcp_congestion_algorithm.upper()} dynamics."
            )
        })

    # 4. Packet Analysis Insights
    if pkt_summary and getattr(pkt_summary, "total_tcp_packets", 0) > 0:
        total_tcp = pkt_summary.total_tcp_packets
        retrans_rate = pkt_summary.retransmission_rate
        dup_rate = pkt_summary.duplicate_ack_rate
        fn = pkt_summary.filename

        insights.append({
            "category": "Wire Packet Capture Dissection",
            "title": f"Packet Inspection of '{fn}'",
            "body": (
                f"Dissected {total_tcp:,} TCP frames with an observed retransmission rate of {retrans_rate:.2f}% "
                f"and duplicate ACK rate of {dup_rate:.2f}%. "
                f"Engineering context: Retransmissions on the wire indicate sender recovery actions, but do not directly "
                f"reveal internal kernel variables like CWND or SSTHRESH."
            )
        })

    return insights

