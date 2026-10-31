"""
Test Suite: TCP Congestion Control & Architecture Tests
======================================================
Validates:
- Slow Start exponential growth
- Congestion Avoidance linear growth (AIMD)
- TCP Tahoe 3-duplicate-ACK and Timeout state transitions
- TCP Reno Fast Retransmit and Fast Recovery state transitions
- Timeout handling for both algorithms
- Multiple congestion events and recovery cycles
- Input validation and boundary enforcement
- Maximum CWND capping
- Random seed reproducibility
- Schema compliance and DataFrame column completeness
- Algorithm comparative metrics
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager

try:
    import pytest
except ImportError:
    pytest = None

@contextmanager
def dummy_raises(expected_exception, match=None):
    try:
        yield
    except expected_exception as e:
        if match and match not in str(e):
            raise AssertionError(f"Pattern '{match}' not found in exception message '{e}'")
    else:
        raise AssertionError(f"Expected {expected_exception} was not raised.")

class FakePytest:
    raises = staticmethod(dummy_raises)

if pytest is None:
    pytest = FakePytest

import pandas as pd

# Add project root to sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.congestion_control import (
    SimulationParameters,
    SimulationStep,
    SimulationResult,
    TCPState,
    LossEventType,
    TCPTahoe,
    TCPReno,
    BaseTCPCongestionControl,
    simulate_tcp,
    compare_algorithms,
)
from core.network_simulation import (
    NetworkExperimentConfig,
    ExperimentResult,
    NetworkExperimentManager,
    PythonNetworkEmulator,
    parse_iperf3_json,
    calculate_experiment_throughput,
    calculate_throughput_efficiency,
    save_experiment_history,
    load_experiment_history,
)
from core.packet_analysis import (
    PacketRecord,
    PacketAnalysisSummary,
    PacketAnalyzer,
    validate_capture_file,
)
import tempfile
import subprocess
from unittest.mock import patch
from utils.helpers import (
    is_windows,
    is_linux,
    format_bitrate,
    format_bytes,
    calculate_simulation_metrics,
    build_state_residency_chart,
    build_multi_experiment_chart,
    build_tcp_state_timeline_chart,
    build_comparison_state_chart,
    generate_automatic_performance_insights,
)


class TestSimulationParametersValidation:
    """Tests parameter validation for congestion control simulations."""

    def test_default_parameters_are_valid(self):
        params = SimulationParameters()
        params.validate()
        assert params.algorithm == "Tahoe"
        assert params.initial_cwnd == 1.0
        assert params.initial_ssthresh == 16.0
        assert params.num_rounds == 30
        assert params.mss == 1460
        assert params.max_cwnd == 64.0

    def test_invalid_algorithm_raises_error(self):
        params = SimulationParameters(algorithm="Vegas")
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            params.validate()

    def test_negative_or_zero_cwnd_raises_error(self):
        with pytest.raises(ValueError, match="initial_cwnd must be greater than 0"):
            SimulationParameters(initial_cwnd=-2.0).validate()
        with pytest.raises(ValueError, match="initial_cwnd must be greater than 0"):
            SimulationParameters(initial_cwnd=0.0).validate()

    def test_zero_or_negative_ssthresh_raises_error(self):
        with pytest.raises(ValueError, match="initial_ssthresh must be greater than 0"):
            SimulationParameters(initial_ssthresh=0.0).validate()
        with pytest.raises(ValueError, match="initial_ssthresh must be greater than 0"):
            SimulationParameters(initial_ssthresh=-10.0).validate()

    def test_zero_or_negative_mss_raises_error(self):
        with pytest.raises(ValueError, match="mss must be a positive integer"):
            SimulationParameters(mss=0).validate()
        with pytest.raises(ValueError, match="mss must be a positive integer"):
            SimulationParameters(mss=-1460).validate()

    def test_negative_or_zero_num_rounds_raises_error(self):
        with pytest.raises(ValueError, match="num_rounds must be a positive integer"):
            SimulationParameters(num_rounds=0).validate()
        with pytest.raises(ValueError, match="num_rounds must be a positive integer"):
            SimulationParameters(num_rounds=-5).validate()

    def test_invalid_loss_probability_raises_error(self):
        with pytest.raises(ValueError, match="loss_probability must be between 0.0 and 1.0"):
            SimulationParameters(loss_probability=1.5).validate()
        with pytest.raises(ValueError, match="loss_probability must be between 0.0 and 1.0"):
            SimulationParameters(loss_probability=-0.1).validate()

    def test_max_cwnd_bounds_validation(self):
        with pytest.raises(ValueError, match="max_cwnd must be positive"):
            SimulationParameters(max_cwnd=0.0).validate()
        with pytest.raises(ValueError, match="cannot be less than initial_cwnd"):
            SimulationParameters(initial_cwnd=10.0, max_cwnd=5.0).validate()


class TestSlowStart:
    """Verifies exponential growth dynamics during Slow Start."""

    def test_slow_start_exponential_growth(self):
        # Initial CWND = 1.0, SSTHRESH = 16.0
        # Round 1: 2.0, Round 2: 4.0, Round 3: 8.0, Round 4: 16.0
        params = SimulationParameters(
            algorithm="Tahoe",
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=4,
            loss_probability=0.0
        )
        engine = TCPTahoe(params)
        res = engine.run_simulation()
        cwnds = [s.cwnd for s in res.steps]

        assert cwnds == [2.0, 4.0, 8.0, 16.0], f"Expected [2.0, 4.0, 8.0, 16.0], got {cwnds}"
        assert res.steps[0].tcp_state == TCPState.SLOW_START
        assert res.steps[1].tcp_state == TCPState.SLOW_START
        assert res.steps[2].tcp_state == TCPState.SLOW_START
        # At Round 4, CWND reaches SSTHRESH (16.0) and transitions to Congestion Avoidance
        assert res.steps[3].tcp_state == TCPState.CONGESTION_AVOIDANCE


class TestCongestionAvoidance:
    """Verifies linear growth dynamics (+1 MSS per RTT) during Congestion Avoidance."""

    def test_congestion_avoidance_linear_growth(self):
        # Start directly at SSTHRESH
        params = SimulationParameters(
            algorithm="Tahoe",
            initial_cwnd=16.0,
            initial_ssthresh=16.0,
            num_rounds=5,
            loss_probability=0.0
        )
        engine = TCPTahoe(params)
        res = engine.run_simulation()
        cwnds = [s.cwnd for s in res.steps]

        # Each round in Congestion Avoidance should increase CWND by exactly 1.0 MSS
        assert cwnds == [17.0, 18.0, 19.0, 20.0, 21.0]
        for s in res.steps:
            assert s.tcp_state == TCPState.CONGESTION_AVOIDANCE


class TestTCPTahoeAlgorithm:
    """Verifies TCP Tahoe loss handling and state transitions."""

    def test_triple_duplicate_ack_drops_to_one(self):
        # At Round 5, CWND = 17.0, SSTHRESH = 16.0
        # At Round 6, 3 Duplicate ACKs occur:
        # Tahoe must set SSTHRESH = max(floor(17/2), 2) = 8.0
        # Tahoe must set CWND = 1.0 MSS
        # Tahoe must return to Slow Start
        params = SimulationParameters(
            algorithm="Tahoe",
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=7,
            loss_events={6: LossEventType.TRIPLE_DUPLICATE_ACK}
        )
        engine = TCPTahoe(params)
        res = engine.run_simulation()
        step6 = res.steps[5]  # 0-indexed: Round 6

        assert step6.round_number == 6
        assert step6.cwnd == 1.0, f"Tahoe CWND must be 1.0 MSS after 3 Dup ACKs, got {step6.cwnd}"
        assert step6.ssthresh == 8.0, f"Tahoe SSTHRESH must be 8.0, got {step6.ssthresh}"
        assert step6.tcp_state == TCPState.SLOW_START
        assert step6.retransmission_event is True
        assert step6.congestion_event == LossEventType.TRIPLE_DUPLICATE_ACK

    def test_slow_start_resumes_after_tahoe_loss(self):
        # After dropping to 1.0 in Round 6, Round 7 must double CWND to 2.0 in Slow Start
        params = SimulationParameters(
            algorithm="Tahoe",
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=7,
            loss_events={6: LossEventType.TRIPLE_DUPLICATE_ACK}
        )
        res = TCPTahoe(params).run_simulation()
        step7 = res.steps[6]

        assert step7.round_number == 7
        assert step7.cwnd == 2.0, f"Round 7 CWND must be 2.0 MSS, got {step7.cwnd}"
        assert step7.ssthresh == 8.0
        assert step7.tcp_state == TCPState.SLOW_START


class TestTCPRenoAlgorithm:
    """Verifies TCP Reno Fast Retransmit and Fast Recovery."""

    def test_fast_retransmit_and_fast_recovery(self):
        # At Round 5, CWND = 17.0, SSTHRESH = 16.0
        # At Round 6, 3 Duplicate ACKs occur:
        # Reno calculates SSTHRESH = max(floor(17/2), 2) = 8.0
        # Reno inflates CWND = SSTHRESH + 3 = 11.0 MSS
        # Reno enters Fast Recovery
        params = SimulationParameters(
            algorithm="Reno",
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=8,
            loss_events={6: LossEventType.TRIPLE_DUPLICATE_ACK}
        )
        res = TCPReno(params).run_simulation()
        step6 = res.steps[5]

        assert step6.round_number == 6
        assert step6.ssthresh == 8.0
        assert step6.cwnd == 11.0, f"Reno CWND must be inflated to 11.0 MSS in Fast Recovery, got {step6.cwnd}"
        assert step6.tcp_state == TCPState.FAST_RECOVERY
        assert step6.retransmission_event is True

    def test_recovery_ack_deflates_cwnd_to_ssthresh(self):
        # In Round 7 (after Fast Recovery in Round 6):
        # When the recovery ACK arrives, CWND deflates to SSTHRESH (8.0 MSS)
        # And transitions to Congestion Avoidance
        params = SimulationParameters(
            algorithm="Reno",
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=8,
            loss_events={6: LossEventType.TRIPLE_DUPLICATE_ACK}
        )
        res = TCPReno(params).run_simulation()
        step7 = res.steps[6]

        assert step7.round_number == 7
        assert step7.cwnd == 8.0, f"Reno CWND must deflate to SSTHRESH (8.0 MSS), got {step7.cwnd}"
        assert step7.tcp_state == TCPState.CONGESTION_AVOIDANCE
        assert step7.retransmission_event is False

        # In Round 8, Congestion Avoidance adds 1 MSS: 8.0 + 1.0 = 9.0 MSS
        step8 = res.steps[7]
        assert step8.cwnd == 9.0
        assert step8.tcp_state == TCPState.CONGESTION_AVOIDANCE


class TestTimeoutHandling:
    """Verifies RTO Timeout behaviour for both Tahoe and Reno."""

    def test_timeout_reduces_cwnd_to_one_in_both(self):
        loss_dict = {5: LossEventType.TIMEOUT}
        # Run Tahoe
        tahoe_res = TCPTahoe(SimulationParameters(algorithm="Tahoe", initial_cwnd=1.0, num_rounds=6, loss_events=loss_dict)).run_simulation()
        # Run Reno
        reno_res = TCPReno(SimulationParameters(algorithm="Reno", initial_cwnd=1.0, num_rounds=6, loss_events=loss_dict)).run_simulation()

        tahoe_loss_step = tahoe_res.steps[4]
        reno_loss_step = reno_res.steps[4]

        # Both algorithms must drop CWND to 1.0 MSS on Timeout
        assert tahoe_loss_step.cwnd == 1.0, f"Tahoe must drop to 1.0 on timeout, got {tahoe_loss_step.cwnd}"
        assert reno_loss_step.cwnd == 1.0, f"Reno must drop to 1.0 on timeout, got {reno_loss_step.cwnd}"

        # Both must be in Slow Start
        assert tahoe_loss_step.tcp_state == TCPState.SLOW_START
        assert reno_loss_step.tcp_state == TCPState.SLOW_START

        # Both must flag retransmission
        assert tahoe_loss_step.retransmission_event is True
        assert reno_loss_step.retransmission_event is True

    def test_timeout_ssthresh_minimum_clamp(self):
        # If CWND = 2.0 when timeout occurs: floor(2/2) = 1, but minimum SSTHRESH is 2.0
        params = SimulationParameters(algorithm="Tahoe", initial_cwnd=1.0, num_rounds=3, loss_events={2: LossEventType.TIMEOUT})
        res = TCPTahoe(params).run_simulation()
        step2 = res.steps[1]
        assert step2.ssthresh == 2.0


class TestMultipleCongestionEvents:
    """Tests complex scenarios with multiple loss events across simulation rounds."""

    def test_multiple_loss_events(self):
        # Round 4: 3 Dup ACKs, Round 8: Timeout
        params = SimulationParameters(
            algorithm="Reno",
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=10,
            loss_events={
                4: LossEventType.TRIPLE_DUPLICATE_ACK,
                8: LossEventType.TIMEOUT
            }
        )
        res = TCPReno(params).run_simulation()
        df = res.to_dataframe()

        # Check Round 4 event
        r4 = df[df["RTT_Round"] == 4].iloc[0]
        assert r4["TCP_State"] == "Fast Recovery"
        assert bool(r4["Retransmission"]) is True

        # Check Round 8 event
        r8 = df[df["RTT_Round"] == 8].iloc[0]
        assert r8["CWND"] == 1.0
        assert r8["TCP_State"] == "Slow Start"
        assert bool(r8["Retransmission"]) is True


class TestMaximumCWND:
    """Verifies that CWND is strictly capped at max_cwnd."""

    def test_max_cwnd_enforcement(self):
        params = SimulationParameters(
            algorithm="Tahoe",
            initial_cwnd=16.0,
            initial_ssthresh=16.0,
            max_cwnd=18.0,
            num_rounds=5,
            loss_probability=0.0
        )
        res = TCPTahoe(params).run_simulation()
        cwnds = [s.cwnd for s in res.steps]
        # Round 1: 17.0, Round 2: 18.0, Round 3: 18.0 (capped), Round 4: 18.0, Round 5: 18.0
        assert max(cwnds) == 18.0
        assert cwnds[2:] == [18.0, 18.0, 18.0]


class TestRandomSeedReproducibility:
    """Verifies that identical random seeds produce identical loss patterns and traces."""

    def test_reproducible_loss_with_same_seed(self):
        p1 = SimulationParameters(algorithm="Reno", num_rounds=25, loss_probability=0.2, random_seed=1234)
        p2 = SimulationParameters(algorithm="Reno", num_rounds=25, loss_probability=0.2, random_seed=1234)
        p3 = SimulationParameters(algorithm="Reno", num_rounds=25, loss_probability=0.2, random_seed=5678)

        df1, _ = simulate_tcp(p1)
        df2, _ = simulate_tcp(p2)
        df3, _ = simulate_tcp(p3)

        assert list(df1["CWND"]) == list(df2["CWND"]), "Same seed must produce identical CWND time series"
        assert list(df1["Loss_Event"]) == list(df2["Loss_Event"])

        # Different seed should produce a different trace
        assert list(df1["CWND"]) != list(df3["CWND"]), "Different seeds should produce differing traces"


class TestDataFrameColumnsAndMetrics:
    """Verifies schema completeness, column names, and summary metrics."""

    def test_correct_dataframe_columns(self):
        df, metrics = simulate_tcp(algorithm="Tahoe", num_rounds=10)
        expected_cols = [
            "RTT_Round", "Algorithm", "CWND", "SSTHRESH", "TCP_State",
            "Loss_Event", "Retransmission", "Action", "Explanation"
        ]
        for col in expected_cols:
            assert col in df.columns, f"Missing required column '{col}' in DataFrame"

        assert metrics["algorithm"] == "Tahoe"
        assert metrics["total_rounds"] == 10
        assert "average_cwnd" in metrics
        assert "peak_cwnd" in metrics

    def test_algorithm_comparison_results(self):
        comp_df, comp_summary = compare_algorithms(
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=8,
            loss_events={6: LossEventType.TRIPLE_DUPLICATE_ACK}
        )
        assert "Tahoe_CWND" in comp_df.columns
        assert "Reno_CWND" in comp_df.columns
        assert "CWND_Difference" in comp_df.columns

        # Verify that Reno outperformed Tahoe following 3 Duplicate ACKs
        assert comp_summary["reno_average_cwnd"] > comp_summary["tahoe_average_cwnd"]
        assert comp_summary["reno_throughput_advantage_percent"] > 0.0


class TestDataStructures:
    """Tests basic DataFrame export and schema compliance from Phase 1."""

    def test_simulation_result_empty_dataframe(self):
        params = SimulationParameters()
        result = SimulationResult(parameters=params)
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_simulation_result_with_steps(self):
        params = SimulationParameters()
        step = SimulationStep(
            round_number=1,
            algorithm="Tahoe",
            cwnd=1.0,
            ssthresh=16.0,
            tcp_state=TCPState.SLOW_START,
            congestion_event=LossEventType.NONE,
            retransmission_event=False,
            algorithm_action="Initialize Slow Start",
            explanation="Initial round"
        )
        result = SimulationResult(parameters=params, steps=[step])
        df = result.to_dataframe()
        assert len(df) == 1
        assert df.iloc[0]["CWND"] == 1.0
        assert df.iloc[0]["TCP_State"] == "Slow Start"

    def test_packet_analysis_empty_dataframe(self):
        summary = PacketAnalysisSummary(filename="test.pcap")
        df = summary.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert "seq_number" in df.columns

    def test_network_experiment_config_validation(self):
        valid_config = NetworkExperimentConfig(
            experiment_id="EXP-1",
            bandwidth_mbps=10.0,
            delay_ms=20.0,
            loss_percentage=2.0,
            duration_seconds=10
        )
        valid_config.validate()

        invalid_config = NetworkExperimentConfig(
            experiment_id="EXP-2",
            bandwidth_mbps=-5.0
        )
        with pytest.raises(ValueError, match="bandwidth_mbps must be positive"):
            invalid_config.validate()


class TestNetworkExperimentValidation:
    """Verifies parameter validation for Mininet & iPerf3 network experiments."""

    def test_valid_network_experiment_config(self):
        config = NetworkExperimentConfig(
            experiment_id="EXP-VALID",
            bandwidth_mbps=25.0,
            delay_ms=15.0,
            loss_percentage=1.0,
            duration_seconds=10,
            tcp_congestion_algorithm="cubic"
        )
        config.validate()
        assert config.experiment_id == "EXP-VALID"
        assert config.bandwidth_mbps == 25.0
        assert config.delay_ms == 15.0
        assert config.loss_percentage == 1.0
        assert config.duration_seconds == 10
        assert config.tcp_congestion_algorithm == "cubic"

    def test_invalid_bandwidth_raises_error(self):
        with pytest.raises(ValueError, match="bandwidth_mbps must be positive"):
            NetworkExperimentConfig(experiment_id="EXP-BAD", bandwidth_mbps=0.0).validate()
        with pytest.raises(ValueError, match="bandwidth_mbps must be positive"):
            NetworkExperimentConfig(experiment_id="EXP-BAD", bandwidth_mbps=-10.0).validate()

    def test_invalid_delay_raises_error(self):
        with pytest.raises(ValueError, match="delay_ms cannot be negative"):
            NetworkExperimentConfig(experiment_id="EXP-BAD", delay_ms=-5.0).validate()

    def test_invalid_loss_percentage_raises_error(self):
        with pytest.raises(ValueError, match="loss_percentage must be between 0.0 and 100.0%"):
            NetworkExperimentConfig(experiment_id="EXP-BAD", loss_percentage=-1.0).validate()
        with pytest.raises(ValueError, match="loss_percentage must be between 0.0 and 100.0%"):
            NetworkExperimentConfig(experiment_id="EXP-BAD", loss_percentage=105.0).validate()

    def test_invalid_duration_raises_error(self):
        with pytest.raises(ValueError, match="duration_seconds must be a positive integer"):
            NetworkExperimentConfig(experiment_id="EXP-BAD", duration_seconds=0).validate()
        with pytest.raises(ValueError, match="duration_seconds must be a positive integer"):
            NetworkExperimentConfig(experiment_id="EXP-BAD", duration_seconds=-5).validate()

    def test_invalid_algorithm_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported Linux congestion algorithm"):
            NetworkExperimentConfig(experiment_id="EXP-BAD", tcp_congestion_algorithm="unsupported_algo").validate()


class TestIPerf3OutputParsing:
    """Verifies iPerf3 JSON output parsing and metric extraction."""

    SAMPLE_IPERF3_JSON = """{
        "start": {
            "connected": [{"socket": 5, "local_host": "10.0.0.1", "remote_host": "10.0.0.2"}],
            "version": "iperf 3.9"
        },
        "end": {
            "streams": [
                {
                    "sender": {
                        "socket": 5, "start": 0, "end": 10.0001, "seconds": 10.0001,
                        "bytes": 119537664, "bits_per_second": 95629174.5,
                        "retransmits": 14, "mean_rtt": 20450
                    },
                    "receiver": {
                        "socket": 5, "start": 0, "end": 10.0001, "seconds": 10.0001,
                        "bytes": 118882304, "bits_per_second": 95104892.1
                    }
                }
            ],
            "sum_sent": {
                "start": 0, "end": 10.0001, "seconds": 10.0001,
                "bytes": 119537664, "bits_per_second": 95629174.5, "retransmits": 14
            },
            "sum_received": {
                "start": 0, "end": 10.0001, "seconds": 10.0001,
                "bytes": 118882304, "bits_per_second": 95104892.1
            }
        }
    }"""

    def test_parse_valid_iperf3_json_string(self):
        parsed = parse_iperf3_json(self.SAMPLE_IPERF3_JSON)
        assert parsed["throughput_mbps"] == 95.10
        assert parsed["transfer_mb"] == 113.38
        assert parsed["duration_seconds"] == 10.00
        assert parsed["retransmissions"] == 14
        assert parsed["rtt_ms"] == 20.45

    def test_parse_valid_iperf3_json_dict(self):
        import json
        data_dict = json.loads(self.SAMPLE_IPERF3_JSON)
        parsed = parse_iperf3_json(data_dict)
        assert parsed["throughput_mbps"] == 95.10
        assert parsed["retransmissions"] == 14

    def test_parse_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="Failed to parse iPerf3 output as JSON"):
            parse_iperf3_json("not a valid json string")
        with pytest.raises(ValueError, match="iPerf3 output is empty"):
            parse_iperf3_json("")

    def test_parse_iperf3_error_response_raises_runtime_error(self):
        error_json = '{"error": "error - unable to connect to server: Connection refused"}'
        with pytest.raises(RuntimeError, match="iPerf3 execution reported error"):
            parse_iperf3_json(error_json)

    def test_parse_missing_end_block_raises_value_error(self):
        malformed_json = '{"start": {"version": "3.9"}}'
        with pytest.raises(ValueError, match="missing 'end' statistics block"):
            parse_iperf3_json(malformed_json)


class TestNetworkExperimentEnvironmentAndManager:
    """Verifies environment detection, manager workflow, and failure handling."""

    def test_environment_detection_structure(self):
        env = NetworkExperimentManager.verify_environment()
        assert isinstance(env, dict)
        for key in ["supported", "is_linux", "mininet_available", "iperf3_available", "has_root", "guidance"]:
            assert key in env, f"Missing key '{key}' in verify_environment output"
        assert isinstance(env["supported"], bool)
        assert isinstance(env["guidance"], str)

    def test_unsupported_environment_raises_environment_error(self):
        # On Windows or systems without Mininet/root, running experiment must raise EnvironmentError
        config = NetworkExperimentConfig(experiment_id="EXP-FAIL-TEST", bandwidth_mbps=10.0)
        manager = NetworkExperimentManager(config)
        env = manager.verify_environment()
        if not env["supported"]:
            with pytest.raises(EnvironmentError):
                manager.run_experiment()

    def test_experiment_result_dataframe_export(self):
        res = ExperimentResult(
            experiment_id="EXP-101",
            configured_bandwidth_mbps=10.0,
            configured_delay_ms=20.0,
            configured_loss_percentage=0.5,
            measured_throughput_mbps=9.45,
            transfer_amount_mb=11.25,
            measured_retransmissions=3,
            measured_rtt_ms=21.5,
            experiment_duration_sec=10.0,
            tcp_congestion_algorithm="reno",
            status="Completed"
        )
        df = res.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert df.iloc[0]["Experiment_ID"] == "EXP-101"
        assert df.iloc[0]["Measured_Throughput_Mbps"] == 9.45
        assert df.iloc[0]["Throughput_Efficiency_Pct"] == 94.5
        assert df.iloc[0]["Status"] == "Completed"


class TestHelperUtilities:
    """Tests utility and formatting functions."""

    def test_format_bitrate(self):
        assert format_bitrate(500) == "500 bps"
        assert format_bitrate(2_500) == "2.50 Kbps"
        assert format_bitrate(10_000_000) == "10.00 Mbps"
        assert format_bitrate(1_500_000_000) == "1.50 Gbps"

    def test_format_bytes(self):
        assert format_bytes(512) == "512 B"
        assert format_bytes(2048) == "2.00 KB"
        assert format_bytes(5 * 1024 * 1024) == "5.00 MB"

    def test_build_tcp_state_timeline_chart_no_multiple_values_error(self):
        import plotly.graph_objects as go
        df, _ = simulate_tcp(SimulationParameters(algorithm="Reno", num_rounds=10))
        fig = build_tcp_state_timeline_chart(df, "Reno")
        assert isinstance(fig, go.Figure)
        assert "State Machine Transitions Timeline" in fig.layout.title.text

    def test_build_comparison_state_chart_no_multiple_values_error(self):
        import plotly.graph_objects as go
        comp_df, _ = compare_algorithms(SimulationParameters(num_rounds=10))
        fig = build_comparison_state_chart(comp_df)
        assert isinstance(fig, go.Figure)
        assert "State Machine Divergence" in fig.layout.title.text


class TestPacketCaptureValidation:
    """Verifies file format, size, and header magic bytes validation for PCAP/PCAPNG files."""

    def test_valid_pcap_header_validation(self):
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
            tmp.write(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
            tmp_path = tmp.name
        try:
            validate_capture_file(tmp_path)
            analyzer = PacketAnalyzer(tmp_path)
            assert analyzer.filename == os.path.basename(tmp_path)
            assert analyzer.file_size == 24
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_valid_pcapng_header_validation(self):
        with tempfile.NamedTemporaryFile(suffix=".pcapng", delete=False) as tmp:
            tmp.write(b"\x0a\x0d\x0d\x0a" + b"\x00" * 24)
            tmp_path = tmp.name
        try:
            validate_capture_file(tmp_path)
            analyzer = PacketAnalyzer(tmp_path)
            assert analyzer.filename.endswith(".pcapng")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_empty_capture_raises_error(self):
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with pytest.raises(ValueError, match="Capture file is empty"):
                validate_capture_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_corrupted_capture_raises_error(self):
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
            tmp.write(b"CORRUPTED_NON_PCAP_DATA_STREAM")
            tmp_path = tmp.name
        try:
            with pytest.raises(ValueError, match="Invalid or corrupted capture file"):
                validate_capture_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_unsupported_file_extension_raises_error(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
            tmp_path = tmp.name
        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                validate_capture_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_file_not_found_raises_error(self):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            validate_capture_file("nonexistent_trace_file.pcap")


class TestTSharkOutputParsing:
    """Verifies parsing of TShark TSV output, missing fields, retransmissions, duplicate ACKs, and flags."""

    SAMPLE_TSHARK_TSV = (
        "frame.number\tframe.time_relative\tip.src\tipv6.src\tip.dst\tipv6.dst\t"
        "tcp.srcport\ttcp.dstport\ttcp.seq\ttcp.ack\ttcp.seq_raw\ttcp.ack_raw\t"
        "tcp.len\ttcp.flags\ttcp.flags.syn\ttcp.flags.ack\ttcp.flags.fin\t"
        "tcp.flags.reset\ttcp.flags.push\ttcp.flags.urg\ttcp.flags.ece\ttcp.flags.cwr\t"
        "tcp.window_size_value\ttcp.analysis.retransmission\t"
        "tcp.analysis.fast_retransmission\ttcp.analysis.spurious_retransmission\t"
        "tcp.analysis.out_of_order\ttcp.analysis.duplicate_ack\t"
        "tcp.analysis.duplicate_ack_num\ttcp.analysis.ack_rtt\n"
        "1\t0.000000\t192.168.1.10\t\t192.168.1.20\t\t54321\t80\t0\t0\t1000\t0\t0\t0x0002\t1\t0\t0\t0\t0\t0\t0\t0\t64240\t\t\t\t\t\t\t\n"
        "2\t0.001200\t192.168.1.20\t\t192.168.1.10\t\t80\t54321\t0\t1\t2000\t1001\t0\t0x0012\t1\t1\t0\t0\t0\t0\t0\t0\t65535\t\t\t\t\t\t\t0.001200\n"
        "3\t0.001500\t192.168.1.10\t\t192.168.1.20\t\t54321\t80\t1\t1\t1001\t2001\t0\t0x0010\t0\t1\t0\t0\t0\t0\t0\t0\t64240\t\t\t\t\t\t\t\n"
        "4\t0.005000\t192.168.1.10\t\t192.168.1.20\t\t54321\t80\t1\t1\t1001\t2001\t1460\t0x0018\t0\t1\t0\t0\t1\t0\t0\t0\t64240\t\t\t\t\t\t\t\n"
        "5\t0.010000\t192.168.1.10\t\t192.168.1.20\t\t54321\t80\t1461\t1\t2461\t2001\t1460\t0x0010\t0\t1\t0\t0\t0\t0\t0\t0\t64240\t\t\t\t\t\t\t\n"
    )

    def _create_analyzer(self) -> Tuple[PacketAnalyzer, str]:
        tmp = tempfile.NamedTemporaryFile(suffix=".pcap", delete=False)
        tmp.write(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
        tmp.close()
        analyzer = PacketAnalyzer(tmp.name)
        return analyzer, tmp.name

    def test_parse_valid_tcp_packets_tsv(self):
        analyzer, tmp_path = self._create_analyzer()
        try:
            summary = analyzer.parse_tshark_output(self.SAMPLE_TSHARK_TSV, total_packets=5, duration_seconds=0.010)
            assert summary.total_tcp_packets == 5
            assert summary.total_packets == 5
            assert summary.duration_seconds == 0.010
            assert summary.syn_count == 2
            assert summary.retransmission_count == 0

            df = summary.to_dataframe()
            assert len(df) == 5
            assert df.iloc[0]["source_ip"] == "192.168.1.10"
            assert df.iloc[0]["destination_ip"] == "192.168.1.20"
            assert df.iloc[0]["source_port"] == 54321
            assert df.iloc[0]["destination_port"] == 80
            assert bool(df.iloc[0]["flag_syn"]) is True
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_empty_tcp_results_returns_empty_summary(self):
        analyzer, tmp_path = self._create_analyzer()
        try:
            summary = analyzer.parse_tshark_output("", total_packets=0)
            assert summary.total_tcp_packets == 0
            df = summary.to_dataframe()
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0
            assert "seq_number" in df.columns
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_missing_fields_handled_gracefully(self):
        analyzer, tmp_path = self._create_analyzer()
        tsv_with_missing_columns = (
            "frame.number\tframe.time_relative\tip.src\tip.dst\ttcp.srcport\ttcp.dstport\ttcp.seq\n"
            "1\t0.000\t10.0.0.1\t10.0.0.2\t12345\t80\t100\n"
            "2\t\t\t\t\t\t\n"
        )
        try:
            summary = analyzer.parse_tshark_output(tsv_with_missing_columns)
            assert summary.total_tcp_packets >= 1
            df = summary.to_dataframe()
            assert df.iloc[0]["source_ip"] == "10.0.0.1"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_retransmission_parsing(self):
        analyzer, tmp_path = self._create_analyzer()
        tsv = (
            "frame.number\tframe.time_relative\tip.src\tip.dst\ttcp.srcport\ttcp.dstport\ttcp.seq\ttcp.ack\ttcp.len\ttcp.flags\t"
            "tcp.analysis.retransmission\ttcp.analysis.fast_retransmission\ttcp.analysis.spurious_retransmission\ttcp.analysis.out_of_order\n"
            "1\t0.01\t10.0.0.1\t10.0.0.2\t5000\t80\t100\t1\t1460\t0x0010\t1\t0\t0\t0\n"
            "2\t0.02\t10.0.0.1\t10.0.0.2\t5000\t80\t100\t1\t1460\t0x0010\t1\t1\t0\t0\n"
            "3\t0.03\t10.0.0.1\t10.0.0.2\t5000\t80\t100\t1\t1460\t0x0010\t1\t0\t1\t0\n"
            "4\t0.04\t10.0.0.1\t10.0.0.2\t5000\t80\t2920\t1\t1460\t0x0010\t0\t0\t0\t1\n"
        )
        try:
            summary = analyzer.parse_tshark_output(tsv)
            assert summary.total_tcp_packets == 4
            assert summary.retransmission_count == 3
            assert summary.fast_retransmission_count == 1
            assert summary.spurious_retransmission_count == 1
            assert summary.out_of_order_count == 1
            assert summary.retransmission_rate == 75.0
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_duplicate_ack_parsing(self):
        analyzer, tmp_path = self._create_analyzer()
        tsv = (
            "frame.number\tframe.time_relative\tip.src\tip.dst\ttcp.srcport\ttcp.dstport\ttcp.seq\ttcp.ack\ttcp.len\ttcp.flags\t"
            "tcp.analysis.duplicate_ack\ttcp.analysis.duplicate_ack_num\n"
            "10\t0.10\t10.0.0.2\t10.0.0.1\t80\t5000\t1\t1461\t0\t0x0010\t1\t1\n"
            "11\t0.11\t10.0.0.2\t10.0.0.1\t80\t5000\t1\t1461\t0\t0x0010\t1\t2\n"
            "12\t0.12\t10.0.0.2\t10.0.0.1\t80\t5000\t1\t1461\t0\t0x0010\t1\t3\n"
        )
        try:
            summary = analyzer.parse_tshark_output(tsv)
            assert summary.duplicate_ack_count == 3
            assert summary.duplicate_ack_rate == 100.0
            p3 = summary.packets[2]
            assert p3.is_duplicate_ack is True
            assert p3.duplicate_ack_num == 3
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_tcp_flag_extraction(self):
        analyzer, tmp_path = self._create_analyzer()
        tsv = (
            "frame.number\tframe.time_relative\tip.src\tip.dst\ttcp.srcport\ttcp.dstport\ttcp.seq\ttcp.ack\ttcp.len\ttcp.flags\t"
            "tcp.flags.syn\ttcp.flags.ack\ttcp.flags.fin\ttcp.flags.reset\ttcp.flags.push\ttcp.flags.urg\ttcp.flags.ece\ttcp.flags.cwr\n"
            "1\t0.01\t10.0.0.1\t10.0.0.2\t5000\t80\t0\t0\t0\t0x0002\t1\t0\t0\t0\t0\t0\t0\t0\n"
            "2\t0.02\t10.0.0.2\t10.0.0.1\t80\t5000\t0\t1\t0\t0x0012\t1\t1\t0\t0\t0\t0\t0\t0\n"
            "3\t0.03\t10.0.0.1\t10.0.0.2\t5000\t80\t1\t1\t100\t0x0018\t0\t1\t0\t0\t1\t0\t0\t0\n"
            "4\t0.04\t10.0.0.1\t10.0.0.2\t5000\t80\t101\t1\t0\t0x0001\t0\t0\t1\t0\t0\t0\t0\t0\n"
            "5\t0.05\t10.0.0.2\t10.0.0.1\t80\t5000\t1\t101\t0\t0x0004\t0\t0\t0\t1\t0\t0\t0\t0\n"
        )
        try:
            summary = analyzer.parse_tshark_output(tsv)
            flags = summary.flag_distribution
            assert flags["SYN"] == 2
            assert flags["ACK"] == 2
            assert flags["PSH"] == 1
            assert flags["FIN"] == 1
            assert flags["RST"] == 1
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestPacketDataFrameFiltering:
    """Verifies PacketAnalyzer.filter_dataframe operations."""

    def _sample_df(self) -> pd.DataFrame:
        data = [
            {"packet_id": 1, "source_ip": "10.0.0.1", "destination_ip": "10.0.0.2", "source_port": 5000, "destination_port": 80, "flag_syn": True, "flag_ack": False, "is_retransmission": False, "is_duplicate_ack": False},
            {"packet_id": 2, "source_ip": "10.0.0.2", "destination_ip": "10.0.0.1", "source_port": 80, "destination_port": 5000, "flag_syn": True, "flag_ack": True, "is_retransmission": False, "is_duplicate_ack": False},
            {"packet_id": 3, "source_ip": "10.0.0.1", "destination_ip": "10.0.0.2", "source_port": 5000, "destination_port": 80, "flag_syn": False, "flag_ack": True, "is_retransmission": True, "is_duplicate_ack": False},
            {"packet_id": 4, "source_ip": "10.0.0.2", "destination_ip": "10.0.0.1", "source_port": 80, "destination_port": 5000, "flag_syn": False, "flag_ack": True, "is_retransmission": False, "is_duplicate_ack": True},
        ]
        return pd.DataFrame(data)

    def test_filter_by_ip_and_port(self):
        df = self._sample_df()
        filtered = PacketAnalyzer.filter_dataframe(df, source_ip="10.0.0.1")
        assert len(filtered) == 2
        assert all(filtered["source_ip"] == "10.0.0.1")

        filtered_port = PacketAnalyzer.filter_dataframe(df, source_port=80)
        assert len(filtered_port) == 2

    def test_filter_by_retransmission_and_dup_ack(self):
        df = self._sample_df()
        retrans_df = PacketAnalyzer.filter_dataframe(df, retransmissions_only=True)
        assert len(retrans_df) == 1
        assert retrans_df.iloc[0]["packet_id"] == 3

        dup_df = PacketAnalyzer.filter_dataframe(df, duplicate_acks_only=True)
        assert len(dup_df) == 1
        assert dup_df.iloc[0]["packet_id"] == 4

    def test_filter_by_flags(self):
        df = self._sample_df()
        syn_df = PacketAnalyzer.filter_dataframe(df, flag_filter="SYN")
        assert len(syn_df) == 2


class TestPacketAnalyzerExecutionAndSafety:
    """Verifies error handling, missing TShark detection, tempfile cleanup, and subprocess timeout handling."""

    def test_missing_tshark_raises_environment_error(self):
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
            tmp.write(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
            tmp_path = tmp.name
        try:
            analyzer = PacketAnalyzer(tmp_path, tshark_path="/nonexistent/binary/tshark")
            with patch("core.packet_analysis.is_tshark_available", return_value=False):
                with pytest.raises(EnvironmentError, match="TShark CLI was not found"):
                    analyzer.analyze()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_subprocess_timeout_handling(self):
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
            tmp.write(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
            tmp_path = tmp.name
        try:
            analyzer = PacketAnalyzer(tmp_path)
            with patch("core.packet_analysis.is_tshark_available", return_value=True):
                with patch("core.packet_analysis.run_safe_command", side_effect=subprocess.TimeoutExpired(cmd="tshark", timeout=5)):
                    with pytest.raises(TimeoutError, match="timed out"):
                        analyzer.analyze(timeout=5)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_temporary_file_cleanup(self):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
                tmp.write(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
                temp_path = tmp.name
            assert os.path.exists(temp_path)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        assert not os.path.exists(temp_path)


class TestPerformanceAnalytics:
    """Verifies Phase 7 Performance Analytics calculations, metrics, comparisons, and persistence."""

    def test_empty_analytics_dashboard_handling(self):
        metrics_none = calculate_simulation_metrics(None)
        assert metrics_none["total_rounds"] == 0
        assert metrics_none["average_cwnd"] == 0.0
        assert metrics_none["final_state"] == "N/A"

        metrics_empty = calculate_simulation_metrics(pd.DataFrame())
        assert metrics_empty["total_rounds"] == 0
        assert metrics_empty["average_cwnd"] == 0.0

    def test_simulation_metrics_calculation(self):
        df = pd.DataFrame([
            {"RTT_Round": 1, "CWND": 1.0, "SSTHRESH": 16.0, "TCP_State": "Slow Start", "Loss_Event": "None", "Retransmission": False},
            {"RTT_Round": 2, "CWND": 2.0, "SSTHRESH": 16.0, "TCP_State": "Slow Start", "Loss_Event": "None", "Retransmission": False},
            {"RTT_Round": 3, "CWND": 4.0, "SSTHRESH": 16.0, "TCP_State": "Slow Start", "Loss_Event": "None", "Retransmission": False},
            {"RTT_Round": 4, "CWND": 8.0, "SSTHRESH": 16.0, "TCP_State": "Slow Start", "Loss_Event": "None", "Retransmission": False},
            {"RTT_Round": 5, "CWND": 4.0, "SSTHRESH": 4.0, "TCP_State": "Slow Start", "Loss_Event": "Timeout", "Retransmission": True},
        ])
        metrics = calculate_simulation_metrics(df)
        assert metrics["total_rounds"] == 5
        assert metrics["average_cwnd"] == 3.8
        assert metrics["peak_cwnd"] == 8.0
        assert metrics["min_cwnd"] == 1.0
        assert metrics["final_cwnd"] == 4.0
        assert metrics["total_loss_events"] == 1
        assert metrics["total_retransmissions"] == 1
        assert metrics["state_counts"]["Slow Start"] == 5
        assert metrics["state_percentages"]["Slow Start"] == 100.0

    def test_tahoe_reno_comparisons_analytics(self):
        params = SimulationParameters(
            algorithm="Tahoe",
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=20,
            loss_events={8: LossEventType.TRIPLE_DUPLICATE_ACK}
        )
        comp_df, summary = compare_algorithms(params)
        assert isinstance(comp_df, pd.DataFrame)
        assert len(comp_df) == 20
        assert "reno_throughput_advantage_percent" in summary
        assert "reno_average_cwnd" in summary
        assert "tahoe_average_cwnd" in summary
        assert summary["tahoe_average_cwnd"] > 0
        assert summary["reno_average_cwnd"] > 0
        assert isinstance(summary["reno_throughput_advantage_percent"], float)
        assert summary["tahoe_peak_cwnd"] > 0
        assert summary["reno_peak_cwnd"] > 0

    def test_network_experiment_metrics(self):
        exp = ExperimentResult(
            experiment_id="EXP-ANALYTICS-1",
            configured_bandwidth_mbps=20.0,
            configured_delay_ms=10.0,
            configured_loss_percentage=0.0,
            measured_throughput_mbps=18.5,
            transfer_amount_mb=23.1,
            measured_retransmissions=0,
            measured_rtt_ms=20.5,
            experiment_duration_sec=10.0,
            tcp_congestion_algorithm="cubic",
            status="Completed"
        )
        df = exp.to_dataframe()
        assert df.iloc[0]["Measured_Throughput_Mbps"] == 18.5
        assert df.iloc[0]["Throughput_Efficiency_Pct"] == 92.5
        assert df.iloc[0]["Configured_Bandwidth_Mbps"] == 20.0

    def test_packet_analysis_metrics(self):
        summary = PacketAnalysisSummary(
            filename="analytics_trace.pcap",
            total_packets=50,
            total_tcp_packets=50,
            retransmission_count=5,
            duplicate_ack_count=10,
            duration_seconds=5.0
        )
        assert summary.retransmission_rate == 10.0
        assert summary.duplicate_ack_rate == 20.0

    def test_throughput_calculation_formula(self):
        # 12,500,000 bytes over 10 seconds = 100,000,000 bits / 10s = 10 Mbps
        tp = calculate_experiment_throughput(bytes_transferred=12_500_000, duration_seconds=10.0)
        assert abs(tp - 10.0) < 0.001
        assert calculate_experiment_throughput(0, 10.0) == 0.0
        assert calculate_experiment_throughput(10_000, 0.0) == 0.0

    def test_retransmission_percentage_formula(self):
        eff = calculate_throughput_efficiency(measured_mbps=8.5, configured_mbps=10.0)
        assert abs(eff - 85.0) < 0.001
        assert calculate_throughput_efficiency(5.0, 0.0) == 0.0

        empty_summary = PacketAnalysisSummary(filename="empty.pcap")
        assert empty_summary.retransmission_rate == 0.0
        assert empty_summary.duplicate_ack_rate == 0.0

    def test_missing_data_handling(self):
        res = ExperimentResult.from_dict({})
        assert res.experiment_id == "EXP-UNKNOWN"
        assert res.configured_bandwidth_mbps == 10.0
        assert res.status == "Completed"

        insights = generate_automatic_performance_insights(None, None, None, None)
        assert insights == []

    def test_invalid_records_handling(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(b"{MALFORMED_JSON_STRING")
            tmp_path = tmp.name
        try:
            records = load_experiment_history(tmp_path)
            assert records == []
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_multiple_experiment_comparisons_and_charts(self):
        e1 = ExperimentResult("E1", 10.0, 10.0, 0.0, 9.2, 11.5, 0, 20.0, 10.0, "cubic")
        e2 = ExperimentResult("E2", 50.0, 10.0, 0.0, 46.5, 58.1, 1, 20.2, 10.0, "cubic")
        e3 = ExperimentResult("E3", 100.0, 10.0, 0.0, 91.0, 113.8, 4, 20.4, 10.0, "cubic")

        history_df = pd.concat([e1.to_dataframe(), e2.to_dataframe(), e3.to_dataframe()], ignore_index=True)
        assert len(history_df) == 3

        fig = build_multi_experiment_chart(
            history_df,
            "Configured_Bandwidth_Mbps",
            "Bandwidth (Mbps)",
            "Throughput vs. Bandwidth"
        )
        assert fig is not None
        assert len(fig.data) >= 1

    def test_persistence_save_and_load(self):
        e1 = ExperimentResult("P1", 20.0, 15.0, 1.0, 16.5, 20.0, 2, 30.0, 10.0, "reno")
        e2 = ExperimentResult("P2", 40.0, 15.0, 1.0, 34.0, 42.0, 5, 30.2, 10.0, "reno")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            save_experiment_history([e1, e2], tmp_path)
            assert os.path.exists(tmp_path)

            loaded = load_experiment_history(tmp_path)
            assert len(loaded) == 2
            assert loaded[0].experiment_id == "P1"
            assert loaded[0].configured_bandwidth_mbps == 20.0
            assert loaded[1].experiment_id == "P2"
            assert loaded[1].measured_throughput_mbps == 34.0
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_session_state_and_automatic_insights_behaviour(self):
        sim_metrics = {
            "total_rounds": 30,
            "average_cwnd": 12.5,
            "peak_cwnd": 24.0,
            "final_cwnd": 16.0,
            "total_loss_events": 2,
            "state_percentages": {"Congestion Avoidance": 80.0, "Slow Start": 20.0}
        }
        comp_summary = {
            "tahoe_average_cwnd": 10.0,
            "reno_average_cwnd": 13.5,
            "reno_throughput_advantage_percent": 35.0
        }
        exp_result = ExperimentResult("EXP-INSIGHT", 50.0, 10.0, 2.0, 42.0, 52.5, 3, 20.0, 10.0, "cubic")
        pkt_summary = PacketAnalysisSummary("trace.pcap", 100, 100, 4, 6, 10.0)

        insights = generate_automatic_performance_insights(
            sim_metrics=sim_metrics,
            comp_summary=comp_summary,
            exp_result=exp_result,
            pkt_summary=pkt_summary
        )

        assert len(insights) == 4
        categories = [item["category"] for item in insights]
        assert "Simulation Dynamics" in categories
        assert "Comparative Analysis" in categories
        assert "Empirical Network Performance" in categories
        assert "Wire Packet Capture Dissection" in categories


class TestEndToEndIntegrationWorkflows:
    """Verifies end-to-end integration across Workflows A, B, C, and D as required by Phase 8."""

    def test_workflow_a_simulation_pipeline(self):
        """Workflow A: Parameter configuration -> Tahoe & Reno simulation -> DataFrame trace -> Comparison."""
        params = SimulationParameters(
            algorithm="Tahoe",
            initial_cwnd=1.0,
            initial_ssthresh=16.0,
            num_rounds=25,
            loss_events={8: LossEventType.TIMEOUT}
        )
        params.validate()
        df, sim_summary = simulate_tcp(params)

        assert len(df) == 25
        assert df.iloc[0]["RTT_Round"] == 1
        assert df.iloc[0]["CWND"] == 2.0  # Slow start doubles from 1.0 to 2.0 MSS upon ACK receipt
        assert sim_summary["total_rounds"] == 25
        # Round 8 timeout resets CWND to 1.0 MSS and SSTHRESH to floor(19/2) = 9.0
        r8 = df[df["RTT_Round"] == 8].iloc[0]
        assert r8["CWND"] == 1.0
        assert r8["SSTHRESH"] == 9.0

        # Comparative run
        comp_df, summary = compare_algorithms(params)
        assert len(comp_df) == 25
        assert "Tahoe_CWND" in comp_df.columns
        assert "Reno_CWND" in comp_df.columns
        assert "reno_throughput_advantage_percent" in summary

    def test_workflow_b_network_experiment_pipeline(self):
        """Workflow B: Config validation -> Environment inspection -> Result schema -> JSON persistence."""
        config = NetworkExperimentConfig(
            experiment_id="E2E-EXP-1",
            bandwidth_mbps=20.0,
            delay_ms=10.0,
            loss_percentage=1.0,
            duration_seconds=5,
            tcp_congestion_algorithm="cubic"
        )
        config.validate()

        env = NetworkExperimentManager.verify_environment()
        assert "supported" in env
        assert "guidance" in env

        # Simulate completed result recording and persistence
        res = ExperimentResult(
            experiment_id=config.experiment_id,
            configured_bandwidth_mbps=config.bandwidth_mbps,
            configured_delay_ms=config.delay_ms,
            configured_loss_percentage=config.loss_percentage,
            measured_throughput_mbps=18.4,
            transfer_amount_mb=11.5,
            measured_retransmissions=2,
            measured_rtt_ms=20.5,
            experiment_duration_sec=5.0,
            tcp_congestion_algorithm=config.tcp_congestion_algorithm,
            status="Completed"
        )
        df = res.to_dataframe()
        assert df.iloc[0]["Throughput_Efficiency_Pct"] == 92.0

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            save_experiment_history([res], tmp_path)
            loaded = load_experiment_history(tmp_path)
            assert len(loaded) == 1
            assert loaded[0].experiment_id == "E2E-EXP-1"
            assert loaded[0].measured_throughput_mbps == 18.4
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_workflow_c_packet_analysis_pipeline(self):
        """Workflow C: PCAP validation -> Header extraction -> Filter -> Retransmission & Flag analysis."""
        sample_path = os.path.join(PROJECT_ROOT, "data", "sample_tcp_traffic.pcap")
        if os.path.exists(sample_path):
            validate_capture_file(sample_path)
            analyzer = PacketAnalyzer(sample_path)
            assert analyzer.file_size > 0

        # Dissection and filtering with mocked output
        tsv = (
            "frame.number\tframe.time_relative\tip.src\tip.dst\ttcp.srcport\ttcp.dstport\ttcp.seq\ttcp.ack\ttcp.len\ttcp.flags\t"
            "tcp.flags.syn\ttcp.flags.ack\ttcp.flags.fin\ttcp.flags.reset\ttcp.flags.push\ttcp.flags.urg\ttcp.flags.ece\ttcp.flags.cwr\t"
            "tcp.window_size_value\ttcp.analysis.retransmission\ttcp.analysis.fast_retransmission\ttcp.analysis.spurious_retransmission\t"
            "tcp.analysis.out_of_order\ttcp.analysis.duplicate_ack\ttcp.analysis.duplicate_ack_num\ttcp.analysis.ack_rtt\n"
            "1\t0.00\t192.168.1.10\t192.168.1.20\t5000\t80\t0\t0\t0\t0x0002\t1\t0\t0\t0\t0\t0\t0\t0\t64240\t\t\t\t\t\t\t\n"
            "2\t0.01\t192.168.1.20\t192.168.1.10\t80\t5000\t0\t1\t0\t0x0012\t1\t1\t0\t0\t0\t0\t0\t0\t65535\t\t\t\t\t\t\t0.01\n"
            "3\t0.02\t192.168.1.10\t192.168.1.20\t5000\t80\t1\t1\t1460\t0x0018\t0\t1\t0\t0\t1\t0\t0\t0\t64240\t\t\t\t\t\t\t\n"
            "4\t0.05\t192.168.1.10\t192.168.1.20\t5000\t80\t1\t1\t1460\t0x0018\t0\t1\t0\t0\t1\t0\t0\t0\t64240\t1\t0\t0\t0\t\t\t\n"
        )
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
            tmp.write(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
            tmp_path = tmp.name
        try:
            pa_obj = PacketAnalyzer(tmp_path)
            summary = pa_obj.parse_tshark_output(tsv)
            assert summary.total_tcp_packets == 4
            assert summary.retransmission_count == 1
            assert summary.retransmission_rate == 25.0
            assert summary.syn_count == 2

            df = summary.to_dataframe()
            retrans_only = PacketAnalyzer.filter_dataframe(df, retransmissions_only=True)
            assert len(retrans_only) == 1
            assert retrans_only.iloc[0]["packet_id"] == 4
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_workflow_d_performance_analytics_dashboard_pipeline(self):
        """Workflow D: Cross-module performance analytics aggregation & dynamic insight synthesis."""
        # Simulation trace
        df_sim = pd.DataFrame([
            {"RTT_Round": 1, "CWND": 1.0, "SSTHRESH": 16.0, "TCP_State": "Slow Start", "Loss_Event": "None", "Retransmission": False},
            {"RTT_Round": 2, "CWND": 2.0, "SSTHRESH": 16.0, "TCP_State": "Slow Start", "Loss_Event": "None", "Retransmission": False},
            {"RTT_Round": 3, "CWND": 4.0, "SSTHRESH": 16.0, "TCP_State": "Slow Start", "Loss_Event": "None", "Retransmission": False},
            {"RTT_Round": 4, "CWND": 8.0, "SSTHRESH": 16.0, "TCP_State": "Slow Start", "Loss_Event": "None", "Retransmission": False},
            {"RTT_Round": 5, "CWND": 4.0, "SSTHRESH": 4.0, "TCP_State": "Slow Start", "Loss_Event": "Timeout", "Retransmission": True},
        ])
        sim_metrics = calculate_simulation_metrics(df_sim)
        assert sim_metrics["peak_cwnd"] == 8.0

        chart = build_state_residency_chart(sim_metrics["state_counts"])
        assert chart is not None

        exp_result = ExperimentResult("E2E-EXP", 50.0, 10.0, 1.0, 44.5, 55.6, 2, 20.1, 10.0, "cubic")
        pkt_summary = PacketAnalysisSummary("test.pcap", 100, 100, 2, 3, 10.0)

        insights = generate_automatic_performance_insights(
            sim_metrics=sim_metrics,
            comp_summary={"tahoe_average_cwnd": 10.0, "reno_average_cwnd": 13.0, "reno_throughput_advantage_percent": 30.0},
            exp_result=exp_result,
            pkt_summary=pkt_summary
        )

        assert len(insights) == 4
        for item in insights:
            assert len(item["title"]) > 0
            assert len(item["body"]) > 0


class TestPythonNetworkEmulator:
    """Verifies the Python-based Network Emulation engine operating on Windows 10."""

    def test_default_emulation_execution(self):
        config = NetworkExperimentConfig(
            experiment_id="TEST-DEFAULT",
            bandwidth_mbps=10.0,
            delay_ms=20.0,
            loss_percentage=0.0,
            buffer_size_packets=50,
            duration_seconds=5,
            tcp_congestion_algorithm="reno"
        )
        emulator = PythonNetworkEmulator(config)
        res = emulator.run()

        assert res.status == "Completed"
        assert res.measured_throughput_mbps > 0.0
        assert res.transfer_amount_mb > 0.0
        assert res.is_simulated is True
        assert res.configured_buffer_size == 50
        assert res.time_series_data is not None
        assert len(res.time_series_data) > 0

        first_step = res.time_series_data[0]
        required_keys = ["Time_Sec", "RTT_Round", "CWND", "SSTHRESH", "Throughput_Mbps", "Buffer_Occupancy", "RTT_Ms", "TCP_State"]
        for key in required_keys:
            assert key in first_step, f"Missing key '{key}' in time series data"

    def test_bandwidth_throttling_ceiling(self):
        config = NetworkExperimentConfig(
            experiment_id="TEST-BW-CEIL",
            bandwidth_mbps=5.0,
            delay_ms=10.0,
            loss_percentage=0.0,
            duration_seconds=5
        )
        emulator = PythonNetworkEmulator(config)
        res = emulator.run()
        # Simulated throughput cannot exceed link bandwidth
        assert res.measured_throughput_mbps <= 5.0

    def test_propagation_delay_increases_rtt(self):
        cfg_low = NetworkExperimentConfig(
            experiment_id="LOW-DELAY",
            bandwidth_mbps=20.0,
            delay_ms=5.0,
            duration_seconds=3
        )
        cfg_high = NetworkExperimentConfig(
            experiment_id="HIGH-DELAY",
            bandwidth_mbps=20.0,
            delay_ms=40.0,
            duration_seconds=3
        )
        res_low = PythonNetworkEmulator(cfg_low).run()
        res_high = PythonNetworkEmulator(cfg_high).run()

        assert res_high.measured_rtt_ms > res_low.measured_rtt_ms
        assert res_high.measured_rtt_ms >= 80.0  # 2 * 40 ms base RTT

    def test_router_buffer_size_tail_drop(self):
        cfg_small = NetworkExperimentConfig(
            experiment_id="SMALL-BUF",
            bandwidth_mbps=25.0,
            delay_ms=20.0,
            loss_percentage=0.0,
            buffer_size_packets=5,
            duration_seconds=6
        )
        res_small = PythonNetworkEmulator(cfg_small).run()
        # A 5-packet buffer under 25 Mbps and 40 ms RTT (BDP ~ 83 packets) must experience buffer drops
        assert res_small.buffer_drops > 0
        assert res_small.measured_retransmissions > 0

    def test_packet_loss_triggers_retransmissions(self):
        cfg_loss = NetworkExperimentConfig(
            experiment_id="LOSS-EXP",
            bandwidth_mbps=15.0,
            delay_ms=15.0,
            loss_percentage=5.0,
            duration_seconds=5,
            random_seed=42
        )
        res = PythonNetworkEmulator(cfg_loss).run()
        assert res.random_drops > 0
        assert res.measured_retransmissions > 0

    def test_tcp_reno_vs_tahoe_under_loss(self):
        cfg_reno = NetworkExperimentConfig(
            experiment_id="RENO-RUN",
            bandwidth_mbps=15.0,
            delay_ms=15.0,
            loss_percentage=2.0,
            duration_seconds=6,
            tcp_congestion_algorithm="reno",
            random_seed=123
        )
        cfg_tahoe = NetworkExperimentConfig(
            experiment_id="TAHOE-RUN",
            bandwidth_mbps=15.0,
            delay_ms=15.0,
            loss_percentage=2.0,
            duration_seconds=6,
            tcp_congestion_algorithm="tahoe",
            random_seed=123
        )
        res_reno = PythonNetworkEmulator(cfg_reno).run()
        res_tahoe = PythonNetworkEmulator(cfg_tahoe).run()

        assert res_reno.status == "Completed"
        assert res_tahoe.status == "Completed"
        # Reno preserves higher or equal throughput due to Fast Recovery
        assert res_reno.measured_throughput_mbps >= res_tahoe.measured_throughput_mbps

    def test_experiment_dataframe_and_dict_serialization(self):
        cfg = NetworkExperimentConfig(
            experiment_id="SERIAL-TEST",
            bandwidth_mbps=10.0,
            delay_ms=10.0,
            buffer_size_packets=30,
            duration_seconds=3
        )
        res = PythonNetworkEmulator(cfg).run()
        df = res.to_dataframe()
        assert "Buffer_Size_Packets" in df.columns
        assert "Buffer_Drops" in df.columns
        assert "Random_Drops" in df.columns
        assert df.iloc[0]["Buffer_Size_Packets"] == 30

        d = res.to_dict()
        assert d["configured_buffer_size"] == 30
        res2 = ExperimentResult.from_dict(d)
        assert res2.configured_buffer_size == 30
        assert res2.experiment_id == "SERIAL-TEST"

    def test_manager_verify_environment_windows_ready(self):
        env = NetworkExperimentManager.verify_environment()
        assert env["supported"] is True
        assert env["engine"] == "Python Network Emulator"
        assert "Windows" in env["guidance"] or "verified" in env["guidance"].lower()


if __name__ == "__main__":
    print("=" * 70)
    print("EXECUTING TCP CONGESTION CONTROL & PACKET ANALYSIS TEST SUITE (PHASE 8)")
    print("=" * 70)

    test_classes = [
        TestSimulationParametersValidation,
        TestSlowStart,
        TestCongestionAvoidance,
        TestTCPTahoeAlgorithm,
        TestTCPRenoAlgorithm,
        TestTimeoutHandling,
        TestMultipleCongestionEvents,
        TestMaximumCWND,
        TestRandomSeedReproducibility,
        TestDataFrameColumnsAndMetrics,
        TestDataStructures,
        TestNetworkExperimentValidation,
        TestIPerf3OutputParsing,
        TestNetworkExperimentEnvironmentAndManager,
        TestHelperUtilities,
        TestPacketCaptureValidation,
        TestTSharkOutputParsing,
        TestPacketDataFrameFiltering,
        TestPacketAnalyzerExecutionAndSafety,
        TestPerformanceAnalytics,
        TestEndToEndIntegrationWorkflows,
        TestPythonNetworkEmulator,
    ]

    total_tests = 0
    passed_tests = 0

    for test_cls in test_classes:
        instance = test_cls()
        test_methods = [m for m in dir(instance) if m.startswith("test_")]
        print(f"\nRunning {test_cls.__name__} ({len(test_methods)} tests)...")
        for method_name in test_methods:
            method = getattr(instance, method_name)
            total_tests += 1
            try:
                method()
                passed_tests += 1
                print(f"  [PASS] {method_name}")
            except Exception as e:
                print(f"  [FAIL] {method_name}: {e}")
                raise

    print("\n" + "=" * 70)
    print(f"ALL {passed_tests} / {total_tests} TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

