#!/usr/bin/env python3
"""
Team-kit Stop Guard Hook

Prevents premature "done" claims. Checks that all required gates have
passed before allowing a task to be marked as complete.

Checks:
- Active task exists?
- Check passed?
- Review gates passed?
- Spec update decision recorded?
- Build/test done?
- Task archived?
- Planning phase and source was edited? -> warn about consent violation

Trigger: Stop
"""
from __future__ import annotations

import json
import os
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

# States where source editing is forbidden
PLANNING_STATES = {"planning", "PLANNING", "PLANNING_PRD", "PLANNING_GRILL",
                   "PLANNING_DESIGN", "PLANNING_IMPLEMENT", "WAITING_IMPLEMENTATION_APPROVAL"}


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _resolve_active_task(root: Path, input_data: dict) -> Optional[dict]:
    """Resolve active task, return dict with task info."""
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


def _check_gate_status(task_dir: Path) -> dict:
    """Check which gates have passed based on artifact presence."""
    gates: dict[str, bool] = {}

    # Check gate: look for PASS in check output or validation
    validation_dir = task_dir / "validation"
    if validation_dir.is_dir():
        test_results = validation_dir / "test-results.md"
        if test_results.is_file():
            try:
                content = test_results.read_text(encoding="utf-8").lower()
                gates["check"] = "pass" in content
            except OSError:
                gates["check"] = False
        else:
            gates["check"] = False
    else:
        gates["check"] = False

    # Review gates: look for PASS in review outputs
    review_dir = task_dir / "review"
    if review_dir.is_dir():
        all_pass = True
        has_reviews = False
        for review_file in review_dir.iterdir():
            if review_file.is_file() and review_file.suffix == ".md":
                has_reviews = True
                try:
                    content = review_file.read_text(encoding="utf-8").lower()
                    if "fail" in content and "pass" not in content.split("fail")[0][-50:]:
                        all_pass = False
                        break
                except OSError:
                    all_pass = False
                    break
        gates["review"] = all_pass if has_reviews else None  # None = no reviews required
    else:
        gates["review"] = None

    # Spec update decision: check finish.md for Spec Update Decision
    finish_md = task_dir / "finish.md"
    if finish_md.is_file():
        try:
            content = finish_md.read_text(encoding="utf-8").lower()
            gates["spec_update"] = "spec update decision" in content
        except OSError:
            gates["spec_update"] = False
    else:
        gates["spec_update"] = False

    # Build/test: check validation/test-results.md
    if validation_dir.is_dir():
        test_results = validation_dir / "test-results.md"
        commands_md = validation_dir / "commands.md"
        gates["build_test"] = test_results.is_file() or commands_md.is_file()
    else:
        gates["build_test"] = False

    return gates


def _check_planning_source_violation(root: Path, task_info: dict) -> bool:
    """Check if source files were edited during planning phase.

    This is a best-effort check using git diff. Returns True if a
    consent violation is suspected.
    """
    status = task_info.get("status", "")
    if status.lower() not in ("planning",):
        return False

    # Check if there are modified source files (not in .trellis/)
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=3, cwd=str(root),
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line and not line.startswith(".trellis/"):
                    return True
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        pass

    return False


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

    task_info = _resolve_active_task(root, input_data)
    if task_info is None:
        return 0  # No active task, nothing to guard

    status = task_info.get("status", "unknown")
    task_id = task_info.get("task_id", "unknown")

    # If task is already completed/done, no guard needed
    if status.lower() in ("completed", "done"):
        return 0

    warnings: list[str] = []

    # Check for planning-phase source editing (consent violation)
    if _check_planning_source_violation(root, task_info):
        warnings.append(
            "CONSENT VIOLATION: Source files were edited during the planning phase. "
            "Task creation approval is NOT implementation approval. "
            "Revert source changes and wait for implementation consent."
        )

    # For in_progress tasks, check gates
    if status.lower() == "in_progress":
        gates = _check_gate_status(task_info["task_dir"])

        if not gates.get("check"):
            warnings.append("Check gate: NOT PASSED. Run trellis-check before claiming done.")
        if gates.get("review") is False:
            warnings.append("Review gates: NOT PASSED. All selected review gates must pass.")
        if not gates.get("spec_update"):
            warnings.append("Spec update decision: NOT RECORDED. Run trellis-update-spec first.")
        if not gates.get("build_test"):
            warnings.append("Build/test: NOT DONE. Run build/test or record why it cannot be executed.")

    # If status is planning, remind that task is not done
    if status.lower() == "planning":
        warnings.append(
            "Task is still in planning. Implementation has not started. "
            "Do NOT claim done on an incomplete task."
        )

    if not warnings:
        return 0

    warning_text = "<stop-guard-warning>\n"
    warning_text += f"Task '{task_id}' is NOT done. Outstanding issues:\n"
    for w in warnings:
        warning_text += f"  - {w}\n"
    warning_text += (
        "Do NOT claim the task is complete until all gates pass and "
        "finish-work succeeds.\n"
        "</stop-guard-warning>"
    )

    result = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": warning_text,
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
