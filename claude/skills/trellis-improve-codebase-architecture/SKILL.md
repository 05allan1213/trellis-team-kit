---
name: trellis-improve-codebase-architecture
description: "Dual-mode skill for architecture guidance and deep review. Guidance mode (before implementation) outputs to design.md Architecture Guidance. Deep-review mode (after implementation) outputs to review/architecture-deep-review.md with PASS/FAIL. Triggers when changes cross 3+ layers, add new modules, change API/schema/persistence, modify shared types/util/config, introduce new abstractions, refactor, or use multi-subagent parallel execution."
---

# Trellis Improve Codebase Architecture

## Preconditions

### Guidance Mode
- PRD is complete and grilled.
- Task is L3-L5 and one or more trigger conditions apply:
  - Change crosses 3+ layers
  - New module being added
  - API/schema/persistence change
  - Shared type/util/config change
  - New abstraction being introduced
  - Refactor planned
  - Multi-subagent parallel execution planned

### Deep-Review Mode
- `trellis-check` has passed.
- Deep review is selected in the Review Gate Contract (required for L5).

## Core Rules

This skill operates in two modes. The mode is determined by when it is invoked:

- **Guidance mode** (Phase 1.3): before implementation. Output goes to `design.md` Architecture Guidance section.
- **Deep-review mode** (Phase 2.3): after implementation. Output goes to `review/architecture-deep-review.md`.

FAIL in deep-review mode must return to IMPLEMENTING. Do not proceed to finish.

## Workflow

### Guidance Mode

1. **Read `prd.md`** — understand scope and constraints.
2. **Explore current architecture** — map the relevant layers, modules, and dependencies.
3. **Identify architectural impact** — what will this change affect structurally?
4. **Produce guidance** covering:
   - Which layers are involved and how they should connect
   - Where new code should live (module placement)
   - What shared types/utilities need to change
   - What the data flow should look like
   - What contracts need to be defined
   - What existing patterns to follow
   - What pitfalls to avoid
5. **Write to `design.md`** Architecture Guidance section.

### Deep-Review Mode

1. **Read changed files** — `git diff HEAD` for the full diff.
2. **Read task artifacts** — `prd.md`, `design.md`, `implement.md`.
3. **Compare implementation against design** — does the code match the architectural guidance?
4. **Review each dimension** below.
5. **Write findings** to `review/architecture-deep-review.md`.

#### Dimensions (Deep-Review)

##### Structural Alignment with Design
- Does the implementation follow the architecture guidance from `design.md`?
- Were architectural decisions made during implementation that deviate from the plan?
- Are deviations justified and documented?

##### Cross-Layer Integration
- Do layers interact through well-defined interfaces?
- Are there direct dependencies that should go through an abstraction?
- Is data flow consistent across layers (no missing transformations)?

##### Module Ownership
- Does each module own a clear domain of knowledge?
- Is knowledge duplicated across modules?
- Are module boundaries respected (no reaching into another module's internals)?

##### Shared Type/Utility Impact
- Did shared type/utility changes break or risk breaking other consumers?
- Are shared utilities still general-purpose, or have they become task-specific?
- Are new shared types necessary, or should they be local?

##### Extensibility and Coupling
- Is the implementation extensible for foreseeable changes?
- Are components loosely coupled?
- Can parts be tested independently?
- Are there hard dependencies that prevent partial deployment or testing?

##### Concurrency and Consistency (if applicable)
- Are there race conditions in shared state?
- Is data consistency maintained across concurrent access?
- Are transactions or locks used correctly?

## Output Format

### Guidance Mode: design.md Architecture Guidance

```markdown
## Architecture Guidance

### Layers Involved
- [layer]: [role in this change]

### Module Placement
- New code for [X] should go in [module] because [reason].

### Data Flow
- [description of data flow across layers]

### Contracts to Define
- [contract]: [shape, direction, error cases]

### Shared Changes
- [shared type/util]: [what changes, impact on other consumers]

### Patterns to Follow
- [pattern from .trellis/spec/]: [how it applies]

### Pitfalls to Avoid
- [pitfall]: [why it's a risk, how to avoid it]
```

### Deep-Review Mode: review/architecture-deep-review.md

```markdown
# Architecture Deep Review: [Task Title]

## Files Reviewed
- [file path]
- [file path]

## Structural Alignment with Design
- [finding]
- Verdict: PASS/FAIL

## Cross-Layer Integration
- [finding]
- Verdict: PASS/FAIL

## Module Ownership
- [finding]
- Verdict: PASS/FAIL

## Shared Type/Utility Impact
- [finding]
- Verdict: PASS/FAIL

## Extensibility and Coupling
- [finding]
- Verdict: PASS/FAIL

## Concurrency and Consistency (if applicable)
- [finding]
- Verdict: PASS/FAIL / N/A

## Blocking Issues
1. [issue]: [architectural impact]
(or "none")

## Non-Blocking Issues
1. [suggestion]: [improvement rationale]
(or "none")

## Verdict
- PASS — architecture is sound
- FAIL — must return to implement:
  1. [blocking issue summary]
```

## Quality Bar

- Guidance mode provides specific, actionable direction (not generic principles).
- Deep-review mode compares implementation against design (not just general quality).
- Blocking issues explain the architectural impact, not just the symptom.
- FAIL verdict returns to IMPLEMENTING — this is not advisory.
- L5 tasks that skip deep review are in violation of the Review Gate Contract.
