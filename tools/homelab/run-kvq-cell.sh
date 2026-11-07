#!/usr/bin/env bash
# One lease: n=40 MCQ accuracy at ctx 4096 with a chosen KV cache type.
# Reads tools/homelab/kvq-config.env: KV=f16|q8_0, TAG=...
set -euo pipefail
export REPO=/workspace/repo
export MODELS_DIR=/models
[ -f "$REPO/tools/homelab/kvq-config.env" ] && . "$REPO/tools/homelab/kvq-config.env"
KV=${KV:-f16}; TAG=${TAG:-kv}; LIMIT=${LIMIT:-40}
SPEC="/workspace/.tmp/kvq-$TAG.yaml"
mkdir -p /workspace/.tmp
BASE="$REPO/configs/campaigns/gpu-lab-kv-quality.yaml"
sed -e "s|^campaign: .*|campaign: gpu-lab-kvq-$TAG|" \
    -e "s|^  limit: .*|  limit: $LIMIT|" \
    -e "s|^  cache_type_k: .*|  cache_type_k: $KV|" \
    -e "s|^  cache_type_v: .*|  cache_type_v: $KV|" \
    "$BASE" > "$SPEC"
# base spec has no cache type lines: inject them under server
python3 - "$SPEC" "$KV" <<'PY'
import sys
p, kv = sys.argv[1], sys.argv[2]
s = open(p).read()
if "cache_type_k" not in s:
    s = s.replace("  cache_ram: 0\n", f"  cache_ram: 0\n  cache_type_k: {kv}\n  cache_type_v: {kv}\n")
open(p, "w").write(s)
PY
export SPEC
export GPU_LAB_TASK=campaign
export CAMPAIGN_NO_BENCH=1
exec bash "$REPO/tools/homelab/campaign-entrypoint.sh"
