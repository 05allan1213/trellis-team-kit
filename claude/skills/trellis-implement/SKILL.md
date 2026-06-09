---
name: trellis-implement
description: "Implementation rules: only implement what is in PRD/design/implement scope. Don't expand scope. Don't commit. If design gaps are found, return to planning. Output changed files, summary, validation attempted, and unresolved risks."
---

# Trellis Implement

## Preconditions

- Before-dev gate has been passed (all artifacts and specs read).
- Task status is `in_progress`.
- Implementation consent has been obtained.

## Core Rules

### Scope Discipline

Only implement what is in the PRD, design, and implement scope. Do not expand scope. If you discover something that should be done but is not in scope, record it as a follow-up, not as an implementation addition.

### No Commit

Do not commit. Commits happen in Phase 3.2 after spec update decision and review gates pass.

### Design Gaps

If you find a design gap — something the PRD or design did not account for that affects implementation — do NOT guess. Return to planning. Record the gap and request clarification or a PRD/design update.

### Self-Exemption

If you are already running as a `trellis-implementer` sub-agent, implement directly. Do NOT spawn another implement sub-agent.

## Workflow

1. **Confirm before-dev constraints** are loaded.
2. **Implement in order** per `implement.md` steps.
3. **Run validation commands** from `implement.md` as you complete each step.
4. **If TDD is enabled** — write test first, then implement to pass.
5. **If design gap found** — stop, record the gap, return to planning.
6. **If scope ambiguity found** — implement the minimum viable interpretation and flag it.
7. **Run lint and type-check** before declaring implementation done.
8. **Output the implementation summary** in the required format.

## Output Format

The subagent-stop-guard validates this output format. It must contain all four
summary sections plus an explicit no-commit confirmation. The implementer must
also write `{TASK_DIR}/agent-results/trellis-implementer-<timestamp>.json`.

```markdown
## Implementation Summary

### Changed Files
- [file path]: [what changed and why]
- [file path]: [what changed and why]

### Summary
[1-3 sentences on what was implemented]

### Validation Attempted
- [command]: [result]
- [command]: [result]

### Unresolved Risks
- [risk]: [why unresolved, recommended next step]
- (or "none" if all risks are resolved)

### Did Not Commit
- Did not commit: yes
```

Required agent-result JSON fields: `version`, `agent`, `status`,
object-shaped `changed_files`, `validation`, and `blocking_issues`.

## Quality Bar

- No changes outside PRD/design/implement scope.
- No commits made.
- Lint and type-check attempted.
- Design gaps reported, not silently resolved.
- Output format includes changed files, summary, validation, risks, and did-not-commit confirmation.
- `agent-results/trellis-implementer-<timestamp>.json` exists and uses the required schema.
- Unresolved risks are explicit — do not hide them.
