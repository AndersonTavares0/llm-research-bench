import unittest
import numpy as np
from src.llm_research_bench.statistical_analysis import compute_sample_stats, compute_cohens_d


class TestStatisticalEngine(unittest.TestCase):
    def test_compute_sample_stats(self):
        samples = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = compute_sample_stats(samples)
        self.assertEqual(stats["n"], 5)
        self.assertEqual(stats["mean"], 30.0)
        self.assertEqual(stats["median"], 30.0)
        self.assertTrue(stats["ci_low"] < 30.0 < stats["ci_high"])
        self.assertAlmostEqual(stats["std"], np.std(samples, ddof=1), places=2)

    def test_compute_cohens_d(self):
        group1 = [40.0, 42.0, 44.0, 46.0]
        group2 = [30.0, 32.0, 34.0, 36.0]
        d = compute_cohens_d(group1, group2)
        # Difference in means is 10.0, std of each is ~2.58 -> d ~ 3.87
        self.assertTrue(d > 2.0)

    def test_edge_case_single_element(self):
        stats = compute_sample_stats([42.0])
        self.assertEqual(stats["n"], 1)
        self.assertEqual(stats["mean"], 42.0)
        self.assertEqual(stats["std"], 0.0)
        self.assertEqual(stats["ci_95_margin"], 0.0)


if __name__ == "__main__":
    unittest.main()
