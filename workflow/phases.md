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
| 2.0 | Before-dev | required · once | Constraint checklist |
| 2.1 | Implement | required · repeatable | Changed files |
| 2.2 | Quality check | required · repeatable | PASS/FAIL |
| 2.3 | Review gates | required · repeatable | Each review PASS/FAIL |
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
| 3.1 | Finish evidence | required · once | Spec Update Decision + Observable Outcomes in `finish.md` |
| 3.2 | Commit changes | required · once | git commits |
| 3.3 | Merge review | conditional · once | `review/merge-review.md` |
| 3.4 | Validation | required · once | `validation/test-results.md` |
| 3.5 | Finish work | required · once | archive + journal |
| 3.6 | Debug retrospective | on demand | `research/break-loop.md` |

### Finish-Work Preconditions

1. Implementation complete
2. `trellis-check` PASS
3. Selected review gates PASS
4. Spec update decision recorded
5. Observable outcomes recorded with evidence
6. Code committed or explicitly no commit needed
7. Build/test PASS or explicitly recorded as not executable
