#!/usr/bin/env python3
"""Validate finish-stage delivery sync between implementation and user docs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import re

PUBLIC_LITERAL_RE = re.compile(r"/(?:[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.:-]+)+)")
SOURCE_EXTS = {
    ".go", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".rb", ".php",
    ".rs", ".kt", ".swift", ".sh", ".bash", ".zsh", ".sql", ".json",
    ".yaml", ".yml", ".toml",
}
DOC_GLOBS = ("README.md", "docs/**/*.md", "docs/**/*.mdx")
SKIP_DIRS = {".git", ".trellis", ".claude", "node_modules", ".omc"}


def find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir() or (cur / ".git").is_dir():
            return cur
        cur = cur.parent
    return None


def _git_diff(repo_root: Path) -> str:
    commands = [
        ["git", "diff", "--unified=0", "--no-color", "HEAD", "--"],
        ["git", "diff", "--unified=0", "--no-color", "--"],
    ]
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=repo_root,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    return ""


def _is_doc_file(path_str: str) -> bool:
    path = Path(path_str)
    if path.name.lower() == "readme.md":
        return True
    return "docs" in path.parts and path.suffix.lower() in (".md", ".mdx")


def _is_source_file(path_str: str) -> bool:
    path = Path(path_str)
    if _is_doc_file(path_str):
        return False
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix.lower() in SOURCE_EXTS


def _extract_removed_public_literals(diff_text: str) -> set[str]:
    removed: set[str] = set()
    current_file = ""

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if line.startswith("--- a/") or line.startswith("@@"):
            continue
        if not current_file or not _is_source_file(current_file):
            continue
        if line.startswith("-") and not line.startswith("---"):
            removed.update(PUBLIC_LITERAL_RE.findall(line[1:]))

    return removed


def _collect_doc_files(repo_root: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for pattern in DOC_GLOBS:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            try:
                docs[str(path.relative_to(repo_root))] = path.read_text(encoding="utf-8")
            except OSError:
                continue
    return docs


def _literal_regex(literal: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_.:-]){re.escape(literal)}(?![A-Za-z0-9_.:/-])")


def _literal_in_current_source(repo_root: Path, literal: str) -> bool:
    literal_re = _literal_regex(literal)
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root)
        if not _is_source_file(rel.as_posix()):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if literal_re.search(content):
            return True
    return False


def validate_delivery_sync(task_dir: str | Path) -> tuple[bool, list[str]]:
    task_path = Path(task_dir)
    errors: list[str] = []

    if not task_path.exists():
        return False, [f"Task directory does not exist: {task_path}"]

    repo_root = find_repo_root(task_path)
    if repo_root is None:
        return False, [f"Cannot find repo root for task: {task_path}"]

    diff_text = _git_diff(repo_root)
    if not diff_text:
        return True, []

    removed_literals = _extract_removed_public_literals(diff_text)
    if not removed_literals:
        return True, []

    docs = _collect_doc_files(repo_root)
    if not docs:
        return True, []

    for literal in sorted(removed_literals):
        if _literal_in_current_source(repo_root, literal):
            continue
        literal_re = _literal_regex(literal)
        for doc_path, content in docs.items():
            if literal_re.search(content):
                errors.append(
                    f"{doc_path} still references removed public literal '{literal}'"
                )

    return len(errors) == 0, errors


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <task-dir>")
        return 1

    ok, issues = validate_delivery_sync(sys.argv[1])
    if ok:
        print("PASS: delivery sync checks passed")
        return 0

    print(f"FAIL: delivery sync has {len(issues)} issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
