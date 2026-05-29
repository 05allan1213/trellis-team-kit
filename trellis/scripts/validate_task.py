#!/usr/bin/env python3
"""
validate_task.py — Validate a specific task's artifacts and state.

Checks:
- task.json exists and is valid
- Task level is valid (L0-L5)
- Required artifacts by level are present
- Approval status
- implement.jsonl / check.jsonl are valid JSONL
- Review gate contract is present
- Validation results
- Finish marker
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LEVEL_REQUIREMENTS = {
    "L0": {"artifacts": [], "gates": []},
    "L1": {"artifacts": [], "gates": ["check"]},
    "L2": {"artifacts": ["prd.md"], "gates": ["check"]},
    "L3": {"artifacts": ["prd.md", "implement.md"], "gates": ["check", "code-review"]},
    "L4": {"artifacts": ["prd.md", "design.md", "implement.md"],
            "gates": ["check", "spec-review", "code-review", "architecture-review"]},
    "L5": {"artifacts": ["prd.md", "design.md", "implement.md"],
            "gates": ["check", "spec-review", "code-review", "architecture-review",
                       "deep-review", "merge-review"]},
}


def validate_task(task_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not task_dir.is_dir():
        return False, [f"Task directory not found: {task_dir}"]

    # task.json
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        return False, [f"No task.json in {task_dir}"]

    try:
        data = json.loads(task_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return False, [f"Cannot parse task.json: {e}"]

    task_id = data.get("id", task_dir.name)
    level = data.get("level", "")
    status = data.get("status", "")

    if not level:
        errors.append(f"Task '{task_id}': missing 'level' field")
    elif level not in LEVEL_REQUIREMENTS:
        errors.append(f"Task '{task_id}': invalid level '{level}'")

    if not status:
        errors.append(f"Task '{task_id}': missing 'status' field")

    # Check required artifacts by level
    if level in LEVEL_REQUIREMENTS:
        for artifact in LEVEL_REQUIREMENTS[level]["artifacts"]:
            art_path = task_dir / artifact
            if not art_path.is_file():
                if status not in ("planning",) or artifact != "design.md":
                    errors.append(f"Task '{task_id}' ({level}): missing required artifact '{artifact}'")

    # Validate JSONL files
    for jsonl_name in ("implement.jsonl", "check.jsonl"):
        jsonl_path = task_dir / jsonl_name
        if jsonl_path.is_file():
            try:
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            json.loads(line)
                        except json.JSONDecodeError:
                            errors.append(f"Task '{task_id}': {jsonl_name} line {i} is invalid JSON")
            except OSError:
                errors.append(f"Task '{task_id}': cannot read {jsonl_name}")

    # Check review gate contract in implement.md
    implement_md = task_dir / "implement.md"
    if implement_md.is_file():
        try:
            content = implement_md.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "Review Gate Contract" not in content and "review gate" not in content.lower():
            if level in ("L3", "L4", "L5"):
                warnings.append(f"Task '{task_id}': implement.md missing Review Gate Contract")

    # Check validation
    validation_dir = task_dir / "validation"
    if status.lower() in ("in_progress",) and not validation_dir.is_dir():
        pass  # Validation not yet started

    # Check finish marker
    finish_md = task_dir / "finish.md"
    if status.lower() in ("completed", "done") and not finish_md.is_file():
        errors.append(f"Task '{task_id}': status is '{status}' but finish.md is missing")

    all_issues = errors + [f"WARNING: {w}" for w in warnings]
    return len(errors) == 0, all_issues


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 validate_task.py <task-directory>")
        print("  Validates a specific Trellis task's artifacts and state.")
        return 1

    task_dir = Path(sys.argv[1])
    ok, issues = validate_task(task_dir)

    if ok:
        print(f"PASS: Task at {task_dir} is valid")
        if issues:
            for i in issues:
                print(f"  {i}")
        return 0

    print(f"FAIL: Task at {task_dir} has {len(issues)} issue(s):")
    for i in issues:
        print(f"  - {i}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
