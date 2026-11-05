#!/usr/bin/env bash
# Entry point for `gpu-lab job` inside the gpu-lab sandbox container.
#
# Installs nothing globally: llama.cpp and lm-eval live under $WORKSPACE so the
# run is reproducible and the read-only image and /cache (noexec) stay untouched.
# Everything is idempotent, so a re-run resumes instead of re-downloading.
set -euo pipefail

GPU_LAB_TASK="${GPU_LAB_TASK:-campaign}"
case "$GPU_LAB_TASK" in
  campaign) ;;
  gsm8k-paired) ;;
  sweep) ;;
  *) echo "unsupported GPU_LAB_TASK: $GPU_LAB_TASK" >&2; exit 2 ;;
esac

WORKSPACE="${WORKSPACE:-/workspace}"
if [ "$GPU_LAB_TASK" = "gsm8k-paired" ]; then
  REPO="$WORKSPACE/repo"
  SPEC="$REPO/configs/campaigns/smoke-qwen3-1.7b.yaml"
  MODELS_DIR=/models
  LLAMA_RELEASE=b12024
  LM_EVAL_REF=d6de81643928d653435c431bae19945d41d32520
else
  REPO="${REPO:-$WORKSPACE/repo}"
  SPEC="${SPEC:-$REPO/configs/campaigns/smoke-qwen3-1.7b.yaml}"
  MODELS_DIR="${MODELS_DIR:-/models}"
  LLAMA_RELEASE="${LLAMA_RELEASE:-b12024}"
fi
TOOLS="$WORKSPACE/tools"
VENV="$WORKSPACE/venv"
RESULTS="$WORKSPACE/results/campaigns"

log() { echo "[$(date -u +%H:%M:%S)] $*"; }

# CUDA runtime libraries shipped inside the image's torch wheels.
NVIDIA_LIBS=""
for lib in /usr/local/lib/python3.11/site-packages/nvidia/*/lib; do
  [ -d "$lib" ] || continue
  export LD_LIBRARY_PATH="$lib:${LD_LIBRARY_PATH:-}"
  NVIDIA_LIBS="${NVIDIA_LIBS:+$NVIDIA_LIBS:}$lib"
done

GLIBC="$WORKSPACE/glibc"
BIN="$TOOLS/bin"

mkdir -p "$WORKSPACE/.tmp"
log "python $(python3 --version 2>&1)"

fetch_url() {
  # The image has no curl/wget; python is the only downloader available.
  python3 - "$1" "$2" <<'PY'
import sys, urllib.request
urllib.request.urlretrieve(sys.argv[1], sys.argv[2])
PY
}

# Current llama.cpp Linux releases are built against glibc >= 2.38, the image
# ships 2.36. The container host's newer loader/libs are mounted via /workspace
# and drive the binaries instead (see bootstrap-glibc.sh).
ensure_glibc() {
  [ -x "$GLIBC/ld-linux-x86-64.so.2" ] && return 0
  echo "missing $GLIBC: llama.cpp $LLAMA_RELEASE needs glibc >= 2.38, image has 2.36." >&2
  echo "run tools/homelab/bootstrap-glibc.sh on the container host first" >&2
  return 1
}

install_wrappers() {
  local bin="$1" lp tool
  # ggml_backend_load_all() looks for libggml-*.so next to /proc/self/exe, so the
  # loader has to be copied into the binary dir, not merely invoked from /workspace.
  cp -f "$GLIBC/ld-linux-x86-64.so.2" "$bin/ld-linux-x86-64.so.2"
  lp="$GLIBC:$bin:$NVIDIA_LIBS:/usr/local/lib:/usr/lib/x86_64-linux-gnu"
  mkdir -p "$BIN"
  for tool in llama-server llama-bench; do
    printf '#!/bin/sh\nexec "%s/ld-linux-x86-64.so.2" --library-path "%s" "%s/%s" "$@"\n' \
      "$bin" "$lp" "$bin" "$tool" > "$BIN/$tool"
    chmod +x "$BIN/$tool"
  done
}

dir_for() { echo "$TOOLS/llama-${LLAMA_RELEASE}-$1"; }

llama_bin_dir() {
  # Tarball layout moved between releases (build/bin vs llama-<tag>/), so search.
  local server
  server="$(find "$(dir_for "$1")" -maxdepth 3 -name llama-server -type f -print -quit 2>/dev/null || true)"
  [ -n "$server" ] && dirname "$server"
}

fetch_llama() {
  local variant="$1" url
  case "$variant" in
    cuda) url="https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_RELEASE}/llama-${LLAMA_RELEASE}-bin-ubuntu-cuda-12.8-x64.tar.gz" ;;
    *) echo "unknown variant $variant" >&2; return 1 ;;
  esac
  [ -n "$(llama_bin_dir "$variant")" ] && return 0
  mkdir -p "$(dir_for "$variant")"
  log "downloading llama.cpp $variant build ($LLAMA_RELEASE)"
  fetch_url "$url" "$TOOLS/$variant.tar.gz"
  tar -xzf "$TOOLS/$variant.tar.gz" -C "$(dir_for "$variant")"
  rm -f "$TOOLS/$variant.tar.gz"
}

ensure_glibc
fetch_llama cuda
LLAMA_BIN="$(llama_bin_dir cuda)"
[ -n "$LLAMA_BIN" ] || { echo "llama-server not found in the $LLAMA_RELEASE tarball" >&2; exit 1; }
install_wrappers "$LLAMA_BIN"
export PATH="$BIN:$PATH"
llama-server --version
DEVICES="$(llama-server --list-devices 2>&1 || true)"
case "$DEVICES" in
  *CUDA*) log "llama.cpp devices: $(echo "$DEVICES" | tr '\n' ' ')" ;;
  *) echo "no CUDA device visible to llama.cpp: $DEVICES" >&2; exit 1 ;;
esac

# lm-eval sees the image's torch/transformers/datasets as satisfied because the
# venv inherits system site-packages; only the harness and its small deps install.
# Pin a harness commit: 0.4.13's gguf backend still expects the legacy
# `token_logprobs` payload, which llama.cpp releases since 2025 no longer send.
LM_EVAL_REF="${LM_EVAL_REF:-d6de81643928d653435c431bae19945d41d32520}"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv --system-site-packages "$VENV"
fi
if [ "$(cat "$VENV/.lm-eval-ref" 2>/dev/null || true)" != "$LM_EVAL_REF" ]; then
  log "installing lm-eval @ $LM_EVAL_REF"
  fetch_url "https://codeload.github.com/EleutherAI/lm-evaluation-harness/tar.gz/$LM_EVAL_REF" \
    "$TOOLS/lm-eval.tar.gz"
  "$VENV/bin/python" -m pip install --quiet "$TOOLS/lm-eval.tar.gz"
  echo "$LM_EVAL_REF" > "$VENV/.lm-eval-ref"
fi
export PATH="$VENV/bin:$PATH"
"$VENV/bin/python" -m pip install --quiet "tenacity==9.1.2" "langdetect==1.0.9" "immutabledict==4.2.1"
"$VENV/bin/python" -c "import importlib.metadata as m; print('lm-eval', m.version('lm-eval'))"

SPEC_VALUES="$("$VENV/bin/python" - "$SPEC" <<'PY'
import sys
import yaml
model = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))["models"][0]
print(f"{model['hf_repo']}|{model['file']}|{model.get('hf_revision', 'main')}")
PY
)"
HF_REPO="${SPEC_VALUES%%|*}"
_rest="${SPEC_VALUES#*|}"
HF_FILE="${_rest%%|*}"
HF_REV="${_rest#*|}"

if [ ! -f "$MODELS_DIR/$HF_FILE" ]; then
  log "downloading $HF_REPO/$HF_FILE @ $HF_REV"
  mkdir -p "$MODELS_DIR"
  hf download "$HF_REPO" "$HF_FILE" --revision "$HF_REV" --local-dir "$MODELS_DIR"
fi

if [ "$GPU_LAB_TASK" = "gsm8k-paired" ]; then
  log "running fixed GSM8K zero-shot/five-shot diagnostic"
  exec bash "$REPO/tools/homelab/gsm8k-diagnostic.sh"
fi

if [ "$GPU_LAB_TASK" = "sweep" ]; then
  log "running context/KV sweep into ${SWEEP_OUT:-$WORKSPACE/results/sweeps/kv-ctx}"
  PYTHONPATH="$REPO/src" "$VENV/bin/python" -m llm_research_bench.sweep run \
    --base "${SWEEP_BASE:-$REPO/configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml}" \
    --grid "${SWEEP_GRID:-ctx=2048,4096,8192}" \
    --kv "${SWEEP_KV:-f16,q8_0}" \
    --out "${SWEEP_OUT:-$WORKSPACE/results/sweeps/kv-ctx}" \
    --models-dir "$MODELS_DIR"
  exit $?
fi

cd "$REPO"
set +e
PYTHONPATH="$REPO/src" "$VENV/bin/python" -m llm_research_bench.campaign run \
  --spec "$SPEC" \
  --out "$RESULTS" \
  --models-dir "$MODELS_DIR"
RUN_CODE=$?
set -e

PYTHONPATH="$REPO/src" "$VENV/bin/python" -m llm_research_bench.campaign summary --out "$RESULTS" || true
log "campaign finished with code $RUN_CODE"
exit "$RUN_CODE"
