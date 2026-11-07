#!/usr/bin/env bash
# One lease, three stages:
#   1. H2 offload boundary (Llama-3.2-3B, bench only; -ngl per cell)
#   2. H4 concurrency (Qwen3-1.7B, parallel 1/2/4, two-client rounds)
#   3. q8_0 vs f16 KV quality (Qwen3-1.7B, ctx 4096, n=100 MCQ)
set -euo pipefail
export REPO=/workspace/repo
export MODELS_DIR=/models

# Offload boundary only; concurrency and KV quality are already measured.
export SWEEP_BASE="$REPO/configs/campaigns/gpu-lab-offload-llama32-3b.yaml"
export SWEEP_GRID=ctx=2048
export SWEEP_KV=q8_0
unset SWEEP_PARALLEL
export SWEEP_LAYERS=99,32,24,16
export SWEEP_OUT=/workspace/results/sweeps/offload2
SWEEP_BENCH_ONLY=1 GPU_LAB_TASK=sweep bash "$REPO/tools/homelab/campaign-entrypoint.sh" || echo "stage offload failed"
