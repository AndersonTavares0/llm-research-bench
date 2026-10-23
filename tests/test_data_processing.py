import json
from pathlib import Path
import unittest
import sys

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_research_bench.split_results import process_benchmark_data


class TestDataProcessing(unittest.TestCase):
    def test_process_benchmark_data(self):
        tmp_dir = Path("C:/Users/ander/Desktop/llm-research-bench/tests/_tmp_test")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        raw_file = tmp_dir / "raw.json"
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
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(mock_raw, f)

        out_dir = tmp_dir / "results"
        process_benchmark_data(raw_file, out_dir)

        sys_csv = out_dir / "system_performance" / "system_metrics.csv"
        sys_json = out_dir / "system_performance" / "system_metrics.json"
        qual_csv = out_dir / "model_quality" / "quality_summary.csv"
        qual_json = out_dir / "model_quality" / "quality_evaluations.json"

        self.assertTrue(sys_csv.exists())
        self.assertTrue(sys_json.exists())
        self.assertTrue(qual_csv.exists())
        self.assertTrue(qual_json.exists())

        # Cleanup
        import shutil
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    unittest.main()
