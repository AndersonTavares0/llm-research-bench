"""
test_multilingual_and_sensitive_topics.py - Test Suite for Multilingual Parallel Corpus and Sensitive Topics Suite

Validates:
1. Parallel multilingual corpus schema, 3-language completeness (en-US, pt-BR, zh-CN), and domain balance.
2. Sensitive topics benchmark suite balance, operational taxonomy, rubric integrity, and pending status flag.
3. Multilingual tokenization results invariants, expansion ratio consistency, and context capacity bounds.
"""

import json
import unittest
from pathlib import Path


class TestMultilingualAndSensitiveTopics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.corpus_path = cls.repo_root / "datasets" / "multilingual" / "parallel_corpus_multilingual.json"
        cls.sensitive_path = cls.repo_root / "datasets" / "sensitive_topics" / "sensitive_topics_eval_suite.json"
        cls.tok_results_path = cls.repo_root / "results" / "system_performance" / "multilingual_tokenization_results.json"

        with open(cls.corpus_path, "r", encoding="utf-8") as f:
            cls.corpus = json.load(f)

        with open(cls.sensitive_path, "r", encoding="utf-8") as f:
            cls.sensitive_suite = json.load(f)

        with open(cls.tok_results_path, "r", encoding="utf-8") as f:
            cls.tok_results = json.load(f)

    def test_parallel_corpus_structure_and_completeness(self):
        """Verify 12 canonical parallel items across 6 balanced domains with valid texts in all 3 languages."""
        self.assertEqual(len(self.corpus), 12, "Parallel corpus must contain exactly 12 items")
        required_domains = {"everyday", "academic", "technical", "narrative", "questions", "instructions"}
        observed_domains = {item["domain"] for item in self.corpus}
        self.assertEqual(required_domains, observed_domains, "All 6 required domains must be represented")

        for item in self.corpus:
            self.assertTrue(item["id"].startswith("para_"), f"Item id must start with para_: {item['id']}")
            for lang in ["en-US", "pt-BR", "zh-CN"]:
                self.assertIn(lang, item, f"Missing language {lang} in item {item['id']}")
                text = item[lang]
                self.assertIsInstance(text, str)
                self.assertGreater(len(text.strip()), 20, f"Text in {lang} for {item['id']} is too short")

    def test_sensitive_topics_suite_balance_and_rubrics(self):
        """Verify 10 balanced sensitive topic probes, operational rubrics, and formal pending execution status."""
        self.assertEqual(len(self.sensitive_suite), 10, "Sensitive suite must contain exactly 10 probes")
        required_categories = {"geopolitics", "historical_controversy", "freedom_of_expression", "human_rights", "armed_conflict"}
        observed_categories = {item["category"] for item in self.sensitive_suite}
        self.assertEqual(required_categories, observed_categories)

        for item in self.sensitive_suite:
            self.assertIn("framing", item)
            self.assertIn(item["framing"], {"neutral", "critical"})
            self.assertEqual(item["status"], "PROTOCOL_SPECIFIED_PENDING_EXECUTION", "Must be formally marked as pending")
            for p_key in ["prompt_en", "prompt_pt", "prompt_zh"]:
                self.assertIn(p_key, item)
                self.assertGreater(len(item[p_key]), 20)

            rubric = item.get("rubric", {})
            self.assertIn("acceptable_outcomes", rubric)
            self.assertIn("problematic_outcomes", rubric)
            self.assertGreater(len(rubric["acceptable_outcomes"]), 0)

    def test_multilingual_tokenization_results_validity(self):
        """Verify tokenization metrics, non-negative ratios, and expected cross-lingual ordering."""
        agg = self.tok_results.get("aggregated_metrics", {})
        self.assertIn("qwen2.5", agg)
        self.assertIn("smollm2", agg)
        self.assertIn("gemma2", agg)
        self.assertIn("llama3.2", agg)

        # Invariant 1: SmolLM2 has higher Portuguese and Chinese expansion ratios than Qwen2.5
        smollm_pt = agg["smollm2"]["mean_pt_over_en_ratio"]
        qwen_pt = agg["qwen2.5"]["mean_pt_over_en_ratio"]
        self.assertGreater(smollm_pt, qwen_pt, "SmolLM2 must exhibit higher Portuguese fragmentation than Qwen2.5")

        smollm_zh = agg["smollm2"]["mean_zh_over_en_ratio"]
        qwen_zh = agg["qwen2.5"]["mean_zh_over_en_ratio"]
        self.assertGreater(smollm_zh, qwen_zh, "SmolLM2 must exhibit higher Chinese fragmentation than Qwen2.5")

        # Invariant 2: Context capacity is strictly bounded in [0.0, 1.0] relative to English
        for tok, data in agg.items():
            cap = data["context_window_4096_budget_impact"]
            self.assertGreater(cap["pt_capacity_relative"], 0.2)
            self.assertLessEqual(cap["pt_capacity_relative"], 1.0)
            self.assertGreater(cap["zh_capacity_relative"], 0.1)
            self.assertLessEqual(cap["zh_capacity_relative"], 1.0)


if __name__ == "__main__":
    unittest.main()
