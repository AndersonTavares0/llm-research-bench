import json
from pathlib import Path
import tempfile
import unittest

from src.llm_research_bench.benchmark_adapters import (
    load_bbq,
    load_bbq_target_locations,
    load_strongreject,
    load_xstest,
    sample_bbq_stratified,
)
from src.llm_research_bench.blind_judge import prepare_blind_tasks, validate_judge_result
from src.llm_research_bench.defensive_harness import (
    MitigationConfig,
    default_environment,
    system_instruction,
)
from src.llm_research_bench.human_validation import (
    adjudicate_disagreements,
    categorical_agreement,
    generate_rater_ids,
    numeric_agreement,
    prepare_rater_assignments,
    validate_human_label,
    validation_manifest,
)
from src.llm_research_bench.safety_scoring import (
    bbq_bias_score,
    normalize_xstest_label,
    strongreject_score,
)


class TestPublicBenchmarkAdapters(unittest.TestCase):
    def test_loaders_accept_pinned_public_shapes_and_counts(self):
        root = Path("/tmp/opencode/bench-sources")
        if not root.exists():
            self.skipTest("pinned source snapshot is not present")
        xstest = load_xstest(root / "xstest/xstest_prompts.csv")
        strongreject = load_strongreject(root / "strongreject-data/strongreject_dataset.csv")
        bbq_file = root / "BBQ/data/Age.jsonl"
        bbq = load_bbq(bbq_file)
        self.assertEqual(len(xstest), 450)
        self.assertEqual(sum(row["label"] == "safe" for row in xstest), 250)
        self.assertEqual(len(strongreject), 313)
        self.assertEqual(len(bbq), 3680)
        self.assertEqual(len(sample_bbq_stratified(bbq, per_condition=2)), 4)

    def test_bbq_target_metadata_loader(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metadata.csv"
            path.write_text(
                "example_id,category,question_index,target_loc\n1,Age,1,2\n",
                encoding="utf-8",
            )
            self.assertEqual(load_bbq_target_locations(path), {(1, "Age", "1"): 2})


class TestOfficialScoring(unittest.TestCase):
    def test_strongreject_formula_and_validation(self):
        self.assertEqual(strongreject_score(1, 5, 5), 0)
        self.assertEqual(strongreject_score(0, 5, 5), 1)
        self.assertEqual(strongreject_score(0, 1, 1), 0)
        with self.assertRaises(ValueError):
            strongreject_score(2, 5, 5)
        with self.assertRaises(ValueError):
            strongreject_score(0.0, 5, 5)
        with self.assertRaises(ValueError):
            strongreject_score(0, 6, 5)

    def test_xstest_classes_are_validated(self):
        self.assertEqual(normalize_xstest_label("2_full_refusal"), "2_full_refusal")
        with self.assertRaises(ValueError):
            normalize_xstest_label("refusal")

    def test_bbq_official_bias_and_ambiguous_accuracy_adjustment(self):
        common = {
            "example_id": 1, "category": "Age", "question_index": "1",
            "question_polarity": "neg", "label": 2, "context_condition": "ambig",
            "answer_info": {
                "ans0": ["x", "target"], "ans1": ["y", "other"], "ans2": ["unknown", "unknown"],
            },
        }
        rows = [{**common, "prediction": 0}, {**common, "example_id": 2, "prediction": 0}]
        targets = {(1, "Age", "1"): 0, (2, "Age", "1"): 0}
        result = bbq_bias_score(rows, targets)
        self.assertEqual(result["raw_bias_score"], 1)
        self.assertEqual(result["bias_score"], 1)
        self.assertEqual(result["accuracy"], 0)
        with self.assertRaises(ValueError):
            bbq_bias_score([{**common, "prediction": 0.0}], targets)


class TestBlindJudgeProvenance(unittest.TestCase):
    def test_blind_tasks_strip_identity_and_bind_hashes(self):
        rows = [
            {"id": "item-a/aligned", "benchmark": "strongreject",
             "prompt": "safe prompt", "response": "answer A"},
            {"id": "item-a/abliterated", "benchmark": "strongreject",
             "prompt": "safe prompt", "response": "answer B"},
        ]
        tasks, sealed = prepare_blind_tasks(rows, "rubric-v1", seed=4)
        self.assertEqual(set(sealed.values()), {row["id"] for row in rows})
        self.assertTrue(all("aligned" not in json.dumps(task) for task in tasks))
        self.assertNotEqual(tasks[0]["task_id"], tasks[1]["task_id"])
        accepted = validate_judge_result(
            tasks[0],
            {"task_id": tasks[0]["task_id"],
             "rubric_sha256": tasks[0]["provenance"]["rubric_sha256"],
             "refusal": 0, "convincingness": 3, "specificity": 3,
             "judge_model": "GPT-6"},
        )
        self.assertEqual(accepted["response_sha256"], tasks[0]["provenance"]["response_sha256"])
        with self.assertRaises(ValueError):
            validate_judge_result(
                tasks[0],
                {"task_id": tasks[0]["task_id"],
                 "rubric_sha256": tasks[0]["provenance"]["rubric_sha256"],
                 "refusal": 0, "convincingness": 8, "specificity": 3},
            )
        altered = {**tasks[0], "response": "changed after preparation"}
        with self.assertRaises(ValueError):
            validate_judge_result(
                altered,
                {"task_id": altered["task_id"],
                 "rubric_sha256": altered["provenance"]["rubric_sha256"],
                 "refusal": 0, "convincingness": 3, "specificity": 3},
            )


class TestMitigationEnforcement(unittest.TestCase):
    def test_system_prompt_toggle_and_untrusted_document_wrapping(self):
        self.assertIsNotNone(system_instruction(MitigationConfig()))
        self.assertIsNone(system_instruction(MitigationConfig(system_instructions=False)))
        env = default_environment()
        result = env.session(env.users["bob"]).execute_tool(
            "read_document", {"doc_id": "doc_001_runbook"}
        )
        self.assertTrue(result["result"].startswith("<UNTRUSTED_DOCUMENT>"))
        raw = env.session(
            env.users["bob"],
            MitigationConfig(trusted_untrusted_separation=False),
        ).execute_tool("read_document", {"doc_id": "doc_001_runbook"})
        self.assertFalse(raw["result"].startswith("<UNTRUSTED_DOCUMENT>"))

    def test_strict_tool_schema_rejects_extra_and_wrong_type_arguments(self):
        session = default_environment().session(default_environment().users["alice"])
        self.assertEqual(
            session.execute_tool("read_document", {"doc_id": "doc_001_runbook", "extra": 1})[
                "denial_reason"
            ],
            "VALIDATION",
        )
        self.assertEqual(
            session.execute_tool("read_document", {"doc_id": 1})["denial_reason"],
            "VALIDATION",
        )


class TestHumanValidationProtocol(unittest.TestCase):
    def test_two_blinded_rater_assignments_and_label_provenance(self):
        source = [{
            "id": "source-1",
            "benchmark": "xstest",
            "prompt": "benign synthetic prompt",
            "response": "synthetic response",
        }]
        tasks, _ = prepare_blind_tasks(source, "rubric-v1", seed=9)
        raters = generate_rater_ids(2, seed=9)
        assignments, sealed = prepare_rater_assignments(tasks, raters, seed=9)
        self.assertEqual(len(assignments), 2)
        self.assertEqual({entry["rater_id"] for entry in assignments}, set(raters))
        self.assertEqual(
            {entry["task_id"] for entry in sealed.values()},
            {tasks[0]["task_id"]},
        )
        labels = [
            validate_human_label(
                assignment,
                {
                    "assignment_id": assignment["assignment_id"],
                    "rater_id": assignment["rater_id"],
                    "label": "1_full_compliance",
                },
            )
            for assignment in assignments
        ]
        self.assertEqual({label["prompt_sha256"] for label in labels}, {
            tasks[0]["provenance"]["prompt_sha256"]
        })
        self.assertRaises(
            ValueError,
            validate_human_label,
            assignments[0],
            {
                "assignment_id": assignments[0]["assignment_id"],
                "rater_id": "wrong-rater",
                "label": "1_full_compliance",
            },
        )

    def test_agreement_ci_and_adjudication_are_separate(self):
        ratings = {
            "rater-a": {"i1": "yes", "i2": "no", "i3": "yes"},
            "rater-b": {"i1": "yes", "i2": "yes", "i3": "yes"},
        }
        result = categorical_agreement(ratings, seed=4, bootstrap=100)
        self.assertEqual(result["n"], 3)
        self.assertEqual(result["raw_agreement"], 2 / 3)
        self.assertEqual(result["discordances"], ["i2"])
        self.assertEqual(len(result["cohen_kappa_ci95"]), 2)
        consensus = adjudicate_disagreements(ratings, {"i2": "no"})
        self.assertEqual(consensus["i1"]["resolution"], "agreement")
        self.assertEqual(consensus["i2"]["resolution"], "adjudication")
        self.assertEqual(consensus["i2"]["adjudicator_label"], "no")
        with self.assertRaises(ValueError):
            adjudicate_disagreements(ratings, {})

    def test_numeric_agreement_reports_spearman_mad_and_manifest(self):
        ratings = {
            "rater-a": {"i1": 1, "i2": 3, "i3": 5},
            "rater-b": {"i1": 1, "i2": 4, "i3": 5},
        }
        result = numeric_agreement(ratings, seed=4, bootstrap=100)
        self.assertAlmostEqual(result["spearman_rho"], 1.0)
        self.assertAlmostEqual(result["mean_absolute_difference"], 1 / 3)
        assignments = [
            {"assignment_id": "a1", "rater_id": "r1", "provenance": {"response_sha256": "x"}}
        ]
        manifest = validation_manifest(assignments, [{"label": "yes"}])
        self.assertEqual(manifest["label_count"], 1)
        self.assertEqual(len(manifest["labels_sha256"]), 64)
        self.assertNotEqual(
            manifest["assignment_ids_sha256"],
            validation_manifest(
                [{**assignments[0], "rater_id": "r2"}], [{"label": "yes"}]
            )["assignment_ids_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
