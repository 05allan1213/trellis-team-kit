#!/usr/bin/env bash
set -euo pipefail

# install-claude-code-assets.sh
# Installs team-kit Claude Code assets into the target project.
# Called by init.sh after trellis init completes.

TARGET_DIR="${1:-.}"
RAW_BASE="https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main"

echo "Installing team-kit Claude Code assets..."

# settings.json
echo "  .claude/settings.json"
mkdir -p "$TARGET_DIR/.claude"
curl -fsSL "$RAW_BASE/claude/settings.json" -o "$TARGET_DIR/.claude/settings.json"

# settings.local.json.example
echo "  .claude/settings.local.json.example"
curl -fsSL "$RAW_BASE/claude/settings.local.json.example" -o "$TARGET_DIR/.claude/settings.local.json.example"

# skills
echo "  .claude/skills/"
mkdir -p "$TARGET_DIR/.claude/skills"
for skill_dir in trellis-brainstorm trellis-grill-me trellis-dev-strategy trellis-before-dev trellis-implement trellis-check trellis-spec-review trellis-code-review trellis-code-architecture-review trellis-improve-codebase-architecture trellis-update-spec trellis-break-loop trellis-merge-review trellis-finish-work; do
  mkdir -p "$TARGET_DIR/.claude/skills/$skill_dir"
  curl -fsSL "$RAW_BASE/claude/skills/$skill_dir/SKILL.md" -o "$TARGET_DIR/.claude/skills/$skill_dir/SKILL.md"
done

# agents
echo "  .claude/agents/"
mkdir -p "$TARGET_DIR/.claude/agents"
for agent in trellis-researcher trellis-implementer trellis-checker trellis-spec-reviewer trellis-code-reviewer trellis-architecture-reviewer trellis-architecture-deep-reviewer trellis-merge-reviewer trellis-spec-updater; do
  curl -fsSL "$RAW_BASE/claude/agents/$agent.md" -o "$TARGET_DIR/.claude/agents/$agent.md"
done

# hooks
echo "  .claude/hooks/"
mkdir -p "$TARGET_DIR/.claude/hooks"
for hook in session-start inject-workflow-state inject-subagent-context subagent-stop-guard stop-guard protect-dangerous-actions post-edit-reminder pre-compact-save-state; do
  curl -fsSL "$RAW_BASE/claude/hooks/$hook.py" -o "$TARGET_DIR/.claude/hooks/$hook.py"
done

# notification hook
curl -fsSL "$RAW_BASE/claude/hooks/trellis-notify.sh" -o "$TARGET_DIR/.claude/hooks/trellis-notify.sh"
chmod +x "$TARGET_DIR/.claude/hooks/trellis-notify.sh"

# commands
echo "  .claude/commands/"
mkdir -p "$TARGET_DIR/.claude/commands/trellis"
for cmd in finish-work continue create-manifest; do
  curl -fsSL "$RAW_BASE/claude/commands/trellis/$cmd.md" -o "$TARGET_DIR/.claude/commands/trellis/$cmd.md"
done

echo "Claude Code assets installed."
