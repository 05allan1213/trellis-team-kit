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

import warnings
warnings.filterwarnings("ignore")

if sys.platform.startswith("win"):
    import io as _io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    elif hasattr(sys.stdout, "detach"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")

TRELLIS_DIR = ".trellis"

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
    AGENT_ARCHITECTURE_DEEP_REVIEWER, AGENT_MERGE_REVIEWER,
)
AGENTS_ALL = (
    AGENT_RESEARCH, AGENT_IMPLEMENT, AGENT_CHECK,
) + AGENTS_REVIEW + (AGENT_SPEC_UPDATER,)

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
                    content = _read_file(base_path, file_path)
                    if content:
                        results.append((file_path, content))
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
    val = _read_file(repo_root, f"{task_dir}/validation/results.md")
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
    val = _read_file(repo_root, f"{task_dir}/validation/results.md")
    if val:
        parts.append(f"## Validation\n```\n{val[:1500]}\n```")

    return "\n\n".join(parts)


def _build_research_prompt(original_prompt: str, context: str) -> str:
    return (
        f"<!-- team-kit-hook-injected -->\n"
        f"# Research Agent Task\n\n"
        f"You are the Research Agent in the Team-kit pipeline.\n\n"
        f"## Core Principle\n\n"
        f"**You do one thing: find and explain information.** "
        f"You are a documenter, not a reviewer.\n\n"
        f"## Project Context\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Output Format\n\n"
        f"- Research Question\n"
        f"- Files / Sources inspected\n"
        f"- Findings\n"
        f"- Decision impact\n"
        f"- Output file updated\n\n"
        f"## Strict Boundaries\n\n"
        f"**Only allowed**: Describe what exists, where it is, how it works.\n"
        f"**Forbidden**: Suggest improvements, criticize, recommend refactoring, modify files."
    )


def _build_implement_prompt(original_prompt: str, context: str) -> str:
    return (
        f"<!-- team-kit-hook-injected -->\n"
        f"# Implement Agent Task\n\n"
        f"You are the Implement Agent in the Team-kit pipeline.\n\n"
        f"## Your Context\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Output Format (REQUIRED)\n\n"
        f"- **Implementation Summary**: what was implemented\n"
        f"- **Changed Files**: list all modified/created files\n"
        f"- **Validation Attempted**: what checks were run\n"
        f"- **Risks / Follow-ups**: any remaining concerns\n"
        f"- **Did not commit**: confirm no git commit was executed\n\n"
        f"## Important Constraints\n\n"
        f"- Do NOT execute git commit, only code modifications\n"
        f"- Follow all dev specs injected above\n"
        f"- Follow implement.md ordered steps\n"
        f"- Do not expand scope beyond the task"
    )


def _build_check_prompt(original_prompt: str, context: str) -> str:
    return (
        f"<!-- team-kit-hook-injected -->\n"
        f"# Check Agent Task\n\n"
        f"You are the Check Agent in the Team-kit pipeline.\n\n"
        f"## Your Context\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Output Format (REQUIRED)\n\n"
        f"```\n"
        f"Status:\n"
        f"- [ ] PASS\n"
        f"- [ ] FAIL\n\n"
        f"Commands run:\n\n"
        f"Failures:\n\n"
        f"Files inspected:\n\n"
        f"Required fixes (if FAIL):\n"
        f"```\n\n"
        f"## Important Constraints\n\n"
        f"- Fix issues yourself, do not just report\n"
        f"- MUST output PASS or FAIL verdict\n"
        f"- Run lint/typecheck if available"
    )


def _build_review_prompt(original_prompt: str, context: str, agent_type: str) -> str:
    review_type_map = {
        "trellis-spec-reviewer": "Spec Review",
        "trellis-code-reviewer": "Code Review",
        "trellis-architecture-reviewer": "Architecture Review",
        "trellis-architecture-deep-reviewer": "Deep Architecture Review",
        "trellis-merge-reviewer": "Merge Review",
    }
    review_type = review_type_map.get(agent_type, "Review")
    return (
        f"<!-- team-kit-hook-injected -->\n"
        f"# {review_type} Agent Task\n\n"
        f"You are the {review_type} Agent in the Team-kit pipeline.\n\n"
        f"## Your Context\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Output Format (REQUIRED)\n\n"
        f"```\n"
        f"Status:\n"
        f"- [ ] PASS\n"
        f"- [ ] FAIL\n\n"
        f"Scope reviewed:\n\n"
        f"Blocking issues:\n\n"
        f"Non-blocking issues:\n\n"
        f"Required fixes:\n"
        f"```\n\n"
        f"## Important Constraints\n\n"
        f"- MUST output PASS or FAIL verdict\n"
        f"- MUST list blocking issues with file citations\n"
        f"- MUST list non-blocking issues separately\n"
        f"- FAIL must include specific required fixes"
    )


def _build_spec_updater_prompt(original_prompt: str, context: str) -> str:
    return (
        f"<!-- team-kit-hook-injected -->\n"
        f"# Spec Update Agent Task\n\n"
        f"You are the Spec Update Agent in the Team-kit pipeline.\n\n"
        f"## Your Context\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Output Format (REQUIRED)\n\n"
        f"```\n"
        f"Spec Update Decision:\n\n"
        f"Need spec update:\n"
        f"- [ ] yes\n"
        f"- [ ] no\n\n"
        f"Reason:\n\n"
        f"Updated files (if yes):\n"
        f"```\n\n"
        f"## Important Constraints\n\n"
        f"- MUST output Spec Update Decision\n"
        f"- MUST state yes/no explicitly\n"
        f"- MUST provide reason for decision"
    )


def _build_merge_reviewer_prompt(original_prompt: str, context: str) -> str:
    return (
        f"<!-- team-kit-hook-injected -->\n"
        f"# Merge Review Agent Task\n\n"
        f"You are the Merge Review Agent in the Team-kit pipeline.\n\n"
        f"## Your Context\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Output Format (REQUIRED)\n\n"
        f"```\n"
        f"Status:\n"
        f"- [ ] PASS\n"
        f"- [ ] FAIL\n\n"
        f"Scope reviewed:\n\n"
        f"Blocking issues:\n\n"
        f"Non-blocking issues:\n\n"
        f"Required fixes:\n"
        f"```\n\n"
        f"## Important Constraints\n\n"
        f"- MUST output PASS or FAIL verdict\n"
        f"- Check merge conflicts, commit coherence, cross-branch consistency"
    )


def _extract_subagent_name(tool_input: dict) -> str:
    """Extract subagent name from various platform encodings."""
    for key in ("subagent_type", "subagentType", "subagent_type_name",
                "subagentTypeName", "agent_type", "agentType", "name"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, dict):
            for k in ("name", "subagent_type_name", "subagentTypeName"):
                v = val.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    return ""


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    # Parse subagent info
    tool_input = input_data.get("tool_input", {})
    tool_name = input_data.get("tool_name", "") or input_data.get("toolName", "")
    subagent_type = ""

    # SubagentStart event: check agent_name
    agent_name = input_data.get("agent_name", "")
    if isinstance(agent_name, str) and agent_name in AGENTS_ALL:
        subagent_type = agent_name

    # Fallback: PreToolUse event for Task/Agent
    if not subagent_type and tool_name.lower() in ("task", "agent", "subagent"):
        subagent_type = _extract_subagent_name(tool_input)

    # Gemini: tool_name IS the agent name
    if not subagent_type and tool_name in AGENTS_ALL:
        subagent_type = tool_name

    if subagent_type not in AGENTS_ALL:
        return 0

    original_prompt = tool_input.get("prompt", "") or input_data.get("prompt", "")
    cwd = input_data.get("cwd", os.getcwd())

    repo_root = _find_repo_root(cwd)
    if not repo_root:
        return 0

    task_dir = _get_current_task(repo_root)

    # For agents that require a task
    if subagent_type in AGENTS_REQUIRE_TASK or subagent_type in AGENTS_REVIEW or subagent_type == AGENT_SPEC_UPDATER or subagent_type == AGENT_MERGE_REVIEWER:
        if not task_dir:
            return 0
        task_dir_full = os.path.join(repo_root, task_dir) if not os.path.isabs(task_dir) else task_dir
        if not os.path.exists(task_dir_full):
            return 0

    # Build context by agent type
    context = ""
    new_prompt = ""

    if subagent_type == AGENT_RESEARCH:
        context = _get_research_context(repo_root, task_dir or "")
        new_prompt = _build_research_prompt(original_prompt, context)
    elif subagent_type == AGENT_IMPLEMENT:
        assert task_dir is not None
        context = _get_implement_context(repo_root, task_dir)
        new_prompt = _build_implement_prompt(original_prompt, context)
    elif subagent_type == AGENT_CHECK:
        assert task_dir is not None
        context = _get_check_context(repo_root, task_dir)
        new_prompt = _build_check_prompt(original_prompt, context)
    elif subagent_type in AGENTS_REVIEW:
        assert task_dir is not None
        context = _get_review_context(repo_root, task_dir)
        if subagent_type == AGENT_MERGE_REVIEWER:
            new_prompt = _build_merge_reviewer_prompt(original_prompt, context)
        else:
            new_prompt = _build_review_prompt(original_prompt, context, subagent_type)
    elif subagent_type == AGENT_SPEC_UPDATER:
        assert task_dir is not None
        context = _get_spec_updater_context(repo_root, task_dir)
        new_prompt = _build_spec_updater_prompt(original_prompt, context)
    else:
        return 0

    if not context and subagent_type in AGENTS_REQUIRE_TASK:
        # Missing context for task-requiring agent — warn but proceed
        pass

    # Truncate if too large
    if len(new_prompt) > MAX_CONTEXT_CHARS + len(original_prompt):
        new_prompt = new_prompt[:MAX_CONTEXT_CHARS] + "\n\n[... context truncated ...]"

    updated = {**tool_input, "prompt": new_prompt}

    # SubagentStart event format
    event_name = input_data.get("hook_event_name", "") or input_data.get("hookEventName", "")
    if not event_name:
        event_name = "SubagentStart" if "agent_name" in input_data else "PreToolUse"

    output = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "allow",
            "updatedInput": updated,
        },
        "permission": "allow",
        "updated_input": updated,
        "updatedInput": updated,
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
