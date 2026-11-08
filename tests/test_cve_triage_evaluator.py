import json
from pathlib import Path
import unittest

from src.llm_research_bench.evaluators import (
    aggregate_cve_triage_metrics,
    is_affected,
    parse_version_key,
    satisfies_range,
    score_cve_advisory_case,
    score_cve_advisory_run,
)


def load_dataset(name="cve_advisory_triage_v1.json"):
    path = Path(__file__).resolve().parents[1] / "datasets" / name
    return json.loads(path.read_text(encoding="utf-8"))


class TestVersionParsing(unittest.TestCase):
    def test_sortable_ordering_including_letter_patches(self):
        ordered = ["1.9.5", "1.9.5p1", "1.9.5p2", "1.9.6"]
        keys = [parse_version_key(version) for version in ordered]
        self.assertEqual(keys, sorted(keys))

    def test_bare_letter_suffix_sorts_before_numbered_patch(self):
        self.assertLess(parse_version_key("1.0.1f"), parse_version_key("1.0.1g"))
        self.assertLess(parse_version_key("1.0.1f"), parse_version_key("1.0.1f1"))

    def test_unsupported_versions_fail_closed(self):
        for bad in ("abc", "1.0.0-rc1", "", None, 3, True):
            with self.assertRaises(ValueError):
                parse_version_key(bad)


class TestRangeExpressions(unittest.TestCase):
    def test_operators(self):
        self.assertTrue(satisfies_range("1.2.3", "< 1.2.4"))
        self.assertFalse(satisfies_range("1.2.4", "< 1.2.4"))
        self.assertTrue(satisfies_range("1.2.4", "<= 1.2.4"))
        self.assertTrue(satisfies_range("1.2.4", "== 1.2.4"))
        self.assertFalse(satisfies_range("1.2.4", "!= 1.2.4"))
        self.assertTrue(satisfies_range("1.2.4", "!= 1.2.5"))
        self.assertFalse(satisfies_range("1.2.4", ">= 2.0.0"))

    def test_letter_patch_boundary_is_exact(self):
        self.assertTrue(satisfies_range("1.9.5p1", "< 1.9.5p2"))
        self.assertFalse(satisfies_range("1.9.5p2", "< 1.9.5p2"))

    def test_conjunction_clause(self):
        self.assertTrue(satisfies_range("2.13.0", ">= 2.0.0 && < 2.15.0"))
        self.assertFalse(satisfies_range("1.2.17", ">= 2.0.0 && < 2.15.0"))
        self.assertFalse(satisfies_range("2.17.0", ">= 2.0.0 && < 2.15.0"))

    def test_unsupported_operator_fails_closed(self):
        with self.assertRaises(ValueError):
            satisfies_range("1.0.0", "~ 1.0.0")


class TestDatasetIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_dataset()

    def test_unique_ids_and_cve_prefixes(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in self.cases:
            self.assertTrue(case["cve"].startswith("CVE-"))
            self.assertTrue(case["remediation_keywords"])
            self.assertTrue(case["affected_ranges"])
            self.assertTrue(case["source"])

    def test_labels_match_deterministic_version_check(self):
        for case in self.cases:
            for row in case["inventory"]:
                if row["version"] is None:
                    self.assertEqual(row["expected"], "insufficient_evidence")
                else:
                    self.assertEqual(
                        row["expected"],
                        "affected" if is_affected(case, row["package"], row["version"]) else "not_affected",
                        f"{case['id']} {row['package']} {row['version']}",
                    )

    def test_every_package_has_ranges(self):
        for case in self.cases:
            packages = {row["package"] for row in case["inventory"] if row["version"] is not None}
            self.assertTrue(packages <= set(case["affected_ranges"]))


class TestScoreCveAdvisoryCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_dataset()
        cls.sudo = cls.cases[0]
        cls.good = json.dumps({
            "classifications": [
                {"package": "sudo", "version": "1.8.31", "status": "affected", "cited_cve": "CVE-2021-3156"},
                {"package": "sudo", "version": "1.9.5p2", "status": "not_affected", "cited_cve": "CVE-2021-3156"},
                {"package": "sudo", "version": None, "status": "insufficient_evidence"},
            ],
            "remediation": "Upgrade sudo to 1.9.5p2 or later from the distribution repository.",
        })

    def test_good_response_scores_perfectly(self):
        row = score_cve_advisory_case(self.sudo, self.good)
        self.assertEqual(
            (row["accuracy"], row["unsafe_misses"], row["false_alarms"], row["correct_abstentions"]),
            (1.0, 0, 0, 1),
        )
        self.assertEqual(row["remediation_coverage"], 1.0)
        self.assertEqual(row["invented_cve_references"], 0)
        self.assertFalse(row["malformed_output"])

    def test_unsafe_miss_is_affected_called_not_affected(self):
        response = json.dumps({"classifications": [
            {"package": "sudo", "version": "1.8.31", "status": "not_affected"},
        ]})
        row = score_cve_advisory_case(self.sudo, response)
        self.assertEqual(row["unsafe_misses"], 1)
        self.assertEqual(row["accuracy"], 0.0)
        self.assertEqual(row["unclassified_rows"], 2)

    def test_unknown_and_invalid_classifications_fail_closed(self):
        response = json.dumps({"classifications": [
            {"package": "sudo", "version": "1.9.9", "status": "affected", "cited_cve": "CVE-9999-9999"},
            {"package": "sudo", "version": "1.9.5p2", "status": "very_broken"},
        ]})
        row = score_cve_advisory_case(self.sudo, response)
        self.assertEqual(row["invalid_classifications"], 2)
        self.assertEqual(row["invented_cve_references"], 1)
        self.assertEqual(row["unclassified_rows"], 2)

    def test_malformed_and_absent_outputs_are_misses(self):
        malformed = score_cve_advisory_case(self.sudo, "not json")
        self.assertTrue(malformed["malformed_output"])
        self.assertEqual(malformed["remediation_coverage"], 0.0)
        self.assertEqual(malformed["classified_rows"], 0)
        no_remediation = score_cve_advisory_case(self.sudo, '{"classifications": []}')
        self.assertEqual(no_remediation["remediation_coverage"], 0.0)

    def test_non_string_remediation_invalidates_response(self):
        row = score_cve_advisory_case(self.sudo, '{"classifications": [], "remediation": 7}')
        self.assertTrue(row["malformed_output"])


class TestScoreCveAdvisoryRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_dataset()
        def shaped(case):
            classifications = [
                {"package": row["package"], "version": row["version"], "status": row["expected"]}
                for row in case["inventory"]
            ]
            return json.dumps({"classifications": classifications, "remediation": "upgrade to a fixed release"})

        cls.outputs = {case["id"]: shaped(case) for case in cls.cases}

    def test_perfect_run_metrics(self):
        result = score_cve_advisory_run(self.cases, self.outputs)
        metrics = result["metrics"]
        self.assertEqual(metrics["case_count"], len(self.cases))
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["unsafe_misses"], 0)
        self.assertEqual(metrics["false_alarms"], 0)
        self.assertEqual(metrics["invented_cve_references"], 0)
        self.assertEqual(metrics["malformed_outputs"], 0)
        self.assertEqual(metrics["mean_remediation_coverage"], 1.0)

    def test_empty_aggregate_has_null_accuracy(self):
        empty = aggregate_cve_triage_metrics([])
        self.assertIsNone(empty["accuracy"])

    def test_run_rejects_unknown_outputs_and_counts_absent(self):
        with self.assertRaises(ValueError):
            score_cve_advisory_run(self.cases, {"other": "{}"})
        result = score_cve_advisory_run(self.cases, {})
        self.assertEqual(result["metrics"]["malformed_outputs"], len(self.cases))

    def test_letter_patch_sudo_case_is_scored_exactly(self):
        synthetic = self.cases[5]
        row = score_cve_advisory_case(synthetic, self.outputs[synthetic["id"]])
        self.assertEqual(
            (row["correct_classifications"], row["unsafe_misses"], row["correct_abstentions"]),
            (4, 0, 1),
        )


if __name__ == "__main__":
    unittest.main()
