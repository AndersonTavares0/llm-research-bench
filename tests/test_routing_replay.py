import unittest

from src.llm_research_bench.routing_replay import (
    ARMS,
    DATASETS,
    STATION,
    analyze,
    mcnemar_exact,
    pair_rows,
    summarize,
)


def row(doc_id, prompt_hash, acc, acc_norm=0):
    doc = {"id": doc_id} if doc_id is not None else {"question": "q"}
    return {"doc": doc, "prompt_hash": prompt_hash, "acc": acc, "acc_norm": acc_norm}


class TestPairing(unittest.TestCase):
    def test_mismatched_item_fails_closed(self):
        left = [row("a", "p", 1)]
        right = [row("b", "p", 1)]
        with self.assertRaises(ValueError):
            pair_rows(left, right, "synthetic")

    def test_mismatched_prompt_hash_fails_closed(self):
        left = [row("a", "p1", 1)]
        right = [row("a", "p2", 1)]
        with self.assertRaises(ValueError):
            pair_rows(left, right, "synthetic")

    def test_unequal_row_counts_fail_closed(self):
        with self.assertRaises(ValueError):
            pair_rows([row("a", "p", 1)], [], "synthetic")

    def test_rows_without_doc_id_pair_on_full_document(self):
        left = [row(None, "p", 1)]
        right = [row(None, "p", 0)]
        self.assertEqual(len(pair_rows(left, right, "synthetic")), 1)

        drifted = [{"doc": {"question": "other"}, "prompt_hash": "p", "acc": 0, "acc_norm": 0}]
        with self.assertRaises(ValueError):
            pair_rows([row(None, "p", 1)], drifted, "synthetic")


class TestSummary(unittest.TestCase):
    def test_cells_and_oracle_ceiling(self):
        # both=2, left_only=1, right_only=3, both_wrong=4 (n=10)
        pairs = (
            [(row("x", "p", 1, 1), row("x", "p", 1, 1))] * 2
            + [(row("x", "p", 1), row("x", "p", 0))]
            + [(row("x", "p", 0), row("x", "p", 1))] * 3
            + [(row("x", "p", 0), row("x", "p", 0))] * 4
        )
        summary = summarize(pairs, "synthetic", "acc")
        self.assertEqual(
            summary["cells"],
            {"both_correct": 2, "left_only": 1, "right_only": 3, "both_wrong": 4},
        )
        self.assertEqual(summary["accuracy"], {
            "left": 0.3, "right": 0.5, "oracle": 0.6, "oracle_gain_over_best_arm": 0.1,
        })
        self.assertEqual(summary["agreement_pct"], 60.0)
        # oracle can never be below the better arm
        self.assertGreaterEqual(summary["accuracy"]["oracle"], summary["accuracy"]["right"])
        ci = summary["ci95_clopper_pearson"]["oracle"]
        self.assertLessEqual(ci["lower"], 60.0)
        self.assertGreaterEqual(ci["upper"], 60.0)

    def test_mcnemar_extremes(self):
        self.assertEqual(mcnemar_exact(0, 0), 1.0)
        self.assertGreater(mcnemar_exact(1, 1), 0.9)
        self.assertLess(mcnemar_exact(1, 20), 0.01)


class TestRecordedPair(unittest.TestCase):
    """The one recorded quant pair must still join cleanly (local checkpoint only)."""

    @unittest.skipUnless(
        STATION.joinpath(ARMS["q4_k_m"], "knowledge-mcq/meta.json").is_file(),
        "local-rtx3060ti campaign is gitignored; raw pair only exists on the recording host",
    )
    def test_recorded_arms_join_and_report(self):
        artifact = analyze()
        self.assertEqual(artifact["status"], "exploratory_analysis")
        for dataset in DATASETS:
            for metric in ("acc", "acc_norm"):
                result = artifact["results"][dataset][metric]
                self.assertEqual(result["n"], 100)
                self.assertEqual(result["cells"]["both_correct"]
                                 + result["cells"]["left_only"]
                                 + result["cells"]["right_only"]
                                 + result["cells"]["both_wrong"], 100)
                self.assertGreaterEqual(
                    result["accuracy"]["oracle"],
                    max(result["accuracy"]["left"], result["accuracy"]["right"]),
                )
        self.assertIn("cross_model_cascade_replay", artifact["blocked"])


if __name__ == "__main__":
    unittest.main()
