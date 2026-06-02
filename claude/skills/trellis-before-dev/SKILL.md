---
name: trellis-before-dev
description: "Read all task artifacts and specs before writing code. Outputs implementation constraints. Use after task.py start and before any source editing — the before-dev gate is mandatory and blocks code changes until satisfied."
---

# Trellis Before Dev

## Preconditions

- Task status is `in_progress` (`task.py start` has been run).
- Planning artifacts are complete (prd.md, implement.md, design.md if L4/L5).

## Core Rules

This skill is a gate. You MUST NOT edit source code before completing it. Reading is allowed. Writing code is forbidden until this skill finishes.

## Workflow

1. **Read `prd.md`** — understand the goal, scope, acceptance criteria, and out-of-scope items.
2. **Read `design.md`** (if present) — understand architecture, data flow, contracts, and trade-offs.
3. **Read `implement.md`** — understand execution strategy, review gate contract, and validation commands.
4. **Read `implement.jsonl` entries** — understand which specs and research files are curated for implementation context.
5. **Read relevant specs** — use `.trellis/spec/index.md` to route to the right spec files. Read the specific guideline files, not just the index.
6. **Read relevant research** — any `research/*.md` files referenced by the task.
7. **Output implementation constraints** — a concise list of what must be true during implementation.
8. **Confirm task is `in_progress`** — verify status before proceeding.

### Spec Reading

```bash
# Discover packages and their spec layers
python3 ./.trellis/scripts/get_context.py --mode packages

# Read spec index for each relevant package
cat .trellis/spec/<package>/<layer>/index.md

# Read the specific guideline files listed in the index
cat .trellis/spec/<package>/<layer>/<guideline>.md

# Always read shared guides
cat .trellis/spec/guides/index.md
```

The index is NOT the goal — it points to the actual guideline files. Read those files to understand the coding standards and patterns.

## Output Format

### Implementation Constraints

```markdown
# Before-Dev Constraints: [Task Title]

## Task Context
- Task level: [L0-L5]
- Goal: [one sentence from prd.md]

## Scope Boundaries
- In scope: [from prd.md]
- Out of scope: [from prd.md]

## Spec Constraints
- [spec file]: [key constraint]
- [spec file]: [key constraint]

## Design Constraints
- [from design.md, if present]

## Implementation Strategy
- Mode: [from implement.md]
- TDD: [yes/no]
- Review gates: [selected gates from contract]

## Acceptance Criteria
- [AC 1]
- [AC 2]

## Observable Outcomes
- [what the user or operator must be able to observe after implementation]

## Must NOT
- [boundary from prd.md or implement.md]
```

## Quality Bar

- All task artifacts have been read (prd.md, design.md, implement.md, JSONL entries).
- Relevant spec files have been read (not just the index).
- Implementation constraints are specific and actionable.
- Observable outcomes to preserve or prove are captured before coding starts.
- The task status is confirmed as `in_progress`.
- No source code has been edited before this skill completes.

If any artifact is missing, report it before proceeding. Missing `design.md` is acceptable for L2-L3. Missing `prd.md` or `implement.md` is blocking.
