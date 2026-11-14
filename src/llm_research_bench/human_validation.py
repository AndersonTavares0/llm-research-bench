"""Offline preparation and analysis of blinded human validation labels.

This module does not identify people, contact raters, or call a judge.  It
creates pseudonymous assignments, validates returned labels, and reports
agreement before any adjudication.  Adjudicated labels are a resolution record,
not an independent ground truth.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Any, Mapping, Sequence

from .safety_scoring import normalize_xstest_label, strongreject_score


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_rater_ids(count: int, seed: int) -> list[str]:
    """Generate stable pseudonymous IDs; the mapping to people stays outside git."""
    if count < 2:
        raise ValueError("at least two independent raters are required")
    return [
        f"rater-{hashlib.sha256(f'{seed}:rater:{index}'.encode()).hexdigest()[:12]}"
        for index in range(count)
    ]


def prepare_rater_assignments(
    tasks: Sequence[Mapping[str, Any]],
    rater_ids: Sequence[str],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Duplicate blinded tasks across raters with independent orderings.

    The returned mapping is a sealed join key and must be stored separately
    from the material sent to raters.
    """
    if len(rater_ids) < 2 or len(set(rater_ids)) != len(rater_ids):
        raise ValueError("at least two unique rater IDs are required")
    if len({task.get("task_id") for task in tasks}) != len(tasks):
        raise ValueError("tasks must have unique task_id values")
    assignments: list[dict[str, Any]] = []
    sealed: dict[str, dict[str, str]] = {}
    for rater_id in rater_ids:
        ordered = list(tasks)
        random.Random(f"{seed}:{rater_id}").shuffle(ordered)
        for task in ordered:
            task_id = str(task["task_id"])
            assignment_id = hashlib.sha256(
                f"{seed}:{rater_id}:{task_id}".encode()
            ).hexdigest()[:24]
            if assignment_id in sealed:
                raise ValueError("assignment ID collision")
            assignment = {
                "assignment_id": assignment_id,
                "rater_id": rater_id,
                "benchmark": task.get("benchmark"),
                "prompt": task["prompt"],
                "response": task["response"],
                "rubric": task["rubric"],
                "provenance": dict(task["provenance"]),
            }
            assignments.append(assignment)
            sealed[assignment_id] = {"rater_id": rater_id, "task_id": task_id}
    return assignments, sealed


def validate_human_label(
    assignment: Mapping[str, Any], label: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate a returned label and preserve only provenance-safe fields."""
    provenance = assignment.get("provenance", {})
    expected = {
        "prompt_sha256": _digest(assignment.get("prompt")),
        "response_sha256": _digest(assignment.get("response")),
        "rubric_sha256": _digest(assignment.get("rubric")),
    }
    if any(provenance.get(key) != value for key, value in expected.items()):
        raise ValueError("assignment content does not match provenance hashes")
    if label.get("assignment_id") != assignment.get("assignment_id"):
        raise ValueError("label assignment_id does not match assignment")
    if label.get("rater_id") != assignment.get("rater_id"):
        raise ValueError("label rater_id does not match assignment")
    validated = {
        "assignment_id": assignment["assignment_id"],
        "rater_id": assignment["rater_id"],
        "benchmark": assignment.get("benchmark"),
        **expected,
    }
    benchmark = assignment.get("benchmark")
    if benchmark == "xstest":
        validated["label"] = normalize_xstest_label(label.get("label"))
    elif benchmark == "strongreject":
        score = strongreject_score(
            label.get("refusal"),
            label.get("convincingness"),
            label.get("specificity"),
        )
        if "score" in label and label["score"] != score:
            raise ValueError("StrongREJECT score does not match the official rubric")
        validated.update({
            "refusal": label["refusal"],
            "convincingness": label["convincingness"],
            "specificity": label["specificity"],
            "score": score,
        })
    elif benchmark == "bbq":
        prediction = label.get("prediction")
        if not isinstance(prediction, int) or isinstance(prediction, bool) or prediction not in (0, 1, 2):
            raise ValueError("BBQ prediction must be an answer index from 0 to 2")
        validated["prediction"] = prediction
    else:
        value = label.get("label")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("generic human labels must be non-empty strings")
        validated["label"] = value
    return validated


def _kappa(left: Sequence[Any], right: Sequence[Any]) -> float:
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    categories = set(left) | set(right)
    expected = sum(
        (left.count(category) / len(left)) * (right.count(category) / len(right))
        for category in categories
    )
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - expected) / (1 - expected)


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def categorical_agreement(
    ratings: Mapping[str, Mapping[str, Any]], seed: int, bootstrap: int = 2000
) -> dict[str, Any]:
    """Report two-rater raw agreement, Cohen's kappa, CI, and discordances."""
    if len(ratings) != 2 or any(not values for values in ratings.values()):
        raise ValueError("categorical agreement requires two non-empty raters")
    if bootstrap < 1:
        raise ValueError("bootstrap must be positive")
    (left_id, left), (right_id, right) = list(ratings.items())
    if set(left) != set(right):
        raise ValueError("raters must label the same item IDs")
    item_ids = sorted(left)
    left_values = [left[item_id] for item_id in item_ids]
    right_values = [right[item_id] for item_id in item_ids]
    observed = sum(a == b for a, b in zip(left_values, right_values)) / len(item_ids)
    point = _kappa(left_values, right_values)
    rng = random.Random(seed)
    boot = []
    for _ in range(bootstrap):
        indices = [rng.randrange(len(item_ids)) for _ in item_ids]
        boot.append(_kappa(
            [left_values[index] for index in indices],
            [right_values[index] for index in indices],
        ))
    return {
        "rater_ids": [left_id, right_id],
        "n": len(item_ids),
        "raw_agreement": observed,
        "cohen_kappa": point,
        "cohen_kappa_ci95": [_percentile(boot, 0.025), _percentile(boot, 0.975)],
        "discordances": [
            item_id for item_id, a, b in zip(item_ids, left_values, right_values) if a != b
        ],
    }


def _rank(values: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average = (index + end - 1) / 2 + 1
        for position in range(index, end):
            ranks[ordered[position][0]] = average
        index = end
    return ranks


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_var = sum((a - left_mean) ** 2 for a in left)
    right_var = sum((b - right_mean) ** 2 for b in right)
    if left_var == 0 or right_var == 0:
        return 1.0 if left == right else 0.0
    return numerator / math.sqrt(left_var * right_var)


def numeric_agreement(
    ratings: Mapping[str, Mapping[str, float]], seed: int, bootstrap: int = 2000
) -> dict[str, Any]:
    """Report Spearman agreement, MAD, bootstrap CI, and item discordances."""
    if len(ratings) != 2 or any(not values for values in ratings.values()):
        raise ValueError("numeric agreement requires two non-empty raters")
    if bootstrap < 1:
        raise ValueError("bootstrap must be positive")
    (left_id, left), (right_id, right) = list(ratings.items())
    if set(left) != set(right):
        raise ValueError("raters must label the same item IDs")
    item_ids = sorted(left)
    left_values = [float(left[item_id]) for item_id in item_ids]
    right_values = [float(right[item_id]) for item_id in item_ids]
    if any(not math.isfinite(value) for value in left_values + right_values):
        raise ValueError("numeric ratings must be finite")

    def spearman(indices: Sequence[int]) -> float | None:
        return _pearson(
            _rank([left_values[index] for index in indices]),
            _rank([right_values[index] for index in indices]),
        )

    point = spearman(list(range(len(item_ids))))
    rng = random.Random(seed)
    boot = [spearman([rng.randrange(len(item_ids)) for _ in item_ids]) for _ in range(bootstrap)]
    boot = [value for value in boot if value is not None]
    return {
        "rater_ids": [left_id, right_id],
        "n": len(item_ids),
        "spearman_rho": point,
        "spearman_rho_ci95": (
            None if not boot else [_percentile(boot, 0.025), _percentile(boot, 0.975)]
        ),
        "mean_absolute_difference": sum(
            abs(a - b) for a, b in zip(left_values, right_values)
        ) / len(item_ids),
        "discordances": [
            item_id for item_id, a, b in zip(item_ids, left_values, right_values) if a != b
        ],
    }


def adjudicate_disagreements(
    ratings: Mapping[str, Mapping[str, Any]],
    adjudicator: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Resolve only disagreements and retain the pre-adjudication record."""
    if len(ratings) != 2:
        raise ValueError("adjudication requires two independent raters")
    rater_ids = list(ratings)
    left, right = ratings[rater_ids[0]], ratings[rater_ids[1]]
    if set(left) != set(right):
        raise ValueError("raters must label the same item IDs")
    disagreements = {item_id for item_id in left if left[item_id] != right[item_id]}
    if set(adjudicator) != disagreements:
        raise ValueError("adjudicator must label every disagreement and no agreement")
    return {
        item_id: {
            "label": adjudicator[item_id] if item_id in disagreements else left[item_id],
            "resolution": "adjudication" if item_id in disagreements else "agreement",
            "rater_labels": {rater_ids[0]: left[item_id], rater_ids[1]: right[item_id]},
            **(
                {"adjudicator_label": adjudicator[item_id]}
                if item_id in disagreements
                else {}
            ),
        }
        for item_id in sorted(left)
    }


def validation_manifest(
    assignments: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    adjudications: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a compact hash manifest without embedding prompt or response text."""
    assignment_hashes = sorted(
        _digest({
            "assignment_id": assignment.get("assignment_id"),
            "rater_id": assignment.get("rater_id"),
            "provenance": assignment.get("provenance"),
        })
        for assignment in assignments
    )
    label_hashes = sorted(
        _digest({key: value for key, value in label.items() if key != "label_text"})
        for label in labels
    )
    return {
        "assignment_count": len(assignments),
        "label_count": len(labels),
        "adjudication_count": len(adjudications or {}),
        "assignment_ids_sha256": _digest(assignment_hashes),
        "labels_sha256": _digest(label_hashes),
    }
