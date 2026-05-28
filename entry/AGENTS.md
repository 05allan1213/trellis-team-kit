<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI coding agents working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:

- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

<!-- CUSTOM:START -->
## Custom Agent Contract

This file is an entry point only.

For non-trivial development work, follow the Trellis workflow before changing code. Prefer structured task execution over ad-hoc implementation.

### Operating Principles

- Understand the user's goal before editing.
- Plan before implementing when the task affects behavior, architecture, data, UI, or multiple files.
- Keep changes scoped to the active Trellis task, or create/follow the appropriate task before making non-trivial changes.
- Prefer small, reversible changes over broad rewrites.
- Verify the result before reporting completion.
- Be explicit about what changed, what was checked, and what remains uncertain.

### Rule Discovery

- Do not assume all rules are already loaded.
- For task-specific guidance, inspect only the relevant files under `.trellis/spec/`.
- For platform-specific commands, agents, skills, hooks, or local behavior, inspect only the relevant platform directory if it exists.
- Load only the guidance needed for the current task. Do not load unrelated rules by default.

### Boundaries

- Do not bypass the Trellis workflow, active task scope, acceptance criteria, repository hooks, tests, or safeguards.
- Do not perform destructive, irreversible, production-impacting, secret-related, or deployment-related actions without explicit user approval.
- Do not hide failures. If verification cannot be completed, report exactly what was not verified and why.

### Context Discipline

- Do not store project knowledge, task notes, coding standards, testing rules, debugging rules, frontend rules, review rules, or temporary decisions here.
- Keep project knowledge in the repository's dedicated documentation, Trellis task files, specs, research, or memory areas.
- Do not paste large rule files, logs, generated files, or unrelated documentation into the conversation unless needed for the current task.

Only update this custom section when the global agent contract itself changes.
<!-- CUSTOM:END -->
