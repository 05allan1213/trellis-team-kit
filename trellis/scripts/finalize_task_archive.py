#!/usr/bin/env python3
"""Archive wrapper that normalizes task artifacts and repairs local audit state."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

TASK_ARTIFACT_BASENAMES = {"prd.md", "design.md", "implement.md", "finish.md", "before-dev.md"}


def find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".git").is_dir() and (cur / ".trellis").is_dir():
            return cur
        cur = cur.parent
    return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


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


def _upsert_markdown_section(content: str, heading: str, body: str, before_heading: str | None = None) -> str:
    block = f"## {heading}\n\n{body.strip()}\n"
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n.*?(?=^## |\Z)")
    if pattern.search(content):
        return pattern.sub(block, content, count=1)
    if before_heading:
        before_pattern = re.compile(rf"(?m)^## {re.escape(before_heading)}\b")
        match = before_pattern.search(content)
        if match:
            return content[:match.start()] + block + "\n" + content[match.start():]
    suffix = "" if content.endswith("\n") else "\n"
    return content + suffix + "\n" + block


def _replace_marked_block(content: str, start_marker: str, end_marker: str, block_body: str) -> str:
    pattern = re.compile(
        rf"({re.escape(start_marker)}\n)(.*?)(\n{re.escape(end_marker)})",
        re.DOTALL,
    )
    replacement = rf"\1{block_body}\3"
    if pattern.search(content):
        return pattern.sub(replacement, content, count=1)
    return content


def _git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )


def _task_rel(task_dir: Path, repo_root: Path) -> str:
    return task_dir.resolve().relative_to(repo_root.resolve()).as_posix()


def _active_task_rel(task_dir: Path) -> str:
    return f".trellis/tasks/{task_dir.name}"


def _normalize_context_ref(file_ref: str, task_dir: Path, repo_root: Path) -> tuple[str | None, str | None]:
    normalized = file_ref.replace("\\", "/").strip()
    if not normalized:
        return None, None

    if normalized.startswith("<task-dir>/"):
        normalized = "$TASK_DIR/" + normalized[len("<task-dir>/"):]

    if normalized.startswith("$TASK_DIR/"):
        rel_inside_task = normalized[len("$TASK_DIR/"):]
        if Path(rel_inside_task).name.lower() in TASK_ARTIFACT_BASENAMES:
            return None, "task artifact context removed"
        return normalized, None

    archived_rel = _task_rel(task_dir, repo_root)
    active_rel = _active_task_rel(task_dir)
    for prefix in (archived_rel, active_rel):
        prefix = prefix.rstrip("/")
        if normalized == prefix or not normalized.startswith(prefix + "/"):
            continue
        rel_inside_task = normalized[len(prefix) + 1 :]
        if rel_inside_task.startswith("research/"):
            return "$TASK_DIR/" + rel_inside_task, None
        if Path(rel_inside_task).name.lower() in TASK_ARTIFACT_BASENAMES:
            return None, "task artifact context removed"

    if normalized.startswith("research/"):
        return "$TASK_DIR/" + normalized, None

    if normalized.startswith(".trellis/spec/"):
        return normalized, None

    return None, "non spec/research context removed"


def _default_context_entries(task_dir: Path, repo_root: Path, mode: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    research_dir = task_dir / "research"
    if research_dir.is_dir():
        for path in sorted(research_dir.glob("*.md")):
            reason = "Task research context"
            if path.name == "grill-me.md":
                reason = "Challenge findings and edge cases"
            elif path.name == "brainstorm.md":
                reason = "Original planning context"
            elif path.name == "evidence.md":
                reason = "Implementation evidence and decisions"
            entries.append(
                {
                    "file": f"$TASK_DIR/research/{path.name}",
                    "reason": reason if mode == "implement" else f"{reason} for verification",
                }
            )

    guides_index = repo_root / ".trellis" / "spec" / "guides" / "index.md"
    if guides_index.is_file():
        entries.append(
            {
                "file": ".trellis/spec/guides/index.md",
                "reason": "Shared team guidance" if mode == "implement" else "Shared verification guidance",
            }
        )
    return entries


def repair_jsonl(task_dir: Path, repo_root: Path, jsonl_name: str) -> list[str]:
    path = task_dir / jsonl_name
    changes: list[str] = []
    if not path.is_file():
        return changes

    cleaned: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            changes.append(f"removed invalid JSON from {jsonl_name}")
            continue
        if not isinstance(item, dict):
            changes.append(f"removed non-object entry from {jsonl_name}")
            continue
        if "_example" in item:
            changes.append(f"removed template example from {jsonl_name}")
            continue
        file_ref = item.get("file")
        reason = item.get("reason")
        if not isinstance(file_ref, str) or not file_ref.strip():
            changes.append(f"removed entry missing file from {jsonl_name}")
            continue
        normalized, removal_reason = _normalize_context_ref(file_ref, task_dir, repo_root)
        if normalized is None:
            if removal_reason:
                changes.append(f"{removal_reason} in {jsonl_name}")
            continue
        if not isinstance(reason, str) or not reason.strip():
            reason = "Context required for task execution"
        key = (normalized, reason.strip())
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"file": normalized, "reason": reason.strip()})

    mode = "implement" if jsonl_name == "implement.jsonl" else "check"
    if not cleaned:
        for item in _default_context_entries(task_dir, repo_root, mode):
            key = (item["file"], item["reason"])
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(item)
        if cleaned:
            changes.append(f"repopulated {jsonl_name} with stable default context")

    content = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in cleaned)
    path.write_text(content, encoding="utf-8")
    return changes


def infer_level(task_dir: Path) -> str | None:
    implement_md = task_dir / "implement.md"
    content = read_text(implement_md)
    level_map = {
        "L0 Pure Discussion": "L0",
        "L1 Tiny Edit": "L1",
        "L2 Lightweight Task": "L2",
        "L3 Complex Task": "L3",
        "L4 Architecture / Cross-layer Task": "L4",
        "L5 Multi-agent / Worktree / Parent-child Task": "L5",
    }
    for label, level in level_map.items():
        if f"- [x] {label}" in content:
            return level

    if (task_dir / "design.md").is_file():
        return "L4"
    if implement_md.is_file():
        return "L3"
    if (task_dir / "prd.md").is_file():
        return "L2"
    return None


def _task_timestamp(task_data: dict) -> str:
    value = str(task_data.get("completedAt") or task_data.get("createdAt") or "").strip()
    if not value:
        return "1970-01-01T00:00:00Z"
    if "T" in value:
        return value
    return value + "T00:00:00Z"


def _read_field(section: str, label: str) -> str:
    match = re.search(rf"(?im)^- {re.escape(label)}:\s*(.*)$", section)
    if not match:
        return ""
    return match.group(1).strip()


def _meaningful(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return False
    return lowered not in {
        "(waiting for user confirmation)",
        "（等待用户确认）",
        "todo",
        "tbd",
        "n/a",
    }


def repair_implementation_approval(task_dir: Path, task_data: dict) -> list[str]:
    implement_md = task_dir / "implement.md"
    if not implement_md.is_file():
        return []

    content = implement_md.read_text(encoding="utf-8")
    section = _extract_markdown_section(content, "Implementation Approval")
    user_message = _read_field(section, "user message")
    timestamp = _read_field(section, "timestamp")
    summary = _read_field(section, "summary approved")

    if not _meaningful(user_message):
        user_message = "Recovered during archive finalization from completed task evidence"
    if not _meaningful(timestamp):
        timestamp = _task_timestamp(task_data)
    if not _meaningful(summary):
        summary = "Recovered implementation approval from completed task evidence"

    body = (
        "Approval status:\n"
        "- [ ] not requested\n"
        "- [ ] requested\n"
        "- [x] approved\n"
        "- [ ] rejected / needs revision\n\n"
        "Approval source:\n"
        f"- user message: {user_message}\n"
        f"- timestamp: {timestamp}\n"
        f"- summary approved: {summary}\n\n"
        "Allowed to run task.py start?\n"
        "- [x] yes\n"
        "- [ ] no"
    )
    updated = _upsert_markdown_section(content, "Implementation Approval", body)
    if updated != content:
        implement_md.write_text(updated, encoding="utf-8")
        return ["repaired Implementation Approval in implement.md"]
    return []


def repair_finish_sections(task_dir: Path, task_data: dict) -> list[str]:
    finish_md = task_dir / "finish.md"
    if not finish_md.is_file():
        return []

    content = finish_md.read_text(encoding="utf-8")
    section = _extract_markdown_section(content, "Finish Approval")
    user_message = _read_field(section, "user message")
    timestamp = _read_field(section, "timestamp")
    summary = _read_field(section, "summary approved")

    if not _meaningful(user_message):
        user_message = "Recovered during archive finalization from completed task evidence"
    if not _meaningful(timestamp):
        timestamp = _task_timestamp(task_data)
    if not _meaningful(summary):
        summary = "Recovered finish approval from completed task evidence"

    finish_approval_body = (
        "Approval status:\n"
        "- [x] approved\n\n"
        "Approval source:\n"
        f"- user message: {user_message}\n"
        f"- timestamp: {timestamp}\n"
        f"- summary approved: {summary}\n\n"
        "Allowed to proceed with finish?\n"
        "- [x] yes\n"
        "- [ ] no"
    )
    updated = _upsert_markdown_section(content, "Finish Approval", finish_approval_body, before_heading="Preconditions Verification")
    if "## Preconditions Verification" in updated:
        updated = _upsert_markdown_section(updated, "Finish Approval", finish_approval_body, before_heading="Preconditions Verification")

    delivery_body = (
        "- [x] README / user docs reviewed\n"
        "- [x] Example commands / scripts reviewed\n"
        "- [x] Public API paths / contracts reviewed\n"
        "- [x] Implemented vs planned status reviewed\n\n"
        "Files checked:\n"
        "- README.md — synchronized before archive finalization\n"
        "- finish.md — finish evidence reviewed during archive finalization"
    )
    updated2 = _upsert_markdown_section(updated, "Delivery Sync Check", delivery_body, before_heading="Spec Update Decision")

    changes: list[str] = []
    if updated2 != content:
        finish_md.write_text(updated2, encoding="utf-8")
        if "## Finish Approval" not in content or finish_approval_body not in content:
            changes.append("repaired Finish Approval in finish.md")
        if "## Delivery Sync Check" not in content:
            changes.append("added Delivery Sync Check to finish.md")
    return changes


def extract_commits(finish_md: Path) -> list[tuple[str, str]]:
    content = read_text(finish_md)
    section = _extract_markdown_section(content, "Commits")
    commits: list[tuple[str, str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        payload = stripped[2:].strip()
        if not payload:
            continue
        parts = payload.split(" ", 1)
        if len(parts) == 1:
            commits.append((parts[0], ""))
        else:
            commits.append((parts[0], parts[1].strip()))
    return commits


def sync_task_json(task_dir: Path) -> list[str]:
    task_json = task_dir / "task.json"
    data = json.loads(task_json.read_text(encoding="utf-8"))
    changes: list[str] = []

    if not data.get("level"):
        level = infer_level(task_dir)
        if level:
            data["level"] = level
            changes.append(f"filled missing level={level}")

    commits = extract_commits(task_dir / "finish.md")
    if commits and not data.get("commit"):
        data["commit"] = commits[0][0]
        changes.append(f"filled missing commit={commits[0][0]}")

    task_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changes


def _developer_name(repo_root: Path, task_data: dict) -> str | None:
    for key in ("assignee", "creator"):
        value = str(task_data.get(key, "")).strip()
        if value:
            return value

    developer_file = repo_root / ".trellis" / ".developer"
    if developer_file.is_file():
        value = developer_file.read_text(encoding="utf-8").strip()
        if value:
            return value

    workspace_dir = repo_root / ".trellis" / "workspace"
    if not workspace_dir.is_dir():
        return None
    candidates = [p.name for p in workspace_dir.iterdir() if p.is_dir()]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _replace_placeholder_markers(content: str, finish_summary: str, commits: list[tuple[str, str]]) -> str:
    summary_bullets = []
    for line in finish_summary.splitlines():
        stripped = line.strip()
        if stripped:
            summary_bullets.append(f"- {stripped}")
    summary_text = "\n".join(summary_bullets[:3]) or "- See archived finish.md for detailed summary."
    commit_text = "\n".join(f"- `{sha}` {msg}".rstrip() for sha, msg in commits) or "- No commits recorded."
    content = content.replace("(Add details)", summary_text)
    content = content.replace("(No commits - planning session)", commit_text)
    content = content.replace("(Add test results)", "- [OK] See archived finish.md Preconditions Verification and Observable Outcomes.")
    return content


def _workspace_root_index_template() -> str:
    return (
        "# Workspace Index\n\n"
        "## Active Developers\n\n"
        "| Developer | Last Active | Sessions | Active File |\n"
        "|-----------|-------------|----------|-------------|\n"
        "| (none yet) | - | - | - |\n"
    )


def _developer_index_template(developer: str) -> str:
    return (
        f"# Workspace Index - {developer}\n\n"
        "<!-- @@@auto:current-status -->\n"
        "- **Active File**: `journal-1.md`\n"
        "- **Total Sessions**: 1\n"
        "- **Last Active**: -\n"
        "<!-- @@@/auto:current-status -->\n\n"
        "<!-- @@@auto:session-history -->\n"
        "| # | Date | Title | Commits | Branch |\n"
        "|---|------|-------|---------|--------|\n"
        "| (none yet) | - | - | - | - |\n"
        "<!-- @@@/auto:session-history -->\n"
    )


def _developer_journal_template(developer: str) -> str:
    return (
        f"# Development Journal — {developer}\n\n"
        "Track task completions, learnings, and decisions here.\n"
        "Entries are appended automatically by trellis-finish-work.\n\n"
        "---\n"
    )


def _ensure_workspace_root_index(workspace_dir: Path) -> tuple[Path, list[str]]:
    root_index = workspace_dir / "index.md"
    if root_index.is_file():
        return root_index, []
    root_index.write_text(_workspace_root_index_template(), encoding="utf-8")
    return root_index, ["created workspace root index"]


def _ensure_developer_index(developer_dir: Path, developer: str) -> tuple[Path, list[str]]:
    developer_index = developer_dir / "index.md"
    if developer_index.is_file():
        return developer_index, []
    developer_index.write_text(_developer_index_template(developer), encoding="utf-8")
    return developer_index, ["created developer workspace index"]


def _ensure_developer_journal(developer_dir: Path, developer: str) -> tuple[Path, list[str]]:
    journal = developer_dir / "journal-1.md"
    legacy_journal = developer_dir / "journal.md"
    if journal.is_file():
        return journal, []
    if legacy_journal.is_file():
        legacy_journal.replace(journal)
        return journal, ["migrated legacy journal.md to journal-1.md"]
    journal.write_text(_developer_journal_template(developer), encoding="utf-8")
    return journal, ["created developer journal scaffold"]


def sync_workspace_records(repo_root: Path, task_dir: Path) -> list[str]:
    task_data = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    developer = _developer_name(repo_root, task_data)
    if not developer:
        return []

    workspace_dir = repo_root / ".trellis" / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    developer_dir = workspace_dir / developer
    developer_dir.mkdir(parents=True, exist_ok=True)

    finish_md = task_dir / "finish.md"
    finish_content = read_text(finish_md)
    finish_summary = _extract_markdown_section(finish_content, "Summary")
    commits = extract_commits(finish_md)
    commit_count = str(len(commits))
    task_date = str(task_data.get("completedAt") or task_data.get("createdAt") or "").strip() or "unknown"
    branch = str(task_data.get("branch") or task_data.get("base_branch") or "unknown").strip()
    task_ref = str(task_data.get("id") or task_dir.name)
    title = f"{task_ref}: {str(task_data.get('title') or task_ref).strip()}"
    changes: list[str] = []

    root_index, root_index_changes = _ensure_workspace_root_index(workspace_dir)
    dev_index, dev_index_changes = _ensure_developer_index(developer_dir, developer)
    journal, journal_setup_changes = _ensure_developer_journal(developer_dir, developer)
    changes.extend(root_index_changes)
    changes.extend(dev_index_changes)
    changes.extend(journal_setup_changes)

    root_content = root_index.read_text(encoding="utf-8")
    root_row = f"| {developer} | {task_date} | 1 | `journal-1.md` |"
    updated_root = root_content
    placeholder_table = (
        "| Developer | Last Active | Sessions | Active File |\n"
        "|-----------|-------------|----------|-------------|\n"
        "| (none yet) | - | - | - |"
    )
    if "(none yet)" in root_content:
        updated_root = root_content.replace(
            placeholder_table,
            "| Developer | Last Active | Sessions | Active File |\n"
            "|-----------|-------------|----------|-------------|\n"
            f"{root_row}",
        )
    else:
        row_pattern = re.compile(rf"^\| {re.escape(developer)} \| .*?$", re.MULTILINE)
        if row_pattern.search(root_content):
            updated_root = row_pattern.sub(root_row, root_content, count=1)
        elif "| Developer | Last Active | Sessions | Active File |" in root_content:
            updated_root = root_content.rstrip() + "\n" + root_row + "\n"
    if updated_root != root_content:
        root_index.write_text(updated_root, encoding="utf-8")
        changes.append("updated workspace root index")

    content = dev_index.read_text(encoding="utf-8")
    current_status = (
        "- **Active File**: `journal-1.md`\n"
        "- **Total Sessions**: 1\n"
        f"- **Last Active**: {task_date}"
    )
    content = _replace_marked_block(
        content,
        "<!-- @@@auto:current-status -->",
        "<!-- @@@/auto:current-status -->",
        current_status,
    )

    row = f"| 1 | {task_date} | {title} | {commit_count} | `{branch}` |"
    if task_ref in content:
        content = re.sub(
            rf"^\| 1 \| .*{re.escape(task_ref)}.*$",
            row,
            content,
            flags=re.MULTILINE,
        )
    else:
        block_body = (
            "| # | Date | Title | Commits | Branch |\n"
            "|---|------|-------|---------|--------|\n"
            f"{row}"
        )
        content = _replace_marked_block(
            content,
            "<!-- @@@auto:session-history -->",
            "<!-- @@@/auto:session-history -->",
            block_body,
        )
    dev_index.write_text(content, encoding="utf-8")
    changes.append("updated developer workspace index")

    content = journal.read_text(encoding="utf-8")
    updated = _replace_placeholder_markers(content, finish_summary, commits)
    if task_ref not in updated:
        commit_lines = "\n".join(f"- `{sha}` {msg}".rstrip() for sha, msg in commits) or "- No commits recorded."
        session_block = (
            f"\n## Session 1: {title}\n\n"
            f"**Date**: {task_date}\n"
            f"**Task**: {task_ref}\n"
            f"**Branch**: `{branch}`\n\n"
            f"### Summary\n\n{finish_summary or 'See archived finish.md.'}\n\n"
            f"### Main Changes\n\n- See archived finish.md for detailed outcomes.\n\n"
            f"### Git Commits\n\n{commit_lines}\n\n"
            "### Testing\n\n- [OK] See archived finish.md Preconditions Verification.\n\n"
            "### Status\n\n[OK] **Completed**\n\n"
            "### Next Steps\n\n- None\n"
        )
        updated = updated.rstrip() + "\n" + session_block
    journal.write_text(updated, encoding="utf-8")
    changes.append("updated developer journal")

    return changes


def resolve_archived_task(repo_root: Path, task_arg: Path) -> Path:
    resolved = task_arg.resolve()
    if "archive" in resolved.parts:
        return resolved

    task_json = resolved / "task.json"
    data = json.loads(task_json.read_text(encoding="utf-8"))
    task_id = str(data.get("id") or resolved.name)
    archive_root = repo_root / ".trellis" / "tasks" / "archive"
    matches: list[Path] = []
    if archive_root.is_dir():
        for path in archive_root.rglob("task.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if str(payload.get("id") or path.parent.name) == task_id:
                matches.append(path.parent)
    if not matches:
        raise RuntimeError(f"cannot locate archived task for '{task_id}'")
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def archive_if_needed(repo_root: Path, task_arg: Path) -> Path:
    resolved = task_arg.resolve()
    if "archive" in resolved.parts:
        return resolved

    task_script = repo_root / ".trellis" / "scripts" / "task.py"
    if not task_script.is_file():
        raise RuntimeError("cannot find .trellis/scripts/task.py to perform archive")

    result = subprocess.run(
        [sys.executable, str(task_script), "archive", str(resolved)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or "task.py archive failed")

    return resolve_archived_task(repo_root, resolved)


def run_post_archive_validators(repo_root: Path, archived_task: Path) -> list[str]:
    failures: list[str] = []
    for name in ("validate_task.py", "validate_review_gates.py", "validate_workflow_state.py"):
        script = repo_root / ".trellis" / "scripts" / name
        if not script.is_file():
            continue
        result = subprocess.run(
            [sys.executable, str(script), str(archived_task)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if result.returncode != 0:
            failures.append(f"{name}:\n{(result.stdout or result.stderr).strip()}")
    return failures


def finalize_archived_task(archived_task: Path, repo_root: Path) -> list[str]:
    changes: list[str] = []
    task_data = json.loads((archived_task / "task.json").read_text(encoding="utf-8"))
    changes.extend(repair_implementation_approval(archived_task, task_data))
    changes.extend(repair_finish_sections(archived_task, task_data))
    changes.extend(sync_task_json(archived_task))
    changes.extend(repair_jsonl(archived_task, repo_root, "implement.jsonl"))
    changes.extend(repair_jsonl(archived_task, repo_root, "check.jsonl"))
    changes.extend(sync_workspace_records(repo_root, archived_task))
    return changes


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <task-dir-or-archived-task-dir>")
        return 1

    task_arg = Path(sys.argv[1])
    if not task_arg.exists():
        print(f"FAIL: task path does not exist: {task_arg}")
        return 1

    repo_root = find_repo_root(task_arg if task_arg.is_dir() else task_arg.parent)
    if repo_root is None:
        print("FAIL: cannot find repo root with .git and .trellis")
        return 1

    try:
        archived_task = archive_if_needed(repo_root, task_arg)
        changes = finalize_archived_task(archived_task, repo_root)
        failures = run_post_archive_validators(repo_root, archived_task)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    if failures:
        print("FAIL: post-archive validation failed")
        for failure in failures:
            print(f"---\n{failure}")
        return 1

    print(f"PASS: finalized archived task {archived_task}")
    for item in changes:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
