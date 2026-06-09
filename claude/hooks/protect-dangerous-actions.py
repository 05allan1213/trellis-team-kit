#!/usr/bin/env python3
"""
Team-kit Protect Dangerous Actions Hook — v0.3 Hardened

Protects against dangerous operations with clear hard block / soft warning /
allow-with-reason distinction.

Hard block (deny):
- rm -rf, git reset --hard, git clean -fd, git push --force
- Editing .env or secrets/credentials files
- Deleting migration files
- Source file editing during planning phase (before implementation approval)
- Source file editing during in_progress without before-dev.md
- task.py start without implementation consent
- Spawning implementer without approval
- Writing `finish.md` before explicit Finish consent
- `git commit` / `task.py archive` before Finish consent is recorded in `finish.md`

Soft warning (allow with reason):
- Editing lockfiles
- Editing generated files
- Modifying shared types
- Modifying env example / config files
- Changing (not deleting) migrations
- Large-scale formatting

Override (soft warnings only):
- User says "override team-kit guardrail: <reason>"
- Hard blocks CANNOT be overridden

Trigger: PreToolUse (before Bash, Write, Edit tools)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from typing import Optional

if sys.platform.startswith("win"):
    import io as _io
    for _stream_name in ("stdin", "stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        elif hasattr(_stream, "detach"):
            try:
                setattr(
                    sys, _stream_name,
                    _io.TextIOWrapper(_stream.detach(), encoding="utf-8", errors="replace"),
                )
            except Exception:
                pass

TRELLIS_DIR = ".trellis"
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR / "lib"))

from task_artifacts import parse_implementation_approval  # type: ignore[import-not-found]
from task_artifacts import (  # type: ignore[import-not-found]
    finish_approval_complete,
    implementation_approval_complete,
    parse_finish_approval,
)
from scope_manifest import (  # type: ignore[import-not-found]
    format_declared_scope,
    is_path_declared,
    load_scope_contract,
)

# ---- Hard block: dangerous bash command patterns ----
BLOCKED_BASH_PATTERNS = [
    (r"\brm\s+.*-rf\b",
     "BLOCKED: rm -rf detected.\n"
     "  Blocked action: Recursive force delete\n"
     "  Reason: Irreversible file deletion.\n"
     "  Correct next step: Use targeted file deletion instead."),
    (r"\bgit\s+reset\s+--hard\b",
     "BLOCKED: git reset --hard detected.\n"
     "  Blocked action: Hard reset\n"
     "  Reason: Destroys uncommitted work irreversibly.\n"
     "  Correct next step: Use git stash or git checkout instead."),
    (r"\bgit\s+clean\s+-fd\b",
     "BLOCKED: git clean -fd detected.\n"
     "  Blocked action: Force delete untracked files\n"
     "  Reason: Irreversibly removes untracked files.\n"
     "  Correct next step: Remove files individually."),
    (r"\bgit\s+push\s+.*--force\b",
     "BLOCKED: Force push detected.\n"
     "  Blocked action: Force push\n"
     "  Reason: Overwrites remote history, can destroy teammates' work.\n"
     "  Correct next step: Use regular push or coordinate with team."),
    (r"\bgit\s+push\s+-f\b",
     "BLOCKED: Force push detected.\n"
     "  Blocked action: Force push\n"
     "  Reason: Overwrites remote history, can destroy teammates' work.\n"
     "  Correct next step: Use regular push or coordinate with team."),
    (r"\bgit\s+push\s+--force-with-lease\b",
     "BLOCKED: Force push (--force-with-lease) detected.\n"
     "  Blocked action: Force push\n"
     "  Reason: Overwrites remote history.\n"
     "  Correct next step: Use regular push."),
]

# ---- Hard block: dangerous file patterns ----
BLOCKED_FILE_PATTERNS = [
    (r"(^|/)\.env$",
     "BLOCKED: Editing .env file.\n"
     "  Reason: .env files may contain secrets and credentials.\n"
     "  Correct next step: Edit .env manually, or use .env.example."),
    (r"(^|/)\.env\.local",
     "BLOCKED: Editing .env.local file.\n"
     "  Reason: Local env files may contain secrets.\n"
     "  Correct next step: Edit manually."),
    (r"(^|/)secrets?\.(json|yaml|yml|toml|env|py)",
     "BLOCKED: Editing secrets file.\n"
     "  Reason: Secrets files must not be edited through AI tools.\n"
     "  Correct next step: Edit manually."),
    (r"(^|/)credentials?\.(json|yaml|yml|env)",
     "BLOCKED: Editing credentials file.\n"
     "  Reason: Credentials files must not be edited through AI tools.\n"
     "  Correct next step: Edit manually."),
    (r"/migrations?/\d+_",
     "BLOCKED: Deleting migration file.\n"
     "  Reason: Deleting applied migrations can break database state.\n"
     "  Correct next step: Create a new migration instead."),
]

# ---- Soft warning patterns ----
SOFT_WARNING_PATTERNS = [
    (r"(^|/)package-lock\.json$", "lockfile"),
    (r"(^|/)yarn\.lock$", "lockfile"),
    (r"(^|/)pnpm-lock\.yaml$", "lockfile"),
    (r"(^|/)Cargo\.lock$", "lockfile"),
    (r"(^|/)Gemfile\.lock$", "lockfile"),
    (r"(^|/)poetry\.lock$", "lockfile"),
    (r"(^|/)go\.sum$", "lockfile"),
    (r"\.generated\.", "generated file"),
    (r"(^|/)generated/", "generated file"),
    (r"(^|/)__generated__/", "generated file"),
    (r"(^|/)(shared|common)/", "shared types"),
    (r"\.d\.ts$", "generated type declarations"),
    (r"\.generated\.\w+$", "generated file"),
    (r"(^|/)\.env\.example$", "env example"),
    (r"(^|/)\.env\.\w+\.example$", "env example"),
    (r"(^|/)docker-compose\.", "infrastructure config"),
    (r"(^|/)Dockerfile", "infrastructure config"),
    (r"(^|/)\.github/workflows/", "CI config"),
    (r"(^|/)\.gitlab-ci\.yml$", "CI config"),
    (r"(^|/)Jenkinsfile", "CI config"),
    (r"/migrations?/\w+\.(py|sql|ts|js)$", "migration file"),
]

# task.py start pattern
TASK_START_PATTERN = re.compile(r"task\.py\s+start\b")
TASK_ARCHIVE_PATTERN = re.compile(r"task\.py\s+archive\b")
GIT_COMMIT_PATTERN = re.compile(r"\bgit\s+commit\b")
FINALIZE_ARCHIVE_PATTERN = re.compile(r"finalize_task_archive\.py\b")
OMC_EXECUTABLE_PATTERN = re.compile(
    r"(?:^|[\s;|&()\"'`])(?P<exe>(?:[^\s;|&()\"'`]+/)?(?:ulw|ultrawork))(?=$|[\s;|&()\"'`])",
    re.IGNORECASE,
)
OMC_ACTION_PATTERN = re.compile(
    r"(?:\b(?:run|start|spawn|launch|work|exec)\b|\B--parallel\b)",
    re.IGNORECASE,
)
COMMAND_SEPARATOR_PATTERN = re.compile(r"[;&|\n]")

# Override pattern
OVERRIDE_PATTERN = re.compile(r"override\s+team-kit\s+guardrail\s*:\s*(.+)", re.IGNORECASE)
FINISH_CONSENT_PATTERN = re.compile(
    r"(?i)("
    r"进入\s*finish|进入\s*phase\s*3|进入\s*收尾|开始\s*finish|开始\s*收尾|"
    r"finish\s*阶段|收尾阶段|enter\s+finish|start\s+finish|proceed\s+to\s+finish"
    r")"
)

# Planning states
PLANNING_STATES = {
    "PLANNING_PRD", "PLANNING_GRILL", "PLANNING_DESIGN",
    "PLANNING_IMPLEMENT", "WAITING_IMPLEMENTATION_APPROVAL",
}

# Hard-blocked commands that CANNOT be overridden
HARD_BLOCKED_COMMANDS = {
    "rm -rf", "git reset --hard", "git push --force",
    "git push -f", "git clean -fd",
}

# Source file extensions
SOURCE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".kt", ".swift", ".c", ".cpp", ".h", ".hpp", ".rb", ".php",
    ".cs", ".scala", ".sh", ".bash", ".zsh", ".sql", ".vue", ".svelte",
}

HIGH_RISK_PATTERNS = [
    r"(^|/)auth/",
    r"(^|/)authentication/",
    r"(^|/)migrations?/",
    r"(^|/)schema\.",
    r"(^|/)api/",
    r"(^|/)routes/",
    r"(^|/)endpoints/",
    r"(^|/)(shared|common)/types",
    r"(^|/)contracts?/",
    r"(^|/)proto/",
]


def _find_trellis_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _get_task_status(root: Path) -> Optional[str]:
    active_file = root / TRELLIS_DIR / "active-task"
    if not active_file.is_file():
        return None
    try:
        ref = active_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not ref:
        return None

    task_dir = Path(ref)
    if not task_dir.is_absolute():
        task_dir = root / ref

    task_json = task_dir / "task.json"
    if task_json.is_file():
        try:
            data = json.loads(task_json.read_text(encoding="utf-8"))
            return data.get("status", "")
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _get_task_dir(root: Path) -> Optional[Path]:
    active_file = root / TRELLIS_DIR / "active-task"
    if not active_file.is_file():
        return None
    try:
        ref = active_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not ref:
        return None
    task_dir = Path(ref)
    if not task_dir.is_absolute():
        task_dir = root / ref
    return task_dir


def _is_planning_phase(status: Optional[str]) -> bool:
    if not status:
        return False
    return status.lower() == "planning" or status.upper() in PLANNING_STATES


def _is_source_file(file_path: str) -> bool:
    if file_path.startswith(".trellis/") or file_path.startswith(".claude/"):
        return False
    _, ext = os.path.splitext(file_path)
    return ext.lower() in SOURCE_EXTS


def _normalize_repo_path(root: Path, file_path: str) -> str:
    path_obj = Path(file_path)
    if path_obj.is_absolute():
        try:
            return path_obj.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return path_obj.as_posix()

    normalized = file_path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_high_risk_path(file_path: str) -> bool:
    norm = file_path.replace("\\", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, norm):
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


def _omc_approval_complete(task_dir: Optional[Path]) -> bool:
    if task_dir is None:
        return False
    implement_md = task_dir / "implement.md"
    if not implement_md.is_file():
        return False
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return False

    section = _extract_markdown_section(content, "Execution Mode Decision")
    checked = _checked_labels_in_section(section)
    if "user explicitly approved omc" not in checked:
        return False

    placeholders = {"", "tbd", "todo", "n/a", "none", "-"}
    user_message = _section_field_value(section, "user message").lower()
    timestamp = _section_field_value(section, "timestamp").lower()
    return user_message not in placeholders and timestamp not in placeholders


def _omc_start_requested(command: str) -> bool:
    for match in OMC_EXECUTABLE_PATTERN.finditer(command):
        segment = command[match.end("exe"):]
        separator = COMMAND_SEPARATOR_PATTERN.search(segment)
        if separator:
            segment = segment[:separator.start()]
        if OMC_ACTION_PATTERN.search(segment):
            return True
    return False


def _check_override(input_data: dict) -> Optional[str]:
    """Check if user provided an override reason. Only applies to soft warnings."""
    prompt = input_data.get("prompt", "") or input_data.get("message", "") or ""
    if isinstance(prompt, str):
        m = OVERRIDE_PATTERN.search(prompt)
        if m:
            return m.group(1).strip()
    return None


def _write_override_ledger(
    task_dir: Optional[Path],
    *,
    decision: str,
    reason: str,
    message: str,
    input_data: dict,
) -> None:
    if task_dir is None:
        return

    tool_name = input_data.get("tool_name", "") or input_data.get("toolName", "")
    tool_input = input_data.get("tool_input", {}) or input_data.get("toolInput", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    file_path = tool_input.get("file_path", "") or tool_input.get("filePath", "")
    command = tool_input.get("command", "")
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "kind": "soft_warning" if decision == "accepted" else "hard_block_override_attempt",
        "decision": decision,
        "reason": reason,
        "tool_name": tool_name,
        "message": message.splitlines()[0] if message else "",
    }
    if isinstance(file_path, str) and file_path:
        entry["path"] = file_path
    if isinstance(command, str) and command:
        entry["command"] = command

    runtime_dir = task_dir / "runtime"
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        with open(runtime_dir / "guardrail-overrides.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _extract_prompt_text(input_data: dict) -> str:
    for field in ("prompt", "message", "text", "content"):
        value = input_data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    nested = input_data.get("result")
    if isinstance(nested, dict):
        for field in ("prompt", "message", "text", "content"):
            value = nested.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def _has_explicit_finish_consent(input_data: dict) -> bool:
    prompt = _extract_prompt_text(input_data)
    return bool(prompt and FINISH_CONSENT_PATTERN.search(prompt))


def _missing_implementation_approval_fields(approval: dict[str, str | bool]) -> list[str]:
    missing: list[str] = []
    if not approval.get("approved"):
        missing.append("approved")
    if not approval.get("start_allowed"):
        missing.append("Allowed to run task.py start? -> yes")
    for field in ("user_message", "timestamp", "summary_approved"):
        value = str(approval.get(field, "")).strip()
        if not value:
            missing.append(field.replace("_", " "))
    return missing


def _finish_artifact_recorded(task_dir: Optional[Path]) -> bool:
    if task_dir is None:
        return False
    return finish_approval_complete(parse_finish_approval(task_dir / "finish.md"))


def _is_local_state_path(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/").strip()
    if not normalized:
        return False
    if normalized == ".claude/settings.local.json":
        return True
    if normalized == ".trellis/.developer" or normalized.startswith(".trellis/.developer/"):
        return True
    parts = normalized.split("/")
    return ".omc" in parts


def _finish_workspace_issue(root: Path) -> Optional[str]:
    prepare_script = root / ".trellis" / "scripts" / "prepare_finish_workspace.py"
    if not prepare_script.is_file():
        return None

    tracked_local: list[str] = []
    dirty_local: list[str] = []

    try:
        tracked = subprocess.run(
            ["git", "ls-files", "-z"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            cwd=str(root),
        )
        if tracked.returncode == 0:
            tracked_local = [
                path for path in tracked.stdout.split("\0")
                if path and _is_local_state_path(path)
            ]
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        tracked_local = []

    try:
        dirty = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            cwd=str(root),
        )
        if dirty.returncode == 0:
            for line in dirty.stdout.splitlines():
                if not line.strip():
                    continue
                path = line[3:].strip()
                if _is_local_state_path(path):
                    dirty_local.append(line.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        dirty_local = []

    if tracked_local or dirty_local:
        detail_lines: list[str] = []
        if tracked_local:
            detail_lines.append("tracked local-state paths: " + ", ".join(tracked_local[:10]))
        if dirty_local:
            detail_lines.append("dirty local-state paths: " + ", ".join(dirty_local[:10]))
        detail = "\n".join(f"  - {line}" for line in detail_lines)
        return (
            "BLOCKED: git commit is forbidden while local runtime state is still in scope.\n"
            "  Blocked action: git commit\n"
            "  Reason: `.omc/` / local-only state must be cleaned before the final commit, "
            "otherwise finish can still end in a dirty repository.\n"
            f"{detail}\n"
            "  Correct next step: run "
            "`python3 ./.trellis/scripts/prepare_finish_workspace.py`, review the resulting "
            "git diff, then retry the commit."
        )

    return None


def _check_bash_command(command: str, root: Path) -> tuple[Optional[str], bool]:
    """Check bash command. Returns (message, is_hard_block)."""
    for pattern, message in BLOCKED_BASH_PATTERNS:
        if re.search(pattern, command):
            return message, True

    if _omc_start_requested(command) and not _omc_approval_complete(_get_task_dir(root)):
        return (
            "BLOCKED: OMC execution requires explicit user approval.\n"
            "  Blocked action: ulw/ultrawork command\n"
            "  Reason: OMC parallel execution must be approved and recorded in "
            "implement.md before runtime startup.\n"
            "  Correct next step: Record 'user explicitly approved OMC', user message, "
            "and timestamp in the Execution Mode Decision, then retry."
        ), True

    if TASK_START_PATTERN.search(command):
        status = _get_task_status(root)
        task_dir = _get_task_dir(root)
        if _is_planning_phase(status):
            approval = (
                parse_implementation_approval(task_dir / "implement.md")
                if task_dir is not None
                else None
            )
            if approval and implementation_approval_complete(approval):
                return None, False
            missing = _missing_implementation_approval_fields(approval or {})
            return (
                "BLOCKED: task.py start is forbidden during planning phase.\n"
                "  Current state: PLANNING\n"
                "  Blocked action: task.py start\n"
                "  Reason: Implementation approval has not been written back into "
                "implement.md.\n"
                "  Correct next step: Wait for explicit user approval, then update "
                "implement.md Implementation Approval by marking 'approved', filling "
                "user message / timestamp / summary approved, and marking "
                "'Allowed to run task.py start? -> yes'.\n"
                f"  Missing fields: {', '.join(missing)}"
            ), True

    if TASK_ARCHIVE_PATTERN.search(command) and not FINALIZE_ARCHIVE_PATTERN.search(command):
        return (
            "BLOCKED: direct `task.py archive` is forbidden.\n"
            "  Blocked action: task.py archive\n"
            "  Reason: team-kit archive finalization must normalize archived JSONL context, "
            "sync workspace journal/index, and run post-archive validators.\n"
            "  Correct next step: run "
            "`python3 ./.trellis/scripts/finalize_task_archive.py <task-dir>` instead."
        ), True

    if GIT_COMMIT_PATTERN.search(command):
        workspace_issue = _finish_workspace_issue(root)
        if workspace_issue:
            return workspace_issue, True

    if GIT_COMMIT_PATTERN.search(command) or TASK_ARCHIVE_PATTERN.search(command):
        status = _get_task_status(root)
        task_dir = _get_task_dir(root)
        if status and status.lower() == "in_progress" and not _finish_artifact_recorded(task_dir):
            action = "git commit" if GIT_COMMIT_PATTERN.search(command) else "task.py archive"
            return (
                f"BLOCKED: {action} is forbidden before explicit Finish consent is recorded.\n"
                "  Current state: IN_PROGRESS\n"
                f"  Blocked action: {action}\n"
                "  Reason: finish.md does not yet contain a complete Finish Approval "
                "record with user message / timestamp / summary and "
                "'Allowed to proceed with finish? -> yes'.\n"
                "  Correct next step: Wait for the user to explicitly enter Finish, "
                "record that consent in finish.md, then continue with spec update / commit / archive."
            ), True

    return None, False


def _check_file_operation(
    file_path: str,
    tool_name: str,
    root: Path,
    input_data: dict,
) -> tuple[Optional[str], bool]:
    """Check file write/edit. Returns (message, is_hard_block)."""
    norm_path = _normalize_repo_path(root, file_path)

    # Check hard-blocked file patterns
    for pattern, message in BLOCKED_FILE_PATTERNS:
        if re.search(pattern, norm_path):
            return message, True

    task_dir = _get_task_dir(root)
    status = _get_task_status(root)
    if tool_name in ("Write", "Edit") and task_dir is not None:
        try:
            finish_rel = (task_dir / "finish.md").resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            finish_rel = ""
        if finish_rel and norm_path == finish_rel and status and status.lower() == "in_progress":
            recorded = parse_finish_approval(task_dir / "finish.md")
            if finish_approval_complete(recorded) or _has_explicit_finish_consent(input_data):
                return None, False
            return (
                "BLOCKED: Writing finish.md without explicit Finish consent.\n"
                "  Current state: IN_PROGRESS\n"
                "  Blocked action: Write/Edit finish.md\n"
                "  Reason: Finish is a separate user-approved phase. "
                "The user must explicitly say to enter Finish before finish.md "
                "can be created or edited.\n"
                "  Correct next step: Wait for a message such as '进入 Finish 阶段', "
                "then record that approval in the Finish Approval section."
            ), True

    # Source file editing during planning phase
    if tool_name in ("Write", "Edit") and _is_source_file(norm_path):
        if _is_planning_phase(status):
            return (
                "BLOCKED: Editing source files during planning phase.\n"
                "  Current state: PLANNING\n"
                "  Blocked action: Write/Edit to source file\n"
                "  Reason: Task creation approval is NOT implementation approval.\n"
                "  Correct next step: Complete planning artifacts and wait for "
                "user to explicitly approve implementation."
            ), True

        if status and status.lower() == "in_progress":
            if task_dir:
                approval = parse_implementation_approval(task_dir / "implement.md")
                if not implementation_approval_complete(approval):
                    return (
                        "BLOCKED: Editing source files without recorded implementation approval.\n"
                        "  Current state: IN_PROGRESS\n"
                        "  Blocked action: Write/Edit to source file\n"
                        "  Reason: implement.md does not show an approved implementation "
                        "consent record with full audit fields.\n"
                        "  Correct next step: Update the Implementation Approval section "
                        "in implement.md from the user's approval before continuing."
                    ), True
            if task_dir and not (task_dir / "before-dev.md").is_file():
                return (
                    "BLOCKED: Editing source files without before-dev constraints.\n"
                    "  Current state: IN_PROGRESS\n"
                    "  Blocked action: Write/Edit to source file\n"
                    "  Reason: trellis-before-dev has not been completed. "
                    "Run trellis-before-dev first to read all artifacts and "
                    "output implementation constraints.\n"
                    "  Correct next step: Run trellis-before-dev skill, then "
                    "create before-dev.md in the task directory."
                ), True

            if task_dir and (task_dir / "before-dev.md").is_file():
                implement_md = task_dir / "implement.md"
                declared_paths, declared_globs, high_risk_allowed, scope_source = load_scope_contract(task_dir, implement_md)
                if (
                    (declared_paths or declared_globs)
                    and not is_path_declared(norm_path, declared_paths, declared_globs)
                ):
                    if _is_high_risk_path(norm_path):
                        return (
                            f"WARNING: Editing high-risk undeclared path: {norm_path}\n"
                            f"  Current state: IN_PROGRESS\n"
                            f"  Warned action: Write/Edit to source file\n"
                            f"  Reason: This file is in a high-risk area (auth, migration, "
                            f"schema, API contract, shared types) and is NOT declared in "
                            f"{scope_source}.\n"
                            f"  Declared scope: {format_declared_scope(declared_paths, declared_globs)}\n"
                            f"  Correct next step: Either add this path to implement.md, "
                            f"or use 'override team-kit guardrail: <reason>' if intentional."
                        ), False
                    return (
                        f"WARNING: Editing undeclared source path: {norm_path}\n"
                        f"  Current state: IN_PROGRESS\n"
                        f"  Warned action: Write/Edit to source file\n"
                        f"  Reason: This source file is NOT declared in {scope_source}.\n"
                        f"  Declared scope: {format_declared_scope(declared_paths, declared_globs)}\n"
                        f"  Correct next step: Either add this path to implement.md or "
                        f"scope-manifest.json, or use "
                        f"'override team-kit guardrail: <reason>' if intentional."
                    ), False
                if (
                    (declared_paths or declared_globs)
                    and is_path_declared(norm_path, declared_paths, declared_globs)
                    and _is_high_risk_path(norm_path)
                    and not is_path_declared(norm_path, high_risk_allowed, high_risk_allowed)
                ):
                    return (
                        f"WARNING: Editing high-risk path without high_risk_allowed: {norm_path}\n"
                        f"  Current state: IN_PROGRESS\n"
                        f"  Warned action: Write/Edit to source file\n"
                        f"  Reason: This file is in a high-risk area and is declared in "
                        f"{scope_source}, but it is not listed in high_risk_allowed.\n"
                        f"  High-risk allowlist: {format_declared_scope(high_risk_allowed, [])}\n"
                        f"  Correct next step: Add this exact high-risk path or glob to "
                        f"scope-manifest.json high_risk_allowed, or use "
                        f"'override team-kit guardrail: <reason>' if intentional."
                    ), False

    # Check soft warning patterns
    if tool_name in ("Write", "Edit"):
        for pattern, category in SOFT_WARNING_PATTERNS:
            if re.search(pattern, norm_path):
                return (
                    f"WARNING: Editing {category} file: {norm_path}\n"
                    f"  Reason: Changes to {category} files can have broad impact.\n"
                    f"  Verify the change is intentional.\n"
                    f"  To bypass: say 'override team-kit guardrail: <reason>'"
                ), False

    return None, False


def _emit_deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def _emit_allow(reason: str | None = None) -> None:
    output: dict = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
    }
    if reason:
        output["permissionDecisionReason"] = reason
    print(json.dumps({"hookSpecificOutput": output}, ensure_ascii=False))
    sys.exit(0)


def _emit_warn(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    cwd_str = input_data.get("cwd") or os.getcwd()
    root = _find_trellis_root(Path(cwd_str))
    if root is None:
        return 0

    tool_name = input_data.get("tool_name", "") or input_data.get("toolName", "")
    tool_input = input_data.get("tool_input", {}) or input_data.get("toolInput", {})

    message: Optional[str] = None
    is_hard_block = False

    if tool_name.lower() == "bash":
        command = tool_input.get("command", "")
        if isinstance(command, str) and command:
            message, is_hard_block = _check_bash_command(command, root)

    elif tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "") or tool_input.get("filePath", "")
        if isinstance(file_path, str) and file_path:
            message, is_hard_block = _check_file_operation(file_path, tool_name, root, input_data)

    if not message:
        return 0

    if is_hard_block:
        # Check for override attempt on hard blocks — always deny
        override_reason = _check_override(input_data)
        if override_reason:
            _write_override_ledger(
                _get_task_dir(root),
                decision="denied",
                reason=override_reason,
                message=message,
                input_data=input_data,
            )
            _emit_deny(
                f"{message}\n\n"
                f"Override attempted with reason: {override_reason}\n"
                f"OVERRIDE DENIED: Hard blocks cannot be overridden. "
                f"User must explicitly confirm this action outside team-kit guardrails."
            )
        _emit_deny(message)

    # Soft warning — check for override
    override_reason = _check_override(input_data)
    if override_reason:
        _write_override_ledger(
            _get_task_dir(root),
            decision="accepted",
            reason=override_reason,
            message=message,
            input_data=input_data,
        )
        _emit_allow(f"Guardrail override accepted: {override_reason}")
    else:
        _emit_warn(message)

    return 0


if __name__ == "__main__":
    sys.exit(main())
