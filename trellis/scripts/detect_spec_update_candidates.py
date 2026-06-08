#!/usr/bin/env python3
"""Suggest spec or workflow docs that may need updates for changed paths."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import PurePosixPath


def normalize_path(path: str) -> str:
    """Return a repository-style path with forward slashes and no leading ./."""
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def logical_path(path: str) -> str:
    """Map installed Trellis paths to source-layout paths for rule matching."""
    normalized = normalize_path(path)
    if normalized.startswith(".claude/"):
        return "claude/" + normalized[len(".claude/") :]
    if normalized.startswith(".trellis/config/"):
        return "trellis/config/" + normalized[len(".trellis/config/") :]
    if normalized == ".trellis/workflow.md":
        return "workflow/workflow.md"
    if normalized.startswith(".trellis/workflow/"):
        return "workflow/" + normalized[len(".trellis/workflow/") :]
    if normalized.startswith(".trellis/spec/"):
        return "spec/" + normalized[len(".trellis/spec/") :]
    if normalized.startswith(".trellis/scripts/"):
        return "trellis/scripts/" + normalized[len(".trellis/scripts/") :]
    return normalized


def path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")


def read_changed_paths_from_git() -> list[str]:
    diff_result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    untracked_result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        text=True,
        capture_output=True,
        check=False,
    )
    if diff_result.returncode != 0 and untracked_result.returncode != 0:
        return []

    changed: list[str] = []
    seen: set[str] = set()
    for output in (diff_result.stdout, untracked_result.stdout):
        for line in output.splitlines():
            path = line.strip()
            if not path or path in seen:
                continue
            changed.append(path)
            seen.add(path)
    return changed


def add_candidate(
    candidates: list[dict[str, str]],
    seen_targets: set[str],
    target: str,
    reason: str,
) -> None:
    if target in seen_targets:
        return
    candidates.append({"target": target, "reason": reason})
    seen_targets.add(target)


def detect_candidates(changed_files: list[str]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen_targets: set[str] = set()

    for changed_file in changed_files:
        path = logical_path(changed_file)

        if path_matches_prefix(path, "claude/hooks"):
            add_candidate(
                candidates,
                seen_targets,
                "spec/guides/ai-behavior/guardrails.md",
                "Claude hook behavior changed; guardrail guidance may need to match runtime behavior.",
            )

        if path_matches_prefix(path, "claude/skills"):
            add_candidate(
                candidates,
                seen_targets,
                "spec/guides/ai-behavior/skill-routing.md",
                "Claude skill behavior changed; skill routing guidance may need to be refreshed.",
            )

        if path_matches_prefix(path, "claude/agents"):
            add_candidate(
                candidates,
                seen_targets,
                "spec/guides/ai-behavior/agent-results.md",
                "Claude agent behavior changed; agent-results or agent guidance may need to be refreshed.",
            )

        if path_matches_prefix(path, "trellis/scripts"):
            add_candidate(
                candidates,
                seen_targets,
                "docs/verify-workflow.md",
                "Trellis runtime script behavior changed; workflow verification docs may need updated commands or expectations.",
            )

        if path_matches_prefix(path, "claude/commands/trellis"):
            add_candidate(
                candidates,
                seen_targets,
                "docs/verify-workflow.md",
                "Trellis command behavior changed; workflow verification docs may need updated command guidance.",
            )

        if path == "claude/commands/trellis/doctor.md":
            add_candidate(
                candidates,
                seen_targets,
                "claude/commands/trellis/doctor.md",
                "Doctor command changed; command docs should stay aligned with trellis_doctor.py behavior.",
            )

        if path_matches_prefix(path, "bootstrap"):
            add_candidate(
                candidates,
                seen_targets,
                "bootstrap/smoke-test-install.sh",
                "Installer behavior changed; smoke install checks may need to cover the new installed artifacts.",
            )

        if path == "README.md":
            add_candidate(
                candidates,
                seen_targets,
                "docs/verify-workflow.md",
                "README workflow guidance changed; verification docs may need to stay aligned.",
            )

        if path == "docs/verify-workflow.md":
            add_candidate(
                candidates,
                seen_targets,
                "README.md",
                "Workflow verification docs changed; README workflow summary may need to stay aligned.",
            )

        if path == "trellis/config/routing_rules.json":
            add_candidate(
                candidates,
                seen_targets,
                "workflow/routing.md",
                "Routing rules changed; workflow routing documentation may need to match the rules.",
            )

        if path == "omc/orchestration.md":
            add_candidate(
                candidates,
                seen_targets,
                "spec/guides/ai-behavior/orchestration.md",
                "OMC orchestration guidance changed; AI behavior orchestration guidance may need sync.",
            )

        if path_matches_prefix(path, "workflow"):
            add_candidate(
                candidates,
                seen_targets,
                "README.md",
                "Workflow documentation changed; README workflow summary may need to stay in sync.",
            )

        path_parts = set(PurePosixPath(path).parts)
        if (
            path_matches_prefix(path, "tests/fixtures/replay")
            or "replay" in path_parts
            or "replay-failures" in path_parts
        ):
            add_candidate(
                candidates,
                seen_targets,
                "spec/guides/ai-behavior/common-mistakes.md",
                "Replay failure evidence changed; common mistakes guidance may need a new lesson.",
            )

    return candidates


def build_payload(argv: list[str]) -> dict[str, object]:
    raw_paths = argv if argv else read_changed_paths_from_git()
    changed_files = [normalize_path(path) for path in raw_paths if normalize_path(path)]
    candidates = detect_candidates(changed_files)
    return {
        "need_spec_update": bool(candidates),
        "candidates": candidates,
        "changed_files": changed_files,
    }


def main(argv: list[str]) -> int:
    payload = build_payload(argv)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
