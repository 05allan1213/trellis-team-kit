# Spec Index

trellis-team-kit installs workflow behavior specs for AI agents plus
project-fillable backend/frontend convention templates. Fill convention
templates from actual project patterns, not personal preference.

## Two Spec Types

| Type | Definition | Examples | Directory |
|------|-----------|----------|-----------|
| **workflow behavior spec** | Process rules the AI must follow | When to create a task, how to configure Review Gates, what checks to run | `guides/ai-behavior/` |
| **project convention template** | Project-specific backend/frontend rules to fill from real implementation patterns | Database, error handling, components, hooks, state, type safety | `backend/` `frontend/` |
| **guide** | How the AI should think | How to judge architecture boundaries, how to review code, how to debug | `guides/` |

**Out of scope**: Personal coding style preferences that are not backed by
actual project conventions or workflow reliability needs.

## Directory Map

| Directory | Scope | Entry |
|---|---|---|
| `guides/` | Cross-layer process and AI workflow guides: tooling, testing, debugging, review, parallel agents, architecture thinking, spec writing, code reuse | [guides/index.md](./guides/index.md) |
| `backend/` | Project-fillable backend convention templates | [backend/index.md](./backend/index.md) |
| `frontend/` | Project-fillable frontend convention templates | [frontend/index.md](./frontend/index.md) |

## Quick Discovery

```bash
python3 ./.trellis/scripts/get_context.py --mode packages
```

## Loading Order

1. Start here — identify which directories apply
2. Read the directory `index.md` — it lists available specs and when to load each
3. Load only the spec files relevant to the task

Do not load all specs by default. Load the smallest set sufficient for the task.
