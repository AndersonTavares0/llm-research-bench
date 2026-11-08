import json
import tempfile
import unittest
from pathlib import Path

from src.llm_research_bench.routing_replay import (
    ARMS,
    DATASETS,
    STATION,
    analyze,
    mcnemar_exact,
    pair_rows,
    summarize,
)


def row(doc_id, prompt_hash, acc, acc_norm=0, target="t", doc_hash="d"):
    doc = {"id": doc_id} if doc_id is not None else {"question": "q"}
    return {
        "doc": doc,
        "prompt_hash": prompt_hash,
        "target": target,
        "doc_hash": doc_hash,
        "acc": acc,
        "acc_norm": acc_norm,
    }


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

    def test_mismatched_target_fails_closed(self):
        left = [row("a", "p", 1, target="1")]
        right = [row("a", "p", 1, target="2")]
        with self.assertRaises(ValueError):
            pair_rows(left, right, "synthetic")

    def test_mismatched_doc_hash_fails_closed(self):
        left = [row("a", "p", 1, doc_hash="d1")]
        right = [row("a", "p", 1, doc_hash="d2")]
        with self.assertRaises(ValueError):
            pair_rows(left, right, "synthetic")

    def test_missing_label_fields_fail_closed(self):
        left = [row("a", "p", 1)]
        del left[0]["target"]
        with self.assertRaises(ValueError):
            pair_rows(left, [row("a", "p", 1)], "synthetic")

    def test_unequal_row_counts_fail_closed(self):
        with self.assertRaises(ValueError):
            pair_rows([row("a", "p", 1)], [], "synthetic")

    def test_rows_without_doc_id_pair_on_full_document(self):
        left = [row(None, "p", 1)]
        right = [row(None, "p", 0)]
        self.assertEqual(len(pair_rows(left, right, "synthetic")), 1)

        drifted = [row(None, "p", 1)]
        drifted[0]["doc"] = {"question": "other"}
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

    def test_missing_or_invalid_binary_observations_fail_closed(self):
        # Regression: null/non-binary observations used to be silently counted
        # as wrong, and missing keys only failed with a bare KeyError.
        base = row("x", "p", 1, 1)
        cases = {
            "missing acc": {"doc": {"id": "x"}, "prompt_hash": "p", "target": "t",
                            "doc_hash": "d", "acc_norm": 1},
            "null acc": {**base, "acc": None},
            "integer acc": {**base, "acc": 2},
            "negative acc": {**base, "acc": -1},
            "fractional acc": {**base, "acc": 0.5},
            "string acc": {**base, "acc": "1"},
            "boolean acc": {**base, "acc": True},
            "null acc_norm": {**base, "acc_norm": None},
            "integer acc_norm": {**base, "acc_norm": 2},
            "string acc_norm": {**base, "acc_norm": "0"},
        }
        for label, bad in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    summarize([(base, bad)], "synthetic", "acc")

    def test_one_invalid_observation_rejects_the_whole_summary(self):
        good = (row("x", "p", 1, 1), row("x", "p", 1, 1))
        bad = (row("x", "p", 0, 0), row("x", "p", None, 0))
        with self.assertRaises(ValueError):
            summarize([good, bad], "synthetic", "acc")

    def test_empty_pairs_fail_closed(self):
        with self.assertRaises(ValueError):
            summarize([], "synthetic", "acc")

    def test_integral_floats_are_accepted(self):
        pairs = [(row("x", "p", 1.0, 1.0), row("x", "p", 0.0, 0.0))]
        summary = summarize(pairs, "synthetic", "acc")
        self.assertEqual(summary["n"], 1)
        self.assertEqual(summary["cells"]["left_only"], 1)


class TestAnalyzeFixture(unittest.TestCase):
    """End-to-end analyze() run on a synthetic station tree (runs in CI)."""

    def _write_fixture(self, root):
        accs = {"q4_k_m": [1, 1, 0, 0], "q8_0": [1, 0, 1, 0]}
        for label, name in ARMS.items():
            arm = root / STATION / name / "knowledge-mcq"
            raw = arm / "raw" / "wnnhj7xv"
            raw.mkdir(parents=True)
            (arm / "meta.json").write_text(json.dumps({"model": {
                "file": f"{name}.gguf",
                "quantization": "Q4_K_M" if label == "q4_k_m" else "Q8_0",
                "hf_repo": f"org/{name}",
                "hf_revision": "rev",
                "sha256": "a" * 64,
                "size_bytes": 123,
            }}), encoding="utf-8")
            for dataset in DATASETS:
                lines = [
                    json.dumps({
                        "doc": {"id": f"doc-{index}"},
                        "prompt_hash": f"prompt-{index}",
                        "target": "t",
                        "doc_hash": f"hash-{index}",
                        "acc": acc,
                        "acc_norm": 0,
                    })
                    for index, acc in enumerate(accs[label])
                ]
                (raw / f"samples_{dataset}_fixture.jsonl").write_text(
                    "\n".join(lines) + "\n", encoding="utf-8"
                )

    def test_fixture_tree_is_analyzed_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            artifact = analyze(root=root)
            self.assertEqual(artifact["status"], "exploratory_analysis")
            self.assertEqual(artifact["models"]["q8_0"]["quantization"], "Q8_0")
            for dataset in DATASETS:
                result = artifact["results"][dataset]["acc"]
                self.assertEqual(result["n"], 4)
                self.assertEqual(result["cells"], {
                    "both_correct": 1, "left_only": 1,
                    "right_only": 1, "both_wrong": 1,
                })
                self.assertEqual(result["accuracy"], {
                    "left": 0.5, "right": 0.5, "oracle": 0.75,
                    "oracle_gain_over_best_arm": 0.25,
                })
                self.assertEqual(result["agreement_pct"], 50.0)
                self.assertEqual(result["mcnemar_exact_p"], 1.0)
                self.assertTrue(
                    artifact["inputs"][dataset]["q4_k_m"]["path"].endswith(
                        f"samples_{dataset}_fixture.jsonl"
                    )
                )

    def test_ambiguous_samples_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            raw = root / STATION / ARMS["q4_k_m"] / "knowledge-mcq" / "raw" / "wnnhj7xv"
            original = raw / "samples_arc_challenge_fixture.jsonl"
            (raw / "samples_arc_challenge_stale.jsonl").write_text(
                original.read_text(encoding="utf-8"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                analyze(root=root)


class TestCommittedArtifact(unittest.TestCase):
    def test_committed_artifact_arithmetic_is_internally_consistent(self):
        # The raw campaign is gitignored, so this guards the tracked artifact
        # against silent drift even on a fresh clone.
        path = Path(__file__).resolve().parents[1] / "results/analysis/quant-cascade-oracle-v1.json"
        artifact = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "exploratory_analysis")
        for dataset in DATASETS:
            for metric in ("acc", "acc_norm"):
                result = artifact["results"][dataset][metric]
                cells = result["cells"]
                n = result["n"]
                self.assertEqual(sum(cells.values()), n)
                expected = {
                    "left": round((cells["both_correct"] + cells["left_only"]) / n, 6),
                    "right": round((cells["both_correct"] + cells["right_only"]) / n, 6),
                    "oracle": round(
                        (cells["both_correct"] + cells["left_only"] + cells["right_only"]) / n,
                        6,
                    ),
                }
                for arm, value in expected.items():
                    self.assertEqual(result["accuracy"][arm], value)
                self.assertEqual(
                    result["mcnemar_exact_p"],
                    mcnemar_exact(cells["left_only"], cells["right_only"]),
                )

    def test_committed_paired_rows_recompute_the_report(self):
        # The embedded derived rows are the fresh-clone reproducibility unit:
        # every reported statistic must follow from them alone.
        path = Path(__file__).resolve().parents[1] / "results/analysis/quant-cascade-oracle-v1.json"
        artifact = json.loads(path.read_text(encoding="utf-8"))
        for dataset in DATASETS:
            rows = artifact["paired_rows"][dataset]
            self.assertEqual(len(rows), 100)
            self.assertEqual(len({r["item_sha256"] for r in rows}), 100)
            pairs = [
                (r["left"], r["right"])
                for r in rows
            ]
            for metric in ("acc", "acc_norm"):
                recomputed = summarize(pairs, dataset, metric)
                committed = artifact["results"][dataset][metric]
                for key in ("n", "cells", "accuracy", "agreement_pct", "mcnemar_exact_p"):
                    self.assertEqual(recomputed[key], committed[key], f"{dataset} {metric} {key}")


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
