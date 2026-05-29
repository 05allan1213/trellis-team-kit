#!/usr/bin/env python3
"""
Team-kit Protect Dangerous Actions Hook

Protects against dangerous operations by blocking or warning.

Hard block:
- rm -rf, git reset --hard, git clean -fd
- Force push
- Editing .env or secrets
- Deleting migrations
- Running task.py start without implementation consent
- Write/Edit to source files during planning phase (before approval)

Soft warning:
- Editing lockfiles
- Editing generated files
- Modifying shared types
- Modifying env/config files
- Changing migrations

Bypass (soft warnings only):
- User says "override team-kit guardrail: <reason>"
- AI proceeds despite the warning
- Hard blocks require explicit user confirmation

Trigger: PreToolUse (before Bash, Write, Edit tools)
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Force UTF-8 on Windows
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
     "  Correct next step: Use targeted file deletion instead.\n"
     "  How to unblock: User must explicitly confirm this action."),
    (r"\brm\s+-rf\b",
     "BLOCKED: rm -rf detected.\n"
     "  Blocked action: Recursive force delete\n"
     "  Reason: Irreversible file deletion.\n"
     "  Correct next step: Use targeted file deletion instead.\n"
     "  How to unblock: User must explicitly confirm this action."),
    (r"\bgit\s+reset\s+--hard\b",
     "BLOCKED: git reset --hard detected.\n"
     "  Blocked action: Hard reset\n"
     "  Reason: Destroys uncommitted work irreversibly.\n"
     "  Correct next step: Use git stash or git checkout instead.\n"
     "  How to unblock: User must explicitly confirm this action."),
    (r"\bgit\s+clean\s+-fd\b",
     "BLOCKED: git clean -fd detected.\n"
     "  Blocked action: Force delete untracked files\n"
     "  Reason: Irreversibly removes untracked files.\n"
     "  Correct next step: Remove files individually.\n"
     "  How to unblock: User must explicitly confirm this action."),
    (r"\bgit\s+push\s+.*--force\b",
     "BLOCKED: Force push detected.\n"
     "  Blocked action: Force push\n"
     "  Reason: Overwrites remote history, can destroy teammates' work.\n"
     "  Correct next step: Use regular push or rebase.\n"
     "  How to unblock: User must explicitly confirm force push."),
    (r"\bgit\s+push\s+-f\b",
     "BLOCKED: Force push detected.\n"
     "  Blocked action: Force push\n"
     "  Reason: Overwrites remote history, can destroy teammates' work.\n"
     "  Correct next step: Use regular push or rebase.\n"
     "  How to unblock: User must explicitly confirm force push."),
    (r"\bgit\s+push\s+--force-with-lease\b",
     "BLOCKED: Force push detected.\n"
     "  Blocked action: Force push (--force-with-lease)\n"
     "  Reason: Overwrites remote history.\n"
     "  Correct next step: Use regular push.\n"
     "  How to unblock: User must explicitly confirm force push."),
]

# ---- Hard block: dangerous file patterns ----
BLOCKED_FILE_PATTERNS = [
    (r"^\.env$",
     "BLOCKED: Editing .env file.\n"
     "  Blocked action: Write/Edit to .env\n"
     "  Reason: .env files may contain secrets and credentials.\n"
     "  Correct next step: Edit .env manually, or use .env.example.\n"
     "  How to unblock: User must explicitly confirm editing secrets."),
    (r"^\.env\.",
     "BLOCKED: Editing .env file.\n"
     "  Blocked action: Write/Edit to .env.*\n"
     "  Reason: .env files may contain secrets and credentials.\n"
     "  Correct next step: Edit manually, or use .env.example.\n"
     "  How to unblock: User must explicitly confirm editing secrets."),
    (r"secrets?\.",
     "BLOCKED: Editing secrets file.\n"
     "  Blocked action: Write/Edit to secrets file\n"
     "  Reason: Secrets files must not be edited through AI tools.\n"
     "  Correct next step: Edit manually.\n"
     "  How to unblock: User must explicitly confirm editing secrets."),
    (r"credentials?\.",
     "BLOCKED: Editing credentials file.\n"
     "  Blocked action: Write/Edit to credentials file\n"
     "  Reason: Credentials files must not be edited through AI tools.\n"
     "  Correct next step: Edit manually.\n"
     "  How to unblock: User must explicitly confirm editing credentials."),
    (r"/migrations/\d+_",
     "BLOCKED: Deleting migration file.\n"
     "  Blocked action: Delete/Edit migration\n"
     "  Reason: Deleting applied migrations can break database state.\n"
     "  Correct next step: Create a new migration instead.\n"
     "  How to unblock: User must explicitly confirm migration deletion."),
]

# ---- Soft warning: patterns that trigger a warning but don't block ----
SOFT_WARNING_FILE_PATTERNS = [
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
    (r"(^|/)shared/", "shared types"),
    (r"(^|/)common/", "shared types"),
    (r"\.d\.ts$", "generated file"),
    (r"\.generated\.\w+$", "generated file"),
]

# task.py start without consent
TASK_START_PATTERN = re.compile(r"task\.py\s+start\b")


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _get_task_status(root: Path, input_data: dict) -> Optional[str]:
    """Get current task status from active task resolver."""
    scripts_dir = root / TRELLIS_DIR / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]
        active = resolve_active_task(root, input_data)
        if active and active.task_path:
            task_dir = Path(active.task_path)
            if not task_dir.is_absolute():
                task_dir = root / task_dir
            task_json = task_dir / "task.json"
            if task_json.is_file():
                try:
                    data = json.loads(task_json.read_text(encoding="utf-8"))
                    return data.get("status", "")
                except (json.JSONDecodeError, OSError):
                    pass
    except Exception:
        pass

    # Fallback
    active_file = root / TRELLIS_DIR / "active-task"
    if active_file.is_file():
        try:
            ref = active_file.read_text(encoding="utf-8").strip()
            if ref:
                task_dir = root / ref
                task_json = task_dir / "task.json"
                if task_json.is_file():
                    try:
                        data = json.loads(task_json.read_text(encoding="utf-8"))
                        return data.get("status", "")
                    except (json.JSONDecodeError, OSError):
                        pass
        except OSError:
            pass
    return None


# States where source editing is forbidden (all planning sub-phases + waiting approval)
PLANNING_STATES = {"planning", "PLANNING", "PLANNING_PRD", "PLANNING_GRILL",
                   "PLANNING_DESIGN", "PLANNING_IMPLEMENT", "WAITING_IMPLEMENTATION_APPROVAL"}


def _is_planning_phase(status: Optional[str]) -> bool:
    """Check if the current task status indicates planning or pre-approval phase."""
    if not status:
        return False
    return status.lower() in ("planning",) or status.upper() in PLANNING_STATES


def _is_source_file(file_path: str) -> bool:
    """Check if a file path looks like a source file (not a .trellis artifact)."""
    if file_path.startswith(".trellis/"):
        return False
    source_exts = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
        ".kt", ".swift", ".c", ".cpp", ".h", ".hpp", ".rb", ".php",
        ".cs", ".scala", ".sh", ".bash", ".zsh", ".sql",
    }
    _, ext = os.path.splitext(file_path)
    return ext.lower() in source_exts


def _check_soft_warning(file_path: str) -> Optional[str]:
    """Check if a file matches soft warning patterns. Returns category or None."""
    norm = file_path.replace("\\", "/")
    for pattern, category in SOFT_WARNING_FILE_PATTERNS:
        if re.search(pattern, norm):
            return category
    return None


def _check_bash_command(command: str, root: Path, input_data: dict) -> tuple[Optional[str], bool]:
    """Check a bash command for dangerous patterns. Returns (message, is_hard_block)."""
    # Check hard-blocked patterns
    for pattern, message in BLOCKED_BASH_PATTERNS:
        if re.search(pattern, command):
            return message, True

    # Check task.py start without implementation consent
    if TASK_START_PATTERN.search(command):
        status = _get_task_status(root, input_data)
        if _is_planning_phase(status):
            return (
                "BLOCKED: task.py start is forbidden during planning phase.\n"
                "  Current state: PLANNING (task status = planning)\n"
                "  Blocked action: task.py start\n"
                "  Reason: Implementation consent has not been given.\n"
                "  Correct next step: Complete planning artifacts and wait for user to explicitly approve implementation.\n"
                "  How to unblock: User must say \"start implementation\" / \"approve implementation\" / \"begin coding\"."
            ), True

    return None, False


def _check_file_operation(file_path: str, tool_name: str, root: Path, input_data: dict) -> tuple[Optional[str], bool]:
    """Check a file write/edit for dangerous patterns. Returns (message, is_hard_block)."""
    norm_path = file_path.replace("\\", "/")
    if norm_path.startswith("./"):
        norm_path = norm_path[2:]

    # Check hard-blocked file patterns
    for pattern, message in BLOCKED_FILE_PATTERNS:
        if re.search(pattern, norm_path):
            return message, True

    # Check source file editing during planning (hard block after approval missing)
    if tool_name in ("Write", "Edit") and _is_source_file(norm_path):
        status = _get_task_status(root, input_data)
        if _is_planning_phase(status):
            return (
                "BLOCKED: Editing source files during planning phase.\n"
                "  Current state: PLANNING (task status = planning)\n"
                "  Blocked action: Write/Edit to source file\n"
                "  Reason: Task creation approval is NOT implementation approval.\n"
                "  Correct next step: Complete planning artifacts (prd.md, design.md, implement.md) and wait for user to explicitly approve implementation.\n"
                "  How to unblock: User must say \"start implementation\" / \"approve implementation\" / \"begin coding\"."
            ), True

    # Check soft warning patterns
    if tool_name in ("Write", "Edit"):
        category = _check_soft_warning(norm_path)
        if category:
            return (
                "WARNING: Editing {category} file: {path}\n"
                "  Current state: Editing a {category}\n"
                "  Reason: Changes to {category} files can have broad impact.\n"
                "  Correct next step: Verify the change is intentional and understand the impact.\n"
                "  How to bypass: User says \"override team-kit guardrail: <reason>\" to proceed.\n"
                "  This is a soft warning — the action is allowed."
            ).format(category=category, path=norm_path), False

    return None, False


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

    # Check Bash commands
    if tool_name.lower() == "bash":
        command = tool_input.get("command", "")
        if isinstance(command, str) and command:
            message, is_hard_block = _check_bash_command(command, root, input_data)

    # Check Write/Edit operations
    elif tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "") or tool_input.get("filePath", "")
        if isinstance(file_path, str) and file_path:
            message, is_hard_block = _check_file_operation(file_path, tool_name, root, input_data)

    if not message:
        return 0

    if is_hard_block:
        permission_decision = "deny"
    else:
        permission_decision = "allow"

    guard_type = "hard-block" if is_hard_block else "soft-warning"
    warning_block = (
        f"<dangerous-action-guard type=\"{guard_type}\">\n"
        f"{message}\n"
        f"</dangerous-action-guard>"
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission_decision,
            "additionalContext": warning_block,
        }
    }

    if is_hard_block:
        output["hookSpecificOutput"]["denialReason"] = message

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
