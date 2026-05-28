# code-review.md

## Purpose

Review the current task diff for correctness, scope, safety, and readiness.

Do not turn review into unrelated refactoring.

## When to Load

Load when:

* a task produced a meaningful code diff
* the task enters Check or Finish
* the user requests review
* API, auth, data, security, payment, config, or shared logic changed
* multiple agents contributed

Skip for formatting-only or documentation-only changes unless review is requested.

## Review Rules

Review the diff against:

* PRD and acceptance criteria
* changed files
* verification results
* known risks

Check for:

* missing or incorrect behavior
* unrelated changes
* broken compatibility
* missing validation or error handling
* security or data risks
* missing or misleading verification
* inconsistent multi-agent integration

Use `testing.md` for verification rules.

Use `debugging.md` for bug-fix validation.

## Severity

### P0 — Blocker

Must fix before completion.

Examples:

* requirement not met
* broken build, typecheck, or critical test
* security, auth, privacy, payment, or data-loss risk
* unsafe migration or production-impacting config
* broken runtime path
* false or missing critical verification

### P1 — Major

Should fix before merge.

Examples:

* likely edge-case failure
* incomplete validation or error handling
* fragile integration
* missing regression coverage
* important loading/error/empty state missing
* meaningful performance risk

### P2 — Minor

Non-blocking improvement.

Examples:

* naming or readability issue
* minor duplication
* documentation or test improvement
* small consistency issue

Do not escalate style preferences into P0/P1.

## Human Review Required

Require human review for:

* auth or permissions
* payments or financial data
* production migrations or destructive operations
* security-sensitive behavior
* public API contracts
* legal/privacy/compliance behavior
* core architecture or cross-service contracts

## Review Output

```text
Review Result: Pass / Pass with Notes / Changes Required

P0 Blockers:
- None

P1 Major Issues:
- None

P2 Minor Issues:
- None

Verification Notes:
- ...

Human Review Needed:
- Yes/No, with reason

Summary:
- ...
```

## Pass Criteria

A diff passes when:

* no P0 issues remain
* P1 issues are fixed or accepted
* acceptance criteria are met
* verification is appropriate and honest
* unrelated changes are justified or removed
* remaining risks are visible

## Never

Never:

* approve without inspecting the diff
* hide failing checks
* treat missing verification as passed
* ignore unrelated changes
* downgrade security or data risks without evidence
* mark a task done with unresolved P0 issues
