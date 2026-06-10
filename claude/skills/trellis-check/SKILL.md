---
name: trellis-check
description: "Quality verification: git diff/status, lint, type-check, tests, no debug logs, no suppressed errors, no unsafe type bypass. Deep check for L4/L5 adds spec compliance, cross-layer data flow, API/schema/type consistency, and code reuse. Outputs PASS/FAIL with blocking issues."
---

# Trellis Check

## Preconditions

- Implementation is done (Phase 2.1 complete).
- Source code changes exist.

## Core Rules

Check is a gate. FAIL means return to IMPLEMENTING. Do not proceed to review gates or finish until check passes.

## Workflow

### Basic Check (L2-L3)

1. **Identify what changed**
   ```bash
   git diff --name-only HEAD
   git status
   ```

2. **Run project checks**
   - Linter
   - Type checker (if applicable)
   - Tests

3. **Read common mistakes** — if present, read `.trellis/spec/guides/ai-behavior/common-mistakes.md` before reviewing the diff.

4. **Review against checklist**

   #### Code Quality
   - [ ] Linter passes
   - [ ] Type checker passes
   - [ ] Tests pass
   - [ ] No debug logging left in (`console.log`, `print`, `debugger`, `TODO`, `HACK`)
   - [ ] No suppressed warnings or type-safety bypasses (`@ts-ignore`, `# type: ignore`, `eslint-disable`)

   #### Test Coverage
   - [ ] New function has unit test
   - [ ] Bug fix has regression test
   - [ ] Changed behavior has updated tests
   - [ ] Observable behavior is verified and the evidence is ready for `finish.md`

   #### Common Mistakes
   - [ ] Common mistakes regression: PASS/FAIL — documented workflow mistakes are not repeated in the current change

5. **Report and fix** — fix violations directly. Re-run checks after fixes.

6. **Write the check gate artifact** — save the gate report to
   `{TASK_DIR}/validation/check-results.md`.
   `validation/test-results.md` is reserved for the later finish-stage
   validation summary, not for Phase 2.2.
   When this check runs as `trellis-checker` or the selected execution mode uses
   Trellis subagents / Trellis-native parallel / OMC, also write
   `{TASK_DIR}/agent-results/trellis-checker-<timestamp>.json`.

### Deep Check (L4-L5)

In addition to the basic check, verify these dimensions:

7. **Read task artifacts and specs** — `prd.md`, `design.md`, `implement.md`, relevant spec files, and `.trellis/spec/guides/ai-behavior/common-mistakes.md`.

8. **Spec compliance** — does the implementation follow `.trellis/spec/` guidelines?

9. **Cross-layer data flow** (changes touch 3+ layers)
   - [ ] Read flow traces correctly: Storage -> Service -> API -> UI
   - [ ] Write flow traces correctly: UI -> API -> Service -> Storage
   - [ ] Types/schemas correctly passed between layers
   - [ ] Errors properly propagated to caller

10. **API/schema/type consistency**
   - [ ] API contracts match between frontend and backend
   - [ ] Database schema matches ORM/entity definitions
   - [ ] Shared types are consistent across packages

11. **Import/dependency direction**
   - [ ] No circular dependencies
   - [ ] Correct import paths (relative vs absolute)
   - [ ] Dependencies point inward (toward core, not toward periphery)

12. **Same-concept consistency**
    - [ ] Other places using the same concept are consistent
    - [ ] No duplicate definitions of the same constant or type

13. **Code reuse search**
    ```bash
    grep -r "pattern" src/
    ```
    - [ ] Searched for existing similar code before creating new
    - [ ] If 2+ places define same value, extracted to shared constant
    - [ ] After batch modification, all occurrences updated

14. **Edge cases** — does the implementation handle boundary conditions per the PRD?

15. **Test coverage depth**
    - [ ] Happy path tested
    - [ ] Error paths tested
    - [ ] Boundary conditions tested
    - [ ] Integration between changed components tested

16. **Rollback safety**
    - [ ] Changes can be reverted without data loss
    - [ ] Migration (if any) has a rollback path

## Output Format

Write to `{TASK_DIR}/validation/check-results.md`:

```markdown
# Check Results: [Task Title]

## Changed Files
- [file]: [status]

## Basic Check
- Linter: PASS/FAIL — [details]
- Type check: PASS/FAIL — [details]
- Tests: PASS/FAIL — [details]
- Debug logs: PASS/FAIL — [details]
- Suppressed errors: PASS/FAIL — [details]
- Common mistakes regression: PASS/FAIL — [details]

## Deep Check (L4/L5 only)
- Spec compliance: PASS/FAIL — [details]
- Cross-layer data flow: PASS/FAIL — [details]
- API/schema consistency: PASS/FAIL — [details]
- Import direction: PASS/FAIL — [details]
- Same-concept consistency: PASS/FAIL — [details]
- Code reuse: PASS/FAIL — [details]
- Edge cases: PASS/FAIL — [details]
- Test coverage: PASS/FAIL — [details]
- Rollback safety: PASS/FAIL — [details]

## Observable Verification
- [observable outcome]: PASS/FAIL — [how verified]

## Verdict
- [x] PASS — all checks pass
- [ ] FAIL — blocking issues:
  1. list each concrete blocker

## Fixes Applied
- None.
```

## Quality Bar

- All applicable checks are run (basic for L2-L3, deep for L4-L5).
- FAIL verdict includes specific blocking issues with file references.
- Fixes are applied and re-checked before reporting.
- A repeated documented common mistake is a blocking FAIL when it affects the current change.
- No debug logging, suppressed errors, or unsafe type bypasses remain.
- Observable behavior is checked alongside build/test and captured as evidence.
- The verdict is honest — do not soften a FAIL into a PASS.
- Subagent-mode checks are not complete until the `trellis-checker` agent result
  JSON exists and validates.
