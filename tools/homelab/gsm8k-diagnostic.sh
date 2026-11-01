#!/usr/bin/env bash
# One-item GSM8K diagnosis: compare raw llama-server responses with pinned lm-eval.
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
OUT="$WORKSPACE/results/diagnostics/pr9-gsm8k-$(date -u +%Y%m%dT%H%M%SZ)"
MODEL=/models/Qwen3-1.7B-Q4_K_M.gguf
PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
mkdir -p "$OUT"
test -x "$WORKSPACE/tools/bin/llama-server"
test -x "$WORKSPACE/venv/bin/python"
test -f "$MODEL"

"$WORKSPACE/tools/bin/llama-server" \
  -m "$MODEL" --host 127.0.0.1 --port "$PORT" --ctx-size 4096 \
  --n-gpu-layers 99 --threads 2 --alias qwen3-1.7b --parallel 1 \
  --jinja --chat-template-kwargs '{"enable_thinking":false}' \
  --no-webui >"$OUT/llama-server.log" 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

python3 - "$PORT" <<'PY'
import sys, time, urllib.error, urllib.request
url = f"http://127.0.0.1:{sys.argv[1]}/health"
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                break
    except (urllib.error.URLError, OSError):
        time.sleep(1)
else:
    raise SystemExit("llama-server health timeout")
PY

python3 - "$PORT" "$OUT" <<'PY'
import json, pathlib, sys, urllib.request
port, out = sys.argv[1], pathlib.Path(sys.argv[2])
prompt = ("Question: Janet’s ducks lay 16 eggs per day. She eats three for breakfast "
          "every morning and bakes muffins for her friends every day with four. "
          "She sells the remainder at the farmers' market daily for $2 per fresh "
          "duck egg. How much in dollars does she make every day at the farmers' "
          "market?\nAnswer:")
for cap in (256, 384):
    payload = {
        "model": "qwen3-1.7b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": cap,
        "temperature": 0,
        "seed": 42,
        "stop": ["Question:", "</s>", "<|im_end|>"],
    }
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = json.load(response)
    choice = raw.get("choices", [{}])[0]
    message = choice.get("message", {})
    reasoning = message.pop("reasoning_content", None)
    raw["choices"][0]["message"]["reasoning_content_present"] = reasoning is not None
    raw["choices"][0]["message"]["reasoning_content_chars"] = len(reasoning or "")
    (out / f"raw-{cap}.json").write_text(
        json.dumps({"request": payload, "response": raw}, indent=2), encoding="utf-8"
    )
    print(f"raw cap={cap} finish={choice.get('finish_reason')!r} "
          f"content={message.get('content')!r} "
          f"reasoning_content_present={reasoning is not None} "
          f"reasoning_content_chars={len(reasoning or '')} "
          f"usage={raw.get('usage')!r}")
PY

EVAL_OUT="$OUT/harness"
mkdir -p "$EVAL_OUT"
timeout 180s "$WORKSPACE/venv/bin/python" -m lm_eval \
  --model local-chat-completions --tasks gsm8k --limit 1 --seed 42 \
  --num_fewshot 0 --batch_size 1 --output_path "$EVAL_OUT" --log_samples \
  --model_args "model=qwen3-1.7b,base_url=http://127.0.0.1:$PORT/v1/chat/completions,max_gen_toks=384,eos_string=<|im_end|>" \
  --apply_chat_template >"$OUT/lm-eval.log" 2>&1

python3 - "$OUT" <<'PY'
import json, pathlib, sys
out = pathlib.Path(sys.argv[1])
samples = next((out / "harness").rglob("samples_gsm8k_*.jsonl"), None)
if samples is None:
    raise SystemExit("lm-eval GSM8K sample file missing")
sample = json.loads(samples.read_text(encoding="utf-8").splitlines()[0])
harness = sample.get("resps", [[""]])[0][0]
raw = json.loads((out / "raw-384.json").read_text(encoding="utf-8"))
choice = raw["response"].get("choices", [{}])[0]
message = choice.get("message", {})
direct = message.get("content")
report = {
    "harness_response": harness,
    "harness_filtered": sample.get("filtered_resps"),
    "raw_content": direct,
    "raw_reasoning_content_present": message.get("reasoning_content_present"),
    "raw_reasoning_content_chars": message.get("reasoning_content_chars"),
    "raw_finish_reason": choice.get("finish_reason"),
    "content_matches_harness": direct == harness,
}
(out / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
PY
