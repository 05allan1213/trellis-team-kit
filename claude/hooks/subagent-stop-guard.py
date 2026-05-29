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


def _emit_warning(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SubagentStop",
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

    subagent_type = _detect_subagent_type(input_data)
    if subagent_type is None or subagent_type not in AGENTS_ALL:
        return 0

    output_text = _get_agent_output(input_data)
    if not output_text:
        # Can't validate without output — warn but don't block
        _emit_warning(
            f"<subagent-stop-guard>\n"
            f"Agent '{subagent_type}' stopped but no output text was found. "
            f"Cannot validate output format.\n"
            f"</subagent-stop-guard>"
        )
        return 0

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
        return 0

    # Build block reason
    reason = (
        f"Subagent '{agent_label}' output is missing required elements:\n\n"
    )
    for item in missing:
        reason += f"  - {item}\n"
    reason += (
        f"\nThe subagent must provide all required output elements. "
        f"Re-run the agent with explicit output format instructions."
    )

    # Researcher gets soft warning unless evidence is required
    if subagent_type == AGENT_RESEARCH:
        warning = (
            f"<subagent-format-warning>\n"
            f"Subagent '{agent_label}' output is missing elements:\n"
        )
        for item in missing:
            warning += f"  - {item}\n"
        warning += (
            f"Please ensure the research agent follows the expected output format.\n"
            f"</subagent-format-warning>"
        )
        _emit_warning(warning)
    else:
        _emit_block(reason)

    return 0


if __name__ == "__main__":
    sys.exit(main())
