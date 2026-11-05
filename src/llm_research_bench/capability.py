"""Deterministic capability probes: JSON-schema adherence and tool-call validity.

These are probes, not leaderboard tasks: the case sets are small, fixed and
synthetic, so results describe this model/server pair only. Every probe returns
a campaign-compatible ``results.json`` payload (``results.<suite>``) so the
existing ``campaign summarize`` picks it up without a second schema.
"""

from __future__ import annotations

import argparse
import json
import random
import time
import urllib.request
from pathlib import Path
from typing import Any

from llm_research_bench.latency import percentile, summarize_ms

FILLER = ("The quick brown fox jumps over the lazy dog while the engineer "
          "records the measurement carefully and repeats the run. ")

SCHEMAS: dict[str, dict[str, Any]] = {
    "person": {
        "type": "object",
        "required": ["name", "age", "city"],
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "city": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "weather": {
        "type": "object",
        "required": ["city", "unit"],
        "properties": {"city": {"type": "string"}, "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}},
        "additionalProperties": False,
    },
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Current weather for a city",
            "parameters": {
                "type": "object",
                "required": ["city", "unit"],
                "properties": {
                    "city": {"type": "string"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
            },
        },
    }
]

CASES: dict[str, list[dict[str, Any]]] = {
    # Rounds are generated from --limit/--clients; the key only has to exist so
    # argparse can offer the suite name.
    "concurrency": [],
    "structured_output": [
        {"prompt": "Extract: Ada Lovelace, 36, London.", "schema": "person"},
        {"prompt": "Extract: Grace Hopper, 85, New York.", "schema": "person"},
        {"prompt": "Extract: Alan Turing, 41, Manchester.", "schema": "person"},
        {"prompt": "Extract: Katherine Johnson, 101, Hampton.", "schema": "person"},
        {"prompt": "Extract: Linus Torvalds, 54, Portland.", "schema": "person"},
        {"prompt": "Weather in Lisbon, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Oslo, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Miami, use fahrenheit.", "schema": "weather"},
        {"prompt": "Weather in Tokyo, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Lima, use celsius.", "schema": "weather"},
    ],
    "tool_call": [
        {"prompt": "What is the weather in Lisbon in celsius?", "tool": "get_weather"},
        {"prompt": "What is the weather in Oslo in celsius?", "tool": "get_weather"},
        {"prompt": "What is the weather in Miami in fahrenheit?", "tool": "get_weather"},
        {"prompt": "What is the weather in Tokyo in celsius?", "tool": "get_weather"},
        {"prompt": "What is the weather in Lima in celsius?", "tool": "get_weather"},
    ],
}

TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate a small JSON-Schema subset; returns human-readable errors."""
    errors: list[str] = []
    expected = schema.get("type")
    if expected:
        py = TYPES.get(expected)
        if py is None:
            errors.append(f"{path}: unsupported schema type {expected!r}")
        elif expected == "integer" and isinstance(instance, bool):
            errors.append(f"{path}: expected integer, got boolean")
        elif not isinstance(instance, py):
            errors.append(f"{path}: expected {expected}, got {type(instance).__name__}")
            return errors
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in enum {schema['enum']}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                errors.extend(validate(value, props[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property {key!r}")
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors.extend(validate(item, schema["items"], f"{path}[{i}]"))
    return errors


def _post(base_url: str, model: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _extract_content(response: dict[str, Any]) -> str:
    return response["choices"][0]["message"].get("content") or ""


def run_suite(
    base_url: str,
    model: str,
    suite: str,
    *,
    limit: int,
    seed: int = 42,
    timeout: int = 600,
    clients: int = 2,
) -> dict[str, Any]:
    if suite == "concurrency":
        cases = [{"round": i} for i in range(max(1, limit))]
        clients = max(1, int(clients))
    else:
        cases = CASES[suite][:limit]
    random.Random(seed).shuffle(cases)
    details: list[dict[str, Any]] = []
    latencies_ms: list[float] = []
    round_ms: list[float] = []
    for case in cases:
        if suite == "concurrency":
            from concurrent.futures import ThreadPoolExecutor

            def hit(client: int) -> tuple[float | None, str | None]:
                prompt = (f"Round {case['round']} client {client}. " + FILLER * 40
                          + "\nReply with one short sentence.")
                started = time.perf_counter()
                try:
                    _post(base_url, model, {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 32,
                        "temperature": 0,
                    }, timeout)
                except Exception as exc:  # a 400 (e.g. ctx/parallel split) must not kill the cell
                    return None, str(exc)
                return (time.perf_counter() - started) * 1000, None

            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=clients) as pool:
                results = list(pool.map(hit, range(clients)))
            elapsed = (time.perf_counter() - started) * 1000
            walls = [w for w, _ in results if w is not None]
            errors = [e for _, e in results if e]
            latencies_ms.extend(walls)
            if errors:
                details.append({"round": case["round"], "valid": False, "errors": errors})
                continue
            round_ms.append(elapsed)
            details.append({"round": case["round"], "wall_ms": [round(w, 1) for w in walls],
                            "round_ms": round(elapsed, 1), "valid": True})
            continue
        if suite == "structured_output":
            schema = SCHEMAS[case["schema"]]
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{case['prompt']} Reply with JSON only, matching this schema: "
                        f"{json.dumps(schema)}",
                    }
                ],
                "max_tokens": 256,
                "temperature": 0,
            }
            started = time.perf_counter()
            content = _extract_content(_post(base_url, model, payload, timeout))
            latencies_ms.append((time.perf_counter() - started) * 1000)
            try:
                parsed = json.loads(content)
                errors = validate(parsed, schema)
            except json.JSONDecodeError as exc:
                parsed, errors = None, [f"invalid JSON: {exc}"]
            details.append({"prompt": case["prompt"], "valid": not errors, "errors": errors})
        else:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": case["prompt"]}],
                "tools": TOOLS,
                "max_tokens": 256,
                "temperature": 0,
            }
            started = time.perf_counter()
            message = _post(base_url, model, payload, timeout)["choices"][0]["message"]
            latencies_ms.append((time.perf_counter() - started) * 1000)
            calls = message.get("tool_calls") or []
            errors = []
            if not calls:
                errors.append("no tool_calls in response")
            else:
                args = calls[0].get("function", {}).get("arguments")
                try:
                    parsed_args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    parsed_args, errors = None, ["tool arguments are not JSON"]
                if parsed_args is not None:
                    errors = validate(parsed_args, TOOLS[0]["function"]["parameters"])
                if calls[0].get("function", {}).get("name") != case["tool"]:
                    errors.append("wrong tool name")
            details.append({"prompt": case["prompt"], "valid": not errors, "errors": errors})
    valid = sum(1 for d in details if d["valid"])
    rate = valid / len(details) if details else 0.0
    latency = summarize_ms(latencies_ms)
    return {
        "results": {
            suite: {
                "name": suite,
                "alias": suite,
                "sample_len": len(details),
                "valid_rate,none": round(rate, 4),
                "valid_rate_stderr,none": round((rate * (1 - rate) / len(details)) ** 0.5, 6)
                if details
                else 0.0,
                # End-to-end client latency; deliberately not a ",none" metric so
                # the campaign summary does not treat it as a quality score.
                "latency_p50_ms": latency["p50_ms"],
                "latency_p95_ms": latency["p95_ms"],
                "latency_n": latency["n"],
                **({
                    "round_p50_ms": percentile(round_ms, 50),
                    "slowest_ms": round(max(latencies_ms), 1) if latencies_ms else None,
                    "aggregate_rps": round(clients * len(round_ms) / (sum(round_ms) / 1000), 3)
                    if round_ms else None,
                } if suite == "concurrency" else {}),
            }
        },
        "cases": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--base-url", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--suite", choices=sorted(CASES), required=True)
    run.add_argument("--limit", type=int, default=10)
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--clients", type=int, default=2)
    run.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = run_suite(args.base_url, args.model, args.suite, limit=args.limit,
                        seed=args.seed, clients=args.clients)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
