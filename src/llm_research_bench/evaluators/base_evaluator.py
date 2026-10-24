"""Base Evaluator Interface for LLM Research Bench."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseEvaluator(ABC):
    """Abstract base class for all benchmark evaluators."""

    @abstractmethod
    def evaluate(self, item: Dict[str, Any], response_text: str, **kwargs) -> Dict[str, Any]:
        """Evaluate a model's response against ground truth or rubric.

        Returns a dictionary containing:
        - score: float (normalized 0.0 to 1.0 or category score)
        - passed: bool
        - details: dict of domain-specific metrics
        """
        pass
