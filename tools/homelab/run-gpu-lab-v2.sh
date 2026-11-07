#!/usr/bin/env bash
# Job wrapper for `gpu-lab job tools/homelab/run-gpu-lab-v2.sh`.
# Pins the spec and workspace paths the campaign entrypoint expects.
set -euo pipefail
export REPO=/workspace/repo
export SPEC=/workspace/repo/configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml
export MODELS_DIR=/models
export GPU_LAB_TASK=campaign
exec bash "$REPO/tools/homelab/campaign-entrypoint.sh"
