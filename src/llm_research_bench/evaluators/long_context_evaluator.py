"""Long-Context Needle-In-A-Haystack Evaluator (RULER methodology).

Measures retrieval precision across token context depths (0% to 100%)
and context lengths from 1k to 16k tokens.
"""

import re
from typing import Any, Dict
from .base_evaluator import BaseEvaluator


class LongContextEvaluator(BaseEvaluator):
    """Evaluates information retrieval from dense long contexts."""

    def evaluate(self, item: Dict[str, Any], response_text: str, **kwargs) -> Dict[str, Any]:
        needle = item.get("needle_key", "")
        needle_value = item.get("needle_value", "")
        context_len = item.get("context_len", 1024)
        depth_pct = item.get("depth_pct", 50.0)

        # Check if the needle value is recovered in the output
        text_clean = response_text.strip().lower()
        val_clean = str(needle_value).strip().lower()

        exact_match = (val_clean in text_clean)
        
        # Word-level overlap score
        val_words = set(re.findall(r"\w+", val_clean))
        text_words = set(re.findall(r"\w+", text_clean))
        overlap = len(val_words.intersection(text_words)) / len(val_words) if val_words else 0.0

        passed = exact_match or (overlap >= 0.8)

        return {
            "score": 1.0 if passed else overlap,
            "passed": passed,
            "exact_match": exact_match,
            "overlap_ratio": round(overlap, 3),
            "context_len": context_len,
            "depth_pct": depth_pct,
            "needle_key": needle,
            "retrieved_snippet": response_text[:200],
        }
