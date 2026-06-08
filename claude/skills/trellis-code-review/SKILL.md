---
name: trellis-code-review
description: "Review code for correctness, readability, maintainability, error handling, performance, tests, security, and unnecessary complexity. Outputs to review/code-review.md with PASS/FAIL, separating blocking from non-blocking issues. Use as a review gate when selected in the Review Gate Contract."
---

# Trellis Code Review

## Preconditions

- `trellis-check` has passed.
- Code review is selected in the Review Gate Contract.

## Core Rules

Code review focuses on the implementation quality of the changed code. It does not check spec compliance (that is `trellis-spec-review`) or architecture (that is `trellis-code-architecture-review`).

Separate blocking issues from non-blocking issues. Blocking issues must be fixed before the review passes. Non-blocking issues are suggestions that can be addressed later.

## Workflow

1. **Read changed files** — `git diff HEAD` for the full diff.
2. **Read task artifacts** — `prd.md` for scope, `design.md` for contracts (if present).
3. **Read common mistakes** — if present, read `.trellis/spec/guides/ai-behavior/common-mistakes.md` and check whether the diff repeats a documented mistake.
4. **Review each dimension** below.
5. **Write findings** to `review/code-review.md`.

### Dimensions

#### Correctness

- Does the code do what the PRD says?
- Are there off-by-one errors, wrong conditions, or logic inversions?
- Are there race conditions or concurrency issues?
- Does error handling cover all documented failure modes?

#### Readability

- Can a new team member understand this code without asking the author?
- Are names descriptive and consistent with the codebase?
- Is the control flow clear (no deeply nested conditions)?
- Are complex sections commented with "why", not "what"?

#### Maintainability

- Can this code be modified without touching unrelated code?
- Are functions small and focused?
- Is there unnecessary coupling between components?
- Are magic numbers/strings extracted to named constants?

#### Error Handling

- Are errors caught and handled (not swallowed)?
- Are error messages actionable (tell the user what to do)?
- Are edge cases handled (null, empty, zero, boundary values)?
- Does the code fail fast when preconditions are not met?

#### Performance

- Are there N+1 queries or unbounded loops?
- Are there unnecessary allocations or copies?
- Are expensive operations cached when appropriate?
- Are there obvious performance bottlenecks?

#### Tests

- Do tests cover the happy path?
- Do tests cover error paths?
- Do tests cover edge cases?
- Are tests independent and deterministic?
- Do test names describe the expected behavior?

#### Security

- Is user input validated and sanitized?
- Are there injection risks (SQL, XSS, command)?
- Are sensitive data handled properly (no logging, no exposure)?
- Are authentication and authorization checks in place?

#### Unnecessary Complexity

- Is there code that could be simpler?
- Are there abstractions that add indirection without value?
- Are there features implemented "just in case" (YAGNI violations)?
- Is there dead code or unreachable branches?

#### Common Mistakes Regression

- Does the diff repeat a documented common mistake from `.trellis/spec/guides/ai-behavior/common-mistakes.md`?
- Does the task preserve routing, scope-manifest, override ledger, agent-results, replay, doctor, OMC approval, and merge-review requirements when they apply?
- If a repeated documented mistake affects the current change, classify it as blocking.

## Output Format

### review/code-review.md

```markdown
# Code Review: [Task Title]

## Files Reviewed
- [file path]
- [file path]

## Blocking Issues
1. [file:line]: [issue description] — [why it's blocking]
2. [file:line]: [issue description] — [why it's blocking]
(or "none")

## Non-Blocking Issues
1. [file:line]: [suggestion] — [why it would be better]
2. [file:line]: [suggestion] — [why it would be better]
(or "none")

## Positive Observations
- [what was done well]

## Common Mistakes Regression
- PASS/FAIL — [evidence]

## Verdict
- PASS — no blocking issues
- FAIL — blocking issues must be fixed:
  1. [blocking issue summary]
  2. [blocking issue summary]
```

## Quality Bar

- Each dimension has been reviewed, not just the easy ones.
- Blocking issues are specific (file:line reference, not vague).
- Non-blocking issues are clearly separated from blocking ones.
- Positive observations are included (reviews are not just about finding problems).
- Common mistakes regression is checked and reported explicitly.
- FAIL verdict lists specific blocking issues.
- The review is honest — do not upgrade non-blocking to blocking, or downgrade blocking to non-blocking.
