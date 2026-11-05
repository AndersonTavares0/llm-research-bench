#!/usr/bin/env bash
# One lease, one concurrency cell with equivalent per-slot context.
# Reads /workspace/repo/tools/homelab/conc-config.env: CTX, PAR, CLIENTS, TAG, ROUNDS.
set -euo pipefail
export REPO=/workspace/repo
export MODELS_DIR=/models
[ -f "$REPO/tools/homelab/conc-config.env" ] && . "$REPO/tools/homelab/conc-config.env"
TAG=${TAG:-cell}
SPEC="/workspace/.tmp/conc-$TAG.yaml"
mkdir -p /workspace/.tmp /workspace/results/conc
BASE="$REPO/configs/campaigns/gpu-lab-concurrency-qwen3.yaml"
sed -e "s|^campaign: .*|campaign: gpu-lab-conc-equiv-$TAG|" \
    -e "s|^  ctx_size: .*|  ctx_size: $CTX|" \
    -e "s|^  parallel: .*|  parallel: $PAR|" \
    -e "s|^  clients: .*|  clients: $CLIENTS\n  vram_csv: /workspace/results/conc/$TAG-vram.csv|" \
    -e "s|^  limit: .*|  limit: ${ROUNDS:-6}|" \
    -e "s|^  max_gen_toks: .*|  max_gen_toks: 32|" \
    "$BASE" > "$SPEC"
export SPEC
export GPU_LAB_TASK=campaign
export CAMPAIGN_NO_BENCH=1
exec bash "$REPO/tools/homelab/campaign-entrypoint.sh"
