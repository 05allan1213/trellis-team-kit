# Guardrails

> Purpose: keep Trellis tasks inside declared scope while making allowed
> exceptions auditable.

Use this guide before editing source files, reviewing scope warnings, accepting
guardrail overrides, or finishing a task with risk evidence.

---

## Scope Manifest Authority

For L2+ tasks, `scope-manifest.json` is the machine-readable scope contract.
Markdown plans can explain intent, but guardrails and validators use the
manifest.

The manifest must include:

- `declared_paths` or `declared_globs` with at least one non-empty entry.
- `out_of_scope` with explicit boundaries.
- `level` and `profile` that match the routed task complexity.
- `high_risk_allowed` when API, auth, schema, migration, shared type, contract,
  or similar high-risk paths are intentionally in scope.

Before development starts, `before-dev.md` and `scope-manifest.json` must both
exist. Starting implementation without them is a workflow failure.

---

## Undeclared Source Paths

Any source or test edit outside `declared_paths` / `declared_globs` must produce
a scope warning. Non-high-risk undeclared edits still need an auditable scope
update or accepted guardrail override before they can be treated as intentional.

High-risk paths require the same declared scope plus extra scrutiny. Exact
directories such as `api`, `src/api`, `auth`, `src/auth`, `migrations`, and
`contracts` are high-risk even before choosing a child file.

If a high-risk edit is not declared, or is declared but missing from
`high_risk_allowed`, the hook should warn. The agent must either stop and update
the task scope through the normal workflow or record an allowed override when
the guardrail permits it.

---

## Override Ledger

Soft guardrail overrides must be written to:

```text
{TASK_DIR}/runtime/guardrail-overrides.jsonl
```

Each entry needs a timestamp, tool name, path, warning kind, decision, and
reason. An override is not approval to skip review, expand scope silently, or
finish without evidence.

`finish.md` must review the ledger and record a concrete decision. Empty values,
template placeholders, `N/A`, and missing reasons are not review evidence.

---

## Hard Blocks

Some states are not overrideable:

- source edits during planning phases
- missing required task artifacts
- finishing without required approval or review evidence
- writing Finish-phase artifacts before explicit Finish consent; the first
  `finish.md` write may proceed only when that same content records a complete
  `Finish Approval` section from the user's consent
- starting OMC `ulw/ultrawork` without explicit user approval, user message,
  and timestamp recorded in `implement.md`
- hard workflow phase mismatches

When a hard block fires, repair the task state or return to the correct phase.
Do not work around the hook.

---

## Review And Doctor

Reviewers must treat relevant guardrail regressions as blocking issues. The
doctor workflow must report missing scope manifests, unreviewed override
ledgers, phase mismatches, missing approval, missing checker/reviewer agent
results, placeholder review artifacts, and missing review gates with a concrete
next repair step.

---

**Core Principle**: scope can change only through auditable task evidence, not
through silent edits or final-chat explanations.
