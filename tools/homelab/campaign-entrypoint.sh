#!/usr/bin/env bash
# Entry point for `gpu-lab job` inside the gpu-lab sandbox container.
#
# Installs nothing globally: llama.cpp and lm-eval live under $WORKSPACE so the
# run is reproducible and the read-only image and /cache (noexec) stay untouched.
# Everything is idempotent, so a re-run resumes instead of re-downloading.
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
REPO="${REPO:-$WORKSPACE/repo}"
SPEC="${SPEC:-$REPO/configs/campaigns/smoke-qwen3-1.7b.yaml}"
MODELS_DIR="${MODELS_DIR:-/models}"
LLAMA_RELEASE="${LLAMA_RELEASE:-b12024}"
TOOLS="$WORKSPACE/tools"
VENV="$WORKSPACE/venv"
RESULTS="$WORKSPACE/results/campaigns"

log() { echo "[$(date -u +%H:%M:%S)] $*"; }

# CUDA runtime libraries shipped inside the image's torch wheels.
for lib in /usr/local/lib/python3.11/site-packages/nvidia/*/lib; do
  [ -d "$lib" ] && export LD_LIBRARY_PATH="$lib:${LD_LIBRARY_PATH:-}"
done

mkdir -p "$WORKSPACE/.tmp"
log "python $(python3 --version 2>&1)"
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader || true

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
    cpu) url="https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_RELEASE}/llama-${LLAMA_RELEASE}-bin-ubuntu-x64.tar.gz" ;;
    *) echo "unknown variant $variant" >&2; return 1 ;;
  esac
  [ -n "$(llama_bin_dir "$variant")" ] && return 0
  mkdir -p "$(dir_for "$variant")"
  log "downloading llama.cpp $variant build ($LLAMA_RELEASE)"
  curl -fsSL --retry 3 -o "$TOOLS/$variant.tar.gz" "$url"
  tar -xzf "$TOOLS/$variant.tar.gz" -C "$(dir_for "$variant")"
  rm -f "$TOOLS/$variant.tar.gz"
}

LLAMA_BIN=""
if fetch_llama cuda; then
  LLAMA_BIN="$(llama_bin_dir cuda)"
  if [ -z "$LLAMA_BIN" ] || ! "$LLAMA_BIN/llama-server" --version >/dev/null 2>&1; then
    log "CUDA build unusable here, falling back to the CPU build (recorded in the manifest)"
    LLAMA_BIN=""
  fi
fi
if [ -z "$LLAMA_BIN" ]; then
  fetch_llama cpu
  LLAMA_BIN="$(llama_bin_dir cpu)"
fi
[ -n "$LLAMA_BIN" ] || { echo "no llama.cpp binary available" >&2; exit 1; }
export PATH="$LLAMA_BIN:$PATH"
llama-server --version || true
llama-bench --help 2>&1 | head -1 || true

# lm-eval sees the image's torch/transformers/datasets as satisfied because the
# venv inherits system site-packages; only the harness and its small deps install.
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv --system-site-packages "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet "lm-eval"
export PATH="$VENV/bin:$PATH"
"$VENV/bin/python" -m lm_eval --version

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
