# Skill Routing

> Purpose: load the right workflow skills and specs for the routed task level
> without inventing a parallel lifecycle.

Use this guide when deciding whether to answer inline, create a Trellis task,
dispatch subagents, load Superpowers, or route to OMC guidance.

---

## Routing Levels

Trellis routes work by concrete levels:

- L0: answer or explain, no task.
- L1: small inline edit or text change.
- L2: light task with scoped artifacts.
- L3: standard feature or bugfix.
- L4: strict high-risk, cross-layer, API, schema, auth, migration, or shared
  contract work.
- L5: orchestrated multi-agent, broad refactor, or architecture-level work.

Do not use `L3+` as an executable route. If the task is above L2, choose L3,
L4, or L5 and record the profile.

---

## Profile Mapping

Profiles describe the workflow weight:

- quick: L0/L1 response or inline edit.
- light: L2 scoped task.
- standard: L3 task with check and review gates.
- strict: L4 task with stronger scope, high-risk, and review evidence.
- orchestrated: L5 task with workstreams, subagents, agent results, and
  merge-review.

The profile should match `routing_rules.json`, `workflow_profiles.json`, task
artifacts, and review gates.

---

## Skill Loading

Load only the smallest relevant set of instructions:

- Use Trellis skills for the active lifecycle phase.
- Use Superpowers as reasoning discipline for brainstorming, plans, TDD,
  debugging, verification, review, and finishing.
- Load specs from `.trellis/spec/` based on task risk and phase.
- Do not load every guide by default.

When a task touches hooks, validators, routing, agents, OMC, replay, or specs,
check the matching ai-behavior guide before implementation or review.

---

## OMC Routing

OMC is not selected by routing alone. A prompt may mention OMC and still only
route to L5 until the user explicitly approves OMC. The Trellis task lifecycle,
scope manifest, agent-results, check, review, merge-review, and finish gates
still apply.

---

**Core Principle**: route to the smallest sufficient Trellis workflow, then load
the skills and specs needed for that route.
