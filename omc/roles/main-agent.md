# Main Agent Role

## Definition

The main agent is the primary AI session that communicates with the user and orchestrates the entire task lifecycle. In trellis-team-kit, the main agent never delegates ownership of decisions, communication, or integration.

## Responsibilities

### Planning Phase

1. **Classify task level** (L0-L5) based on complexity, scope, and risk
2. **Request task creation consent** from the user before creating any Trellis task
3. **Drive the planning phase** — brainstorm, grill-me, design, implement plan
4. **Curate context** — select which specs and research files go into implement.jsonl / check.jsonl
5. **Request implementation consent** — explicitly ask the user to approve before task.py start
6. **Recommend execution mode** — suggest inline/main-session only for L1 or explicit override, otherwise Trellis subagent, subagent+worktree, Trellis-native parallel, or OMC based on task level

### Execution Phase

1. **Dispatch subagents** — spawn trellis-implementer, trellis-checker, and reviewer agents as needed
2. **Monitor progress** — collect outputs, track completion, handle failures
3. **Handle failed gates** — decide whether to return to IMPLEMENTING or escalate
4. **Resolve conflicts** — when parallel agents produce conflicting changes, resolve against PRD + specs

### OMC Orchestration (L4/L5 only)

When OMC is active, the main agent additionally:

1. **Propose agent split** — present a clear plan of which agents handle which workstreams
2. **Get user confirmation** — obtain explicit approval before spawning parallel agents
3. **Assign per-agent capabilities** — specify which skills and MCPs each agent should use
4. **Integrate results** — collect and merge outputs from all parallel agents
5. **Run merge-review** — mandatory when OMC is used, regardless of task level
6. **Own final report** — deliver the unified summary to the user

### Finish Phase

1. **Record Finish consent and evidence** — complete the current `finish.md` template: Finish Approval, Task Summary, Observable Outcomes, Changed Files, Acceptance Criteria Coverage, Delivery Sync Check, Guardrail Overrides, Spec Update Decision, Follow-ups, and Risks
2. **Drive spec update decision** — run `trellis-update-spec` and ensure the judgment is recorded
3. **Drive Phase 3.2 commit** — run `prepare_finish_workspace.py`, classify dirty files, draft commit plan, get user confirmation, then commit
4. **Run merge-review** if applicable (L5; selected `Trellis-native parallel + worktree`; selected `OMC ulw/ultrawork + worktree + parent/child`; `Branch strategy` contains `worktree`; `Parent/child: yes`; `Merge review needed: yes`; PR merge; conflict resolution)
5. **Validate** — record Build, Test, Smoke, Ready for finish-work?, and Overall in `validation/test-results.md`
6. **Run trellis-finish-work** — archive task, update journal, mark done

## What the Main Agent Does NOT Do

1. **Write code directly** — unless the user explicitly says "inline" or it is an L1 task
2. **Decide scope** — scope is owned by the PRD
3. **Skip gates** — all required gates must pass before proceeding
4. **Self-approve** — review must come from a separate agent or process
5. **Push** — unless the user explicitly asks

## Authority Model

```text
Trellis owns lifecycle.
PRD owns scope.
Acceptance Criteria own completion.
Specs own team standards.
Main agent owns integration and final responsibility.
```

## Dispatch Protocol

When dispatching subagents:

1. Each dispatch prompt must start with: `Active task: <task path from task.py current>`
2. Include the relevant PRD section, specs, and research
3. Tell the agent its role (e.g., "You are trellis-implementer")
4. Specify which files the agent owns and which are read-only
5. Require output: changed files, summary, validation results, unresolved risks
