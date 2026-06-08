#!/usr/bin/env python3
"""Replay workflow behavior cases from JSON fixtures."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parent.parent


def _layout_path(source_relative: str, installed_relative: str) -> Path:
    installed = REPO_ROOT / installed_relative
    source = REPO_ROOT / source_relative
    if SCRIPT_DIR.parent.name == ".trellis":
        return installed
    return source if source.exists() else installed


HOOKS_DIR = _layout_path("claude/hooks", ".claude/hooks")
TRELLIS_SCRIPTS_DIR = _layout_path("trellis/scripts", ".trellis/scripts")
TRELLIS_CONFIG_DIR = _layout_path("trellis/config", ".trellis/config")
INJECT_WORKFLOW_STATE = HOOKS_DIR / "inject-workflow-state.py"
VALIDATOR_SCRIPTS = {
    "validate-task": TRELLIS_SCRIPTS_DIR / "validate_task.py",
    "validate-scope-manifest": TRELLIS_SCRIPTS_DIR / "validate_scope_manifest.py",
    "validate-guardrail-overrides": TRELLIS_SCRIPTS_DIR / "validate_guardrail_overrides.py",
    "validate-agent-results": TRELLIS_SCRIPTS_DIR / "validate_agent_results.py",
}


@dataclass
class ReplayResult:
    path: Path
    name: str
    passed: bool
    message: str
    text: str


def _read_case(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"{path}: replay case must be a JSON object")
    return data


def _write_tree(root: Path, files: dict[str, Any]) -> None:
    for rel_path, value in files.items():
        if not isinstance(rel_path, str) or not rel_path.strip():
            raise ValueError("fixture file paths must be non-empty strings")
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, (dict, list)):
            text = json.dumps(value, indent=2) + "\n"
        else:
            text = str(value)
        target.write_text(text, encoding="utf-8")


def _prepare_workspace(case: dict[str, Any], tmp_root: Path) -> Path:
    workspace = tmp_root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    trellis_dir = workspace / ".trellis"
    trellis_dir.mkdir(exist_ok=True)
    (trellis_dir / "workflow.md").write_text("", encoding="utf-8")
    config_dir = trellis_dir / "config"
    config_dir.mkdir(exist_ok=True)
    for config_name in ("routing_rules.json", "workflow_profiles.json"):
        source = TRELLIS_CONFIG_DIR / config_name
        if source.is_file():
            shutil.copy2(source, config_dir / config_name)

    workspace_data = case.get("workspace", {})
    if workspace_data is None:
        workspace_data = {}
    if not isinstance(workspace_data, dict):
        raise ValueError("workspace must be a JSON object")

    copy_from = workspace_data.get("copy_from")
    if copy_from:
        src = Path(str(copy_from))
        if not src.is_absolute():
            src = REPO_ROOT / src
        if not src.is_dir():
            raise ValueError(f"workspace.copy_from directory not found: {src}")
        shutil.copytree(src, workspace, dirs_exist_ok=True)

    files = workspace_data.get("files", {})
    if files:
        if not isinstance(files, dict):
            raise ValueError("workspace.files must be a JSON object")
        _write_tree(workspace, files)

    task = workspace_data.get("task")
    if task is not None:
        _prepare_task(workspace, task)

    return workspace


def _prepare_task(workspace: Path, task: Any) -> Path:
    if not isinstance(task, dict):
        raise ValueError("workspace.task must be a JSON object")
    rel_task_dir = str(task.get("path") or ".trellis/tasks/replay-task")
    task_dir = workspace / rel_task_dir
    task_dir.mkdir(parents=True, exist_ok=True)

    data = task.get("task_json", {})
    if not isinstance(data, dict):
        raise ValueError("workspace.task.task_json must be a JSON object")
    if "id" not in data:
        data["id"] = task_dir.name
    if "level" not in data:
        data["level"] = "L2"
    if "status" not in data:
        data["status"] = "in_progress"
    (task_dir / "task.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    if task.get("active", False):
        (workspace / ".trellis" / "active-task").write_text(rel_task_dir, encoding="utf-8")

    files = task.get("files", {})
    if files:
        if not isinstance(files, dict):
            raise ValueError("workspace.task.files must be a JSON object")
        _write_tree(task_dir, files)

    return task_dir


def _run_subprocess(args: list[str], *, input_text: str = "", cwd: Path | None = None) -> str:
    result = subprocess.run(
        args,
        input=input_text,
        cwd=str(cwd or REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return "\n".join(
        part
        for part in (
            f"exit_code={result.returncode}",
            result.stdout.strip(),
            result.stderr.strip(),
        )
        if part
    )


def _run_inject_workflow_state(case: dict[str, Any], workspace: Path) -> str:
    input_data = case.get("input", {})
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")
    payload = {"cwd": str(workspace)}
    payload.update(input_data)

    raw = _run_subprocess(
        [sys.executable, str(INJECT_WORKFLOW_STATE)],
        input_text=json.dumps(payload),
        cwd=REPO_ROOT,
    )
    context = ""
    first_json = raw.find("{")
    if first_json >= 0:
        try:
            decoded = json.loads(raw[first_json:])
            context = str(
                decoded.get("hookSpecificOutput", {}).get("additionalContext", "")
            )
        except json.JSONDecodeError:
            context = ""
    return raw + ("\n" + context if context else "")


def _run_router(case: dict[str, Any], workspace: Path) -> str:
    input_data = case.get("input", {})
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")
    prompt = str(input_data.get("prompt", ""))
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str((HOOKS_DIR / 'lib')).__repr__()})\n"
        "from pathlib import Path\n"
        "from prompt_routing import classify_no_task_prompt\n"
        f"decision = classify_no_task_prompt({prompt!r}, root=Path({str(workspace)!r}))\n"
        "print(f'route={decision.route}')\n"
        "print(f'confidence={decision.confidence}')\n"
        "for reason in decision.reasons:\n"
        "    print(reason)\n"
    )
    return _run_subprocess([sys.executable, "-c", script], cwd=REPO_ROOT)


def _resolve_task_arg(case: dict[str, Any], workspace: Path) -> Path:
    input_data = case.get("input", {})
    if input_data is None:
        input_data = {}
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")
    task_dir = input_data.get("task_dir")
    if task_dir:
        path = Path(str(task_dir))
        return path if path.is_absolute() else workspace / path

    task = case.get("workspace", {}).get("task") if isinstance(case.get("workspace"), dict) else None
    if isinstance(task, dict) and task.get("path"):
        return workspace / str(task["path"])
    return workspace / ".trellis" / "tasks" / "replay-task"


def _run_validator(case: dict[str, Any], workspace: Path, runner: str) -> str:
    script = VALIDATOR_SCRIPTS.get(runner)
    if script is None:
        raise ValueError(f"unsupported validator runner: {runner}")
    task_dir = _resolve_task_arg(case, workspace)
    return _run_subprocess([sys.executable, str(script), str(task_dir)], cwd=REPO_ROOT)


def _run_script(case: dict[str, Any], workspace: Path) -> str:
    input_data = case.get("input", {})
    if not isinstance(input_data, dict):
        raise ValueError("input must be a JSON object")
    command = input_data.get("command")
    if not isinstance(command, list) or not command:
        raise ValueError("script cases require input.command as a non-empty list")
    args = [str(part).replace("{workspace}", str(workspace)).replace("{repo}", str(REPO_ROOT)) for part in command]
    stdin = str(input_data.get("stdin", ""))
    return _run_subprocess(args, input_text=stdin, cwd=workspace)


def _execute_case(path: Path, case: dict[str, Any]) -> str:
    runner = str(case.get("run", "")).strip()
    if not runner:
        raise ValueError(f"{path}: missing run")

    with tempfile.TemporaryDirectory(prefix="trellis-replay-") as tmpdir:
        workspace = _prepare_workspace(case, Path(tmpdir))
        if runner in ("inject-workflow-state", "hook:inject-workflow-state"):
            return _run_inject_workflow_state(case, workspace)
        if runner == "router":
            return _run_router(case, workspace)
        if runner.startswith("validate-"):
            return _run_validator(case, workspace, runner)
        if runner == "script":
            return _run_script(case, workspace)
        raise ValueError(f"{path}: unsupported run value '{runner}'")


def _listify(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError(f"expect.{field_name} must be a string or list of strings")


def _check_expectations(text: str, expect: Any) -> tuple[bool, str]:
    if expect is None:
        expect = {}
    if not isinstance(expect, dict):
        raise ValueError("expect must be a JSON object")

    failures: list[str] = []
    for expected in _listify(expect.get("contains"), "contains"):
        if expected not in text:
            failures.append(f"missing expected text: {expected}")
    for unexpected in _listify(expect.get("not_contains"), "not_contains"):
        if unexpected in text:
            failures.append(f"found unexpected text: {unexpected}")

    if failures:
        return False, "; ".join(failures)
    return True, "ok"


def replay_case(path: Path) -> ReplayResult:
    try:
        case = _read_case(path)
        name = str(case.get("name") or path.stem)
        text = _execute_case(path, case)
        passed, message = _check_expectations(text, case.get("expect"))
        return ReplayResult(path=path, name=name, passed=passed, message=message, text=text)
    except Exception as e:
        return ReplayResult(path=path, name=path.stem, passed=False, message=str(e), text="")


def run_replay_cases(root: Path | str) -> list[ReplayResult]:
    root_path = Path(root)
    if root_path.is_file():
        case_paths = [root_path]
    else:
        case_paths = sorted(root_path.rglob("*.json"))
    return [replay_case(path) for path in case_paths]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay workflow JSON cases.")
    parser.add_argument("path", nargs="?", help="Replay fixture file or directory")
    args = parser.parse_args(argv)
    if not args.path:
        print("PASS: replay_workflow_cases.py is available")
        return 0

    results = run_replay_cases(args.path)
    if not results:
        print(f"FAIL no replay cases found under {args.path}")
        return 1

    failures = 0
    for result in results:
        rel_path = os.path.relpath(result.path, REPO_ROOT)
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {rel_path}: {result.name}")
        if not result.passed:
            failures += 1
            print(f"  {result.message}")
    print(f"Replay cases: {len(results) - failures}/{len(results)} passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
