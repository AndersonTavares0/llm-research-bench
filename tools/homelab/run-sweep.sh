#!/usr/bin/env bash
# Job wrapper for the H1 context/KV sweep: one lease, six cells.
#   ssh gpu-lab-ander@192.168.1.23 'job repo/tools/homelab/run-sweep.sh'
set -euo pipefail
export REPO=/workspace/repo
export MODELS_DIR=/models
export GPU_LAB_TASK=sweep
export SWEEP_BASE="$REPO/configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml"
export SWEEP_GRID="${SWEEP_GRID:-ctx=2048,4096,8192}"
export SWEEP_KV="${SWEEP_KV:-f16,q8_0}"
export SWEEP_OUT="${SWEEP_OUT:-/workspace/results/sweeps/kv-ctx}"
exec bash "$REPO/tools/homelab/campaign-entrypoint.sh"
