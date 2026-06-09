# OMC Orchestration Strategy

## When to Use OMC

oh-my-claudecode (OMC) is a parallel execution extension for trellis-team-kit.
In this workflow, OMC specifically means the official `ulw/ultrawork` mode.
Use it only when all of the following are true:

1. **Task level is L4 or L5** — complex cross-layer changes, multi-agent work, or large refactors
2. **Independent workstreams** — parent/child task structure is required only when the split creates independently finishable child tasks
3. **Multi-agent parallel execution** — when the PRD confirms that work can be safely split into independent streams
4. **User explicitly confirms** — OMC `ulw/ultrawork` requires explicit user approval before spawning agents

OMC must NOT be used for L0-L3 tasks. If the work truly needs OMC, reroute or rescope it as an L4/L5 task and get explicit OMC `ulw/ultrawork` approval.
If OMC is unavailable, the task must continue on the Trellis-native path instead of blocking.

## Execution Mode Hierarchy

The execution mode escalates based on task complexity:

| Level | Mode | When |
|-------|------|------|
| L1 | Main session | Direct inline answer or tiny change |
| L2 | Single Trellis subagent by default | Main session only with explicit inline override |
| L3 | Subagent | Dispatch trellis-implementer / trellis-checker subagents |
| L4 | Subagent + worktree | Default complex-task path |
| L5 | Trellis-native parallel + worktree | Default heavy-task parallel path |
| L5 advanced | OMC `ulw/ultrawork` + worktree + parent/child | When advanced orchestration is worth the overhead |

### Escalation Rules

- A lower mode can always be used for a higher-level task if the work turns out to be simpler than expected
- A higher mode must NOT be used for a lower-level task (overhead without benefit)
- Mode changes mid-task require user confirmation

## Prerequisites for OMC

Before enabling OMC `ulw/ultrawork`:

1. **Confirmed PRD** — prd.md exists with verifiable Acceptance Criteria
2. **Clear AC** — each acceptance criterion is independently testable
3. **Safe splitting** — workstreams have minimal overlap in source files
4. **Explicit user confirmation** — user must approve the agent split plan

If any prerequisite fails, fall back to Trellis-native subagents/worktrees.

## OMC Must Not

1. **Decide scope** — scope is owned by the PRD, not by the execution layer
2. **Bypass Plan** — planning artifacts (prd.md, design.md, implement.md) must be complete before OMC starts
3. **Bypass Check** — every agent's output must pass trellis-check
4. **Replace Trellis task state** — task status, PRD, AC, check, finish, and spec update remain under Trellis lifecycle
5. **Skip merge-review** — merge-review is mandatory when OMC is used (see below)
6. **Self-approve** — agents cannot approve their own work; integration review is separate

## Main Agent Role in OMC

When OMC is active, the main agent retains full responsibility for:

1. **Recommend mode** — suggest the appropriate execution mode based on task level
2. **Propose agent split** — present a clear plan of which agents handle which workstreams, which files they edit, and how integration works
3. **Get confirmation** — obtain explicit user approval before spawning parallel agents
4. **Integrate results** — collect outputs from all agents, resolve conflicts, verify completeness
5. **Resolve conflicts** — when agents produce conflicting changes, resolve against PRD + specs
6. **Own final report** — the main agent delivers the summary to the user, not individual agents

## Merge-Review Requirement

**merge-review is mandatory whenever OMC is used.**

This applies regardless of task level. When parallel agents modify the codebase:

1. After all agents report completion, the main agent runs trellis-merge-review
2. Merge-review checks for: conflicts, duplicate implementations, missing files, interface consistency
3. If merge-review FAIL, the main agent resolves issues and re-runs merge-review
4. Only after merge-review PASS can the workflow proceed to validation and finish

## OMC Agent Dispatch Protocol

When dispatching OMC parallel agents:

1. Each agent prompt must start with: `Active task: <task path from task.py current>`
2. Each agent must receive: prd.md section relevant to its workstream, relevant specs, relevant research
3. Each agent must know: which files it owns, which files are read-only, what interfaces it must preserve
4. Each agent must output: changed files, summary, validation results, unresolved risks

## Conflict Prevention

To minimize conflicts between parallel agents:

1. Assign non-overlapping file ownership per agent
2. Define shared interfaces upfront in design.md
3. Mark shared files as read-only for all agents
4. Use worktrees when agents modify the same package
5. If conflict is unavoidable, serialize that portion of the work
