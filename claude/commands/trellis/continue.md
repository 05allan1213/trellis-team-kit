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
   - `planning` + prd.md but no implement.md → PLANNING_GRILL / PLANNING_DESIGN
   - `planning` + implement.md → WAITING_IMPLEMENTATION_APPROVAL
   - `in_progress` + no before-dev.md → BEFORE_DEV
   - `in_progress` + before-dev.md + no validation/ → IMPLEMENTING
   - `in_progress` + validation/check-results.md but pending/missing review gates → CHECKING / REVIEWING
   - `in_progress` + review/ dir with selected gates not all PASS → REVIEWING
   - `in_progress` + `validate_review_gates.py` PASS but no finish.md → REVIEWING (waiting for explicit Finish consent)
   - `in_progress` + finish.md but no commit evidence → UPDATING_SPEC / COMMITTING
   - `in_progress` + merge-review required and missing/failing → MERGE_REVIEWING
   - `in_progress` + commit evidence but no validation/test-results.md → VALIDATING
   - `in_progress` + finish.md + commit evidence + validation/test-results.md → FINISHING

4. **Find the last failure** — Check for any FAIL verdicts:
   - Read `validation/check-results.md` for check FAIL
   - Run or inspect `validate_review_gates.py <task-dir>` for selected review gate failures, missing reviewer results, and unresolved placeholders
   - Read `validation/test-results.md` for Build/Test/Smoke FAIL, `Ready for finish-work?`: no, or missing Ready
   - If a FAIL exists, summarize: which gate, what the blocking issue was

5. **Check missing artifacts** for the current level:
   - L2: prd.md, implement.md
   - L3: prd.md, research/grill-me.md, implement.md, implement.jsonl, check.jsonl
   - L4: prd.md, research/grill-me.md, design.md, implement.md, implement.jsonl, check.jsonl
   - L5: all of above, plus review/merge-review.md when required

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
   - REVIEWING (waiting for explicit Finish consent) → summarize passed gates and ask the user to explicitly enter Finish
   - UPDATING_SPEC / COMMITTING → complete finish.md evidence, run prepare_finish_workspace.py, present commit plan
   - MERGE_REVIEWING → run trellis-merge-review
   - VALIDATING → fill validation/test-results.md with Build, Test, Smoke, Ready for finish-work?, and Overall
   - FINISHING → trellis-finish-work

**Important**: Do NOT skip steps or assume previous work was completed. Verify each artifact exists before advancing.
