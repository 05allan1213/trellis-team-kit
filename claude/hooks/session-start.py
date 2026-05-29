#!/usr/bin/env python3
"""
Team-kit Session Start Hook

Injects compact project context and task status at session start.
Reads task.json for active task status. Keeps output short.

Trigger: SessionStart
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Force UTF-8 on Windows to avoid encoding errors with non-ASCII content.
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


def _find_trellis_root(start: Path) -> Optional[Path]:
    """Walk up from start to find directory containing .trellis/."""
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _run_git(repo_root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=3, cwd=str(repo_root),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _resolve_active_task(repo_root: Path, input_data: dict) -> Optional[dict]:
    """Resolve the active task via common.active_task if available, else task.json scan."""
    scripts_dir = repo_root / TRELLIS_DIR / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]
        active = resolve_active_task(repo_root, input_data)
        if active and active.task_path:
            return {"task_path": active.task_path, "stale": active.stale}
    except Exception:
        pass

    # Fallback: read .trellis/active-task if it exists
    active_file = repo_root / TRELLIS_DIR / "active-task"
    if active_file.is_file():
        try:
            ref = active_file.read_text(encoding="utf-8").strip()
            if ref:
                return {"task_path": ref, "stale": False}
        except OSError:
            pass
    return None


def _collect_spec_indexes(trellis_dir: Path) -> list[str]:
    """Collect spec index paths under .trellis/spec/."""
    paths: list[str] = []
    spec_dir = trellis_dir / "spec"
    if not spec_dir.is_dir():
        return paths

    guides_index = spec_dir / "guides" / "index.md"
    if guides_index.is_file():
        paths.append(".trellis/spec/guides/index.md")

    for sub in sorted(spec_dir.iterdir()):
        if not sub.is_dir() or sub.name.startswith(".") or sub.name == "guides":
            continue
        index_file = sub / "index.md"
        if index_file.is_file():
            paths.append(f".trellis/spec/{sub.name}/index.md")
            continue
        for nested in sorted(sub.iterdir()):
            if nested.is_dir():
                nested_index = nested / "index.md"
                if nested_index.is_file():
                    paths.append(f".trellis/spec/{sub.name}/{nested.name}/index.md")
    return paths


def _determine_workflow_phase(status: str, task_dir: Path) -> str:
    """Map task.json status + artifact presence to workflow phase."""
    status_lower = status.lower() if status else ""

    if status_lower in ("completed", "done"):
        return "DONE"
    if status_lower == "planning":
        # Check which planning sub-phase based on artifacts
        has_prd = (task_dir / "prd.md").is_file()
        has_design = (task_dir / "design.md").is_file()
        has_implement = (task_dir / "implement.md").is_file()
        if not has_prd:
            return "PLANNING_PRD"
        if has_implement:
            return "WAITING_IMPLEMENTATION_APPROVAL"
        if has_design:
            return "PLANNING_IMPLEMENT"
        return "PLANNING_GRILL"
    if status_lower == "in_progress":
        # Check sub-phase within execution
        if (task_dir / "validation").is_dir() and list((task_dir / "validation").iterdir()):
            return "VALIDATING"
        if (task_dir / "review").is_dir() and list((task_dir / "review").iterdir()):
            return "REVIEWING"
        return "IMPLEMENTING"

    return status_lower.upper() if status_lower else "UNKNOWN"


def _determine_next_action(phase: str) -> str:
    """Return the recommended next action for the given phase."""
    actions = {
        "NO_TASK": "Classify the current request (L0-L5) before creating a task.",
        "PLANNING_PRD": "Load trellis-brainstorm; write prd.md. Do NOT edit source code.",
        "PLANNING_GRILL": "Load trellis-grill-me; challenge the PRD. Do NOT edit source code.",
        "PLANNING_DESIGN": "Write design.md for complex tasks. Do NOT edit source code.",
        "PLANNING_IMPLEMENT": "Write implement.md with Review Gate Contract. Do NOT edit source code.",
        "WAITING_IMPLEMENTATION_APPROVAL": "Wait for user to explicitly approve implementation. Do NOT edit source code.",
        "IN_PROGRESS": "Run trellis-before-dev, then implement.",
        "BEFORE_DEV": "Read all task artifacts and specs before writing code.",
        "IMPLEMENTING": "Dispatch trellis-implement sub-agent or implement inline.",
        "CHECKING": "Dispatch trellis-check sub-agent.",
        "REVIEWING": "Run review gates per Review Gate Contract.",
        "UPDATING_SPEC": "Run trellis-update-spec; record decision.",
        "COMMITTING": "Inspect dirty state, draft commit plan, confirm with user.",
        "MERGE_REVIEWING": "Run trellis-merge-review for complex tasks.",
        "VALIDATING": "Run build/test; record results in validation/test-results.md.",
        "FINISHING": "Run trellis-finish-work to archive and wrap up.",
        "DONE": "Task complete. No further action needed.",
    }
    return actions.get(phase, "Follow the matching per-turn workflow-state.")


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        input_data = {}

    cwd_str = input_data.get("cwd") or os.getcwd()
    repo_root = _find_trellis_root(Path(cwd_str))
    if repo_root is None:
        return 0  # Not a Trellis project

    trellis_dir = repo_root / TRELLIS_DIR

    # Git state
    branch = _run_git(repo_root, ["branch", "--show-current"]) or "(detached)"
    dirty_lines = [
        line for line in _run_git(repo_root, ["status", "--porcelain"]).splitlines()
        if line.strip()
    ]
    dirty_state = "clean" if not dirty_lines else "dirty"

    # Active task
    active = _resolve_active_task(repo_root, input_data)
    if active and active.get("task_path"):
        task_ref = active["task_path"]
        task_dir = Path(task_ref)
        if not task_dir.is_absolute():
            task_dir = repo_root / task_ref
        task_json_path = task_dir / "task.json"
        task_data = _read_json(task_json_path) if task_json_path.is_file() else {}
        task_id = task_data.get("id", task_dir.name)
        task_status = task_data.get("status", "unknown")
        active_task = str(task_dir.relative_to(repo_root)) if task_dir.is_relative_to(repo_root) else str(task_dir)
        workflow_phase = _determine_workflow_phase(task_status, task_dir)
        next_action = _determine_next_action(workflow_phase)
    else:
        active_task = "none"
        task_status = "NO_TASK"
        workflow_phase = "NO_TASK"
        next_action = _determine_next_action("NO_TASK")

    # Spec indexes
    spec_indexes = _collect_spec_indexes(trellis_dir)
    spec_line = " ".join(spec_indexes) if spec_indexes else "(none found)"

    # Build compact context block
    output_text = (
        f"<team-kit-session>\n"
        f"repo: {repo_root.name}\n"
        f"branch: {branch}\n"
        f"dirty_state: {dirty_state}\n"
        f"active_task: {active_task}\n"
        f"task_status: {task_status}\n"
        f"workflow_phase: {workflow_phase}\n"
        f"next_action: {next_action}\n"
        f"spec_indexes: {spec_line}\n"
        f"</team-kit-session>"
    )

    result = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": output_text,
        }
    }

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
