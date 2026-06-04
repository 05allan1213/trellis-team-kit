"""
Team-kit Task Artifact Helpers.

Check existence and content of task artifacts (review files, validation, gates).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# Review gate file mapping (canonical)
GATE_FILE_MAP: dict[str, str] = {
    "trellis-check": "review/check-review.md",
    "trellis-spec-review": "review/spec-review.md",
    "trellis-code-review": "review/code-review.md",
    "trellis-code-architecture-review": "review/architecture-review.md",
    "trellis-improve-codebase-architecture deep-review": "review/architecture-deep-review.md",
    "trellis-merge-review": "review/merge-review.md",
}

REQUIRED_REVIEW_FIELDS = ("status", "scope reviewed", "blocking issues")
REQUIRED_VALIDATION_FILE = "validation/test-results.md"
REQUIRED_APPROVAL_FIELDS = ("user_message", "timestamp", "summary_approved")


def has_review_dir(task_dir: Path) -> bool:
    return (task_dir / "review").is_dir()


def _has_status_section(content: str) -> bool:
    return "status:" in content or bool(
        re.search(r"^\s*(?:#+\s*)?(?:status|verdict)(?:\s*:|\s|$)", content, re.MULTILINE)
    )


def _extract_review_verdict(content: str) -> Optional[str]:
    for line in content.splitlines():
        stripped = line.strip().lower()
        if not stripped:
            continue
        inline = re.match(r"^(?:#+\s*)?(?:status|verdict)\s*:\s*(.+)$", stripped)
        if inline:
            payload = inline.group(1).strip()
            if re.match(r"^fail\b", payload):
                return "fail"
            if re.match(r"^(?:redesign-required|redesign required)\b", payload):
                return "fail"
            if re.match(r"^pass\b", payload):
                return "pass"
        if re.match(r"^-\s*\[x\]\s*fail\b", stripped):
            return "fail"
        if re.match(r"^-\s*\[x\]\s*pass\b", stripped):
            return "pass"

    section_match = re.search(
        r"^\s*#+\s*(?:status|verdict)\s*$",
        content,
        re.MULTILINE,
    )
    if not section_match:
        return None

    section = content[section_match.end():]
    for line in section.splitlines():
        stripped = line.strip().lower()
        if not stripped:
            continue
        if stripped.startswith("#"):
            break
        if re.match(r"^-\s*\[x\]\s*fail\b", stripped):
            return "fail"
        if re.match(r"^-\s*\[x\]\s*pass\b", stripped):
            return "pass"
        if re.match(r"^fail\b(?!\s*/)", stripped):
            return "fail"
        if re.match(r"^(?:redesign-required|redesign required)\b", stripped):
            return "fail"
        if re.match(r"^pass\b(?!\s*/)", stripped):
            return "pass"
    return None


def check_review_gate(task_dir: Path, gate_name: str) -> Optional[str]:
    """Check a single review gate. Returns 'pass', 'fail', 'missing', or 'no-verdict'."""
    file_rel = GATE_FILE_MAP.get(gate_name)
    if not file_rel:
        return "missing"

    gate_file = task_dir / file_rel
    if not gate_file.is_file():
        return "missing"

    try:
        content = gate_file.read_text(encoding="utf-8").lower()
    except OSError:
        return "missing"

    if not _has_status_section(content):
        return "no-verdict"

    verdict = _extract_review_verdict(content)
    if verdict == "fail":
        return "fail"
    if verdict == "pass":
        return "pass"
    return "no-verdict"


def check_all_selected_gates(task_dir: Path, selected_gates: list[str]) -> dict:
    """Check all selected review gates. Returns per-gate status dict."""
    results: dict[str, str] = {}
    for gate in selected_gates:
        results[gate] = check_review_gate(task_dir, gate)
    return results


def parse_selected_gates(implement_md: Path) -> list[str]:
    """Parse the Review Gate Contract from implement.md."""
    if not implement_md.is_file():
        return []

    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return []

    gates: list[str] = []
    in_selected = False
    for line in content.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith("selected gates:") or lowered.startswith("### selected gates"):
            in_selected = True
            continue
        if in_selected:
            if stripped.startswith("#"):
                in_selected = False
                continue
            if stripped.lower().startswith("selection rationale:"):
                in_selected = False
                continue
            if stripped.lower().startswith("- [x]") and "]" in stripped:
                gate = stripped.split("] ", 1)[-1].strip()
                if gate:
                    gates.append(gate)
            elif stripped and not stripped.startswith("-"):
                in_selected = False
    return gates


def check_validation(task_dir: Path) -> dict:
    """Check validation results. Returns {build, test, smoke, ready}."""
    results: dict = {"build": "missing", "test": "missing", "smoke": "missing", "ready": "missing"}

    validation_dir = task_dir / "validation"
    if not validation_dir.is_dir():
        return results

    results_file = validation_dir / "test-results.md"
    if not results_file.is_file():
        return results

    try:
        content = results_file.read_text(encoding="utf-8").lower()
    except OSError:
        return results

    # Use line-start anchored regex to find ## Build, ## Test, ## Smoke
    # (not occurrences inside comments or table cells)
    # Note: cannot use \b in rf-strings — Python interprets \b as backspace.
    # Use (?:\n|$) to match end-of-heading instead.
    for check in ("build", "test", "smoke"):
        match = re.search(rf"^## {check}(?:\s|$)", content, re.MULTILINE)
        if match is None:
            continue
        section_start = match.start()
        section = content[section_start:section_start + 500]
        if "- [x] pass" in section:
            results[check] = "pass"
        elif "- [x] fail" in section:
            results[check] = "fail"
        elif "skipped with reason" in section:
            results[check] = "skipped"

    # Scope ready check to the section, not global content
    ready_match = re.search(r"^## ready for finish-work\?", content, re.MULTILINE)
    if ready_match is not None:
        ready_section = content[ready_match.start():ready_match.start() + 300]
        if "- [x] yes" in ready_section:
            results["ready"] = "yes"
        elif "- [x] no" in ready_section:
            results["ready"] = "no"

    return results


def parse_implementation_approval(implement_md: Path) -> dict[str, str | bool]:
    """Parse the Implementation Approval section from implement.md."""
    result: dict[str, str | bool] = {
        "approved": False,
        "start_allowed": False,
        "user_message": "",
        "timestamp": "",
        "summary_approved": "",
    }

    if not implement_md.is_file():
        return result

    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return result

    in_section = False
    in_source = False
    in_start = False

    for line in content.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()

        if lowered == "## implementation approval":
            in_section = True
            in_source = False
            in_start = False
            continue

        if in_section and stripped.startswith("## "):
            break

        if not in_section:
            continue

        if lowered.startswith("approval source:"):
            in_source = True
            in_start = False
            continue

        if lowered.startswith("allowed to run task.py start?"):
            in_start = True
            in_source = False
            continue

        if stripped.startswith("- [") and "]" in stripped:
            checked = stripped.lower().startswith("- [x]")
            label = stripped.split("] ", 1)[-1].strip().lower()
            if label == "approved":
                result["approved"] = checked
            elif in_start and label == "yes":
                result["start_allowed"] = checked
            continue

        if in_source:
            if lowered.startswith("- user message:"):
                result["user_message"] = stripped.split(":", 1)[-1].strip()
            elif lowered.startswith("- timestamp:"):
                result["timestamp"] = stripped.split(":", 1)[-1].strip()
            elif lowered.startswith("- summary approved:"):
                result["summary_approved"] = stripped.split(":", 1)[-1].strip()

    return result


def implementation_approval_complete(approval: dict[str, str | bool]) -> bool:
    """Return True when the implementation approval record is fully populated."""
    if not approval.get("approved") or not approval.get("start_allowed"):
        return False
    for field in REQUIRED_APPROVAL_FIELDS:
        value = str(approval.get(field, "")).strip()
        if not value:
            return False
    return True


def parse_finish_approval(finish_md: Path) -> dict[str, str | bool]:
    """Parse the Finish Approval section from finish.md."""
    result: dict[str, str | bool] = {
        "approved": False,
        "finish_allowed": False,
        "user_message": "",
        "timestamp": "",
        "summary_approved": "",
    }

    if not finish_md.is_file():
        return result

    try:
        content = finish_md.read_text(encoding="utf-8")
    except OSError:
        return result

    in_section = False
    in_source = False
    in_allowed = False

    for line in content.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()

        if lowered == "## finish approval":
            in_section = True
            in_source = False
            in_allowed = False
            continue

        if in_section and stripped.startswith("## "):
            break

        if not in_section:
            continue

        if lowered.startswith("approval source:"):
            in_source = True
            in_allowed = False
            continue

        if lowered.startswith("allowed to proceed with finish?"):
            in_allowed = True
            in_source = False
            continue

        if stripped.startswith("- [") and "]" in stripped:
            checked = stripped.lower().startswith("- [x]")
            label = stripped.split("] ", 1)[-1].strip().lower()
            if label == "approved":
                result["approved"] = checked
            elif in_allowed and label == "yes":
                result["finish_allowed"] = checked
            continue

        if in_source:
            if lowered.startswith("- user message:"):
                result["user_message"] = stripped.split(":", 1)[-1].strip()
            elif lowered.startswith("- timestamp:"):
                result["timestamp"] = stripped.split(":", 1)[-1].strip()
            elif lowered.startswith("- summary approved:"):
                result["summary_approved"] = stripped.split(":", 1)[-1].strip()

    return result


def finish_approval_complete(approval: dict[str, str | bool]) -> bool:
    """Return True when the finish approval record is fully populated."""
    if not approval.get("approved") or not approval.get("finish_allowed"):
        return False
    for field in REQUIRED_APPROVAL_FIELDS:
        value = str(approval.get(field, "")).strip()
        if not value:
            return False
    return True
