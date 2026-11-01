#!/usr/bin/env bash
# Isolated 20-item GSM8K diagnostic; never writes into the historical smoke campaign.
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
OUT="$WORKSPACE/results/diagnostics/pr9-gsm8k-n20-$(date -u +%Y%m%dT%H%M%SZ)"
MODEL=/models/Qwen3-1.7B-Q4_K_M.gguf
test -x "$WORKSPACE/tools/bin/llama-server"
test -x "$WORKSPACE/venv/bin/python"
test -f "$MODEL"
mkdir -p "$OUT"

python3 - "$WORKSPACE" "$OUT" "$MODEL" <<'PY'
import hashlib
import http.server
import json
import pathlib
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

workspace, out, model = map(pathlib.Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    server_port = sock.getsockname()[1]
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    proxy_port = sock.getsockname()[1]

base = f"http://127.0.0.1:{server_port}"
records = []
record_lock = threading.Lock()

class Proxy(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        request_bytes = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        request = json.loads(request_bytes)
        forward = urllib.request.Request(
            base + self.path, request_bytes,
            {"Content-Type": self.headers.get("Content-Type", "application/json")},
        )
        try:
            with urllib.request.urlopen(forward, timeout=240) as response:
                status, response_bytes = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, response_bytes = error.code, error.read()
        parsed = json.loads(response_bytes)
        saved = json.loads(json.dumps(parsed))
        choices = saved.get("choices", [])
        for choice in choices:
            message = choice.get("message", {})
            reasoning = message.pop("reasoning_content", None)
            message["reasoning_content_present"] = reasoning is not None
            message["reasoning_content_chars"] = len(reasoning or "")
        record = {"request": request, "status": status, "response": saved}
        with record_lock:
            records.append(record)
        body = response_bytes
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def get_json(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)

server_log = (out / "llama-server.log").open("wb")
proc = subprocess.Popen([
    str(workspace / "tools/bin/llama-server"), "-m", str(model),
    "--host", "127.0.0.1", "--port", str(server_port), "--ctx-size", "4096",
    "--n-gpu-layers", "99", "--threads", "2", "--alias", "qwen3-1.7b",
    "--parallel", "1", "--jinja", "--chat-template-kwargs",
    '{"enable_thinking":false}', "--no-webui",
], stdout=server_log, stderr=subprocess.STDOUT)
proxy = http.server.ThreadingHTTPServer(("127.0.0.1", proxy_port), Proxy)
proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
proxy_thread.start()

try:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited with {proc.returncode}")
        try:
            if get_json(base + "/health").get("status") == "ok":
                break
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(1)
    else:
        raise TimeoutError("llama-server health check timed out")

    props = get_json(base + "/props", timeout=10)
    template = props.get("chat_template")
    props["chat_template_observed"] = isinstance(template, str) and bool(template)
    props["chat_template_sha256"] = (
        hashlib.sha256(template.encode()).hexdigest()
        if props["chat_template_observed"] else None
    )
    (out / "server-props.json").write_text(json.dumps(props, indent=2), encoding="utf-8")
    model_hash = hashlib.sha256()
    with model.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(8 * 1024 * 1024), b""):
            model_hash.update(chunk)
    model_sha256 = model_hash.hexdigest()
    if model_sha256 != "d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5":
        raise RuntimeError(f"unexpected GGUF SHA-256: {model_sha256}")
    (out / "model.json").write_text(json.dumps({
        "path": str(model), "size_bytes": model.stat().st_size,
        "sha256": model_sha256,
    }, indent=2), encoding="utf-8")
    version = subprocess.run(
        [
            str(workspace / "venv/bin/python"), "-c",
            "import importlib.metadata as m; print('lm-eval', m.version('lm-eval'))",
        ], check=True, capture_output=True, text=True,
    ).stdout.strip()
    harness_ref_path = workspace / "venv/.lm-eval-ref"
    harness_ref = harness_ref_path.read_text(encoding="utf-8").strip() if harness_ref_path.exists() else None
    if harness_ref != "d6de81643928d653435c431bae19945d41d32520":
        raise RuntimeError(f"unexpected lm-eval source revision: {harness_ref!r}")
    eval_out = out / "harness"
    eval_out.mkdir()
    command = [
        str(workspace / "venv/bin/python"), "-m", "lm_eval",
        "--model", "local-chat-completions", "--tasks", "gsm8k",
        "--limit", "20", "--seed", "42", "--num_fewshot", "0",
        "--batch_size", "1", "--output_path", str(eval_out), "--log_samples",
        "--model_args",
        f"model=qwen3-1.7b,base_url=http://127.0.0.1:{proxy_port}/v1/chat/completions,max_gen_toks=384,eos_string=<|im_end|>",
        "--apply_chat_template",
    ]
    result = subprocess.run(command, stdout=(out / "lm-eval.log").open("wb"),
                            stderr=subprocess.STDOUT, timeout=900, check=False)
    if result.returncode:
        raise RuntimeError(f"lm-eval exited with {result.returncode}; inspect lm-eval.log")
finally:
    proxy.shutdown()
    proxy.server_close()
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    server_log.close()

(out / "api-captures.jsonl").write_text(
    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
    encoding="utf-8",
)
sample_files = list(eval_out.rglob("samples_gsm8k_*.jsonl"))
if len(sample_files) != 1:
    raise RuntimeError(f"expected one GSM8K sample file, found {len(sample_files)}")
samples = [json.loads(line) for line in sample_files[0].read_text(encoding="utf-8").splitlines()]
if len(records) != 20 or len(samples) != 40 or len({r["doc_id"] for r in samples}) != 20:
    raise RuntimeError(f"expected 20 requests/docs; captured {len(records)} requests and {len(samples)} sample rows")

def captured_for(question):
    matches = [r for r in records if any(
        m.get("role") == "user" and question in m.get("content", "")
        for m in r["request"].get("messages", [])
    )]
    if len(matches) != 1:
        raise RuntimeError(f"expected one captured request for doc question; found {len(matches)}")
    return matches[0]

per_doc = {}
for sample in samples:
    doc_id = sample["doc_id"]
    question = sample["doc"]["question"]
    capture = captured_for(question)
    choice = capture["response"].get("choices", [{}])[0]
    message = choice.get("message", {})
    harness_response = sample.get("resps", [[""]])[0][0]
    row = per_doc.setdefault(str(doc_id), {
        "doc_id": doc_id,
        "api_content": message.get("content"),
        "reasoning_content_present": message.get("reasoning_content_present", False),
        "reasoning_content_chars": message.get("reasoning_content_chars", 0),
        "finish_reason": choice.get("finish_reason"),
        "usage": capture["response"].get("usage"),
        "content_matches_harness": True,
        "formats": [],
    })
    row["content_matches_harness"] &= message.get("content") == harness_response
    row["formats"].append({
        "filter": sample.get("filter"),
        "harness_response": harness_response,
        "extracted": sample.get("filtered_resps"),
        "invalid": "[invalid]" in sample.get("filtered_resps", []),
        "has_gsm8k_marker": "####" in (message.get("content") or ""),
    })

filters = sorted({f["filter"] for doc in per_doc.values() for f in doc["formats"]})
if filters != ["flexible-extract", "strict-match"] or any(
    len(doc["formats"]) != 2 for doc in per_doc.values()
):
    raise RuntimeError(f"expected strict and flexible filter outputs for every doc; got {filters}")
filter_stats = {}
for name in filters:
    rows = [f for doc in per_doc.values() for f in doc["formats"] if f["filter"] == name]
    filter_stats[name] = {
        "n": len(rows), "invalid_n": sum(r["invalid"] for r in rows),
        "invalid_rate": sum(r["invalid"] for r in rows) / len(rows),
        "extracted_counts": {},
    }
    for row in rows:
        value = json.dumps(row["extracted"], ensure_ascii=False)
        filter_stats[name]["extracted_counts"][value] = filter_stats[name]["extracted_counts"].get(value, 0) + 1

report = {
    "n_examples": len(per_doc), "n_api_requests": len(records),
    "parameters": {
        "enable_thinking": False, "max_gen_toks": 384,
        "eos_string": "<|im_end|>", "num_fewshot": 0,
        "stop": ["Question:", "</s>", "<|im_end|>"],
        "limit": 20, "seed": 42, "batch_size": 1,
    },
    "lm_eval_version": version,
    "lm_eval_source_ref": harness_ref,
    "llama_cpp_version": props.get("build_info"),
    "llama_cpp_version_source": "server-props.build_info",
    "chat_template_observed": props["chat_template_observed"],
    "template_sha256": props["chat_template_sha256"],
    "finish_reason_counts": {},
    "reasoning_content_present_n": sum(d["reasoning_content_present"] for d in per_doc.values()),
    "content_matches_harness_n": sum(d["content_matches_harness"] for d in per_doc.values()),
    "gsm8k_marker_n": sum("####" in (d["api_content"] or "") for d in per_doc.values()),
    "filters": filter_stats,
    "items": list(per_doc.values()),
}
for item in per_doc.values():
    reason = item["finish_reason"] or "null"
    report["finish_reason_counts"][reason] = report["finish_reason_counts"].get(reason, 0) + 1
(out / "analysis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k != "items"}, ensure_ascii=False))
print(f"DIAGNOSTIC_OUTPUT={out}")
PY
