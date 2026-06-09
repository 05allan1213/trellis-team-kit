# Orchestration

> Purpose: choose and control multi-agent execution without making OMC the
> default path.

Use this guide when a task routes to L4/L5, names parallel agents, mentions
worktrees, or asks about OMC `ulw/ultrawork`.

---

## Default Execution Path

Trellis-native execution comes first:

- L3: Trellis subagent execution with normal check and review gates.
- L4: Trellis subagent plus worktree isolation by default for high-risk or
  cross-layer work.
- L5: Trellis-native parallel plus worktree by default for large multi-agent
  work.

OMC is an advanced optional execution path. It requires explicit OMC
`ulw/ultrawork` approval after PRD and acceptance criteria are clear. Routing to
L5 is not approval to start OMC.

---

## Execution Mode Decision

`implement.md` must record the selected execution mode before implementation:

- main session (L1 or explicit inline override only)
- single Trellis subagent
- Trellis subagents
- Trellis-native parallel + worktree
- OMC ulw/ultrawork + worktree + parent/child

L5/orchestrated tasks must not select `main session`; use Trellis-native
parallel plus worktree by default, or a narrower level if the work is actually
serial.

When OMC is selected, `implement.md` must also include the user approval
message and timestamp. Missing audit details invalidate the OMC path, and
runtime hooks must block `ulw/ultrawork` startup until the record is complete.

---

## Workstream Ownership

Parallel execution must define ownership before dispatch:

- each workstream has a name
- each workstream has an owner agent
- changed paths or globs are declared in `scope-manifest.json`
- high-risk paths are listed in `high_risk_allowed`
- expected review gates are recorded

Agents should not edit the same file unless the plan explicitly calls for a
merge step and merge-review is required.

---

## Result Aggregation

Every subagent writes `agent-results/*.json`. The main session integrates the
results and remains responsible for final behavior. Subagents do not approve
their own output.

Merge-review is required when any validator trigger applies: L5; selected
`Trellis-native parallel + worktree`; selected `OMC ulw/ultrawork + worktree +
parent/child`; `Branch strategy` contains `worktree`; `Parent/child: yes`;
`Merge review needed: yes`; PR merge; or conflict resolution. Merge-review must
inspect agent results, scope, override ledger entries, validation failures,
blocking issues, and OMC approval evidence.

---

## Fallback

If OMC is unavailable or not approved, use the Trellis-native path. Do not block
the task solely because the advanced OMC path is unavailable.

---

**Core Principle**: Trellis owns the lifecycle and evidence; OMC is only an
approved execution accelerator.
