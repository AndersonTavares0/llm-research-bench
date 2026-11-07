#!/usr/bin/env python3
"""Bounded in-service latency probe for an already-running llama-server.

Uses only the public chat-completions endpoint, at low request volume, and reads
the server-reported timings (prompt_ms / predicted_ms / cache_n) plus a
client-side wall clock. This does not acquire a lab lease and does not stop
production; it measures the service as it is deployed.

Limitations that must travel with the numbers:
- the model is whatever the service serves, not the lab campaign model;
- the server keeps its production settings (ctx, parallel slots, KV type);
- request volume is small and the service may be shared with other clients.

Usage:
    python3 in-service-probe.py --base-url http://127.0.0.1:18081 \
        --model qwen3.5:4B --out /tmp/probe.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

FILLER = ("The quick brown fox jumps over the lazy dog while the engineer "
          "records the measurement carefully and repeats the run. ")


def post(base_url: str, model: str, prompt: str, max_tokens: int, timeout: int) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read())
    wall_ms = (time.perf_counter() - started) * 1000
    timings = payload.get("timings") or {}
    usage = payload.get("usage") or {}
    return {
        "wall_ms": round(wall_ms, 2),
        "prompt_n": timings.get("prompt_n", usage.get("prompt_tokens")),
        "prompt_ms": timings.get("prompt_ms"),
        "predicted_n": timings.get("predicted_n", usage.get("completion_tokens")),
        "predicted_ms": timings.get("predicted_ms"),
        "cache_n": timings.get("cache_n"),
        "finish_reason": payload["choices"][0].get("finish_reason"),
    }


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    pos = (len(ordered) - 1) * q / 100
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (pos - low), 2)


def summarize(rows: list[dict], key: str) -> dict:
    values = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return {"n": len(values), "p50": pct(values, 50), "p95": pct(values, 95),
            "mean": round(statistics.fmean(values), 2) if values else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    result: dict = {"model": args.model, "base_url": args.base_url,
                    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "lengths": [], "cache": [], "concurrency": []}

    # 1. Latency vs prompt length (distinct prompts, no prefix reuse).
    for reps in (4, 20, 60, 120):
        rows = []
        for i in range(args.reps):
            prompt = f"Run {i}. " + FILLER * reps + "\nReply with one short sentence."
            rows.append(post(args.base_url, args.model, prompt, 32, args.timeout))
        result["lengths"].append({
            "requested_reps": reps,
            "prompt_tokens": rows[0]["prompt_n"],
            "wall_ms": summarize(rows, "wall_ms"),
            "prompt_ms": summarize(rows, "prompt_ms"),
            "prefill_tok_s": round(rows[0]["prompt_n"] / (rows[0]["prompt_ms"] / 1000), 2)
            if rows[0].get("prompt_ms") else None,
            "decode_tok_s": round(rows[0]["predicted_n"] / (rows[0]["predicted_ms"] / 1000), 2)
            if rows[0].get("predicted_ms") else None,
            "cache_n": [r["cache_n"] for r in rows],
        })

    # 2. Repeated identical prompt: does the server reuse a cached prefix?
    prompt = "Caching check. " + FILLER * 40 + "\nReply with one short sentence."
    for _ in range(args.reps):
        result["cache"].append(post(args.base_url, args.model, prompt, 32, args.timeout))

    # 3. Two concurrent clients on the deployed slot count.
    def one(i: int) -> dict:
        return post(args.base_url, args.model, f"Concurrent {i}. " + FILLER * 40, 32, args.timeout)

    for round_no in range(args.reps):
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(one, (round_no * 2, round_no * 2 + 1)))
        result["concurrency"].append({
            "round": round_no,
            "wall_ms": [r["wall_ms"] for r in rows],
            "prompt_tokens": [r["prompt_n"] for r in rows],
        })

    result["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
