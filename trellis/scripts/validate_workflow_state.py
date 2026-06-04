#!/usr/bin/env python3
"""Validate workflow-state evidence for trellis-team-kit tasks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PLACEHOLDER_JOURNAL_MARKERS = (
    "(No commits - planning session)",
    "(Add details)",
    "(Add test results)",
)


def read_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def read_task_json(task_dir: Path) -> dict | None:
    content = read_file(task_dir / "task.json")
    if content is None:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir():
            return cur
        cur = cur.parent
    return None


def get_modified_source_files(repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0:
        return []

    files: list[str] = []
    for line in result.stdout.strip().splitlines():
        if line and not line.startswith(".trellis/"):
            files.append(line)
    return files


def check_planning_no_source_edits(repo_root: Path, task_data: dict) -> list[str]:
    violations: list[str] = []
    status = str(task_data.get("status", "")).lower()
    if status != "planning":
        return violations

    modified = get_modified_source_files(repo_root)
    if modified:
        violations.append(
            f"Task status is 'planning' but source files are modified: {', '.join(modified)}"
        )
    return violations


def check_done_requires_no_failures(task_dir: Path, task_data: dict) -> list[str]:
    violations: list[str] = []
    status = str(task_data.get("status", "")).lower()
    if status not in ("done", "archived", "completed"):
        return violations

    for subdir in ("validation", "review"):
        base = task_dir / subdir
        if not base.exists():
            continue
        for md_file in base.glob("*.md"):
            content = read_file(md_file)
            if content and "FAIL" in content.upper():
                violations.append(
                    f"Task claims done/archived but {md_file.relative_to(task_dir)} contains FAIL"
                )
    return violations


def check_archived_has_journal(task_dir: Path, task_data: dict, repo_root: Path) -> list[str]:
    violations: list[str] = []
    status = str(task_data.get("status", "")).lower()
    if status not in ("done", "archived", "completed"):
        return violations

    workspace_dir = repo_root / ".trellis" / "workspace"
    if not workspace_dir.exists():
        return ["Task archived but no .trellis/workspace/ directory exists"]

    journal_files = list(workspace_dir.rglob("journal*.md"))
    if not journal_files:
        return ["Task archived but no journal*.md found in .trellis/workspace/"]

    task_refs = [
        task_dir.name,
        str(task_data.get("id", "")).strip(),
        str(task_data.get("title", "")).strip(),
    ]
    task_refs = [ref for ref in task_refs if ref]

    found_reference = False
    for journal_file in journal_files:
        content = read_file(journal_file) or ""
        if any(ref in content for ref in task_refs):
            found_reference = True
            for marker in PLACEHOLDER_JOURNAL_MARKERS:
                if marker in content:
                    violations.append(
                        f"Journal file {journal_file.relative_to(repo_root)} still contains placeholder marker: {marker}"
                    )
                    break

    if not found_reference:
        violations.append(
            f"Task archived but no journal entry references task '{task_dir.name}'"
        )

    return violations


def check_workspace_index(task_dir: Path, task_data: dict, repo_root: Path) -> list[str]:
    violations: list[str] = []
    status = str(task_data.get("status", "")).lower()
    if status not in ("done", "archived", "completed"):
        return violations

    workspace_dir = repo_root / ".trellis" / "workspace"
    if not workspace_dir.exists():
        return violations

    root_index = workspace_dir / "index.md"
    root_content = read_file(root_index) or ""
    if "(none yet)" in root_content:
        violations.append("Workspace index still shows '(none yet)' despite archived task activity")

    task_refs = [
        task_dir.name,
        str(task_data.get("id", "")).strip(),
        str(task_data.get("title", "")).strip(),
    ]
    task_refs = [ref for ref in task_refs if ref]

    developer_indexes = [
        path for path in workspace_dir.rglob("index.md") if path != root_index
    ]
    if not developer_indexes:
        violations.append("Workspace has no developer index.md files")
        return violations

    found_reference = False
    for index_file in developer_indexes:
        content = read_file(index_file) or ""
        matched_line = ""
        for line in content.splitlines():
            if any(ref in line for ref in task_refs):
                found_reference = True
                matched_line = line
                break
        if matched_line and "| - |" in matched_line:
            violations.append(
                f"Developer index {index_file.relative_to(repo_root)} records the task with missing commit info"
            )

    if not found_reference:
        violations.append(
            f"No developer workspace index references task '{task_dir.name}'"
        )

    return violations


def check_runtime_state_not_tracked(task_data: dict, repo_root: Path) -> list[str]:
    status = str(task_data.get("status", "")).lower()
    if status not in ("done", "archived", "completed"):
        return []

    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0:
        return []

    dirty_lines = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        path = line[3:].strip()
        if not path:
            continue
        parts = path.replace("\\", "/").split("/")
        if ".omc" not in parts:
            continue
        deletion_only = all(ch in {" ", "D"} for ch in status) and "D" in status
        if deletion_only:
            continue
        dirty_lines.append(line.rstrip())
    if not dirty_lines:
        return []

    return [
        "Tracked or untracked runtime state files remain after finish: "
        + ", ".join(dirty_lines)
    ]


def validate_workflow_state(task_dir: str) -> bool:
    task_path = Path(task_dir)
    if not task_path.exists():
        print(f"FAIL: task directory does not exist: {task_path}")
        return False

    repo_root = find_repo_root(task_path)
    if repo_root is None:
        print(f"FAIL: cannot find repo root for task: {task_path}")
        return False

    task_data = read_task_json(task_path)
    if task_data is None:
        print(f"FAIL: cannot read task.json in: {task_path}")
        return False

    print(f"Task status: {task_data.get('status', 'unknown')}")

    violations: list[str] = []
    violations.extend(check_planning_no_source_edits(repo_root, task_data))
    violations.extend(check_done_requires_no_failures(task_path, task_data))
    violations.extend(check_archived_has_journal(task_path, task_data, repo_root))
    violations.extend(check_workspace_index(task_path, task_data, repo_root))
    violations.extend(check_runtime_state_not_tracked(task_data, repo_root))

    if violations:
        print("FAIL: the following violations were found:")
        for violation in violations:
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
