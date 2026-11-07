"""Paired, source-grounded HotpotQA evaluation for a running campaign server."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import string
import time
from pathlib import Path
from typing import Any

from llm_research_bench import capability
from llm_research_bench.latency import summarize_ms


def normalize_answer(value: str) -> str:
    """HotpotQA-style normalization for short exact-match answers."""
    text = value.lower()
    text = "".join(char for char in text if char not in string.punctuation)
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def render_prompt(row: dict[str, Any], support_first: bool) -> str:
    titles = row["context"]["title"]
    sentences = row["context"]["sentences"]
    support_titles = set(row["supporting_facts"]["title"])
    docs = list(zip(titles, sentences))
    supporting = [doc for doc in docs if doc[0] in support_titles]
    distractors = [doc for doc in docs if doc[0] not in support_titles]
    ordered = supporting + distractors if support_first else distractors + supporting
    context = "\n\n".join(
        f"## {title}\n" + " ".join(f"[{i}] {sentence}" for i, sentence in enumerate(body))
        for title, body in ordered
    )
    return (
        "Answer the question using only the passages. Give a concise answer and "
        "identify the titles of the passages that support it. Return one JSON "
        'object: {"answer": "...", "supporting_titles": ["..."]}.\n\n'
        f"Passages:\n{context}\n\nQuestion: {row['question']}\nWhat is the answer?"
    )


def score_response(content: str, gold_answer: str, gold_titles: list[str]) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
        answer = parsed.get("answer") if isinstance(parsed, dict) else None
        titles = parsed.get("supporting_titles", []) if isinstance(parsed, dict) else []
        if not isinstance(answer, str) or not isinstance(titles, list) or not all(
            isinstance(title, str) for title in titles
        ):
            raise ValueError("expected string answer and list of title strings")
        parse_error, parse_status = None, "ok"
    except json.JSONDecodeError as exc:
        parsed, answer, titles = None, "", []
        parse_error, parse_status = str(exc), "malformed_json"
    except ValueError as exc:
        parsed, answer, titles = None, "", []
        parse_error, parse_status = str(exc), "invalid_response_shape"

    gold = {normalize_answer(title) for title in gold_titles}
    predicted = {normalize_answer(title) for title in titles}
    overlap = len(gold & predicted)
    precision = overlap / len(predicted) if predicted else 0.0
    recall = overlap / len(gold) if gold else 0.0
    return {
        "parsed": parsed,
        "parse_error": parse_error,
        "parse_status": parse_status,
        "answer": answer,
        "answer_exact_match": normalize_answer(answer) == normalize_answer(gold_answer),
        "support_titles_precision": precision,
        "support_titles_recall": recall,
        "support_titles_f1": 2 * precision * recall / (precision + recall)
        if precision + recall else 0.0,
        "joint_exact": normalize_answer(answer) == normalize_answer(gold_answer)
        and predicted == gold,
    }


def run_batch(base_url: str, model: str, dataset_path: Path, batch_index: int,
              batch_size: int = 5, max_gen_toks: int = 128, timeout: int = 120,
              think: bool = False, vram_csv: str | None = None) -> dict[str, Any]:
    dataset_bytes = dataset_path.read_bytes()
    dataset_sha256 = hashlib.sha256(dataset_bytes).hexdigest()
    rows = [json.loads(line) for line in dataset_bytes.decode("utf-8").splitlines()]
    manifest_path = dataset_path.with_suffix(".manifest.json")
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else None
    if source_manifest and source_manifest.get("sha256") != dataset_sha256:
        raise ValueError("RAG dataset does not match its source manifest SHA-256")
    if batch_size < 1 or batch_index < 0 or batch_index * batch_size >= len(rows):
        raise ValueError("RAG batch index/size is outside the selected dataset")
    selected = rows[batch_index * batch_size:(batch_index + 1) * batch_size]
    if len(selected) != batch_size:
        raise ValueError(f"RAG batch has {len(selected)} rows; expected {batch_size}")
    details = []
    latencies = []
    sampler = capability._VramSampler(Path(vram_csv)) if vram_csv else None
    if sampler:
        sampler.start()
    try:
        for case_index, row in enumerate(selected):
            gold_titles = list(dict.fromkeys(row["supporting_facts"]["title"]))
            prompts = {
                "support_first": render_prompt(row, True),
                "support_last": render_prompt(row, False),
            }
            payloads = {
                condition: {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_gen_toks,
                    "temperature": 0,
                    **({"chat_template_kwargs": {"enable_thinking": False}} if not think else {}),
                }
                for condition, prompt in prompts.items()
            }
            counts = {}
            count_responses = {}
            original_payloads = dict(payloads)
            for condition, payload in payloads.items():
                counts[condition], count_responses[condition] = capability._count_input_tokens(
                    base_url, payload, timeout
                )
            target = max(counts.values())
            prepared = {}
            pad_provenance = {}
            for condition, payload in payloads.items():
                if counts[condition] < target:
                    padded, payload = capability._pad_prompt_to_tokens(
                        base_url, payload, target, timeout
                    )
                    pad_provenance[condition] = padded
                else:
                    pad_provenance[condition] = {"padding": "", "count": target,
                                                 "response": count_responses[condition]}
                prepared[condition] = payload
            global_index = batch_index * batch_size + case_index
            conditions = ("support_first", "support_last") if global_index % 2 == 0 \
                else ("support_last", "support_first")
            for condition in conditions:
                payload = prepared[condition]
                started = time.perf_counter()
                response = capability._post(base_url, model, payload, timeout)
                latency = (time.perf_counter() - started) * 1000
                latencies.append(latency)
                content = capability._extract_content(response)
                scored = score_response(content, row["answer"], gold_titles)
                finish_reason = ((response.get("choices") or [{}])[0]).get("finish_reason")
                response_status = "truncated" if finish_reason == "length" else scored["parse_status"]
                usage_tokens = (response.get("usage") or {}).get("prompt_tokens")
                details.append({
                    "id": row["id"], "type": row["type"], "level": row["level"],
                    "condition": condition, "question": row["question"],
                    "gold_answer": row["answer"], "gold_support_titles": gold_titles,
                    "gold_support_facts": row["supporting_facts"],
                    "prompt": payload["messages"][0]["content"], "request": payload,
                    "response": response, "content": content, **scored,
                    "response_status": response_status,
                    "matched_input_tokens": target,
                    "usage_prompt_tokens": usage_tokens,
                    "usage_matches_input_tokens": usage_tokens == target,
                    "padding": pad_provenance[condition].get("padding", ""),
                    "token_count_provenance": {
                        "before": {"request": original_payloads[condition],
                                   "count": counts[condition], "response": count_responses[condition]},
                        "after": {**pad_provenance[condition], "request": prepared[condition]},
                    },
                    "latency_ms": round(latency, 1),
                })
    finally:
        if sampler:
            sampler.stop()

    summaries = {}
    for condition in ("support_first", "support_last"):
        condition_rows = [row for row in details if row["condition"] == condition]
        summaries[condition] = {
            "n": len(condition_rows),
            "answer_exact_match": sum(row["answer_exact_match"] for row in condition_rows),
            "support_title_f1_mean": round(sum(row["support_titles_f1"] for row in condition_rows)
                                             / max(1, len(condition_rows)), 4),
            "joint_exact": sum(row["joint_exact"] for row in condition_rows),
        }
    latency_summary = summarize_ms(latencies)
    return {
        "dataset": {"file": dataset_path.name, "sha256": dataset_sha256,
                    "manifest": source_manifest},
        "results": {"hotpotqa_rag": {"name": "hotpotqa_rag", "conditions": summaries,
                                      "usage_mismatch_count": sum(
                                          not row["usage_matches_input_tokens"] for row in details),
                                      "latency_p50_ms": latency_summary["p50_ms"],
                                      "latency_p95_ms": latency_summary["p95_ms"]}},
        "cases": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--batch-index", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--max-gen-toks", type=int, default=128)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--think", action="store_true")
    parser.add_argument("--vram-csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_batch(args.base_url, args.model, args.dataset, args.batch_index,
                       args.batch_size, args.max_gen_toks, args.timeout,
                       args.think, args.vram_csv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
