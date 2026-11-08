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


if __name__ == "__main__":
    unittest.main()
