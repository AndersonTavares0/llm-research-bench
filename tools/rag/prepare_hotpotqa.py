"""Select a small, deterministic, provenance-preserving HotpotQA slice."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

REPO = "hotpotqa/hotpot_qa"
REVISION = "1908d6afbbead072334abe2965f91bd2709910ab"
LICENSE = "CC-BY-SA-4.0"
PER_TYPE = 50
MAX_CONTEXT_CHARS = 10_000


def _eligible(row: dict) -> bool:
    context = row["context"]
    titles = set(context["title"])
    facts = row["supporting_facts"]
    if len(facts["title"]) != len(facts["sent_id"]):
        return False
    if len({title for title, _ in zip(facts["title"], facts["sent_id"])}) < 2:
        return False
    if len(json.dumps(context, ensure_ascii=False)) > MAX_CONTEXT_CHARS:
        return False
    return all(
        title in titles and 0 <= sentence < len(context["sentences"][context["title"].index(title)])
        for title, sentence in zip(facts["title"], facts["sent_id"])
    )


def select_rows(rows: Iterable[dict], per_type: int = PER_TYPE) -> list[dict]:
    buckets: dict[str, list[dict]] = {"bridge": [], "comparison": []}
    for row in rows:
        if row["type"] not in buckets or not _eligible(row):
            continue
        buckets[row["type"]].append(row)
    selected_by_type = {}
    for kind in ("bridge", "comparison"):
        ranked = sorted(
            buckets[kind],
            key=lambda row: hashlib.sha256(row["id"].encode("utf-8")).hexdigest(),
        )
        if len(ranked) < per_type:
            raise ValueError(f"only {len(ranked)} eligible {kind} items; need {per_type}")
        selected_by_type[kind] = ranked[:per_type]
    return [selected_by_type[kind][index]
            for index in range(per_type) for kind in ("bridge", "comparison")]


def main() -> None:
    from datasets import load_dataset

    rows = load_dataset(REPO, "distractor", split="validation", revision=REVISION, streaming=True)
    selected = select_rows(rows)
    out = Path("data/rag/hotpotqa-validation-100.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as stream:
        for row in selected:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    manifest = {
        "dataset": REPO,
        "revision": REVISION,
        "config": "distractor",
        "split": "validation",
        "license": LICENSE,
        "datasets_version": __import__("datasets").__version__,
        "selector": f"SHA256(id) ascending; first {PER_TYPE} per type; interleave bridge/comparison; context JSON <= {MAX_CONTEXT_CHARS} chars; >=2 supported titles; support indices validated",
        "balanced_types": {kind: PER_TYPE for kind in ("bridge", "comparison")},
        "row_count": len(selected),
        "ids": [row["id"] for row in selected],
        "sha256": digest,
    }
    Path("data/rag/hotpotqa-validation-100.manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"rows": len(selected), "sha256": digest, "output": str(out)}))


if __name__ == "__main__":
    main()
