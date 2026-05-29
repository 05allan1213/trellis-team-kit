#!/usr/bin/env python3
"""
Team-kit Sub-agent Stop Guard Hook

Validates subagent output format when a trellis sub-agent stops.

Validation rules:
- Implementer: must have changed files, summary, validation attempted, unresolved risks
- Checker: must have PASS/FAIL, commands run, failures, fixes
- Reviewer: must have PASS/FAIL, blocking issues, non-blocking issues, exact file/spec citations

If format is invalid, emits a warning.

Trigger: SubagentStop
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

AGENT_IMPLEMENT = "trellis-implement"
AGENT_CHECK = "trellis-check"
AGENT_RESEARCH = "trellis-research"
AGENTS_ALL = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_RESEARCH)


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _validate_implement_output(output_text: str) -> list[str]:
    """Validate implementer output format. Returns list of missing elements."""
    missing: list[str] = []
    text_lower = output_text.lower()

    if not any(kw in text_lower for kw in ("changed file", "modified file", "created file", "files changed")):
        missing.append("changed files list")
    if not any(kw in text_lower for kw in ("summary", "implemented", "what was implemented")):
        missing.append("implementation summary")
    if not any(kw in text_lower for kw in ("validation", "lint", "typecheck", "checked", "verified")):
        missing.append("validation attempted")
    if not any(kw in text_lower for kw in ("unresolved risk", "remaining concern", "open issue", "risk", "no unresolved")):
        missing.append("unresolved risks statement")

    return missing


def _validate_check_output(output_text: str) -> list[str]:
    """Validate checker output format. Returns list of missing elements."""
    missing: list[str] = []
    text_lower = output_text.lower()

    if "pass" not in text_lower and "fail" not in text_lower:
        missing.append("PASS/FAIL verdict")
    if not any(kw in text_lower for kw in ("command", "ran", "executed", "ran:", "commands")):
        missing.append("commands run")
    if "fail" in text_lower and not any(kw in text_lower for kw in ("failure", "failed", "error")):
        missing.append("failure details")
    if not any(kw in text_lower for kw in ("fix", "applied", "resolved", "corrected")):
        missing.append("fixes applied")

    return missing


def _validate_review_output(output_text: str) -> list[str]:
    """Validate reviewer output format. Returns list of missing elements."""
    missing: list[str] = []
    text_lower = output_text.lower()

    if "pass" not in text_lower and "fail" not in text_lower:
        missing.append("PASS/FAIL verdict")
    if not any(kw in text_lower for kw in ("blocking", "blocker", "critical")):
        missing.append("blocking issues")
    if not any(kw in text_lower for kw in ("non-blocking", "minor", "suggestion", "non blocking")):
        missing.append("non-blocking issues")
    # Check for file/spec citations (paths or .md references)
    has_citation = (
        "/" in output_text
        or ".md" in output_text
        or "spec" in text_lower
        or "file" in text_lower
    )
    if not has_citation:
        missing.append("exact file/spec citations")

    return missing


def _detect_subagent_type(input_data: dict) -> Optional[str]:
    """Detect which subagent type is stopping from the hook input."""
    # Check transcript or agent name in various formats
    agent_name = input_data.get("agent_name", "")
    if isinstance(agent_name, str) and agent_name in AGENTS_ALL:
        return agent_name

    subagent_type = input_data.get("subagent_type", "")
    if isinstance(subagent_type, str) and subagent_type in AGENTS_ALL:
        return subagent_type

    # Check tool_input for agent type
    tool_input = input_data.get("tool_input", {})
    if isinstance(tool_input, dict):
        for key in ("subagent_type", "subagentType", "name"):
            val = tool_input.get(key, "")
            if isinstance(val, str) and val in AGENTS_ALL:
                return val

    return None


def _get_agent_output(input_data: dict) -> str:
    """Extract the sub-agent's output text from the hook input."""
    # Various places the output might be
    for key in ("output", "result", "transcript", "message", "text"):
        val = input_data.get(key, "")
        if isinstance(val, str) and len(val) > 50:
            return val

    # Check nested structures
    result = input_data.get("result", {})
    if isinstance(result, dict):
        for key in ("output", "text", "message", "content"):
            val = result.get(key, "")
            if isinstance(val, str) and len(val) > 50:
                return val

    return ""


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
        return 0

    # Validate based on agent type
    missing: list[str] = []
    if subagent_type == AGENT_IMPLEMENT:
        missing = _validate_implement_output(output_text)
    elif subagent_type == AGENT_CHECK:
        missing = _validate_check_output(output_text)
    elif subagent_type == AGENT_RESEARCH:
        # Research agents have lighter format requirements; skip strict validation
        return 0

    if not missing:
        return 0

    warning = (
        f"<subagent-format-warning>\n"
        f"Sub-agent '{subagent_type}' output is missing required elements:\n"
    )
    for item in missing:
        warning += f"  - {item}\n"
    warning += (
        f"Please ensure the sub-agent follows the expected output format.\n"
        f"</subagent-format-warning>"
    )

    result = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStop",
            "additionalContext": warning,
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
