import json
from pathlib import Path
import unittest

from src.llm_research_bench.evaluators import (
    aggregate_static_triage_metrics,
    score_static_triage_case,
    score_static_triage_run,
)


class TestStaticCybersecurityEvaluator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "datasets" / "cybersecurity_static_triage_v1.json"
        cls.cases = json.loads(path.read_text(encoding="utf-8"))

    def test_dataset_has_unique_ids_and_expected_line_ranges(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in self.cases:
            self.assertEqual(case["split"], "exploratory")
            for finding in case["expected_findings"]:
                self.assertGreaterEqual(finding["line"], 1)
                self.assertLessEqual(finding["line"], len(case["code"].splitlines()))

    def test_exact_finding_and_safe_negative_control(self):
        vulnerable = {"id": "v", "code": "a\nb\nc\nd", "expected_findings": [{"weakness_id": "CWE-78", "line": 4}]}
        safe = {"id": "n", "code": "pass", "expected_findings": []}
        hit = score_static_triage_case(vulnerable, '{"findings":[{"weakness_id":"CWE-78","line":4}]}')
        negative = score_static_triage_case(safe, '{"findings":[]}')
        self.assertEqual((hit["true_positive"], hit["false_negative"], hit["f1"]), (1, 0, 1.0))
        self.assertTrue(negative["true_negative_case"])
        self.assertIsNone(negative["precision"])

    def test_missed_finding_has_zero_recall_and_f1(self):
        case = {"id": "v", "code": "vulnerable", "expected_findings": [{"weakness_id": "CWE-78", "line": 1}]}
        row = score_static_triage_case(case, '{"findings":[]}')
        self.assertIsNone(row["precision"])
        self.assertEqual(row["recall"], 0.0)
        self.assertEqual(row["f1"], 0.0)

    def test_wrong_line_and_overreport_are_errors(self):
        case = {"id": "v", "code": "a\nb\nc\nd", "expected_findings": [{"weakness_id": "CWE-78", "line": 4}]}
        row = score_static_triage_case(case, json.dumps({"findings": [
            {"weakness_id": "CWE-78", "line": 3},
            {"weakness_id": "CWE-89", "line": 4},
        ]}))
        self.assertEqual((row["true_positive"], row["false_positive"], row["false_negative"]), (0, 2, 1))

    def test_malformed_output_is_counted_and_empty_aggregate_is_null(self):
        case = {"id": "v", "code": "a\nb", "expected_findings": [{"weakness_id": "CWE-89", "line": 2}]}
        malformed = score_static_triage_case(case, "not json")
        self.assertTrue(malformed["malformed_output"])
        self.assertEqual(malformed["false_negative"], 1)
        empty = aggregate_static_triage_metrics([])
        self.assertEqual(empty["case_count"], 0)
        self.assertIsNone(empty["micro_precision"])
        self.assertIsNone(empty["micro_recall"])

    def test_malformed_negative_control_is_not_counted_as_true_negative(self):
        case = {"id": "n", "code": "pass", "expected_findings": []}
        row = score_static_triage_case(case, "not json")
        self.assertFalse(row["true_negative_case"])

    def test_run_requires_unique_ids_and_rejects_unmatched_outputs(self):
        case = {"id": "n", "code": "pass", "expected_findings": []}
        scored = score_static_triage_run([case], {})
        self.assertEqual(scored["metrics"]["malformed_outputs"], 1)
        with self.assertRaises(ValueError):
            score_static_triage_run([case], {"other": '{"findings": []}'})

    def test_dataset_gold_shaped_outputs_score_as_expected(self):
        outputs = {
            case["id"]: json.dumps({"findings": case["expected_findings"]})
            for case in self.cases
        }
        metrics = score_static_triage_run(self.cases, outputs)["metrics"]
        self.assertEqual((metrics["true_positive"], metrics["false_positive"], metrics["false_negative"]), (2, 0, 0))
        self.assertEqual(metrics["true_negative_cases"], 2)
        self.assertEqual(metrics["micro_f1"], 1.0)

    def test_schema_rejects_boolean_line(self):
        case = {"id": "v", "code": "pass", "expected_findings": []}
        row = score_static_triage_case(case, '{"findings":[{"weakness_id":"CWE-78","line":true}]}')
        self.assertTrue(row["malformed_output"])


class TestRemediationScoringAndV2Dataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "datasets" / "cybersecurity_static_triage_v2.json"
        cls.cases = json.loads(path.read_text(encoding="utf-8"))
        cls.expectations = {
            "cyber_static_001_shell_interpolation": 4,
            "cyber_static_003_sql_interpolation": 2,
            "cyber_static_005_reflected_xss": 4,
            "cyber_static_007_path_traversal": 4,
            "cyber_static_008_hardcoded_credential": 4,
            "cyber_static_009_unbounded_stack_copy": 6,
        }

    def test_v2_dataset_integrity(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 10)
        lines = {case["id"]: [f["line"] for f in case["expected_findings"]] for case in self.cases}
        for case in self.cases:
            self.assertEqual(case["split"], "exploratory")
            for finding in case["expected_findings"]:
                self.assertLessEqual(finding["line"], len(case["code"].splitlines()))
        self.assertEqual([f["line"] for f in self.cases[0]["expected_findings"]], [4])
        self.assertEqual(self.expectations["cyber_static_009_unbounded_stack_copy"], 6)

    def test_v1_cases_without_expectation_have_null_remediation(self):
        case = self.cases[1]  # negative control without expected_remediation
        self.assertNotIn("expected_remediation", case)
        output = json.dumps({"findings": case["expected_findings"]})
        self.assertIsNone(score_static_triage_case(case, output)["remediation_coverage"])

    def test_gold_output_with_matching_remediation_scores_full_coverage(self):
        case = next(c for c in self.cases if c["id"] == "cyber_static_001_shell_interpolation")
        output = json.dumps({
            "findings": case["expected_findings"],
            "remediation": "Pass ArgumentVector explicitly and keep shell=False for the subprocess call.",
        })
        row = score_static_triage_case(case, output)
        self.assertEqual((row["true_positive"], row["false_negative"]), (1, 0))
        self.assertEqual(row["remediation_coverage"], 1.0)

    def test_missing_or_wrong_remediation_scores_zero_when_expected(self):
        case = next(c for c in self.cases if c["id"] == "cyber_static_007_path_traversal")
        findings_only = json.dumps({"findings": case["expected_findings"]})
        self.assertEqual(score_static_triage_case(case, findings_only)["remediation_coverage"], 0.0)
        off_topic = json.dumps({
            "findings": case["expected_findings"],
            "remediation": "sanitize with html.escape",
        })
        self.assertEqual(score_static_triage_case(case, off_topic)["remediation_coverage"], 0.0)

    def test_non_string_remediation_invalidates_response(self):
        case = next(c for c in self.cases if c["id"] == "cyber_static_008_hardcoded_credential")
        row = score_static_triage_case(case, '{"findings": [], "remediation": 7}')
        self.assertTrue(row["malformed_output"])

    def test_v2_dataset_gold_outputs_full_marks(self):
        outputs = {
            case["id"]: json.dumps({"findings": case["expected_findings"]})
            for case in self.cases
        }
        metrics = score_static_triage_run(self.cases, outputs)["metrics"]
        self.assertEqual((metrics["true_positive"], metrics["false_positive"], metrics["false_negative"]), (6, 0, 0))
        self.assertEqual(metrics["true_negative_cases"], 4)
        self.assertEqual(metrics["micro_f1"], 1.0)
        self.assertEqual(metrics["remediation_cases"], 6)
        self.assertEqual(metrics["mean_remediation_coverage"], 0.0)  # findings-only responses carry no remediation


if __name__ == "__main__":
    unittest.main()
