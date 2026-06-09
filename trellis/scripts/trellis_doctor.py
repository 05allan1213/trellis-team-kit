#!/usr/bin/env python3
"""Trellis setup and workflow doctor."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_agent_results import validate_agent_results  # type: ignore[import-not-found]
from validate_guardrail_overrides import validate_guardrail_overrides  # type: ignore[import-not-found]
from validate_review_gates import validate_review_gates  # type: ignore[import-not-found]
from validate_scope_manifest import validate_scope_manifest  # type: ignore[import-not-found]
from validate_task import validate_task  # type: ignore[import-not-found]


VALID_LEVELS = {"L0", "L1", "L2", "L3", "L4", "L5"}
VALID_STATUSES = {
    "planning",
    "in_progress",
    "completed",
    "done",
    "PLANNING_PRD",
    "PLANNING_GRILL",
    "PLANNING_DESIGN",
    "PLANNING_IMPLEMENT",
    "WAITING_IMPLEMENTATION_APPROVAL",
}
PLANNING_PHASE_STATUSES = {
    "PLANNING_PRD",
    "PLANNING_GRILL",
    "PLANNING_DESIGN",
    "PLANNING_IMPLEMENT",
    "WAITING_IMPLEMENTATION_APPROVAL",
}
BROAD_SCOPE_PATTERNS = (
    r"^\*$",
    r"^src/\*$",
    r"^\.?/?$",
    r"^\*\*/\*$",
    r"^\.\./?$",
)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir() or (cur / "trellis").is_dir():
            return cur
        cur = cur.parent
    return None


def _active_task_from_root(root: Path) -> Path | None:
    active = root / ".trellis" / "active-task"
    if not active.is_file():
        return None
    try:
        value = active.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path if path.is_dir() else None


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


def _checked_labels(section: str) -> set[str]:
    labels: set[str] = set()
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("- [x]") and "]" in stripped:
            labels.add(stripped.split("]", 1)[-1].strip().lower())
    return labels


def _section_field_value(section: str, field_name: str) -> str:
    pattern = re.compile(
        rf"^\s*-\s*{re.escape(field_name)}\s*:\s*(.*)$",
        re.IGNORECASE,
    )
    for line in section.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return ""


def _omc_approval_has_audit_details(section: str) -> bool:
    user_message = _section_field_value(section, "user message")
    timestamp = _section_field_value(section, "timestamp")
    placeholders = {"", "tbd", "todo", "n/a", "none", "-"}
    return user_message.lower() not in placeholders and timestamp.lower() not in placeholders


def _infer_phase(task_dir: Path, status: str) -> str:
    if status == "planning" or status in PLANNING_PHASE_STATUSES:
        if (task_dir / "implement.md").is_file():
            return "WAITING_IMPLEMENTATION_APPROVAL"
        if (task_dir / "design.md").is_file():
            return "PLANNING_IMPLEMENT"
        if (task_dir / "research" / "grill-me.md").is_file():
            return "PLANNING_DESIGN"
        if (task_dir / "prd.md").is_file():
            return "PLANNING_GRILL"
        return "PLANNING_PRD"

    if status == "in_progress":
        finish = task_dir / "finish.md"
        finish_content = _read_text(finish)
        if "## Finish Approval" in finish_content and "- [x] approved" in finish_content.lower():
            return "FINISHING"
        if (task_dir / "review").is_dir() and any((task_dir / "review").iterdir()):
            return "REVIEWING"
        if (task_dir / "validation" / "check-results.md").is_file():
            return "UPDATING_SPEC"
        if (task_dir / "before-dev.md").is_file():
            return "IMPLEMENTING"
        return "BEFORE_DEV"

    if status in {"completed", "done"}:
        return "FINISHING"
    return status.upper() or "UNKNOWN"


def _phase_mismatch(task_dir: Path, status: str, inferred: str) -> str | None:
    if status in PLANNING_PHASE_STATUSES and inferred != status:
        return f"phase mismatch: expected {status} but inferred {inferred} from artifacts"
    if status == "planning" and (task_dir / "before-dev.md").is_file():
        return "phase mismatch: before-dev.md exists while task status is planning"
    if status == "planning" and (task_dir / "finish.md").is_file():
        return "phase mismatch: finish.md exists while task status is planning"
    if status == "in_progress" and (task_dir / "finish.md").is_file():
        content = _read_text(task_dir / "finish.md").lower()
        if "## finish approval" not in content or "- [x] approved" not in content:
            return "phase mismatch: finish.md exists before Finish approval"
    if inferred == "FINISHING" and status == "planning":
        return "phase mismatch: finishing artifacts exist while task is still planning"
    return None


def _scope_breadth_issues(task_dir: Path) -> list[str]:
    manifest = _read_json(task_dir / "scope-manifest.json")
    if not manifest:
        return []
    paths = []
    for key in ("declared_paths", "declared_globs"):
        value = manifest.get(key)
        if isinstance(value, list):
            paths.extend(str(item) for item in value if isinstance(item, str))
    issues: list[str] = []
    for path in paths:
        norm = path.replace("\\", "/").strip("/")
        for pattern in BROAD_SCOPE_PATTERNS:
            if re.match(pattern, norm):
                issues.append(f"scope declaration '{path}' is too broad")
                break
    return issues


def _finish_placeholder_issues(task_dir: Path) -> list[str]:
    finish = task_dir / "finish.md"
    if not finish.is_file():
        return []
    content = _read_text(finish)
    issues: list[str] = []
    observable = _extract_markdown_section(content, "Observable Outcomes").lower()
    if any(marker in observable for marker in ("<outcome", "<evidence", "<!--", "tbd", "todo")):
        issues.append("Observable Outcomes appears to contain placeholders")
    spec = _extract_markdown_section(content, "Spec Update Decision").lower()
    if any(marker in spec for marker in ("<reason", "<!--", "tbd", "todo")):
        issues.append("Spec Update Decision appears to contain placeholders")
    return issues


def _execution_mode_issues(task_dir: Path, level: str) -> tuple[str, list[str]]:
    implement = task_dir / "implement.md"
    content = _read_text(implement)
    section = _extract_markdown_section(content, "Execution Mode Decision")
    checked = _checked_labels(section)
    execution_mode = "not recorded"
    issues: list[str] = []
    for label in (
        "main session",
        "single trellis subagent",
        "trellis subagents",
        "trellis-native parallel + worktree",
        "omc ulw/ultrawork + worktree + parent/child",
    ):
        if label in checked:
            execution_mode = label
            break
    omc_selected = "omc ulw/ultrawork + worktree + parent/child" in checked
    omc_approved = "user explicitly approved omc" in checked
    if omc_selected and not omc_approved:
        issues.append("OMC execution requires explicit user approval")
    if omc_selected and omc_approved and not _omc_approval_has_audit_details(section):
        issues.append("OMC approval requires user message and timestamp")
    if (
        "trellis-native parallel + worktree" in checked
        or omc_selected
    ):
        review = _extract_markdown_section(content, "Review Gate Contract")
        if "trellis-merge-review" not in _checked_labels(review):
            issues.append("parallel or OMC execution requires trellis-merge-review")
    return execution_mode, issues


def _result_line(label: str, status: str, detail: str) -> str:
    return f"  {label:<22} {status} {detail}".rstrip()


def _first_existing_dir(root: Path, *relative_paths: str) -> Path | None:
    for relative_path in relative_paths:
        path = root / relative_path
        if path.is_dir():
            return path
    return None


def _missing_named_files(base: Path | None, names: tuple[str, ...]) -> list[str]:
    if base is None:
        return list(names)
    return [name for name in names if not (base / name).is_file()]


def _setup_check_line(
    label: str,
    base: Path | None,
    required_files: tuple[str, ...],
    fix: str,
) -> tuple[bool, str, str | None]:
    missing = _missing_named_files(base, required_files)
    present = len(required_files) - len(missing)
    status = "PASS" if not missing else "FAIL"
    detail = f"{present}/{len(required_files)} present"
    if missing:
        detail += " (missing: " + ", ".join(missing) + ")"
    line = _result_line(label + ":", status, detail)
    return not missing, line, None if not missing else f"To fix: {fix}"


def _settings_registered_hooks(settings_path: Path | None) -> tuple[bool, str, str | None]:
    required_events = (
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "SubagentStart",
        "SubagentStop",
        "Stop",
        "PreCompact",
        "Notification",
    )
    if settings_path is None or not settings_path.is_file():
        return (
            False,
            _result_line("Settings:", "FAIL", "settings.json missing"),
            "To fix: reinstall trellis-team-kit to restore .claude/settings.json.",
        )
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            False,
            _result_line("Settings:", "FAIL", f"settings.json invalid: {exc}"),
            "To fix: restore a valid .claude/settings.json from trellis-team-kit.",
        )
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return (
            False,
            _result_line("Settings:", "FAIL", "hooks object missing"),
            "To fix: restore hook registrations in .claude/settings.json.",
        )
    missing_events = [event for event in required_events if event not in hooks]
    if missing_events:
        return (
            False,
            _result_line("Settings:", "FAIL", "missing events: " + ", ".join(missing_events)),
            "To fix: restore required hook events in .claude/settings.json.",
        )
    return (
        True,
        _result_line("Settings:", "PASS", f"{len(required_events)}/{len(required_events)} hook events registered"),
        None,
    )


def diagnose_workflow(repo_root: Path, task_dir: Path | None = None) -> tuple[bool, str]:
    root = repo_root.resolve()
    if task_dir is None:
        task_dir = _active_task_from_root(root)
    if task_dir is None:
        return True, "\n".join(
            [
                "Trellis Workflow Doctor",
                "=======================",
                "",
                "Active task: NO_ACTIVE_TASK",
                "Overall: PASS (no active task)",
            ]
        )

    task_dir = task_dir.resolve()
    task_data = _read_json(task_dir / "task.json")
    if task_data is None:
        return False, "\n".join(
            [
                "Trellis Workflow Doctor",
                "=======================",
                "",
                f"Active task: {task_dir}",
                "Workflow alignment:",
                _result_line("Task JSON:", "FAIL", "task.json missing or invalid"),
                "Recommended fixes:",
                "  To fix: create or repair task.json with id, status, and level.",
            ]
        )

    task_id = str(task_data.get("id") or task_dir.name)
    level = str(task_data.get("level") or "")
    status = str(task_data.get("status") or "")
    inferred = _infer_phase(task_dir, status)
    execution_mode, execution_issues = _execution_mode_issues(task_dir, level)
    findings: list[tuple[str, str, str, str]] = []
    fixes: list[str] = []

    def add(label: str, status_text: str, detail: str, fix: str = "") -> None:
        findings.append((label, status_text, detail, fix))
        if status_text == "FAIL" and fix:
            fixes.append(f"To fix: {fix}")

    if level not in VALID_LEVELS:
        add("Level/artifacts:", "FAIL", f"invalid level '{level}'", "set task.json level to L0-L5.")
    elif status not in VALID_STATUSES:
        add("Level/artifacts:", "FAIL", f"invalid status '{status}'", "set task.json status to a valid workflow status.")
    else:
        add("Level/artifacts:", "PASS", f"{level} task has level/status metadata")

    mismatch = _phase_mismatch(task_dir, status, inferred)
    if mismatch:
        add("Phase:", "FAIL", mismatch, "move task status/artifacts back to the matching workflow phase.")
    else:
        add("Phase:", "PASS", f"inferred {inferred}")

    before_dev = task_dir / "before-dev.md"
    if status == "in_progress" and not before_dev.is_file():
        add("Before-dev:", "FAIL", "missing before-dev.md", "run trellis-before-dev before implementation.")
    elif before_dev.is_file():
        add("Before-dev:", "PASS", "before-dev.md exists")
    else:
        add("Before-dev:", "PASS", "not required yet")

    require_scope = before_dev.is_file() or status == "in_progress"
    scope_ok, scope_issues = validate_scope_manifest(task_dir, require_manifest=require_scope)
    if scope_ok:
        add("Scope manifest:", "PASS", "scope-manifest.json valid" if (task_dir / "scope-manifest.json").is_file() else "not required yet")
    else:
        detail = "; ".join(scope_issues)
        if "missing required scope-manifest.json" in detail:
            detail = detail.replace("missing required scope-manifest.json", "missing scope-manifest.json")
        add("Scope manifest:", "FAIL", detail, "write scope-manifest.json with declared_paths or declared_globs.")

    breadth = _scope_breadth_issues(task_dir)
    if breadth:
        add("Scope breadth:", "FAIL", "; ".join(breadth), "narrow broad declared scope entries.")
    else:
        add("Scope breadth:", "PASS", "no broad scope declarations found")

    override_ok, override_issues = validate_guardrail_overrides(task_dir)
    if override_ok:
        add("Overrides:", "PASS", "override ledger absent or reviewed")
    else:
        add("Overrides:", "FAIL", "; ".join(override_issues), "review guardrail overrides in finish.md.")

    review_ok, review_issues = validate_review_gates(task_dir)
    if review_ok:
        add("Review contract:", "PASS", "review gates aligned with level")
    else:
        add("Review contract:", "FAIL", "; ".join(review_issues), "select and complete required review gates.")

    agent_ok, agent_issues = validate_agent_results(task_dir)
    if agent_ok:
        add("Agent results:", "PASS", "agent results valid or not required yet")
    else:
        add("Agent results:", "FAIL", "; ".join(agent_issues), "write valid agent-results/*.json for parallel or merge-review work.")

    if execution_issues:
        add("OMC usage:", "FAIL", "; ".join(execution_issues), "record explicit OMC approval or switch to Trellis-native execution with merge-review.")
    else:
        add("OMC usage:", "PASS", "not used or explicitly approved")

    task_ok, task_issues = validate_task(task_dir)
    task_issue_text = "; ".join(issue.replace("WARNING: ", "") for issue in task_issues)
    if task_ok:
        add("Task validator:", "PASS", "validate_task.py passes")
    else:
        add("Task validator:", "FAIL", task_issue_text, "resolve validate_task.py issues before finish.")

    placeholders = _finish_placeholder_issues(task_dir)
    if placeholders:
        add("Finish readiness:", "FAIL", "; ".join(placeholders), "replace finish.md placeholders with concrete evidence.")
    else:
        add("Finish readiness:", "PASS", "no finish placeholders detected")

    overall_ok = all(status_text != "FAIL" for _, status_text, _, _ in findings)
    lines = [
        "Trellis Workflow Doctor",
        "=======================",
        "",
        f"Active task: {task_id} ({level or 'unknown'}, {status or 'unknown'})",
        f"Inferred phase: {inferred}",
        f"Execution mode: {execution_mode}",
        "",
        "Workflow alignment:",
    ]
    lines.extend(_result_line(label, status_text, detail) for label, status_text, detail, _ in findings)
    if fixes:
        lines.append("")
        lines.append("Recommended fixes:")
        lines.extend(f"  {fix}" for fix in fixes)
    lines.append("")
    lines.append("Overall: " + ("PASS" if overall_ok else "FAIL"))
    return overall_ok, "\n".join(lines)


def diagnose_setup(repo_root: Path) -> tuple[bool, str]:
    root = repo_root.resolve()
    required_scripts = (
        "validate_claude_settings.py",
        "validate_naming_map.py",
        "validate_hooks.py",
        "validate_trellis_config.py",
        "validate_spec_index.py",
        "validate_task.py",
        "validate_review_gates.py",
        "validate_runtime_hardening.py",
        "validate_workflow_state.py",
        "validate_delivery_sync.py",
        "prepare_finish_workspace.py",
        "finalize_task_archive.py",
        "validate_routing_rules.py",
        "validate_scope_manifest.py",
        "validate_guardrail_overrides.py",
        "validate_agent_results.py",
        "validate_spec_update_targets.py",
        "replay_workflow_cases.py",
        "detect_spec_update_candidates.py",
        "trellis_doctor.py",
    )
    required_hooks = (
        "session-start.py",
        "inject-workflow-state.py",
        "protect-dangerous-actions.py",
        "post-edit-reminder.py",
        "inject-subagent-context.py",
        "subagent-stop-guard.py",
        "stop-guard.py",
        "pre-compact-save-state.py",
        "trellis-notify.sh",
    )
    required_hook_libs = (
        "__init__.py",
        "hook_output.py",
        "workflow_state.py",
        "task_artifacts.py",
        "naming.py",
        "prompt_routing.py",
        "scope_manifest.py",
    )
    required_skills = (
        "trellis-before-dev",
        "trellis-brainstorm",
        "trellis-break-loop",
        "trellis-check",
        "trellis-code-architecture-review",
        "trellis-code-review",
        "trellis-dev-strategy",
        "trellis-finish-work",
        "trellis-grill-me",
        "trellis-implement",
        "trellis-improve-codebase-architecture",
        "trellis-merge-review",
        "trellis-spec-review",
        "trellis-update-spec",
    )
    required_agents = (
        "trellis-architecture-deep-reviewer.md",
        "trellis-architecture-reviewer.md",
        "trellis-checker.md",
        "trellis-code-reviewer.md",
        "trellis-implementer.md",
        "trellis-merge-reviewer.md",
        "trellis-researcher.md",
        "trellis-spec-reviewer.md",
        "trellis-spec-updater.md",
    )
    required_commands = (
        "auto-context.md",
        "continue.md",
        "create-manifest.md",
        "doctor.md",
        "finish-work.md",
        "new.md",
        "status.md",
    )
    required_config = (
        "config.json",
        "routing_rules.json",
        "workflow_profiles.json",
    )
    required_templates = (
        "prd.md.tmpl",
        "design.md.tmpl",
        "implement.md.tmpl",
        "finish.md.tmpl",
        "pr-template.md",
        "scope-manifest.json.tmpl",
        "before-dev.md",
        "research/evidence.md.tmpl",
        "research/brainstorm.md.tmpl",
        "research/grill-me.md.tmpl",
        "research/external-docs.md.tmpl",
        "research/architecture-options.md.tmpl",
        "research/break-loop.md.tmpl",
        "research/spike-results.md.tmpl",
        "research/decision-log.md.tmpl",
        "review/spec-review.md.tmpl",
        "review/code-review.md.tmpl",
        "review/architecture-review.md.tmpl",
        "review/merge-review.md.tmpl",
        "validation/commands.md.tmpl",
        "validation/test-results.md.tmpl",
        "validation/build-results.md.tmpl",
    )

    scripts_dir = _first_existing_dir(root, ".trellis/scripts", "trellis/scripts")
    hooks_dir = _first_existing_dir(root, ".claude/hooks", "claude/hooks")
    hook_lib_dir = _first_existing_dir(root, ".claude/hooks/lib", "claude/hooks/lib")
    skills_dir = _first_existing_dir(root, ".claude/skills", "claude/skills")
    agents_dir = _first_existing_dir(root, ".claude/agents", "claude/agents")
    commands_dir = _first_existing_dir(root, ".claude/commands/trellis", "claude/commands/trellis")
    config_dir = _first_existing_dir(root, ".trellis/config", "trellis/config")
    templates_dir = _first_existing_dir(root, ".trellis/templates", "trellis/task-templates")
    spec_dir = _first_existing_dir(root, ".trellis/spec", "marketplace/specs/web-app")
    settings_path = None
    for relative_path in (".claude/settings.json", "claude/settings.json"):
        candidate = root / relative_path
        if candidate.is_file():
            settings_path = candidate
            break

    checks: list[tuple[bool, str, str | None]] = []
    checks.append(
        _setup_check_line(
            "Scripts",
            scripts_dir,
            required_scripts,
            "reinstall trellis-team-kit or restore missing .trellis/scripts files.",
        )
    )
    checks.append(_settings_registered_hooks(settings_path))
    checks.append(
        _setup_check_line(
            "Hooks",
            hooks_dir,
            required_hooks,
            "restore missing .claude/hooks files.",
        )
    )
    checks.append(
        _setup_check_line(
            "Hook libs",
            hook_lib_dir,
            required_hook_libs,
            "restore missing .claude/hooks/lib files.",
        )
    )

    missing_skills = []
    for skill in required_skills:
        if skills_dir is None or not (skills_dir / skill / "SKILL.md").is_file():
            missing_skills.append(skill)
    skills_present = len(required_skills) - len(missing_skills)
    checks.append(
        (
            not missing_skills,
            _result_line(
                "Skills:",
                "PASS" if not missing_skills else "FAIL",
                f"{skills_present}/{len(required_skills)} present"
                + ("" if not missing_skills else " (missing: " + ", ".join(missing_skills) + ")"),
            ),
            None if not missing_skills else "To fix: restore missing .claude/skills/*/SKILL.md files.",
        )
    )
    checks.append(
        _setup_check_line(
            "Agents",
            agents_dir,
            required_agents,
            "restore missing .claude/agents files.",
        )
    )
    checks.append(
        _setup_check_line(
            "Commands",
            commands_dir,
            required_commands,
            "restore missing .claude/commands/trellis files.",
        )
    )
    checks.append(
        _setup_check_line(
            "Config",
            config_dir,
            required_config,
            "restore missing .trellis/config files.",
        )
    )
    checks.append(
        _setup_check_line(
            "Task templates",
            templates_dir,
            required_templates,
            "restore missing .trellis/templates files.",
        )
    )

    spec_ok = spec_dir is not None and (spec_dir / "index.md").is_file()
    checks.append(
        (
            spec_ok,
            _result_line("Specs:", "PASS" if spec_ok else "FAIL", "index.md present" if spec_ok else "spec index missing"),
            None if spec_ok else "To fix: restore .trellis/spec/index.md from the team spec template.",
        )
    )

    ok = all(check_ok for check_ok, _, _ in checks)
    lines = [
        "Trellis Setup Doctor",
        "====================",
        "",
        "Installation health:",
    ]
    lines.extend(line for _, line, _ in checks)
    fixes = [fix for _, _, fix in checks if fix]
    if fixes:
        lines.append("")
        lines.append("Recommended fixes:")
        lines.extend(f"  {fix}" for fix in fixes)
    lines.append("Overall: " + ("PASS" if ok else "FAIL"))
    return ok, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Trellis setup or workflow doctor.")
    parser.add_argument("mode", nargs="?", choices=("setup", "workflow"), default="setup")
    parser.add_argument("task_dir", nargs="?")
    parser.add_argument("--dry-run", action="store_true", help="accepted for command compatibility")
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    root = _find_repo_root(cwd) or cwd
    if args.mode == "setup":
        ok, report = diagnose_setup(root)
    else:
        task_dir = Path(args.task_dir) if args.task_dir else None
        ok, report = diagnose_workflow(root, task_dir)
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
