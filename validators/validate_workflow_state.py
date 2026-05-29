#!/usr/bin/env python3
"""Validate workflow state consistency for trellis-team-kit.

Checks that task state is consistent with the actual state of artifacts
and files. Outputs PASS or FAIL with specific violations.

Usage:
    python3 validate_workflow_state.py <task-dir>
    python3 validate_workflow_state.py .trellis/tasks/05-29-my-feature/
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def read_file(path: Path) -> str | None:
    """Read file contents, return None if file does not exist."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def read_task_json(task_dir: Path) -> dict | None:
    """Read and parse task.json."""
    content = read_file(task_dir / "task.json")
    if content is None:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def get_modified_source_files(task_dir: Path) -> list[str]:
    """Check if source files were modified relative to git HEAD."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=task_dir.parent.parent.parent,  # repo root
            timeout=10,
        )
        if result.returncode != 0:
            return []
        # Filter to source files (not .trellis/ internal files)
        files = []
        for line in result.stdout.strip().split("\n"):
            if line and not line.startswith(".trellis/"):
                files.append(line)
        return files
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def check_planning_no_source_edits(task_dir: Path, task_data: dict) -> list[str]:
    """If task status is 'planning' but source files are modified, FAIL."""
    violations = []
    status = task_data.get("status", "").lower()

    if status != "planning":
        return violations

    # Check for source file modifications in the task directory
    # Look at git diff for the task's work
    modified = get_modified_source_files(task_dir)
    if modified:
        violations.append(
            f"Task status is 'planning' but source files are modified: {', '.join(modified)}"
        )

    return violations


def check_done_requires_check_pass(task_dir: Path, task_data: dict) -> list[str]:
    """If check failed but task claims done, FAIL."""
    violations = []
    status = task_data.get("status", "").lower()

    if status not in ("done", "archived"):
        return violations

    # Check if check result exists and is FAIL
    check_results_dir = task_dir / "validation"
    if check_results_dir.exists():
        for result_file in check_results_dir.glob("*.md"):
            content = read_file(result_file)
            if content and "FAIL" in content.upper():
                violations.append(
                    f"Task claims done/archived but check result in {result_file.name} contains FAIL"
                )

    # Check review results
    review_dir = task_dir / "review"
    if review_dir.exists():
        for review_file in review_dir.glob("*.md"):
            content = read_file(review_file)
            if content and "FAIL" in content.upper():
                violations.append(
                    f"Task claims done/archived but review in {review_file.name} contains FAIL"
                )

    return violations


def check_review_gate_fail_not_done(task_dir: Path, task_data: dict) -> list[str]:
    """If review gate FAIL but task claims done, FAIL."""
    violations = []
    status = task_data.get("status", "").lower()

    if status not in ("done", "archived"):
        return violations

    review_dir = task_dir / "review"
    if not review_dir.exists():
        return violations

    for review_file in review_dir.glob("*.md"):
        content = read_file(review_file)
        if content is None:
            continue
        # Look for FAIL verdict
        import re
        if re.search(r"verdict\s*:\s*FAIL", content, re.IGNORECASE):
            violations.append(
                f"Task claims done/archived but review gate {review_file.name} has FAIL verdict"
            )

    return violations


def check_archived_has_journal(task_dir: Path, task_data: dict) -> list[str]:
    """If task archived but no journal entry, FAIL."""
    violations = []
    status = task_data.get("status", "").lower()

    if status not in ("done", "archived"):
        return violations

    # Check for journal entry in .trellis/workspace/
    workspace_dir = task_dir.parent.parent / "workspace"
    if not workspace_dir.exists():
        violations.append("Task archived but no .trellis/workspace/ directory exists")
        return violations

    # Check for any journal file
    journal_files = list(workspace_dir.rglob("journal.md"))
    if not journal_files:
        violations.append("Task archived but no journal.md found in .trellis/workspace/")
        return violations

    # Check if any journal references this task
    task_name = task_dir.name
    found_reference = False
    for journal_file in journal_files:
        content = read_file(journal_file)
        if content and task_name in content:
            found_reference = True
            break

    if not found_reference:
        violations.append(
            f"Task archived but no journal entry references task '{task_name}'"
        )

    return violations


def validate_workflow_state(task_dir: str) -> bool:
    """Run all workflow state validations. Returns True if PASS."""
    task_path = Path(task_dir)

    if not task_path.exists():
        print(f"FAIL: task directory does not exist: {task_path}")
        return False

    task_data = read_task_json(task_path)
    if task_data is None:
        print(f"FAIL: cannot read task.json in: {task_path}")
        return False

    print(f"Task status: {task_data.get('status', 'unknown')}")

    all_violations: list[str] = []

    # Run all checks
    all_violations.extend(check_planning_no_source_edits(task_path, task_data))
    all_violations.extend(check_done_requires_check_pass(task_path, task_data))
    all_violations.extend(check_review_gate_fail_not_done(task_path, task_data))
    all_violations.extend(check_archived_has_journal(task_path, task_data))

    if all_violations:
        print("FAIL: the following violations were found:")
        for violation in all_violations:
            print(f"  - {violation}")
        return False

    print("PASS: workflow state is consistent")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <task-dir>")
        sys.exit(1)

    passed = validate_workflow_state(sys.argv[1])
    sys.exit(0 if passed else 1)
