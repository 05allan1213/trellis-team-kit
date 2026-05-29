#!/usr/bin/env python3
"""
Team-kit Pre-Compact Save State Hook

Saves current session state to {TASK_DIR}/research/session-state.md
before compaction occurs. This preserves context that would otherwise
be lost during conversation compaction.

Saved information:
- Current phase
- Decisions made
- Unresolved questions
- Last successful command
- Failed checks
- Next action

Must NOT include secrets or sensitive data.

Trigger: PreCompact
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
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

# Patterns that look like secrets -- redact from saved state
SECRET_PATTERNS = [
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "access_key", "private_key", "credentials", "auth_token",
]


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _resolve_active_task(root: Path, input_data: dict) -> Optional[Path]:
    """Resolve the active task directory path."""
    scripts_dir = root / TRELLIS_DIR / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    task_path = None
    try:
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]
        active = resolve_active_task(root, input_data)
        if active and active.task_path:
            task_path = active.task_path
    except Exception:
        pass

    if not task_path:
        active_file = root / TRELLIS_DIR / "active-task"
        if active_file.is_file():
            try:
                task_path = active_file.read_text(encoding="utf-8").strip() or None
            except OSError:
                pass

    if not task_path:
        return None

    task_dir = Path(task_path)
    if not task_dir.is_absolute():
        task_dir = root / task_path
    return task_dir if task_dir.is_dir() else None


def _read_task_json(task_dir: Path) -> dict:
    task_json = task_dir / "task.json"
    if task_json.is_file():
        try:
            return json.loads(task_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _determine_phase(task_data: dict, task_dir: Path) -> str:
    """Determine the current workflow phase from task status and artifacts."""
    status = task_data.get("status", "unknown").lower()

    if status == "planning":
        if not (task_dir / "prd.md").is_file():
            return "PLANNING_PRD"
        if (task_dir / "implement.md").is_file():
            return "WAITING_IMPLEMENTATION_APPROVAL"
        if (task_dir / "design.md").is_file():
            return "PLANNING_IMPLEMENT"
        return "PLANNING_GRILL"
    elif status == "in_progress":
        if (task_dir / "validation").is_dir():
            return "VALIDATING"
        if (task_dir / "review").is_dir():
            return "REVIEWING"
        return "IMPLEMENTING"
    elif status in ("completed", "done"):
        return "DONE"
    return status.upper()


def _collect_decisions(task_dir: Path) -> list[str]:
    """Collect documented decisions from task artifacts."""
    decisions: list[str] = []

    # Check implement.md for decisions
    implement_md = task_dir / "implement.md"
    if implement_md.is_file():
        try:
            content = implement_md.read_text(encoding="utf-8")
            # Look for decision sections
            for line in content.splitlines():
                line_stripped = line.strip()
                if line_stripped.startswith("- ") and any(
                    kw in line_stripped.lower()
                    for kw in ("decided", "decision", "chose", "chosen", "selected", "will use")
                ):
                    decisions.append(line_stripped)
        except OSError:
            pass

    # Check design.md for decisions
    design_md = task_dir / "design.md"
    if design_md.is_file():
        try:
            content = design_md.read_text(encoding="utf-8")
            for line in content.splitlines():
                line_stripped = line.strip()
                if line_stripped.startswith("- ") and any(
                    kw in line_stripped.lower()
                    for kw in ("decided", "decision", "chose", "chosen", "selected", "will use")
                ):
                    decisions.append(line_stripped)
        except OSError:
            pass

    return decisions


def _collect_unresolved_questions(task_dir: Path) -> list[str]:
    """Collect open questions from task artifacts."""
    questions: list[str] = []

    for artifact in ("prd.md", "design.md", "implement.md"):
        artifact_path = task_dir / artifact
        if not artifact_path.is_file():
            continue
        try:
            content = artifact_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line_stripped = line.strip()
                if "?" in line_stripped and (
                    line_stripped.startswith("- ")
                    or line_stripped.startswith("* ")
                    or "open question" in line_stripped.lower()
                    or "todo" in line_stripped.lower()
                    or "tbd" in line_stripped.lower()
                ):
                    questions.append(f"[{artifact}] {line_stripped}")
        except OSError:
            pass

    return questions


def _collect_failed_checks(task_dir: Path) -> list[str]:
    """Collect failed check/review results."""
    failed: list[str] = []

    # Check validation directory
    validation_dir = task_dir / "validation"
    if validation_dir.is_dir():
        for vf in validation_dir.iterdir():
            if vf.is_file() and vf.suffix == ".md":
                try:
                    content = vf.read_text(encoding="utf-8").lower()
                    if "fail" in content:
                        failed.append(f"validation/{vf.name}")
                except OSError:
                    pass

    # Check review directory
    review_dir = task_dir / "review"
    if review_dir.is_dir():
        for rf in review_dir.iterdir():
            if rf.is_file() and rf.suffix == ".md":
                try:
                    content = rf.read_text(encoding="utf-8").lower()
                    if "fail" in content:
                        failed.append(f"review/{rf.name}")
                except OSError:
                    pass

    return failed


def _get_git_status(repo_root: Path) -> str:
    """Get brief git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=3, cwd=str(repo_root),
        )
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
            return f"{len(lines)} changed files" if lines else "clean"
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        pass
    return "unknown"


def _redact_secrets(text: str) -> str:
    """Remove lines that look like they contain secrets."""
    lines = text.splitlines()
    redacted: list[str] = []
    for line in lines:
        line_lower = line.lower()
        if any(pattern in line_lower for pattern in SECRET_PATTERNS):
            # Redact the value but keep the key
            if "=" in line:
                key = line.split("=", 1)[0]
                redacted.append(f"{key}=***REDACTED***")
            elif ":" in line:
                key = line.split(":", 1)[0]
                redacted.append(f"{key}: ***REDACTED***")
            else:
                redacted.append("***REDACTED***")
        else:
            redacted.append(line)
    return "\n".join(redacted)


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        input_data = {}

    cwd_str = input_data.get("cwd") or os.getcwd()
    root = _find_trellis_root(Path(cwd_str))
    if root is None:
        return 0

    task_dir = _resolve_active_task(root, input_data)
    if task_dir is None:
        return 0  # No active task, nothing to save

    task_data = _read_task_json(task_dir)
    task_id = task_data.get("id", task_dir.name)
    phase = _determine_phase(task_data, task_dir)
    decisions = _collect_decisions(task_dir)
    unresolved = _collect_unresolved_questions(task_dir)
    failed_checks = _collect_failed_checks(task_dir)
    git_status = _get_git_status(root)

    # Ensure research directory exists
    research_dir = task_dir / "research"
    research_dir.mkdir(parents=True, exist_ok=True)

    # Build session state file
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    state_lines = [
        "# Session State (Auto-saved before compaction)",
        "",
        f"Saved: {now}",
        f"Task: {task_id}",
        f"Phase: {phase}",
        f"Git status: {git_status}",
        "",
        "## Decisions Made",
    ]
    if decisions:
        for d in decisions:
            state_lines.append(d)
    else:
        state_lines.append("(none recorded)")

    state_lines.append("")
    state_lines.append("## Unresolved Questions")
    if unresolved:
        for q in unresolved:
            state_lines.append(q)
    else:
        state_lines.append("(none)")

    state_lines.append("")
    state_lines.append("## Failed Checks")
    if failed_checks:
        for f in failed_checks:
            state_lines.append(f"- {f}")
    else:
        state_lines.append("(none)")

    state_lines.append("")
    state_lines.append("## Next Action")
    next_actions = {
        "PLANNING_PRD": "Continue writing prd.md with trellis-brainstorm.",
        "PLANNING_GRILL": "Run trellis-grill-me to challenge the PRD.",
        "PLANNING_DESIGN": "Write design.md for the task.",
        "PLANNING_IMPLEMENT": "Write implement.md with Review Gate Contract.",
        "WAITING_IMPLEMENTATION_APPROVAL": "Wait for user to approve implementation.",
        "IN_PROGRESS": "Run trellis-before-dev, then implement.",
        "BEFORE_DEV": "Read all artifacts and specs.",
        "IMPLEMENTING": "Continue implementation or dispatch trellis-implement.",
        "CHECKING": "Run trellis-check to validate.",
        "REVIEWING": "Run remaining review gates.",
        "UPDATING_SPEC": "Run trellis-update-spec; record decision.",
        "COMMITTING": "Draft and execute commit plan.",
        "MERGE_REVIEWING": "Run trellis-merge-review.",
        "VALIDATING": "Run build/test and record results.",
        "FINISHING": "Run trellis-finish-work.",
        "DONE": "Task complete.",
    }
    state_lines.append(next_actions.get(phase, "Follow workflow.md for current step."))

    state_content = _redact_secrets("\n".join(state_lines))

    # Write session state file
    state_file = research_dir / "session-state.md"
    try:
        state_file.write_text(state_content, encoding="utf-8")
    except OSError as e:
        print(
            f"[pre-compact-save-state] WARN: Could not write session state: {e}",
            file=sys.stderr,
        )
        return 0

    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": (
                f"<compact-state-saved>\n"
                f"Session state saved to {state_file.relative_to(root)}\n"
                f"Phase: {phase}\n"
                f"</compact-state-saved>"
            ),
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
