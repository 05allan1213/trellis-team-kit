"""
Team-kit Unified Hook Output Helpers.

Provides consistent output formatting across all hooks so that
hard blocks, soft warnings, and context injection are unambiguous.

Usage:
    from lib.hook_output import block, allow, warn, additional_context
    from lib.hook_output import pretool_deny, pretool_allow, pretool_warn
"""

from __future__ import annotations

import json
import sys


def _emit(obj: dict) -> None:
    """Emit JSON to stdout and exit 0."""
    print(json.dumps(obj, ensure_ascii=False))


# -- PreToolUse helpers -------------------------------------------------------

def pretool_deny(reason: str, event_name: str = "PreToolUse") -> None:
    """Hard block a tool invocation. Returns deny decision."""
    _emit({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    })
    sys.exit(0)


def pretool_allow(reason: str | None = None, event_name: str = "PreToolUse") -> None:
    """Allow a tool invocation with optional reason."""
    output: dict = {
        "hookEventName": event_name,
        "permissionDecision": "allow",
    }
    if reason:
        output["permissionDecisionReason"] = reason
    _emit({"hookSpecificOutput": output})
    sys.exit(0)


def pretool_warn(reason: str, event_name: str = "PreToolUse") -> None:
    """Allow with a warning message."""
    _emit({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    })
    sys.exit(0)


# -- Stop / SubagentStop helpers ---------------------------------------------

def block(reason: str, event_name: str = "Stop") -> None:
    """Hard block: the session/subagent cannot proceed."""
    _emit({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "decision": "block",
            "reason": reason,
        }
    })
    sys.exit(0)


def allow(reason: str | None = None, event_name: str = "Stop") -> None:
    """Allow the action to proceed."""
    output: dict = {
        "hookEventName": event_name,
        "decision": "allow",
    }
    if reason:
        output["reason"] = reason
    _emit({"hookSpecificOutput": output})
    sys.exit(0)


def warn(context: str, event_name: str = "Stop") -> None:
    """Soft warning: action can proceed but user should be aware."""
    _emit({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": context,
        }
    })
    sys.exit(0)


def additional_context(text: str, event_name: str = "UserPromptSubmit") -> None:
    """Inject context without blocking."""
    _emit({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": text,
        }
    })
    sys.exit(0)


# -- Utility -----------------------------------------------------------------

def format_block_reason(
    current_state: str,
    violated_gate: str,
    missing_artifact: str,
    required_action: str,
) -> str:
    """Format a block reason consistently."""
    return (
        f"Cannot mark task done.\n\n"
        f"Current state: {current_state}\n"
        f"Violated: {violated_gate}\n"
        f"Missing: {missing_artifact}\n"
        f"Required next action: {required_action}"
    )
