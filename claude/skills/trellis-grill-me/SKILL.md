---
name: trellis-grill-me
description: "Challenge the PRD for testability, scope clarity, edge cases, and risks. Checks AC testability, out-of-scope clarity, edge cases, auth/security/performance, migration/rollback, and scope creep risk. Use after brainstorm completes, before design or implementation planning."
---

# Trellis Grill Me

## Preconditions

- `prd.md` exists with basic acceptance criteria.
- Brainstorm (Phase 1.1) is complete.

## Core Rules

Grill the PRD rigorously. The purpose is to find gaps before they become bugs. A solid PRD prevents wasted implementation cycles.

If the PRD is already solid after review, explicitly write "no blocking questions" — do not invent concerns.

## Workflow

1. **Read `prd.md`** in full.
2. **Check each dimension** below. For each, determine if the PRD adequately addresses it.
3. **Write findings** to `research/grill-me.md`.
4. **Update `prd.md`** — add findings to Risks, Open Questions, or Out of Scope sections as appropriate.

### Dimensions to Check

#### Acceptance Criteria Testability

- Can each AC be verified with a concrete test or observation?
- Are there vague words ("fast", "good", "proper", "correct") that need measurable definitions?
- Does each AC have a clear pass/fail boundary?

#### Out-of-Scope Clarity

- Is it explicit what this task does NOT cover?
- Could an implementer reasonably interpret ambiguous items as in-scope?
- Are adjacent features that look similar explicitly listed as out-of-scope?

#### Edge Cases

- What happens with empty input? Null? Zero? Negative?
- What happens with concurrent access or race conditions?
- What happens when external dependencies are unavailable?
- What happens with data at boundary values (max length, min length)?

#### Auth/Security/Performance

- Does the change touch authentication or authorization?
- Are there data exposure or injection risks?
- Are there performance implications (N+1 queries, large payloads, unbounded lists)?
- Are there rate-limiting or resource-exhaustion concerns?

#### Migration/Rollback

- Does the change require data migration?
- Can the change be rolled back without data loss?
- Are there backward compatibility concerns?
- Does the change affect existing API contracts?

#### Scope Creep Risk

- Are there "nice to have" items mixed with "must have"?
- Could one requirement silently expand into three during implementation?
- Are there implicit dependencies on other unfinished work?

## Output Format

### research/grill-me.md

```markdown
# Grill Me: [Task Title]

## AC Testability
- [AC #]: [issue or "testable"]
- Verdict: PASS / NEEDS REVISION

## Out-of-Scope Clarity
- [finding]
- Verdict: PASS / NEEDS REVISION

## Edge Cases
- [finding]
- Verdict: PASS / NEEDS REVISION

## Auth/Security/Performance
- [finding]
- Verdict: PASS / NEEDS REVISION

## Migration/Rollback
- [finding]
- Verdict: PASS / NEEDS REVISION

## Scope Creep Risk
- [finding]
- Verdict: PASS / NEEDS REVISION

## Overall Verdict
- PASS: no blocking questions
- NEEDS REVISION: [list blocking issues]

## PRD Updates Made
- [section updated]: [what was added/changed]
```

## Quality Bar

- Every dimension has been checked, not just the easy ones.
- If the PRD is solid, explicitly state "no blocking questions" — honesty matters.
- If issues are found, they are specific and actionable (not "needs improvement").
- `prd.md` is updated with all findings before moving to the next phase.
- Grill-me is required once per task (Phase 1.2). Do not skip it.
