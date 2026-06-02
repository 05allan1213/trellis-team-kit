---
name: trellis-dev-strategy
description: "Decide execution mode, branch strategy, TDD approach, review gates, and architecture guidance for the task. Outputs Development Strategy and Review Gate Contract to implement.md. Use during Phase 1.4 after PRD and design are complete."
---

# Trellis Dev Strategy

## Preconditions

- `prd.md` is complete and grilled (Phase 1.1 + 1.2 done).
- `design.md` exists for L4/L5 tasks (Phase 1.3 done for complex tasks).

## Core Rules

The development strategy must match the task's complexity level. L4/L5 tasks MUST NOT default to main-session execution.

## Workflow

1. **Read task artifacts** — `prd.md`, `design.md` (if present).
2. **Classify the task** — confirm L0-L5 level.
3. **Decide each dimension** below.
4. **Write to `implement.md`** with Development Strategy and Review Gate Contract.

### Decisions

#### Execution Mode

| Mode | When to Use | Notes |
|------|-------------|-------|
| Main session | L0-L1 only, or explicit user override | Must not be default for L2+ |
| Subagent | L2-L3, or L4 with tightly coupled work | Standard Trellis path |
| Subagent + worktree | L4, cross-package changes | Isolated branch |
| OMC parallel | L5, confirmed PRD, clear AC, independent workstreams | Requires explicit user confirmation |

L4/L5 MUST NOT default to main-session. If the user requests main-session for L4/L5, warn about risks and record the decision.

#### Branch Strategy

| Strategy | When to Use |
|----------|-------------|
| Current branch | L0-L2, small changes, no conflict risk |
| Dedicated worktree | L3+ with cross-package changes, parallel work, or PR-type tasks |

Worktree policy: required for multiple subagents in parallel, OMC execution, cross-package changes, large refactors, PR-type tasks, and parent/child tasks.

#### TDD

| Choice | When to Use |
|--------|-------------|
| Yes | New API endpoints, auth/security logic, data transformation, complex business rules |
| No | UI tweaks, config changes, simple CRUD, documentation |

#### Parent/Child Task

| Choice | When to Use |
|--------|-------------|
| Yes | Multiple independently verifiable deliverables in one request |
| No | Single deliverable or tightly coupled work |

Parent owns: source requirements, child mapping, cross-child AC, final integration review, merge-review.
Child owns: independent implementation, independent check, local AC, archive.

#### Architecture Guidance

| Choice | When to Use |
|--------|-------------|
| Yes | Crosses 3+ layers, new module, API/schema/persistence change, shared type/util/config change, new abstraction |
| No | Single-layer, well-understood pattern |

If yes, load `trellis-improve-codebase-architecture guidance` before implementation.

#### Review Gates

Select gates based on the Review Gate Contract defaults:

| Level | check | spec-review | code-review | architecture-review | deep-review | merge-review |
|-------|-------|-------------|-------------|-------------------|-------------|-------------|
| L2 | required | | | | | |
| L3 | required | | required | | | |
| L4 | required | required | required | required | | |
| L5 | required | required | required | required | required | required |

Customize based on task specifics, but do not remove required gates.

#### Merge Review

Required for: worktree, multi-subagent, OMC parallel, PR merge, conflict resolution, parent/child task.

## Output Format

### implement.md

```markdown
# Implementation Plan: [Task Title]

## Development Strategy

- **Execution mode**: [main-session / subagent / subagent+worktree / OMC]
- **Branch strategy**: [current / dedicated worktree at .trellis/worktrees/<slug>/]
- **TDD**: [yes / no]
- **Parent/child**: [yes — describe split / no]
- **Architecture guidance**: [yes — load trellis-improve-codebase-architecture guidance / no]
- **Merge review needed**: [yes / no]

## Review Gate Contract

Contract version: team-kit

Required gates:
- [x] trellis-check

Selected gates:
- [ ] trellis-spec-review
- [ ] trellis-code-review
- [ ] trellis-code-architecture-review
- [ ] trellis-improve-codebase-architecture deep-review
- [ ] trellis-merge-review

Selection rationale: [why these gates]

Failure rule:
- Failed gate returns to trellis-implement.
- Do not skip a failed gate.
- Do not mark done until all selected gates pass.

## Implementation Steps

1. [step description]
2. [step description]

## Validation Commands

- [command to verify each step]
- [manual or scripted check that proves a user-visible or operator-visible outcome]

## Risky Files / Rollback Points

- [file]: [why risky, rollback strategy]
```

## Quality Bar

- Execution mode matches task complexity (L4/L5 never defaults to main-session).
- Review Gate Contract is complete with rationale.
- All dimensions are decided (no "TBD" on strategy items).
- Validation commands are concrete, runnable, and include at least one way to prove observable outcomes.
- `implement.md` is ready for Phase 1.6 (context configuration) and Phase 1.7 (implementation approval).
