Run Trellis setup or workflow health checks.

Usage:

```bash
/trellis:doctor setup
/trellis:doctor workflow
```

If no mode is provided, use `setup`.

## Setup Mode

Run:

```bash
python3 .trellis/scripts/trellis_doctor.py setup
```

Use this to verify installation-level health: managed scripts, validators,
config, hooks, skills, templates, and command availability.

## Workflow Mode

Run:

```bash
python3 .trellis/scripts/trellis_doctor.py workflow
```

Use this to inspect the active task's workflow alignment. The workflow doctor
reports:

- level/artifact mismatches
- inferred phase mismatches
- missing `before-dev.md`
- missing or invalid `scope-manifest.json`
- broad scope declarations
- unreviewed `runtime/guardrail-overrides.jsonl`
- review contract issues for the task level, including missing reviewer
  results or review artifacts that still contain placeholders
- missing or invalid `agent-results/*.json`
- OMC execution without explicit approval
- parallel or OMC execution without merge-review
- finish/spec-update placeholder evidence

When the report includes `To fix:` lines, follow those concrete repairs before
continuing the workflow.
