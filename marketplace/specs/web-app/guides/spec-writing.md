# Spec Writing

## Purpose

This guide defines how this repository writes and updates Trellis specs.

Specs are long-lived team conventions that future AI agents should follow before coding. They are not task notes, chat summaries, or generic best-practice essays.

## When to Use

Use this guide when:

* Creating a new spec
* Updating an existing spec
* Running `trellis-update-spec`
* Deciding whether a task lesson should become a team rule
* Splitting or cleaning up an existing spec

Do not use this guide to define workflow phases. `workflow.md` owns the Trellis lifecycle.

Do not use this guide to route all specs. Directory `index.md` files own routing for their own area.

## Core Rules

1. Write specs from real project conventions.
2. Prefer concrete rules over abstract advice.
3. Prefer examples and anti-examples when code shape matters.
4. Keep each spec focused on one responsibility.
5. Update existing specs before creating new ones.
6. Remove stale or duplicated rules.
7. Do not store one-task-only knowledge in specs.

## What Belongs in Spec

Add a rule to spec when it should affect future tasks.

Good candidates:

* Repeated project convention
* Reusable implementation pattern
* Bug prevention rule
* Architecture decision
* Testing requirement
* Review requirement
* Error-handling rule
* Directory or naming convention
* Security or data-safety rule

A spec update should help a future agent avoid asking the same question or making the same mistake.

## What Does Not Belong in Spec

Do not add:

* One-off task requirements
* Temporary implementation notes
* Raw chat history
* Prompt templates
* Generic advice
* Unverified guesses
* Large copied documentation
* Session summaries
* Details that only explain what happened once

Use task files or journal for those.

## Placement

Place rules by scope:

```text
spec/backend/   → backend code conventions
spec/frontend/  → frontend code conventions
spec/guides/    → cross-layer thinking and spec-maintenance guides
```

Use the most specific existing file that fits.

Create a new spec only when no existing file has the right scope.

If a new file is created, update the relevant directory `index.md`.

## Index Files

Directory `index.md` files should stay short.

They should explain:

* What specs exist in this directory
* When each spec should be read
* Any short checklist needed before work

They should not contain all detailed rules.

Move detailed rules into focused spec files.

## Spec Shape

Most specs should follow this shape:

```markdown
# <Spec Name>

## Purpose

## When to Use

## Rules

## Examples

## Anti-Patterns

## Quality Check
```

Small specs may omit sections that do not add value.

Every spec should still answer:

* When should AI read this?
* What must AI do?
* What must AI avoid?
* How can compliance be checked?

## Rule Quality

A good rule has:

* Trigger: when it applies
* Action: what to do
* Constraint: what not to do
* Check: how to verify it

Prefer:

```markdown
When adding an auth-protected API route, add tests for both allowed and denied access.
Do not only test the happy path.
Check that unauthorized requests fail with the expected error shape.
```

Avoid:

```markdown
Test auth carefully.
```

Avoid vague words unless they are defined:

* good
* clean
* proper
* robust
* scalable
* user-friendly
* production-ready

## Examples

Use examples when the rule affects structure, naming, data shape, or control flow.

Keep examples short.

Prefer:

```markdown
Good: validate input at the route boundary, then pass typed data into service code.
Bad: pass raw request bodies deep into business logic.
```

Do not paste large code blocks unless the exact structure is the rule.

## Size

Keep specs short enough to load when needed.

Team target:

* Ideal: 60–150 lines
* Review carefully: over 180 lines
* Split or simplify: over 220 lines

A spec may be longer only when it is still focused and highly useful.

## Updating Specs

Before updating:

1. Read the relevant directory `index.md`
2. Read the closest existing spec
3. Check whether the rule already exists
4. Edit existing wording when possible
5. Add a new rule only when needed

When updating:

* Add the smallest useful rule
* Make it concrete
* Keep examples current
* Remove stale wording
* Avoid duplicate rules

## Creating New Specs

Create a new spec only when:

* The rule has a distinct scope
* Existing specs would become confusing if expanded
* Future routing becomes clearer with a separate file

Do not create a new spec just because one task was difficult.

## Finish Judgment

During Finish, always decide whether `trellis-update-spec` is needed.

Update spec when the task revealed:

* A reusable convention
* A repeated mistake
* A missing check
* A new decision
* A bug pattern worth preventing

Do not update spec when the task only produced:

* One-off product details
* Temporary workaround notes
* Task-specific implementation choices
* Information already covered elsewhere

If no update is needed, say why.

## Review Checklist

Before accepting a spec change, check:

* Is this useful beyond the current task?
* Is it in the right file?
* Is it concrete?
* Is it checkable?
* Does it duplicate another rule?
* Does the relevant `index.md` need an update?
* Is the spec still short and focused?

## Final Rule

A spec should reduce future prompting.

If a rule does not make future AI behavior more reliable, do not add it.
