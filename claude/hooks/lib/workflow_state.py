"""
Team-kit Workflow State Helpers.

Parse workflow state from task.json and artifact presence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

TRELLIS_DIR = ".trellis"

# States where source editing is forbidden
PLANNING_STATES = {
    "PLANNING_PRD", "PLANNING_GRILL", "PLANNING_DESIGN",
    "PLANNING_IMPLEMENT", "WAITING_IMPLEMENTATION_APPROVAL",
}


def find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def resolve_active_task(root: Path) -> Optional[dict]:
    """Return {task_dir, task_id, status} or None."""
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
    task_data = {}
    if task_json.is_file():
        try:
            task_data = json.loads(task_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "task_dir": task_dir,
        "task_id": task_data.get("id", task_dir.name),
        "status": task_data.get("status", "unknown"),
    }


def is_planning_phase(status: str) -> bool:
    return status.upper() in PLANNING_STATES or status.lower() == "planning"


def determine_phase(task_data: dict, task_dir: Path) -> str:
    status = task_data.get("status", "unknown").lower()
    if status in ("completed", "done"):
        return "DONE"
    if status == "planning":
        if not (task_dir / "prd.md").is_file():
            return "PLANNING_PRD"
        if (task_dir / "implement.md").is_file():
            return "WAITING_IMPLEMENTATION_APPROVAL"
        if (task_dir / "design.md").is_file():
            return "PLANNING_IMPLEMENT"
        return "PLANNING_GRILL"
    if status == "in_progress":
        if (task_dir / "validation").is_dir() and any((task_dir / "validation").iterdir()):
            return "VALIDATING"
        if (task_dir / "review").is_dir() and any((task_dir / "review").iterdir()):
            return "REVIEWING"
        return "IMPLEMENTING"
    return status.upper()
