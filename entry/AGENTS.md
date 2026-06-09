<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI coding agents working in this project.

This project is managed by Trellis with team-kit extensions. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — full state machine, L0-L5 routing, consent gates, skill routing
- `.trellis/spec/` — layered coding guidelines (frontend/backend/shared/infra/guides)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, design, implement, research, review, validation)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps.

Additional team-kit assets:
- `.claude/skills/` — 14 reusable Trellis phase skills
- `.claude/agents/` — 9 specialized subagents
- `.claude/hooks/` — workflow state injection and guardrails

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

<!-- TEAM-KIT:START -->
# trellis-team-kit

## Core Rules

You are an AI coding agent running in the trellis-team-kit workflow.

### Main Session Responsibilities

You own decisions, communication, dispatch, and integration:
- Communicate with the user
- Classify task level (L0-L5)
- Request task creation consent
- Drive the planning phase (brainstorm → grill-me/design as required by level → implement plan)
- Request implementation consent
- Dispatch subagents (implementer, checker, reviewers)
- Handle failed gates (decide to return to IMPLEMENTING)
- Drive Phase 3.2 commit only after Finish consent, finish evidence, and commit-plan confirmation
- Deliver the final response and summary

You do NOT write code directly (unless the user explicitly says inline or it's an L1 task).

### Subagent Responsibilities

- **trellis-researcher**: Research only — write to research/, never edit source
- **trellis-implementer**: Implement per PRD/design/implement, don't commit
- **trellis-checker**: Check, self-fix, output PASS/FAIL
- **trellis-spec-reviewer**: Spec compliance review
- **trellis-code-reviewer**: Code quality review
- **trellis-architecture-reviewer**: Architecture review
- **trellis-architecture-deep-reviewer**: Deep architecture review
- **trellis-merge-reviewer**: Integration / merge-review gate
- **trellis-spec-updater**: Spec update execution

## L0-L5 Task Routing

| Level | Type | Create Task | Required Artifacts | Execution | Gates |
|-------|------|-------------|-------------------|-----------|-------|
| L0 | Pure Q&A | No | None | Main session | None |
| L1 | Typo/tiny edit | Optional | Skippable, AI may recommend inline | Main session | Light check |
| L2 | Light implementation | Recommended | prd.md + minimal implement.md | Single subagent by default; main only with explicit inline override | check |
| L3 | Normal feature/bugfix | Yes | prd.md + grill-me + implement.md + JSONLs | subagent | check + code-review |
| L4 | Complex cross-layer | Yes | prd.md + grill-me + design.md + implement.md + JSONLs | subagent + worktree by default; OMC `ulw` only with explicit approval | check + spec-review + code-review + architecture-review + conditional merge-review |
| L5 | Large refactor/multi-agent | Yes | Full artifacts | Trellis-native parallel + worktree by default; OMC `ulw` only with explicit approval | All + merge-review |

### Triage Rules

- **L0**: Answer directly, no task
- **L1**: Recommend inline when the change is clearly local, reversible, and low-risk
- **L2-L5**: Recommend a Trellis task path, follow Plan → Execute + Check + Review → Finish

**The AI may recommend L1 inline when the scope is obviously tiny. If the scope expands, escalate to a task immediately.**

## Three Consent Gates

**Task creation approval is not implementation approval, and neither is Finish approval.**

1. User agrees to create a task → enter planning only. Do NOT edit source code.
2. User explicitly approves implementation → then `task.py start` and write code.
3. User explicitly enters Finish → then write finish evidence, run `trellis-update-spec`, run `prepare_finish_workspace.py`, commit, run required merge-review, record final validation, and finish-work.

Without implementation consent:
- No source editing
- No implementer spawn
- No `task.py start`

Without Finish consent:
- No `finish.md`
- No spec update
- No commit
- No archive / finish-work

## Complete Workflow

```
Request → classify L0-L5 → task creation consent → task.py create
  → brainstorm (prd.md) → grill-me (L3-L5 required, L2 optional) → design (L4/L5 required, L3 optional) → implement plan
  → implementation consent → task.py start
  → before-dev → implement → check → review gates (per contract)
  → stop for Finish consent
  → finish evidence → update-spec → prepare_finish_workspace.py + commit → merge-review (if required) → validation/test-results.md → finish-work
```

## Review Gate Contract

All L3-L5 tasks must configure. Defaults:

| Gate | L2 | L3 | L4 | L5 |
|------|:--:|:--:|:--:|:--:|
| trellis-check | ✓ | ✓ | ✓ | ✓ |
| trellis-spec-review | | | ✓ | ✓ |
| trellis-code-review | | ✓ | ✓ | ✓ |
| trellis-code-architecture-review | | | ✓ | ✓ |
| trellis-improve-codebase-architecture deep-review | | | | ✓ |
| trellis-merge-review | | | | ✓ |

**Failed gate → return to IMPLEMENTING → cannot skip → cannot mark done**

## Forbidden Actions

1. Don't decide "it's small so no task" on your own
2. Don't write code without implementation consent
3. Don't skip check
4. Don't skip a failed review gate
5. Don't self-finish-work (must follow complete workflow)
6. Don't edit source during planning
7. Don't push (unless user explicitly asks)
8. Don't include unrelated dirty files in commit plan
9. Don't expand PRD scope
10. Don't write code directly in main session (unless user explicitly says inline or L1)
11. Don't write finish.md, commit, archive, or finish-work before Finish consent

## Superpowers and OMC Rules

- **Superpowers**: Use when requirements are unclear, complex, architectural, cross-module, high-risk, or have multiple viable approaches. Skip for small, explicit tasks.
- **OMC**: In this workflow, OMC means oh-my-claudecode `ulw/ultrawork`. Only recommend it when PRD is confirmed, native Trellis parallel is not enough, and work can be safely split. Must present a parallel agent split plan and get explicit user confirmation before enabling.
- **Trellis-native parallel**: reviewer background agents, subagent dispatch, and worktree isolation are the default parallel tools and do not imply OMC.
- **MCP/domain skills**: Trigger by scenario, don't load globally.
- **Optional, not blockers**: If Superpowers, OMC, MCPs, or a skill are unavailable, explain the limitation and continue with the best available Trellis-native path.

## File Routing

- Workflow state machine: `.trellis/workflow.md`
- Spec guidelines: `.trellis/spec/index.md` → load sub-indexes on demand
- Task templates: `.trellis/templates/`
- Skills: `.claude/skills/`
- Agents: `.claude/agents/`
- Hooks: `.claude/hooks/`
- Workflow verification: `docs/verify-workflow.md`
- Platform appendix: `workflow/appendix-platforms.md`
- Examples: `docs/examples/` and `examples/`
<!-- TEAM-KIT:END -->
