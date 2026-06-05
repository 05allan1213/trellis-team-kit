#!/usr/bin/env bash
# init-local.sh — Legacy compatibility alias for personalize-local.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$SCRIPT_DIR/personalize-local.sh"

echo "[init-local] compatibility alias: forwarding to personalize-local.sh" >&2
exec bash "$TARGET" "$@"
