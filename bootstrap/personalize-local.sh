#!/usr/bin/env bash
# personalize-local.sh — Optional local personalization for trellis-team-kit
# Rebuilds local-only files if needed and creates personal preferences.
# Run AFTER init.sh when you want extra local customization.
set -euo pipefail

DEV_NAME="${1:-}"

if [ -z "$DEV_NAME" ]; then
  echo "Usage: personalize-local.sh <developer-name>"
  echo ""
  echo "Example: personalize-local.sh alice"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_ROOT="$(pwd)"
SETTINGS_TEMPLATE="$KIT_ROOT/claude/settings.local.json.example"

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
info()  { echo "[personalize-local] $*"; }
warn()  { echo "[personalize-local] WARNING: $*" >&2; }

write_workspace_root_index() {
  local root_index="$TARGET_ROOT/.trellis/workspace/index.md"
  if [ -f "$root_index" ]; then
    return 0
  fi
  cat > "$root_index" <<'ROOT_INDEX_EOF'
# Workspace Index

## Active Developers

| Developer | Last Active | Sessions | Active File |
|-----------|-------------|----------|-------------|
| (none yet) | - | - | - |
ROOT_INDEX_EOF
  info "  Created workspace root index at .trellis/workspace/index.md"
}

write_developer_index() {
  local developer_index="$WORKSPACE_DIR/index.md"
  if [ -f "$developer_index" ]; then
    return 0
  fi
  cat > "$developer_index" <<DEV_INDEX_EOF
# Workspace Index - $DEV_NAME

<!-- @@@auto:current-status -->
- **Active File**: \`journal-1.md\`
- **Total Sessions**: 1
- **Last Active**: -
<!-- @@@/auto:current-status -->

<!-- @@@auto:session-history -->
| # | Date | Title | Commits | Branch |
|---|------|-------|---------|--------|
| (none yet) | - | - | - | - |
<!-- @@@/auto:session-history -->
DEV_INDEX_EOF
  info "  Created developer workspace index at .trellis/workspace/$DEV_NAME/index.md"
}

ensure_journal_file() {
  local journal_file="$WORKSPACE_DIR/journal-1.md"
  local legacy_journal="$WORKSPACE_DIR/journal.md"

  if [ -f "$journal_file" ]; then
    info "  Workspace already exists at .trellis/workspace/$DEV_NAME/"
    return 0
  fi

  if [ -f "$legacy_journal" ]; then
    mv "$legacy_journal" "$journal_file"
    info "  Migrated legacy journal to .trellis/workspace/$DEV_NAME/journal-1.md"
    return 0
  fi

  cat > "$journal_file" <<JOURNAL_EOF
# Development Journal — $DEV_NAME

Track task completions, learnings, and decisions here.
Entries are appended automatically by trellis-finish-work.

---

JOURNAL_EOF
  info "  Created workspace and journal at .trellis/workspace/$DEV_NAME/"
}

# --- Step 1: Create claude/settings.local.json ---
info "Step 1/3: Creating .claude/settings.local.json ..."
mkdir -p "$TARGET_ROOT/.claude"

if [ -f "$TARGET_ROOT/.claude/settings.local.json" ]; then
  warn "  .claude/settings.local.json already exists, skipping"
else
  if [ -f "$SETTINGS_TEMPLATE" ]; then
    cp "$SETTINGS_TEMPLATE" "$TARGET_ROOT/.claude/settings.local.json"
  else
    cat > "$TARGET_ROOT/.claude/settings.local.json" <<'SETTINGS_EOF'
{
  "permissions": {
    "allow": [],
    "deny": []
  }
}
SETTINGS_EOF
  fi
  info "  .claude/settings.local.json created"
fi

# --- Step 2: Create .trellis/workspace/<name>/ ---
info "Step 2/3: Creating workspace directory ..."
WORKSPACE_DIR="$TARGET_ROOT/.trellis/workspace/$DEV_NAME"
mkdir -p "$WORKSPACE_DIR"
printf '%s\n' "$DEV_NAME" > "$TARGET_ROOT/.trellis/.developer"
write_workspace_root_index
write_developer_index
ensure_journal_file

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
echo "  Local personalization complete for $DEV_NAME"
echo "=========================================="
echo ""
echo "  Created:"
echo "    .claude/settings.local.json"
echo "    .trellis/.developer"
echo "    .trellis/workspace/index.md"
echo "    .trellis/workspace/$DEV_NAME/index.md"
echo "    .trellis/workspace/$DEV_NAME/journal-1.md"
echo "    .trellis/workspace/$DEV_NAME/preferences.md"
echo ""
echo "  Next steps:"
echo "    1. Edit .trellis/workspace/$DEV_NAME/preferences.md"
echo "    2. Add custom permissions to .claude/settings.local.json"
echo "    3. Re-run this script any time you want to rebuild local files"
echo "=========================================="
