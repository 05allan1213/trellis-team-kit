#!/usr/bin/env python3
"""
Team-kit Subagent Stop Guard Hook — v0.3 Hardened

Validates subagent output format when a trellis subagent stops.
Returns BLOCK (not additionalContext) when required output elements are missing.

Validation rules:
- Implementer: must have changed files, summary, validation attempted, no-commit
- Checker: must have PASS/FAIL, commands run, failures, fixes
- Reviewer: must have PASS/FAIL, blocking issues, non-blocking issues, citations
- Spec-updater: must have decision, need-spec-update, reason
- Researcher: must have question, sources, findings, decision impact, output

Trigger: SubagentStop
"""
from __future__ import annotations

import json
import os
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

# Canonical agent names
AGENT_IMPLEMENT = "trellis-implementer"
AGENT_CHECK = "trellis-checker"
AGENT_RESEARCH = "trellis-researcher"
AGENT_SPEC_REVIEWER = "trellis-spec-reviewer"
AGENT_CODE_REVIEWER = "trellis-code-reviewer"
AGENT_ARCHITECTURE_REVIEWER = "trellis-architecture-reviewer"
AGENT_ARCHITECTURE_DEEP_REVIEWER = "trellis-architecture-deep-reviewer"
AGENT_MERGE_REVIEWER = "trellis-merge-reviewer"
AGENT_SPEC_UPDATER = "trellis-spec-updater"

AGENTS_IMPLEMENT_CHECK = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_RESEARCH)
AGENTS_REVIEW = (
    AGENT_SPEC_REVIEWER, AGENT_CODE_REVIEWER, AGENT_ARCHITECTURE_REVIEWER,
    AGENT_ARCHITECTURE_DEEP_REVIEWER, AGENT_MERGE_REVIEWER,
)
AGENTS_ALL = AGENTS_IMPLEMENT_CHECK + AGENTS_REVIEW + (AGENT_SPEC_UPDATER,)
AGENTS_REQUIRE_AGENT_RESULT = (AGENT_IMPLEMENT, AGENT_CHECK) + AGENTS_REVIEW
AGENT_RESULT_REQUIRED_FIELDS = (
    "version",
    "agent",
    "status",
    "changed_files",
    "validation",
    "blocking_issues",
)


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _detect_subagent_type(input_data: dict) -> Optional[str]:
    """Detect which subagent type is stopping from the hook input.
    Official field is agent_type first, then backward compatible with others.
    """
    agent_name = (
        input_data.get("agent_type")
        or input_data.get("agent_name")
        or input_data.get("subagent_type")
        or ""
    )
    if isinstance(agent_name, str) and agent_name in AGENTS_ALL:
        return agent_name

    tool_input = input_data.get("tool_input", {})
    if isinstance(tool_input, dict):
        for key in ("subagent_type", "subagentType", "name", "agent_type", "agentType"):
            val = tool_input.get(key, "")
            if isinstance(val, str) and val in AGENTS_ALL:
                return val

    return None


def _get_agent_output(input_data: dict) -> str:
    """Extract the subagent's output text from the hook input.
    Official field is last_assistant_message first, then backward compatible.
    """
    for key in ("last_assistant_message", "output", "result", "transcript", "message", "text"):
        val = input_data.get(key, "")
        if isinstance(val, str) and len(val) > 50:
            return val

    result = input_data.get("result", {})
    if isinstance(result, dict):
        for key in ("last_assistant_message", "output", "text", "message", "content"):
            val = result.get(key, "")
            if isinstance(val, str) and len(val) > 50:
                return val

    return ""


def _get_current_task_dir(root: Path) -> Optional[Path]:
    active_file = root / TRELLIS_DIR / "active-task"
    if not active_file.is_file():
        return None
    try:
        raw = active_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    task_dir = Path(raw)
    if not task_dir.is_absolute():
        task_dir = root / task_dir
    return task_dir if task_dir.is_dir() else None


def _validate_agent_result_file(path: Path, subagent_type: str) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path.name}: invalid JSON ({e})"]

    if not isinstance(payload, dict):
        return [f"{path.name}: must contain a JSON object"]

    missing = [field for field in AGENT_RESULT_REQUIRED_FIELDS if field not in payload]
    if missing:
        return [f"{path.name}: missing required field(s): {', '.join(missing)}"]

    errors: list[str] = []
    if payload.get("version") != 1:
        errors.append(f"{path.name}: version must be 1")
    if payload.get("agent") != subagent_type:
        errors.append(f"{path.name}: agent must be {subagent_type}")
    if payload.get("status") not in ("PASS", "FAIL", "REDESIGN-REQUIRED", "BLOCKED"):
        errors.append(f"{path.name}: invalid status")
    changed_files = payload.get("changed_files")
    if not isinstance(changed_files, list):
        errors.append(f"{path.name}: changed_files must be a list of objects")
    else:
        for index, item in enumerate(changed_files, 1):
            if not isinstance(item, dict):
                errors.append(f"{path.name}: changed_files must be a list of objects")
                continue
            if not isinstance(item.get("path"), str) or not item.get("path", "").strip():
                errors.append(f"{path.name}: changed_files item {index} missing path")
            if not isinstance(item.get("summary"), str) or not item.get("summary", "").strip():
                errors.append(f"{path.name}: changed_files item {index} missing summary")
    if not isinstance(payload.get("validation"), list):
        errors.append(f"{path.name}: validation must be a list")
    if not isinstance(payload.get("blocking_issues"), list):
        errors.append(f"{path.name}: blocking_issues must be a list")
    return errors


def _find_agent_result_errors(task_dir: Path, subagent_type: str) -> list[str]:
    results_dir = task_dir / "agent-results"
    if not results_dir.is_dir():
        return [f"missing {results_dir}/ for subagent result JSON"]

    files = sorted(results_dir.glob("*.json"))
    if not files:
        return [f"missing agent-results/*.json for subagent '{subagent_type}'"]

    candidate_errors: list[str] = []
    saw_candidate = False
    for path in files:
        matches_name = path.name.startswith(f"{subagent_type}-")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            if matches_name:
                saw_candidate = True
                candidate_errors.append(f"{path.name}: invalid JSON ({e})")
            continue
        matches_payload = isinstance(payload, dict) and payload.get("agent") == subagent_type
        if not matches_name and not matches_payload:
            continue
        saw_candidate = True
        errors = _validate_agent_result_file(path, subagent_type)
        if not errors:
            return []
        candidate_errors.extend(errors)

    if not saw_candidate:
        return [f"missing agent-results JSON for subagent '{subagent_type}'"]
    return candidate_errors


# -- Validators --------------------------------------------------------------

def _validate_implement_output(output_text: str) -> list[str]:
    """Validate implementer output. Returns list of missing elements."""
    missing: list[str] = []
    text_lower = output_text.lower()

    if not any(kw in text_lower for kw in (
        "changed file", "modified file", "created file", "files changed",
        "file changed", "files modified",
    )):
        missing.append("Changed Files list")

    if not any(kw in text_lower for kw in (
        "summary", "implemented", "what was implemented", "implementation summary",
    )):
        missing.append("Implementation Summary")

    if not any(kw in text_lower for kw in (
        "validation", "lint", "typecheck", "checked", "verified", "tested",
    )):
        missing.append("Validation Attempted")

    if not any(kw in text_lower for kw in (
        "unresolved risk", "remaining concern", "open issue", "risk",
        "no unresolved", "follow-up", "followup",
    )):
        missing.append("Risks / Follow-ups")

    if not any(kw in text_lower for kw in (
        "did not commit", "no commit", "not committed", "without commit",
    )):
        missing.append("Did not commit confirmation")

    return missing


def _validate_check_output(output_text: str) -> list[str]:
    """Validate checker output. Returns list of missing elements."""
    missing: list[str] = []
    text_lower = output_text.lower()

    has_pass = any(kw in text_lower for kw in ("- [x] pass", "[x] pass", "status: pass"))
    has_fail = any(kw in text_lower for kw in ("- [x] fail", "[x] fail", "status: fail"))
    if not has_pass and not has_fail:
        missing.append("Status: PASS or FAIL")

    if not any(kw in text_lower for kw in ("command", "ran", "executed", "ran:", "commands")):
        missing.append("Commands run")

    if has_fail and not any(kw in text_lower for kw in ("failure", "failed", "error")):
        missing.append("Failure details")

    if not any(kw in text_lower for kw in ("fix", "applied", "resolved", "corrected", "required fix")):
        missing.append("Required fixes (if FAIL) or fixes applied")

    if not any(kw in text_lower for kw in ("file", "inspected", "checked")):
        missing.append("Files inspected")

    return missing


def _validate_review_output(output_text: str) -> list[str]:
    """Validate reviewer output. Returns list of missing elements."""
    missing: list[str] = []
    text_lower = output_text.lower()

    has_pass = any(kw in text_lower for kw in ("- [x] pass", "[x] pass", "status: pass"))
    has_fail = any(kw in text_lower for kw in ("- [x] fail", "[x] fail", "status: fail"))
    if not has_pass and not has_fail:
        missing.append("Status: PASS or FAIL")

    if not any(kw in text_lower for kw in ("scope reviewed", "scope", "reviewed:")):
        missing.append("Scope reviewed")

    if not any(kw in text_lower for kw in ("blocking", "blocker", "critical")):
        missing.append("Blocking issues")

    if not any(kw in text_lower for kw in ("non-blocking", "minor", "suggestion", "non blocking")):
        missing.append("Non-blocking issues")

    if not any(kw in text_lower for kw in ("required fix", "fix required", "must fix", "need to fix")):
        if has_fail:
            missing.append("Required fixes (mandatory when FAIL)")

    return missing


def _validate_spec_updater_output(output_text: str) -> list[str]:
    """Validate spec-updater output. Returns list of missing elements."""
    missing: list[str] = []
    text_lower = output_text.lower()

    if "spec update decision" not in text_lower:
        missing.append("Spec Update Decision section")

    if not any(kw in text_lower for kw in ("need spec update", "spec update:")):
        missing.append("Need spec update: yes/no")

    if not any(kw in text_lower for kw in ("reason", "because", "justification")):
        missing.append("Reason for decision")

    return missing


def _validate_research_output(output_text: str) -> list[str]:
    """Validate researcher output. Returns list of missing elements."""
    missing: list[str] = []
    text_lower = output_text.lower()

    if not any(kw in text_lower for kw in ("research question", "question", "query")):
        missing.append("Research Question")

    if not any(kw in text_lower for kw in ("source", "inspected", "file", "searched")):
        missing.append("Files / Sources inspected")

    if not any(kw in text_lower for kw in ("finding", "result", "discovered", "found")):
        missing.append("Findings")

    if not any(kw in text_lower for kw in ("impact", "decision", "conclusion", "recommendation")):
        missing.append("Decision impact")

    return missing


# -- Output helpers -----------------------------------------------------------

def _emit_block(reason: str) -> None:
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "SubagentStop",
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

    subagent_type = _detect_subagent_type(input_data)
    if subagent_type is None or subagent_type not in AGENTS_ALL:
        return 0

    output_text = _get_agent_output(input_data)
    if not output_text:
        _emit_block(
            f"Subagent '{subagent_type}' stopped but no output text was found. "
            f"Cannot validate output format. Subagent must produce output before stopping."
        )

    # Validate based on agent type
    missing: list[str] = []
    agent_label = subagent_type

    if subagent_type == AGENT_IMPLEMENT:
        missing = _validate_implement_output(output_text)
    elif subagent_type == AGENT_CHECK:
        missing = _validate_check_output(output_text)
    elif subagent_type in AGENTS_REVIEW:
        missing = _validate_review_output(output_text)
    elif subagent_type == AGENT_SPEC_UPDATER:
        missing = _validate_spec_updater_output(output_text)
    elif subagent_type == AGENT_RESEARCH:
        missing = _validate_research_output(output_text)

    if not missing:
        if subagent_type in AGENTS_REQUIRE_AGENT_RESULT:
            task_dir = _get_current_task_dir(root)
            if task_dir is None:
                _emit_block(
                    f"Subagent '{subagent_type}' stopped but the active Trellis task "
                    f"could not be resolved. Cannot validate agent-results JSON."
                )
            result_errors = _find_agent_result_errors(task_dir, subagent_type)
            if result_errors:
                reason = (
                    f"Subagent '{subagent_type}' must write a machine-readable "
                    f"agent-results JSON before stopping:\n\n"
                )
                for item in result_errors:
                    reason += f"  - {item}\n"
                reason += (
                    f"\nWrite {task_dir}/agent-results/"
                    f"{subagent_type}-<timestamp>.json with version, agent, status, "
                    f"changed_files, validation, and blocking_issues."
                )
                _emit_block(reason)
        return 0

    reason = (
        f"Subagent '{agent_label}' output is missing required elements:\n\n"
    )
    for item in missing:
        reason += f"  - {item}\n"
    reason += (
        f"\nThe subagent must provide all required output elements. "
        f"Re-run the agent with explicit output format instructions."
    )
    _emit_block(reason)


if __name__ == "__main__":
    sys.exit(main())
