#!/usr/bin/env python3
"""Validate that spec-update detector targets resolve to real spec files."""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def find_scripts_dir(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        scripts = cur / ".trellis" / "scripts"
        if scripts.is_dir():
            return scripts
        scripts = cur / "trellis" / "scripts"
        if scripts.is_dir():
            return scripts
        cur = cur.parent
    return None


def find_spec_dir(scripts_dir: Path) -> Path | None:
    installed_spec_dir = scripts_dir.parent / "spec"
    if installed_spec_dir.is_dir():
        return installed_spec_dir

    source_spec_dir = scripts_dir.parent.parent / "marketplace" / "specs" / "web-app"
    if source_spec_dir.is_dir():
        return source_spec_dir

    return None


def collect_spec_targets(detector_path: Path) -> list[str]:
    tree = ast.parse(detector_path.read_text(encoding="utf-8"))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "add_candidate":
            continue
        if len(node.args) < 3:
            continue
        target_node = node.args[2]
        if isinstance(target_node, ast.Constant) and isinstance(target_node.value, str):
            if target_node.value.startswith("spec/"):
                targets.add(target_node.value)
    return sorted(targets)


def validate_spec_update_targets(
    detector_path: Path,
    spec_dir: Path,
) -> tuple[bool, list[str], list[str]]:
    targets = collect_spec_targets(detector_path)
    issues: list[str] = []

    if not targets:
        issues.append(f"{detector_path.name}: no spec/* targets found")
        return False, targets, issues

    for target in targets:
        rel_path = target.removeprefix("spec/")
        if not (spec_dir / rel_path).is_file():
            issues.append(f"{target}: target file does not exist under {spec_dir}")

    return not issues, targets, issues


def main() -> int:
    scripts_dir = find_scripts_dir(Path.cwd())
    if scripts_dir is None:
        print("FAIL: Cannot find .trellis/scripts/ or trellis/scripts/ directory")
        return 1

    detector_path = scripts_dir / "detect_spec_update_candidates.py"
    if not detector_path.is_file():
        print(f"FAIL: detector script not found: {detector_path}")
        return 1

    spec_dir = find_spec_dir(scripts_dir)
    if spec_dir is None:
        print("FAIL: Cannot find installed or source spec directory")
        return 1

    ok, targets, issues = validate_spec_update_targets(detector_path, spec_dir)
    if ok:
        print(
            "PASS: spec update detector targets exist "
            f"({len(targets)} spec target(s) under {spec_dir})"
        )
        return 0

    print(f"FAIL: {len(issues)} spec update target issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
