"""Offline quant-pair cascade oracle replay (F3, exploratory only).

The repository records exactly one pair of per-item model outputs over the
same items on the same host: Qwen3-1.7B Q4_K_M vs Q8_0 on
``local-rtx3060ti-8gib``, arc_challenge and hellaswag, first-100 subsets.
This module joins those rows and reports the *oracle cascade ceiling* -- the
accuracy of an ideal router that always picks an arm that answered correctly.

That number is a ceiling, not a router policy: an oracle cannot be deployed,
so it bounds what any selector over these two arms could gain and nothing
more. Cross-model cascade replay is not possible with the recorded artifacts
(no second model has per-item outputs anywhere in results/campaigns).
"""

from __future__ import annotations

import hashlib
import json
from math import comb
from pathlib import Path
from typing import Any, Dict, List

from .benchmark_suite import compute_clopper_pearson_ci

REPO = Path(__file__).resolve().parents[2]
STATION = Path("results/campaigns/local-rtx3060ti-qwen3-1.7b-v1/local-rtx3060ti-8gib")
RAW_SUBDIR = Path("knowledge-mcq/raw/wnnhj7xv")
ARMS = {"q4_k_m": "qwen3-1.7b-q4km", "q8_0": "qwen3-1.7b-q8"}
DATASETS = ("arc_challenge", "hellaswag")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _doc_key(row: Dict[str, Any]) -> str:
    # arc_challenge rows carry doc.id; hellaswag rows do not, so fall back to
    # the full document payload to prove both arms saw the same item.
    doc = row["doc"]
    if doc.get("id") is not None:
        return f"id:{doc['id']}"
    return "doc:" + json.dumps(doc, sort_keys=True)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for b/c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(0, min(b, c) + 1)) / float(2 ** n)
    return min(1.0, 2.0 * tail)


def pair_rows(
    left: List[Dict[str, Any]], right: List[Dict[str, Any]], dataset: str
) -> List[tuple]:
    """Zip two arms row-by-row, failing closed on any item or prompt mismatch."""
    if len(left) != len(right):
        raise ValueError(f"{dataset}: row counts differ ({len(left)} vs {len(right)})")
    if not left:
        raise ValueError(f"{dataset}: no rows")
    pairs = []
    for index, (a, b) in enumerate(zip(left, right)):
        if _doc_key(a) != _doc_key(b):
            raise ValueError(f"{dataset} row {index}: item mismatch between arms")
        if a.get("prompt_hash") != b.get("prompt_hash"):
            raise ValueError(f"{dataset} row {index}: prompt_hash mismatch between arms")
        pairs.append((a, b))
    return pairs


def summarize(pairs: List[tuple], dataset: str, key: str = "acc") -> Dict[str, Any]:
    n = len(pairs)
    both = sum(1 for a, b in pairs if a[key] == 1 and b[key] == 1)
    left_only = sum(1 for a, b in pairs if a[key] == 1 and b[key] == 0)
    right_only = sum(1 for a, b in pairs if a[key] == 0 and b[key] == 1)
    neither = n - both - left_only - right_only
    left_correct = both + left_only
    right_correct = both + right_only
    oracle_correct = both + left_only + right_only
    return {
        "dataset": dataset,
        "metric": key,
        "n": n,
        "cells": {
            "both_correct": both,
            "left_only": left_only,
            "right_only": right_only,
            "both_wrong": neither,
        },
        "accuracy": {
            "left": round(left_correct / n, 6),
            "right": round(right_correct / n, 6),
            "oracle": round(oracle_correct / n, 6),
            "oracle_gain_over_best_arm": round(oracle_correct / n - max(left_correct, right_correct) / n, 6),
        },
        "ci95_clopper_pearson": {
            "left": compute_clopper_pearson_ci(left_correct, n),
            "right": compute_clopper_pearson_ci(right_correct, n),
            "oracle": compute_clopper_pearson_ci(oracle_correct, n),
        },
        "agreement_pct": round((both + neither) / n * 100, 3),
        "mcnemar_exact_p": mcnemar_exact(left_only, right_only),
    }


def analyze() -> Dict[str, Any]:
    arms = {label: REPO / STATION / name / RAW_SUBDIR for label, name in ARMS.items()}
    inputs: Dict[str, Any] = {}
    models: Dict[str, Any] = {}
    for label, raw_dir in arms.items():
        meta = json.loads((raw_dir.parent.parent / "meta.json").read_text(encoding="utf-8"))
        models[label] = {
            "file": meta["model"]["file"],
            "quantization": meta["model"]["quantization"],
            "hf_repo": meta["model"]["hf_repo"],
            "hf_revision": meta["model"]["hf_revision"],
            "gguf_sha256": meta["model"]["sha256"],
            "size_bytes": meta["model"]["size_bytes"],
        }

    results: Dict[str, Any] = {}
    for dataset in DATASETS:
        paths = {label: next(raw_dir.glob(f"samples_{dataset}_*.jsonl")) for label, raw_dir in arms.items()}
        inputs[dataset] = {
            label: {"path": str(path.relative_to(REPO)), "sha256": sha256_file(path)}
            for label, path in paths.items()
        }
        pairs = pair_rows(
            _load_jsonl(paths["q4_k_m"]), _load_jsonl(paths["q8_0"]), dataset
        )
        results[dataset] = {
            "acc": summarize(pairs, dataset, "acc"),
            "acc_norm": summarize(pairs, dataset, "acc_norm"),
        }

    return {
        "status": "exploratory_analysis",
        "analysis": "quant_pair_cascade_oracle_ceiling",
        "arms": {"left": "q4_k_m", "right": "q8_0", "both": "Qwen3-1.7B"},
        "host": "local-rtx3060ti-8gib",
        "models": models,
        "inputs": inputs,
        "results": results,
        "claims": {
            "supported": (
                "On these fixed first-100 subsets, the optional-gain pool between "
                "Q4_K_M and Q8_0 is small; the oracle ceiling bounds any selector "
                "over these two arms."
            ),
            "not_supported": [
                "That a deployable router achieves any part of the oracle gain.",
                "That these two arms differ in capability (passing CI overlap, tiny discordant counts).",
                "Any cross-model routing or cascade claim: no second-model per-item outputs are recorded in this repository.",
            ],
        },
        "limitations": [
            "Fixed first-100 items per task, selected by run constraints, not a random sample of each benchmark.",
            "Single host, single greedy decode (temperature 0.0), one run per arm: no technical replicates.",
            "Arms differ in packaging as well as precision (Q4_K_M from unsloth/Qwen3-1.7B-GGUF, Q8_0 from Qwen/Qwen3-1.7B-GGUF), so a quant effect and a packaging effect cannot be separated.",
            "Oracle framing is an upper bound computed with hindsight over both arms; it is not a leakage-free predictor.",
        ],
        "blocked": {
            "cross_model_cascade_replay": "No per-item outputs for any second model exist under results/campaigns; only llama-bench timing artifacts (no correctness labels) mention other models.",
        },
    }


def main() -> None:
    out_path = REPO / "results/analysis/quant-cascade-oracle-v1.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = analyze()
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(
        {
            name: {
                metric: {
                    "left": row["accuracy"]["left"],
                    "right": row["accuracy"]["right"],
                    "oracle": row["accuracy"]["oracle"],
                    "gain": row["accuracy"]["oracle_gain_over_best_arm"],
                    "agreement_pct": row["agreement_pct"],
                    "mcnemar_p": row["mcnemar_exact_p"],
                }
                for metric, row in per_task.items()
            }
            for name, per_task in artifact["results"].items()
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
