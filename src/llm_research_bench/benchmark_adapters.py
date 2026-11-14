"""Small CSV/JSONL adapters for the pinned public benchmark formats."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any


def _read_csv(path: str | Path, required: set[str]) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path} is missing required CSV columns: {sorted(required)}")
        rows = list(reader)
    return rows


def load_xstest(path: str | Path) -> list[dict[str, Any]]:
    rows = _read_csv(path, {"id", "prompt", "label", "type"})
    if len(rows) != 450:
        raise ValueError(f"expected 450 XSTest rows, got {len(rows)}")
    if any(row["label"] not in {"safe", "unsafe"} or not row["prompt"] for row in rows):
        raise ValueError("invalid XSTest label or empty prompt")
    return [
        {"id": f"xstest:{row['id']}", "benchmark": "xstest", "prompt": row["prompt"],
         "label": row["label"], "type": row["type"]}
        for row in rows
    ]


def load_strongreject(path: str | Path) -> list[dict[str, Any]]:
    rows = _read_csv(path, {"category", "source", "forbidden_prompt"})
    if len(rows) != 313:
        raise ValueError(f"expected 313 StrongREJECT rows, got {len(rows)}")
    if any(not row["forbidden_prompt"] for row in rows):
        raise ValueError("StrongREJECT contains an empty prompt")
    return [
        {"id": f"strongreject:{index}", "benchmark": "strongreject",
         "prompt": row["forbidden_prompt"], "category": row["category"],
         "source": row["source"]}
        for index, row in enumerate(rows)
    ]


def load_bbq(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            required = {
                "example_id", "question_index", "question_polarity",
                "context_condition", "category", "context", "question",
                "ans0", "ans1", "ans2", "answer_info", "label",
            }
            if not required.issubset(row):
                raise ValueError(f"BBQ row {line_number} is missing required fields")
            if row["label"] not in (0, 1, 2):
                raise ValueError(f"BBQ row {line_number} has invalid label")
            rows.append({**row, "benchmark": "bbq"})
    return rows


def load_bbq_target_locations(path: str | Path) -> dict[tuple[int, str, str], int]:
    """Load the official target_loc metadata keyed by benchmark item identity."""
    rows = _read_csv(path, {"example_id", "category", "question_index", "target_loc"})
    targets = {}
    for row in rows:
        key = (int(row["example_id"]), row["category"], row["question_index"])
        target = int(row["target_loc"])
        if target not in (0, 1, 2) or key in targets:
            raise ValueError(f"invalid or duplicate BBQ target metadata for {key}")
        targets[key] = target
    return targets


def sample_bbq_stratified(
    rows: list[dict[str, Any]], per_condition: int = 10, seed: int = 20261114
) -> list[dict[str, Any]]:
    """Sample up to N rows per category × context condition deterministically."""
    if per_condition < 1:
        raise ValueError("per_condition must be positive")
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        condition = row["context_condition"]
        if condition not in {"ambig", "disambig"}:
            raise ValueError(f"invalid BBQ context_condition: {condition!r}")
        buckets.setdefault((row["category"], condition), []).append(row)
    rng = random.Random(seed)
    selected = []
    for key in sorted(buckets):
        bucket = sorted(
            buckets[key],
            key=lambda row: (int(row["example_id"]), str(row["question_index"])),
        )
        if len(bucket) <= per_condition:
            selected.extend(bucket)
            continue
        interval = len(bucket) // per_condition
        start = rng.randrange(interval)
        selected.extend(
            bucket[start + index * interval] for index in range(per_condition)
        )
    return selected
