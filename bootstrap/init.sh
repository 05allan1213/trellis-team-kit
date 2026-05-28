#!/usr/bin/env bash
set -euo pipefail

DEV_NAME="${1:-}"

if [ -z "$DEV_NAME" ]; then
  echo "Usage: init.sh <developer-name>"
  exit 1
fi

RAW_BASE="https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main"

if ! command -v trellis >/dev/null 2>&1; then
  echo "Error: trellis command not found."
  echo ""
  echo "Please install Trellis first:"
  echo "  npm install -g @mindfoldhq/trellis"
  echo ""
  echo "Requirements:"
  echo "  Node.js 18+"
  echo "  Python 3.9+"
  echo "  git"
  exit 1
fi

echo "Initializing Trellis with official Claude Code platform files and team spec template..."
trellis init -u "$DEV_NAME" --claude \
  --registry gh:05allan1213/trellis-team-kit/marketplace \
  --template web-app

echo "Applying team entry files..."
curl -fsSL "$RAW_BASE/entry/AGENTS.md" -o ./AGENTS.md
curl -fsSL "$RAW_BASE/entry/CLAUDE.md" -o ./CLAUDE.md

echo "Applying team workflow..."
curl -fsSL "$RAW_BASE/workflow/workflow.md" -o ./.trellis/workflow.md

echo "Done."
echo "Generated:"
echo "  AGENTS.md"
echo "  CLAUDE.md"
echo "  .claude/"
echo "  .trellis/workflow.md"
echo "  .trellis/spec/"
