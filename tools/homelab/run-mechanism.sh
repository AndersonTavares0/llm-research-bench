#!/usr/bin/env bash
# One short lease: sentinel-field probe for constrained decoding.
set -euo pipefail
export REPO=/workspace/repo MODELS_DIR=/models
[ -f "$REPO/tools/homelab/mech-config.env" ] && . "$REPO/tools/homelab/mech-config.env"
TAG=${TAG:-mech}
SPEC="/workspace/.tmp/mech-$TAG.yaml"
mkdir -p /workspace/.tmp
sed -e "s|^campaign: .*|campaign: gpu-lab-mechanism-$TAG|" \
    "$REPO/configs/campaigns/gpu-lab-mechanism-probe.yaml" > "$SPEC"
export SPEC GPU_LAB_TASK=campaign CAMPAIGN_NO_BENCH=1
exec bash "$REPO/tools/homelab/campaign-entrypoint.sh"
