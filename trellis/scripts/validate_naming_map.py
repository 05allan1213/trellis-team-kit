#!/usr/bin/env python3
"""
validate_naming_map.py — 验证命名一致性。

检查：
- 所有 agent frontmatter name 在 canonical agent 列表中
- Hook 脚本使用 canonical agent names
- 同时支持 kit 仓库布局（claude/）和安装后项目布局（.claude/）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CANONICAL_AGENTS = {
    "trellis-researcher",
    "trellis-implementer",
    "trellis-checker",
    "trellis-spec-reviewer",
    "trellis-code-reviewer",
    "trellis-architecture-reviewer",
    "trellis-architecture-deep-reviewer",
    "trellis-merge-reviewer",
    "trellis-spec-updater",
}

CANONICAL_SKILLS = {
    "trellis-brainstorm", "trellis-grill-me", "trellis-dev-strategy",
    "trellis-before-dev", "trellis-implement", "trellis-check",
    "trellis-spec-review", "trellis-code-review",
    "trellis-code-architecture-review", "trellis-improve-codebase-architecture",
    "trellis-update-spec", "trellis-break-loop", "trellis-merge-review",
    "trellis-finish-work",
}

# trellis init 基础模板自带的 agent 名称（与 kit canonical 不同但合法）
TRELLIS_BASE_AGENTS = {
    "trellis-research", "trellis-check", "trellis-implement",
}

KNOWN_NAMES = CANONICAL_AGENTS | CANONICAL_SKILLS | TRELLIS_BASE_AGENTS


def find_project_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        # Kit 仓库布局
        if (cur / "claude" / "agents").is_dir():
            return cur
        # 安装后项目布局
        if (cur / ".claude" / "agents").is_dir():
            return cur
        cur = cur.parent
    return None


def find_agents_dir(root: Path) -> Path | None:
    installed = root / ".claude" / "agents"
    if installed.is_dir():
        return installed
    kit = root / "claude" / "agents"
    if kit.is_dir():
        return kit
    return None


def find_hooks_dir(root: Path) -> Path | None:
    installed = root / ".claude" / "hooks"
    if installed.is_dir():
        return installed
    kit = root / "claude" / "hooks"
    if kit.is_dir():
        return kit
    return None


def check_naming(root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    agents_dir = find_agents_dir(root)
    if agents_dir is None:
        return False, ["找不到 agents 目录"]

    # 检查 agent frontmatter names
    for agent_file in agents_dir.glob("*.md"):
        try:
            content = agent_file.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
        if m:
            name = m.group(1).strip()
            if name not in CANONICAL_AGENTS and name.startswith("trellis-"):
                if name in TRELLIS_BASE_AGENTS:
                    continue  # trellis init 基础模板自带，非 kit 管理
                errors.append(
                    f"{agent_file.name}: frontmatter name '{name}' "
                    f"不在 canonical agent 列表中"
                )

    # 检查 hooks 使用 canonical agent names
    hooks_dir = find_hooks_dir(root)
    if hooks_dir is not None:
        for hook_file in hooks_dir.glob("*.py"):
            try:
                content = hook_file.read_text(encoding="utf-8")
            except OSError:
                continue

            agent_refs = re.findall(r'"trellis-[\w-]+"', content)
            for ref in agent_refs:
                name = ref.strip('"')
                if name.startswith("trellis-") and name not in KNOWN_NAMES:
                    errors.append(
                        f"{hook_file.name}: 引用了未知名称 '{name}'"
                    )

    return len(errors) == 0, errors


def main() -> int:
    cwd = Path.cwd()
    root = find_project_root(cwd)
    if root is None:
        print("FAIL: 找不到 trellis-team-kit 或项目根目录")
        return 1

    ok, errors = check_naming(root)
    if ok:
        print("PASS: 命名一致性检查通过")
        return 0

    print(f"FAIL: {len(errors)} 个命名问题：")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
