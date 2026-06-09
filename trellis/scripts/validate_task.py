#!/usr/bin/env python3
"""
validate_task.py — Validate a specific task's artifacts and state.

Checks:
- task.json exists and is valid
- Task level is valid (L0-L5)
- Required artifacts by level are present
- L3/L4/L5 implement.jsonl / check.jsonl must exist and be non-empty
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

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_guardrail_overrides import validate_guardrail_overrides  # type: ignore[import-not-found]
from validate_agent_results import validate_agent_results  # type: ignore[import-not-found]
from validate_scope_manifest import validate_scope_manifest  # type: ignore[import-not-found]

LEVEL_ARTIFACT_REQUIREMENTS: dict[str, list[str]] = {
    "L0": [],
    "L1": [],
    "L2": ["prd.md", "implement.md"],
    "L3": ["prd.md", "research/grill-me.md", "implement.md"],
    "L4": ["prd.md", "research/grill-me.md", "implement.md", "design.md"],
    "L5": ["prd.md", "research/grill-me.md", "implement.md", "design.md"],
}

LEVEL_JSONL_REQUIREMENTS: dict[str, list[str]] = {
    "L0": [],
    "L1": [],
    "L2": [],
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

TASK_ARTIFACT_BASENAMES = {
    "prd.md",
    "design.md",
    "implement.md",
    "finish.md",
    "before-dev.md",
}
TASK_DIR_PLACEHOLDERS = ("$TASK_DIR/", "<task-dir>/")

REQUIRED_DELIVERY_SYNC_ITEMS = (
    "README / user docs reviewed",
    "Example commands / scripts reviewed",
    "Public API paths / contracts reviewed",
    "Implemented vs planned status reviewed",
)

CHECK_GATE_NAMES = {"trellis-check"}
EXECUTION_MODE_LABELS = (
    "main session",
    "single trellis subagent",
    "trellis subagents",
    "trellis-native parallel + worktree",
    "omc ulw/ultrawork + worktree + parent/child",
)


def _find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir() or (cur / "trellis").is_dir():
            return cur
        cur = cur.parent
    return None


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


def _extract_gate_verdict(content: str) -> str | None:
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

    verdicts: set[str] = set()
    section = content[section_match.end():]
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


def _has_concrete_observable_outcome(section_text: str) -> bool:
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells or all(not cell for cell in cells):
                continue
            if all(re.fullmatch(r"[:\- ]*", cell) for cell in cells):
                continue
            lowered_cells = [cell.lower() for cell in cells]
            if all(
                cell in ("#", "outcome", "evidence", "remaining gap / risk", "remaining gap/risk")
                for cell in lowered_cells
            ):
                continue
            return True
        if re.fullmatch(r"[|:\- ]+", stripped):
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

    errors.extend(_check_finish_approval(content, task_id))
    errors.extend(_check_delivery_sync(content, task_id))

    return errors


def _parse_finish_approval(content: str) -> dict[str, str | bool]:
    result: dict[str, str | bool] = {
        "approved": False,
        "finish_allowed": False,
        "user_message": "",
        "timestamp": "",
        "summary_approved": "",
    }

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


def _check_finish_approval(content: str, task_id: str) -> list[str]:
    section = _extract_markdown_section(content, "Finish Approval")
    if not section:
        return [f"Task '{task_id}': finish.md missing 'Finish Approval' section"]

    approval = _parse_finish_approval(content)
    errors: list[str] = []
    if not approval["approved"]:
        errors.append(
            f"Task '{task_id}': finish.md Finish Approval is not marked approved"
        )
    if not approval["finish_allowed"]:
        errors.append(
            f"Task '{task_id}': finish.md does not allow proceeding with finish"
        )
    for field in ("user_message", "timestamp", "summary_approved"):
        value = str(approval.get(field, "")).strip()
        if not value:
            errors.append(
                f"Task '{task_id}': finish.md Finish Approval field '{field}' is empty"
            )
    return errors


def _check_delivery_sync(content: str, task_id: str) -> list[str]:
    section = _extract_markdown_section(content, "Delivery Sync Check")
    if not section:
        return [f"Task '{task_id}': finish.md missing 'Delivery Sync Check' section"]

    errors: list[str] = []
    lowered = section.lower()
    for item in REQUIRED_DELIVERY_SYNC_ITEMS:
        pattern = re.compile(rf"-\s*\[x\]\s*{re.escape(item.lower())}")
        if not pattern.search(lowered):
            errors.append(
                f"Task '{task_id}': finish.md Delivery Sync Check must mark '{item}' as reviewed"
            )

    has_files_checked = False
    in_files = False
    for line in section.splitlines():
        stripped = line.strip()
        lowered_line = stripped.lower()
        if lowered_line.startswith("files checked:"):
            in_files = True
            continue
        if not in_files:
            continue
        if not stripped or stripped.startswith("<!--"):
            continue
        if stripped.startswith("- "):
            payload = stripped[2:].strip()
            if payload and "<!--" not in payload:
                has_files_checked = True
                break

    if not has_files_checked:
        errors.append(
            f"Task '{task_id}': finish.md Delivery Sync Check must list at least one checked file"
        )

    return errors


def _parse_implementation_approval(implement_md: Path) -> dict[str, str | bool]:
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


def _check_implementation_approval(implement_md: Path, task_id: str, status: str) -> list[str]:
    if not implement_md.is_file():
        return []
    if status.lower() not in ("in_progress", "completed", "done"):
        return []
    approval = _parse_implementation_approval(implement_md)
    errors: list[str] = []
    if not approval["approved"]:
        errors.append(
            f"Task '{task_id}': implement.md Implementation Approval is not marked approved"
        )
    if not approval["start_allowed"]:
        errors.append(
            f"Task '{task_id}': implement.md does not allow task.py start"
        )
    for field in ("user_message", "timestamp", "summary_approved"):
        value = str(approval.get(field, "")).strip()
        if not value:
            errors.append(
                f"Task '{task_id}': implement.md approval field '{field}' is empty"
            )
    return errors


def _check_requires_checker_pass(implement_md: Path, task_dir: Path, task_id: str, status: str, level: str) -> list[str]:
    """For L2+ active/completed tasks, validation/check-results.md must exist and contain PASS."""
    errors: list[str] = []
    if level not in ("L2", "L3", "L4", "L5"):
        return errors
    if status.lower() not in ("in_progress", "completed", "done"):
        return errors

    check_results = task_dir / "validation" / "check-results.md"
    if not check_results.is_file():
        errors.append(
            f"Task '{task_id}': trellis-check is required for {level} tasks but validation/check-results.md is missing"
        )
        return errors

    try:
        check_content = check_results.read_text(encoding="utf-8").lower()
    except OSError:
        errors.append(
            f"Task '{task_id}': cannot read validation/check-results.md"
        )
        return errors

    if _extract_gate_verdict(check_content) != "pass":
        errors.append(
            f"Task '{task_id}': validation/check-results.md exists but no PASS verdict found"
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


def _section_field_value(section_text: str, field_name: str) -> str:
    pattern = re.compile(
        rf"^\s*-\s*{re.escape(field_name)}\s*:\s*(.*)$",
        re.IGNORECASE,
    )
    for line in section_text.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return ""


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


def _merge_review_required(content: str, level: str) -> bool:
    execution_section = _extract_markdown_section(content, "Execution Mode Decision")
    checked = _checked_labels_in_section(execution_section)
    if level == "L5":
        return True
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


def _omc_approval_has_audit_details(section_text: str) -> bool:
    user_message = _section_field_value(section_text, "user message")
    timestamp = _section_field_value(section_text, "timestamp")
    placeholders = {"", "tbd", "todo", "n/a", "none", "-"}
    return user_message.lower() not in placeholders and timestamp.lower() not in placeholders


def _check_execution_mode_decision(implement_md: Path, task_id: str, level: str) -> list[str]:
    if level not in ("L4", "L5"):
        return []
    if not implement_md.is_file():
        return []
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return [f"Task '{task_id}' ({level}): cannot read implement.md for Execution Mode Decision"]

    section = _extract_markdown_section(content, "Execution Mode Decision")
    if not section:
        return [
            f"Task '{task_id}' ({level}): implement.md missing 'Execution Mode Decision' section"
        ]

    errors: list[str] = []
    checked = _checked_labels_in_section(section)
    selected_modes = [label for label in EXECUTION_MODE_LABELS if label in checked]
    if len(selected_modes) != 1:
        errors.append(
            f"Task '{task_id}' ({level}): Execution Mode Decision must select exactly one recommended mode"
        )

    omc_selected = "omc ulw/ultrawork + worktree + parent/child" in selected_modes
    omc_approved = "user explicitly approved omc" in checked
    omc_not_applicable = "not applicable" in checked

    if level == "L5" and "main session" in selected_modes:
        errors.append(
            f"Task '{task_id}' ({level}): L5 orchestrated execution cannot use main session"
        )
    if omc_selected and not omc_approved:
        errors.append(
            f"Task '{task_id}' ({level}): OMC execution requires explicit user approval in Execution Mode Decision"
        )
    if omc_selected and omc_approved and not _omc_approval_has_audit_details(section):
        errors.append(
            f"Task '{task_id}' ({level}): OMC approval requires user message and timestamp in Execution Mode Decision"
        )
    if not omc_selected and not omc_not_applicable and not omc_approved:
        errors.append(
            f"Task '{task_id}' ({level}): Execution Mode Decision must mark OMC approval as not applicable or explicitly approved"
        )

    review_section = _extract_markdown_section(content, "Review Gate Contract")
    review_checked = _checked_labels_in_section(review_section)
    if _merge_review_required(content, level) and "trellis-merge-review" not in review_checked:
        errors.append(
            f"Task '{task_id}' ({level}): worktree, parallel/OMC, PR merge, conflict resolution, or parent/child execution requires trellis-merge-review in Review Gate Contract"
        )

    return errors


def _check_final_validation_results(task_dir: Path, task_id: str, status: str, level: str) -> list[str]:
    errors: list[str] = []
    if level not in ("L2", "L3", "L4", "L5"):
        return errors
    if status.lower() not in ("completed", "done"):
        return errors

    test_results = task_dir / "validation" / "test-results.md"
    if not test_results.is_file():
        return [
            f"Task '{task_id}': final validation requires validation/test-results.md; validation/test-results.md is missing"
        ]

    try:
        content = test_results.read_text(encoding="utf-8").lower()
    except OSError:
        return [f"Task '{task_id}': cannot read validation/test-results.md"]

    if _extract_gate_verdict(content) != "pass" and "skipped with valid reason" not in content:
        errors.append(
            f"Task '{task_id}': validation/test-results.md exists but no PASS verdict or skipped-with-reason evidence found"
        )
    return errors


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


def _validate_jsonl_context(
    task_dir: Path,
    task_id: str,
    jsonl_name: str,
    is_planning: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    task_dir_abs = task_dir.resolve()
    jsonl_path = task_dir_abs / jsonl_name
    if not jsonl_path.is_file():
        return errors, warnings

    repo_root = _find_repo_root(task_dir_abs)
    task_rel = ""
    if repo_root is not None:
        try:
            task_rel = task_dir_abs.relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            task_rel = ""

    try:
        lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [f"Task '{task_id}': cannot read {jsonl_name}"], warnings

    for i, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"Task '{task_id}': {jsonl_name} line {i} is invalid JSON")
            continue

        if not isinstance(entry, dict):
            errors.append(f"Task '{task_id}': {jsonl_name} line {i} must be a JSON object")
            continue

        if "_example" in entry:
            if not is_planning:
                errors.append(
                    f"Task '{task_id}': {jsonl_name} line {i} still contains the template example entry"
                )
            continue

        file_ref = entry.get("file")
        reason = entry.get("reason")
        if not isinstance(file_ref, str) or not file_ref.strip():
            errors.append(
                f"Task '{task_id}': {jsonl_name} line {i} missing non-empty 'file'"
            )
            continue
        if not isinstance(reason, str) or not reason.strip():
            errors.append(
                f"Task '{task_id}': {jsonl_name} line {i} missing non-empty 'reason'"
            )

        normalized = file_ref.replace("\\", "/").strip()
        if normalized.startswith("./"):
            normalized = normalized[2:]

        resolved = normalized
        for placeholder in TASK_DIR_PLACEHOLDERS:
            if normalized.startswith(placeholder):
                suffix = normalized[len(placeholder):]
                resolved = f"{task_rel}/{suffix}" if task_rel else suffix
                break

        basename = Path(resolved).name.lower()
        if basename in TASK_ARTIFACT_BASENAMES:
            errors.append(
                f"Task '{task_id}': {jsonl_name} line {i} references task artifact '{normalized}' "
                f"but JSONL context must contain only spec/research files"
            )

        if task_rel:
            allowed_prefixes = (".trellis/spec/", f"{task_rel}/research/")
            if not resolved.startswith(allowed_prefixes):
                errors.append(
                    f"Task '{task_id}': {jsonl_name} line {i} points to '{normalized}', "
                    f"which is outside allowed spec/research context"
                )

        if repo_root is not None:
            target = repo_root / resolved
            if not target.is_file():
                errors.append(
                    f"Task '{task_id}': {jsonl_name} line {i} references missing file '{normalized}'"
                )

    return errors, warnings


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
        has_task_artifacts = any(
            (task_dir / name).exists()
            for name in (
                "prd.md", "design.md", "implement.md", "finish.md",
                "implement.jsonl", "check.jsonl",
            )
        )
        if has_task_artifacts or status.lower() != "planning":
            errors.append(f"Task '{task_id}': missing 'level' field")
        else:
            warnings.append(
                f"Task '{task_id}': missing 'level' field — bootstrap/setup tasks may not have a level yet"
            )
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
        jsonl_errors, jsonl_warnings = _validate_jsonl_context(
            task_dir, task_id, jsonl_name, is_planning
        )
        errors.extend(jsonl_errors)
        warnings.extend(jsonl_warnings)

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

    errors.extend(
        _check_execution_mode_decision(task_dir / "implement.md", task_id, level)
    )

    if not is_planning:
        agent_results_ok, agent_results_issues = validate_agent_results(task_dir)
        if not agent_results_ok:
            errors.extend(agent_results_issues)

    if level in LEVEL_ARTIFACT_REQUIREMENTS and not is_planning:
        scope_warnings = _check_scope_quality(
            task_dir / "implement.md", task_id, level
        )
        warnings.extend(scope_warnings)

    before_dev_md = task_dir / "before-dev.md"
    require_scope_contract = level in ("L2", "L3", "L4", "L5") and not is_planning
    if require_scope_contract and not before_dev_md.is_file():
        errors.append(
            f"Task '{task_id}' ({level}): missing required before-dev.md before implementation"
        )
    if require_scope_contract:
        scope_ok, scope_issues = validate_scope_manifest(task_dir)
        if not scope_ok:
            errors.extend(scope_issues)

    errors.extend(
        _check_implementation_approval(task_dir / "implement.md", task_id, status)
    )

    errors.extend(
        _check_requires_checker_pass(
            task_dir / "implement.md", task_dir, task_id, status, level
        )
    )

    finish_md = task_dir / "finish.md"
    if status.lower() in ("completed", "done") and not finish_md.is_file():
        errors.append(f"Task '{task_id}': status is '{status}' but finish.md is missing")
    elif finish_md.is_file():
        errors.extend(_check_finish_requirements(finish_md, task_id))
        override_ok, override_issues = validate_guardrail_overrides(task_dir)
        if not override_ok:
            errors.extend(override_issues)

    errors.extend(_check_final_validation_results(task_dir, task_id, status, level))

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
