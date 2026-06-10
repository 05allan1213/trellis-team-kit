#!/usr/bin/env python3
"""
validate_review_gates.py — Validate review gate completion.

Checks:
- Level-based mandatory gates are selected
- Selected gates in implement.md
- Required review files exist
- Each review file has PASS/FAIL
- Each selected review gate has a matching PASS reviewer agent result
- Review files do not retain unresolved template placeholders
- Disabled gates have reason
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_agent_results import validate_agent_results  # type: ignore[import-not-found]

GATE_FILE_MAP: dict[str, str] = {
    "trellis-spec-review": "review/spec-review.md",
    "trellis-code-review": "review/code-review.md",
    "trellis-code-architecture-review": "review/architecture-review.md",
    "trellis-improve-codebase-architecture deep-review": "review/architecture-deep-review.md",
    "trellis-merge-review": "review/merge-review.md",
}

GATE_AGENT_MAP: dict[str, str] = {
    "trellis-spec-review": "trellis-spec-reviewer",
    "trellis-code-review": "trellis-code-reviewer",
    "trellis-code-architecture-review": "trellis-architecture-reviewer",
    "trellis-improve-codebase-architecture deep-review": "trellis-architecture-deep-reviewer",
    "trellis-merge-review": "trellis-merge-reviewer",
}

NON_REVIEW_GATE_NAMES = {"trellis-check"}

MANDATORY_GATES: dict[str, list[str]] = {
    "L0": [],
    "L1": [],
    "L2": [],
    "L3": ["trellis-code-review"],
    "L4": [
        "trellis-spec-review",
        "trellis-code-review",
        "trellis-code-architecture-review",
    ],
    "L5": [
        "trellis-spec-review",
        "trellis-code-review",
        "trellis-code-architecture-review",
        "trellis-improve-codebase-architecture deep-review",
        "trellis-merge-review",
    ],
}


def _has_status_section(content: str) -> bool:
    return "status:" in content or bool(
        re.search(r"^\s*(?:#+\s*)?(?:status|verdict)(?:\s*:|\s|$)", content, re.MULTILINE)
    )


def _classify_verdict_payload(payload: str) -> str | None:
    stripped = payload.strip().lower()
    if not stripped:
        return None
    if re.search(r"\bpass\s*/\s*fail\b|\bfail\s*/\s*pass\b", stripped):
        return None

    if re.match(r"^[-*]\s*\[[ x]\]\s*", stripped):
        if not re.match(r"^[-*]\s*\[[x]\]\s*", stripped):
            return None
        stripped = re.sub(r"^[-*]\s*\[[x]\]\s*", "", stripped, count=1)
    else:
        stripped = re.sub(r"^(?:[-*]|\d+\.)\s*", "", stripped, count=1)

    if re.match(r"^(?:redesign-required|redesign required)\b", stripped):
        return "fail"
    if re.match(r"^pass\b", stripped):
        return "pass"
    if re.match(r"^fail\b", stripped):
        return "fail"
    return None


def _extract_review_verdict(content: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip().lower()
        if not stripped:
            continue
        inline = re.match(r"^(?:#+\s*)?(?:status|verdict)\s*:\s*(.+)$", stripped)
        if inline:
            verdict = _classify_verdict_payload(inline.group(1))
            if verdict is not None:
                return verdict
        if re.match(r"^[-*]\s*\[[x]\]\s*", stripped):
            verdict = _classify_verdict_payload(stripped)
            if verdict is not None:
                return verdict

    section_match = re.search(
        r"^\s*#+\s*(?:status|verdict)\s*$",
        content,
        re.IGNORECASE | re.MULTILINE,
    )
    if not section_match:
        return None

    section = content[section_match.end():]
    verdicts: set[str] = set()
    for line in section.splitlines():
        stripped = line.strip().lower()
        if not stripped:
            continue
        if stripped.startswith("#"):
            break
        verdict = _classify_verdict_payload(stripped)
        if verdict is not None:
            verdicts.add(verdict)
    if len(verdicts) == 1:
        return next(iter(verdicts))
    return None


def _review_artifact_issues(content: str, file_rel: str) -> list[str]:
    issues: list[str] = []
    lowered = content.lower()
    if re.search(r"\bpass\s*/\s*fail\b|\bfail\s*/\s*pass\b", lowered):
        issues.append(f"{file_rel} still contains PASS/FAIL placeholder text")
    if "{{" in content or "}}" in content:
        issues.append(f"{file_rel} still contains template variable markers")
    if "<!--" in content:
        issues.append(f"{file_rel} still contains unresolved HTML template comments")
    if re.search(r"<(?:file|description|issue|severity|suggested|module|source|signature|path|agent|command)[^>]*>", content):
        issues.append(f"{file_rel} still contains unresolved angle-bracket placeholders")
    if re.search(
        r"\[(?:"
        r"issue|why|suggestion|source|agent|path|summary|evidence|command|"
        r"task\s+title|file\s+path|finding|reason|description|"
        r"blocking\s+issue|spec\s+file|violation|entries|yes\s*/\s*no|"
        r"duplicate|expected\s+file|list\s+of|present\s*/\s*missing|"
        r"absent\s*/\s*present"
        r")[^\]]*\]",
        content,
        re.IGNORECASE,
    ):
        issues.append(f"{file_rel} still contains unresolved bracket placeholders")
    return issues


def _read_task_level(task_dir: Path) -> str:
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        return ""
    try:
        data = json.loads(task_json.read_text(encoding="utf-8"))
        return data.get("level", "")
    except (json.JSONDecodeError, OSError):
        return ""


def parse_selected_gates(implement_md: Path) -> list[str]:
    if not implement_md.is_file():
        return []
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return []

    review_section = _extract_markdown_section(content, "Review Gate Contract")
    if not review_section:
        return []

    gates: list[str] = []
    for line in review_section.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("- [x]") or "]" not in stripped:
            continue
        gate = stripped.split("]", 1)[-1].strip()
        if gate.lower().startswith("trellis-") and gate not in NON_REVIEW_GATE_NAMES:
            gates.append(gate)
    return gates


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


def _checked_labels(section_text: str) -> set[str]:
    labels: set[str] = set()
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("- [x]"):
            continue
        label = stripped.split("]", 1)[-1].strip().lower()
        if label:
            labels.add(label)
    return labels


def _markdown_field_value(content: str, field_name: str) -> str:
    pattern = re.compile(
        rf"^\s*-\s*(?:\*\*)?{re.escape(field_name)}(?:\*\*)?\s*:\s*(.*)$",
        re.IGNORECASE,
    )
    for line in content.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return ""


def _merge_review_required(level: str, implement_md: Path) -> bool:
    if level == "L5":
        return True
    if not implement_md.is_file():
        return False
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return False

    checked = _checked_labels(_extract_markdown_section(content, "Execution Mode Decision"))
    if (
        "trellis-native parallel + worktree" in checked
        or "omc ulw/ultrawork + worktree + parent/child" in checked
    ):
        return True

    branch_strategy = _markdown_field_value(content, "Branch strategy").lower()
    parent_child = _markdown_field_value(content, "Parent/child").lower()
    merge_review_needed = _markdown_field_value(content, "Merge review needed").lower()
    if "worktree" in branch_strategy:
        return True
    if parent_child.startswith("yes"):
        return True
    if merge_review_needed.startswith("yes"):
        return True

    lowered = content.lower()
    return bool(
        re.search(r"\bpr[- ]type\b|\bpr merge\b|\bconflict resolution\b", lowered)
    )


def _passing_agent_results_by_agent(task_dir: Path) -> set[str]:
    results_dir = task_dir / "agent-results"
    if not results_dir.is_dir():
        return set()

    agents: set[str] = set()
    for path in sorted(results_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        agent = payload.get("agent") if isinstance(payload, dict) else None
        status = payload.get("status") if isinstance(payload, dict) else None
        if isinstance(agent, str) and agent.strip() and status == "PASS":
            agents.add(agent.strip())
    return agents


def validate_review_gates(task_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not task_dir.is_dir():
        return False, [f"Task directory not found: {task_dir}"]

    task_json = task_dir / "task.json"
    if not task_json.is_file():
        return False, [f"No task.json in {task_dir}"]

    level = _read_task_level(task_dir)
    implement_md = task_dir / "implement.md"
    selected = parse_selected_gates(implement_md)
    agent_results_ok, agent_result_issues = validate_agent_results(task_dir, require_results=False)
    result_agents = _passing_agent_results_by_agent(task_dir) if agent_results_ok else set()
    for issue in agent_result_issues:
        errors.append(f"agent-results invalid: {issue}")

    mandatory = MANDATORY_GATES.get(level, [])
    if _merge_review_required(level, implement_md) and "trellis-merge-review" not in mandatory:
        mandatory = [*mandatory, "trellis-merge-review"]
    if mandatory:
        for gate in mandatory:
            if gate not in selected:
                errors.append(
                    f"Level {level} requires gate '{gate}' but it is not selected "
                    f"in implement.md Review Gate Contract"
                )

    if not selected and not mandatory:
        return True, []

    for gate in selected:
        file_rel = GATE_FILE_MAP.get(gate)
        if not file_rel:
            errors.append(f"Unknown gate: '{gate}' — not in canonical gate map")
            continue

        gate_file = task_dir / file_rel
        if not gate_file.is_file():
            errors.append(f"Gate '{gate}': review file missing ({file_rel})")
            continue

        try:
            raw_content = gate_file.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"Gate '{gate}': cannot read {file_rel}")
            continue
        content = raw_content.lower()

        has_status = _has_status_section(content)
        verdict = _extract_review_verdict(content)
        expected_agent = GATE_AGENT_MAP.get(gate)

        if not has_status:
            errors.append(f"Gate '{gate}': no 'Status' or 'Verdict' section found in {file_rel}")
        elif verdict is None:
            errors.append(f"Gate '{gate}': no PASS/FAIL verdict in {file_rel}")
        elif verdict == "fail":
            errors.append(f"Gate '{gate}': FAILED — must return to IMPLEMENTING")
        if expected_agent and expected_agent not in result_agents:
            errors.append(
                f"Gate '{gate}': missing PASS agent-results JSON from {expected_agent}"
            )
        for issue in _review_artifact_issues(raw_content, file_rel):
            errors.append(f"Gate '{gate}': {issue}")

    return len(errors) == 0, errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 validate_review_gates.py <task-directory>")
        print("  Validates review gate completion for a task.")
        return 1

    task_dir = Path(sys.argv[1])
    ok, errors = validate_review_gates(task_dir)

    if ok:
        print(f"PASS: All selected review gates are complete for {task_dir}")
        return 0

    print(f"FAIL: {len(errors)} gate issue(s):")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
