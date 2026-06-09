#!/usr/bin/env python3
"""Validate guardrail override ledger entries and finish review."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

VALID_DECISIONS = {"accepted", "denied"}


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


def _ledger_path(task_dir: Path) -> Path:
    return task_dir / "runtime" / "guardrail-overrides.jsonl"


def _validate_entry(entry: Any, *, line_no: int, task_id: str) -> list[str]:
    if not isinstance(entry, dict):
        return [f"Task '{task_id}': guardrail override line {line_no} must be a JSON object"]

    errors: list[str] = []
    for field in ("timestamp", "reason", "decision", "tool_name"):
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"Task '{task_id}': guardrail override line {line_no} missing non-empty '{field}'"
            )

    decision = entry.get("decision")
    if isinstance(decision, str) and decision.strip() and decision not in VALID_DECISIONS:
        errors.append(
            f"Task '{task_id}': guardrail override line {line_no} has invalid decision '{decision}'"
        )

    if not entry.get("path") and not entry.get("command"):
        errors.append(
            f"Task '{task_id}': guardrail override line {line_no} must record path or command"
        )

    return errors


def _finish_review_complete(task_dir: Path) -> bool:
    finish_md = task_dir / "finish.md"
    if not finish_md.is_file():
        return False
    try:
        content = finish_md.read_text(encoding="utf-8")
    except OSError:
        return False

    section = _extract_markdown_section(content, "Guardrail Overrides")
    if not section:
        return False

    lowered = section.lower()
    has_review = bool(re.search(r"-\s*\[x\]\s*override ledger reviewed", lowered))
    has_ledger = "runtime/guardrail-overrides.jsonl" in lowered
    decision_match = re.search(r"^\s*-\s*decision\s*:\s*(.+)$", section, re.IGNORECASE | re.MULTILINE)
    decision = decision_match.group(1).strip() if decision_match else ""
    decision_lower = decision.lower()
    placeholder_decisions = {"", "tbd", "todo", "n/a", "none", "-"}
    has_decision = (
        decision_lower not in placeholder_decisions
        and not decision_lower.startswith("n/a")
        and "<!--" not in decision
        and "-->" not in decision
    )
    return has_review and has_ledger and has_decision


def validate_guardrail_overrides(task_dir: Path) -> tuple[bool, list[str]]:
    if not task_dir.is_dir():
        return False, [f"Task directory not found: {task_dir}"]

    task_id = task_dir.name
    task_json = task_dir / "task.json"
    if task_json.is_file():
        try:
            data = json.loads(task_json.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                task_id = str(data.get("id") or task_id)
        except (json.JSONDecodeError, OSError):
            pass

    ledger = _ledger_path(task_dir)
    if not ledger.is_file():
        return True, []

    errors: list[str] = []
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return False, [f"Task '{task_id}': cannot read runtime/guardrail-overrides.jsonl: {e}"]

    non_blank = 0
    for line_no, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            continue
        non_blank += 1
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errors.append(
                f"Task '{task_id}': guardrail override line {line_no} is invalid JSON"
            )
            continue
        errors.extend(_validate_entry(entry, line_no=line_no, task_id=task_id))

    if non_blank == 0:
        return True, []

    if not _finish_review_complete(task_dir):
        errors.append(
            f"Task '{task_id}': finish.md missing completed 'Guardrail Overrides' review for runtime/guardrail-overrides.jsonl"
        )

    return len(errors) == 0, errors


def main() -> int:
    if len(sys.argv) < 2:
        print("PASS: validate_guardrail_overrides.py is available")
        return 0

    task_dir = Path(sys.argv[1])
    ok, issues = validate_guardrail_overrides(task_dir)
    if ok:
        print(f"PASS: guardrail overrides are valid for {task_dir}")
        return 0

    print(f"FAIL: {len(issues)} guardrail override issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
