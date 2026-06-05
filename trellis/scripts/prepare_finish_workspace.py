#!/usr/bin/env python3
"""Prepare repository-local Trellis/OMC state before the final code commit.

This script makes local workflow/runtime state safe for Phase 3.2 commits:
- ensure ignore rules exist for local-only state
- untrack any previously tracked local-only state paths
- remove stale, unregistered `.trellis/worktrees/*` residue

It does NOT delete active git worktrees. Cleanup only removes `.trellis`
residue directories that are not registered in `git worktree list`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

IGNORE_BLOCK_BEGIN = "# BEGIN trellis-team-kit local state"
IGNORE_BLOCK_END = "# END trellis-team-kit local state"
IGNORE_BLOCK_LINES = [
    IGNORE_BLOCK_BEGIN,
    ".trellis/.developer",
    ".trellis/worktrees/",
    ".claude/settings.local.json",
    ".omc/",
    "**/.omc/",
    IGNORE_BLOCK_END,
]


def find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".git").is_dir():
            return cur
        cur = cur.parent
    return None


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )


def ensure_ignore_block(repo_root: Path) -> bool:
    gitignore = repo_root / ".gitignore"
    existing = ""
    if gitignore.is_file():
        existing = gitignore.read_text(encoding="utf-8")

    if IGNORE_BLOCK_BEGIN in existing and IGNORE_BLOCK_END in existing:
        return False

    block = "\n".join(IGNORE_BLOCK_LINES) + "\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    gitignore.write_text(existing + block, encoding="utf-8")
    return True


def _is_local_state_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        return False
    if normalized == ".trellis/.developer" or normalized.startswith(".trellis/.developer/"):
        return True
    if normalized == ".trellis/worktrees" or normalized.startswith(".trellis/worktrees/"):
        return True
    if normalized == ".claude/settings.local.json":
        return True
    parts = normalized.split("/")
    return ".omc" in parts


def tracked_local_state_paths(repo_root: Path) -> list[str]:
    result = _run_git(repo_root, ["ls-files", "-z"])
    if result.returncode != 0:
        return []

    paths = [p for p in result.stdout.split("\0") if p]
    return [p for p in paths if _is_local_state_path(p)]


def untrack_paths(repo_root: Path, paths: list[str]) -> bool:
    if not paths:
        return False

    result = _run_git(repo_root, ["rm", "--cached", "-r", "--quiet", "--ignore-unmatch", "--", *paths])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git rm --cached failed")
    return True


def _registered_worktree_paths(repo_root: Path) -> set[Path]:
    result = _run_git(repo_root, ["worktree", "list", "--porcelain"])
    if result.returncode != 0:
        return set()

    paths: set[Path] = set()
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            raw_path = line[len("worktree "):].strip()
            if raw_path:
                paths.add(Path(raw_path).resolve())
    return paths


def cleanup_stale_trellis_worktrees(repo_root: Path) -> list[str]:
    worktrees_dir = repo_root / ".trellis" / "worktrees"
    if not worktrees_dir.is_dir():
        return []

    registered = _registered_worktree_paths(repo_root)
    changes: list[str] = []
    for child in sorted(worktrees_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.resolve() in registered:
            continue
        if (child / ".git").exists():
            continue
        shutil.rmtree(child)
        changes.append(f"removed stale trellis worktree residue '{child.relative_to(repo_root)}'")
    return changes


def prepare_finish_workspace(repo_root: Path) -> tuple[list[str], list[str]]:
    changes: list[str] = []
    warnings: list[str] = []

    if ensure_ignore_block(repo_root):
        changes.append("updated .gitignore with local-state ignore rules")

    tracked = tracked_local_state_paths(repo_root)
    if tracked:
        untrack_paths(repo_root, tracked)
        changes.append(f"untracked {len(tracked)} local-state path(s) from git index")

    changes.extend(cleanup_stale_trellis_worktrees(repo_root))

    if not changes:
        warnings.append("no local-state cleanup was needed")

    return changes, warnings


def main() -> int:
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        print("FAIL: cannot find git repository root")
        return 1

    try:
        changes, warnings = prepare_finish_workspace(repo_root)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    if changes:
        print("PASS: finish workspace prepared")
        for item in changes:
            print(f"  - {item}")
    else:
        print("PASS: finish workspace already clean")

    for item in warnings:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
