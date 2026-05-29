#!/usr/bin/env bash
# init.sh — Initialize trellis-team-kit in a project directory
set -euo pipefail

DEV_NAME="${1:-}"

if [ -z "$DEV_NAME" ]; then
  echo "Usage: init.sh <developer-name>"
  echo ""
  echo "Example:"
  echo "  Local:  bash path/to/trellis-team-kit/bootstrap/init.sh alice"
  echo "  Remote: bash <(curl -fsSL https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh) alice"
  exit 1
fi

RAW_BASE="https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main"
TARGET_ROOT="$(pwd)"

# Detect execution mode: local (has real script path) or remote (piped via curl)
if [ -f "${BASH_SOURCE[0]}" ] && [[ "${BASH_SOURCE[0]}" != "/dev/fd/"* ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  KIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  MODE="local"
else
  KIT_ROOT=""
  MODE="remote"
fi

if [ "$MODE" = "local" ] && [ "$TARGET_ROOT" = "$KIT_ROOT" ]; then
  echo "Error: do not run this script inside trellis-team-kit."
  echo "Run it from the project directory you want to initialize."
  exit 1
fi

# --- Helpers ---
info()  { echo "[init] $*"; }
error() { echo "[init] ERROR: $*" >&2; exit 1; }

# Get a file: local copy or remote download
get_file() {
  local src="$1" dst="$2"
  if [ "$MODE" = "local" ]; then
    cp "$KIT_ROOT/$src" "$dst"
  else
    curl -fsSL "$RAW_BASE/$src" -o "$dst"
  fi
}

# Get a directory: local copy or remote download (file by file)
get_dir() {
  local src="$1" dst="$2" file_list="$3"
  mkdir -p "$dst"
  if [ "$MODE" = "local" ]; then
    cp -R "$KIT_ROOT/$src/"* "$dst/" 2>/dev/null || true
  else
    for f in $file_list; do
      curl -fsSL "$RAW_BASE/$src/$f" -o "$dst/$f"
    done
  fi
}

# --- Pre-flight ---
if ! command -v trellis >/dev/null 2>&1; then
  error "trellis command not found. Install it first: npm install -g @mindfoldhq/trellis"
fi

if [ ! -d "$TARGET_ROOT/.git" ]; then
  error "Not a git repository. Run 'git init' first."
fi

# --- Step 1: Run trellis init with team marketplace ---
info "Step 1/9: Running trellis init with team marketplace..."
trellis init -u "$DEV_NAME" --claude \
  --registry "gh:05allan1213/trellis-team-kit/marketplace" \
  --template web-app

# --- Step 2: Install entry files (AGENTS.md, CLAUDE.md) ---
info "Step 2/9: Installing entry files..."
get_file "entry/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
get_file "entry/CLAUDE.md" "$TARGET_ROOT/CLAUDE.md"
info "  AGENTS.md installed"
info "  CLAUDE.md installed"

# --- Step 3: Install workflow ---
info "Step 3/9: Installing workflow..."
mkdir -p "$TARGET_ROOT/.trellis"
get_file "workflow/workflow.md" "$TARGET_ROOT/.trellis/workflow.md"
info "  .trellis/workflow.md installed"

# --- Step 4: Install claude/settings.json ---
info "Step 4/9: Installing Claude settings..."
mkdir -p "$TARGET_ROOT/.claude"
get_file "claude/settings.json" "$TARGET_ROOT/.claude/settings.json"
info "  .claude/settings.json installed"

# --- Step 5: Install skills ---
info "Step 5/9: Installing skills..."
SKILL_COUNT=0
for skill in \
  trellis-before-dev trellis-brainstorm trellis-break-loop trellis-check \
  trellis-code-architecture-review trellis-code-review trellis-dev-strategy \
  trellis-finish-work trellis-grill-me trellis-implement \
  trellis-improve-codebase-architecture trellis-merge-review \
  trellis-spec-review trellis-update-spec; do
  target_dir="$TARGET_ROOT/.claude/skills/$skill"
  mkdir -p "$target_dir"
  get_file "claude/skills/$skill/SKILL.md" "$target_dir/SKILL.md"
  SKILL_COUNT=$((SKILL_COUNT + 1))
done
info "  $SKILL_COUNT skills installed"

# --- Step 6: Install agents ---
info "Step 6/9: Installing agents..."
AGENT_COUNT=0
mkdir -p "$TARGET_ROOT/.claude/agents"
for agent in \
  trellis-architecture-deep-reviewer trellis-architecture-reviewer \
  trellis-checker trellis-code-reviewer trellis-implementer \
  trellis-merge-reviewer trellis-researcher trellis-spec-reviewer \
  trellis-spec-updater; do
  get_file "claude/agents/$agent.md" "$TARGET_ROOT/.claude/agents/$agent.md"
  AGENT_COUNT=$((AGENT_COUNT + 1))
done
info "  $AGENT_COUNT agents installed"

# --- Step 7: Install hooks, commands, and hook libs ---
info "Step 7/9: Installing hooks, commands, and hook libs..."
HOOK_COUNT=0
mkdir -p "$TARGET_ROOT/.claude/hooks"
for hook in \
  inject-subagent-context inject-workflow-state post-edit-reminder \
  pre-compact-save-state protect-dangerous-actions session-start \
  stop-guard subagent-stop-guard; do
  get_file "claude/hooks/$hook.py" "$TARGET_ROOT/.claude/hooks/$hook.py"
  HOOK_COUNT=$((HOOK_COUNT + 1))
done

# Install notification hook
get_file "claude/hooks/trellis-notify.sh" "$TARGET_ROOT/.claude/hooks/trellis-notify.sh"
chmod +x "$TARGET_ROOT/.claude/hooks/trellis-notify.sh"
HOOK_COUNT=$((HOOK_COUNT + 1))

# Install hook libs
LIB_COUNT=0
mkdir -p "$TARGET_ROOT/.claude/hooks/lib"
for lib in __init__ hook_output workflow_state task_artifacts naming; do
  get_file "claude/hooks/lib/$lib.py" "$TARGET_ROOT/.claude/hooks/lib/$lib.py"
  LIB_COUNT=$((LIB_COUNT + 1))
done
info "  $HOOK_COUNT hooks installed"
info "  $LIB_COUNT hook libs installed"

COMMAND_COUNT=0
mkdir -p "$TARGET_ROOT/.claude/commands/trellis"
for cmd in finish-work continue create-manifest; do
  get_file "claude/commands/trellis/$cmd.md" "$TARGET_ROOT/.claude/commands/trellis/$cmd.md"
  COMMAND_COUNT=$((COMMAND_COUNT + 1))
done
info "  $COMMAND_COUNT commands installed"

# --- Step 8: Install validators ---
info "Step 8/9: Installing static validators..."
VALIDATOR_COUNT=0
mkdir -p "$TARGET_ROOT/.trellis/scripts"
for v in \
  validate_claude_settings validate_naming_map validate_hooks \
  validate_task validate_review_gates validate_runtime_hardening; do
  get_file "trellis/scripts/$v.py" "$TARGET_ROOT/.trellis/scripts/$v.py"
  VALIDATOR_COUNT=$((VALIDATOR_COUNT + 1))
done
info "  $VALIDATOR_COUNT validators installed"

# --- Step 9: Install specs, templates, and record version ---
info "Step 9/9: Installing specs, templates, and recording version..."

# Specs are already installed by trellis init --template web-app in Step 1.
# Count what trellis init placed.
SPEC_COUNT=$(find "$TARGET_ROOT/.trellis/spec" -name "*.md" 2>/dev/null | wc -l)
info "  $SPEC_COUNT spec files installed"

# Install task templates
TEMPLATE_COUNT=0
mkdir -p "$TARGET_ROOT/.trellis/templates"
for tmpl in \
  prd.md.tmpl design.md.tmpl implement.md.tmpl finish.md.tmpl pr-template.md \
  research/evidence.md.tmpl research/brainstorm.md.tmpl research/grill-me.md.tmpl \
  research/external-docs.md.tmpl research/architecture-options.md.tmpl \
  research/break-loop.md.tmpl research/spike-results.md.tmpl research/decision-log.md.tmpl \
  review/spec-review.md.tmpl review/code-review.md.tmpl \
  review/architecture-review.md.tmpl review/merge-review.md.tmpl \
  validation/commands.md.tmpl validation/test-results.md.tmpl validation/build-results.md.tmpl; do
  mkdir -p "$(dirname "$TARGET_ROOT/.trellis/templates/$tmpl")"
  get_file "trellis/task-templates/$tmpl" "$TARGET_ROOT/.trellis/templates/$tmpl"
  TEMPLATE_COUNT=$((TEMPLATE_COUNT + 1))
done
info "  $TEMPLATE_COUNT task templates installed"

# Record version
get_file "VERSION" "$TARGET_ROOT/.trellis/.team-kit-version"
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
echo "    Hook libs:    $LIB_COUNT"
echo "    Commands:     $COMMAND_COUNT"
echo "    Validators:   $VALIDATOR_COUNT"
echo "    Spec files:   $SPEC_COUNT"
echo "    Templates:    $TEMPLATE_COUNT"
echo ""
echo "  Next steps:"
echo "    1. Run local setup:"
echo "       bash bootstrap/init-local.sh <name>"
echo ""
echo "    2. Run static validation:"
echo "       python3 .trellis/scripts/validate_runtime_hardening.py"
echo ""
echo "    3. Open Claude Code and verify hook registration."
echo ""
echo "    4. Real smoke test is recommended before team pilot."
echo "=========================================="
