import sys
import unittest
from pathlib import Path
import numpy as np

# Dynamically ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.llm_research_bench.statistical_engine import calculate_metrics_with_ci
from src.llm_research_bench.statistical_analysis import compute_sample_stats, compute_cohens_d


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
        self.assertEqual(metrics["mean"], 0.0)
        self.assertEqual(metrics["ci_95_margin"], 0.0)

    def test_calculate_metrics_with_ci_single_value(self):
        metrics = calculate_metrics_with_ci([35.5])
        self.assertEqual(metrics["n"], 1)
        self.assertEqual(metrics["mean"], 35.5)
        self.assertEqual(metrics["std_dev"], 0.0)
        self.assertEqual(metrics["ci_95_margin"], 0.0)

    def test_compute_sample_stats_empty(self):
        stats = compute_sample_stats([])
        self.assertEqual(stats["n"], 0)
        self.assertEqual(stats["mean"], 0.0)
        self.assertEqual(stats["ci_95_margin"], 0.0)

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
        d = compute_cohens_d([10.0, 10.0], [10.0, 10.0])
        self.assertEqual(d, 0.0)


if __name__ == "__main__":
    unittest.main()
