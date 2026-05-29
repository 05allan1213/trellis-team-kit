#!/usr/bin/env python3
"""
Team-kit Inject Sub-agent Context Hook

When a trellis-implement/trellis-check/trellis-research subagent is spawned,
injects task context: implement.jsonl or check.jsonl entries + prd.md +
design.md + implement.md.

Must handle the case where hook didn't fire (Windows/--continue) -- the
subagent's own context loading protocol is the fallback.

Trigger: PreToolUse (before Task/Agent tool)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Suppress warnings early
import warnings
warnings.filterwarnings("ignore")

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    import io as _io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    elif hasattr(sys.stdout, "detach"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")

TRELLIS_DIR = ".trellis"

AGENT_IMPLEMENT = "trellis-implement"
AGENT_CHECK = "trellis-check"
AGENT_RESEARCH = "trellis-research"
AGENTS_REQUIRE_TASK = (AGENT_IMPLEMENT, AGENT_CHECK)
AGENTS_ALL = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_RESEARCH)


def _find_repo_root(start_path: str) -> Optional[str]:
    """Find git repo root from start_path upwards."""
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def _detect_platform(input_data: dict) -> Optional[str]:
    if isinstance(input_data.get("cursor_version"), str):
        return "cursor"
    env_map = {
        "CLAUDE_PROJECT_DIR": "claude",
        "CURSOR_PROJECT_DIR": "cursor",
        "CODEBUDDY_PROJECT_DIR": "codebuddy",
        "FACTORY_PROJECT_DIR": "droid",
        "GEMINI_PROJECT_DIR": "gemini",
        "QODER_PROJECT_DIR": "qoder",
        "KIRO_PROJECT_DIR": "kiro",
        "COPILOT_PROJECT_DIR": "copilot",
    }
    for env_name, platform in env_map.items():
        if os.environ.get(env_name):
            return platform
    return None


def _get_current_task(repo_root: str, input_data: dict) -> Optional[str]:
    """Resolve current task directory through the active task resolver."""
    scripts_dir = Path(repo_root) / TRELLIS_DIR / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]
        active = resolve_active_task(
            Path(repo_root), input_data,
            platform=_detect_platform(input_data),
        )
        return active.task_path
    except Exception:
        pass

    # Fallback: read .trellis/active-task
    active_file = Path(repo_root) / TRELLIS_DIR / "active-task"
    if active_file.is_file():
        try:
            return active_file.read_text(encoding="utf-8").strip() or None
        except OSError:
            pass
    return None


def _read_file_content(base_path: str, file_path: str) -> Optional[str]:
    """Read file content, return None if file doesn't exist."""
    full_path = os.path.join(base_path, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    return None


def _read_jsonl_entries(base_path: str, jsonl_path: str) -> list[tuple[str, str]]:
    """Read all file contents referenced in a jsonl file.

    Schema:
        {"file": "path/to/file.md", "reason": "..."}
        {"file": "path/to/dir/", "type": "directory", "reason": "..."}
        {"_example": "..."}  # seed row -- skipped (no `file` field)
    """
    full_path = os.path.join(base_path, jsonl_path)
    if not os.path.exists(full_path):
        return []

    results: list[tuple[str, str]] = []
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    file_path = item.get("file") or item.get("path")
                    if not file_path:
                        continue  # Seed/comment row
                    content = _read_file_content(base_path, file_path)
                    if content:
                        results.append((file_path, content))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return results


def _get_implement_context(repo_root: str, task_dir: str) -> str:
    """Context for Implement Agent: implement.jsonl + prd.md + design.md + implement.md."""
    parts: list[str] = []

    # 1. implement.jsonl entries
    for file_path, content in _read_jsonl_entries(repo_root, f"{task_dir}/implement.jsonl"):
        parts.append(f"=== {file_path} ===\n{content}")

    # 2. prd.md
    prd = _read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd:
        parts.append(f"=== {task_dir}/prd.md (Requirements) ===\n{prd}")

    # 3. design.md
    design = _read_file_content(repo_root, f"{task_dir}/design.md")
    if design:
        parts.append(f"=== {task_dir}/design.md (Technical Design) ===\n{design}")

    # 4. implement.md
    impl_plan = _read_file_content(repo_root, f"{task_dir}/implement.md")
    if impl_plan:
        parts.append(f"=== {task_dir}/implement.md (Execution Plan) ===\n{impl_plan}")

    return "\n\n".join(parts)


def _get_check_context(repo_root: str, task_dir: str) -> str:
    """Context for Check Agent: check.jsonl + prd.md + design.md + implement.md."""
    parts: list[str] = []

    for file_path, content in _read_jsonl_entries(repo_root, f"{task_dir}/check.jsonl"):
        parts.append(f"=== {file_path} ===\n{content}")

    prd = _read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd:
        parts.append(f"=== {task_dir}/prd.md (Requirements) ===\n{prd}")

    design = _read_file_content(repo_root, f"{task_dir}/design.md")
    if design:
        parts.append(f"=== {task_dir}/design.md (Technical Design) ===\n{design}")

    impl_plan = _read_file_content(repo_root, f"{task_dir}/implement.md")
    if impl_plan:
        parts.append(f"=== {task_dir}/implement.md (Execution Plan) ===\n{impl_plan}")

    return "\n\n".join(parts)


def _get_research_context(repo_root: str, task_dir: Optional[str]) -> str:
    """Context for Research Agent: project spec structure overview."""
    _ = task_dir
    parts: list[str] = []

    spec_path = f"{TRELLIS_DIR}/spec"
    spec_root = Path(repo_root) / TRELLIS_DIR / "spec"

    tree_lines = [f"{spec_path}/"]
    if spec_root.is_dir():
        pkg_dirs = sorted(d for d in spec_root.iterdir() if d.is_dir())
        for i, pkg_dir in enumerate(pkg_dirs):
            is_last = i == len(pkg_dirs) - 1
            prefix = "+-- " if is_last else "|-- "
            layers = sorted(d.name for d in pkg_dir.iterdir() if d.is_dir())
            layer_info = f" ({', '.join(layers)})" if layers else ""
            tree_lines.append(f"{prefix}{pkg_dir.name}/{layer_info}")

    spec_tree = "\n".join(tree_lines)
    parts.append(
        f"## Project Spec Directory Structure\n\n```\n{spec_tree}\n```\n\n"
        f"Spec files: `{spec_path}/**/*.md`\n"
        f"Code search: Use Glob and Grep tools."
    )
    return "\n\n".join(parts)


def _build_implement_prompt(original_prompt: str, context: str) -> str:
    return (
        f"<!-- team-kit-hook-injected -->\n"
        f"# Implement Agent Task\n\n"
        f"You are the Implement Agent in the Team-kit pipeline.\n\n"
        f"## Your Context\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Workflow\n\n"
        f"1. **Understand specs** - All dev specs injected above, understand them\n"
        f"2. **Understand task artifacts** - Read prd.md, design.md, implement.md\n"
        f"3. **Implement feature** - Implement following specs and task artifacts\n"
        f"4. **Self-check** - Ensure code quality against check specs\n\n"
        f"## Output Format\n\n"
        f"- Changed files: list all modified/created files\n"
        f"- Summary: what was implemented\n"
        f"- Validation attempted: what checks were run\n"
        f"- Unresolved risks: any remaining concerns\n\n"
        f"## Important Constraints\n\n"
        f"- Do NOT execute git commit, only code modifications\n"
        f"- Follow all dev specs injected above\n"
        f"- Report list of modified/created files when done"
    )


def _build_check_prompt(original_prompt: str, context: str) -> str:
    return (
        f"<!-- team-kit-hook-injected -->\n"
        f"# Check Agent Task\n\n"
        f"You are the Check Agent in the Team-kit pipeline.\n\n"
        f"## Your Context\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Workflow\n\n"
        f"1. **Get changes** - Run `git diff --name-only` and `git diff`\n"
        f"2. **Check against specs** - Check item by item against specs above\n"
        f"3. **Self-fix** - Fix issues directly, do not just report\n"
        f"4. **Run verification** - Run project lint and typecheck commands\n\n"
        f"## Output Format\n\n"
        f"- PASS or FAIL\n"
        f"- Commands run\n"
        f"- Failures found\n"
        f"- Fixes applied\n\n"
        f"## Important Constraints\n\n"
        f"- Fix issues yourself, do not just report\n"
        f"- Must execute complete checklist in check specs\n"
        f"- Pay special attention to impact radius analysis (L1-L5)"
    )


def _build_research_prompt(original_prompt: str, context: str) -> str:
    return (
        f"# Research Agent Task\n\n"
        f"You are the Research Agent in the Team-kit pipeline.\n\n"
        f"## Core Principle\n\n"
        f"**You do one thing: find and explain information.**\n"
        f"You are a documenter, not a reviewer.\n\n"
        f"## Project Info\n\n{context}\n\n---\n\n"
        f"## Your Task\n\n{original_prompt}\n\n---\n\n"
        f"## Workflow\n\n"
        f"1. **Understand query** - Determine search type and scope\n"
        f"2. **Plan search** - List search steps\n"
        f"3. **Execute search** - Execute searches\n"
        f"4. **Organize results** - Output structured report\n\n"
        f"## Strict Boundaries\n\n"
        f"**Only allowed**: Describe what exists, where it is, how it works\n"
        f"**Forbidden** (unless explicitly asked): Suggest improvements, "
        f"criticize implementation, recommend refactoring, modify any files"
    )


def _string_value(value) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _extract_subagent_name(value) -> str:
    """Extract sub-agent name from various platform encodings."""
    direct = _string_value(value)
    if direct:
        return direct
    if not isinstance(value, dict):
        return ""
    for key in ("name", "subagent_type_name", "subagentTypeName"):
        v = _string_value(value.get(key))
        if v:
            return v
    custom = value.get("custom")
    if isinstance(custom, dict):
        v = _string_value(custom.get("name"))
        if v:
            return v
    oneof = value.get("type")
    if isinstance(oneof, dict):
        case_name = _string_value(oneof.get("case"))
        if case_name == "custom":
            nested = oneof.get("value")
            if isinstance(nested, dict):
                v = _string_value(nested.get("name"))
                if v:
                    return v
        if case_name:
            return case_name
    return ""


def _extract_subagent_type(tool_input: dict) -> str:
    for key in ("subagent_type", "subagentType", "subagent_type_name",
                "subagentTypeName", "agent_type", "agentType", "name"):
        name = _extract_subagent_name(tool_input.get(key))
        if name:
            return name
    return ""


def _parse_hook_input(input_data: dict) -> tuple[str, str, dict]:
    """Parse hook input across platform formats.

    Returns (subagent_type, original_prompt, tool_input).
    """
    tool_input = input_data.get("tool_input", {})
    tool_name = input_data.get("tool_name", "") or input_data.get("toolName", "")

    if tool_name.lower() in ("task", "agent", "subagent"):
        return (
            _extract_subagent_type(tool_input),
            tool_input.get("prompt", ""),
            tool_input,
        )

    # Kiro: agentSpawn hook
    agent_name = input_data.get("agent_name", "")
    if agent_name:
        return agent_name, tool_input.get("prompt", input_data.get("prompt", "")), tool_input

    # Gemini: tool_name IS the agent name
    if tool_name in AGENTS_ALL:
        return tool_name, tool_input.get("prompt", ""), tool_input

    return "", "", tool_input


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    subagent_type, original_prompt, tool_input = _parse_hook_input(input_data)
    cwd = input_data.get("cwd", os.getcwd())

    if subagent_type not in AGENTS_ALL:
        return 0

    repo_root = _find_repo_root(cwd)
    if not repo_root:
        return 0

    task_dir = _get_current_task(repo_root, input_data)

    if subagent_type in AGENTS_REQUIRE_TASK:
        if not task_dir:
            return 0
        task_dir_full = os.path.join(repo_root, task_dir) if not os.path.isabs(task_dir) else task_dir
        if not os.path.exists(task_dir_full):
            return 0

    if subagent_type == AGENT_IMPLEMENT:
        assert task_dir is not None
        context = _get_implement_context(repo_root, task_dir)
        new_prompt = _build_implement_prompt(original_prompt, context)
    elif subagent_type == AGENT_CHECK:
        assert task_dir is not None
        context = _get_check_context(repo_root, task_dir)
        new_prompt = _build_check_prompt(original_prompt, context)
    elif subagent_type == AGENT_RESEARCH:
        context = _get_research_context(repo_root, task_dir)
        new_prompt = _build_research_prompt(original_prompt, context)
    else:
        return 0

    if not context:
        # Hook didn't fire properly; subagent's own context loading is fallback
        return 0

    updated = {**tool_input, "prompt": new_prompt}
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
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
