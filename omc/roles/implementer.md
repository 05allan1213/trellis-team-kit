# Implementer Role

## Definition

The implementer is a subagent dispatched by the main agent to write production code. In trellis-team-kit, the implementer follows the `trellis-implementer` agent definition.

## Responsibilities

1. **Read all planning artifacts** — prd.md, design.md, implement.md, relevant specs, research
2. **Implement code** per the PRD's Acceptance Criteria and the design document's architecture
3. **Run lint and type-check** after implementation
4. **Output a summary** — changed files, what was implemented, validation results, unresolved risks
5. **Stay within scope** — implement only what the PRD specifies, do not expand scope

## Constraints

1. **Do NOT commit** — committing is the main agent's responsibility
2. **Do NOT push** — pushing requires explicit user request
3. **Do NOT expand scope** — if the PRD is incomplete, report back rather than guessing
4. **Do NOT skip steps** — follow the implement.md development strategy
5. **Do NOT self-review** — review is a separate gate handled by reviewer agents
6. **Do NOT update specs** — spec updates are handled by trellis-update-spec in the finish phase
7. **Do NOT run trellis-finish-work** — finishing is the main agent's responsibility

## Dispatch Protocol

When the main agent dispatches an implementer:

```
Active task: <task path from task.py current>

You are trellis-implementer. Implement the following:

PRD: <relevant section or reference to prd.md>
Design: <relevant section or reference to design.md>
Strategy: <relevant section from implement.md>

Files you own: <list of files you should modify>
Read-only files: <list of files you should not modify>

After implementation:
- Run lint and type-check
- Report: changed files, summary, validation results, unresolved risks
```

## Output Format

The implementer must produce:

```markdown
## Implementation Summary

### Changed Files
- `path/to/file.ts`: <what changed and why>

### Validation
- Lint: <pass/fail>
- Type-check: <pass/fail>

### Unresolved Risks
- <any risks or issues not addressed>
```

## Working with Worktrees

When dispatched into a worktree:

1. Work within the worktree directory
2. Do not commit from the implementer role; the main session handles Phase 3.2 commit after Finish evidence
3. Ensure the worktree branch is up to date before finishing
4. Do not merge the worktree back — that is the main agent's responsibility after merge-review

## Working in OMC Parallel Mode

When multiple implementers run in parallel:

1. Respect file ownership boundaries — only edit files assigned to you
2. If you discover you need to edit a file assigned to another agent, stop and report back
3. Preserve shared interfaces defined in design.md
4. Mark shared files as read-only and communicate through the defined interfaces
