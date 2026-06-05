#!/usr/bin/env python3
"""Validate task artifact completeness for trellis-team-kit.

Checks that all required artifacts exist and contain the necessary sections
based on task level. Outputs PASS or FAIL with specific missing items.

Usage:
    python3 validate_task.py <task-dir>
    python3 validate_task.py .trellis/tasks/05-29-my-feature/
"""

import json
import os
import re
import sys
from pathlib import Path


def read_file(path: Path) -> str | None:
    """Read file contents, return None if file does not exist."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def determine_task_level(task_dir: Path) -> str:
    """Determine task level from implement.md or prd.md."""
    implement_path = task_dir / "implement.md"
    prd_path = task_dir / "prd.md"

    implement_content = read_file(implement_path)
    if implement_content:
        level_match = re.search(r"task\s*level[:\s]+L(\d)", implement_content, re.IGNORECASE)
        if level_match:
            return f"L{level_match.group(1)}"

    prd_content = read_file(prd_path)
    if prd_content:
        level_match = re.search(r"task\s*level[:\s]+L(\d)", prd_content, re.IGNORECASE)
        if level_match:
            return f"L{level_match.group(1)}"

    # Infer from artifacts present
    has_design = (task_dir / "design.md").exists()
    if has_design:
        return "L4"
    return "L2"


def check_required_files(task_dir: Path, level: str) -> list[str]:
    """Check that required files exist for the given task level."""
    missing = []

    # prd.md required for L2+
    if level in ("L2", "L3", "L4", "L5"):
        if not (task_dir / "prd.md").exists():
            missing.append("prd.md (required for L2+)")
        if not (task_dir / "implement.md").exists():
            missing.append("implement.md (required for L2+ implementation approval)")

    # design.md required for L4/L5
    if level in ("L4", "L5"):
        if not (task_dir / "design.md").exists():
            missing.append("design.md (required for L4/L5)")

    return missing


def check_prd_acceptance_criteria(task_dir: Path) -> list[str]:
    """Check that prd.md has an Acceptance Criteria section."""
    missing = []
    content = read_file(task_dir / "prd.md")
    if content is None:
        missing.append("prd.md does not exist, cannot check Acceptance Criteria")
        return missing

    # Look for Acceptance Criteria section
    if not re.search(r"##?\s*acceptance\s+criteria", content, re.IGNORECASE):
        missing.append("prd.md missing 'Acceptance Criteria' section")

    return missing


def check_implement_sections(task_dir: Path, level: str) -> list[str]:
    """Check that implement.md has required sections."""
    missing = []
    content = read_file(task_dir / "implement.md")
    if content is None:
        return missing

    if level == "L2":
        if not re.search(r"##?\s*implementation\s+approval", content, re.IGNORECASE):
            missing.append("implement.md missing 'Implementation Approval' section")
        return missing

    if not re.search(r"##?\s*development\s+strategy", content, re.IGNORECASE):
        missing.append("implement.md missing 'Development Strategy' section")

    if not re.search(r"##?\s*review\s+gate\s+contract", content, re.IGNORECASE):
        if level in ("L3", "L4", "L5"):
            missing.append("implement.md missing 'Review Gate Contract' section")

    return missing


def validate_jsonl(task_dir: Path) -> list[str]:
    """Validate that JSONL files are parseable."""
    issues = []
    for jsonl_file in task_dir.rglob("*.jsonl"):
        rel_path = jsonl_file.relative_to(task_dir)
        try:
            lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
            for i, line in enumerate(lines, 1):
                if line.strip():
                    json.loads(line)
        except json.JSONDecodeError as e:
            issues.append(f"{rel_path} line {i}: invalid JSON - {e}")
        except FileNotFoundError:
            issues.append(f"{rel_path}: file not found")
    return issues


def check_review_results(task_dir: Path) -> list[str]:
    """Check that review results have PASS/FAIL verdict."""
    issues = []
    review_dir = task_dir / "review"
    if not review_dir.exists():
        return issues

    for review_file in review_dir.glob("*.md"):
        content = read_file(review_file)
        if content is None:
            continue
        rel_path = review_file.relative_to(task_dir)
        if not re.search(r"(PASS|FAIL)", content, re.IGNORECASE):
            issues.append(f"{rel_path}: no PASS/FAIL verdict found")

    return issues


def check_spec_update_decision(task_dir: Path) -> list[str]:
    """Check that finish.md has a spec update decision."""
    issues = []
    content = read_file(task_dir / "finish.md")
    if content is None:
        # finish.md may not exist yet
        return issues

    if not re.search(r"spec\s+update\s+decision", content, re.IGNORECASE):
        issues.append("finish.md missing 'Spec Update Decision' section")

    return issues


def validate_task(task_dir: str) -> bool:
    """Run all validations on a task directory. Returns True if PASS."""
    task_path = Path(task_dir)

    if not task_path.exists():
        print(f"FAIL: task directory does not exist: {task_path}")
        return False

    if not (task_path / "task.json").exists():
        print(f"FAIL: task.json not found in: {task_path}")
        return False

    all_issues: list[str] = []

    # Determine level
    level = determine_task_level(task_path)
    print(f"Task level detected: {level}")

    # Check required files
    all_issues.extend(check_required_files(task_path, level))

    # Check PRD acceptance criteria
    all_issues.extend(check_prd_acceptance_criteria(task_path))

    # Check implement.md sections
    all_issues.extend(check_implement_sections(task_path, level))

    # Validate JSONL files
    all_issues.extend(validate_jsonl(task_path))

    # Check review results
    all_issues.extend(check_review_results(task_path))

    # Check spec update decision
    all_issues.extend(check_spec_update_decision(task_path))

    if all_issues:
        print("FAIL: the following issues were found:")
        for issue in all_issues:
            print(f"  - {issue}")
        return False

    print("PASS: all required artifacts are present and valid")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <task-dir>")
        sys.exit(1)

    passed = validate_task(sys.argv[1])
    sys.exit(0 if passed else 1)
