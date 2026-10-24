"""Mathematical Reasoning Evaluator (GSM8K / MATH-500 methodology).

Extracts and verifies numerical and algebraic solutions without relying
on fragile substring match.
"""

from fractions import Fraction
import math
import re
from typing import Any, Dict, Optional
from .base_evaluator import BaseEvaluator


class MathEvaluator(BaseEvaluator):
    """Evaluates multi-step mathematical reasoning solutions."""

    def __init__(self):
        # Support balanced nested single-level braces for LaTeX fractions like \boxed{\frac{a}{b}}
        self.boxed_pattern = re.compile(r"\\boxed\{((?:[^{}]|\{[^{}]*\})+)\}")
        self.hash_pattern = re.compile(r"####\s*([^\n\r]+)")
        self.number_pattern = re.compile(r"[-+]?(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?(?:/\d+)?")

    def normalize_value(self, val_str: str) -> Optional[float]:
        """Convert string to normalized float or float equivalent from fraction."""
        if not val_str:
            return None
        
        # Handle LaTeX \frac{a}{b}
        frac_match = re.search(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", val_str)
        if frac_match:
            try:
                num = float(frac_match.group(1).strip())
                den = float(frac_match.group(2).strip())
                if den != 0:
                    return num / den
            except Exception:
                pass

        cleaned = val_str.strip().replace(",", "").replace("$", "").replace("%", "").strip()
        # Handle trailing period or punctuation
        cleaned = re.sub(r"[^\d./\-+]", "", cleaned)
        if not cleaned:
            return None
        try:
            if "/" in cleaned:
                parts = cleaned.split("/")
                if len(parts) == 2 and float(parts[1]) != 0:
                    return float(Fraction(int(parts[0]), int(parts[1])))
            return float(cleaned)
        except Exception:
            return None

    def extract_predicted_answer(self, response_text: str) -> Optional[str]:
        """Extract candidate answer using standard benchmark patterns."""
        # 1. LaTeX \boxed{...} pattern (MATH-500 style)
        boxed_matches = self.boxed_pattern.findall(response_text)
        if boxed_matches:
            return boxed_matches[-1].strip()

        # 2. GSM8K #### pattern
        hash_matches = self.hash_pattern.findall(response_text)
        if hash_matches:
            return hash_matches[-1].strip()

        # 3. Final sentence search for 'the answer is ...'
        lines = [line.strip() for line in response_text.splitlines() if line.strip()]
        for line in reversed(lines[-4:]):
            m = re.search(r"(?:the answer is|is equal to|=)\s*([$]?\d[\d,.]*)", line, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        # 4. Fallback to last number in text
        numbers = self.number_pattern.findall(response_text)
        if numbers:
            return numbers[-1].strip()

        return None

    def evaluate(self, item: Dict[str, Any], response_text: str, **kwargs) -> Dict[str, Any]:
        ground_truth_raw = str(item.get("answer", "")).strip()
        predicted_raw = self.extract_predicted_answer(response_text)

        gt_norm = self.normalize_value(ground_truth_raw)
        pred_norm = self.normalize_value(predicted_raw) if predicted_raw else None

        exact_str_match = False
        if predicted_raw and ground_truth_raw:
            exact_str_match = (predicted_raw.lower() == ground_truth_raw.lower())

        numerical_match = False
        if gt_norm is not None and pred_norm is not None:
            # Allow tolerance for floating point representations
            numerical_match = math.isclose(gt_norm, pred_norm, rel_tol=1e-4, abs_tol=1e-4)

        passed = exact_str_match or numerical_match

        return {
            "score": 1.0 if passed else 0.0,
            "passed": passed,
            "predicted_raw": predicted_raw,
            "ground_truth_raw": ground_truth_raw,
            "numerical_match": numerical_match,
            "exact_str_match": exact_str_match,
        }
