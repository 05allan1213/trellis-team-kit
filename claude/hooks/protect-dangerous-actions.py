#!/usr/bin/env python3
"""
Team-kit Protect Dangerous Actions Hook

Protects against dangerous operations by blocking or warning.

Blocked/warned operations:
- rm -rf, git reset --hard, git clean -fd
- Force push
- Deleting migrations
- Editing .env or secrets
- Running task.py start without implementation consent
- Write/Edit to source files during planning phase

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

# Dangerous bash command patterns
BLOCKED_BASH_PATTERNS = [
    (r"\brm\s+.*-rf\b", "rm -rf detected. Use targeted file deletion instead."),
    (r"\brm\s+-rf\b", "rm -rf detected. Use targeted file deletion instead."),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard is blocked. Use git stash or git checkout instead."),
    (r"\bgit\s+clean\s+-fd\b", "git clean -fd is blocked. Remove files individually."),
    (r"\bgit\s+push\s+.*--force\b", "Force push is blocked. Use regular push or rebase."),
    (r"\bgit\s+push\s+-f\b", "Force push is blocked. Use regular push or rebase."),
    (r"\bgit\s+push\s+--force-with-lease\b", "Force push is blocked. Use regular push."),
]

# Dangerous file patterns
BLOCKED_FILE_PATTERNS = [
    (r"^\.env", ".env files must not be edited through AI tools."),
    (r"^\.env\.", ".env files must not be edited through AI tools."),
    (r"secrets?\.", "Secrets files must not be edited through AI tools."),
    (r"credentials?\.", "Credentials files must not be edited through AI tools."),
    (r"/migrations/\d+_", "Deleting migrations is blocked. Create a new migration instead."),
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


def _is_planning_phase(status: Optional[str]) -> bool:
    """Check if the current task status indicates planning phase."""
    if not status:
        return False
    return status.lower() in ("planning",)


def _is_source_file(file_path: str) -> bool:
    """Check if a file path looks like a source file (not a .trellis artifact)."""
    # Files under .trellis/ are artifacts, not source
    if file_path.startswith(".trellis/"):
        return False
    # Common source extensions
    source_exts = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
        ".kt", ".swift", ".c", ".cpp", ".h", ".hpp", ".rb", ".php",
        ".cs", ".scala", ".sh", ".bash", ".zsh", ".sql",
    }
    _, ext = os.path.splitext(file_path)
    return ext.lower() in source_exts


def _check_bash_command(command: str, root: Path, input_data: dict) -> Optional[str]:
    """Check a bash command for dangerous patterns. Returns warning or None."""
    # Check blocked patterns
    for pattern, message in BLOCKED_BASH_PATTERNS:
        if re.search(pattern, command):
            return message

    # Check task.py start without implementation consent
    if TASK_START_PATTERN.search(command):
        status = _get_task_status(root, input_data)
        if _is_planning_phase(status):
            return (
                "BLOCKED: task.py start is forbidden during planning phase. "
                "Implementation consent has not been given. "
                "Wait for the user to explicitly approve implementation."
            )

    return None


def _check_file_operation(file_path: str, tool_name: str, root: Path, input_data: dict) -> Optional[str]:
    """Check a file write/edit for dangerous patterns. Returns warning or None."""
    # Normalize path
    norm_path = file_path.replace("\\", "/")
    if norm_path.startswith("./"):
        norm_path = norm_path[2:]

    # Check blocked file patterns
    for pattern, message in BLOCKED_FILE_PATTERNS:
        if re.search(pattern, norm_path):
            return message

    # Check source file editing during planning
    if tool_name in ("Write", "Edit") and _is_source_file(norm_path):
        status = _get_task_status(root, input_data)
        if _is_planning_phase(status):
            return (
                "WARNING: Editing source files during planning phase. "
                "Task creation approval is NOT implementation approval. "
                "Source editing requires explicit implementation consent."
            )

    return None


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

    warning: Optional[str] = None

    # Check Bash commands
    if tool_name.lower() == "bash":
        command = tool_input.get("command", "")
        if isinstance(command, str) and command:
            warning = _check_bash_command(command, root, input_data)

    # Check Write/Edit operations
    elif tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "") or tool_input.get("filePath", "")
        if isinstance(file_path, str) and file_path:
            warning = _check_file_operation(file_path, tool_name, root, input_data)

    if not warning:
        return 0

    # Determine severity: "BLOCKED" -> deny, "WARNING" -> allow with warning
    is_blocked = warning.startswith("BLOCKED")

    if is_blocked:
        permission_decision = "deny"
    else:
        permission_decision = "allow"

    warning_block = (
        f"<dangerous-action-guard>\n"
        f"{warning}\n"
        f"</dangerous-action-guard>"
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission_decision,
            "additionalContext": warning_block,
        }
    }

    # For denied operations, include denial reason
    if is_blocked:
        output["hookSpecificOutput"]["denialReason"] = warning

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
