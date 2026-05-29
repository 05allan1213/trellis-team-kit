#!/usr/bin/env python3
"""
Team-kit Post-Edit Reminder Hook

Reminds based on what changed after a Write/Edit operation:
- API/schema/env/config files -> remind update-spec
- Shared utils/types -> remind deep check
- Test files -> remind run affected tests
- Workflow/spec files -> remind update docs

Trigger: PostToolUse (after Write/Edit)
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

# File path patterns and their associated reminders
# Patterns use "/" as separator; _match_patterns normalizes paths and
# ensures both leading-slash and no-leading-slash forms match.
API_PATTERNS = [
    "api/", "routes/", "endpoints/", "controllers/",
    "graphql/", "resolvers/", "swagger", "openapi",
    "schema.prisma", "schema.sql", ".proto",
]

SCHEMA_PATTERNS = [
    "models/", "entities/", "types/", "schemas/",
    "migration", "schema.py", "schema.ts", "schema.js",
    "types.ts", "types.py", "interfaces.ts",
]

CONFIG_PATTERNS = [
    ".env", ".env.", "config.yaml", "config.yml", "config.json",
    "config.toml", "settings.py", "settings.ts",
    "docker-compose", "Dockerfile", ".dockerignore",
    "pyproject.toml", "package.json", "tsconfig.json",
]

SHARED_UTILS_PATTERNS = [
    "utils/", "helpers/", "lib/", "shared/", "common/",
    "core/", "foundation/",
]

TEST_PATTERNS = [
    "test_", "_test.", ".spec.", ".test.", "/tests/", "/test/",
    "/__tests__/", "/spec/",
]

WORKFLOW_SPEC_PATTERNS = [
    ".trellis/workflow", ".trellis/spec/", ".trellis/config",
]


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _match_patterns(file_path: str, patterns: list[str]) -> bool:
    """Check if a file path matches any of the given patterns.

    Normalizes the path by adding leading/trailing slashes so that
    directory-boundary patterns like "api/" match both "api/users/endpoint.py"
    and "/api/users/endpoint.py".
    """
    norm = file_path.replace("\\", "/").lower()
    # Ensure the path has a leading slash for consistent matching
    if not norm.startswith("/"):
        norm = "/" + norm
    for pattern in patterns:
        pl = pattern.lower()
        if pl.startswith("/"):
            if pl in norm:
                return True
        elif pl.endswith("/"):
            # Directory pattern: match as /<dir>/
            if f"/{pl}" in norm:
                return True
        else:
            # Plain pattern: substring match
            if pl in norm:
                return True
    return False


def _determine_reminders(file_path: str) -> list[str]:
    """Determine which reminders apply to the edited file."""
    reminders: list[str] = []

    is_api = _match_patterns(file_path, API_PATTERNS)
    is_schema = _match_patterns(file_path, SCHEMA_PATTERNS)
    is_config = _match_patterns(file_path, CONFIG_PATTERNS)
    is_shared = _match_patterns(file_path, SHARED_UTILS_PATTERNS)
    is_test = _match_patterns(file_path, TEST_PATTERNS)
    is_workflow = _match_patterns(file_path, WORKFLOW_SPEC_PATTERNS)

    if is_api or is_schema or is_config:
        reminders.append(
            "update-spec: This file may define API contracts, schemas, or configuration. "
            "Consider running trellis-update-spec to capture new patterns or contracts."
        )

    if is_shared:
        reminders.append(
            "deep-check: This file is in a shared/common area. Changes here may have "
            "broad impact. Run a thorough check after modification."
        )

    if is_test:
        reminders.append(
            "run-tests: Test file modified. Run the affected test suite to verify changes."
        )

    if is_workflow:
        reminders.append(
            "update-docs: Workflow or spec file modified. Ensure documentation is consistent."
        )

    return reminders


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

    tool_name = input_data.get("tool_name", "") or input_data.get("toolName", "")
    if tool_name not in ("Write", "Edit"):
        return 0

    tool_input = input_data.get("tool_input", {}) or input_data.get("toolInput", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("filePath", "")
    if not isinstance(file_path, str) or not file_path:
        return 0

    reminders = _determine_reminders(file_path)
    if not reminders:
        return 0

    reminder_text = "<post-edit-reminder>\n"
    reminder_text += f"File changed: {file_path}\n"
    for r in reminders:
        reminder_text += f"  - {r}\n"
    reminder_text += "</post-edit-reminder>"

    result = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reminder_text,
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
