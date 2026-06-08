# General Development Guides

> **Purpose**: Help AI assistants choose the right workflow, tools, checks, and thinking process before and during development.

---

## Why General Guides?

Most AI coding failures do not come from lack of coding ability. They come from missing process boundaries:

* Didn't confirm the task lifecycle before coding
* Didn't choose the right tool or skill for the task
* Didn't think about cross-layer impact
* Didn't search for existing reusable code
* Didn't test the right things
* Didn't debug from root cause
* Didn't review the final diff carefully

These guides help AI assistants ask the right questions and load the right rules without reading every spec file by default.

---

## Available Guides

| Guide                                                         | Purpose                                                                         | When to Use                                           |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------- |
| [Common Mistakes](./ai-behavior/common-mistakes.md)           | Prevent repeated workflow regressions in routing, scope, overrides, agents, replay, doctor, and OMC approval | Before-dev, check, code review, and workflow hardening |
| [AI Tooling](./ai-tooling.md)                                 | Define Trellis, Superpowers, oh-my-claudecode, MCP, skills, and hooks ownership | When deciding which tool or workflow should be used   |
| [Architecture Thinking](./architecture-thinking.md)           | Reason about module boundaries, contracts, compatibility, and trade-offs        | When a task crosses layers, introduces modules, or changes contracts |
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)   | Identify patterns and reduce duplication                                        | When you notice repeated patterns or create utilities |
| [Code Review](./code-review.md)                               | Review AI-generated changes before delivery                                     | Before final summary, PR, or user handoff             |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through data flow across layers                                           | When a feature spans multiple layers                  |
| [Debugging](./debugging.md)                                   | Reproduce, diagnose, and fix bugs from root cause                               | When fixing bugs or investigating failures            |
| [Parallel Agents](./parallel-agents.md)                       | Decide when and how to use parallel agents                                      | When work can be safely split across agents           |
| [Review Thinking](./review-thinking.md)                       | Perform effective, honest code review with actionable findings                  | When reviewing code as a subagent or before handoff   |
| [Spec Writing](./spec-writing.md)                             | Keep specs short, focused, and maintainable                                     | When creating or updating specs                       |
| [Testing](./testing.md)                                       | Decide what validation is required                                              | Before and after implementation                       |
| [Frontend Design](../frontend/frontend-design.md)             | UI/UX design contract, visual quality, project stage awareness                  | When a task touches frontend UI, components, or pages |

---

## Quick Reference: Thinking Triggers

### When to Think About Tools

* [ ] The task is complex or ambiguous
* [ ] The task may benefit from Superpowers reasoning
* [ ] The task can be split into independent workstreams
* [ ] External facts, docs, browser checks, or MCP tools are needed
* [ ] A domain-specific skill may apply

→ Read [AI Tooling](./ai-tooling.md)

### When to Think About Cross-Layer Issues

* [ ] Feature touches 3+ layers
* [ ] Data format changes between layers
* [ ] Multiple consumers need the same data
* [ ] You're not sure where to put some logic

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When to Think About Code Reuse

* [ ] You're writing similar code to something that exists
* [ ] You see the same pattern repeated 3+ times
* [ ] You're adding a new field to multiple places
* [ ] You're modifying any constant or config
* [ ] You're creating a new utility/helper function

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

### When to Think About Verification

* [ ] The task changes behavior
* [ ] The task fixes a bug
* [ ] The task touches UI, API, database, auth, or shared logic
* [ ] The implementation has meaningful risk
* [ ] You are preparing the final handoff

→ Read [Testing](./testing.md) and [Code Review](./code-review.md)

### When to Think About Architecture

* [ ] Feature crosses 3+ layers
* [ ] Introducing a new module, package, or service
* [ ] Changing an API, schema, shared type, or config contract
* [ ] Modifying shared utilities or constants
* [ ] Introducing a new abstraction or pattern
* [ ] Refactoring that moves code across boundaries
* [ ] Multiple subagents working in parallel

→ Read [Architecture Thinking](./architecture-thinking.md)

### When to Think About Review Quality

* [ ] You are about to review code as a subagent (spec-reviewer, code-reviewer, architecture-reviewer)
* [ ] You are performing a merge-review after multi-agent work
* [ ] A previous review failed and the code is being re-reviewed
* [ ] You are preparing the final handoff and need to verify quality

→ Read [Review Thinking](./review-thinking.md)

---

## Pre-Modification Rule

> **Before changing any existing value, behavior, config, or shared pattern, search first.**

Search for existing usage before editing, replacing, deleting, or introducing a new abstraction.

This habit prevents many "forgot to update X" bugs.

---

## How to Use This Directory

1. **Before coding**: Load only the guide relevant to the active task
2. **During coding**: Re-check the guide if the task becomes broader or riskier
3. **After coding**: Use testing and review guides before final handoff
4. **After repeated mistakes**: Update the relevant guide instead of adding prompt instructions

---

## Contributing

Found a repeated mistake, missing trigger, or useful decision rule? Add it to the relevant guide.

Keep each guide short, focused, and loadable.

---

**Core Principle**: Load the right guide at the right time, not every guide every time.

**Language**: All documentation should be written in **English**.
