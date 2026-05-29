# Worktree Usage Policy

## Recommended Path

All worktrees created as part of trellis-team-kit workflows should be placed under:

```
.trellis/worktrees/<task-slug>/
```

This keeps worktrees organized alongside other Trellis artifacts and makes cleanup straightforward.

## Must Use Worktree

A worktree is required in the following situations:

1. **Multi-subagent parallel** — when two or more subagents are implementing simultaneously in the same package
2. **OMC parallel execution** — when oh-my-claudecode spawns parallel agents that modify code
3. **Cross-package changes** — when changes span multiple packages or modules and isolation is needed
4. **Large refactors** — when a refactor touches many files and rollback risk is high
5. **PR tasks** — when the task is intended to produce a pull request against a target branch
6. **Parent/child tasks** — when child tasks need isolated branches for independent development

## Forbidden

The following actions are prohibited with worktrees:

1. **Multiple agents editing the same files in the same worktree** — if two agents need to edit the same file, serialize their work or use separate worktrees
2. **Merging without merge-review** — all worktree merges must pass trellis-merge-review before integration
3. **Unrelated changes in worktree** — a worktree is scoped to a single task; do not include changes from other tasks
4. **Direct push from worktree** — worktree branches must go through the standard commit and review workflow before pushing
5. **Stale worktrees** — worktrees must be cleaned up after task completion (see Cleanup below)

## Worktree Lifecycle

### Creation

```bash
# Using git worktree
git worktree add .trellis/worktrees/<task-slug> -b <task-slug>

# Or using the EnterWorktree tool if available
```

### During Work

- Commit regularly within the worktree
- Run checks and reviews within the worktree before proposing merge
- Keep the branch up to date with the base branch if long-running

### Merge

1. Ensure trellis-check PASS within the worktree
2. Ensure all review gates PASS
3. Run trellis-merge-review against the worktree branch
4. Only merge after merge-review PASS
5. Use standard git merge or PR process

### Cleanup

Remove the worktree after:

1. **merge-review PASS** — the code has been reviewed and approved
2. **Task archive** — the task has been archived via trellis-finish-work

```bash
# Remove worktree
git worktree remove .trellis/worktrees/<task-slug>

# Delete the branch (if not needed for PR)
git branch -d <task-slug>
```

## Worktree Naming Convention

- Use the task slug from `task.py current` as the worktree directory name
- Branch name matches the worktree directory name
- Example: task `05-29-add-auth-flow` uses worktree `.trellis/worktrees/add-auth-flow/` on branch `add-auth-flow`

## Conflict Resolution

When a worktree merge produces conflicts:

1. The main agent is responsible for resolving conflicts
2. Resolution must follow the PRD and specs as the source of truth
3. If both branches made valid changes, prefer the change that better satisfies Acceptance Criteria
4. After resolution, re-run trellis-check and trellis-merge-review
5. Document any non-trivial resolution decisions in the task's finish.md
