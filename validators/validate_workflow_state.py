#!/usr/bin/env python3
"""Compatibility wrapper for the canonical workflow-state validator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_IMPL_PATH = (
    Path(__file__).resolve().parents[1]
    / "trellis"
    / "scripts"
    / "validate_workflow_state.py"
)

_SPEC = importlib.util.spec_from_file_location("validate_workflow_state_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Cannot load validator implementation: {_IMPL_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

validate_workflow_state = _MODULE.validate_workflow_state


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <task-dir>")
        return 1

    return 0 if validate_workflow_state(sys.argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main())
