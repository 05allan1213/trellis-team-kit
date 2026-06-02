#!/usr/bin/env python3
"""
validate_task.py — Validate a specific task's artifacts and state.

Checks:
- task.json exists and is valid
- Task level is valid (L0-L5)
- Required artifacts by level are present
- implement.jsonl / check.jsonl must exist and be non-empty
- Approval status
- Review gate contract is present
- Validation results
- Finish marker for completed tasks
- finish.md Spec Update Decision and Observable Outcomes sections
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LEVEL_ARTIFACT_REQUIREMENTS: dict[str, list[str]] = {
    "L0": [],
    "L1": [],
    "L2": ["prd.md", "research/grill-me.md"],
    "L3": ["prd.md", "research/grill-me.md", "implement.md"],
    "L4": ["prd.md", "research/grill-me.md", "implement.md", "design.md"],
    "L5": ["prd.md", "research/grill-me.md", "implement.md", "design.md"],
}

LEVEL_JSONL_REQUIREMENTS: dict[str, list[str]] = {
    "L0": [],
    "L1": [],
    "L2": ["implement.jsonl", "check.jsonl"],
    "L3": ["implement.jsonl", "check.jsonl"],
    "L4": ["implement.jsonl", "check.jsonl"],
    "L5": ["implement.jsonl", "check.jsonl"],
}


BROAD_SCOPE_PATTERNS = [
    r"^\*$",
    r"^src/\*$",
    r"^\.?/?$",
    r"^\*\*/\*$",
    r"^\.\./?$",
]


def _extract_markdown_section(content: str, heading: str) -> str:
    lines = content.splitlines()
    target = heading.strip().lower()
    collected: list[str] = []
    in_section = False

    for line in lines:
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


def _has_concrete_observable_outcome(section_text: str) -> bool:
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("|") or re.fullmatch(r"[|:\- ]+", stripped):
            continue

        payload = re.sub(r"^(?:-|\d+\.)\s*", "", stripped).strip()
        if not payload or "<!--" in payload:
            continue

        if re.fullmatch(
            r"(?i)(outcome|evidence|remaining gap(?: / risk)?|risk)\s*:\s*",
            payload,
        ):
            continue

        return True
    return False


def _check_finish_requirements(finish_md: Path, task_id: str) -> list[str]:
    if not finish_md.is_file():
        return []

    try:
        content = finish_md.read_text(encoding="utf-8")
    except OSError as e:
        return [f"Task '{task_id}': cannot read finish.md: {e}"]

    errors: list[str] = []
    spec_section = _extract_markdown_section(content, "Spec Update Decision")
    if not spec_section:
        errors.append(
            f"Task '{task_id}': finish.md missing 'Spec Update Decision' section"
        )

    observable_section = _extract_markdown_section(content, "Observable Outcomes")
    if not observable_section:
        errors.append(
            f"Task '{task_id}': finish.md missing 'Observable Outcomes' section"
        )
    elif not _has_concrete_observable_outcome(observable_section):
        errors.append(
            f"Task '{task_id}': finish.md 'Observable Outcomes' must include at least one concrete outcome"
        )

    return errors


def _check_scope_quality(implement_md: Path, task_id: str, level: str) -> list[str]:
    if not implement_md.is_file():
        return []
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return []

    paths: list[str] = []
    in_section = False
    for line in content.splitlines():
        stripped = line.strip()
        clean = stripped.lstrip("#").strip()
        if clean.lower().startswith("files / areas likely touched") or \
           clean.lower().startswith("files/areas likely touched"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("##"):
                break
            m = re.match(r"-\s*`([^`]+)`", stripped)
            if m:
                paths.append(m.group(1).strip())

    if not paths:
        return []

    warnings: list[str] = []
    for p in paths:
        norm = p.replace("\\", "/").strip("/")
        for pattern in BROAD_SCOPE_PATTERNS:
            if re.match(pattern, norm):
                warnings.append(
                    f"Task '{task_id}' ({level}): implement.md scope declaration "
                    f"'{p}' is too broad — use more specific paths to enable "
                    f"effective scope guarding"
                )
                break

    return warnings


def _check_jsonl_non_empty(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "file does not exist"
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    return True, ""
        return False, "file is empty (no non-blank lines)"
    except OSError as e:
        return False, f"cannot read: {e}"


def validate_task(task_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not task_dir.is_dir():
        return False, [f"Task directory not found: {task_dir}"]

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
        warnings.append(f"Task '{task_id}': missing 'level' field — "
                        f"bootstrap/setup tasks may not have a level. "
                        f"Skipping artifact and JSONL checks.")
    elif level not in LEVEL_ARTIFACT_REQUIREMENTS:
        errors.append(f"Task '{task_id}': invalid level '{level}'")

    if not status:
        errors.append(f"Task '{task_id}': missing 'status' field")

    is_planning = status.lower() == "planning" or status.upper() in (
        "PLANNING_PRD", "PLANNING_GRILL", "PLANNING_DESIGN",
        "PLANNING_IMPLEMENT", "WAITING_IMPLEMENTATION_APPROVAL",
    )

    if level in LEVEL_ARTIFACT_REQUIREMENTS:
        for artifact in LEVEL_ARTIFACT_REQUIREMENTS[level]:
            art_path = task_dir / artifact
            if not art_path.is_file():
                if is_planning and artifact == "design.md":
                    continue
                errors.append(
                    f"Task '{task_id}' ({level}): missing required artifact '{artifact}'"
                )

    if level in LEVEL_JSONL_REQUIREMENTS and not is_planning:
        for jsonl_name in LEVEL_JSONL_REQUIREMENTS[level]:
            jsonl_path = task_dir / jsonl_name
            ok, detail = _check_jsonl_non_empty(jsonl_path)
            if not ok:
                errors.append(
                    f"Task '{task_id}' ({level}): required '{jsonl_name}' {detail}"
                )

    for jsonl_name in ("implement.jsonl", "check.jsonl"):
        jsonl_path = task_dir / jsonl_name
        if not jsonl_path.is_file():
            continue
        ok, _ = _check_jsonl_non_empty(jsonl_path)
        if not ok:
            continue
        try:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        errors.append(
                            f"Task '{task_id}': {jsonl_name} line {i} is invalid JSON"
                        )
        except OSError:
            errors.append(f"Task '{task_id}': cannot read {jsonl_name}")

    implement_md = task_dir / "implement.md"
    if implement_md.is_file():
        try:
            content = implement_md.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "Review Gate Contract" not in content and "review gate" not in content.lower():
            if level in ("L3", "L4", "L5"):
                warnings.append(
                    f"Task '{task_id}': implement.md missing Review Gate Contract"
                )

    if level in LEVEL_ARTIFACT_REQUIREMENTS and not is_planning:
        scope_warnings = _check_scope_quality(
            task_dir / "implement.md", task_id, level
        )
        warnings.extend(scope_warnings)

    finish_md = task_dir / "finish.md"
    if status.lower() in ("completed", "done") and not finish_md.is_file():
        errors.append(f"Task '{task_id}': status is '{status}' but finish.md is missing")
    elif finish_md.is_file():
        errors.extend(_check_finish_requirements(finish_md, task_id))

    before_dev_md = task_dir / "before-dev.md"
    if status.lower() == "in_progress" and before_dev_md.is_file():
        try:
            bd_content = before_dev_md.read_text(encoding="utf-8")
        except OSError:
            bd_content = ""

        scope_filled = False
        files_filled = False
        in_constraints = False
        for line in bd_content.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("- scope:"):
                in_constraints = True
                val = stripped.split(":", 1)[-1].strip()
                if val and val.lower() not in ("", "n/a", "tbd", "todo"):
                    scope_filled = True
            elif stripped.lower().startswith("- files likely touched:"):
                in_constraints = True
                val = stripped.split(":", 1)[-1].strip()
                if val and val.lower() not in ("", "n/a", "tbd", "todo"):
                    files_filled = True
            elif in_constraints and stripped.startswith("-"):
                pass
            elif in_constraints and stripped and not stripped.startswith("-"):
                in_constraints = False

        if not scope_filled:
            errors.append(
                f"Task '{task_id}': before-dev.md 'Scope' field is empty — "
                f"fill in the implementation scope before editing source code"
            )
        if not files_filled:
            errors.append(
                f"Task '{task_id}': before-dev.md 'Files likely touched' field is empty — "
                f"declare which files will be modified before editing source code"
            )

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
