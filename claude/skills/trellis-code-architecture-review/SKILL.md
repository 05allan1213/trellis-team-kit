---
name: trellis-code-architecture-review
description: "Review dependency direction, module boundaries, abstraction quality, duplicated concepts, layering violations, shared utility misuse, API contract clarity, and future extensibility. Outputs to review/architecture-review.md with PASS/FAIL. Required for L4/L5 tasks."
---

# Trellis Code Architecture Review

## Preconditions

- `trellis-check` has passed.
- Architecture review is selected in the Review Gate Contract (required for L4/L5).

## Core Rules

Architecture review focuses on structural quality — how the code is organized and how parts relate to each other. It does not check line-level code quality (that is `trellis-code-review`) or spec compliance (that is `trellis-spec-review`).

For L4/L5 tasks, this review is mandatory. The higher the task level, the more rigorous the review must be.

## Workflow

1. **Read changed files** — `git diff HEAD` for the full diff.
2. **Read task artifacts** — `prd.md`, `design.md` (required for L4/L5), `implement.md`.
3. **Review each dimension** below.
4. **Write findings** to `review/architecture-review.md`.

### Dimensions

#### Dependency Direction

- Do dependencies point inward (toward core/domain, not toward infrastructure)?
- Are there any circular dependencies?
- Does the code import from the correct layer (not skipping layers)?
- Are infrastructure details (DB, HTTP, file system) isolated from domain logic?

#### Module Boundaries

- Does each module have a clear responsibility?
- Are module interfaces narrow (minimal surface area)?
- Can a module be understood without reading another module's implementation?
- Are there modules that do too many unrelated things?

#### Abstraction Quality

- Are abstractions at the right level (not too high, not too low)?
- Does each abstraction earn its complexity (does it hide enough detail)?
- Are there "shallow" abstractions that just forward calls without adding value?
- Are there leaky abstractions where callers must know internals?

#### Duplicated Concepts

- Is the same concept defined in multiple places?
- Are there different names for the same thing?
- Are there similar but slightly different versions of the same utility?
- Should shared concepts be extracted to a common module?

#### Layering Violations

- Does the code respect the project's defined layers?
- Are there cross-layer calls that skip intermediate layers?
- Is domain logic leaking into infrastructure or presentation code?
- Are there UI concerns in service/controller code?

#### Shared Utility Misuse

- Are shared utilities used for their intended purpose?
- Are there utilities that have grown to serve too many unrelated callers?
- Are there utilities that should be domain-specific but are in shared?
- Is there over-generalization (making a utility too generic for one use case)?

#### API Contract Clarity

- Are API contracts explicit (typed, documented)?
- Are request/response shapes clear and stable?
- Are error contracts consistent?
- Are breaking changes handled (versioning, backward compatibility)?

#### Future Extensibility

- Can new features be added without modifying existing code (open/closed)?
- Are extension points documented?
- Are there hard-coded assumptions that will break later?
- Is the design flexible enough for foreseeable changes?

## Output Format

### review/architecture-review.md

```markdown
# Architecture Review: [Task Title]

## Files Reviewed
- [file path]
- [file path]

## Dependency Direction
- [finding]
- Result: PASS or FAIL — [evidence]

## Module Boundaries
- [finding]
- Result: PASS or FAIL — [evidence]

## Abstraction Quality
- [finding]
- Result: PASS or FAIL — [evidence]

## Duplicated Concepts
- [finding]
- Result: PASS or FAIL — [evidence]

## Layering Violations
- [finding]
- Result: PASS or FAIL — [evidence]

## Shared Utility Misuse
- [finding]
- Result: PASS or FAIL — [evidence]

## API Contract Clarity
- [finding]
- Result: PASS or FAIL — [evidence]

## Future Extensibility
- [finding]
- Result: PASS or FAIL — [evidence]

## Blocking Issues
1. [issue]: [why it blocks]
(or "none")

## Non-Blocking Issues
1. [suggestion]: [why it would improve architecture]
(or "none")

## Verdict
- [x] PASS — no architecture blocking issues
- [ ] FAIL — must return to implement:
  1. [blocking issue summary]
<!-- For a failing review, mark FAIL instead and list blockers. -->
```

## Quality Bar

- All dimensions are reviewed (not just the ones that are easy to check).
- `design.md` is used as the baseline for L4/L5 (implementation should match design).
- Blocking issues cite specific files and explain the architectural impact.
- The review does not confuse code quality with architecture quality.
- FAIL verdict is honest — structural problems that will compound over time are blocking.
