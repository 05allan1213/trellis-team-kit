---
name: trellis-brainstorm
description: "Evidence-first requirements discovery before implementation. Creates task directory, seeds PRD, asks one question at a time, researches the repo before asking the user, and converges on MVP scope. Use when requirements are unclear, there are multiple valid approaches, or the user describes a new feature or complex task."
---

# Trellis Brainstorm

## Preconditions

- Task-creation consent has been obtained (consent gate 1).
- Task directory exists via `task.py create`.
- User is ready to enter Trellis planning (Phase 1.1).

## Core Rules

### Evidence Before Questions

If a question can be answered by exploring the codebase, explore the codebase. Do not ask the user to confirm facts that the repository can answer. Ask only for product intent, preference, scope, risk tolerance, or decisions that remain ambiguous after inspection.

Mandatory evidence sources to check before asking the user:
- Code, tests, fixtures, configs
- README files, docs, existing specs, domain notes
- Related Trellis tasks, research files, session history

### One Question at a Time

Each message asks exactly one question. Each question must include:
- The decision needed
- Why the answer matters
- Your recommended answer
- The trade-off if the user chooses differently

Do not ask process questions (whether to search, inspect files, or continue brainstorming). Do the evidence work directly.

### Prefer Options Over Open-Ended Questions

Instead of "What should we do about X?", offer:
- "For X, I recommend option A because [reason]. Option B trades off [trade-off]. Which do you prefer?"

### Separate Fact From Decision

After researching, separate findings into three categories:
1. **Confirmed facts** — repository evidence, no user input needed
2. **Product-intent questions** — only the user can answer (goal, scope, risk tolerance)
3. **Scope/risk decisions** — user must choose (in/out of scope, migration risk, rollback appetite)

Record confirmed facts directly in `prd.md`. Only ask the user about categories 2 and 3.

### Update PRD Immediately

After each user answer, update `prd.md` before continuing. Do not batch updates.

## Workflow

1. **Capture initial request** — write the user's request and known facts into `prd.md`.
2. **Inspect evidence** — search the repository for relevant code, tests, configs, specs, and existing tasks.
3. **Write evidence file** — record findings in `research/evidence.md` with confirmed facts vs. open questions.
4. **Write brainstorm log** — record the question-answer trajectory in `research/brainstorm.md`.
5. **Ask the single highest-value remaining question** — with recommendation and trade-off.
6. **After each answer** — update `prd.md`, then update `research/brainstorm.md`.
7. **For non-trivial tasks** — create or update `implement.md` before implementation starts; create `design.md` for L4/L5 tasks and optionally for L3 tasks with architectural impact.
8. **Declare planning ready** when: all repository-answerable questions are resolved, remaining questions are genuinely about user intent, and `prd.md` has testable acceptance criteria.

Do not invent a project-specific hierarchy. If the repository already has product, domain, or spec docs, use them. If it does not, proceed with the evidence that exists.

## Output Format

### research/evidence.md

```markdown
# Evidence: [Task Title]

## Confirmed Facts
- [fact from code/config/spec inspection]

## Product-Intent Questions (need user)
- [question] — why it matters, recommended answer, trade-off

## Scope/Risk Decisions (need user)
- [decision] — options, recommended, trade-off

## Likely Out-of-Scope
- [item] — reason
```

### research/brainstorm.md

```markdown
# Brainstorm Log: [Task Title]

## Q1: [Question]
- Recommended: [answer]
- User answer: [answer]
- PRD updated: [section changed]

## Q2: [Question]
- Recommended: [answer]
- User answer: [answer]
- PRD updated: [section changed]
```

### prd.md (minimum sections)

```markdown
# PRD: [Task Title]

## Goal and User Value
[What this achieves and for whom]

## Observable Outcomes
[What a user or operator should be able to see, do, or verify when this works]

## Confirmed Facts
[From evidence.md]

## Requirements
[Numbered, specific]

## Acceptance Criteria
[Testable, measurable]

## Out of Scope
[Explicit boundaries]

## Open Questions
[Still blocking planning, if any]

## Risks
[Identified risks]
```

## Quality Bar

- `prd.md` contains testable acceptance criteria.
- Repository-answerable questions have already been answered through inspection.
- Remaining open questions are genuinely about user intent or scope.
- Complex tasks (L3-L5) have `design.md` and `implement.md`.
- `research/evidence.md` separates confirmed facts from questions.
- `research/brainstorm.md` records the full question-answer trajectory.
- The user has reviewed the final planning artifacts or explicitly approved proceeding.

Do not start implementation until the user approves or asks for implementation. That requires the Implementation Consent gate.
