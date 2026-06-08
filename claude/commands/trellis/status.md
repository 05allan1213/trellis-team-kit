Show the current Trellis task status in a compact, actionable summary.

**Steps:**

1. Run `python3 .trellis/scripts/task.py current --source` to find the active task.
2. If no active task, output: `No active task. Use /trellis:new to start one.` and stop.
3. Read the task's `task.json` to get: id, status, level, title.
4. Infer the precise sub-phase using artifact presence:
   - planning + no prd.md → PLANNING_PRD
   - planning + prd.md but no implement.md → PLANNING_GRILL / PLANNING_DESIGN
   - planning + implement.md → WAITING_IMPLEMENTATION_APPROVAL
   - in_progress + no before-dev.md → BEFORE_DEV
   - in_progress + before-dev.md + no validation/ → IMPLEMENTING
   - in_progress + validation/check-results.md → CHECKING
   - in_progress + review/ dir with files → REVIEWING
   - in_progress + finish.md → FINISHING
5. Check which required artifacts are **missing** for the current level:
   - L2: prd.md
   - L3: prd.md, implement.md
   - L4: prd.md, design.md, implement.md
   - L5: prd.md, design.md, implement.md, research/
6. Check gate status: read review/ files for PASS/FAIL, read validation/test-results.md for build/test status.
7. Check scope and override audit:
   - If `before-dev.md` exists on an L2+ task, report whether `scope-manifest.json` exists and whether it has declared paths/globs.
   - If `runtime/guardrail-overrides.jsonl` exists, report entry count and whether `finish.md` contains a completed `Guardrail Overrides` review.
8. Output in this exact format:

```
📋 Trellis Status
─────────────────
Task:   <id> — <title>
Level:  <L2-L5>
Phase:  <current sub-phase>

Missing artifacts:
  - <file> (required for L<level>)

Gate results:
  check:   <PASS / FAIL / missing>
  reviews: <N PASS, M FAIL, K missing>

Validation:
  build:   <PASS / FAIL / missing>
  test:    <PASS / FAIL / missing>

Scope:
  manifest: <PASS / missing / invalid / n/a>
  declared: <N paths, M globs>

Guardrail overrides:
  ledger:  <none / N entries>
  review:  <PASS / missing / n/a>

Next step: <one actionable sentence>
```

If all artifacts exist and all gates pass, the next step should be the finish command.
