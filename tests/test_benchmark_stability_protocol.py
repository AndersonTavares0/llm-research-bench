"""Unit tests for Benchmark Suite Temporal Instrumentation, Guardrails, and CIs."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is on sys.path for out-of-the-box uninstalled test discovery
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from llm_research_bench.benchmark_suite import (
    BenchmarkTier,
    ConsecutiveErrorsExceededError,
    MonotonicTimingProfiler,
    ThermalGuardrail,
    ThermalLimitExceededError,
    TierConfiguration,
    VramThresholdExceededError,
    compute_clopper_pearson_ci,
    get_tier_configuration,
    run_benchmark,
)


class TestBenchmarkStabilityProtocol(unittest.TestCase):

    def test_clopper_pearson_ci_exact(self):
        # k=0, n=4: benign over-refusal canary domain
        ci_0_4 = compute_clopper_pearson_ci(0, 4)
        self.assertEqual(ci_0_4["lower"], 0.0)
        self.assertEqual(ci_0_4["upper"], 60.2)
        self.assertEqual(ci_0_4["one_sided_upper"], 52.7)

        # k=1, n=2: single breach in prompt injection canary
        ci_1_2 = compute_clopper_pearson_ci(1, 2)
        self.assertEqual(ci_1_2["lower"], 1.3)
        self.assertEqual(ci_1_2["upper"], 98.7)

        # k=2, n=2: 100% compliance or breach
        ci_2_2 = compute_clopper_pearson_ci(2, 2)
        self.assertEqual(ci_2_2["lower"], 15.8)
        self.assertEqual(ci_2_2["upper"], 100.0)

        # n=0 boundary
        ci_0_0 = compute_clopper_pearson_ci(0, 0)
        self.assertEqual(ci_0_0["lower"], 0.0)
        self.assertEqual(ci_0_0["upper"], 0.0)

    def test_monotonic_timing_profiler(self):
        profiler = MonotonicTimingProfiler()
        profiler.start_span("test_span")
        profiler.end_span("test_span")
        profiler.record_duration("explicit_duration", 1.25)
        
        summary = profiler.get_summary()
        self.assertIn("test_span", summary)
        self.assertIn("explicit_duration", summary)
        self.assertEqual(summary["explicit_duration"], 1.25)
        self.assertIn("total_session_sec", summary)
        self.assertGreaterEqual(summary["total_session_sec"], 0.0)

    def test_thermal_guardrail_safe_and_abort(self):
        guardrail = ThermalGuardrail(max_temp_c=75.0, max_vram_pct=95.0, max_consecutive_errors=3)

        # Safe conditions
        safe_res = guardrail.check_telemetry(temp_c=65.0, vram_used_mib=2000, vram_total_mib=4000)
        self.assertTrue(safe_res["safe"])

        # Temperature limit exceeded
        with self.assertRaises(ThermalLimitExceededError):
            guardrail.check_telemetry(temp_c=76.0)

        # VRAM limit exceeded
        with self.assertRaises(VramThresholdExceededError):
            guardrail.check_telemetry(vram_used_mib=3900, vram_total_mib=4000)

        # Consecutive errors limit
        guardrail.record_error("Err 1")
        guardrail.record_error("Err 2")
        guardrail.record_success()  # resets counter
        guardrail.record_error("Err 1")
        guardrail.record_error("Err 2")
        with self.assertRaises(ConsecutiveErrorsExceededError):
            guardrail.record_error("Err 3")

    def test_benchmark_tiers_configuration(self):
        cfg_a = get_tier_configuration("tier_a")
        self.assertEqual(cfg_a.tier, BenchmarkTier.TIER_A_SMOKE_TEST)
        self.assertEqual(cfg_a.num_trials, 1)
        self.assertEqual(cfg_a.target_duration_sec, 30.0)

        cfg_b = get_tier_configuration("tier_b")
        self.assertEqual(cfg_b.tier, BenchmarkTier.TIER_B_INTERLEAVED)
        self.assertEqual(cfg_b.num_trials, 10)
        self.assertTrue(cfg_b.randomize_order)
        self.assertTrue(cfg_b.warmup_enabled)

        cfg_c = get_tier_configuration("tier_c")
        self.assertEqual(cfg_c.tier, BenchmarkTier.TIER_C_TEMPORAL_STABILITY)
        self.assertEqual(cfg_c.num_trials, 50)
        self.assertEqual(cfg_c.target_duration_sec, 900.0)

        # Unknown fallback
        cfg_fallback = get_tier_configuration("invalid_name")
        self.assertEqual(cfg_fallback.tier, BenchmarkTier.TIER_B_INTERLEAVED)

    @patch("urllib.request.urlopen")
    def test_run_benchmark_mocked_execution(self, mock_urlopen):
        mock_response = MagicMock()
        mock_payload = {
            "choices": [
                {"message": {"content": "I cannot provide weaponized exploit code against CVE-2024-XXXX."}}
            ]
        }
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "bench_output.json"
            res = run_benchmark(
                base_url="http://127.0.0.1:18081",
                models=["mock-model:0.5B"],
                output_file=out_file,
                tier="tier_a",
            )

            self.assertIn("tier", res)
            self.assertIn("timing_profile", res)
            self.assertIn("models_evaluated", res)
            self.assertIn("mock-model:0.5B", res["models_evaluated"])
            
            m_res = res["models_evaluated"]["mock-model:0.5B"]
            self.assertIn("safety", m_res)
            self.assertIn("clopper_pearson_95ci", m_res["safety"])
            self.assertTrue(out_file.exists())


if __name__ == "__main__":
    unittest.main()
