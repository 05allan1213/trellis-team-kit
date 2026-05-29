---
name: trellis-update-spec
description: "Record whether spec updates are needed after a task. Must explain the decision even when no update is needed. Updates are required for new API contracts, env/config conventions, error handling rules, component patterns, bug fix revelations, unclear team rules, and new cross-layer data flows. Use during Phase 3.1 after all checks and reviews pass."
---

# Trellis Update Spec

## Preconditions

- `trellis-check` has passed.
- All selected review gates have passed.
- Code changes exist that may have spec implications.

## Core Rules

Every task MUST record a Spec Update Decision in `finish.md`. This is not optional.

Even if the decision is "no update needed", you MUST explain why. A decision without reasoning is incomplete.

### When Spec Update IS Needed

- New API contract or changed API contract
- New environment variable or configuration convention
- New error handling rule or pattern
- New component or module pattern
- Bug fix reveals a missing convention
- Review finds unclear team rules
- New cross-layer data flow pattern
- Design decision that future sessions need to know

### When Spec Update May NOT Be Needed

- Change is purely internal implementation with no reusable pattern
- Change follows existing specs exactly with no deviation
- No new patterns, contracts, or conventions were introduced
- Bug was a simple logic error with no systemic lesson

Even in these cases, explain why no update is needed. The explanation itself is the decision artifact.

## Workflow

1. **Review what changed** — read `git diff HEAD` and the task artifacts.
2. **Check each trigger** — does the change match any of the "when update IS needed" conditions?
3. **If yes** — identify which spec files need updating and what to add.
4. **If no** — articulate why no update is needed.
5. **Record the decision** in `finish.md`.
6. **If updating** — make the spec updates now, then record which files were updated.

### Spec Writing Rules

- Be specific and actionable — include code examples, not just abstract rules.
- Explain WHY, not just WHAT — future readers need to understand the reasoning.
- Show contracts — add signatures, payload fields, and error behavior.
- Keep it short — one concept per section.
- Do not duplicate — check if the spec already covers this before adding.
- Put "how to write" rules in spec layer directories, "what to consider" in `guides/`.

### Spec vs Guide Decision

| Content | Location |
|---------|----------|
| "This is how to write the code" | `.trellis/spec/<layer>/*.md` |
| "This is what to consider before writing" | `.trellis/spec/guides/*.md` |

## Output Format

### finish.md (Spec Update Decision section)

```markdown
## Spec Update Decision

Need spec update?
- [ ] yes
- [ ] no

Reason:
[Why or why not. Specific about what was learned or why nothing was learned that warrants capture.]

Updated files (if yes):
- .trellis/spec/[path]: [what was added/changed]
- .trellis/spec/[path]: [what was added/changed]
```

## Quality Bar

- The decision is recorded in `finish.md` — not just in conversation.
- "No update needed" includes a specific reason (not "nothing to update").
- If updating, the spec changes are actually made (not just listed as TODO).
- Spec changes follow the project's existing spec structure and style.
- No duplication — check existing specs before adding.
