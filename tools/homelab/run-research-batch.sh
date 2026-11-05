#!/usr/bin/env bash
# One short lease, two stages:
#   1. H1 context/KV probe sweep (server must start per cell; llama-bench alone
#      ignores context and KV type), 6 cells.
#   2. capability campaign (structured output + tool calls) on Qwen3-1.7B.
#   ssh gpu-lab-ander@192.168.1.23 'job repo/tools/homelab/run-research-batch.sh'
set -euo pipefail
export REPO=/workspace/repo
export MODELS_DIR=/models

export SWEEP_BASE="$REPO/configs/campaigns/gpu-lab-ctxkv-probe.yaml"
export SWEEP_GRID="${SWEEP_GRID:-ctx=2048,4096,8192}"
export SWEEP_KV="${SWEEP_KV:-f16,q8_0}"
export SWEEP_OUT="${SWEEP_OUT:-/workspace/results/sweeps/ctxkv2}"
export SWEEP_NO_BENCH=1
GPU_LAB_TASK=sweep bash "$REPO/tools/homelab/campaign-entrypoint.sh"

GPU_LAB_TASK=campaign \
  SPEC="$REPO/configs/campaigns/gpu-lab-capability-probe.yaml" \
  bash "$REPO/tools/homelab/campaign-entrypoint.sh"
