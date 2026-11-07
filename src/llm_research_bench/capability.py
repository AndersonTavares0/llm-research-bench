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
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

from llm_research_bench.latency import percentile, summarize_ms
from llm_research_bench.evaluators.long_context_evaluator import LongContextEvaluator

FILLER = ("The quick brown fox jumps over the lazy dog while the engineer "
          "records the measurement carefully and repeats the run. ")

NEEDLE_CASES = [
    ("K01", "Q7M4K2"), ("K02", "P9V3D6"), ("K03", "R2C8W5"),
    ("K04", "H6N1X4"), ("K05", "B3T9L7"), ("K06", "M5F2Z8"),
    ("K07", "C8J4A1"), ("K08", "W1G7P3"), ("K09", "D4Y6S2"),
    ("K10", "X2L5N9"),
]
NEEDLE_DEPTHS = (10, 50, 90)
NEEDLE_FILLERS = 340
NEEDLE_DECOYS = [
    ("D01", "A7C3M9"), ("D02", "F2R8K4"), ("D03", "J5W1P6"), ("D04", "N9B4T2"),
    ("D05", "C6X2L8"), ("D06", "V3H7Q1"), ("D07", "G8D5Y2"), ("D08", "M1P6Z4"),
]
NEEDLE_DISTRACTOR_ROWS = (205, 220, 235, 250, 265, 280, 295, 310)
NEEDLE_ARCHIVE_REVISIONS = range(2017, 2025)
NEEDLE_PAD_TOKENS = ("x", "a", "note", "item", "blue", "the", "and", "z")
NEEDLE_BATCH_SIZE = 5

EXAMPLES: dict[str, dict[str, Any]] = {
    "person": {"name": "Ada Lovelace", "age": 36, "city": "London"},
    "weather": {"city": "Lisbon", "unit": "celsius"},
}

SCHEMAS: dict[str, dict[str, Any]] = {
    "sentinel": {
        "type": "object",
        "required": ["answer"],
        "properties": {"answer": {"type": "string"}},
        "additionalProperties": False,
    },
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
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert an amount between currencies",
            "parameters": {
                "type": "object",
                "required": ["amount", "from", "to"],
                "properties": {
                    "amount": {"type": "number"},
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Search personal notes",
            "parameters": {
                "type": "object",
                "required": ["query", "limit"],
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
]

CASES: dict[str, list[dict[str, Any]]] = {
    # Rounds are generated from --limit/--clients; the key only has to exist so
    # argparse can offer the suite name.
    "concurrency": [],
    "needle_retrieval": [],
    "needle_distractor": [],
    "needle_archived_conflict": [],
    "needle_unlabeled_conflict": [],
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
        # Cases 11-30 extend the suite; the first ten above stay byte-identical
        # so earlier runs remain comparable on the same prompts.
        {"prompt": "Extract: Marie Curie, 66, Paris.", "schema": "person"},
        {"prompt": "Extract: Nikola Tesla, 86, Belgrade.", "schema": "person"},
        {"prompt": "Extract: Emmy Noether, 53, Erlangen.", "schema": "person"},
        {"prompt": "Extract: Claude Shannon, 84, Petoskey.", "schema": "person"},
        {"prompt": "Extract: Barbara Liskov, 86, Los Angeles.", "schema": "person"},
        {"prompt": "Extract: Tim Berners-Lee, 69, Geneva.", "schema": "person"},
        {"prompt": "Extract: Radia Perlman, 74, Portsmouth.", "schema": "person"},
        {"prompt": "Extract: Donald Knuth, 87, Milwaukee.", "schema": "person"},
        {"prompt": "Weather in Reykjavik, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Singapore, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Chicago, use fahrenheit.", "schema": "weather"},
        {"prompt": "Weather in Sydney, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Cairo, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Toronto, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Phoenix, use fahrenheit.", "schema": "weather"},
        {"prompt": "Weather in Buenos Aires, use celsius.", "schema": "weather"},
        {"prompt": "Extract: Hedy Lamarr, 85, Vienna.", "schema": "person"},
        {"prompt": "Extract: John von Neumann, 53, Budapest.", "schema": "person"},
        {"prompt": "Weather in Nairobi, use celsius.", "schema": "weather"},
        {"prompt": "Weather in Seattle, use fahrenheit.", "schema": "weather"},
    ],

    # Mechanism check: a field the model would never invent on its own. If
    # constrained decoding is active, every response must contain it.
    "mechanism": [
        {"prompt": "Repeat exactly the word HELLO. Do not output JSON.", "schema": "sentinel"},
        {"prompt": "Repeat exactly the word WORLD. Do not output JSON.", "schema": "sentinel"},
        {"prompt": "Reply with the number 7 only.", "schema": "sentinel"},
    ],
    "tool_call": [
        {"prompt": "What is the weather in Lisbon in celsius?", "tool": "get_weather",
         "expect": {"city": "Lisbon", "unit": "celsius"}},
        {"prompt": "What is the weather in Oslo in celsius?", "tool": "get_weather",
         "expect": {"city": "Oslo", "unit": "celsius"}},
        {"prompt": "What is the weather in Miami in fahrenheit?", "tool": "get_weather",
         "expect": {"city": "Miami", "unit": "fahrenheit"}},
        {"prompt": "What is the weather in Tokyo in celsius?", "tool": "get_weather",
         "expect": {"city": "Tokyo", "unit": "celsius"}},
        {"prompt": "What is the weather in Lima in celsius?", "tool": "get_weather",
         "expect": {"city": "Lima", "unit": "celsius"}},
        {"prompt": "What is the weather in Reykjavik in celsius?", "tool": "get_weather",
         "expect": {"city": "Reykjavik", "unit": "celsius"}},
        {"prompt": "Convert 25 USD to EUR.", "tool": "convert_currency",
         "expect": {"amount": 25, "from": "USD", "to": "EUR"}},
        {"prompt": "Convert 100 USD to BRL.", "tool": "convert_currency",
         "expect": {"amount": 100, "from": "USD", "to": "BRL"}},
        {"prompt": "Convert 7.5 GBP to USD.", "tool": "convert_currency",
         "expect": {"amount": 7.5, "from": "GBP", "to": "USD"}},
        {"prompt": "Convert 250 JPY to EUR.", "tool": "convert_currency",
         "expect": {"amount": 250, "from": "JPY", "to": "EUR"}},
        {"prompt": "Convert 1000 CAD to USD.", "tool": "convert_currency",
         "expect": {"amount": 1000, "from": "CAD", "to": "USD"}},
        {"prompt": "Convert 42 CHF to EUR.", "tool": "convert_currency",
         "expect": {"amount": 42, "from": "CHF", "to": "EUR"}},
        {"prompt": "Find up to 3 notes about backups.", "tool": "search_notes",
         "expect": {"query": "backups", "limit": 3}},
        {"prompt": "Find up to 5 notes about kubernetes.", "tool": "search_notes",
         "expect": {"query": "kubernetes", "limit": 5}},
        {"prompt": "Search my notes for proxmox, at most 10 results.", "tool": "search_notes",
         "expect": {"query": "proxmox", "limit": 10}},
        {"prompt": "Find 2 notes mentioning ansible.", "tool": "search_notes",
         "expect": {"query": "ansible", "limit": 2}},
        {"prompt": "Search notes about postgres with limit 4.", "tool": "search_notes",
         "expect": {"query": "postgres", "limit": 4}},
        {"prompt": "Find up to 1 note about grafana.", "tool": "search_notes",
         "expect": {"query": "grafana", "limit": 1}},
    ],
}


def _needle_retrieval_cases() -> list[dict[str, Any]]:
    """Build paired prompts with one exact fact moved through identical filler."""
    cases = []
    for case_id, value in NEEDLE_CASES:
        for depth in NEEDLE_DEPTHS:
            rows = [FILLER] * NEEDLE_FILLERS
            rows[round((NEEDLE_FILLERS - 1) * depth / 100)] = (
                f"Record {case_id}: the exact field code is {value}. "
            )
            prompt = (
                "Find the exact field code in the requested record. Use only the "
                "context below; answer with the code and nothing else.\n\n"
                "Context:\n" + "".join(rows) +
                f"\nWhat is the code in record {case_id}?"
            )
            cases.append({"case_id": case_id, "depth_pct": depth,
                          "needle_value": value, "prompt": prompt})
    return cases


def _needle_distractor_pair(case_id: str, value: str) -> dict[str, Any]:
    """Keep the existing 50%-depth filler prompt and replace eight filler rows with decoys."""
    baseline = next(c["prompt"] for c in _needle_retrieval_cases()
                    if c["case_id"] == case_id and c["depth_pct"] == 50)
    rows = [FILLER] * NEEDLE_FILLERS
    target_index = round((NEEDLE_FILLERS - 1) * 50 / 100)
    rows[target_index] = f"Record {case_id}: the exact field code is {value}. "
    for index, (decoy_id, decoy_value) in zip(NEEDLE_DISTRACTOR_ROWS, NEEDLE_DECOYS):
        rows[index] = f"Record {decoy_id}: exact field code is {decoy_value}. "
    distractor = (
        "Find the exact field code in the requested record. Use only the "
        "context below; answer with the code and nothing else.\n\n"
        "Context:\n" + "".join(rows) +
        f"\nWhat is the code in record {case_id}?"
    )
    return {"case_id": case_id, "needle_value": value, "depth_pct": 50,
            "baseline_prompt": baseline, "distractor_prompt": distractor}


def _needle_archived_conflict_pair(case_id: str, value: str) -> dict[str, Any]:
    """Contrast one active record with later-positioned archived values for that same ID."""
    target_index = round((NEEDLE_FILLERS - 1) * 50 / 100)
    active = f"Record {case_id}: ACTIVE revision 2025; current field code is {value}. "
    rows = [FILLER] * NEEDLE_FILLERS
    rows[target_index] = active
    baseline = (
        "Find the current field code for the requested record. Use only the "
        "context below; answer with the code and nothing else.\n\n"
        "Context:\n" + "".join(rows) +
        f"\nWhat is the active field code in record {case_id}?"
    )
    archived_rows = rows.copy()
    for index, (revision, (_, old_code)) in zip(
        NEEDLE_DISTRACTOR_ROWS, zip(NEEDLE_ARCHIVE_REVISIONS, NEEDLE_DECOYS)
    ):
        archived_rows[index] = (
            f"Record {case_id}: ARCHIVED revision {revision}; superseded field code was "
            f"{old_code}. "
        )
    archived = (
        "Find the current field code for the requested record. Use only the "
        "context below; answer with the code and nothing else.\n\n"
        "Context:\n" + "".join(archived_rows) +
        f"\nWhat is the active field code in record {case_id}?"
    )
    return {"case_id": case_id, "needle_value": value, "depth_pct": 50,
            "baseline_prompt": baseline, "distractor_prompt": archived}


def _needle_unlabeled_conflict_pair(case_id: str, value: str) -> dict[str, Any]:
    """Same-ID conflicting codes with no status labels, so only position separates them."""
    baseline = next(c["prompt"] for c in _needle_retrieval_cases()
                    if c["case_id"] == case_id and c["depth_pct"] == 50)
    rows = [FILLER] * NEEDLE_FILLERS
    rows[round((NEEDLE_FILLERS - 1) * 50 / 100)] = (
        f"Record {case_id}: the exact field code is {value}. "
    )
    for index, (_, other) in zip(NEEDLE_DISTRACTOR_ROWS, NEEDLE_DECOYS):
        rows[index] = f"Record {case_id}: the exact field code is {other}. "
    conflict = (
        "Find the exact field code in the requested record. Use only the "
        "context below; answer with the code and nothing else.\n\n"
        "Context:\n" + "".join(rows) +
        f"\nWhat is the code in record {case_id}?"
    )
    return {"case_id": case_id, "needle_value": value, "depth_pct": 50,
            "baseline_prompt": baseline, "distractor_prompt": conflict}


PAIRED_NEEDLE_SUITES = {
    "needle_distractor": (_needle_distractor_pair, "distractor"),
    "needle_archived_conflict": (_needle_archived_conflict_pair, "archived_conflict"),
    "needle_unlabeled_conflict": (_needle_unlabeled_conflict_pair, "unlabeled_conflict"),
}


def _count_input_tokens(
    base_url: str, payload: dict[str, Any], timeout: int
) -> tuple[int, dict[str, Any]]:
    response = _post_endpoint(
        f"{base_url.rstrip('/')}/v1/chat/completions/input_tokens", payload, timeout
    )
    count = response.get("input_tokens")
    if type(count) is not int or count < 0:
        raise ValueError(f"input_tokens endpoint returned invalid count: {response!r}")
    return count, response


def _pad_prompt_to_tokens(
    base_url: str, payload: dict[str, Any], target_tokens: int, timeout: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Pad before the query until llama.cpp reports an exact rendered-token match."""
    prompt = payload["messages"][0]["content"]
    query_start = prompt.rfind("\nWhat is ")
    if query_start < 0:
        raise ValueError("needle prompt is missing its final query")
    context, query = prompt[:query_start], prompt[query_start:]
    base_count, _ = _count_input_tokens(base_url, payload, timeout)
    if base_count > target_tokens:
        raise ValueError(f"distractor prompt has {base_count} tokens, over target {target_tokens}")
    if base_count == target_tokens:
        count, response = _count_input_tokens(base_url, payload, timeout)
        return {"prompt": prompt, "count": count, "padding": "", "response": response}, payload

    deficit = target_tokens - base_count
    for token in NEEDLE_PAD_TOKENS:
        unit = f" {token}"
        low, high = 0, deficit + 8
        candidate_payload = {**payload, "messages": [{"role": "user", "content": context + unit * high + query}]}
        high_count, _ = _count_input_tokens(base_url, candidate_payload, timeout)
        if high_count < target_tokens:
            continue
        while low < high:
            mid = (low + high) // 2
            candidate_payload = {**payload, "messages": [{"role": "user", "content": context + unit * mid + query}]}
            count, _ = _count_input_tokens(base_url, candidate_payload, timeout)
            if count < target_tokens:
                low = mid + 1
            else:
                high = mid
        for repetitions in range(max(0, low - 3), min(deficit + 8, low + 3) + 1):
            candidate = context + unit * repetitions + query
            candidate_payload = {**payload, "messages": [{"role": "user", "content": candidate}]}
            count, response = _count_input_tokens(base_url, candidate_payload, timeout)
            if count == target_tokens:
                return {"prompt": candidate, "count": count,
                        "padding": unit * repetitions, "response": response}, candidate_payload
    raise ValueError(f"could not exactly pad distractor prompt to {target_tokens} tokens")

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


def _vram_used_mib() -> float | None:
    try:
        import torch
        free, total = torch.cuda.mem_get_info()
        return round((total - free) / 1024**2, 1)
    except Exception:
        return None


class _VramSampler(threading.Thread):
    """1 Hz GPU-memory sampler; no-op when no accelerator is visible."""

    def __init__(self, path: Path):
        super().__init__(daemon=True)
        self.path = Path(path)
        self.stop_event = threading.Event()

    def run(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            handle.write("utc,vram_used_mib\n")
            while not self.stop_event.is_set():
                value = _vram_used_mib()
                if value is not None:
                    handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())},{value}\n")
                    handle.flush()
                self.stop_event.wait(1.0)

    def stop(self) -> None:
        self.stop_event.set()
        self.join(timeout=5)


def classify_failure(errors: list[str], content: str | None) -> str:
    """Bucket a failed structured-output case; keeps empty distinct from echo."""
    text = (content or "").strip()
    if not text:
        return "empty"
    # A truncated schema echo is still an echo, even when json.loads fails.
    if '"type": "object"' in text and '"required"' in text and '"properties"' in text:
        return "schema-echo"
    if any("invalid JSON" in e for e in errors):
        return "invalid-json"
    if errors:
        return "schema"
    return "none"


def _extract_call(message: dict[str, Any], fmt: str) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """Return (tool name, arguments, error) from either response shape."""
    if fmt == "json":
        content = (message.get("content") or "").strip()
        if not content:
            return None, None, "empty content"
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            return None, None, f"invalid JSON: {exc}"
        name = data.get("tool") or data.get("name")
        args = data.get("arguments") or data.get("args")
        if not isinstance(args, dict):
            return name, None, "arguments missing or not an object"
        return name, args, None
    calls = message.get("tool_calls") or []
    if not calls:
        return None, None, "no tool_calls in response"
    fn = calls[0].get("function") or {}
    raw = fn.get("arguments")
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return fn.get("name"), None, "tool arguments are not JSON"
    return fn.get("name"), args if isinstance(args, dict) else None, None


def _semantic_ok(case: dict[str, Any], args: dict[str, Any]) -> bool:
    expect = case.get("expect") or {}
    tool = case["tool"]
    if tool == "get_weather":
        return (str(args.get("city", "")).strip().lower() == str(expect["city"]).lower()
                and args.get("unit") == expect["unit"])
    if tool == "convert_currency":
        try:
            amount = float(args.get("amount"))
        except (TypeError, ValueError):
            return False
        return (abs(amount - float(expect["amount"])) < 1e-6
                and str(args.get("from", "")).upper() == expect["from"]
                and str(args.get("to", "")).upper() == expect["to"])
    if tool == "search_notes":
        try:
            limit = int(args.get("limit"))
        except (TypeError, ValueError):
            return False
        return (expect["query"].lower() in str(args.get("query", "")).lower()
                and limit == expect["limit"])
    return False


def score_tool_case(case: dict[str, Any], name: str | None, args: dict[str, Any] | None,
                    error: str | None) -> dict[str, Any]:
    errors = [error] if error else []
    selection = name == case["tool"]
    if name is not None and not selection:
        errors.append(f"wrong tool: {name!r}")
    schema_ok = False
    if args is not None:
        spec = next(t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == case["tool"])
        schema_errors = validate(args, spec)
        schema_ok = not schema_errors
        errors.extend(schema_errors)
    semantic = bool(args is not None and schema_ok and _semantic_ok(case, args))
    if args is not None and schema_ok and not semantic:
        errors.append("arguments do not match the request")
    return {"valid": bool(selection and schema_ok and semantic), "selection": selection,
            "schema_ok": schema_ok, "semantic": semantic, "errors": errors}


def _post(base_url: str, model: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    return _post_endpoint(f"{base_url.rstrip('/')}/v1/chat/completions", payload, timeout)


def _post_endpoint(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
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
    vram_csv: str | None = None,
    context_fill: int = 0,
    instruction: str = "schema",
    constrain: bool = False,
    constraint_format: str = "json_schema",
    tool_format: str = "native",
    max_gen_toks: int = 256,
    needle_depth: int | None = None,
    needle_batch: int | None = None,
) -> dict[str, Any]:
    if max_gen_toks <= 0:
        raise ValueError("max_gen_toks must be positive")
    if constraint_format not in ("json_schema", "json_object"):
        raise ValueError("constraint_format must be json_schema or json_object")
    paired_needle_suite = suite in PAIRED_NEEDLE_SUITES
    challenge_condition = (PAIRED_NEEDLE_SUITES[suite][1] if paired_needle_suite
                           else "distractor")
    if suite == "concurrency":
        cases = [{"round": i} for i in range(max(1, limit))]
        clients = max(1, int(clients))
    elif suite == "needle_retrieval":
        cases = [case for case in _needle_retrieval_cases()
                 if needle_depth is None or case["depth_pct"] == needle_depth][:limit]
    elif paired_needle_suite:
        if needle_batch not in (0, 1):
            raise ValueError(f"{suite} requires needle_batch 0 or 1")
        if limit <= 0:
            raise ValueError(f"{suite} requires a positive limit")
        make_pair = PAIRED_NEEDLE_SUITES[suite][0]
        pairs = [make_pair(case_id, value) for case_id, value in NEEDLE_CASES]
        random.Random(seed).shuffle(pairs)
        start = needle_batch * NEEDLE_BATCH_SIZE
        cases = pairs[start:start + min(limit, NEEDLE_BATCH_SIZE)]
    else:
        cases = CASES[suite][:limit]
    random.Random(seed).shuffle(cases)
    prepared_pairs = []
    if paired_needle_suite:
        for pair in cases:
            baseline_payload = {
                "model": model,
                "messages": [{"role": "user", "content": pair["baseline_prompt"]}],
                "max_tokens": max_gen_toks,
                "temperature": 0,
            }
            challenge_payload = {
                "model": model,
                "messages": [{"role": "user", "content": pair["distractor_prompt"]}],
                "max_tokens": max_gen_toks,
                "temperature": 0,
            }
            baseline_tokens, baseline_count_response = _count_input_tokens(
                base_url, baseline_payload, timeout
            )
            challenge_tokens, challenge_count_response = _count_input_tokens(
                base_url, challenge_payload, timeout
            )
            # Either arm can be the shorter one; pad the short arm to the common count.
            target_tokens = max(baseline_tokens, challenge_tokens)
            if baseline_tokens == target_tokens:
                baseline_final, baseline_padding = baseline_payload, ""
                baseline_final_response = baseline_count_response
            else:
                baseline_pad, baseline_final = _pad_prompt_to_tokens(
                    base_url, baseline_payload, target_tokens, timeout)
                baseline_padding = baseline_pad["padding"]
                baseline_final_response = baseline_pad["response"]
            if challenge_tokens == target_tokens:
                challenge_final, challenge_padding = challenge_payload, ""
                challenge_final_response = challenge_count_response
            else:
                challenge_pad, challenge_final = _pad_prompt_to_tokens(
                    base_url, challenge_payload, target_tokens, timeout)
                challenge_padding = challenge_pad["padding"]
                challenge_final_response = challenge_pad["response"]
            prepared_pairs.append({
                **pair,
                "baseline_tokens": target_tokens,
                f"{challenge_condition}_tokens_before_padding": challenge_tokens,
                f"{challenge_condition}_tokens": target_tokens,
                "padding": challenge_padding,
                "baseline_padding": baseline_padding,
                "baseline_payload": baseline_final,
                f"{challenge_condition}_payload": challenge_final,
                "count_provenance": {
                    "baseline": {"request": baseline_payload, "response": baseline_count_response},
                    "baseline_after_padding": {
                        "request": baseline_final, "response": baseline_final_response},
                    f"{challenge_condition}_before_padding": {
                        "request": challenge_payload, "response": challenge_count_response},
                    f"{challenge_condition}_after_padding": {
                        "request": challenge_final, "response": challenge_final_response},
                },
            })
    sampler = _VramSampler(Path(vram_csv)) if vram_csv else None
    if sampler:
        sampler.start()
    details: list[dict[str, Any]] = []
    latencies_ms: list[float] = []
    round_ms: list[float] = []
    pad = FILLER * max(0, int(context_fill) // 20)
    if paired_needle_suite:
        for pair_index, pair in enumerate(prepared_pairs):
            conditions = (("baseline", challenge_condition) if pair_index % 2 == 0
                          else (challenge_condition, "baseline"))
            for condition in conditions:
                payload = pair[f"{condition}_payload"]
                started = time.perf_counter()
                response = _post(base_url, model, payload, timeout)
                latency_ms = (time.perf_counter() - started) * 1000
                latencies_ms.append(latency_ms)
                content = _extract_content(response)
                scored = LongContextEvaluator().evaluate(
                    {"needle_key": pair["case_id"], "needle_value": pair["needle_value"],
                     "context_len": pair["baseline_tokens"], "depth_pct": pair["depth_pct"]}, content)
                usage_tokens = (response.get("usage") or {}).get("prompt_tokens")
                details.append({
                    "case_id": pair["case_id"], "condition": condition,
                    "depth_pct": pair["depth_pct"], "needle_value": pair["needle_value"],
                    "prompt": payload["messages"][0]["content"], "content": content,
                    **scored, "valid": bool(scored["exact_match"]),
                    "matched_input_tokens": pair["baseline_tokens"],
                    "condition_input_tokens": pair[f"{condition}_tokens"],
                    "usage_prompt_tokens": usage_tokens,
                    "usage_matches_input_tokens": usage_tokens == pair["baseline_tokens"],
                    "baseline_input_tokens": pair["baseline_tokens"],
                    f"{challenge_condition}_input_tokens_before_padding":
                        pair[f"{challenge_condition}_tokens_before_padding"],
                    "padding": pair["padding"], "baseline_padding": pair["baseline_padding"],
                    "count_provenance": pair["count_provenance"],
                    "latency_ms": round(latency_ms, 1), "request": payload, "response": response,
                })
        cases = []
    for case in cases:
        if pad and suite in ("structured_output", "tool_call"):
            case = {**case, "prompt": pad + "\n" + case["prompt"]}
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
        if suite in ("structured_output", "mechanism"):
            schema = SCHEMAS[case["schema"]]
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                    case["prompt"]  # mechanism: schema is sent only via response_format
                    if suite == "mechanism"
                    else f"{case['prompt']} Reply with one JSON object like this example: "
                    f"{json.dumps(EXAMPLES[case['schema']])} Return it and nothing else."
                    if instruction == "example"
                    else f"{case['prompt']} Reply with JSON only, matching this schema: "
                    f"{json.dumps(schema)}"
                    + (" Return exactly one JSON object and nothing else; do not repeat the schema."
                       if instruction == "strict" else "")
                ),
                    }
                ],
                "max_tokens": max_gen_toks,
                "temperature": 0,
            }
            started = time.perf_counter()
            if constrain:
                payload["response_format"] = ({
                    "type": "json_schema",
                    "json_schema": {"name": case["schema"], "schema": schema, "strict": True},
                } if constraint_format == "json_schema" else {"type": "json_object"})
            response = _post(base_url, model, payload, timeout)
            content = _extract_content(response)
            latencies_ms.append((time.perf_counter() - started) * 1000)
            try:
                parsed = json.loads(content)
                errors = validate(parsed, schema)
            except json.JSONDecodeError as exc:
                parsed, errors = None, [f"invalid JSON: {exc}"]
            details.append({"prompt": case["prompt"], "valid": not errors, "errors": errors,
                            "content": content, "request": payload, "response": response,
                            "failure": None if not errors else classify_failure(errors, content)})
        elif suite == "tool_call":
            started = time.perf_counter()
            if tool_format == "json":
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content":
                        case["prompt"] + " Choose exactly one tool from [get_weather, "
                        "convert_currency, search_notes] and reply with JSON "
                        '{"tool": "<name>", "arguments": {...}} and nothing else.'}],
                    "max_tokens": max_gen_toks,
                    "temperature": 0,
                    "response_format": {"type": "json_schema", "json_schema": {
                        "name": "tool_call", "strict": True, "schema": {
                            "type": "object", "required": ["tool", "arguments"],
                            "properties": {"tool": {"type": "string",
                                                    "enum": [t["function"]["name"] for t in TOOLS]},
                                           "arguments": {"type": "object", "properties": {
                                               "city": {"type": "string"}, "unit": {"type": "string",
                                                   "enum": ["celsius", "fahrenheit"]},
                                               "amount": {"type": "number"}, "from": {"type": "string"},
                                               "to": {"type": "string"}, "query": {"type": "string"},
                                               "limit": {"type": "integer"}}}},
                            "additionalProperties": False}}},
                }
            else:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": case["prompt"]}],
                    "tools": TOOLS,
                    "max_tokens": max_gen_toks,
                    "temperature": 0,
                }
            message = _post(base_url, model, payload, timeout)["choices"][0]["message"]
            latencies_ms.append((time.perf_counter() - started) * 1000)
            name, args, error = _extract_call(message, tool_format)
            score = score_tool_case(case, name, args, error)
            details.append({"prompt": case["prompt"], "tool": name, "args": args,
                            "content": (message.get("content") or "")[:300], **score})
        else:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": case["prompt"]}],
                "max_tokens": max_gen_toks,
                "temperature": 0,
            }
            started = time.perf_counter()
            response = _post(base_url, model, payload, timeout)
            latency_ms = (time.perf_counter() - started) * 1000
            latencies_ms.append(latency_ms)
            content = _extract_content(response)
            scored = LongContextEvaluator().evaluate(
                {"needle_key": case["case_id"], "needle_value": case["needle_value"],
                 "context_len": response.get("usage", {}).get("prompt_tokens"),
                 "depth_pct": case["depth_pct"]}, content)
            details.append({**case, **scored, "valid": scored["passed"],
                            "content": content, "latency_ms": round(latency_ms, 1),
                            "request": payload, "response": response})
    if sampler:
        sampler.stop()
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
                **({"tool_selection_rate": round(sum(1 for d in details if d.get("selection")) / len(details), 3),
                    "args_schema_rate": round(sum(1 for d in details if d.get("schema_ok")) / len(details), 3),
                    "semantic_rate": round(sum(1 for d in details if d.get("semantic")) / len(details), 3)}
                   if details and suite == "tool_call" else {}),
                 **({"retrieval_by_depth": {
                    str(depth): round(sum(1 for d in details if d["depth_pct"] == depth and d["valid"])
                                      / sum(1 for d in details if d["depth_pct"] == depth), 3)
                    for depth in NEEDLE_DEPTHS
                    if any(d["depth_pct"] == depth for d in details)}}
                   if details and suite == "needle_retrieval" else {}),
                **({
                     "exact_retrieval_by_condition": {
                         condition: round(sum(1 for d in details if d["condition"] == condition
                                               and d["exact_match"])
                                           / max(1, sum(1 for d in details if d["condition"] == condition)), 3)
                         for condition in ("baseline", challenge_condition)
                     },
                     "empty_by_condition": {
                         condition: sum(1 for d in details if d["condition"] == condition
                                        and not (d["content"] or "").strip())
                         for condition in ("baseline", challenge_condition)
                    },
                    "usage_mismatch_count": sum(1 for d in details if not d["usage_matches_input_tokens"]),
                 } if details and paired_needle_suite else {}),
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
    run.add_argument("--max-gen-toks", type=int, default=256)
    run.add_argument("--needle-depth", type=int, choices=NEEDLE_DEPTHS)
    run.add_argument("--needle-batch", type=int, choices=(0, 1))
    run.add_argument("--timeout", type=int, default=600)
    run.add_argument("--vram-csv", default=None)
    run.add_argument("--context-fill", type=int, default=0)
    run.add_argument("--instruction", choices=("schema", "strict", "example"), default="schema")
    run.add_argument("--tool-format", choices=("native", "json"), default="native")
    run.add_argument("--constrain", action="store_true",
                     help="send response_format json_schema (constrained decoding)")
    run.add_argument("--constraint-format", choices=("json_schema", "json_object"), default="json_schema")
    run.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = run_suite(args.base_url, args.model, args.suite, limit=args.limit,
                        seed=args.seed, clients=args.clients, vram_csv=args.vram_csv,
                        context_fill=args.context_fill, instruction=args.instruction,
                        constrain=args.constrain, constraint_format=args.constraint_format,
                        tool_format=args.tool_format,
                        max_gen_toks=args.max_gen_toks, timeout=args.timeout,
                        needle_depth=args.needle_depth, needle_batch=args.needle_batch)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
