"""Offline preparation and provenance checks for blinded judge tasks.

This module deliberately performs no network calls. A caller may export the
prepared tasks to an approved judge, then validate and join returned labels.
"""

from __future__ import annotations

import hashlib
import json
import random
import secrets
from typing import Any, Iterable, Mapping


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prepare_blind_tasks(
    records: Iterable[Mapping[str, Any]], rubric: str, seed: int
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Create shuffled, identity-redacted tasks and a separate ID→source map."""
    if not rubric.strip():
        raise ValueError("rubric must not be empty")
    tasks, sealed_mapping, source_ids = [], {}, set()
    for record in records:
        source_id = str(record["id"])
        if source_id in source_ids:
            raise ValueError(f"duplicate source ID: {source_id}")
        source_ids.add(source_id)
        opaque_id = secrets.token_hex(12)
        if opaque_id in sealed_mapping:
            raise ValueError("random blinded task ID collision")
        task = {
            "task_id": opaque_id,
            "benchmark": record.get("benchmark"),
            "prompt": record["prompt"],
            "response": record["response"],
            "rubric": rubric,
            "provenance": {
                "prompt_sha256": _digest(record["prompt"]),
                "response_sha256": _digest(record["response"]),
                "rubric_sha256": _digest(rubric),
            },
        }
        tasks.append(task)
        sealed_mapping[opaque_id] = source_id
    random.Random(seed).shuffle(tasks)
    return tasks, sealed_mapping


def validate_judge_result(task: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a rubric result and bind it to the immutable task provenance."""
    provenance = task.get("provenance", {})
    if (
        provenance.get("prompt_sha256") != _digest(task.get("prompt"))
        or provenance.get("response_sha256") != _digest(task.get("response"))
        or provenance.get("rubric_sha256") != _digest(task.get("rubric"))
    ):
        raise ValueError("judge task content does not match its provenance hashes")
    if result.get("task_id") != task.get("task_id"):
        raise ValueError("judge result task_id does not match task")
    rubric_hash = provenance.get("rubric_sha256")
    if result.get("rubric_sha256") != rubric_hash:
        raise ValueError("judge result rubric hash does not match task")
    judge_model = result.get("judge_model")
    if not isinstance(judge_model, str) or not judge_model.strip():
        raise ValueError("judge_model must identify the judge used")
    validated = {
        "task_id": task["task_id"],
        "judge_model": judge_model,
        "judge_version": result.get("judge_version"),
        "rubric_sha256": rubric_hash,
        "prompt_sha256": task["provenance"]["prompt_sha256"],
        "response_sha256": task["provenance"]["response_sha256"],
    }
    if task.get("benchmark") == "strongreject":
        from .safety_scoring import strongreject_score

        score = strongreject_score(
            result.get("refusal"),
            result.get("convincingness"),
            result.get("specificity"),
        )
        if "score" in result and result["score"] != score:
            raise ValueError("judge score does not match the official StrongREJECT rubric")
        validated.update({
            "refusal": result["refusal"],
            "convincingness": result["convincingness"],
            "specificity": result["specificity"],
            "score": score,
        })
    elif task.get("benchmark") == "xstest":
        from .safety_scoring import normalize_xstest_label

        validated["label"] = normalize_xstest_label(result.get("label"))
    elif task.get("benchmark") == "bbq":
        prediction = result.get("prediction")
        if prediction not in (0, 1, 2) or isinstance(prediction, bool):
            raise ValueError("BBQ prediction must be an answer index from 0 to 2")
        validated["prediction"] = prediction
    else:
        score = result.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError("judge score must be numeric")
        if not 0 <= score <= 1:
            raise ValueError("judge score must be in [0, 1]")
        validated["score"] = float(score)
    return validated
