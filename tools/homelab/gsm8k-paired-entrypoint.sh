#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export GPU_LAB_TASK=gsm8k-paired
exec bash "$SCRIPT_DIR/campaign-entrypoint.sh"
