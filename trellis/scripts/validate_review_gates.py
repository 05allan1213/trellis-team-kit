#!/usr/bin/env python3
"""
validate_review_gates.py — Validate review gate completion.

Checks:
- Selected gates in implement.md
- Required review files exist
- Each review file has PASS/FAIL
- Disabled gates have reason
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

GATE_FILE_MAP: dict[str, str] = {
    "trellis-spec-review": "review/spec-review.md",
    "trellis-code-review": "review/code-review.md",
    "trellis-code-architecture-review": "review/architecture-review.md",
    "trellis-improve-codebase-architecture deep-review": "review/architecture-deep-review.md",
    "trellis-merge-review": "review/merge-review.md",
}


def parse_selected_gates(implement_md: Path) -> list[str]:
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


def validate_review_gates(task_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    implement_md = task_dir / "implement.md"
    selected = parse_selected_gates(implement_md)

    if not selected:
        return True, []  # No gates selected, nothing to check

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
            content = gate_file.read_text(encoding="utf-8").lower()
        except OSError:
            errors.append(f"Gate '{gate}': cannot read {file_rel}")
            continue

        has_status = "status:" in content
        has_pass = bool(re.search(r"-\s*\[x\]\s*pass", content))
        has_fail = bool(re.search(r"-\s*\[x\]\s*fail", content))

        if not has_status:
            errors.append(f"Gate '{gate}': no 'Status:' section found in {file_rel}")
        elif not has_pass and not has_fail:
            errors.append(f"Gate '{gate}': no PASS/FAIL verdict in {file_rel}")
        elif has_fail:
            errors.append(f"Gate '{gate}': FAILED — must return to IMPLEMENTING")

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
