#!/usr/bin/env python3
"""
validate_hooks.py — Validate hook scripts existence and basic structure.

Checks:
- Hook files exist
- Python syntax is valid
- Hook output helpers are importable
- protect-dangerous-actions has deny path
- stop-guard has block path
- subagent-stop-guard has block path
- inject-subagent-context supports all canonical agents
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

REQUIRED_HOOKS = [
    "session-start.py",
    "inject-workflow-state.py",
    "inject-subagent-context.py",
    "protect-dangerous-actions.py",
    "post-edit-reminder.py",
    "subagent-stop-guard.py",
    "stop-guard.py",
    "pre-compact-save-state.py",
]

REQUIRED_SHELL_HOOKS = [
    "trellis-notify.sh",
]

CANONICAL_AGENTS = [
    "trellis-researcher", "trellis-implementer", "trellis-checker",
    "trellis-spec-reviewer", "trellis-code-reviewer",
    "trellis-architecture-reviewer", "trellis-architecture-deep-reviewer",
    "trellis-merge-reviewer", "trellis-spec-updater",
]

BLOCK_KEYWORDS = ["decision\": \"block\"", "decision': 'block'", 'decision": "block"']
DENY_KEYWORDS = ["permissionDecision\": \"deny\"", "permissionDecision': 'deny'"]


def eval_agent_expr(node: ast.AST, names: dict[str, tuple[str, ...]]) -> tuple[str, ...] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, (ast.Tuple, ast.List)):
        values: list[str] = []
        for item in node.elts:
            item_value = eval_agent_expr(item, names)
            if item_value is None:
                return None
            values.extend(item_value)
        return tuple(values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = eval_agent_expr(node.left, names)
        right = eval_agent_expr(node.right, names)
        if left is None or right is None:
            return None
        return left + right
    return None


def agent_result_required_agents(content: str) -> set[str] | None:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    names: dict[str, tuple[str, ...]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = eval_agent_expr(node.value, names)
        if value is not None:
            names[target.id] = value

    required = names.get("AGENTS_REQUIRE_AGENT_RESULT")
    if required is None:
        return None
    return set(required)


def find_project_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / "trellis").is_dir() and (cur / "claude" / "hooks").is_dir():
            return cur
        if (cur / ".trellis").is_dir() and (cur / ".claude" / "hooks").is_dir():
            return cur
        cur = cur.parent
    return None


def find_hooks_dir(root: Path) -> Path | None:
    installed = root / ".claude" / "hooks"
    if installed.is_dir():
        return installed
    kit = root / "claude" / "hooks"
    if kit.is_dir():
        return kit
    return None


def validate_hooks(hooks_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    # Check existence
    for hook_name in REQUIRED_HOOKS:
        hook_path = hooks_dir / hook_name
        if not hook_path.is_file():
            errors.append(f"Missing hook: {hook_name}")

    for hook_name in REQUIRED_SHELL_HOOKS:
        hook_path = hooks_dir / hook_name
        if not hook_path.is_file():
            errors.append(f"Missing hook: {hook_name}")

    # Check syntax
    for hook_file in sorted(hooks_dir.glob("*.py")):
        try:
            source = hook_file.read_text(encoding="utf-8")
            ast.parse(source)
        except SyntaxError as e:
            errors.append(f"{hook_file.name}: syntax error: {e}")
        except OSError:
            errors.append(f"{hook_file.name}: cannot read file")

    # Check protect-dangerous-actions has deny path
    protect = hooks_dir / "protect-dangerous-actions.py"
    if protect.is_file():
        try:
            content = protect.read_text(encoding="utf-8")
        except OSError:
            content = ""
        has_deny = any(kw in content for kw in DENY_KEYWORDS)
        if not has_deny:
            errors.append("protect-dangerous-actions.py: missing deny (hard block) path")

    # Check stop-guard has block path
    stop_guard = hooks_dir / "stop-guard.py"
    if stop_guard.is_file():
        try:
            content = stop_guard.read_text(encoding="utf-8")
        except OSError:
            content = ""
        has_block = any(kw in content for kw in BLOCK_KEYWORDS)
        if not has_block:
            errors.append("stop-guard.py: missing block (hard block) path")

    # Check subagent-stop-guard has block path
    sub_stop = hooks_dir / "subagent-stop-guard.py"
    if sub_stop.is_file():
        try:
            content = sub_stop.read_text(encoding="utf-8")
        except OSError:
            content = ""
        has_block = any(kw in content for kw in BLOCK_KEYWORDS)
        if not has_block:
            errors.append("subagent-stop-guard.py: missing block (hard block) path")
        required_agents = agent_result_required_agents(content)
        if required_agents is None:
            errors.append("subagent-stop-guard.py: cannot resolve AGENTS_REQUIRE_AGENT_RESULT")
        else:
            missing = sorted(set(CANONICAL_AGENTS) - required_agents)
            if missing:
                errors.append(
                    "subagent-stop-guard.py: AGENTS_REQUIRE_AGENT_RESULT missing "
                    + ", ".join(missing)
                )

    # Check inject-subagent-context supports all canonical agents
    inject = hooks_dir / "inject-subagent-context.py"
    if inject.is_file():
        try:
            content = inject.read_text(encoding="utf-8")
        except OSError:
            content = ""
        for agent in CANONICAL_AGENTS:
            if agent not in content:
                errors.append(f"inject-subagent-context.py: missing agent '{agent}'")
        required_agents = agent_result_required_agents(content)
        if required_agents is None:
            errors.append("inject-subagent-context.py: cannot resolve AGENTS_REQUIRE_AGENT_RESULT")
        else:
            missing = sorted(set(CANONICAL_AGENTS) - required_agents)
            if missing:
                errors.append(
                    "inject-subagent-context.py: AGENTS_REQUIRE_AGENT_RESULT missing "
                    + ", ".join(missing)
                )

    # Check lib modules
    lib_dir = hooks_dir / "lib"
    if lib_dir.is_dir():
        for lib_file in lib_dir.glob("*.py"):
            if lib_file.name == "__init__.py":
                continue
            try:
                source = lib_file.read_text(encoding="utf-8")
                ast.parse(source)
            except SyntaxError as e:
                errors.append(f"lib/{lib_file.name}: syntax error: {e}")
            except OSError:
                pass

    return len(errors) == 0, errors


def main() -> int:
    cwd = Path.cwd()
    root = find_project_root(cwd)
    if root is None:
        print("FAIL: No .claude directory found. Run from a project root.")
        return 1

    hooks_dir = find_hooks_dir(root)
    if hooks_dir is None:
        print("FAIL: No .claude/hooks or claude/hooks directory found.")
        return 1
    ok, errors = validate_hooks(hooks_dir)

    if ok:
        print("PASS: All hooks validated")
        return 0

    print(f"FAIL: {len(errors)} hook issue(s):")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
