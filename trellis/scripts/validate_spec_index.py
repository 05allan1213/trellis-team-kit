#!/usr/bin/env python3
"""Validate spec index integrity.

Checks that the spec index tree is consistent: root index links to
sub-indexes, sub-indexes reference files that exist, and there are
no dangling spec links.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def read_file(path: Path) -> str | None:
    """Read file contents, return None if file does not exist."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def extract_markdown_links(content: str, base_dir: Path) -> list[tuple[str, Path]]:
    """Extract markdown links from content, returning (display_text, resolved_path)."""
    links = []
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content):
        display_text = match.group(1)
        link_path = match.group(2)
        if link_path.startswith(("http://", "https://", "mailto:", "#")):
            continue
        resolved = (base_dir / link_path).resolve()
        links.append((display_text, resolved))
    return links


def validate_spec_index(spec_dir: str) -> bool:
    """Run all spec index validations. Returns True if PASS."""
    spec_path = Path(spec_dir).resolve()

    if not spec_path.exists():
        print(f"FAIL: spec directory does not exist: {spec_path}")
        return False

    all_issues: list[str] = []

    root_index = spec_path / "index.md"
    root_content = read_file(root_index)
    if root_content is None:
        print(f"FAIL: root spec index not found: {root_index}")
        return False

    print(f"Root index found: {root_index}")

    root_links = extract_markdown_links(root_content, spec_path)

    sub_index_links = []
    for display_text, link_path in root_links:
        if not link_path.exists():
            all_issues.append(
                f"Root index links to '{link_path}' (text: '{display_text}') but file does not exist"
            )
            continue

        if link_path.name == "index.md" and link_path != root_index:
            sub_index_links.append((display_text, link_path))

    print(f"Sub-indexes referenced: {len(sub_index_links)}")

    for display_text, sub_index_path in sub_index_links:
        sub_content = read_file(sub_index_path)
        if sub_content is None:
            all_issues.append(
                f"Sub-index '{sub_index_path}' referenced but cannot be read"
            )
            continue

        sub_links = extract_markdown_links(sub_content, sub_index_path.parent)
        for link_text, link_path in sub_links:
            if link_path.name == "index.md":
                continue
            if not link_path.exists():
                all_issues.append(
                    f"Sub-index '{sub_index_path.name}' links to '{link_path}' "
                    f"(text: '{link_text}') but file does not exist"
                )

    for md_file in spec_path.rglob("*.md"):
        if md_file.name == "index.md":
            continue
        content = read_file(md_file)
        if content is None:
            continue

        links = extract_markdown_links(content, md_file.parent)
        for link_text, link_path in links:
            if link_path.name == "index.md":
                continue
            if not link_path.exists():
                all_issues.append(
                    f"Spec file '{md_file.relative_to(spec_path)}' links to "
                    f"'{link_path}' (text: '{link_text}') but target does not exist"
                )

    if all_issues:
        print("FAIL: the following issues were found:")
        for issue in all_issues:
            print(f"  - {issue}")
        return False

    print("PASS: spec index is consistent with no dangling links")
    return True


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <spec-dir>")
        return 1

    passed = validate_spec_index(argv[1])
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
