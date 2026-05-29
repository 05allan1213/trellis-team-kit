#!/usr/bin/env bash
# init-local.sh — Local initialization for trellis-team-kit
# Creates local settings, workspace directory, and personal preferences.
# Run AFTER init.sh.
set -euo pipefail

DEV_NAME="${1:-}"

if [ -z "$DEV_NAME" ]; then
  echo "Usage: init-local.sh <developer-name>"
  echo ""
  echo "Example: init-local.sh alice"
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

if [ ! -f "$TARGET_ROOT/.trellis/.team-kit-version" ]; then
  echo "Error: trellis-team-kit not initialized. Run init.sh first."
  exit 1
fi

# --- Helpers ---
info()  { echo "[init-local] $*"; }
warn()  { echo "[init-local] WARNING: $*" >&2; }

# --- Step 1: Create claude/settings.local.json ---
info "Step 1/3: Creating .claude/settings.local.json ..."
mkdir -p "$TARGET_ROOT/.claude"

if [ -f "$TARGET_ROOT/.claude/settings.local.json" ]; then
  warn "  .claude/settings.local.json already exists, skipping"
else
  cat > "$TARGET_ROOT/.claude/settings.local.json" << 'SETTINGS_EOF'
{
  "permissions": {
    "allow": [],
    "deny": []
  }
}
SETTINGS_EOF
  info "  .claude/settings.local.json created"
fi

# --- Step 2: Create .trellis/workspace/<name>/ ---
info "Step 2/3: Creating workspace directory ..."
WORKSPACE_DIR="$TARGET_ROOT/.trellis/workspace/$DEV_NAME"
mkdir -p "$WORKSPACE_DIR"

if [ ! -f "$WORKSPACE_DIR/journal.md" ]; then
  cat > "$WORKSPACE_DIR/journal.md" << JOURNAL_EOF
# Development Journal — $DEV_NAME

Track task completions, learnings, and decisions here.
Entries are appended automatically by trellis-finish-work.

---

JOURNAL_EOF
  info "  Created workspace and journal at .trellis/workspace/$DEV_NAME/"
else
  info "  Workspace already exists at .trellis/workspace/$DEV_NAME/"
fi

# --- Step 3: Generate personal preferences ---
info "Step 3/3: Generating personal preferences ..."
PREFS_FILE="$WORKSPACE_DIR/preferences.md"

if [ -f "$PREFS_FILE" ]; then
  warn "  $PREFS_FILE already exists, skipping"
else
  cat > "$PREFS_FILE" << PREFS_EOF
# Personal Preferences — $DEV_NAME

Customize these preferences to match your workflow.
These are loaded during before-dev to tailor the development experience.

## Commit Style
- Preferred commit message format: conventional commits (feat/fix/refactor/docs)
- Include co-author: yes

## Code Style
- Prefer explicit over implicit
- Prefer early returns over nested conditionals
- Prefer small focused functions

## Review Preferences
- Prefer actionable feedback over vague suggestions
- Flag security and performance concerns immediately

## Notes
- Add any personal workflow preferences here
- This file is not shared with the team
PREFS_EOF
  info "  Created preferences at .trellis/workspace/$DEV_NAME/preferences.md"
fi

# --- Summary ---
echo ""
echo "=========================================="
echo "  Local setup complete for $DEV_NAME"
echo "=========================================="
echo ""
echo "  Created:"
echo "    .claude/settings.local.json"
echo "    .trellis/workspace/$DEV_NAME/journal.md"
echo "    .trellis/workspace/$DEV_NAME/preferences.md"
echo ""
echo "  Next steps:"
echo "    1. Edit .trellis/workspace/$DEV_NAME/preferences.md"
echo "    2. Add custom permissions to .claude/settings.local.json"
echo "    3. Start coding with your personalized setup"
echo "=========================================="
