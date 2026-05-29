---
name: trellis-merge-review
description: "Review integration after worktree, multi-subagent, OMC parallel, PR merge, conflict resolution, or parent/child integration. Checks conflict resolution logic, duplicate implementations, missing files, and interface inconsistencies between agents. Outputs to review/merge-review.md with PASS/FAIL."
---

# Trellis Merge Review

## Preconditions

One or more trigger conditions are met:
- Worktree used (changes need to merge back to main branch)
- Multi-subagent execution (multiple agents produced code independently)
- OMC parallel execution (parallel agents worked on different parts)
- PR merge pending
- Conflict resolution was performed
- Parent/child task integration (child outputs need to integrate into parent)

## Core Rules

Merge review is about integration quality — whether the combined output of multiple sources is coherent and complete. It is not about individual code quality (that is `trellis-code-review`).

For L4/L5 tasks, merge review is required when the task used worktree, OMC, or parent/child structure.

## Workflow

1. **Identify the merge sources** — which worktrees, agents, or child tasks contributed code.
2. **Read all changed files** — `git diff` from the merge base.
3. **Read task artifacts** — `prd.md`, `design.md`, `implement.md`.
4. **Check each dimension** below.
5. **Write findings** to `review/merge-review.md`.

### Dimensions

#### Conflict Resolution Logic

- Were there merge conflicts? How were they resolved?
- Did conflict resolution preserve the intent of both sides?
- Did conflict resolution introduce logical errors (e.g., kept the wrong branch's code)?
- Are there residual conflict markers (`<<<<<<`, `======`, `>>>>>>`)?

#### Duplicate Implementations

- Did multiple agents implement the same functionality independently?
- Are there two versions of the same utility or type?
- Are there overlapping API endpoints or routes?
- Should duplicate implementations be consolidated?

#### Missing Files

- Did an agent's output fail to get included in the merge?
- Are there files that were created in a worktree but not merged?
- Are there test files missing from the final result?
- Are there config or migration files that were supposed to be included?

#### Interface Inconsistencies

- Do different agents use the same interface differently?
- Are shared types consistent across agent outputs?
- Are API contracts the same between frontend and backend changes?
- Are error handling patterns consistent across merged code?

#### Integration Completeness

- Does the merged result satisfy all acceptance criteria from `prd.md`?
- Are all child task deliverables integrated into the parent?
- Are there orphaned pieces of code that no longer connect to anything?
- Are there TODO items left from individual agents that need resolution?

## Output Format

### review/merge-review.md

```markdown
# Merge Review: [Task Title]

## Merge Sources
- [source]: [what it contributed]
- [source]: [what it contributed]

## Conflict Resolution Logic
- [conflict description]: [how resolved] — [correct?]
- (or "no conflicts")

## Duplicate Implementations
- [duplicate]: [source A vs source B] — [recommended consolidation]
- (or "none")

## Missing Files
- [expected file]: [which source should have produced it] — [status]
- (or "none")

## Interface Inconsistencies
- [interface]: [how sources differ] — [which is correct per design.md]
- (or "none")

## Integration Completeness
- [AC from prd.md]: [satisfied by merged result?]
- [AC from prd.md]: [satisfied by merged result?]

## Blocking Issues
1. [issue]: [why it blocks merge]
(or "none")

## Non-Blocking Issues
1. [suggestion]: [improvement rationale]
(or "none")

## Verdict
- PASS — merge is coherent and complete
- FAIL — must resolve blocking issues:
  1. [blocking issue summary]
```

## Quality Bar

- All merge sources are identified and their contributions mapped.
- Conflict resolution is checked for correctness, not just absence of markers.
- Duplicate implementations are flagged for consolidation.
- Missing files are identified by comparing expected outputs against actual.
- Integration completeness is verified against `prd.md` acceptance criteria.
- FAIL verdict is honest — incomplete integration will cause problems later.
