"""
Team-kit Task Artifact Helpers.

Check existence and content of task artifacts (review files, validation, gates).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# Review gate file mapping (canonical)
GATE_FILE_MAP: dict[str, str] = {
    "trellis-spec-review": "review/spec-review.md",
    "trellis-code-review": "review/code-review.md",
    "trellis-code-architecture-review": "review/architecture-review.md",
    "trellis-improve-codebase-architecture deep-review": "review/architecture-deep-review.md",
    "trellis-merge-review": "review/merge-review.md",
}

REQUIRED_REVIEW_FIELDS = ("status", "scope reviewed", "blocking issues")
REQUIRED_VALIDATION_FILE = "validation/results.md"


def has_review_dir(task_dir: Path) -> bool:
    return (task_dir / "review").is_dir()


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

    has_pass = "status:" in content and any(
        marker in content for marker in ("- [x] pass", "[x] pass")
    )
    has_fail = "status:" in content and any(
        marker in content for marker in ("- [x] fail", "[x] fail")
    )

    if has_fail:
        return "fail"
    if has_pass:
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
        if stripped.lower().startswith("selected gates:"):
            in_selected = True
            continue
        if in_selected:
            if stripped.startswith("- [") and "]" in stripped:
                gate = stripped.split("] ", 1)[-1].strip()
                if gate:
                    gates.append(gate)
            elif not stripped.startswith("-"):
                in_selected = False
    return gates


def check_validation(task_dir: Path) -> dict:
    """Check validation results. Returns {build, test, smoke, ready}."""
    results: dict = {"build": "missing", "test": "missing", "smoke": "missing", "ready": "missing"}

    validation_dir = task_dir / "validation"
    if not validation_dir.is_dir():
        return results

    results_file = validation_dir / "results.md"
    if not results_file.is_file():
        return results

    try:
        content = results_file.read_text(encoding="utf-8").lower()
    except OSError:
        return results

    for check in ("build", "test", "smoke"):
        section_start = content.find(f"## {check}")
        if section_start == -1:
            continue
        section = content[section_start:section_start + 500]
        if "- [x] pass" in section:
            results[check] = "pass"
        elif "- [x] fail" in section:
            results[check] = "fail"
        elif "skipped with reason" in section:
            results[check] = "skipped"

    if "ready for finish-work?" in content:
        if "- [x] yes" in content:
            results["ready"] = "yes"
        elif "- [x] no" in content:
            results["ready"] = "no"

    return results
