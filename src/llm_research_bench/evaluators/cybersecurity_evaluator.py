"""Deterministic scoring for the offline static cybersecurity triage set.

Candidate code is treated as data: this evaluator never imports or executes it.
Responses use JSON: {"findings": [{"weakness_id": "CWE-78", "line": 4}]}.
"""

import json
import re
from typing import Any, Dict, List


def score_static_triage_case(case: Dict[str, Any], response_text: str) -> Dict[str, Any]:
    """Score exact weakness-ID and source-line matches; malformed output is a miss."""
    try:
        response = json.loads(response_text)
        if not isinstance(response, dict) or not isinstance(response.get("findings"), list):
            raise ValueError("response must be an object with a findings list")
        predicted = set()
        line_count = len(case["code"].splitlines())
        for finding in response["findings"]:
            if not isinstance(finding, dict):
                raise ValueError("each finding must be an object")
            weakness_id, line = finding.get("weakness_id"), finding.get("line")
            if (not isinstance(weakness_id, str) or not re.fullmatch(r"CWE-[0-9]+", weakness_id)
                    or isinstance(line, bool) or not isinstance(line, int) or not 1 <= line <= line_count):
                raise ValueError("finding requires a CWE identifier and positive integer line")
            if (weakness_id, line) in predicted:
                raise ValueError("duplicate finding")
            predicted.add((weakness_id, line))
        malformed = False
    except (json.JSONDecodeError, ValueError, TypeError):
        predicted = set()
        malformed = True

    expected = {
        (finding["weakness_id"], finding["line"])
        for finding in case["expected_findings"]
    }
    tp = len(expected & predicted)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {
        "id": case["id"],
        "malformed_output": malformed,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative_case": not malformed and not expected and not predicted,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def score_static_triage_run(
    cases: List[Dict[str, Any]], model_outputs: Dict[str, str]
) -> Dict[str, Any]:
    """Score saved responses by case ID; absent responses count as malformed misses."""
    case_ids = [case["id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("benchmark case IDs must be unique")
    extras = set(model_outputs) - set(case_ids)
    if extras:
        raise ValueError(f"outputs contain unknown case IDs: {sorted(extras)}")
    records = [
        score_static_triage_case(case, model_outputs.get(case["id"], ""))
        for case in cases
    ]
    return {"records": records, "metrics": aggregate_static_triage_metrics(records)}


def aggregate_static_triage_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate counts before deriving micro precision/recall/F1."""
    tp = sum(row["true_positive"] for row in records)
    fp = sum(row["false_positive"] for row in records)
    fn = sum(row["false_negative"] for row in records)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {
        "case_count": len(records),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative_cases": sum(row["true_negative_case"] for row in records),
        "malformed_outputs": sum(row["malformed_output"] for row in records),
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
    }
