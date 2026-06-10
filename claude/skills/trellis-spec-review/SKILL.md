---
name: trellis-spec-review
description: "Check whether changes violate .trellis/spec/, miss necessary specs, bypass conventions, or need update-spec. Outputs to review/spec-review.md with PASS/FAIL. Use as a review gate when selected in the Review Gate Contract."
---

# Trellis Spec Review

## Preconditions

- `trellis-check` has passed.
- Spec review is selected in the Review Gate Contract.

## Core Rules

Spec review checks whether the implementation respects the project's documented conventions. It does not check code quality (that is `trellis-code-review`) or architecture (that is `trellis-code-architecture-review`).

## Workflow

1. **Read changed files** — `git diff --name-only HEAD`.
2. **Identify which specs apply** — based on changed packages and layers.
3. **Read the relevant spec files** — start from `.trellis/spec/index.md`, then read the specific guideline files.
4. **Check each dimension** below.
5. **Write findings** to `review/spec-review.md`.

### Dimensions

#### Convention Violations

- Do the changed files follow the coding conventions in `.trellis/spec/`?
- Are naming conventions followed (file names, variable names, function names)?
- Are directory structure conventions followed?
- Are error handling patterns followed per spec?
- Are logging patterns followed per spec?

#### Missing Specs

- Did the implementation introduce a new pattern that has no spec coverage?
- Is there a new component/module type that should be documented?
- Is there a new error category that should be in the error handling spec?

#### Bypassed Conventions

- Did the implementation use `// eslint-disable`, `@ts-ignore`, `# type: ignore`, or similar suppression?
- Did the implementation use a different pattern than what the spec prescribes?
- Did the implementation skip a required validation or transformation?

#### Update-Spec Needed?

- Does this change establish a new convention that should be captured?
- Does this change make an existing spec inaccurate?
- Does this change add a new API contract or data shape?

## Output Format

### review/spec-review.md

```markdown
# Spec Review: Task Title

## Spec Files Checked
- `.trellis/spec/guides/index.md`: relevant guidance checked

## Convention Violations
- None.

## Missing Specs
- None.

## Bypassed Conventions
- None.

## Update-Spec Needed
- [ ] yes — reusable rule identified
- [x] no — no reusable spec update needed

## Verdict
- [x] PASS — no spec violations
- [ ] FAIL — violated spec files:
  1. list each violated spec and concrete violation
```

## Quality Bar

- All relevant spec files are checked (not just the index).
- Violations cite specific spec files and sections.
- "No violation found" is honest — do not invent concerns.
- FAIL verdict lists violated spec files explicitly.
- If update-spec is needed, it is specific about what to update.
- Do not leave placeholder text, HTML comments, or bracket/angle examples in the
  final `review/spec-review.md`; write `None.` for empty sections.
