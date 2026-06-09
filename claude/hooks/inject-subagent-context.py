#!/usr/bin/env python3
"""
Team-kit Inject Subagent Context Hook — v0.3 Hardened

When a trellis subagent is spawned, injects task-specific context based on
agent type. Covers all 9 canonical agents.

Injection strategies:
- researcher: task.json, prd.md, workflow state, spec index, research dir
- implementer: task.json, prd.md, design.md, implement.md, implement.jsonl, approval
- checker: task.json, prd.md, design.md, implement.md, check.jsonl, git diff, contract
- reviewers: task.json, prd.md, design.md, implement.md, git diff, contract, specs
- spec-updater: task.json, prd.md, design.md, implement.md, review results, validation, spec index
- merge-reviewer: task.json, prd.md, design.md, implement.md, commits, validation, gate results

Trigger: SubagentStart
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
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

from task_artifacts import (  # type: ignore[import-not-found]
    implementation_approval_complete,
    parse_implementation_approval,
)

# Canonical agent names
AGENT_RESEARCH = "trellis-researcher"
AGENT_IMPLEMENT = "trellis-implementer"
AGENT_CHECK = "trellis-checker"
AGENT_SPEC_REVIEWER = "trellis-spec-reviewer"
AGENT_CODE_REVIEWER = "trellis-code-reviewer"
AGENT_ARCHITECTURE_REVIEWER = "trellis-architecture-reviewer"
AGENT_ARCHITECTURE_DEEP_REVIEWER = "trellis-architecture-deep-reviewer"
AGENT_MERGE_REVIEWER = "trellis-merge-reviewer"
AGENT_SPEC_UPDATER = "trellis-spec-updater"

AGENTS_REQUIRE_TASK = (AGENT_IMPLEMENT, AGENT_CHECK)
AGENTS_REVIEW = (
    AGENT_SPEC_REVIEWER, AGENT_CODE_REVIEWER, AGENT_ARCHITECTURE_REVIEWER,
    AGENT_ARCHITECTURE_DEEP_REVIEWER,
)
AGENTS_ALL = (
    AGENT_RESEARCH, AGENT_IMPLEMENT, AGENT_CHECK,
) + AGENTS_REVIEW + (AGENT_SPEC_UPDATER, AGENT_MERGE_REVIEWER)
AGENTS_REQUIRE_AGENT_RESULT = AGENTS_ALL

MAX_CONTEXT_CHARS = 32000  # Limit total injected context


def _find_repo_root(start_path: str) -> Optional[str]:
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def _get_current_task(repo_root: str) -> Optional[str]:
    active_file = Path(repo_root) / TRELLIS_DIR / "active-task"
    if active_file.is_file():
        try:
            return active_file.read_text(encoding="utf-8").strip() or None
        except OSError:
            pass
    return None


def _read_file(base_path: str, file_path: str, max_chars: int = 8000) -> Optional[str]:
    full_path = os.path.join(base_path, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read(max_chars)
                return content
        except Exception:
            return None
    return None


def _resolve_context_path(task_dir: str, file_path: str) -> str:
    normalized = file_path.replace("\\", "/").strip()
    if normalized.startswith("<task-dir>/"):
        return f"{task_dir}/{normalized[len('<task-dir>/'):]}"
    if normalized.startswith("$TASK_DIR/"):
        return f"{task_dir}/{normalized[len('$TASK_DIR/'):]}"
    return normalized


def _read_jsonl_entries(base_path: str, jsonl_path: str, max_files: int = 20) -> list[tuple[str, str]]:
    full_path = os.path.join(base_path, jsonl_path)
    if not os.path.exists(full_path):
        return []

    results: list[tuple[str, str]] = []
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                if len(results) >= max_files:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    file_path = item.get("file") or item.get("path")
                    if not file_path:
                        continue
                    resolved_path = _resolve_context_path(os.path.dirname(jsonl_path), str(file_path))
                    content = _read_file(base_path, resolved_path)
                    if content:
                        results.append((str(file_path), content))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return results


def _get_spec_tree(repo_root: str) -> str:
    spec_root = Path(repo_root) / TRELLIS_DIR / "spec"
    if not spec_root.is_dir():
        return "(no spec directory)"

    lines = [".trellis/spec/"]
    if not (spec_root / "index.md").is_file():
        lines.append("  (missing index.md)")
    for pkg in sorted(spec_root.iterdir()):
        if not pkg.is_dir() or pkg.name.startswith("."):
            continue
        layers = sorted(d.name for d in pkg.iterdir() if d.is_dir())
        layer_info = f" ({', '.join(layers)})" if layers else ""
        lines.append(f"  {pkg.name}/{layer_info}")
    return "\n".join(lines)


def _get_research_context(repo_root: str, task_dir: str) -> str:
    """Researcher: task.json, prd.md, workflow state, spec index, research dir."""
    parts: list[str] = []
    parts.append(f"## Project Spec Structure\n```\n{_get_spec_tree(repo_root)}\n```")

    prd = _read_file(repo_root, f"{task_dir}/prd.md")
    if prd:
        parts.append(f"## PRD\n```\n{prd[:4000]}\n```")

    # List existing research files
    research_dir = Path(repo_root) / task_dir / "research"
    if research_dir.is_dir():
        existing = sorted(f.name for f in research_dir.iterdir() if f.is_file())
        if existing:
            parts.append(f"## Existing Research Files\n{', '.join(existing)}")

    return "\n\n".join(parts)


def _get_implement_context(repo_root: str, task_dir: str) -> str:
    """Implementer: implement.jsonl, prd.md, design.md, implement.md, approval."""
    parts: list[str] = []

    # Check approval status
    task_json = _read_file(repo_root, f"{task_dir}/task.json")
    if task_json:
        try:
            tj = json.loads(task_json)
            status = tj.get("status", "")
            if status.upper() in ("WAITING_IMPLEMENTATION_APPROVAL", "PLANNING_IMPLEMENT",
                                   "PLANNING_PRD", "PLANNING_GRILL", "PLANNING_DESIGN"):
                parts.append("**WARNING: Implementation not yet approved.** Check consent before editing source.")
        except Exception:
            pass

    approval = parse_implementation_approval(Path(repo_root) / task_dir / "implement.md")
    if not implementation_approval_complete(approval):
        parts.append(
            "**WARNING: Implementation Approval is not fully recorded in implement.md.** "
            "Update the approval section from the user's consent before starting or continuing execution."
        )

    for file_path, content in _read_jsonl_entries(repo_root, f"{task_dir}/implement.jsonl"):
        parts.append(f"### {file_path}\n```\n{content[:3000]}\n```")

    prd = _read_file(repo_root, f"{task_dir}/prd.md")
    if prd:
        parts.append(f"## PRD (Requirements)\n```\n{prd[:4000]}\n```")

    design = _read_file(repo_root, f"{task_dir}/design.md")
    if design:
        parts.append(f"## Design\n```\n{design[:4000]}\n```")

    impl_plan = _read_file(repo_root, f"{task_dir}/implement.md")
    if impl_plan:
        parts.append(f"## Implement Plan\n```\n{impl_plan[:4000]}\n```")

    return "\n\n".join(parts)


def _get_check_context(repo_root: str, task_dir: str) -> str:
    """Checker: check.jsonl, prd.md, design.md, implement.md, git diff, contract, validation hints."""
    parts: list[str] = []

    for file_path, content in _read_jsonl_entries(repo_root, f"{task_dir}/check.jsonl"):
        parts.append(f"### {file_path}\n```\n{content[:3000]}\n```")

    prd = _read_file(repo_root, f"{task_dir}/prd.md")
    if prd:
        parts.append(f"## PRD\n```\n{prd[:3000]}\n```")

    impl_plan = _read_file(repo_root, f"{task_dir}/implement.md")
    if impl_plan:
        parts.append(f"## Implement Plan (includes Review Gate Contract)\n```\n{impl_plan[:4000]}\n```")

    # Git diff summary
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=5, cwd=repo_root,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts.append(f"## Current Git Diff (stat)\n```\n{result.stdout.strip()[:2000]}\n```")
    except Exception:
        pass

    return "\n\n".join(parts)


def _get_review_context(repo_root: str, task_dir: str) -> str:
    """Reviewers: prd.md, design.md, implement.md, git diff, contract, specs, prev check."""
    parts: list[str] = []

    prd = _read_file(repo_root, f"{task_dir}/prd.md")
    if prd:
        parts.append(f"## PRD\n```\n{prd[:4000]}\n```")

    design = _read_file(repo_root, f"{task_dir}/design.md")
    if design:
        parts.append(f"## Design\n```\n{design[:4000]}\n```")

    impl_plan = _read_file(repo_root, f"{task_dir}/implement.md")
    if impl_plan:
        parts.append(f"## Implement Plan (includes Review Gate Contract)\n```\n{impl_plan[:4000]}\n```")

    # Previous check result
    check_result = _read_file(repo_root, f"{task_dir}/validation/check-results.md")
    if check_result:
        parts.append(f"## Previous Check Result\n```\n{check_result[:3000]}\n```")

    # Git diff summary
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=5, cwd=repo_root,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts.append(f"## Git Diff (stat)\n```\n{result.stdout.strip()[:2000]}\n```")
    except Exception:
        pass

    return "\n\n".join(parts)


def _get_spec_updater_context(repo_root: str, task_dir: str) -> str:
    """Spec-updater: task.json, prd, design, implement, review results, validation, spec index."""
    parts: list[str] = []

    prd = _read_file(repo_root, f"{task_dir}/prd.md")
    if prd:
        parts.append(f"## PRD\n```\n{prd[:3000]}\n```")

    impl_plan = _read_file(repo_root, f"{task_dir}/implement.md")
    if impl_plan:
        parts.append(f"## Implement Plan\n```\n{impl_plan[:3000]}\n```")

    # Review results
    review_dir = Path(repo_root) / task_dir / "review"
    if review_dir.is_dir():
        for rf in sorted(review_dir.iterdir()):
            if rf.is_file() and rf.suffix == ".md":
                content = _read_file(repo_root, f"{task_dir}/review/{rf.name}", max_chars=2000)
                if content:
                    parts.append(f"## Review: {rf.name}\n```\n{content}\n```")

    # Validation results
    val = _read_file(repo_root, f"{task_dir}/validation/test-results.md")
    if val:
        parts.append(f"## Validation Results\n```\n{val[:2000]}\n```")

    # Spec index
    parts.append(f"## Spec Index\n```\n{_get_spec_tree(repo_root)}\n```")

    return "\n\n".join(parts)


def _get_merge_reviewer_context(repo_root: str, task_dir: str) -> str:
    """Merge-reviewer: task.json, prd, design, implement, commits, validation, gate results."""
    parts: list[str] = []

    prd = _read_file(repo_root, f"{task_dir}/prd.md")
    if prd:
        parts.append(f"## PRD\n```\n{prd[:3000]}\n```")

    impl_plan = _read_file(repo_root, f"{task_dir}/implement.md")
    if impl_plan:
        parts.append(f"## Implement Plan\n```\n{impl_plan[:3000]}\n```")

    # Git log
    import subprocess
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=5, cwd=repo_root,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts.append(f"## Recent Commits\n```\n{result.stdout.strip()[:2000]}\n```")
    except Exception:
        pass

    # Gate results
    review_dir = Path(repo_root) / task_dir / "review"
    if review_dir.is_dir():
        for rf in sorted(review_dir.iterdir()):
            if rf.is_file() and rf.suffix == ".md":
                content = _read_file(repo_root, f"{task_dir}/review/{rf.name}", max_chars=1500)
                if content:
                    parts.append(f"## Gate: {rf.name}\n```\n{content}\n```")

    # Validation
    val = _read_file(repo_root, f"{task_dir}/validation/test-results.md")
    if val:
        parts.append(f"## Validation\n```\n{val[:1500]}\n```")

    return "\n\n".join(parts)


def _get_agent_result_instruction(subagent_type: str, task_dir: str | None) -> str:
    if subagent_type not in AGENTS_REQUIRE_AGENT_RESULT or not task_dir:
        return ""

    phase_by_agent = {
        AGENT_RESEARCH: "RESEARCH",
        AGENT_IMPLEMENT: "IMPLEMENTING",
        AGENT_CHECK: "CHECKING",
        AGENT_SPEC_UPDATER: "UPDATING_SPEC",
        AGENT_MERGE_REVIEWER: "MERGE_REVIEW",
    }
    phase = phase_by_agent.get(subagent_type, "REVIEWING")

    return (
        "## Required Agent Result JSON\n"
        f"Before your final response, write `{task_dir}/agent-results/"
        f"{subagent_type}-<timestamp>.json` with this schema:\n"
        "```json\n"
        "{\n"
        '  "version": 1,\n'
        f'  "agent": "{subagent_type}",\n'
        '  "status": "PASS",\n'
        f'  "phase": "{phase}",\n'
        '  "workstream": "<declared workstream name; required for implementer/checker when scope-manifest declares workstreams>",\n'
        '  "changed_files": [{"path": "<repo-relative path>", "summary": "<what changed>"}],\n'
        '  "validation": [{"command": "<command or review performed>", "status": "PASS"}],\n'
        '  "blocking_issues": [],\n'
        '  "non_blocking_issues": [],\n'
        '  "risks": [],\n'
        '  "scope": {"expanded": false, "undeclared_paths": []},\n'
        '  "scope_expansion": [],\n'
        '  "git": {"committed": false},\n'
        '  "execution_mode": "single-agent"\n'
        "}\n"
        "```\n"
        "Set status to FAIL, REDESIGN-REQUIRED, or BLOCKED when appropriate. "
        "Mention the JSON path in your final response."
    )


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    # SubagentStart event: extract agent_type first (official field), backward compatible
    agent_name = (
        input_data.get("agent_type")
        or input_data.get("agent_name")
        or input_data.get("subagent_type")
        or ""
    )
    if not isinstance(agent_name, str) or agent_name not in AGENTS_ALL:
        return 0

    subagent_type = agent_name
    cwd = input_data.get("cwd", os.getcwd())

    repo_root = _find_repo_root(cwd)
    if not repo_root:
        return 0

    task_dir = _get_current_task(repo_root)

    if subagent_type in AGENTS_REQUIRE_TASK or subagent_type in AGENTS_REVIEW or subagent_type in (AGENT_SPEC_UPDATER, AGENT_MERGE_REVIEWER):
        if not task_dir:
            return 0
        task_dir_full = os.path.join(repo_root, task_dir) if not os.path.isabs(task_dir) else task_dir
        if not os.path.exists(task_dir_full):
            return 0

    additional_context = ""

    if subagent_type == AGENT_RESEARCH:
        additional_context = _get_research_context(repo_root, task_dir or "")
    elif subagent_type == AGENT_IMPLEMENT:
        additional_context = _get_implement_context(repo_root, task_dir)
    elif subagent_type == AGENT_CHECK:
        additional_context = _get_check_context(repo_root, task_dir)
    elif subagent_type == AGENT_MERGE_REVIEWER:
        additional_context = _get_merge_reviewer_context(repo_root, task_dir)
    elif subagent_type in AGENTS_REVIEW:
        additional_context = _get_review_context(repo_root, task_dir)
    elif subagent_type == AGENT_SPEC_UPDATER:
        additional_context = _get_spec_updater_context(repo_root, task_dir)
    else:
        return 0

    if not additional_context:
        return 0

    result_instruction = _get_agent_result_instruction(subagent_type, task_dir)
    suffix = f"\n\n{result_instruction}" if result_instruction else ""

    if len(additional_context) + len(suffix) > MAX_CONTEXT_CHARS:
        available = max(0, MAX_CONTEXT_CHARS - len(suffix) - len("\n\n[... context truncated ...]"))
        additional_context = (
            additional_context[:available]
            + "\n\n[... context truncated ...]"
        )

    additional_context = f"{additional_context}{suffix}"

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": additional_context,
        }
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
