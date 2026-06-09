#!/usr/bin/env python3
"""Compatibility wrapper for the canonical task validator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_IMPL_PATH = Path(__file__).resolve().parents[1] / "trellis" / "scripts" / "validate_task.py"

_SPEC = importlib.util.spec_from_file_location("validate_task_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Cannot load validator implementation: {_IMPL_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

validate_task = _MODULE.validate_task
main = _MODULE.main


if __name__ == "__main__":
    sys.exit(main())
