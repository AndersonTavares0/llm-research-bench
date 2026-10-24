"""Knowledge, Hallucination, and Truthfulness Evaluator (TruthfulQA / MMLU-Pro).

Parses multiple choice answers and scores hallucination resistance.
"""

import re
from typing import Any, Dict, List, Optional
from .base_evaluator import BaseEvaluator


class KnowledgeEvaluator(BaseEvaluator):
    """Evaluates multiple-choice reasoning and factual truthfulness."""

    def extract_mcq_choice(self, text: str, options: List[str]) -> Optional[str]:
        """Extract chosen option letter (e.g. 'A', 'B', 'C', 'D')."""
        valid_letters = [chr(65 + i) for i in range(len(options))]
        
        # 1. Search for 'the correct answer is (A)', 'the correct choice is (A)', 'Answer: A'
        patterns = [
            r"(?:the correct (?:answer|choice) is|the (?:answer|choice) is|answer:|choice:)\s*\(?([A-J])\)?",
            r"(?:^|\b)\(?([A-J])\)?\s*(?:is correct|is the (?:answer|choice))",
            r"^\s*(?:Option\s+)?\(?([A-J])\)?[\.\:\-]\s*",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE | re.MULTILINE)
            if m:
                letter = m.group(1).upper()
                if letter in valid_letters:
                    return letter

        # 2. Search for bare letter at the very end
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            last_line = lines[-1]
            m = re.search(r"\(?([A-J])\)?\.?$", last_line)
            if m:
                letter = m.group(1).upper()
                if letter in valid_letters:
                    return letter

        return None

    def evaluate(self, item: Dict[str, Any], response_text: str, **kwargs) -> Dict[str, Any]:
        options = item.get("options", [])
        correct_letter = item.get("correct_answer", "").strip().upper()
        predicted_letter = self.extract_mcq_choice(response_text, options)

        passed = (predicted_letter == correct_letter)

        # For TruthfulQA, also evaluate if text falls for misconception
        misconceptions = item.get("misconceptions", [])
        caught_in_myth = False
        for myth in misconceptions:
            if myth.lower() in response_text.lower():
                caught_in_myth = True
                break

        return {
            "score": 1.0 if (passed and not caught_in_myth) else 0.0,
            "passed": passed and not caught_in_myth,
            "predicted_letter": predicted_letter,
            "correct_letter": correct_letter,
            "caught_in_myth": caught_in_myth,
        }
