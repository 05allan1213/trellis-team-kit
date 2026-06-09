# Workflow Phases

## Phase 1: Plan

Goal: classify the request, get task-creation consent, produce planning artifacts.

### Steps

| Step | Name | Required | Output |
|------|------|----------|--------|
| 1.0 | Create task | required · once | `task.json` |
| 1.1 | Requirement exploration | required · repeatable | `prd.md` |
| 1.2 | Grill PRD | required L3-L5 · optional L2 | `research/grill-me.md` |
| 1.3 | Technical design | conditional · once | `design.md` (L3 optional, L4/L5 required) |
| 1.4 | Execution planning | required · once | minimal `implement.md` for L2; Review Gate Contract for L3-L5 |
| 1.5 | Research | optional · repeatable | `research/*.md` |
| 1.6 | Configure context | required L3-L5 · optional L2 | `implement.jsonl` + `check.jsonl` |
| 1.7 | Implementation approval | required · once | User explicitly approves |
| 1.8 | Activate task | required · once | `task.py start` |

### Gates

- No task creation consent → no `task.py create`
- No implementation consent → no `task.py start`, no source editing
- L4/L5 missing `design.md` → no `task.py start`

---

## Phase 2: Execute

Goal: turn planning artifacts into code that passes quality checks and review gates.

### Steps

| Step | Name | Required | Output |
|------|------|----------|--------|
| 2.0 | Before-dev | required · once | `before-dev.md` + `scope-manifest.json` |
| 2.1 | Implement | required · repeatable | changed files + `agent-results/*.json` when Trellis subagents are used |
| 2.2 | Quality check | required · repeatable | `validation/check-results.md` + checker `agent-results/*.json` when subagent is used |
| 2.3 | Review gates | required · repeatable | `review/*.md` + reviewer `agent-results/*.json` |
| 2.4 | Rollback | on demand | Return to correct state |

### Gates

- No task artifacts read → no source editing
- check FAIL → return to implement
- review gate FAIL → return to implement
- Cannot skip any selected gate

---

## Phase 3: Finish

Goal: ensure quality, capture lessons, record work.

### Steps

| Step | Name | Required | Output |
|------|------|----------|--------|
| 3.0 | Finish consent | required · once | User explicitly enters Finish |
| 3.1 | Finish evidence | required · once | Current `finish.md` template completed: Finish Approval, Task Summary, Observable Outcomes, Changed Files, Acceptance Criteria Coverage, Delivery Sync Check, Guardrail Overrides, Spec Update Decision, Follow-ups, Risks |
| 3.2 | Commit changes | required · once | git commits |
| 3.3 | Merge review | conditional · once | `review/merge-review.md` |
| 3.4 | Validation | required · once | `validation/test-results.md` |
| 3.5 | Finish work | required · once | archive + journal |
| 3.6 | Debug retrospective | on demand | `research/break-loop.md` |

### Gates

- No explicit Finish consent → no `finish.md`, no spec update, no commit, no archive

### Finish-Work Preconditions

1. Implementation complete
2. `trellis-check` PASS
3. Selected review gates PASS
4. Finish Approval recorded
5. Spec Update Decision recorded
6. Observable Outcomes recorded with evidence
7. Delivery Sync Check recorded
8. Guardrail Overrides reviewed when `runtime/guardrail-overrides.jsonl` exists
9. Merge review PASS when required
10. Code committed, PR created, or explicitly no commit needed
11. Build/Test/Smoke recorded in `validation/test-results.md`, `Ready for finish-work?` marked yes, and Overall PASS or skipped-with-valid-reason evidence recorded
