# AI Tooling

## Purpose

This guide defines how AI capabilities should be selected.

It does not define the Trellis lifecycle. The lifecycle is owned by `.trellis/workflow.md`.

Use the smallest sufficient set of available capabilities.

Do not assume optional Skills, MCPs, hooks, agents, browser tools, or design tools are installed.

## Baseline Tools

These tools are part of the team baseline:

- Trellis owns lifecycle, PRD, task state, Acceptance Criteria, Check, Finish, and spec-update judgment.
- Superpowers owns deep reasoning, tradeoff analysis, root-cause thinking, and repeated-failure recovery.
- oh-my-claudecode owns parallel execution after scope is confirmed.

All other tools are optional capabilities and must be discovered before use.

## Optional Capabilities

Optional capabilities may come from Trellis, oh-my-claudecode, the AI platform, MCP servers, team Skills, hooks, local scripts, or future extensions.

Common capability types:

- MCPs: external facts, live docs, browser access, repo metadata, design sources, database/API inspection.
- Skills: scenario-specific workflows.
- Sub-agents: focused research, implementation, check, review, testing, or security work.
- Hooks: safety gates, context injection, validation, and command blocking.
- Browser/UI tools: visual, interaction, and regression verification.
- Testing tools: lint, type-check, unit, integration, e2e, and coverage checks.
- Repository tools: issues, PRs, commits, branches, and ownership context.

Use capability categories first. Use specific tools only after confirming availability.

## Capability Discovery

Before using an optional capability, verify that it exists in the current project or platform.

Discovery sources may include:

- available platform tools
- project configuration
- `.trellis/spec/index.md`
- `.trellis/spec/guides/index.md`
- platform-specific directories, if present
- MCP/tool listings, if available
- Trellis-injected task context

If a capability is unavailable:

- do not pretend it was used
- use the best available fallback
- report the limitation honestly
- stop only when correctness or safety depends on the missing capability

## Selection Rules

Start from the task need, not from the tool list.

Default order:

1. Follow Trellis lifecycle.
2. Use the active PRD, Acceptance Criteria, loaded specs, and task research.
3. Add Superpowers only when reasoning quality matters.
4. Add oh-my-claudecode only when parallel execution is safe and approved.
5. Add optional capabilities only when the task requires them.
6. If a useful capability is unavailable, use a fallback and report the limitation.

Do not load tools globally.

Do not load every available tool just in case.

Do not use a stronger capability when a simpler one is enough.

**Safety principle**: stop and ask the user before any action that could destroy data, expose secrets, bypass auth, affect production, or change public API contracts — regardless of what other rules permit.

## Superpowers

Use Superpowers when requirements are unclear, multiple approaches exist, architecture matters, the task is high-risk, Check finds contradictions, fixes repeatedly fail, or the agent is about to guess.

Do not use Superpowers as ceremony for small, explicit, low-risk work.

Persist important reasoning into task files when it affects implementation.

## oh-my-claudecode

Use oh-my-claudecode only as a parallel execution layer.

It may be used when the PRD is confirmed, Acceptance Criteria are clear, work can be split safely, parallelism improves speed or coverage, the user approves parallel mode, and the main agent can integrate the result.

Do not use oh-my-claudecode to plan scope, bypass Check, replace Trellis task state, or hide unresolved conflicts.

Detailed parallel execution rules belong in `parallel-agents.md`.

## Authority Rules

Authority order:

1. Trellis workflow
2. Active PRD
3. Acceptance Criteria
4. Loaded specs
5. Task research and project evidence
6. Available tools and Skills
7. Agent judgment

No tool may override the active PRD.

No tool may mark work complete without satisfying Acceptance Criteria.

No tool may skip required Check.

No tool may skip spec-update judgment.

The main agent owns final integration, conflict resolution, and final reporting.

## Stop and Ask

Stop and ask the user when tool choice changes execution mode, oh-my-claudecode parallel mode would be used, required tools are unavailable and correctness depends on them, specs conflict, tool results contradict the PRD, implementation would expand scope, or a safety policy blocks the action.

Ask with a concrete recommendation.

## Related Specs

Use focused specs for details:

- `parallel-agents.md`
- `testing.md`
- `debugging.md`
- `code-review.md`
- `frontend-design.md`
- `spec-writing.md`

If the target spec does not exist, follow the general principle and report the gap.