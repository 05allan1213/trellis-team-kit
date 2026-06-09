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
4. `finish.md` records the explicit Finish Approval from the user.
5. Spec update decision is recorded in `finish.md`.
6. Observable outcomes are recorded in `finish.md` with verification evidence.
7. Delivery Sync Check is recorded in `finish.md`.
8. Merge review has PASS when required.
9. Code is committed, or PR is created, or explicitly no commit needed.
10. Build/test PASS, or reason for inability is recorded.

Any missing precondition — finish-work refuses to execute.

## Core Rules

### What Finish-Work DOES

1. Verify all preconditions are met.
2. Run the team-kit archive wrapper.
3. Re-open the archived task and validate the archived artifacts.
4. Update the workspace journal.
5. Update the task index.
6. Summarize commits and PR.
7. Record follow-ups.
8. Mark task done.

### What Finish-Work Does NOT Do

- Write code — implementation is done before finish-work runs.
- Fix bugs — bugs must be fixed before finish-work runs.
- Bypass failed gates — failed gates must pass before finish-work runs.
- Auto-push — push is always manual and requires explicit user action.
- Commit code — commits happen in Phase 3.2, before finish-work.
- Make spec update decisions — those happen in Phase 3.1, before finish-work.

## Workflow

1. **Verify preconditions** — check each of the ten preconditions listed above.
2. **If any precondition fails** — reject with a clear message stating what is missing.
3. **If all preconditions pass** — proceed with the following steps.

### Step 1: Verify Preconditions

```
Implementation complete? [YES/NO]
trellis-check PASS? [YES/NO]
Review gates PASS? [YES/NO]
Finish Approval recorded? [YES/NO]
Spec update decision recorded? [YES/NO]
Observable outcomes recorded? [YES/NO]
Delivery Sync Check recorded? [YES/NO]
Merge review PASS when required? [YES/NO / N/A]
Code committed? [YES/NO / N/A with reason]
Build/test PASS? [YES/NO / N/A with reason]
```

Any NO — stop and report what is missing.

### Step 2: Archive Task

```bash
python3 ./.trellis/scripts/finalize_task_archive.py <task-dir>
```

### Step 3: Validate Archived Artifacts

The archive wrapper must leave the archived task in a validator-clean state:

```bash
python3 ./.trellis/scripts/validate_task.py <archived-task-dir>
python3 ./.trellis/scripts/validate_review_gates.py <archived-task-dir>
python3 ./.trellis/scripts/validate_agent_results.py <archived-task-dir>
python3 ./.trellis/scripts/validate_workflow_state.py <archived-task-dir>
```

Required post-archive checks:
- `task.json` still contains `level`
- `implement.jsonl` / `check.jsonl` still resolve after archive
- JSONL still contains only spec/research context, not duplicated task artifacts
- `agent-results/*.json` is valid when merge-review / parallel / OMC execution requires it
- journal / workspace index entries are updated with real commit information
- no `.omc/state/*` runtime state files remain in the tracked dirty set

If any validator fails, finish-work is not complete yet.

### Step 4: Update Workspace Journal

Add an entry to the workspace journal summarizing:
- What was accomplished
- Key decisions made
- Specs updated (if any)
- Follow-ups recorded (if any)
- Real commits made for this task (do not leave placeholder text)

### Step 5: Update Task Index

Ensure the task is marked as done in the task index.

### Step 6: Summarize Commits/PR

List the commits made during this task:
```
[commit hash] [commit message]
[commit hash] [commit message]
```

If a PR was created, include the PR URL.

### Step 7: Record Follow-ups

If any follow-up items were identified (out-of-scope items, future improvements, known limitations), record them.

### Step 8: Mark Task Done

The task is now DONE. No further changes should be made to this task.

## Output Format

### finish.md (complete)

```markdown
# Finish: [Task Title]

## Preconditions Verification
- Implementation complete: YES
- trellis-check PASS: YES
- Review gates PASS: YES
- Finish Approval recorded: YES
- Spec update decision recorded: YES
- Observable outcomes recorded: YES
- Delivery Sync Check recorded: YES
- Code committed: YES / N/A: [reason]
- Build/test PASS: YES / N/A: [reason]

## Spec Update Decision
Need spec update?
- [ ] yes — [what was updated]
- [ ] no — [reason]

## Finish Approval
Approval status:
- [x] approved

Approval source:
- user message: [exact user message entering Finish]
- timestamp: [timestamp]
- summary approved: [short summary]

Allowed to proceed with finish?
- [x] yes
- [ ] no

## Observable Outcomes
- [outcome] — [evidence]
- [outcome] — [evidence]

## Delivery Sync Check
- [x] README / user docs reviewed
- [x] Example commands / scripts reviewed
- [x] Public API paths / contracts reviewed
- [x] Implemented vs planned status reviewed

Files checked:
- [file] — [what was verified]

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

- All seven preconditions are verified before proceeding.
- If any precondition fails, finish-work is rejected with a clear message.
- No code changes are made during finish-work.
- No failed gates are bypassed.
- No auto-push occurs.
- Archived artifacts still pass validators after archive.
- The task is archived and marked done.
- Follow-ups are recorded, not lost.
