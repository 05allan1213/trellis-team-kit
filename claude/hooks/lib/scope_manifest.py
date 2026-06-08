"""Scope manifest helpers shared by Trellis hooks."""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any


def normalize_repo_path(file_path: str) -> str:
    norm = file_path.replace("\\", "/").strip()
    while norm.startswith("./"):
        norm = norm[2:]
    return norm.strip("/")


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(normalize_repo_path(item))
    return result


def load_scope_manifest(task_dir: Path) -> dict[str, Any] | None:
    manifest_path = task_dir / "scope-manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def parse_markdown_declared_paths(implement_md: Path) -> list[str]:
    if not implement_md.is_file():
        return []
    try:
        content = implement_md.read_text(encoding="utf-8")
    except OSError:
        return []
    paths: list[str] = []
    in_section = False
    for line in content.splitlines():
        stripped = line.strip()
        clean = stripped.lstrip("#").strip()
        if (
            clean.lower().startswith("files / areas likely touched")
            or clean.lower().startswith("files/areas likely touched")
        ):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("##"):
                break
            m = re.match(r"-\s*`([^`]+)`", stripped)
            if m:
                paths.append(normalize_repo_path(m.group(1)))
    return paths


def load_declared_scope(task_dir: Path, implement_md: Path) -> tuple[list[str], list[str], str]:
    """Return declared paths, globs, and source label.

    scope-manifest.json is authoritative when present. implement.md parsing is
    retained as a backward-compatible fallback for older tasks.
    """
    manifest = load_scope_manifest(task_dir)
    if manifest is not None:
        return (
            _as_string_list(manifest.get("declared_paths")),
            _as_string_list(manifest.get("declared_globs")),
            "scope-manifest.json",
        )
    return parse_markdown_declared_paths(implement_md), [], "implement.md"


def _matches_path(norm: str, declared_path: str) -> bool:
    d = normalize_repo_path(declared_path)
    if not d:
        return False
    if norm == d:
        return True
    if d.endswith("/"):
        return norm.startswith(d)
    return norm.startswith(f"{d}/")


def _matches_glob(norm: str, declared_glob: str) -> bool:
    pattern = normalize_repo_path(declared_glob)
    if not pattern:
        return False
    return fnmatch.fnmatchcase(norm, pattern)


def is_path_declared(
    file_path: str,
    declared_paths: list[str],
    declared_globs: list[str] | None = None,
) -> bool:
    norm = normalize_repo_path(file_path)
    for declared_path in declared_paths:
        if _matches_path(norm, declared_path):
            return True
    for declared_glob in declared_globs or []:
        if _matches_glob(norm, declared_glob):
            return True
    return False


def format_declared_scope(paths: list[str], globs: list[str], limit: int = 5) -> str:
    values = [*paths, *[f"glob:{g}" for g in globs]]
    if not values:
        return "(none)"
    suffix = "..." if len(values) > limit else ""
    return ", ".join(values[:limit]) + suffix
