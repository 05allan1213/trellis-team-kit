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
   - in_progress + validation/check-results.md but pending/missing review gates → CHECKING / REVIEWING
   - in_progress + review/ dir with selected gates not all PASS → REVIEWING
   - in_progress + all selected review gates PASS but no finish.md → REVIEWING (waiting for explicit Finish consent)
   - in_progress + finish.md but no commit evidence → UPDATING_SPEC / COMMITTING
   - in_progress + merge-review required and missing/failing → MERGE_REVIEWING
   - in_progress + commit evidence but no validation/test-results.md → VALIDATING
   - in_progress + finish.md + commit evidence + validation/test-results.md → FINISHING
5. Check which required artifacts are **missing** for the current level:
   - L2: prd.md, implement.md
   - L3: prd.md, research/grill-me.md, implement.md, implement.jsonl, check.jsonl
   - L4: prd.md, research/grill-me.md, design.md, implement.md, implement.jsonl, check.jsonl
   - L5: prd.md, research/grill-me.md, design.md, implement.md, implement.jsonl, check.jsonl, review/merge-review.md when required
6. Check gate status: read `validation/check-results.md` for check PASS/FAIL, `review/` files for review PASS/FAIL, and `validation/test-results.md` for final Build/Test/Smoke, Ready, and Overall status.
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
  build:   <PASS / FAIL / skipped / missing>
  test:    <PASS / FAIL / skipped / missing>
  smoke:   <PASS / FAIL / skipped / missing>
  ready:   <yes / no / missing>

Scope:
  manifest: <PASS / missing / invalid / n/a>
  declared: <N paths, M globs>

Guardrail overrides:
  ledger:  <none / N entries>
  review:  <PASS / missing / n/a>

Next step: <one actionable sentence>
```

If all artifacts exist and all selected check/review gates pass but `finish.md` is missing, the next step is to wait for explicit Finish consent. Only suggest `/trellis:finish-work` after Finish Approval, spec update decision, commit, required merge-review, and validation are complete.
