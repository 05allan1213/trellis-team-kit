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

# Review gate file mapping (canonical)
GATE_FILE_MAP: dict[str, str] = {
    "trellis-check": "review/check-review.md",
    "trellis-spec-review": "review/spec-review.md",
    "trellis-code-review": "review/code-review.md",
    "trellis-code-architecture-review": "review/architecture-review.md",
    "trellis-improve-codebase-architecture deep-review": "review/architecture-deep-review.md",
    "trellis-merge-review": "review/merge-review.md",
}

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


def _parse_selected_gates(implement_md: Path) -> list[str]:
    """Parse selected gates from implement.md Review Gate Contract."""
    if not implement_md.is_file():
        return []
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return []

    gates: list[str] = []
    in_selected = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("selected gates:"):
            in_selected = True
            continue
        if in_selected:
            if stripped.startswith("- [") and "]" in stripped:
                gate = stripped.split("] ", 1)[-1].strip()
                if gate:
                    gates.append(gate)
            elif not stripped.startswith("-"):
                in_selected = False
    return gates


def _check_review_gate(task_dir: Path, gate_name: str) -> str:
    """Return 'pass', 'fail', 'missing', or 'no-verdict'."""
    file_rel = GATE_FILE_MAP.get(gate_name)
    if not file_rel:
        return "missing"
    gate_file = task_dir / file_rel
    if not gate_file.is_file():
        return "missing"
    try:
        content = gate_file.read_text(encoding="utf-8").lower()
    except OSError:
        return "missing"

    # Check for Status section with PASS/FAIL
    has_status_section = "status:" in content
    if not has_status_section:
        return "no-verdict"

    # Look for checked PASS or FAIL markers
    has_pass = bool(re.search(r"-\s*\[x\]\s*pass", content))
    has_fail = bool(re.search(r"-\s*\[x\]\s*fail", content))

    if has_fail:
        return "fail"
    if has_pass:
        return "pass"
    return "no-verdict"


def _check_validation(task_dir: Path) -> dict:
    """Check validation status. Returns dict with build/test/smoke/ready."""
    results: dict = {"build": "missing", "test": "missing", "smoke": "missing", "ready": "missing"}

    validation_dir = task_dir / "validation"
    if not validation_dir.is_dir():
        return results

    results_file = validation_dir / "results.md"
    if not results_file.is_file():
        return results

    try:
        content = results_file.read_text(encoding="utf-8").lower()
    except OSError:
        return results

    for check in ("build", "test", "smoke"):
        section_start = content.find(f"## {check}")
        if section_start == -1:
            continue
        section = content[section_start:section_start + 500]
        if "- [x] pass" in section:
            results[check] = "pass"
        elif "- [x] fail" in section:
            results[check] = "fail"
        elif "skipped with reason" in section:
            results[check] = "skipped"

    if "ready for finish-work?" in content:
        if "- [x] yes" in content:
            results["ready"] = "yes"
        elif "- [x] no" in content:
            results["ready"] = "no"

    return results


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
                "Task creation approval is NOT implementation approval. "
                "Revert source changes and wait for implementation consent."
            )
        if claiming_done:
            hard_blocks.append(
                "Task is still in planning. Implementation has not started. "
                "Do NOT claim done on an incomplete task."
            )

    # --- In-progress gate checks ---
    if status.lower() == "in_progress":
        check_file = task_dir / "validation" / "check-results.md"
        check_done = False
        if check_file.is_file():
            try:
                c = check_file.read_text(encoding="utf-8").lower()
                check_done = "pass" in c or "status:" in c
            except OSError:
                pass

        if not check_done:
            hard_blocks.append("Check gate: NOT PASSED. Run trellis-check before claiming done.")

        # Selected review gates
        implement_md = task_dir / "implement.md"
        selected_gates = _parse_selected_gates(implement_md)

        for gate in selected_gates:
            result = _check_review_gate(task_dir, gate)
            if result == "missing":
                hard_blocks.append(
                    f"Selected review gate '{gate}' is missing (no review file found). "
                    f"Run the review agent or disable the gate with reason."
                )
            elif result == "fail":
                hard_blocks.append(
                    f"Selected review gate '{gate}' FAILED. "
                    f"Return to IMPLEMENTING, fix issues, re-check, re-review."
                )
            elif result == "no-verdict":
                hard_blocks.append(
                    f"Selected review gate '{gate}' has no PASS/FAIL verdict. "
                    f"Reviewer must output explicit Status: PASS or FAIL."
                )

        # Validation check
        validation = _check_validation(task_dir)
        if validation["build"] == "missing" and validation["test"] == "missing":
            hard_blocks.append(
                "Validation missing: no build or test results recorded. "
                "Run build/test and record results in validation/results.md."
            )
        elif validation["build"] == "fail":
            hard_blocks.append("Build FAILED. Fix build issues before finishing.")
        elif validation["test"] == "fail":
            hard_blocks.append("Tests FAILED. Fix test failures before finishing.")

        if validation["ready"] == "no":
            hard_blocks.append(
                "Validation says 'Ready for finish-work: no'. "
                "Address remaining issues before finishing."
            )
        elif validation["ready"] == "missing":
            soft_warnings.append(
                "Validation results exist but 'Ready for finish-work?' is not marked. "
                "Mark it explicitly before finishing."
            )

        # Spec update decision
        spec_decision = _check_spec_update(task_dir)
        if spec_decision == "missing":
            hard_blocks.append(
                "Spec update decision missing. Run trellis-update-spec and "
                "record the decision in finish.md."
            )

        for validator in ("validate_task.py", "validate_review_gates.py"):
            validator_output = _run_task_validator(root, task_dir, validator)
            if validator_output:
                hard_blocks.append(
                    f"{validator} FAILED:\n{validator_output}"
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
