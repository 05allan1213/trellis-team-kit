#!/usr/bin/env python3
"""
validate_runtime_hardening.py — Master validator entry point.

Runs all static validators and reports PASS/FAIL for each.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def find_scripts_dir(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        scripts = cur / ".trellis" / "scripts"
        if scripts.is_dir():
            return scripts
        # Also check trellis-team-kit layout
        scripts = cur / "trellis" / "scripts"
        if scripts.is_dir():
            return scripts
        cur = cur.parent
    return None


def find_spec_dir(scripts_dir: Path) -> Path | None:
    """Find the spec directory for either an installed project or this source repo."""
    installed_spec_dir = scripts_dir.parent / "spec"
    if installed_spec_dir.is_dir():
        return installed_spec_dir

    source_spec_dir = scripts_dir.parent.parent / "marketplace" / "specs" / "web-app"
    if source_spec_dir.is_dir():
        return source_spec_dir

    return None


def find_replay_dir(scripts_dir: Path) -> Path | None:
    """Find replay fixtures for either an installed project or this source repo."""
    installed_replay_dir = scripts_dir.parent / "replay"
    if installed_replay_dir.is_dir():
        return installed_replay_dir

    source_replay_dir = scripts_dir.parent.parent / "tests" / "fixtures" / "replay"
    if source_replay_dir.is_dir():
        return source_replay_dir

    return None


def run_validator(script_path: Path, args: list[str] | None = None) -> tuple[str, bool, str]:
    """Run a validator script. Returns (name, passed, output)."""
    cmd = ["python3", str(script_path)]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=30,
        )
        passed = result.returncode == 0
        output = result.stdout.strip()
        if result.stderr.strip():
            output += "\n" + result.stderr.strip()
        return script_path.name, passed, output
    except subprocess.TimeoutExpired:
        return script_path.name, False, "TIMEOUT"
    except FileNotFoundError:
        return script_path.name, False, "python3 not found"
    except Exception as e:
        return script_path.name, False, str(e)


def main() -> int:
    cwd = Path.cwd()
    scripts_dir = find_scripts_dir(cwd)

    if scripts_dir is None:
        print("FAIL: Cannot find .trellis/scripts/ or trellis/scripts/ directory")
        return 1

    print("=" * 50)
    print("  Trellis Team Kit v0.3 Runtime Hardening Validator")
    print("=" * 50)
    print()

    spec_dir = find_spec_dir(scripts_dir)
    replay_dir = find_replay_dir(scripts_dir)
    validators = [
        "validate_claude_settings.py",
        "validate_naming_map.py",
        "validate_hooks.py",
        "validate_trellis_config.py",
        "validate_spec_index.py",
        "validate_routing_rules.py",
        "validate_scope_manifest.py",
        "validate_guardrail_overrides.py",
        "validate_agent_results.py",
        "validate_spec_update_targets.py",
        "replay_workflow_cases.py",
        "detect_spec_update_candidates.py",
        "trellis_doctor.py",
    ]
    availability_only_validators = {
        "validate_scope_manifest.py",
        "validate_guardrail_overrides.py",
        "validate_agent_results.py",
    }

    results: list[tuple[str, str, bool, str]] = []
    for vname in validators:
        vpath = scripts_dir / vname
        if not vpath.is_file():
            results.append((vname, "FAIL", False, "Script not found"))
            continue
        args = None
        if vname == "validate_spec_index.py":
            if spec_dir is None:
                results.append((vname, "FAIL", False, "Spec directory not found"))
                continue
            args = [str(spec_dir)]
        elif vname == "replay_workflow_cases.py":
            if replay_dir is None:
                results.append((vname, "FAIL", False, "Replay fixture directory not found"))
                continue
            args = [str(replay_dir)]
        name, passed, output = run_validator(vpath, args)
        if vname in availability_only_validators and args is None:
            note = "availability check only; pass a task directory for task-runtime validation"
            output = f"{output}\n{note}" if output else note
            results.append((name, "INFO" if passed else "FAIL", passed, output))
        else:
            status_label = "PASS" if passed else "FAIL"
            results.append((name, status_label, passed, output))

    # Print results
    all_pass = True
    for name, status, passed, output in results:
        print(f"[{status}] {name}")
        if output:
            for line in output.splitlines():
                print(f"       {line}")
        print()
        if status == "FAIL" or not passed:
            all_pass = False

    print("=" * 50)
    if all_pass:
        print("  OVERALL: PASS — Runtime hardening checks passed")
    else:
        print("  OVERALL: FAIL — Some checks failed. Fix issues above.")
    print("=" * 50)

    # Hint about task-specific validators
    print()
    print("Task-specific validators (require a task directory argument):")
    print(f"  python3 {scripts_dir}/validate_task.py <task-dir>")
    print(f"  python3 {scripts_dir}/validate_scope_manifest.py <task-dir>")
    print(f"  python3 {scripts_dir}/validate_guardrail_overrides.py <task-dir>")
    print(f"  python3 {scripts_dir}/validate_agent_results.py <task-dir>")
    print(f"  python3 {scripts_dir}/validate_review_gates.py <task-dir>")
    print(f"  python3 {scripts_dir}/validate_delivery_sync.py <task-dir>")
    print(f"  python3 {scripts_dir}/validate_workflow_state.py <task-dir>")
    print(f"  python3 {scripts_dir}/trellis_doctor.py workflow <task-dir>")
    print()
    print("Replay/spec maintenance:")
    print(f"  python3 {scripts_dir}/replay_workflow_cases.py <replay-fixtures-dir>")
    print(f"  python3 {scripts_dir}/detect_spec_update_candidates.py [changed-file ...]")
    print(f"  python3 {scripts_dir}/validate_spec_update_targets.py")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
