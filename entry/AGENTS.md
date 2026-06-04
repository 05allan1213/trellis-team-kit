<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI coding agents working in this project.

This project is managed by Trellis with team-kit extensions. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — full state machine, L0-L5 routing, dual-consent gates, skill routing
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

You own decisions, communication, dispatch, and integration. Do NOT write code directly (unless user explicitly says inline or L1).

### Subagent Responsibilities

| Agent | Role |
|-------|------|
| trellis-researcher | Research only — write research/, never edit source |
| trellis-implementer | Implement per PRD/design/implement |
| trellis-checker | Check, self-fix, output PASS/FAIL |
| trellis-spec-reviewer | Spec compliance review |
| trellis-code-reviewer | Code quality review |
| trellis-architecture-reviewer | Architecture review |
| trellis-architecture-deep-reviewer | Deep architecture review |
| trellis-merge-reviewer | Post-merge review |
| trellis-spec-updater | Spec update execution |

## L0-L5 Task Routing

| Level | Type | Create Task | Required Artifacts | Gates |
|-------|------|-------------|-------------------|-------|
| L0 | Pure Q&A | No | None | None |
| L1 | Typo/tiny edit | Optional | Skippable, AI may recommend inline | Light check |
| L2 | Light implementation | Recommended | prd.md | check |
| L3 | Normal feature/bugfix | Yes | prd.md + implement.md | check + code-review |
| L4 | Complex cross-layer | Yes | prd.md + design.md + implement.md | check + spec-review + code-review + architecture-review |
| L5 | Large refactor/multi-agent | Yes | Full artifacts | All + merge-review |

- **L0**: Answer directly
- **L1**: Recommend inline when the change is clearly local, reversible, and low-risk
- **L2-L5**: Recommend a Trellis task path
- **Parallel by default means Trellis-native parallel**: subagents, reviewer background agents, and worktrees
- **OMC means oh-my-claudecode `ulw/ultrawork`**: an optional advanced mode, not the default meaning of “parallel”

**The AI may recommend L1 inline when the scope is obviously tiny. If the scope expands, escalate to a task immediately.**

## Dual Consent Gates

1. Task creation consent → enter planning only. No source editing.
2. Implementation consent → then `task.py start` and write code.

## Complete Workflow

```
Request → classify → task creation consent → task.py create
  → brainstorm → grill-me → design → implement plan
  → implementation consent → task.py start
  → before-dev → implement → check → review gates
  → update-spec + observable outcomes → commit → merge-review → validate → finish-work
```

## Review Gate Contract

Failed gate → return to IMPLEMENTING → cannot skip → cannot mark done.

## Forbidden Actions

1. Don't decide "small so no task" on your own
2. Don't write code without implementation consent
3. Don't skip check or failed review gate
4. Don't self-finish-work
5. Don't edit source during planning
6. Don't push (unless user explicitly asks)
7. Don't expand PRD scope
8. Don't write code in main session (unless inline or L1)

## Extension Rules

- Superpowers is optional reasoning help, not a hard dependency.
- OMC `ulw/ultrawork` is optional advanced orchestration, not the default parallel path.
- MCPs and scenario skills are optional capabilities, not prerequisites.
- If an extension is unavailable, explain the limitation and continue with the best available Trellis-native path.

## File Routing

- Workflow: `.trellis/workflow.md`
- Specs: `.trellis/spec/index.md`
- Task templates: `.trellis/templates/`
- Skills: `.claude/skills/`
- Agents: `.claude/agents/`
- Hooks: `.claude/hooks/`
<!-- TEAM-KIT:END -->
