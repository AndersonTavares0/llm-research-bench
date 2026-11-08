import copy
import json
from pathlib import Path
import unittest

from src.llm_research_bench.capability import validate
from src.llm_research_bench.defensive_harness import run_scenarios
from src.llm_research_bench.evaluators import score_cve_advisory_case, score_static_triage_run

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "configs" / "schemas" / "defensive_cyber_results.v1.schema.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class TestDefensiveCyberResultsSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(SCHEMA_PATH)
        datasets = Path(__file__).resolve().parents[1] / "datasets"
        cls.static_cases = load_json(datasets / "cybersecurity_static_triage_v1.json")
        cls.cve_cases = load_json(datasets / "cve_advisory_triage_v1.json")
        appsec = run_scenarios(load_json(datasets / "appsec_chatbot_scenarios_v1.json"))
        cls.appsec_record = appsec["records"][0]

    def wrap(self, benchmark, records):
        return {
            "generated_by": "tests/test_defensive_cyber_results_schema.py",
            "status": "deterministic_scoring_only",
            "benchmark": benchmark,
            "dataset_version": "exploratory_v1",
            "summary": {"record_count": len(records)},
            "records": records,
        }

    def wrap_records(self, static_record, cve_record, appsec_record):
        return [
            self.wrap("static_vulnerability_triage", [static_record]),
            self.wrap("cve_advisory_triage", [cve_record]),
            self.wrap("appsec_chatbot_scenarios", [appsec_record]),
        ]

    def record_errors(self, payload):
        """Root-level validation plus benchmark-specific record validation."""
        errors = validate(payload, self.schema, path="$")
        mapping = self.schema["x-record-schema-mapping"]
        definition_name = mapping.get(payload["benchmark"])
        if definition_name is None:
            errors.append(f"unknown benchmark {payload['benchmark']!r}")
            return errors
        for record in payload["records"]:
            definition = self.schema["definitions"][definition_name]
            errors.extend(validate(record, definition, path=f"{payload['benchmark']}.records"))
        return errors

    def test_valid_results_validate(self):
        static_record = score_static_triage_run(
            self.static_cases,
            {case["id"]: json.dumps({"findings": case["expected_findings"]}) for case in self.static_cases},
        )["records"][0]
        cve_record = score_cve_advisory_case(self.cve_cases[0], '{"classifications": []}')
        payload = self.wrap_records(static_record, cve_record, self.appsec_record)
        for item in payload:
            self.assertEqual(self.record_errors(item), [])

    def test_invalid_classification_fails_validation(self):
        broken = copy.deepcopy(self.appsec_record)
        broken["classification"] = "totally_new_verdict"
        payload = self.wrap_records(None, None, broken)
        self.assertNotEqual(self.record_errors(payload[2]), [])

    def test_missing_required_cve_fields_fail_validation(self):
        cve_record = copy.deepcopy(score_cve_advisory_case(self.cve_cases[0], '{"classifications": []}'))
        del cve_record["inventory_rows"]
        payload = self.wrap_records(None, cve_record, self.appsec_record)
        self.assertNotEqual(self.record_errors(payload[1]), [])

    def test_invalid_benchmark_and_status_fail_validation(self):
        static_record = copy.deepcopy(
            score_static_triage_run(self.static_cases, {})["records"][0]
        )
        cve_record = copy.deepcopy(score_cve_advisory_case(self.cve_cases[0], "not json"))
        payload = self.wrap_records(static_record, cve_record, self.appsec_record)
        # Same records under a made-up benchmark name and a forbidden status.
        payload[0]["benchmark"], payload[0]["status"] = "offensive_exploitation", "fabricated_from_memory"
        self.assertNotEqual(self.record_errors(payload[0]), [])
        self.assertNotEqual(validate(payload[0], self.schema, path="$"), [])


if __name__ == "__main__":
    unittest.main()
