# Spec Index

trellis-team-kit specs regulate **AI workflow behavior** only — not personal coding style.

## Two Spec Types

| Type | Definition | Examples | Directory |
|------|-----------|----------|-----------|
| **code-spec** | Process rules the AI must follow | When to create a task, how to configure Review Gates, what checks to run | `backend/` `frontend/` |
| **guide** | How the AI should think | How to judge architecture boundaries, how to review code, how to debug | `guides/` |

**Out of scope**: How to write APIs, how to name components, how to operate databases — these vary by developer and are not team AI workflow specs.

## Directory Map

| Directory | Scope | Entry |
|---|---|---|
| `guides/` | Cross-layer process guides: tooling, testing, debugging, review, parallel agents, architecture thinking, spec writing, code reuse | [guides/index.md](./guides/index.md) |
| `backend/` | Backend AI behavior specs | [backend/index.md](./backend/index.md) |
| `frontend/` | Frontend AI behavior specs | [frontend/index.md](./frontend/index.md) |

## Quick Discovery

```bash
python3 ./.trellis/scripts/get_context.py --mode packages
```

## Loading Order

1. Start here — identify which directories apply
2. Read the directory `index.md` — it lists available specs and when to load each
3. Load only the spec files relevant to the task

Do not load all specs by default. Load the smallest set sufficient for the task.
