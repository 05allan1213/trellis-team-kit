# Review Thinking Guide

> **Purpose**: Help AI assistants perform effective, honest code review — not just rubber-stamp changes.

---

## Why Review Thinking?

AI-generated code passes through multiple agents (implementer → checker → reviewers). Each handoff is an opportunity to catch issues. But reviewers that just say "looks good" waste everyone's time.

This guide helps AI reviewers ask the right questions and produce actionable findings.

---

## Review Mindset

A reviewer's job is to **protect the codebase**, not to be nice to the diff.

- Be direct and evidence-driven
- Cite file:line for every finding
- Separate blocking issues from non-blocking nits
- Don't inflate theoretical concerns into blockers
- Don't let real issues slide to avoid conflict

---

## Review Layers

### Layer 1: Correctness (always)

- Does the change do what the PRD says?
- Are acceptance criteria actually met?
- Are there obvious logic errors?
- Does it handle edge cases mentioned in the PRD?

### Layer 2: Safety (always)

- Are there security concerns (injection, exposed secrets, auth bypass)?
- Can this change break existing behavior?
- Is error handling appropriate?
- Are there debug logs, suppressed errors, or unsafe type bypasses left in?

### Layer 3: Consistency (L3-L5)

- Does the code follow existing patterns in the codebase?
- Are naming conventions consistent?
- Is there duplicated logic that should be shared?
- Does it match the specs in `.trellis/spec/`?

### Layer 4: Architecture (L4/L5)

- Are module boundaries respected?
- Is the dependency direction correct?
- Are there layering violations?
- Is the API contract clear and consistent?
- Are there duplicated concepts across modules?

---

## Output Format

Every review must produce at least:

```markdown
## Verdict

- [x] PASS
- [ ] FAIL

### Blocking Issues
- `file:line` — what is wrong
  - Why blocker: concrete failure mode
  - Fix: 1-2 line direction

### Non-Blocking Issues
- `file:line` — what could be improved
  - Why non-blocking: not a correctness issue

### Good Choices
- Non-obvious good decisions worth noting

### Validation
- lint: pass | fail | not run
- typecheck: pass | fail | not run
- tests: pass | fail | not run
```

For Trellis review gates, this is only the minimum review-thinking shape. Use
the specific `review/*.md` template or reviewer agent instructions for the gate
being run, and write `agent-results/*.json` when a subagent performs the review.

---

## Red Flags for Reviewers

| What you're thinking | Why it's wrong |
|---|---|
| "The implementer probably checked this" | The implementer's job was to write, yours is to verify |
| "This looks fine, I'll just approve" | Every review should find at least one thing — even if it's a "good choices" note |
| "This is too small to review carefully" | Small changes cause big bugs when they touch shared paths |
| "I'll just fix it myself" | Report findings; don't silently rewrite. The implementer learns from feedback |
| "This theoretical concern should block" | Only block on concrete failure modes, not "what if" scenarios |

---

## How to Use

1. **After implementation (L3-L5)**: Load this guide before running `trellis-code-review` or `trellis-spec-review`
2. **Before merge (L4/L5)**: Use as lens for `trellis-merge-review`
3. **When review fails repeatedly**: The review itself may be wrong — check if the PRD or design is the real issue

---

**Core Principle**: A review that finds nothing is either reviewing trivial code or not looking hard enough. Be the reviewer you'd want reviewing your own PR.
