#!/usr/bin/env python3
"""Validate Trellis config.json presence and required fields."""

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


def find_config(root: Path) -> Path | None:
    installed = root / ".trellis" / "config" / "config.json"
    if installed.is_file():
        return installed

    source = root / "trellis" / "config" / "config.json"
    if source.is_file():
        return source

    return None


def validate_config_file(path: Path) -> tuple[bool, list[str]]:
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


def main() -> int:
    cwd = Path.cwd()
    root = find_project_root(cwd)
    if root is None:
        print("FAIL: No Trellis config directory found.")
        print("  Expected: .trellis/config/ OR trellis/config/")
        return 1

    config_path = find_config(root)
    if config_path is None:
        print("FAIL: Cannot find .trellis/config/config.json or trellis/config/config.json")
        return 1

    ok, errors = validate_config_file(config_path)
    if ok:
        print(f"PASS: {config_path} is valid")
        return 0

    print(f"FAIL: {config_path} has {len(errors)} issue(s):")
    for error in errors:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
