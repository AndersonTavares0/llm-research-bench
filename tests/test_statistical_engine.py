import sys
import unittest
from pathlib import Path
import json
import tempfile
import numpy as np

# Dynamically ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.llm_research_bench.statistical_engine import calculate_metrics_with_ci
from src.llm_research_bench.statistical_analysis import (
    bootstrap_cohens_d_ci,
    compute_cohens_d,
    compute_sample_stats,
    holm_adjust,
    run_full_statistical_analysis,
    validate_analysis_samples,
)


class TestStatisticalEngine(unittest.TestCase):
    def test_calculate_metrics_with_ci_basic(self):
        # 15 samples representing N=15 benchmark runs
        samples = [42.0 + (i % 3) for i in range(15)]
        metrics = calculate_metrics_with_ci(samples)
        self.assertEqual(metrics["n"], 15)
        self.assertAlmostEqual(metrics["mean"], np.mean(samples), places=2)
        self.assertTrue(metrics["ci_95_margin"] > 0.0)
        self.assertTrue(metrics["ci_low"] < metrics["mean"] < metrics["ci_high"])

    def test_calculate_metrics_with_ci_empty(self):
        metrics = calculate_metrics_with_ci([])
        self.assertEqual(metrics["n"], 0)
        self.assertIsNone(metrics["mean"])
        self.assertIsNone(metrics["std_dev"])
        self.assertIsNone(metrics["ci_95_margin"])

    def test_calculate_metrics_with_ci_single_value(self):
        metrics = calculate_metrics_with_ci([35.5])
        self.assertEqual(metrics["n"], 1)
        self.assertEqual(metrics["mean"], 35.5)
        self.assertIsNone(metrics["std_dev"])
        self.assertIsNone(metrics["ci_95_margin"])

    def test_compute_sample_stats_empty(self):
        stats = compute_sample_stats([])
        self.assertEqual(stats["n"], 0)
        self.assertIsNone(stats["mean"])
        self.assertIsNone(stats["median"])
        self.assertIsNone(stats["std"])
        self.assertIsNone(stats["q1"])
        self.assertIsNone(stats["q3"])
        self.assertIsNone(stats["iqr"])
        self.assertIsNone(stats["min"])
        self.assertIsNone(stats["max"])

    def test_full_analysis_fails_closed_without_independent_replicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            controlled = Path(tmp) / "results" / "controlled_experiments"
            controlled.mkdir(parents=True)
            historical = controlled / "statistical_summary.json"
            historical.write_text('{"preserved": true}', encoding="utf-8")
            (controlled / "mtp_ablation_results.json").write_text(
                json.dumps({"models": {
                    "gemma4:E2B": {"individual_runs_tok_s": []},
                    "gemma4:MTP": {"individual_runs_tok_s": [1.0, 2.0, 3.0]},
                }}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "repeated queries"):
                run_full_statistical_analysis(Path(tmp))
            self.assertEqual(historical.read_text(encoding="utf-8"), '{"preserved": true}')

    def test_analysis_rejects_nonfinite_observations(self):
        with self.assertRaisesRegex(ValueError, "at least three finite"):
            validate_analysis_samples("MTP", ("model", [1.0, np.nan, 3.0]))

    def test_compute_sample_stats_rich(self):
        samples = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = compute_sample_stats(samples)
        self.assertEqual(stats["n"], 5)
        self.assertEqual(stats["mean"], 30.0)
        self.assertEqual(stats["median"], 30.0)
        self.assertEqual(stats["iqr"], 20.0)
        self.assertTrue(stats["ci_low"] < 30.0 < stats["ci_high"])

    def test_compute_cohens_d(self):
        group1 = [40.0, 42.0, 44.0, 46.0]
        group2 = [30.0, 32.0, 34.0, 36.0]
        d = compute_cohens_d(group1, group2)
        self.assertTrue(d > 2.0)

    def test_compute_cohens_d_zero_variance(self):
        # 0/0 pooled SD: the standardized effect is undefined, not zero.
        self.assertIsNone(compute_cohens_d([10.0, 10.0], [10.0, 10.0]))

    def test_bootstrap_cohens_d_ci_is_deterministic_and_brackets_estimate(self):
        group1 = [40.0, 42.0, 44.0, 46.0, 48.0]
        group2 = [30.0, 32.0, 34.0, 36.0, 38.0]
        d = compute_cohens_d(group1, group2)
        ci = bootstrap_cohens_d_ci(group1, group2, n_resamples=500)
        self.assertEqual(ci, bootstrap_cohens_d_ci(group1, group2, n_resamples=500))
        self.assertLess(ci[0], d)
        self.assertGreater(ci[1], d)

    def test_holm_adjust_controls_family_wise_error(self):
        adjusted = holm_adjust({"a": 0.01, "b": 0.02, "c": 0.5})
        self.assertEqual(adjusted["a"], 0.03)
        self.assertEqual(adjusted["b"], 0.04)
        self.assertEqual(adjusted["c"], 0.5)


if __name__ == "__main__":
    unittest.main()
