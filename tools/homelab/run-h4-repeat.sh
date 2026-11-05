#!/usr/bin/env bash
# One lease, one H4 cell: two concurrent clients against PARALLEL server slots.
#   PARALLEL=1 REPEAT=2 ssh gpu-lab-ander@192.168.1.23 \
#     'PARALLEL=1 REPEAT=2 job repo/tools/homelab/run-h4-repeat.sh'
set -euo pipefail
export REPO=/workspace/repo
# The forced command accepts no extra arguments, so the cell is chosen by this
# file (written by the operator before each lease).
if [ -f "$REPO/tools/homelab/h4-config.env" ]; then . "$REPO/tools/homelab/h4-config.env"; fi
export MODELS_DIR=/models
export SWEEP_BASE="$REPO/configs/campaigns/gpu-lab-concurrency-qwen3.yaml"
export SWEEP_GRID=ctx=8192
export SWEEP_KV=q8_0
export SWEEP_PARALLEL="${PARALLEL:-1}"
export SWEEP_REPEAT="${REPEAT:-1}"
export SWEEP_SUFFIX="r${SWEEP_REPEAT}"
export SWEEP_OUT="/workspace/results/sweeps/h4-par${SWEEP_PARALLEL}-r${SWEEP_REPEAT}"
export GPU_LAB_TASK=sweep
exec bash "$REPO/tools/homelab/campaign-entrypoint.sh"
