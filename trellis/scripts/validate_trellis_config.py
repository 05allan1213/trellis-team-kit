#!/usr/bin/env python3
"""Validate Trellis config files presence and required fields."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def find_project_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis" / "config").is_dir():
            return cur
        if (cur / "trellis" / "config").is_dir():
            return cur
        cur = cur.parent
    return None


def find_config_dir(root: Path) -> Path | None:
    installed = root / ".trellis" / "config"
    if installed.is_dir():
        return installed

    source = root / "trellis" / "config"
    if source.is_dir():
        return source

    return None


def validate_config_json(path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not path.is_file():
        return False, [f"{path} does not exist"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, [f"Cannot parse {path}: {exc}"]

    if not isinstance(data, dict):
        return False, ["config.json must contain a JSON object"]

    codex = data.get("codex")
    if not isinstance(codex, dict):
        errors.append("codex must be a JSON object")
    else:
        dispatch_mode = codex.get("dispatch_mode")
        if not isinstance(dispatch_mode, str) or not dispatch_mode.strip():
            errors.append("codex.dispatch_mode must be a non-empty string")

    return len(errors) == 0, errors


def validate_config_file(path: Path) -> tuple[bool, list[str]]:
    """Backward-compatible wrapper for callers that validate only config.json."""
    return validate_config_json(path)


def validate_workflow_profiles(path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not path.is_file():
        return False, [f"{path} does not exist"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, [f"Cannot parse {path}: {exc}"]

    if not isinstance(data, dict):
        return False, ["workflow_profiles.json must contain a JSON object"]

    if data.get("version") != 1:
        errors.append("workflow_profiles.version must be 1")

    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        errors.append("workflow_profiles.profiles must be a JSON object")
        return False, errors

    expected = {
        "quick": ["L1"],
        "light": ["L2"],
        "standard": ["L3"],
        "strict": ["L4"],
        "orchestrated": ["L5"],
    }
    for name, levels in expected.items():
        profile = profiles.get(name)
        if not isinstance(profile, dict):
            errors.append(f"workflow profile '{name}' missing or not an object")
            continue
        if profile.get("levels") != levels:
            errors.append(f"workflow profile '{name}' must map to levels {levels}")
        if not isinstance(profile.get("execution"), str) or not profile.get("execution", "").strip():
            errors.append(f"workflow profile '{name}' must define execution")
        gates = profile.get("required_gates")
        if not isinstance(gates, list) or not gates:
            errors.append(f"workflow profile '{name}' must define required_gates")

    return len(errors) == 0, errors


def main() -> int:
    cwd = Path.cwd()
    root = find_project_root(cwd)
    if root is None:
        print("FAIL: No Trellis config directory found.")
        print("  Expected: .trellis/config/ OR trellis/config/")
        return 1

    config_dir = find_config_dir(root)
    if config_dir is None:
        print("FAIL: Cannot find .trellis/config/ or trellis/config/")
        return 1

    checks = [
        (config_dir / "config.json", validate_config_json),
        (config_dir / "workflow_profiles.json", validate_workflow_profiles),
    ]
    all_errors: list[str] = []
    for path, validator in checks:
        ok, errors = validator(path)
        if not ok:
            all_errors.extend(errors)

    if not all_errors:
        print(f"PASS: {config_dir} config files are valid")
        return 0

    print(f"FAIL: {config_dir} has {len(all_errors)} issue(s):")
    for error in all_errors:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
