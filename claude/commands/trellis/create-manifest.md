Create a task manifest for the current work. Generate a manifest file that lists all task artifacts, their statuses, scope audit files, and the current workflow state. Run `task.py current --source` to find the active task, then collect all artifact file paths and write a manifest to the task directory.

Usage: Provide an optional task directory path as argument, or use the current active task.

Include `scope-manifest.json` and `runtime/guardrail-overrides.jsonl` in the manifest when present so finish/review can audit scope and overrides.
