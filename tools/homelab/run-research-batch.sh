#!/usr/bin/env bash
# One lease, two stages: H1 context/KV sweep (6 cells) then the capability probe
# campaign (structured output + tool calls). Both reuse the campaign pipeline.
#   ssh gpu-lab-ander@192.168.1.23 'job repo/tools/homelab/run-research-batch.sh'
set -euo pipefail
export REPO=/workspace/repo
export MODELS_DIR=/models

GPU_LAB_TASK=sweep bash "$REPO/tools/homelab/campaign-entrypoint.sh"

GPU_LAB_TASK=campaign \
  SPEC="$REPO/configs/campaigns/gpu-lab-capability-probe.yaml" \
  bash "$REPO/tools/homelab/campaign-entrypoint.sh"
