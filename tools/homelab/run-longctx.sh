#!/usr/bin/env bash
# One lease: structured-output probe with ~3.8k-token prompts.
set -euo pipefail
export REPO=/workspace/repo MODELS_DIR=/models
[ -f "$REPO/tools/homelab/longctx-config.env" ] && . "$REPO/tools/homelab/longctx-config.env"
TAG=${TAG:-longctx}
SPEC="/workspace/.tmp/longctx-$TAG.yaml"
mkdir -p /workspace/.tmp
sed -e "s|^campaign: .*|campaign: gpu-lab-longctx-$TAG|" \
    -e "s|^  context_fill: .*|  context_fill: ${FILL:-3800}\n  vram_csv: /workspace/results/conc/$TAG-vram.csv|" \
    -e "s|^  limit: .*|  limit: ${LIMIT:-3}|" \
    -e "s|^  max_gen_toks: .*|  max_gen_toks: ${GEN:-64}\n  instruction: ${INSTR:-schema}|" \
    "$REPO/configs/campaigns/gpu-lab-longctx-capability.yaml" > "$SPEC"
export SPEC GPU_LAB_TASK=campaign CAMPAIGN_NO_BENCH=1
exec bash "$REPO/tools/homelab/campaign-entrypoint.sh"
