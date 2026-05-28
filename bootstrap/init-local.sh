#!/usr/bin/env bash
set -euo pipefail

DEV_NAME="${1:-}"

if [ -z "$DEV_NAME" ]; then
  echo "Usage: init-local.sh <developer-name>"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_ROOT="$(pwd)"

if [ "$TARGET_ROOT" = "$KIT_ROOT" ]; then
  echo "Error: do not run this script inside trellis-team-kit."
  echo "Run it from the project directory you want to initialize."
  exit 1
fi

echo "Initializing Trellis with official Claude Code platform files..."
trellis init -u "$DEV_NAME" --claude

echo "Applying team entry files..."
cp "$KIT_ROOT/entry/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
cp "$KIT_ROOT/entry/CLAUDE.md" "$TARGET_ROOT/CLAUDE.md"

echo "Applying team workflow..."
cp "$KIT_ROOT/workflow/workflow.md" "$TARGET_ROOT/.trellis/workflow.md"

echo "Applying team specs..."
rm -rf "$TARGET_ROOT/.trellis/spec"
mkdir -p "$TARGET_ROOT/.trellis/spec"
cp -R "$KIT_ROOT/marketplace/specs/web-app/"* "$TARGET_ROOT/.trellis/spec/"

echo "Recording team kit version..."
cp "$KIT_ROOT/VERSION" "$TARGET_ROOT/.trellis/.team-kit-version"
echo "initialized_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$TARGET_ROOT/.trellis/.team-kit-version"

echo "Done."
echo "Generated:"
echo "  AGENTS.md"
echo "  CLAUDE.md"
echo "  .claude/"
echo "  .trellis/workflow.md"
echo "  .trellis/spec/"
