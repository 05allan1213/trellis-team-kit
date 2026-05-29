---
name: trellis-finish-work
description: "Finalize a completed task: verify gates passed, archive task, update workspace journal, update task index, summarize commits/PR, record follow-ups, and mark task done. Does NOT write code, fix bugs, bypass failed gates, or auto-push. Rejects if preconditions are not met."
---

# Trellis Finish Work

## Preconditions

ALL of the following must be satisfied:

1. Implementation is complete.
2. `trellis-check` has PASS.
3. Selected review gates have PASS.
4. Spec update decision is recorded in `finish.md`.
5. Code is committed, or PR is created, or explicitly no commit needed.
6. Build/test PASS, or reason for inability is recorded.

Any missing precondition — finish-work refuses to execute.

## Core Rules

### What Finish-Work DOES

1. Verify all preconditions are met.
2. Archive the task.
3. Update the workspace journal.
4. Update the task index.
5. Summarize commits and PR.
6. Record follow-ups.
7. Mark task done.

### What Finish-Work Does NOT Do

- Write code — implementation is done before finish-work runs.
- Fix bugs — bugs must be fixed before finish-work runs.
- Bypass failed gates — failed gates must pass before finish-work runs.
- Auto-push — push is always manual and requires explicit user action.
- Commit code — commits happen in Phase 3.2, before finish-work.
- Make spec update decisions — those happen in Phase 3.1, before finish-work.

## Workflow

1. **Verify preconditions** — check each of the six items listed above.
2. **If any precondition fails** — reject with a clear message stating what is missing.
3. **If all preconditions pass** — proceed with the following steps.

### Step 1: Verify Preconditions

```
Implementation complete? [YES/NO]
trellis-check PASS? [YES/NO]
Review gates PASS? [YES/NO]
Spec update decision recorded? [YES/NO]
Code committed? [YES/NO / N/A with reason]
Build/test PASS? [YES/NO / N/A with reason]
```

Any NO — stop and report what is missing.

### Step 2: Archive Task

```bash
python3 ./.trellis/scripts/task.py archive <task-dir>
```

### Step 3: Update Workspace Journal

Add an entry to the workspace journal summarizing:
- What was accomplished
- Key decisions made
- Specs updated (if any)
- Follow-ups recorded (if any)

### Step 4: Update Task Index

Ensure the task is marked as done in the task index.

### Step 5: Summarize Commits/PR

List the commits made during this task:
```
[commit hash] [commit message]
[commit hash] [commit message]
```

If a PR was created, include the PR URL.

### Step 6: Record Follow-ups

If any follow-up items were identified (out-of-scope items, future improvements, known limitations), record them.

### Step 7: Mark Task Done

The task is now DONE. No further changes should be made to this task.

## Output Format

### finish.md (complete)

```markdown
# Finish: [Task Title]

## Preconditions Verification
- Implementation complete: YES
- trellis-check PASS: YES
- Review gates PASS: YES
- Spec update decision recorded: YES
- Code committed: YES / N/A: [reason]
- Build/test PASS: YES / N/A: [reason]

## Spec Update Decision
Need spec update?
- [ ] yes — [what was updated]
- [ ] no — [reason]

## Commits
- [hash] [message]

## PR (if applicable)
- [PR URL]

## Summary
[1-3 sentences on what was accomplished]

## Follow-ups
- [follow-up item] — [priority]
- (or "none")

## Journal Entry
[What was accomplished, key decisions, specs updated, follow-ups]
```

## Quality Bar

- All six preconditions are verified before proceeding.
- If any precondition fails, finish-work is rejected with a clear message.
- No code changes are made during finish-work.
- No failed gates are bypassed.
- No auto-push occurs.
- The task is archived and marked done.
- Follow-ups are recorded, not lost.
