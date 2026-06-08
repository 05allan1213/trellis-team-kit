Resume working on the active Trellis task with full context recovery. Detect the current task, summarize where you left off, what remains, the last failure (if any), and the recommended next step.

**Steps:**

1. **Find the active task**:
   ```bash
   python3 .trellis/scripts/task.py current --source
   ```
   If no active task, list available tasks under `.trellis/tasks/` and ask the user which one to continue.

2. **Load task context** — Read these files from the task directory:
   - `task.json` — id, status, level, title
   - `prd.md` — requirements and acceptance criteria
   - `design.md` — technical design (if exists)
   - `implement.md` — execution plan with Review Gate Contract (if exists)
   - `before-dev.md` — implementation constraints (if exists)
   - `scope-manifest.json` — machine-readable scope contract (if exists)
   - `runtime/guardrail-overrides.jsonl` — guardrail override audit ledger (if exists)
   - `finish.md` — spec update decision (if exists)

3. **Determine the exact sub-phase** by checking artifact presence:
   - `planning` + no prd.md → PLANNING_PRD
   - `planning` + prd.md but no implement.md → PLANNING_GRILL/DESIGN
   - `planning` + implement.md → WAITING_IMPLEMENTATION_APPROVAL
   - `in_progress` + no before-dev.md → BEFORE_DEV
   - `in_progress` + before-dev.md + no validation/ → IMPLEMENTING
   - `in_progress` + validation/check-results.md → CHECKING
   - `in_progress` + review/ dir with files → REVIEWING
   - `in_progress` + finish.md → FINISHING

4. **Find the last failure** — Check for any FAIL verdicts:
   - Read `validation/check-results.md` for check FAIL
   - Read `review/*.md` files for any review FAIL
   - Read `validation/test-results.md` for build/test FAIL
   - If a FAIL exists, summarize: which gate, what the blocking issue was

5. **Check missing artifacts** for the current level:
   - L2: prd.md
   - L3: prd.md, implement.md
   - L4: prd.md, design.md, implement.md
   - L5: all of above

6. **Check scope/override audit**:
   - L2+ with `before-dev.md` must have valid `scope-manifest.json`.
   - If `runtime/guardrail-overrides.jsonl` exists, summarize the entry count and whether `finish.md` has a completed `Guardrail Overrides` review.

7. **Output a resume summary** in this format:

```
📋 Resuming Task: <id> — <title>
════════════════════════════════════════
Level: L<level>
Phase: <sub-phase>

Last activity:
  <What was being worked on — e.g., "Implementing PRD requirements" or "Review gate code-review returned FAIL">

Last failure (if any):
  <Gate name>: <blocking issue summary>
  → Next: <what to do about it>

Missing artifacts:
  - <file> (required for L<level>)

Scope manifest:
  <present/missing/invalid/n/a> — <declared paths/globs summary>

Guardrail overrides:
  <none / N entries> — <finish review present/missing>

Next step: <one clear actionable sentence>
```

8. **Resume work** — Load the appropriate skill or dispatch the appropriate sub-agent based on the sub-phase:
   - PLANNING_PRD → trellis-brainstorm
   - PLANNING_GRILL → trellis-grill-me
   - PLANNING_DESIGN → write design.md
   - WAITING_IMPLEMENTATION_APPROVAL → present artifacts and ask for approval
   - BEFORE_DEV → trellis-before-dev
   - IMPLEMENTING → trellis-implement
   - CHECKING → trellis-check
   - REVIEWING → run pending review gates
   - FINISHING → trellis-finish-work

**Important**: Do NOT skip steps or assume previous work was completed. Verify each artifact exists before advancing.
