#!/usr/bin/env python3
"""
validate_claude_settings.py — Validate .claude/settings.json hook schema.

Checks:
- settings.json exists (supports both kit layout: claude/settings.json
  and installed layout: .claude/settings.json)
- hooks field exists
- Each event is a list
- Each entry has matcher and hooks list
- Each hook has type: command
- Each hook command script exists
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_EVENTS = [
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "SubagentStart", "SubagentStop", "Stop", "PreCompact", "Notification",
]


def find_project_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / "trellis").is_dir() and (cur / "claude" / "hooks").is_dir():
            return cur
        if (cur / ".trellis").is_dir() and (cur / ".claude" / "hooks").is_dir():
            return cur
        cur = cur.parent
    return None


def find_settings(root: Path) -> Path | None:
    installed = root / ".claude" / "settings.json"
    if installed.is_file():
        return installed
    kit = root / "claude" / "settings.json"
    if kit.is_file():
        return kit
    return None


def find_claude_dir(root: Path) -> Path | None:
    installed = root / ".claude"
    if installed.is_dir():
        return installed
    kit = root / "claude"
    if kit.is_dir():
        return kit
    return None


def validate_settings(settings_path: Path, root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not settings_path.is_file():
        return False, [f"{settings_path} does not exist"]

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return False, [f"Cannot parse {settings_path}: {e}"]

    hooks = data.get("hooks")
    if hooks is None:
        return False, ["No 'hooks' field in settings.json"]
    if not isinstance(hooks, dict):
        return False, ["'hooks' must be a JSON object"]

    for event_name, entries in hooks.items():
        if not isinstance(entries, list):
            errors.append(f"hooks.{event_name}: must be a list")
            continue

        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"hooks.{event_name}[{i}]: must be an object")
                continue

            if "matcher" not in entry:
                errors.append(f"hooks.{event_name}[{i}]: missing 'matcher' field")

            hook_list = entry.get("hooks")
            if hook_list is None:
                errors.append(
                    f"hooks.{event_name}[{i}]: missing 'hooks' list. "
                    f"Use {{matcher, hooks: [{{type: command, command: ...}}]}}"
                )
                continue
            if not isinstance(hook_list, list):
                errors.append(f"hooks.{event_name}[{i}].hooks: must be a list")
                continue

            for j, hook in enumerate(hook_list):
                if not isinstance(hook, dict):
                    errors.append(f"hooks.{event_name}[{i}].hooks[{j}]: must be an object")
                    continue
                if hook.get("type") != "command":
                    errors.append(
                        f"hooks.{event_name}[{i}].hooks[{j}]: missing or invalid 'type'. "
                        f"Expected 'type: command'"
                    )
                cmd = hook.get("command", "")
                if not cmd:
                    errors.append(f"hooks.{event_name}[{i}].hooks[{j}]: missing 'command'")
                    continue

                if "python3" in cmd:
                    parts = cmd.split()
                    for part in parts:
                        clean = part.strip().strip("\"'")
                        if not clean.endswith(".py"):
                            continue
                        if clean.startswith("${CLAUDE_PROJECT_DIR}/"):
                            clean = clean[len("${CLAUDE_PROJECT_DIR}/"):]
                        elif clean.startswith("$CLAUDE_PROJECT_DIR/"):
                            clean = clean[len("$CLAUDE_PROJECT_DIR/"):]
                        if clean.startswith("./"):
                            clean = clean[2:]
                        script_path = root / clean
                        if not script_path.is_file():
                            if clean.startswith(".claude/"):
                                alt_clean = "claude/" + clean[len(".claude/"):]
                                alt_path = root / alt_clean
                                if alt_path.is_file():
                                    break
                            errors.append(
                                f"hooks.{event_name}[{i}].hooks[{j}]: "
                                f"script not found: {part}"
                            )
                        break

    for event in REQUIRED_EVENTS:
        if event not in hooks:
            errors.append(f"hooks.{event}: recommended event is not configured")

    return len(errors) == 0, errors


def main() -> int:
    cwd = Path.cwd()
    root = find_project_root(cwd)
    if root is None:
        print("FAIL: No trellis-team-kit or project root found.")
        print("  Expected: trellis/ + claude/hooks/ OR .trellis/ + .claude/hooks/")
        return 1

    settings_path = find_settings(root)
    if settings_path is None:
        print("FAIL: Cannot find claude/settings.json or .claude/settings.json")
        return 1

    claude_dir = find_claude_dir(root)
    if claude_dir is None:
        print("FAIL: Cannot find .claude/ or claude/ directory")
        return 1

    ok, errors = validate_settings(settings_path, root)

    if ok:
        print(f"PASS: {settings_path} hook schema is valid")
        return 0

    print(f"FAIL: {settings_path} has {len(errors)} issue(s):")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
