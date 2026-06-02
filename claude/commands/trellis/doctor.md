Run a comprehensive health check on the Trellis setup. Diagnose hooks, templates, tasks, gates, naming, and active-task health. Output a structured report with PASS/WARN/FAIL per check.

**Steps:**

1. **Hooks registration** — Read `.claude/settings.json` and verify all 9 hooks are registered:
   - SessionStart → session-start.py
   - UserPromptSubmit → inject-workflow-state.py
   - PreToolUse → protect-dangerous-actions.py
   - PostToolUse → post-edit-reminder.py
   - SubagentStart → inject-subagent-context.py
   - SubagentStop → subagent-stop-guard.py
   - Stop → stop-guard.py + trellis-notify.sh
   - PreCompact → pre-compact-save-state.py
   - Notification → trellis-notify.sh
   For each: check the hook file exists under `.claude/hooks/` and is registered in settings.json.

2. **Skills registration** — Read `.claude/settings.json` skills section. Verify all 14 skills are registered and their SKILL.md files exist under `.claude/skills/`:
   - trellis-brainstorm, trellis-grill-me, trellis-dev-strategy, trellis-before-dev
   - trellis-implement, trellis-check, trellis-spec-review, trellis-code-review
   - trellis-code-architecture-review, trellis-improve-codebase-architecture
   - trellis-update-spec, trellis-break-loop, trellis-merge-review, trellis-finish-work

3. **Templates integrity** — Verify all template files exist under `.trellis/templates/`:
   - Task: prd.md.tmpl, design.md.tmpl, implement.md.tmpl, finish.md.tmpl, before-dev.md
   - Research: architecture-options, brainstorm, break-loop, decision-log, evidence, external-docs, grill-me, spike-results
   - Review: architecture-review, code-review, merge-review, spec-review
   - Validation: build-results.md.tmpl, commands.md.tmpl, test-results.md.tmpl

4. **Naming compatibility** — Check that NO file references `validation/results.md` (the deprecated name). The canonical names are:
   - `validation/test-results.md` — validation output (Phase 3.4)
   - `validation/check-results.md` — check gate output (Phase 2.2)
   Run: `grep -rn "validation/results\.md" .trellis/ .claude/ --include="*.py" --include="*.md" --include="*.json"` — must return empty.

5. **Trellis config** — Verify `.trellis/config/config.json` exists and has required fields.

6. **Active-task health** — Run `python3 .trellis/scripts/task.py current --source`:
   - If no active task: report NO_ACTIVE_TASK (info, not failure)
   - If active task exists:
     a. Read task.json — verify it has id, status, level fields
     b. Check status is a valid value (planning, in_progress, completed, done)
     c. Check for required artifacts per level:
        - L2: prd.md
        - L3: prd.md, implement.md
        - L4: prd.md, design.md, implement.md
        - L5: all of above + research/
     d. Check implement.md has Review Gate Contract section if it exists
     e. Check no stale state (active-task pointing to non-existent directory)

7. **Scripts availability** — Verify key scripts exist under `.trellis/scripts/`:
   - task.py, validate_task.py, validate_review_gates.py, validate_runtime_hardening.py

8. **Git state** — Check `git status --porcelain` for any uncommitted `.trellis/` or `.claude/` changes that might indicate incomplete setup.

**Output format:**

```
🔍 Trellis Doctor
═════════════════

Hooks:       9/9 registered ✅  (or: 7/9 ⚠️ missing: stop-guard, pre-compact)
Skills:      14/14 registered ✅  (or: 12/14 ⚠️ missing: trellis-break-loop, trellis-merge-review)
Templates:   18/18 present ✅  (or: 16/18 ⚠️ missing: validation/test-results.md.tmpl)
Naming:      ✅ No deprecated references
Config:      ✅ config.json present
Scripts:     5/5 present ✅
Git state:   ✅ Clean (or: ⚠️ 3 uncommitted setup files)

Active task: T001-hello-world (L2, planning)
  Artifacts: prd.md ✅ implement.jsonl ✅ check.jsonl ❌ missing
  Gates:     implement.md missing Review Gate Contract ⚠️

Overall: ⚠️ 2 warnings (or: ✅ All checks passed, or: ❌ 3 failures)
```

If any check fails, include a "To fix:" line for each failure.
