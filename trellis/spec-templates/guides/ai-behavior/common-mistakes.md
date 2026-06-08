# Common Mistakes

> Purpose: prevent repeated Trellis workflow regressions before they reach
> implementation, check, review, or finish.

Use this guide whenever you run `trellis-before-dev`, `trellis-check`, or
`trellis-code-review`. It is a workflow behavior guide, not a coding style
guide.

---

## Routing Mistakes

- Treating `L3+` as a real route. Use explicit L3, L4, or L5.
- Starting implementation before the routing level is confirmed.
- Treating L4 as ordinary L3 work. L4 requires design, stricter review gates,
  and subagent + worktree execution by default.
- Treating L5 as automatic OMC. L5 defaults to Trellis-native parallel +
  worktree. OMC is an advanced optional path only after explicit OMC approval.

## Scope Mistakes

- Writing code before `before-dev.md` and `scope-manifest.json` exist.
- Leaving both `declared_paths` and `declared_globs` empty.
- Expanding into high-risk files without the PRD or implement plan allowing
  that scope.
- Editing outside the declared scope and failing to record the reason.

## Override Ledger Mistakes

- Using a soft guardrail override without writing
  `runtime/guardrail-overrides.jsonl`.
- Recording an override but never reviewing it in `finish.md`.
- Treating override approval as permission to skip scope or review gates.

## Agent Result Mistakes

- Dispatching Trellis subagents without requiring an `agent-results/*.json`
  handoff.
- Omitting `status`, `changed_files`, `validation`, or `blocking_issues`.
- Reporting PASS while validation failed or blocking issues remain.
- Letting two agents edit the same file without merge-review detecting and
  resolving the conflict.

## Replay Lab Mistakes

- Adding or changing workflow behavior without a Replay Lab fixture.
- Only testing the happy path. Replay should cover routing, guardrails,
  finish-blocking behavior, and orchestration cases.
- Forgetting the L5/OMC case where a prompt routes to L5 but does not start OMC
  without explicit OMC approval.

## Doctor Workflow Mistakes

- The doctor workflow is not optional when task state or review evidence looks
  inconsistent.
- Treating `trellis_doctor.py workflow` as a final-only command. Run the doctor
  workflow when task state, artifacts, approval records, or review gates look
  inconsistent.
- Ignoring `To fix` guidance. Doctor output should identify the next concrete
  repair step.
- Finishing with phase mismatch, missing `scope-manifest.json`, missing
  explicit OMC approval, or missing merge-review evidence.

## OMC And Parallel Execution Mistakes

- Describing OMC as the default multi-agent path. Trellis-native parallel is
  the default for L5.
- Starting `ulw/ultrawork` before PRD/AC are confirmed and the user explicitly
  approves OMC.
- Using OMC without merge-review.
- Blocking the task because OMC is unavailable. Fall back to the Trellis-native
  path and report the limitation.

## Before-Dev Translation

When this guide applies, translate the relevant mistake into a concrete
`before-dev.md` constraint or `Must NOT` item. Examples:

- Must NOT start OMC without explicit OMC approval.
- Must NOT edit outside `scope-manifest.json` without recording an override.
- Must preserve `agent-results/*.json` for every Trellis subagent.

## Check And Review Translation

During check or code review, a repeated documented mistake is a blocking FAIL
when it affects the current change. Record it as:

```markdown
Common mistakes regression: PASS/FAIL - [evidence]
```

---

**Core Principle**: repeated workflow mistakes belong in specs, tests, replay
fixtures, or doctor checks; do not rely on memory or final-chat reminders.
