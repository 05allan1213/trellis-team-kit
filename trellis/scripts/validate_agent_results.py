#!/usr/bin/env python3
"""Validate machine-readable Trellis agent result files."""
from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

VALID_AGENTS = {
    "trellis-implementer",
    "trellis-checker",
    "trellis-spec-reviewer",
    "trellis-code-reviewer",
    "trellis-architecture-reviewer",
    "trellis-architecture-deep-reviewer",
    "trellis-merge-reviewer",
}
VALID_STATUS = {"PASS", "FAIL", "REDESIGN-REQUIRED", "BLOCKED"}
OMC_MODE_VALUES = {"omc", "OMC", "omc ulw/ultrawork", "OMC ulw/ultrawork"}
TASK_LOCAL_PATH_PREFIXES = (
    "agent-results/",
    "review/",
    "runtime/",
    "validation/",
    "research/",
)
TASK_LOCAL_PATHS = {
    "before-dev.md",
    "check.jsonl",
    "design.md",
    "finish.md",
    "implement.jsonl",
    "implement.md",
    "prd.md",
    "scope-manifest.json",
    "task.json",
}


def _read_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (json.JSONDecodeError, OSError) as e:
        return None, str(e)


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _normalize(path: str) -> str:
    norm = path.replace("\\", "/").strip()
    while norm.startswith("./"):
        norm = norm[2:]
    return norm.strip("/")


def _load_declared_scope(task_dir: Path) -> tuple[list[str], list[str]]:
    manifest_path = task_dir / "scope-manifest.json"
    data, err = _read_json(manifest_path)
    if err or not isinstance(data, dict):
        return [], []
    return (
        [_normalize(item) for item in _as_string_list(data.get("declared_paths"))],
        [_normalize(item) for item in _as_string_list(data.get("declared_globs"))],
    )


def _matches_declared(file_path: str, declared_paths: list[str], declared_globs: list[str]) -> bool:
    norm = _normalize(file_path)
    if norm.startswith(".trellis/") or norm.startswith(".claude/"):
        return True
    if norm in TASK_LOCAL_PATHS or norm.startswith(TASK_LOCAL_PATH_PREFIXES):
        return True
    for path in declared_paths:
        if norm == path or norm.startswith(f"{path.rstrip('/')}/"):
            return True
    for pattern in declared_globs:
        if fnmatch.fnmatchcase(norm, pattern):
            return True
    return False


def _extract_markdown_section(content: str, heading: str) -> str:
    target = heading.strip().lower()
    collected: list[str] = []
    in_section = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current = stripped[3:].strip().lower()
            if in_section:
                break
            if current == target:
                in_section = True
                continue
        if in_section:
            collected.append(line)
    return "\n".join(collected).strip()


def _checked_labels_in_section(section_text: str) -> set[str]:
    labels: set[str] = set()
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("- [x]"):
            continue
        label = stripped.split("]", 1)[-1].strip().lower()
        if label:
            labels.add(label)
    return labels


def _omc_approved(task_dir: Path) -> bool:
    implement_md = task_dir / "implement.md"
    if not implement_md.is_file():
        return False
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return False
    section = _extract_markdown_section(content, "Execution Mode Decision")
    checked = _checked_labels_in_section(section)
    return "user explicitly approved omc" in checked


def _merge_review_selected(task_dir: Path) -> bool:
    implement_md = task_dir / "implement.md"
    if not implement_md.is_file():
        return False
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return False
    section = _extract_markdown_section(content, "Review Gate Contract")
    return "trellis-merge-review" in _checked_labels_in_section(section)


def _execution_needs_agent_results(task_dir: Path) -> bool:
    if not _merge_review_selected(task_dir):
        return False
    implement_md = task_dir / "implement.md"
    if not implement_md.is_file():
        return True
    try:
        content = implement_md.read_text(encoding="utf-8").lower()
    except OSError:
        return True
    section = _extract_markdown_section(content, "Execution Mode Decision").lower()
    return any(
        phrase in section
        for phrase in (
            "trellis-native parallel + worktree",
            "omc ulw/ultrawork",
            "trellis subagents",
        )
    )


def _validate_result_payload(
    payload: Any,
    *,
    path: Path,
    declared_paths: list[str],
    declared_globs: list[str],
    omc_approved: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    changed_files: list[str] = []

    if not isinstance(payload, dict):
        return [f"{path.name}: must contain a JSON object"], changed_files

    for field in ("version", "agent", "status", "changed_files", "validation", "blocking_issues"):
        if field not in payload:
            errors.append(f"{path.name}: missing required field '{field}'")

    if payload.get("version") != 1:
        errors.append(f"{path.name}: version must be 1")

    agent = payload.get("agent")
    if not isinstance(agent, str) or agent not in VALID_AGENTS:
        errors.append(f"{path.name}: invalid agent '{agent}'")

    status = payload.get("status")
    if not isinstance(status, str) or status not in VALID_STATUS:
        errors.append(f"{path.name}: invalid status '{status}'")
    elif status in {"FAIL", "REDESIGN-REQUIRED", "BLOCKED"}:
        errors.append(f"{path.name}: agent status is {status}")

    changed = payload.get("changed_files")
    if not isinstance(changed, list) or not all(isinstance(item, str) and item.strip() for item in changed):
        errors.append(f"{path.name}: changed_files must be a list of strings")
    else:
        changed_files = [_normalize(item) for item in changed]
        for file_path in changed_files:
            if not _matches_declared(file_path, declared_paths, declared_globs):
                errors.append(f"{path.name}: changed file '{file_path}' is not declared in scope-manifest.json")

    validation = payload.get("validation")
    if not isinstance(validation, list):
        errors.append(f"{path.name}: validation must be a list")
    else:
        for i, item in enumerate(validation, 1):
            if not isinstance(item, dict):
                errors.append(f"{path.name}: validation item {i} must be an object")
                continue
            command = item.get("command")
            item_status = item.get("status")
            if not isinstance(command, str) or not command.strip():
                errors.append(f"{path.name}: validation item {i} missing command")
            if item_status != "PASS":
                errors.append(f"{path.name}: validation failed for '{command or f'item {i}'}'")

    blocking = payload.get("blocking_issues")
    if not isinstance(blocking, list):
        errors.append(f"{path.name}: blocking_issues must be a list")
    elif blocking:
        errors.append(f"{path.name}: unresolved blocking issue(s) remain")

    for optional_list in ("non_blocking_issues", "risks", "scope_expansion"):
        value = payload.get(optional_list, [])
        if not isinstance(value, list):
            errors.append(f"{path.name}: {optional_list} must be a list")

    execution_mode = payload.get("execution_mode")
    if isinstance(execution_mode, str) and execution_mode in OMC_MODE_VALUES and not omc_approved:
        errors.append(f"{path.name}: OMC result requires explicit OMC approval in implement.md")

    return errors, changed_files


def validate_agent_results(
    task_dir: Path,
    *,
    require_results: bool | None = None,
) -> tuple[bool, list[str]]:
    if not task_dir.is_dir():
        return False, [f"Task directory not found: {task_dir}"]

    if require_results is None:
        require_results = _execution_needs_agent_results(task_dir)

    results_dir = task_dir / "agent-results"
    files = sorted(results_dir.glob("*.json")) if results_dir.is_dir() else []
    if not files:
        if require_results:
            return False, [f"Task '{task_dir.name}': required agent-results/*.json is missing"]
        return True, []

    declared_paths, declared_globs = _load_declared_scope(task_dir)
    approved = _omc_approved(task_dir)
    errors: list[str] = []
    changed_by_file: dict[str, list[str]] = {}

    for result_path in files:
        payload, err = _read_json(result_path)
        if err:
            errors.append(f"{result_path.name}: invalid JSON: {err}")
            continue
        result_errors, changed_files = _validate_result_payload(
            payload,
            path=result_path,
            declared_paths=declared_paths,
            declared_globs=declared_globs,
            omc_approved=approved,
        )
        errors.extend(result_errors)
        agent = payload.get("agent") if isinstance(payload, dict) else result_path.name
        for file_path in changed_files:
            changed_by_file.setdefault(file_path, []).append(str(agent))

    for file_path, agents in sorted(changed_by_file.items()):
        unique_agents = sorted(set(agents))
        if len(unique_agents) > 1:
            errors.append(
                f"Changed file '{file_path}' was modified by multiple agents: {', '.join(unique_agents)}"
            )

    return len(errors) == 0, errors


def main() -> int:
    if len(sys.argv) < 2:
        print("PASS: validate_agent_results.py is available")
        return 0

    task_dir = Path(sys.argv[1])
    ok, issues = validate_agent_results(task_dir)
    if ok:
        print(f"PASS: agent results are valid for {task_dir}")
        return 0

    print(f"FAIL: {len(issues)} agent result issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
