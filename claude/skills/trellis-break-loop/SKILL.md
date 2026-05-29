---
name: trellis-break-loop
description: "Deep bug analysis to break the fix-forget-repeat cycle. Triggers when the same issue is fixed 2+ times, check repeatedly fails, review rejects 2+ times, root cause is an implicit assumption, bug propagates cross-layer, or missing test causes regression. Outputs to research/break-loop.md with root cause, failed attempts, and prevention."
---

# Trellis Break Loop

## Preconditions

One or more trigger conditions are met:
- Same issue fixed 2+ times
- Check repeatedly fails on the same problem
- Review rejects the same change 2+ times
- Root cause appears to be an implicit assumption
- Bug propagates across layers
- Missing test coverage caused a regression

## Core Rules

The value of debugging is not in fixing the bug — it is in making this class of bugs never happen again.

30 minutes of analysis saves 30 hours of future debugging.

The analysis is worthless if it stays in chat. The value is in the updated specs, guides, and regression tests.

## Workflow

1. **Classify the root cause** — which category does it belong to?
2. **Analyze failed attempts** — why did earlier fixes fail?
3. **Identify prevention mechanisms** — what would stop this class of bugs?
4. **Expand systematically** — where else might this problem exist?
5. **Take at least one durable action** — this is mandatory.
6. **Write findings** to `research/break-loop.md`.

### Step 1: Root Cause Category

| Category | Characteristics | Example |
|----------|-----------------|---------|
| **A. Missing Spec** | No documentation on how to do it | New feature without checklist |
| **B. Cross-Layer Contract** | Interface between layers unclear | API returns different format than expected |
| **C. Change Propagation Failure** | Changed one place, missed others | Changed function signature, missed call sites |
| **D. Test Coverage Gap** | Unit test passes, integration fails | Works alone, breaks when combined |
| **E. Implicit Assumption** | Code relies on undocumented assumption | Timestamp seconds vs milliseconds |

### Step 2: Why Fixes Failed

If multiple fix attempts were made, analyze each failure:

| Failure Type | Description |
|-------------|-------------|
| Surface Fix | Fixed symptom, not root cause |
| Incomplete Scope | Found root cause, didn't cover all cases |
| Tool Limitation | grep missed it, type check wasn't strict |
| Mental Model | Kept looking in same layer, didn't think cross-layer |

### Step 3: Prevention Mechanisms

| Type | Description | Example |
|------|-------------|---------|
| Documentation | Write it down so the team knows | Update thinking guide |
| Architecture | Make the error impossible structurally | Type-safe wrappers |
| Compile-time | Strict type checking, no escape hatches | Signature change causes compile error |
| Runtime | Monitoring, alerts, scans | Detect orphan entities |
| Test Coverage | E2E tests, integration tests | Verify full flow |
| Code Review | Checklist, PR template | "Did you check X?" |

### Step 4: Systematic Expansion

- **Similar Issues**: Where else might this problem exist?
- **Design Flaw**: Is there a fundamental architecture issue?
- **Process Flaw**: Is there a development process improvement?
- **Knowledge Gap**: Is the team missing some understanding?

### Step 5: Durable Action (Mandatory)

At least one of these must be completed. "No durable action needed" requires explicit justification.

- [ ] Update `.trellis/spec/` — add convention, pattern, or anti-pattern
- [ ] Update `.trellis/spec/guides/` — add thinking guide checklist item
- [ ] Add regression test — prevent the same bug from returning
- [ ] Create follow-up task — for systemic fixes that are out of current scope
- [ ] Explicitly record "no durable action needed" with reason

## Output Format

### research/break-loop.md

```markdown
# Break Loop Analysis: [Bug Description]

## Trigger
- [trigger condition that was met]

## Root Cause Category
- **Category**: [A/B/C/D/E] - [Category Name]
- **Specific Cause**: [Detailed description]

## Why Fixes Failed (if applicable)
1. [First attempt]: [Why it failed]
2. [Second attempt]: [Why it failed]

## Prevention Mechanisms
| Priority | Mechanism | Specific Action | Status |
|----------|-----------|-----------------|--------|
| P0 | [mechanism] | [action] | TODO/DONE |
| P1 | [mechanism] | [action] | TODO/DONE |

## Systematic Expansion
- **Similar Issues**: [Where else might this problem exist]
- **Design Improvement**: [Architecture-level suggestions]
- **Process Improvement**: [Development process suggestions]

## Durable Action
- [ ] [Action taken or "no durable action needed because X"]
- [ ] [Action taken]

## Spec/Guide Updates Made
- [file]: [what was updated]
- (or "none — no durable action needed because [reason]")
```

## Quality Bar

- Root cause is classified into one of the five categories.
- Failed fix attempts are analyzed honestly (no "it just didn't work").
- At least one durable action is taken (not just listed as TODO).
- If "no durable action needed", the reason is explicit and defensible.
- The analysis is written to `research/break-loop.md`, not left in conversation.
