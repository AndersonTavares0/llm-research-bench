import json
from pathlib import Path
import tempfile
import unittest
import sys

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from llm_research_bench.split_results import process_benchmark_data
from llm_research_bench.benchmark_suite import (
    evaluate_safety_response,
    evaluate_reasoning_response,
)


class TestDataProcessing(unittest.TestCase):
    def test_process_benchmark_data_transformation(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp_dir = Path(tmp_str)
            raw_file = tmp_dir / "raw.json"
            telemetry_file = tmp_dir / "telemetry.json"

            mock_raw = {
                "suite_version": "test/v1.0",
                "models_evaluated": {
                    "test_model:1B": {
                        "safety": {"total_tests": 6, "passed_tests": 5, "score_pct": 83.3},
                        "agentic": {"scenario_1": {"passed": True}, "all_passed": True},
                        "reasoning": {"total_tests": 3, "passed_tests": 1, "score_pct": 33.3},
                    }
                },
            }
            mock_telemetry = [
                {
                    "model": "test_model:1B",
                    "parameters_b": 1.0,
                    "quantization": "Q4_0",
                    "vram_peak_mib": 1024,
                    "generation_tok_s": 50.0,
                }
            ]

            with open(raw_file, "w", encoding="utf-8") as f:
                json.dump(mock_raw, f)
            with open(telemetry_file, "w", encoding="utf-8") as f:
                json.dump(mock_telemetry, f)

            out_dir = tmp_dir / "results"
            process_benchmark_data(raw_file, out_dir, telemetry_json_path=telemetry_file)

            sys_csv = out_dir / "system_performance" / "system_metrics.csv"
            sys_json = out_dir / "system_performance" / "system_metrics.json"
            qual_csv = out_dir / "model_quality" / "quality_summary.csv"
            qual_json = out_dir / "model_quality" / "quality_evaluations.json"

            self.assertTrue(sys_csv.exists())
            self.assertTrue(sys_json.exists())
            self.assertTrue(qual_csv.exists())
            self.assertTrue(qual_json.exists())

            with open(qual_json, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertIn("test_model:1B", loaded)
            self.assertEqual(loaded["test_model:1B"]["safety"]["score_pct"], 83.3)

            with open(sys_json, "r", encoding="utf-8") as f:
                loaded_sys = json.load(f)
            self.assertEqual(loaded_sys[0]["model"], "test_model:1B")
            self.assertEqual(loaded_sys[0]["generation_tok_s"], 50.0)

    def test_evaluate_safety_response_refusal(self):
        prompt_meta = {"expected": "refusal"}
        clean_refusal = "I cannot fulfill this request because writing weaponized malware violates safety guidelines."
        compliance_bypass = "Sure, here is your exploit script: import socket..."

        res_clean = evaluate_safety_response(prompt_meta, clean_refusal)
        self.assertTrue(res_clean["passed"])

        res_bypass = evaluate_safety_response(prompt_meta, compliance_bypass)
        self.assertFalse(res_bypass["passed"])

    def test_evaluate_reasoning_response(self):
        prompt_meta = {"required_elements": ["16", "2"]}
        correct_resp = "The RAIDZ2 pool provides 16TB usable capacity and tolerates 2 disk failures."
        wrong_resp = "The pool has 18TB and tolerates 3 disk failures."

        self.assertTrue(evaluate_reasoning_response(prompt_meta, correct_resp)["passed"])
        self.assertFalse(evaluate_reasoning_response(prompt_meta, wrong_resp)["passed"])


if __name__ == "__main__":
    unittest.main()
