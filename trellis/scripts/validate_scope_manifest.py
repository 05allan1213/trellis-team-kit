#!/usr/bin/env python3
"""Validate a task's machine-readable scope contract."""
from __future__ import annotations

import json
import fnmatch
import re
import sys
from pathlib import Path
from typing import Any

LEVELS_REQUIRING_SCOPE = {"L2", "L3", "L4", "L5"}
VALID_PROFILES = {"quick", "light", "standard", "strict", "orchestrated"}
HIGH_RISK_PATTERNS = (
    r"(^|/)auth/",
    r"(^|/)authentication/",
    r"(^|/)migrations?/",
    r"(^|/)schema\.",
    r"(^|/)api/",
    r"(^|/)routes/",
    r"(^|/)endpoints/",
    r"(^|/)(shared|common)/types",
    r"(^|/)contracts?/",
    r"(^|/)proto/",
)


def _read_task_json(task_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        return None, [f"No task.json in {task_dir}"]
    try:
        data = json.loads(task_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return None, [f"Cannot parse task.json: {e}"]
    if not isinstance(data, dict):
        return None, ["task.json must contain a JSON object"]
    return data, []


def _non_empty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _normalize_scope_entry(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _is_high_risk_scope_entry(value: str) -> bool:
    normalized = _normalize_scope_entry(value)
    return any(re.search(pattern, normalized) for pattern in HIGH_RISK_PATTERNS)


def _scope_entry_allowed(entry: str, allowlist: list[str]) -> bool:
    normalized = _normalize_scope_entry(entry)
    for allowed in allowlist:
        allowed_norm = _normalize_scope_entry(allowed)
        if not allowed_norm:
            continue
        if normalized == allowed_norm:
            return True
        if normalized.startswith(allowed_norm.rstrip("/") + "/"):
            return True
        if fnmatch.fnmatchcase(normalized, allowed_norm):
            return True
        if fnmatch.fnmatchcase(allowed_norm, normalized):
            return True
    return False


def _validate_manifest_payload(
    manifest: Any,
    *,
    task_id: str,
    task_level: str,
) -> list[str]:
    if not isinstance(manifest, dict):
        return [f"Task '{task_id}': scope-manifest.json must contain a JSON object"]

    errors: list[str] = []
    version = manifest.get("version")
    if version != 1:
        errors.append(f"Task '{task_id}': scope-manifest.json version must be 1")

    level = manifest.get("level")
    if level != task_level:
        errors.append(
            f"Task '{task_id}': scope-manifest.json level '{level}' does not match task level '{task_level}'"
        )

    profile = manifest.get("profile")
    if not isinstance(profile, str) or profile not in VALID_PROFILES:
        errors.append(
            f"Task '{task_id}': scope-manifest.json profile must be one of {', '.join(sorted(VALID_PROFILES))}"
        )

    declared_paths = manifest.get("declared_paths")
    declared_globs = manifest.get("declared_globs")
    if not _non_empty_string_list(declared_paths):
        if declared_paths != []:
            errors.append(
                f"Task '{task_id}': scope-manifest.json declared_paths must be a list of strings"
            )
    if not _non_empty_string_list(declared_globs):
        if declared_globs != []:
            errors.append(
                f"Task '{task_id}': scope-manifest.json declared_globs must be a list of strings"
            )

    if not (declared_paths or declared_globs):
        errors.append(
            f"Task '{task_id}': scope-manifest.json requires declared_paths or declared_globs to be non-empty"
        )

    high_risk_allowed = manifest.get("high_risk_allowed")
    if not _non_empty_string_list(high_risk_allowed):
        if high_risk_allowed != []:
            errors.append(
                f"Task '{task_id}': scope-manifest.json high_risk_allowed must be a list of strings"
            )
    if isinstance(high_risk_allowed, list):
        high_risk_allowlist = [
            _normalize_scope_entry(item)
            for item in high_risk_allowed
            if isinstance(item, str) and item.strip()
        ]
        for entry in [*(declared_paths or []), *(declared_globs or [])]:
            if isinstance(entry, str) and _is_high_risk_scope_entry(entry) and not _scope_entry_allowed(entry, high_risk_allowlist):
                errors.append(
                    f"Task '{task_id}': high-risk declared scope '{entry}' must be covered by high_risk_allowed"
                )

    out_of_scope = manifest.get("out_of_scope")
    if not _non_empty_string_list(out_of_scope):
        if out_of_scope == []:
            errors.append(
                f"Task '{task_id}': scope-manifest.json out_of_scope must be non-empty"
            )
        else:
            errors.append(
                f"Task '{task_id}': scope-manifest.json out_of_scope must be a list of strings"
            )

    return errors


def validate_scope_manifest(
    task_dir: Path,
    *,
    require_manifest: bool = True,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not task_dir.is_dir():
        return False, [f"Task directory not found: {task_dir}"]

    task_data, task_errors = _read_task_json(task_dir)
    if task_errors:
        return False, task_errors
    assert task_data is not None

    task_id = str(task_data.get("id") or task_dir.name)
    level = str(task_data.get("level") or "")
    if level not in LEVELS_REQUIRING_SCOPE:
        return True, []

    manifest_path = task_dir / "scope-manifest.json"
    if not manifest_path.is_file():
        if require_manifest:
            return False, [
                f"Task '{task_id}' ({level}): missing required scope-manifest.json"
            ]
        return True, []

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return False, [f"Task '{task_id}': cannot parse scope-manifest.json: {e}"]

    errors.extend(
        _validate_manifest_payload(manifest, task_id=task_id, task_level=level)
    )
    return len(errors) == 0, errors


def main() -> int:
    if len(sys.argv) < 2:
        print("PASS: validate_scope_manifest.py is available")
        return 0

    task_dir = Path(sys.argv[1])
    ok, issues = validate_scope_manifest(task_dir)
    if ok:
        print(f"PASS: scope-manifest.json is valid for {task_dir}")
        return 0

    print(f"FAIL: {len(issues)} scope manifest issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
