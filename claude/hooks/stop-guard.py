#!/usr/bin/env python3
"""
Team-kit Stop Guard Hook — v0.3 Hardened

Prevents premature "done" claims. Returns BLOCK (not additionalContext)
when hard violations are detected.

Hard blocks:
- Active task exists but check not passed
- Selected review gate missing / FAIL / no PASS/FAIL
- Spec update decision missing
- Validation missing / FAIL
- Task not archived but assistant says done
- Task in planning but assistant claims implementation completed
- Implementation approval missing but source files were edited

Soft warnings:
- Optional review gate skipped with reason
- Validation skipped with explicit reason
- Spec update decision says no with reason

Trigger: Stop
"""
from __future__ import annotations

import json
import os
import re
import subprocess
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

# Import shared artifact helpers from lib/
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR / "lib"))

from task_artifacts import (  # type: ignore[import-not-found]
    GATE_FILE_MAP,
    check_review_gate,
    check_validation,
    parse_selected_gates,
)

# Keywords that indicate assistant is claiming completion
DONE_KEYWORDS = re.compile(
    r"\b(done|finished|completed|all set|可以交付|已完成|任务完成|task complete|"
    r"task is done|ready to finish|wrapping up)\b",
    re.IGNORECASE,
)

PLANNING_STATES = {
    "PLANNING_PRD", "PLANNING_GRILL", "PLANNING_DESIGN",
    "PLANNING_IMPLEMENT", "WAITING_IMPLEMENTATION_APPROVAL",
}


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _resolve_active_task(root: Path) -> Optional[dict]:
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


def _check_spec_update(task_dir: Path) -> str:
    """Check spec update decision. Returns 'present', 'missing'."""
    finish_md = task_dir / "finish.md"
    if not finish_md.is_file():
        return "missing"
    try:
        content = finish_md.read_text(encoding="utf-8").lower()
    except OSError:
        return "missing"
    if "spec update decision" in content:
        return "present"
    return "missing"


def _run_task_validator(root: Path, task_dir: Path, script_name: str) -> Optional[str]:
    script = root / TRELLIS_DIR / "scripts" / script_name
    if not script.is_file():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(script), str(task_dir)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=10, cwd=str(root),
        )
        if result.returncode != 0:
            output = (result.stdout or "").strip()
            if output:
                return output
            return f"{script_name} failed (exit code {result.returncode})"
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
        return f"{script_name} error: {e}"
    return None


def _detect_done_intent(input_data: dict) -> bool:
    """Check if the assistant's response contains done-intent language."""
    # Check various fields that might contain the assistant's final message
    for field in ("message", "text", "content", "output", "result"):
        val = input_data.get(field, "")
        if isinstance(val, str) and DONE_KEYWORDS.search(val):
            return True

    # Check nested
    result = input_data.get("result", {})
    if isinstance(result, dict):
        for field in ("message", "text", "content", "output"):
            val = result.get(field, "")
            if isinstance(val, str) and DONE_KEYWORDS.search(val):
                return True

    return False


def _check_source_edits_during_planning(root: Path) -> bool:
    """Check if source files were edited (git diff shows changes outside .trellis/)."""
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
                if line and not line.startswith(".trellis/") and not line.startswith(".claude/"):
                    return True
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        pass
    return False


def _emit_block(reason: str) -> None:
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "Stop",
        }
    }, ensure_ascii=False))
    sys.exit(0)


def _emit_warning(text: str) -> None:
    print(json.dumps({
        "decision": "allow",
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": text,
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

    task_info = _resolve_active_task(root)
    if task_info is None:
        return 0  # No active task, nothing to guard

    status = task_info.get("status", "unknown")
    task_id = task_info.get("task_id", "unknown")
    task_dir = task_info["task_dir"]

    # Already done — nothing to guard
    if status.lower() in ("completed", "done"):
        return 0

    # Detect done intent
    claiming_done = _detect_done_intent(input_data)

    hard_blocks: list[str] = []
    soft_warnings: list[str] = []

    # --- Planning phase checks ---
    if status.lower() == "planning" or status.upper() in PLANNING_STATES:
        if _check_source_edits_during_planning(root):
            hard_blocks.append(
                "CONSENT VIOLATION: Source files were edited during the planning phase. "
                "Task creation approval is NOT implementation approval.\n"
                "  → To fix: Revert source changes with 'git checkout -- <file>' "
                "and wait for user to explicitly approve implementation."
            )
        if claiming_done:
            hard_blocks.append(
                "Task is still in planning. Implementation has not started.\n"
                "  → To fix: Complete planning artifacts (prd.md, implement.md), "
                "then ask user to approve implementation before claiming done."
            )

    # --- In-progress gate checks ---
    if status.lower() == "in_progress":
        check_file = task_dir / "validation" / "check-results.md"
        check_done = False
        if check_file.is_file():
            try:
                c = check_file.read_text(encoding="utf-8").lower()
                check_done = "- [x] pass" in c or "- [x] fail" in c
            except OSError:
                pass

        if not check_done:
            hard_blocks.append(
                "Check gate: NOT PASSED.\n"
                "  → To fix: Dispatch trellis-checker sub-agent or run "
                "'/trellis:check' to produce validation/check-results.md with a PASS verdict."
            )

        # Selected review gates
        implement_md = task_dir / "implement.md"
        selected_gates = parse_selected_gates(implement_md)

        for gate in selected_gates:
            result = check_review_gate(task_dir, gate)
            if result == "missing":
                gate_file = GATE_FILE_MAP.get(gate, "?")
                hard_blocks.append(
                    f"Selected review gate '{gate}' is missing (no review file found).\n"
                    f"  → To fix: Run the review agent to create '{gate_file}', "
                    f"or edit implement.md to deselect this gate."
                )
            elif result == "fail":
                gate_file = GATE_FILE_MAP.get(gate, "?")
                hard_blocks.append(
                    f"Selected review gate '{gate}' FAILED.\n"
                    f"  → To fix: Read '{gate_file}' for blocking issues, "
                    f"fix them in code, re-run trellis-check, then re-run this review gate."
                )
            elif result == "no-verdict":
                gate_file = GATE_FILE_MAP.get(gate, "?")
                hard_blocks.append(
                    f"Selected review gate '{gate}' has no PASS/FAIL verdict.\n"
                    f"  → To fix: Open '{gate_file}' and ensure it has "
                    f"checked checkbox verdict ('- [x] pass' or '- [x] fail')."
                )

        # Validation check
        validation = check_validation(task_dir)
        if validation["build"] == "missing" and validation["test"] == "missing":
            hard_blocks.append(
                "Validation missing: no build or test results recorded.\n"
                "  → To fix: Run build/test commands and record results in "
                "validation/test-results.md. Fill in ## Build and ## Test sections "
                "with a checked checkbox verdict ('- [x] pass' or '- [x] fail')."
            )
        elif validation["build"] == "fail":
            hard_blocks.append(
                "Build FAILED.\n"
                "  → To fix: Run build command, read error output, fix build issues, "
                "then update validation/test-results.md ## Build section to PASS."
            )
        elif validation["test"] == "fail":
            hard_blocks.append(
                "Tests FAILED.\n"
                "  → To fix: Run test command, read failure output, fix test failures, "
                "then update validation/test-results.md ## Test section to PASS."
            )

        if validation["ready"] == "no":
            hard_blocks.append(
                "Validation says 'Ready for finish-work: no'.\n"
                "  → To fix: Address the issues listed in validation/test-results.md, "
                "then change 'Ready for finish-work?' to '- [x] yes'."
            )
        elif validation["ready"] == "missing":
            soft_warnings.append(
                "Validation results exist but 'Ready for finish-work?' is not marked.\n"
                "  → To fix: Add '## Ready for finish-work?' section to "
                "validation/test-results.md with '- [x] yes' or '- [x] no'."
            )

        # Spec update decision
        spec_decision = _check_spec_update(task_dir)
        if spec_decision == "missing":
            hard_blocks.append(
                "Spec update decision missing.\n"
                "  → To fix: Run trellis-update-spec skill, then record the decision "
                "in finish.md by adding a '## Spec Update Decision' section with "
                "'Need spec update? - [ ] yes / - [ ] no' and your reason."
            )

        for validator in ("validate_task.py", "validate_review_gates.py"):
            validator_output = _run_task_validator(root, task_dir, validator)
            if validator_output:
                hard_blocks.append(
                    f"{validator} FAILED:\n{validator_output}\n"
                    f"  → To fix: Run 'python3 .trellis/scripts/{validator} {task_dir}' "
                    f"to see detailed errors, then address each one."
                )

    # --- Emit results ---
    if hard_blocks:
        reason = f"Cannot mark task '{task_id}' as done.\n\n"
        reason += f"Current state: {status.upper()}\n\n"
        for i, b in enumerate(hard_blocks, 1):
            reason += f"{i}. {b}\n"
        reason += "\nResolve all blocking issues before finishing."
        _emit_block(reason)

    if soft_warnings:
        warning_text = "<stop-guard-warning>\n"
        warning_text += f"Task '{task_id}' soft warnings:\n"
        for w in soft_warnings:
            warning_text += f"  - {w}\n"
        warning_text += "</stop-guard-warning>"
        _emit_warning(warning_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
