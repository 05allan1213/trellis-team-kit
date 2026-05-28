# Spec Index

This file routes to the distributed spec directories. Detailed indexes live in each directory's own `index.md`.

## Directory Map

| Directory | Scope | Entry |
|---|---|---|
| `guides/` | Cross-layer process guides: tooling, testing, debugging, review, parallel agents, safety, spec writing, code reuse | [guides/index.md](./guides/index.md) |
| `backend/` | Backend code conventions | [backend/index.md](./backend/index.md) |
| `frontend/` | Frontend code and design conventions | [frontend/index.md](./frontend/index.md) |

## Quick Discovery

```bash
python3 ./.trellis/scripts/get_context.py --mode packages
```

Lists available packages and spec layers with paths.

## Loading Order

When a task needs specs, prefer this order:

1. Start here — identify which directory applies
2. Read the directory `index.md` — it lists available specs and when to load each
3. Load only the spec files relevant to the task

Do not load all specs by default. Load the smallest set sufficient for the task.