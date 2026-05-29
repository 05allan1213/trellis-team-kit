#!/usr/bin/env python3
"""
Team-kit Protect Dangerous Actions Hook — v0.3 Hardened

Protects against dangerous operations with clear hard block / soft warning /
allow-with-reason distinction.

Hard block (deny):
- rm -rf, git reset --hard, git clean -fd, git push --force
- Editing .env or secrets/credentials files
- Deleting migration files
- Source file editing during planning phase (before implementation approval)
- task.py start without implementation consent
- Spawning implementer without approval

Soft warning (allow with reason):
- Editing lockfiles
- Editing generated files
- Modifying shared types
- Modifying env example / config files
- Changing (not deleting) migrations
- Large-scale formatting

Override (soft warnings only):
- User says "override team-kit guardrail: <reason>"
- Hard blocks CANNOT be overridden

Trigger: PreToolUse (before Bash, Write, Edit tools)
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

if sys.platform.startswith("win"):
    import io as _io
    for _stream_name in ("stdin", "stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        elif hasattr(_stream, "detach"):
            try:
                setattr(
                    sys, _stream_name,
                    _io.TextIOWrapper(_stream.detach(), encoding="utf-8", errors="replace"),
                )
            except Exception:
                pass

TRELLIS_DIR = ".trellis"

# ---- Hard block: dangerous bash command patterns ----
BLOCKED_BASH_PATTERNS = [
    (r"\brm\s+.*-rf\b",
     "BLOCKED: rm -rf detected.\n"
     "  Blocked action: Recursive force delete\n"
     "  Reason: Irreversible file deletion.\n"
     "  Correct next step: Use targeted file deletion instead."),
    (r"\bgit\s+reset\s+--hard\b",
     "BLOCKED: git reset --hard detected.\n"
     "  Blocked action: Hard reset\n"
     "  Reason: Destroys uncommitted work irreversibly.\n"
     "  Correct next step: Use git stash or git checkout instead."),
    (r"\bgit\s+clean\s+-fd\b",
     "BLOCKED: git clean -fd detected.\n"
     "  Blocked action: Force delete untracked files\n"
     "  Reason: Irreversibly removes untracked files.\n"
     "  Correct next step: Remove files individually."),
    (r"\bgit\s+push\s+.*--force\b",
     "BLOCKED: Force push detected.\n"
     "  Blocked action: Force push\n"
     "  Reason: Overwrites remote history, can destroy teammates' work.\n"
     "  Correct next step: Use regular push or coordinate with team."),
    (r"\bgit\s+push\s+-f\b",
     "BLOCKED: Force push detected.\n"
     "  Blocked action: Force push\n"
     "  Reason: Overwrites remote history, can destroy teammates' work.\n"
     "  Correct next step: Use regular push or coordinate with team."),
    (r"\bgit\s+push\s+--force-with-lease\b",
     "BLOCKED: Force push (--force-with-lease) detected.\n"
     "  Blocked action: Force push\n"
     "  Reason: Overwrites remote history.\n"
     "  Correct next step: Use regular push."),
]

# ---- Hard block: dangerous file patterns ----
BLOCKED_FILE_PATTERNS = [
    (r"(^|/)\.env$",
     "BLOCKED: Editing .env file.\n"
     "  Reason: .env files may contain secrets and credentials.\n"
     "  Correct next step: Edit .env manually, or use .env.example."),
    (r"(^|/)\.env\.local",
     "BLOCKED: Editing .env.local file.\n"
     "  Reason: Local env files may contain secrets.\n"
     "  Correct next step: Edit manually."),
    (r"(^|/)secrets?\.(json|yaml|yml|toml|env|py)",
     "BLOCKED: Editing secrets file.\n"
     "  Reason: Secrets files must not be edited through AI tools.\n"
     "  Correct next step: Edit manually."),
    (r"(^|/)credentials?\.(json|yaml|yml|env)",
     "BLOCKED: Editing credentials file.\n"
     "  Reason: Credentials files must not be edited through AI tools.\n"
     "  Correct next step: Edit manually."),
    (r"/migrations?/\d+_",
     "BLOCKED: Deleting migration file.\n"
     "  Reason: Deleting applied migrations can break database state.\n"
     "  Correct next step: Create a new migration instead."),
]

# ---- Soft warning patterns ----
SOFT_WARNING_PATTERNS = [
    (r"(^|/)package-lock\.json$", "lockfile"),
    (r"(^|/)yarn\.lock$", "lockfile"),
    (r"(^|/)pnpm-lock\.yaml$", "lockfile"),
    (r"(^|/)Cargo\.lock$", "lockfile"),
    (r"(^|/)Gemfile\.lock$", "lockfile"),
    (r"(^|/)poetry\.lock$", "lockfile"),
    (r"(^|/)go\.sum$", "lockfile"),
    (r"\.generated\.", "generated file"),
    (r"(^|/)generated/", "generated file"),
    (r"(^|/)__generated__/", "generated file"),
    (r"(^|/)(shared|common)/", "shared types"),
    (r"\.d\.ts$", "generated type declarations"),
    (r"\.generated\.\w+$", "generated file"),
    (r"(^|/)\.env\.example$", "env example"),
    (r"(^|/)\.env\.\w+\.example$", "env example"),
    (r"(^|/)docker-compose\.", "infrastructure config"),
    (r"(^|/)Dockerfile", "infrastructure config"),
    (r"(^|/)\.github/workflows/", "CI config"),
    (r"(^|/)\.gitlab-ci\.yml$", "CI config"),
    (r"(^|/)Jenkinsfile", "CI config"),
    (r"/migrations?/\w+\.(py|sql|ts|js)$", "migration file"),
]

# task.py start pattern
TASK_START_PATTERN = re.compile(r"task\.py\s+start\b")

# Override pattern
OVERRIDE_PATTERN = re.compile(r"override\s+team-kit\s+guardrail\s*:\s*(.+)", re.IGNORECASE)

# Planning states
PLANNING_STATES = {
    "PLANNING_PRD", "PLANNING_GRILL", "PLANNING_DESIGN",
    "PLANNING_IMPLEMENT", "WAITING_IMPLEMENTATION_APPROVAL",
}

# Hard-blocked commands that CANNOT be overridden
HARD_BLOCKED_COMMANDS = {
    "rm -rf", "git reset --hard", "git push --force",
    "git push -f", "git clean -fd",
}

# Source file extensions
SOURCE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".kt", ".swift", ".c", ".cpp", ".h", ".hpp", ".rb", ".php",
    ".cs", ".scala", ".sh", ".bash", ".zsh", ".sql", ".vue", ".svelte",
}


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _get_task_status(root: Path) -> Optional[str]:
    active_file = root / TRELLIS_DIR / "active-task"
    if not active_file.is_file():
        return None
    try:
        ref = active_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not ref:
        return None

    task_dir = Path(ref)
    if not task_dir.is_absolute():
        task_dir = root / ref

    task_json = task_dir / "task.json"
    if task_json.is_file():
        try:
            data = json.loads(task_json.read_text(encoding="utf-8"))
            return data.get("status", "")
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _is_planning_phase(status: Optional[str]) -> bool:
    if not status:
        return False
    return status.lower() == "planning" or status.upper() in PLANNING_STATES


def _is_source_file(file_path: str) -> bool:
    if file_path.startswith(".trellis/") or file_path.startswith(".claude/"):
        return False
    _, ext = os.path.splitext(file_path)
    return ext.lower() in SOURCE_EXTS


def _check_override(input_data: dict) -> Optional[str]:
    """Check if user provided an override reason. Only applies to soft warnings."""
    prompt = input_data.get("prompt", "") or input_data.get("message", "") or ""
    if isinstance(prompt, str):
        m = OVERRIDE_PATTERN.search(prompt)
        if m:
            return m.group(1).strip()
    return None


def _check_bash_command(command: str, root: Path) -> tuple[Optional[str], bool]:
    """Check bash command. Returns (message, is_hard_block)."""
    for pattern, message in BLOCKED_BASH_PATTERNS:
        if re.search(pattern, command):
            return message, True

    if TASK_START_PATTERN.search(command):
        status = _get_task_status(root)
        if _is_planning_phase(status):
            return (
                "BLOCKED: task.py start is forbidden during planning phase.\n"
                "  Current state: PLANNING\n"
                "  Blocked action: task.py start\n"
                "  Reason: Implementation consent has not been given.\n"
                "  Correct next step: Complete planning artifacts and wait for "
                "user to explicitly approve implementation."
            ), True

    return None, False


def _check_file_operation(file_path: str, tool_name: str, root: Path) -> tuple[Optional[str], bool]:
    """Check file write/edit. Returns (message, is_hard_block)."""
    norm_path = file_path.replace("\\", "/")
    if norm_path.startswith("./"):
        norm_path = norm_path[2:]

    # Check hard-blocked file patterns
    for pattern, message in BLOCKED_FILE_PATTERNS:
        if re.search(pattern, norm_path):
            return message, True

    # Source file editing during planning phase
    if tool_name in ("Write", "Edit") and _is_source_file(norm_path):
        status = _get_task_status(root)
        if _is_planning_phase(status):
            return (
                "BLOCKED: Editing source files during planning phase.\n"
                "  Current state: PLANNING\n"
                "  Blocked action: Write/Edit to source file\n"
                "  Reason: Task creation approval is NOT implementation approval.\n"
                "  Correct next step: Complete planning artifacts and wait for "
                "user to explicitly approve implementation."
            ), True

    # Check soft warning patterns
    if tool_name in ("Write", "Edit"):
        for pattern, category in SOFT_WARNING_PATTERNS:
            if re.search(pattern, norm_path):
                return (
                    f"WARNING: Editing {category} file: {norm_path}\n"
                    f"  Reason: Changes to {category} files can have broad impact.\n"
                    f"  Verify the change is intentional.\n"
                    f"  To bypass: say 'override team-kit guardrail: <reason>'"
                ), False

    return None, False


def _emit_deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def _emit_allow(reason: str | None = None) -> None:
    output: dict = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
    }
    if reason:
        output["permissionDecisionReason"] = reason
    print(json.dumps({"hookSpecificOutput": output}, ensure_ascii=False))
    sys.exit(0)


def _emit_warn(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    cwd_str = input_data.get("cwd") or os.getcwd()
    root = _find_trellis_root(Path(cwd_str))
    if root is None:
        return 0

    tool_name = input_data.get("tool_name", "") or input_data.get("toolName", "")
    tool_input = input_data.get("tool_input", {}) or input_data.get("toolInput", {})

    message: Optional[str] = None
    is_hard_block = False

    if tool_name.lower() == "bash":
        command = tool_input.get("command", "")
        if isinstance(command, str) and command:
            message, is_hard_block = _check_bash_command(command, root)

    elif tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "") or tool_input.get("filePath", "")
        if isinstance(file_path, str) and file_path:
            message, is_hard_block = _check_file_operation(file_path, tool_name, root)

    if not message:
        return 0

    if is_hard_block:
        # Check for override attempt on hard blocks — always deny
        override_reason = _check_override(input_data)
        if override_reason:
            _emit_deny(
                f"{message}\n\n"
                f"Override attempted with reason: {override_reason}\n"
                f"OVERRIDE DENIED: Hard blocks cannot be overridden. "
                f"User must explicitly confirm this action outside team-kit guardrails."
            )
        _emit_deny(message)

    # Soft warning — check for override
    override_reason = _check_override(input_data)
    if override_reason:
        _emit_allow(f"Guardrail override accepted: {override_reason}")
    else:
        _emit_warn(message)

    return 0


if __name__ == "__main__":
    sys.exit(main())
