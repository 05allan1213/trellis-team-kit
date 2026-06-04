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
    validators = [
        "validate_claude_settings.py",
        "validate_naming_map.py",
        "validate_hooks.py",
        "validate_spec_index.py",
        "validate_routing_rules.py",
    ]

    results: list[tuple[str, bool, str]] = []
    for vname in validators:
        vpath = scripts_dir / vname
        if not vpath.is_file():
            results.append((vname, False, "Script not found"))
            continue
        args = None
        if vname == "validate_spec_index.py":
            if spec_dir is None:
                results.append((vname, False, "Spec directory not found"))
                continue
            args = [str(spec_dir)]
        name, passed, output = run_validator(vpath, args)
        results.append((name, passed, output))

    # Print results
    all_pass = True
    for name, passed, output in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
        if output:
            for line in output.splitlines():
                print(f"       {line}")
        print()
        if not passed:
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
    print(f"  python3 {scripts_dir}/validate_review_gates.py <task-dir>")
    print(f"  python3 {scripts_dir}/validate_delivery_sync.py <task-dir>")
    print(f"  python3 {scripts_dir}/validate_workflow_state.py <task-dir>")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
