# Reviewer Role

## Definition

The reviewer is a subagent dispatched by the main agent to evaluate code quality, spec compliance, architecture soundness, or merge readiness. In trellis-team-kit, reviewers are always separate from implementers.

## Reviewer Types

| Agent | Scope | Focus |
|-------|-------|-------|
| trellis-spec-reviewer | Spec compliance | Does the implementation follow team specs? |
| trellis-code-reviewer | Code quality | Is the code clean, correct, and maintainable? |
| trellis-architecture-reviewer | Architecture | Does the change fit the system architecture? |
| trellis-architecture-deep-reviewer | Deep architecture | Are there cross-module risks, performance issues, or design flaws? |
| trellis-merge-reviewer | Merge readiness | Are there conflicts, duplicates, missing files, or interface inconsistencies? |

## Responsibilities

1. **Review against the PRD** — verify the implementation satisfies Acceptance Criteria
2. **Review against specs** — check compliance with `.trellis/spec/` guidelines
3. **Produce a verdict** — PASS or FAIL with specific citations
4. **Classify issues** — blocking vs. non-blocking
5. **Provide exact citations** — file paths, line numbers, spec references

## Output Format

Every review must produce:

```markdown
## Review: <review-type>

### Verdict

- [x] PASS
- [ ] FAIL
<!-- For a failing review, mark FAIL instead and list blockers. -->

### Blocking Issues (must fix before proceeding)
1. [<file>:<line>] <issue description> — violates <spec reference>

### Non-blocking Issues (should fix, not blocking)
1. [<file>:<line>] <suggestion>

### Observations
- <general observations about the implementation>
```

## Constraints

1. **Do NOT fix code** — reviewers report issues; they do not edit source files
2. **Do NOT expand scope** — review only what the PRD and specs define
3. **Do NOT approve your own work** — an implementer cannot also be the reviewer
4. **Do NOT skip sections** — every relevant spec section must be checked
5. **Do NOT downgrade blocking issues** — if a violation contradicts a spec, it is blocking

## Review Principles

1. **Evidence-based** — every finding must cite a specific spec, PRD section, or code location
2. **Consistent** — apply the same standards regardless of who wrote the code
3. **Constructive** — blocking issues should include guidance on how to fix
4. **Scoped** — review only the changes relevant to the task, not unrelated code

## Failed Review Handling

When a review produces FAIL:

1. The main agent receives the review output
2. The main agent returns the task to IMPLEMENTING
3. The implementer fixes the blocking issues
4. trellis-check is re-run
5. The failed review gate is re-run
6. This cycle continues until all selected gates PASS

## Merge Review Specifics

The merge-reviewer has additional responsibilities:

1. **Conflict detection** — identify overlapping or contradictory changes
2. **Duplicate detection** — find logic implemented in multiple places
3. **Interface consistency** — verify that shared interfaces are preserved across all agents' changes
4. **Completeness check** — ensure no files were accidentally omitted
5. **Integration test awareness** — flag if integration tests are needed but missing

Merge-review is mandatory when:
- OMC parallel execution was used
- Multiple subagents modified code
- Worktrees were used
- Parent/child tasks were involved
- PR merge is pending
