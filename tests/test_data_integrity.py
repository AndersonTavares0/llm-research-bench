"""
test_data_integrity.py - Automated Data Integrity, Provenance & Scientific Audit Test Suite

Enforces strict empirical invariants across:
1. Reconciled 1:1 ID alignment between canonical dataset and empirical benchmark results.
2. Complete traceability of prompt, raw response, verdict, and tool execution status.
3. Proper differentiation of tool proposal, schema validation, and harness guardrails.
4. Non-negative physical bounds for latency and throughput confidence intervals.
5. Exact SciPy statistical reproducibility (Welch's t = 84.50 on primary compound comparison).
6. Parallel reference text tokenization fertility validity.
7. Model provenance SHA-256 verification and file specification consistency.
"""

import json
import math
import os
import re
import unittest
from pathlib import Path
import scipy.stats as stats
import numpy as np


class TestDataIntegrityAndProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.defensive_bench_path = cls.repo_root / "datasets" / "defensive_safety_benchmarks.json"
        cls.empirical_results_path = cls.repo_root / "results" / "system_performance" / "empirical_slm_benchmark_results.json"
        cls.model_provenance_path = cls.repo_root / "datasets" / "model_provenance.json"

        with open(cls.defensive_bench_path, "r", encoding="utf-8") as f:
            cls.defensive_bench = json.load(f)

        with open(cls.empirical_results_path, "r", encoding="utf-8") as f:
            cls.empirical_results = json.load(f)

        with open(cls.model_provenance_path, "r", encoding="utf-8") as f:
            cls.model_provenance = json.load(f)

    def test_canonical_defensive_benchmark_ids_alignment(self):
        """Requirement 1: Verify 100% ID alignment between benchmark dataset and results (0 divergent IDs)."""
        expected_ids = [item["id"] for item in self.defensive_bench]
        self.assertEqual(len(expected_ids), 10, "Expected 10 canonical defensive benchmark items")

        for model_id, model_data in self.empirical_results.items():
            safety = model_data.get("safety", {})
            records = safety.get("records", [])
            self.assertEqual(len(records), 10, f"Model {model_id} must have exactly 10 defensive evaluation records")
            record_ids = [r["id"] for r in records]
            self.assertEqual(
                expected_ids,
                record_ids,
                f"Model {model_id} has divergent IDs compared to canonical benchmark dataset: {set(expected_ids) ^ set(record_ids)}"
            )

    def test_raw_response_traceability_never_empty(self):
        """Requirement 4: Verify raw_response is never empty across any model evaluation."""
        empty_records = []
        for model_id, model_data in self.empirical_results.items():
            records = model_data.get("safety", {}).get("records", [])
            for r in records:
                resp = r.get("raw_response", "")
                if not resp or not resp.strip():
                    empty_records.append((model_id, r.get("id")))

        self.assertEqual(
            len(empty_records),
            0,
            f"Found defensive evaluation records with empty raw_response: {empty_records}"
        )

    def test_tool_call_differentiation(self):
        """Requirement 4: Verify tool evaluations differentiate proposed_call, valid_call, and execution_status."""
        tool_ids = {"def_tool_01_command_injection_block", "def_tool_02_destructive_sql_block"}
        for model_id, model_data in self.empirical_results.items():
            records = model_data.get("safety", {}).get("records", [])
            for r in records:
                if r.get("id") in tool_ids:
                    self.assertIn("proposed_call", r, f"{model_id} {r.get('id')} missing proposed_call")
                    self.assertIn("valid_call", r, f"{model_id} {r.get('id')} missing valid_call")
                    self.assertIn("execution_status", r, f"{model_id} {r.get('id')} missing execution_status")
                    self.assertIn(
                        r["execution_status"],
                        {"BLOCKED_BY_HARNESS", "SAFE_EXECUTION", "REFUSED_SAFELY", "NO_TOOL_CALLED", "FAILED_CALL"},
                        f"{model_id} unexpected execution_status: {r['execution_status']}"
                    )
                    # When an unsafe call is proposed, ensure it was blocked by harness and raw_response captures it
                    if r.get("verdict") == "UNSAFE_TOOL_ARGUMENT":
                        self.assertTrue(r["proposed_call"])
                        self.assertEqual(r["execution_status"], "BLOCKED_BY_HARNESS")
                        self.assertTrue("Tool Call Proposta" in r["raw_response"])

    def test_welch_t_test_exact_statistical_reproducibility(self):
        """Requirement 3: Verify Welch's t on compound comparison yields t = 84.50 +- 0.05."""
        q4km = self.empirical_results["gemma4:Q4KM"]
        e2b = self.empirical_results["gemma4:E2B"]
        mtp_base = self.empirical_results["gemma4:MTP"]

        q4km_samples = [t["decode_tok_per_sec"] for t in q4km["perf_trials"]]
        e2b_samples = [t["decode_tok_per_sec"] for t in e2b["perf_trials"]]
        mtp_base_samples = [t["decode_tok_per_sec"] for t in mtp_base["perf_trials"]]

        self.assertEqual(len(q4km_samples), 10)
        self.assertEqual(len(e2b_samples), 10)
        self.assertEqual(len(mtp_base_samples), 10)

        # Compound comparison: IQ4_XS+MTP vs Q4_K_M baseline
        t_stat, p_val = stats.ttest_ind(e2b_samples, q4km_samples, equal_var=False)
        self.assertAlmostEqual(t_stat, 84.50, delta=0.05, msg="Welch's t for primary comparison must equal ~84.50")
        self.assertLess(p_val, 1e-15, "Welch's p-value must be highly significant (p < 1e-15)")

        # Factorial MTP isolated ablation: IQ4_XS+MTP vs IQ4_XS baseline
        t_mtp, p_mtp = stats.ttest_ind(e2b_samples, mtp_base_samples, equal_var=False)
        self.assertAlmostEqual(t_mtp, 43.72, delta=0.10, msg="Welch's t for isolated MTP ablation must equal ~43.72")
        self.assertLess(p_mtp, 1e-14)

    def test_confidence_interval_physical_non_negative_bounds(self):
        """Requirement 6: Verify confidence intervals have valid non-negative lower bounds for latency and throughput."""
        for model_id, model_data in self.empirical_results.items():
            for metric in ["decode_throughput", "prompt_throughput", "ttft"]:
                stat = model_data.get(metric, {})
                mean = stat.get("mean")
                ci_low = stat.get("ci95_low")
                ci_high = stat.get("ci95_high")
                std = stat.get("std")
                se = stat.get("se")

                self.assertIsNotNone(mean, f"{model_id} {metric} missing mean")
                self.assertIsNotNone(ci_low, f"{model_id} {metric} missing ci95_low")
                self.assertIsNotNone(ci_high, f"{model_id} {metric} missing ci95_high")
                self.assertGreaterEqual(ci_low, 0.0, f"{model_id} {metric} ci95_low is negative: {ci_low}")
                self.assertGreaterEqual(ci_high, ci_low, f"{model_id} {metric} ci95_high ({ci_high}) < ci95_low ({ci_low})")
                self.assertAlmostEqual(se, std / math.sqrt(10), delta=0.02, msg=f"{model_id} {metric} SE != std/sqrt(N)")

    def test_parallel_corpus_tokenizer_fertility(self):
        """Requirement 5: Verify parallel reference texts are tokenized with valid counts and fertility ratios."""
        for model_id, model_data in self.empirical_results.items():
            fertility_entries = model_data.get("language_fertility", [])
            self.assertEqual(len(fertility_entries), 3, f"{model_id} must have 3 parallel language evaluations (pt-BR, pt-PT, en-US)")

            lang_map = {e["language"]: e for e in fertility_entries}
            self.assertIn("pt-BR", lang_map)
            self.assertIn("pt-PT", lang_map)
            self.assertIn("en-US", lang_map)

            # English reference text is 40 words, Portuguese reference texts are 43 words
            self.assertEqual(lang_map["en-US"]["word_count"], 40)
            self.assertEqual(lang_map["pt-BR"]["word_count"], 43)
            self.assertEqual(lang_map["pt-PT"]["word_count"], 43)

            for lang, entry in lang_map.items():
                self.assertGreater(entry["token_count"], 0)
                self.assertGreaterEqual(entry["fertility_ratio"], 1.0)
                expected_ratio = round(entry["token_count"] / entry["word_count"], 2)
                self.assertAlmostEqual(entry["fertility_ratio"], expected_ratio, delta=0.02)

    def test_model_provenance_sha256_hashes(self):
        """Requirement 8: Verify model provenance catalog contains verified 64-char hex SHA-256 hashes."""
        models = self.model_provenance.get("models", [])
        self.assertEqual(len(models), 8, "Expected 8 models in provenance catalog")
        hex_pattern = re.compile(r"^[0-9a-f]{64}$")

        provenance_ids = set()
        for m in models:
            m_id = m["model_id"]
            provenance_ids.add(m_id)
            sha = m.get("sha256", "")
            self.assertTrue(hex_pattern.match(sha), f"Model {m_id} has invalid SHA-256 hash: {sha}")
            self.assertGreater(m["file_size_bytes"], 100_000_000)
            self.assertEqual(m["context_window_tested"], 16384)

        # Ensure all models in empirical results exist in provenance catalog
        empirical_ids = set(self.empirical_results.keys())
        self.assertEqual(provenance_ids, empirical_ids, "Mismatch between provenance models and empirical results")


if __name__ == "__main__":
    unittest.main()
