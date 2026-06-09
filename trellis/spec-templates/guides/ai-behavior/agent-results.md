# Agent Results

> Purpose: make every Trellis subagent handoff machine-readable before the main
> session aggregates, reviews, or finishes work.

Use this guide when dispatching, checking, reviewing, merging, or diagnosing
Trellis subagent work.

---

## Required Handoff

Every Trellis subagent must write one JSON file before its final response:

```text
{TASK_DIR}/agent-results/<agent-name>-<timestamp>.json
```

This applies to implementers, checkers, researchers, reviewers,
merge-reviewers, and spec-updaters. Natural language output is not enough.

Required JSON fields:

- `version`: exactly `1`.
- `agent`: the canonical agent name, such as `trellis-implementer`.
- `status`: `PASS`, `FAIL`, `REDESIGN-REQUIRED`, or `BLOCKED`.
- `changed_files`: a list of objects with `path` and `summary`.
- `validation`: a list of objects with `command` and `status`.
- `blocking_issues`: unresolved blockers; empty on `PASS`.

Recommended fields:

- `workstream`: required for implementer/checker results when workstreams are
  declared in `scope-manifest.json`.
- `non_blocking_issues`: follow-up findings that do not block.
- `risks`: residual uncertainty.
- `scope_expansion`: changed paths or behavior outside the expected task scope.
- `execution_mode`: a useful source label such as `single-agent`,
  `Trellis subagents`, `trellis-native parallel + worktree`,
  `merge-review`, or `OMC ulw/ultrawork + worktree + parent/child`.
  Validators use this field to detect OMC approval requirements; do not treat
  the examples here as a closed enum.
- `git.committed`: normally `false`; Trellis subagents must not commit.

---

## Scope Rules

Agent result changed files must stay inside the task contract:

- Source and test files must match `scope-manifest.json` declared paths or
  globs.
- Task-local evidence may use `research/`, `review/`, `runtime/`,
  `validation/`, or `agent-results/`.
- `trellis-spec-updater` may report `.trellis/spec/` paths because its role is
  to update installed team specs during the spec update phase.
- Two agents reporting the same changed file is a merge-review risk.

---

## Validation Rules

Report every command or inspection that affected the result. A validation item
with `status: FAIL` blocks final PASS. A result with `blocking_issues` also
blocks final PASS.

If the agent is blocked, it still writes JSON with `status: BLOCKED` and records
the blocker in `blocking_issues`.

If OMC appears in `execution_mode`, including the canonical
`OMC ulw/ultrawork + worktree + parent/child` value, `implement.md` must include
explicit OMC approval with an auditable user message and timestamp.

---

## Main Session Responsibilities

The main session must aggregate `agent-results/*.json` before finish. It must
not rely on memory, chat summaries, or subagent self-approval.

Merge review must inspect:

- all agent result JSON files
- duplicate changed files
- undeclared changed files
- failed validation
- unresolved blocking issues
- override ledger entries
- OMC approval evidence when OMC was used

---

**Core Principle**: every Trellis subagent leaves structured evidence that the
main session can validate independently.
