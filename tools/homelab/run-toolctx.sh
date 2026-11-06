#!/usr/bin/env bash
# One lease: tool-calling suite at a controlled context length and format.
set -euo pipefail
export REPO=/workspace/repo MODELS_DIR=/models
[ -f "$REPO/tools/homelab/tool-config.env" ] && . "$REPO/tools/homelab/tool-config.env"
TAG=${TAG:-tool}; FILL=${FILL:-1900}; FMT=${FMT:-native}
SPEC="/workspace/.tmp/tool-$TAG.yaml"
mkdir -p /workspace/.tmp
sed -e "s|^campaign: .*|campaign: gpu-lab-toolctx-$TAG|" \
    -e "s|^  context_fill: .*|  context_fill: $FILL\n  vram_csv: /workspace/results/conc/$TAG-vram.csv|" \
    -e "s|^  tool_format: .*|  tool_format: $FMT|" \
    "$REPO/configs/campaigns/gpu-lab-toolcall-longctx.yaml" > "$SPEC"
export SPEC GPU_LAB_TASK=campaign CAMPAIGN_NO_BENCH=1
exec bash "$REPO/tools/homelab/campaign-entrypoint.sh"
