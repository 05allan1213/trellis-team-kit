---
name: trellis-dev-strategy
description: "Decide execution mode, branch strategy, TDD approach, review gates, and architecture guidance for the task. Outputs Development Strategy and Review Gate Contract to implement.md. Use during Phase 1.4 after PRD and design are complete."
---

# Trellis Dev Strategy

## Preconditions

- `prd.md` is complete.
- `research/grill-me.md` exists for L3-L5 tasks; for L2 it is optional unless requirements are unclear or risk increased.
- `design.md` exists for L4/L5 tasks; for L3 it is optional when the change has architectural impact.

## Core Rules

The development strategy must match the task's complexity level. L4/L5 tasks MUST NOT default to main-session execution, and L5/orchestrated tasks MUST NOT select main-session execution.

## Workflow

1. **Read task artifacts** — `prd.md`, `design.md` (if present).
2. **Classify the task** — confirm L0-L5 level.
3. **Decide each dimension** below.
4. **Write to `implement.md`** with Development Strategy and Review Gate Contract.

### Decisions

#### Execution Mode

| Mode | When to Use | Notes |
|------|-------------|-------|
| Main session | L0-L1 only, or explicit user override for non-L5 work | Must not be default for L2+; invalid for L5/orchestrated |
| Single Trellis subagent | L2-L3, or L4 with tightly coupled work | Standard Trellis path |
| Trellis subagents | L3-L4 when checker/reviewer separation is useful | Native Trellis path |
| Trellis-native parallel + worktree | L5, parent/child, multi-agent, large refactor, or independent workstreams | Default orchestrated path |
| OMC ulw/ultrawork + worktree + parent/child | L5 advanced path, confirmed PRD, clear AC, independent workstreams, native Trellis is not enough | Requires explicit user confirmation |

L4/L5 MUST NOT default to main-session. L5 defaults to Trellis-native parallel + worktree when parallelism is justified. OMC is optional and advanced; never select it unless the user explicitly approved OMC. If the user requests main-session for L4, warn about risks and record the decision. If the user requests main-session for L5, re-scope to a narrower level or keep the orchestrated path; do not write L5 main-session into `implement.md`.

#### Branch Strategy

| Strategy | When to Use |
|----------|-------------|
| Current branch | L0-L2, small changes, no conflict risk |
| Dedicated worktree | L3-L5 with cross-package changes, parallel work, or PR-type tasks |

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

Required for: L5, worktree, parallel or workstream multi-subagent execution, OMC parallel, PR merge, conflict resolution, parent/child task.

Ordinary serial Trellis implementer/checker/reviewer subagents require
`agent-results/*.json`, but they do not by themselves require merge-review.

## Output Format

### implement.md

```markdown
# Implementation Plan: [Task Title]

## Development Strategy

- **Mode**: [main-session / single Trellis subagent / Trellis subagents / Trellis-native parallel + worktree / OMC ulw/ultrawork + worktree + parent/child]
- **Branch strategy**: [current / dedicated worktree at .trellis/worktrees/<slug>/]
- **TDD**: [yes / no]
- **Parent/child**: [yes — describe split / no]
- **Architecture guidance**: [yes — load trellis-improve-codebase-architecture guidance / no]
- **Merge review needed**: [yes / no]

## Execution Mode Decision

Recommended mode:
- [ ] main session
- [ ] single Trellis subagent
- [ ] Trellis subagents
- [ ] Trellis-native parallel + worktree
- [ ] OMC ulw/ultrawork + worktree + parent/child

Reason:
- [why this mode fits the task level and risk]

Why not heavier:
- [why not OMC / parent-child / parallel if not selected]

OMC approval:
- [ ] not applicable
- [ ] user explicitly approved OMC
- user message:
- timestamp:

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

- Execution mode matches task complexity (L4/L5 never defaults to main-session, and L5 never selects main-session).
- Review Gate Contract is complete with rationale.
- All dimensions are decided (no "TBD" on strategy items).
- Validation commands are concrete, runnable, and include at least one way to prove observable outcomes.
- `implement.md` is ready for Phase 1.6 (context configuration) and Phase 1.7 (implementation approval).
