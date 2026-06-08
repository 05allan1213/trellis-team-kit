# Architecture Thinking Guide

> **Purpose**: Help AI assistants reason about architecture decisions before and during implementation.

---

## Why Architecture Thinking?

AI coding failures at the architecture level are expensive to fix later:

- Wrong module boundary → tangled dependencies
- No rollback plan → risky deployment
- Duplicated concepts → drift and inconsistency
- Ignored existing patterns → reinvention
- Missing contract definition → integration breakage

This guide helps AI assistants ask the right architecture questions before writing code.

---

## Architecture Trigger Checklist

Ask these questions when the task:

- [ ] Crosses 3 or more layers (UI → API → Service → Persistence)
- [ ] Introduces a new module, package, or service
- [ ] Changes an API, schema, shared type, or config contract
- [ ] Modifies shared utilities or constants
- [ ] Introduces a new abstraction or pattern
- [ ] Is a refactor that moves code across boundaries
- [ ] Involves multiple subagents working in parallel

---

## Decision Framework

### 1. Data Shape First

Before proposing logic, name the durable data:

- What state is created, read, updated, or deleted?
- Where is the single source of truth?
- What format crosses each boundary?

If the data shape is wrong, no amount of logic fixes it.

### 2. Boundary Ownership

For each piece of behavior, ask:

- Which module owns this?
- Is a concern leaking into the wrong layer?
- Does the boundary match the existing architecture?

### 3. Compatibility

Before accepting a change that touches contracts:

- What did the previous version expect?
- What will the new version produce?
- Are existing consumers broken?
- Is a migration path needed?

### 4. One Source of Truth

Reject parallel mechanisms that must stay in sync by memory:

- Two paths producing the same output → what binds them together?
- Manual lists that mirror generated output → automate or eliminate.
- Duplicated constants across packages → centralize.

### 5. Alternatives Considered

For non-trivial design decisions:

- What alternatives were considered?
- Why was each rejected?
- What trade-off does the chosen approach make?

---

## Red Flags

| Signal | Action |
|--------|--------|
| New module without a contract definition | Stop — define the contract first |
| Cross-layer change without data flow mapping | Map the data flow before coding |
| Shared utility change without impact search | Search all call sites first |
| "Temporary" abstraction that looks permanent | Treat it as permanent — design it properly |
| No rollback plan for a schema/API change | Define the rollback before implementing |
| Multiple agents touching the same boundary | Define the contract explicitly before parallel work |

---

## Output

Architecture thinking should produce concrete artifacts:

- **design.md Architecture Guidance section** — for pre-implementation guidance
- **design.md Alternatives Considered** — rejected approaches with reasons
- **review/architecture-review.md** — post-implementation verification

---

## How to Use

1. **Before implementation (L3-L5)**: Load this guide when the task triggers any architecture checklist item
2. **During implementation**: Re-check if the task scope expands or a new boundary is crossed
3. **After implementation (L4/L5)**: Use as review lens in `trellis-code-architecture-review`

---

**Core Principle**: Architecture decisions are cheaper to change before code exists. Think at the boundary level, not the line level.
