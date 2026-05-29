#!/usr/bin/env bash
# init.sh — Initialize trellis-team-kit in a project directory
set -euo pipefail

DEV_NAME="${1:-}"

if [ -z "$DEV_NAME" ]; then
  echo "Usage: init.sh <developer-name>"
  echo ""
  echo "Example: init.sh alice"
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

# --- Helpers ---
info()  { echo "[init] $*"; }
error() { echo "[init] ERROR: $*" >&2; exit 1; }

# --- Pre-flight ---
if ! command -v trellis >/dev/null 2>&1; then
  error "trellis command not found. Install it first: npm install -g @mindfoldhq/trellis"
fi

if [ ! -d "$TARGET_ROOT/.git" ]; then
  error "Not a git repository. Run 'git init' first."
fi

# --- Step 1: Run trellis init with team marketplace ---
info "Step 1/8: Running trellis init with team marketplace..."
trellis init -u "$DEV_NAME" --claude \
  --registry "gh:05allan1213/trellis-team-kit/marketplace" \
  --template web-app

# --- Step 2: Install entry files (AGENTS.md, CLAUDE.md) ---
info "Step 2/8: Installing entry files..."
cp "$KIT_ROOT/entry/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
cp "$KIT_ROOT/entry/CLAUDE.md" "$TARGET_ROOT/CLAUDE.md"
info "  AGENTS.md installed"
info "  CLAUDE.md installed"

# --- Step 3: Install workflow ---
info "Step 3/8: Installing workflow..."
mkdir -p "$TARGET_ROOT/.trellis"
cp "$KIT_ROOT/workflow/workflow.md" "$TARGET_ROOT/.trellis/workflow.md"
info "  .trellis/workflow.md installed"

# --- Step 4: Install claude/settings.json ---
info "Step 4/8: Installing Claude settings..."
mkdir -p "$TARGET_ROOT/.claude"
cp "$KIT_ROOT/claude/settings.json" "$TARGET_ROOT/.claude/settings.json"
info "  .claude/settings.json installed"

# --- Step 5: Install skills ---
info "Step 5/8: Installing skills..."
SKILL_COUNT=0
for skill_dir in "$KIT_ROOT"/claude/skills/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name=$(basename "$skill_dir")
  target_dir="$TARGET_ROOT/.claude/skills/$skill_name"
  mkdir -p "$target_dir"
  cp -R "$skill_dir"* "$target_dir/"
  SKILL_COUNT=$((SKILL_COUNT + 1))
done
info "  $SKILL_COUNT skills installed"

# --- Step 6: Install agents ---
info "Step 6/8: Installing agents..."
AGENT_COUNT=0
mkdir -p "$TARGET_ROOT/.claude/agents"
for agent_file in "$KIT_ROOT"/claude/agents/*.md; do
  [ -f "$agent_file" ] || continue
  cp "$agent_file" "$TARGET_ROOT/.claude/agents/"
  AGENT_COUNT=$((AGENT_COUNT + 1))
done
info "  $AGENT_COUNT agents installed"

# --- Step 7: Install hooks and commands ---
info "Step 7/8: Installing hooks and commands..."
HOOK_COUNT=0
mkdir -p "$TARGET_ROOT/.claude/hooks"
for hook_file in "$KIT_ROOT"/claude/hooks/*.py; do
  [ -f "$hook_file" ] || continue
  cp "$hook_file" "$TARGET_ROOT/.claude/hooks/"
  HOOK_COUNT=$((HOOK_COUNT + 1))
done
info "  $HOOK_COUNT hooks installed"

COMMAND_COUNT=0
for cmd_file in "$KIT_ROOT"/claude/commands/**/*.md; do
  [ -f "$cmd_file" ] || continue
  cmd_rel=${cmd_file#$KIT_ROOT/claude/commands/}
  target_cmd="$TARGET_ROOT/.claude/commands/$cmd_rel"
  mkdir -p "$(dirname "$target_cmd")"
  cp "$cmd_file" "$target_cmd"
  COMMAND_COUNT=$((COMMAND_COUNT + 1))
done
info "  $COMMAND_COUNT commands installed"

# --- Step 8: Install specs and task templates, record version ---
info "Step 8/8: Installing specs, templates, and recording version..."

# Install specs from marketplace
SPEC_COUNT=0
mkdir -p "$TARGET_ROOT/.trellis/spec"
if [ -d "$KIT_ROOT/marketplace/specs/web-app" ]; then
  cp -R "$KIT_ROOT/marketplace/specs/web-app/"* "$TARGET_ROOT/.trellis/spec/"
  SPEC_COUNT=$(find "$TARGET_ROOT/.trellis/spec" -name "*.md" | wc -l)
fi
info "  $SPEC_COUNT spec files installed"

# Install task templates
TEMPLATE_COUNT=0
if [ -d "$KIT_ROOT/trellis/task-templates" ]; then
  mkdir -p "$TARGET_ROOT/.trellis/templates"
  cp -R "$KIT_ROOT/trellis/task-templates/"* "$TARGET_ROOT/.trellis/templates/" 2>/dev/null || true
  TEMPLATE_COUNT=$(find "$TARGET_ROOT/.trellis/templates" -name "*.tmpl" -o -name "*.md" 2>/dev/null | wc -l)
fi
info "  $TEMPLATE_COUNT task templates installed"

# Record version
cp "$KIT_ROOT/VERSION" "$TARGET_ROOT/.trellis/.team-kit-version"
echo "initialized_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$TARGET_ROOT/.trellis/.team-kit-version"
echo "initialized_by: $DEV_NAME" >> "$TARGET_ROOT/.trellis/.team-kit-version"

# --- Summary ---
echo ""
echo "=========================================="
echo "  trellis-team-kit initialized"
echo "=========================================="
echo ""
echo "  Developer:  $DEV_NAME"
echo "  Project:    $TARGET_ROOT"
echo ""
echo "  Installed:"
echo "    Entry files:  AGENTS.md, CLAUDE.md"
echo "    Workflow:     .trellis/workflow.md"
echo "    Settings:     .claude/settings.json"
echo "    Skills:       $SKILL_COUNT"
echo "    Agents:       $AGENT_COUNT"
echo "    Hooks:        $HOOK_COUNT"
echo "    Commands:     $COMMAND_COUNT"
echo "    Spec files:   $SPEC_COUNT"
echo "    Templates:    $TEMPLATE_COUNT"
echo ""
echo "  Next steps:"
echo "    1. Review .trellis/spec/index.md for your project"
echo "    2. Customize specs in .trellis/spec/ for your stack"
echo "    3. Start a task: describe what you want to build"
echo "=========================================="
