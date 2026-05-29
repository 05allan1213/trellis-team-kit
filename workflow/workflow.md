# Development Workflow

---

## Core Principles

1. **Plan before code** — figure out what to do before you start
2. **Specs injected, not remembered** — guidelines are injected via hook/skill, not recalled from memory
3. **Persist everything** — research, decisions, and lessons all go to files; conversations get compacted, files don't
4. **Incremental development** — one task at a time
5. **Capture learnings** — after each task, review and write new knowledge back to spec
6. **Trellis owns lifecycle** — task state, PRD, acceptance criteria, check, finish, and spec update stay under Trellis
7. **Superpowers extends reasoning** — use it for unclear, complex, architectural, or repeatedly failing work; skip it for genuinely small, clear tasks
8. **oh-my-claudecode extends execution** — use it only as a multi-agent parallel execution layer when the PRD is confirmed, the user explicitly approves parallel mode, and the work can be safely split
9. **Scenario tools stay scenario-triggered** — MCPs, domain skills, browser tools, frontend-design, testing, debugging, and review rules load only when the task calls for them

---

## Team Workflow Extensions

This repository uses the official Trellis workflow as the base state machine, with two always-available extensions:

- **Superpowers** is a reasoning workflow extension. It may be used in any phase, but is mandatory only when reasoning quality matters: unclear requirements, multiple viable plans, architecture tradeoffs, cross-module impact, repeated failures, or contradictions found during check. It is not required for small, explicit, low-risk changes.
- **oh-my-claudecode** is a parallel execution extension. It may be used in Execute and Check only when the confirmed PRD can be split across independent agents and the user explicitly confirms parallel mode. It must not decide scope, bypass Plan, bypass Check, or replace Trellis task state.
- **MCPs and domain skills** are scenario capabilities. They are not globally loaded. Use them only when the task domain requires external facts, browser verification, design work, debugging, testing, review, or other specialized capability.
- **Specs remain the team standard source.** The workflow routes to specs; it must not duplicate every scenario rule. For task-specific rules, start from `.trellis/spec/index.md` and load only the relevant files.

Authority model:

```text
Trellis owns lifecycle.
PRD owns scope.
Acceptance Criteria own completion.
Specs own team standards.
Superpowers owns deep reasoning.
oh-my-claudecode owns parallel execution.
MCPs and Skills own scenario capability.
The main agent owns integration and final responsibility.
```

---

## Task Level Routing (L0-L5)

All tasks are classified by complexity to avoid over-engineering small tasks or under-engineering large ones.

| Level | Type | Create Trellis task | Required artifacts | Execution mode | Required gates |
| ----- | ---- | ------------------: | ------------------ | -------------- | -------------- |
| L0 | Pure Q&A / explanation / analysis | No | None | Main session direct answer | None |
| L1 | Tiny change / typo / copy | Optional | Skippable, user confirms | Main session | Light check |
| L2 | Light implementation | Yes | `prd.md` | Main session or subagent | `trellis-check` |
| L3 | Normal feature / bugfix | Yes | `prd.md` + `implement.md`, optionally `design.md` | subagent | check + code-review |
| L4 | Complex cross-layer / API / schema / auth / infra | Yes | `prd.md` + `design.md` + `implement.md` + research | subagent + worktree / OMC | check + spec-review + code-review + architecture-review |
| L5 | Multi-agent / parent-child / large refactor / architecture | Yes | Full artifacts | OMC + worktree + parent/child task | All gates + merge-review |

### Triage Rules

- **L0 (pure Q&A)**: answer directly, no task
- **L1 (tiny change)**: user must explicitly say "skip trellis" / "no task" / "just do it" / "don't create a task"
- **L2-L5 (implementation)**: default to creating a Trellis task, follow Plan → Execute + Check + Review → Finish

**The AI must NOT decide "it's small so no task" on its own.**

---

## Dual Consent Gates

**Task creation approval is not implementation approval.**

1. **Task Creation Consent**: user agrees to create a task → enter planning only. Do NOT edit source code.
2. **Implementation Consent**: user explicitly says "start implementation" / "approve implementation" / "begin coding" → then `task.py start` and write code.

### Forbidden

- Without task creation consent → no `task.py create`
- Without implementation consent → no source editing, no implementer spawn, no `task.py start`
- Source changes during planning → hook blocks or strongly warns

---

## Complete State Machine

```text
NO_TASK
  → TRIAGE (classify request)
    → TASK_CREATED (task.py create)
      → PLANNING_PRD (brainstorm)
        → PLANNING_GRILL (grill-me)
          → PLANNING_DESIGN (design.md for complex tasks)
            → PLANNING_IMPLEMENT (implement.md + review gate contract)
              → WAITING_IMPLEMENTATION_APPROVAL
                → IN_PROGRESS (task.py start)
                  → BEFORE_DEV (read artifacts/specs)
                    → IMPLEMENTING
                      → CHECKING
                        → REVIEWING (spec/code/architecture review gates)
                          → UPDATING_SPEC
                            → COMMITTING
                              → MERGE_REVIEWING (complex tasks)
                                → VALIDATING (build/test)
                                  → FINISHING (archive + journal)
                                    → DONE
```

---

## State Definitions

### NO_TASK
- **Description**: No active task
- **Entry condition**: Session start or no active task
- **Required files**: None
- **Allowed**: Answer L0 questions, triage
- **Forbidden**: Create task (need consent first), edit source (unless L1 explicitly allowed)
- **Exit condition**: Task creation consent obtained or L0/L1 confirmed
- **Next state**: TRIAGE

### TRIAGE
- **Description**: Classify the request
- **Entry condition**: User makes a request
- **Required files**: None
- **Allowed**: Analyze complexity, suggest task level
- **Forbidden**: Create task, edit source
- **Exit condition**: Classification done, user consent obtained
- **Next state**: TASK_CREATED (L2-L5), direct answer (L0), or inline (L1)

### TASK_CREATED
- **Description**: Task created, status = planning
- **Entry condition**: `task.py create` succeeded
- **Required files**: `task.json`
- **Allowed**: Read code, explore repo, write prd.md
- **Forbidden**: Edit source, `task.py start`
- **Exit condition**: prd.md being populated
- **Next state**: PLANNING_PRD
- **Triggerable skills**: `trellis-brainstorm`

### PLANNING_PRD
- **Description**: Requirements clarification
- **Entry condition**: Started filling prd.md
- **Required files**: `prd.md` (at minimum: Problem/Scope/AC)
- **Allowed**: Brainstorm, research, read code evidence, update prd.md
- **Forbidden**: Edit source, `task.py start`, skip evidence and ask user directly
- **Exit condition**: prd.md has verifiable Acceptance Criteria
- **Next state**: PLANNING_GRILL
- **Triggerable skills**: `trellis-brainstorm`, `trellis-researcher` (subagent)

### PLANNING_GRILL
- **Description**: PRD challenge phase
- **Entry condition**: prd.md has basic AC
- **Required files**: `prd.md`, `research/grill-me.md`
- **Allowed**: Check AC testability, boundaries, risks, scope creep
- **Forbidden**: Edit source, `task.py start`
- **Exit condition**: Grill-me complete, PRD Risks/Open Questions/Out of Scope updated
- **Next state**: PLANNING_DESIGN (L3+) or PLANNING_IMPLEMENT (L2)
- **Triggerable skills**: `trellis-grill-me`

### PLANNING_DESIGN
- **Description**: Technical design (L3+)
- **Entry condition**: PRD is solid
- **Required files**: `design.md` (required for L4/L5)
- **Allowed**: Architecture design, contract definition, data flow, alternatives
- **Forbidden**: Edit source, `task.py start`
- **Exit condition**: design.md complete (optional L3, required L4/L5)
- **Next state**: PLANNING_IMPLEMENT
- **Triggerable skills**: `trellis-improve-codebase-architecture guidance`, `trellis-research`

### PLANNING_IMPLEMENT
- **Description**: Execution planning
- **Entry condition**: PRD + design (if needed) done
- **Required files**: `implement.md` (with Development Strategy + Review Gate Contract)
- **Allowed**: Decide execution mode, configure review gates, curate JSONL
- **Forbidden**: Edit source, `task.py start`
- **Exit condition**: implement.md done, review gate contract configured, JSONL curated
- **Next state**: WAITING_IMPLEMENTATION_APPROVAL
- **Triggerable skills**: `trellis-dev-strategy`

### WAITING_IMPLEMENTATION_APPROVAL
- **Description**: Waiting for user to approve implementation
- **Entry condition**: Planning artifacts complete
- **Required files**: `prd.md`, `implement.md` (+ `design.md` for L4/L5)
- **Allowed**: Present planning artifacts, wait for user confirmation
- **Forbidden**: Edit source, spawn implementer, `task.py start`
- **Exit condition**: User explicitly approves implementation
- **Next state**: IN_PROGRESS (via `task.py start`)

### IN_PROGRESS
- **Description**: Task status = in_progress
- **Entry condition**: `task.py start` succeeded
- **Required files**: Same as WAITING_IMPLEMENTATION_APPROVAL
- **Allowed**: before-dev reading
- **Forbidden**: Write code directly (must pass BEFORE_DEV first)
- **Exit condition**: before-dev complete
- **Next state**: BEFORE_DEV
- **Triggerable skills**: `trellis-before-dev`

### BEFORE_DEV
- **Description**: Pre-implementation context loading
- **Entry condition**: task status = in_progress
- **Required files**: Read prd.md, design.md, implement.md, JSONL, specs, research
- **Allowed**: Read all relevant artifacts and specs
- **Forbidden**: Edit source
- **Exit condition**: Context loaded, constraints clear
- **Next state**: IMPLEMENTING
- **Triggerable skills**: `trellis-before-dev`

### IMPLEMENTING
- **Description**: Code implementation
- **Entry condition**: before-dev done
- **Required files**: None new
- **Allowed**: Subagent/OMC implement code, run lint/typecheck
- **Forbidden**: Commit, push, expand scope, self-finish-work
- **Exit condition**: Implementation done, output changed files/summary/validation/unresolved risks
- **Next state**: CHECKING
- **Triggerable skills**: `trellis-implement` (subagent) or OMC parallel agents

### CHECKING
- **Description**: Quality check
- **Entry condition**: Implementation done
- **Required files**: `validation/test-results.md`
- **Allowed**: Lint, typecheck, tests, spec compliance, cross-layer check
- **Forbidden**: Commit, push
- **Exit condition**: Check PASS or FAIL with blocking issues recorded
- **Next state**: REVIEWING (if review gates enabled) or UPDATING_SPEC (check-only)
- **Triggerable skills**: `trellis-check`

### REVIEWING
- **Description**: Review phase (per Review Gate Contract)
- **Entry condition**: Check PASS
- **Required files**: `review/spec-review.md`, `review/code-review.md`, `review/architecture-review.md` (per contract)
- **Allowed**: Review spec/code/architecture, output PASS/FAIL
- **Forbidden**: Skip failed gate, proceed to finish directly
- **Exit condition**: All selected gates PASS
- **Next state**: UPDATING_SPEC (all PASS) or IMPLEMENTING (any FAIL)
- **Triggerable skills**: `trellis-spec-review`, `trellis-code-review`, `trellis-code-architecture-review`, `trellis-improve-codebase-architecture deep-review`

### UPDATING_SPEC
- **Description**: Spec update decision
- **Entry condition**: Check + selected reviews PASS
- **Required files**: `finish.md` (with Spec Update Decision)
- **Allowed**: Judge whether spec update needed, execute update
- **Forbidden**: Skip decision
- **Exit condition**: Spec Update Decision recorded
- **Next state**: COMMITTING
- **Triggerable skills**: `trellis-update-spec`

### COMMITTING
- **Description**: Commit phase
- **Entry condition**: Spec update decision done
- **Required files**: None new
- **Allowed**: git status, classify dirty files, draft commit plan, wait for confirmation, commit
- **Forbidden**: Push, amend, commit unrelated files, auto-commit without confirmation
- **Exit condition**: Code committed or user chooses manual commit
- **Next state**: MERGE_REVIEWING (L4/L5/multi-agent/OMC/worktree) or VALIDATING

### MERGE_REVIEWING
- **Description**: Post-merge review (L4/L5/multi-agent)
- **Entry condition**: Commit done, task used worktree/OMC/multi-subagent/parent-child
- **Required files**: `review/merge-review.md`
- **Allowed**: Check conflicts, duplicate implementations, missing files, interface consistency
- **Forbidden**: Skip
- **Exit condition**: Merge-review PASS
- **Next state**: VALIDATING
- **Triggerable skills**: `trellis-merge-review`

### VALIDATING
- **Description**: Final validation
- **Entry condition**: Commit + merge-review (if needed) done
- **Required files**: `validation/commands.md`, `validation/test-results.md`
- **Allowed**: Build, test, e2e
- **Forbidden**: Skip (unless reason recorded)
- **Exit condition**: Build/test PASS or reason recorded for inability
- **Next state**: FINISHING

### FINISHING
- **Description**: Wrap-up
- **Entry condition**: All preconditions met
- **Required files**: `finish.md`
- **Allowed**: Archive task, update journal, summarize, record follow-ups
- **Forbidden**: Write code, fix bugs, bypass failed gates, push
- **Exit condition**: Task archived, journal updated
- **Next state**: DONE
- **Triggerable skills**: `trellis-finish-work`

### DONE
- **Description**: Task complete
- **Entry condition**: finish-work succeeded
- **Required files**: All artifacts archived
- **Allowed**: None (task archived)
- **Forbidden**: None
- **Exit condition**: None
- **Next state**: NO_TASK

---

## Failed Gate Rules

1. Any FAIL gate must return to IMPLEMENTING. Cannot skip.
2. Review gate FAIL → record blocking issues → return to IMPLEMENTING → fix → re-CHECKING → re-REVIEWING
3. Check FAIL → record blocking issues → return to IMPLEMENTING → fix → re-CHECKING
4. finish-work detects failed gate → refuse execution
5. stop-guard detects failed gate → block "done" claim

---

## Review Gate Contract

All L3+ tasks must configure a Review Gate Contract in `implement.md`:

```markdown
## Review Gate Contract

Contract version: team-kit

Required gates:
- [x] trellis-check

Selected gates:
- [ ] trellis-spec-review
- [ ] trellis-code-review
- [ ] trellis-code-architecture-review
- [ ] trellis-improve-codebase-architecture deep-review
- [ ] trellis-merge-review

Selection rationale: <why these gates>

Failure rule:
- Failed gate returns to trellis-implement.
- Do not skip a failed gate.
- Do not mark done until all selected gates pass.
```

### Gate Defaults by Level

| Task Level | check | spec-review | code-review | architecture-review | deep-review | merge-review |
|-----------|-------|-------------|-------------|-------------------|-------------|-------------|
| L2 | ✓ | | | | | |
| L3 | ✓ | | ✓ | | | |
| L4 | ✓ | ✓ | ✓ | ✓ | | |
| L5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

<!--
  WORKFLOW-STATE BREADCRUMB CONTRACT

  [workflow-state:STATUS] blocks below are the SINGLE source of truth for
  the per-turn <workflow-state> breadcrumb that inject-workflow-state.py
  reads. STATUS charset: [A-Za-z0-9_-]+.

  TAG ↔ STATUS mapping:
    [workflow-state:no_task]              → no active task
    [workflow-state:planning]             → Phase 1 (status='planning')
    [workflow-state:planning-inline]      → Phase 1 inline variant
    [workflow-state:waiting_approval]     → WAITING_IMPLEMENTATION_APPROVAL
    [workflow-state:in_progress]          → Phase 2 + Phase 3 (status='in_progress')
    [workflow-state:in_progress-inline]   → Phase 2/3 inline variant
    [workflow-state:reviewing]            → REVIEWING
    [workflow-state:finishing]            → FINISHING
-->

## Phase Index

```
Phase 1: Plan    → classify, get task-creation consent, then write planning artifacts
Phase 2: Execute → implement only after task status is in_progress and implementation approved
Phase 3: Finish  → verify, update spec, commit, merge-review, validate, and wrap up
```

### Request Triage

- L0 (pure Q&A): answer directly, no task
- L1 (tiny change): ask if user wants to skip Trellis; require explicit phrase
- L2-L5 (implementation): default to creating a Trellis task
- User approval to create a task is NOT approval to start implementation

[workflow-state:no_task]
No active task. First classify the current turn:
**L0 (pure Q&A)**: answer directly, no task.
**L1 (typo/tiny edit)**: ask if user wants to skip Trellis; require explicit "skip trellis" / "no task" / "just do it" phrase.
**L2-L5 (implementation)**: ask for task-creation consent. User approval to create a task is NOT approval to start implementation. Planning still happens first.
[/workflow-state:no_task]

### Phase 1: Plan
- 1.0 Create task `[required · once]` (only after task-creation consent)
- 1.1 Requirement exploration `[required · repeatable]` (`prd.md`; complex tasks also need `design.md` + `implement.md`)
- 1.2 Grill PRD `[required · once]` (check AC testability, risks, scope boundaries)
- 1.3 Technical design `[conditional · once]` (L3 optional, L4/L5 required)
- 1.4 Execution planning `[required · once]` (`implement.md` + Review Gate Contract)
- 1.5 Research `[optional · repeatable]`
- 1.6 Configure context `[required · once]` — curate `implement.jsonl` / `check.jsonl`
- 1.7 Implementation approval `[required · once]` (user must explicitly approve)
- 1.8 Activate task `[required · once]` (`task.py start`; status → in_progress)

[workflow-state:planning]
Load `trellis-brainstorm`; stay in planning.
Task creation approval is NOT implementation approval. Do NOT edit source code.
Lightweight (L2): `prd.md` can be enough. Complex (L3+): finish `prd.md`, `design.md` (L4/L5), and `implement.md`; ask for review before `task.py start`.
Multi-deliverable scope: consider a parent task plus independently verifiable child tasks.
Phase 1.6 (required, once): before `task.py start`, curate `implement.jsonl` and `check.jsonl` with relevant spec/research files.
Use Superpowers reasoning when unclear/complex/architectural/cross-module/high-risk. Do NOT use oh-my-claudecode for implementation before PRD is confirmed.
[/workflow-state:planning]

[workflow-state:planning-inline]
Load `trellis-brainstorm` and iterate on `prd.md` with the user. Use Superpowers reasoning for unclear, complex, architectural, cross-module, high-risk, or multi-approach tasks; skip it for small explicit tasks.
Phase 1.6 jsonl curation is **skipped** in inline dispatch mode.
Do NOT use oh-my-claudecode for implementation before PRD is confirmed. Then run `task.py start <task-dir>` to flip status to in_progress.
[/workflow-state:planning-inline]

[workflow-state:waiting_approval]
Planning artifacts are ready. WAITING FOR USER APPROVAL to begin implementation.
Do NOT edit source code. Do NOT spawn implementer. Do NOT run `task.py start`.
User must explicitly say "start implementation" / "approve implementation" / "begin coding".
[/workflow-state:waiting_approval]

### Phase 2: Execute
- 2.0 Before-dev `[required · once]` (read artifacts, specs, research)
- 2.1 Implement `[required · repeatable]`
- 2.2 Quality check `[required · repeatable]`
- 2.3 Review gates `[required · repeatable]` (per contract)
- 2.4 Rollback `[on demand]`

[workflow-state:in_progress]
**Tools**: `trellis-implementer` / `trellis-researcher` are sub-agent types only (Task/Agent tool, NOT Skill). `trellis-update-spec` is a skill. `trellis-check` exists as both a skill and agent (`trellis-checker`); prefer the Agent form after code changes. Superpowers is a reasoning extension. oh-my-claudecode is a multi-agent parallel execution extension.
**Flow**: `trellis-before-dev` → decide execution mode → `trellis-implement` or OMC parallel agents → `trellis-check` → Superpowers if blocked/repeatedly failing → review gates (per contract) → `trellis-update-spec` → commit (Phase 3.2) → merge-review (if L4/L5/multi-agent) → validate → `/trellis:finish-work`.
**Execution mode gate**: use standard Trellis sub-agents for small or tightly coupled work. Use oh-my-claudecode only when PRD is confirmed, AC are clear, the work can be split safely, and parallelism improves speed or coverage. OMC parallel mode requires explicit user confirmation before spawning.
**Main-session default**: dispatch `trellis-implement` / `trellis-check` sub-agents — the main agent does NOT edit code by default. If oh-my-claudecode is used, the main agent still owns task context, coordination, integration, conflict resolution, and final report.
**Review gates**: after check passes, run each selected review gate from the contract. Any FAIL → return to IMPLEMENTING. All PASS → proceed to spec update.
**Failed gate rule**: failed gate returns to IMPLEMENTING. Do NOT skip. Do NOT mark done until all selected gates pass.
Phase 3.2 commit (required, once): after trellis-update-spec, the main agent drives the commit — state the commit plan in user-facing text, then run `git commit` BEFORE suggesting `/trellis:finish-work`.
**Sub-agent self-exemption**: if you are already running as `trellis-implement`, implement directly and do NOT spawn another; if already `trellis-check`, review/fix directly and do NOT spawn another.
**Sub-agent dispatch protocol**: dispatch prompt MUST start with: `Active task: <task path from task.py current>`. No exceptions.
**Inline override** (per-turn only): user's CURRENT message MUST contain "do it inline" / "no sub-agent" / "main session". Without these phrases you must NOT inline.
[/workflow-state:in_progress]

[workflow-state:in_progress-inline]
**Flow** (inline mode): `trellis-before-dev` → edit code → `trellis-check` → run lint/type-check/tests → fix → Superpowers if blocked → review gates (per contract) → `trellis-update-spec` → commit (Phase 3.2) → merge-review (if L4/L5) → validate → `/trellis:finish-work`.
**Main-session default (inline)**: the main agent edits code directly. Do NOT dispatch `trellis-implement` / `trellis-check` sub-agents.
Phase 3.2 commit (required, once): after `trellis-update-spec`, the main agent drives the commit BEFORE suggesting `/trellis:finish-work`.
[/workflow-state:in_progress-inline]

[workflow-state:reviewing]
Review gates in progress. Run each selected gate from the Review Gate Contract.
Each reviewer must output PASS/FAIL with blocking issues, non-blocking issues, and exact file/spec citations.
FAIL → return to IMPLEMENTING. Do NOT skip. All PASS → proceed to spec update.
[/workflow-state:reviewing]

[workflow-state:finishing]
Finishing. Verify all gates passed, spec update decision recorded, code committed.
Run `/trellis:finish-work` to archive task, update journal, mark done.
Do NOT write new code. Do NOT fix bugs. Do NOT bypass failed gates.
[/workflow-state:finishing]

### Phase 3: Finish
- 3.1 Spec update `[required · once]`
- 3.2 Commit changes `[required · once]`
- 3.3 Merge review `[conditional · once]` (L4/L5/multi-agent/worktree/OMC)
- 3.4 Validation `[required · once]` (build/test)
- 3.5 Finish work `[required · once]` (archive + journal)
- 3.6 Debug retrospective `[on demand]`

### Rules

1. Identify which Phase you're in, then continue from the next step there
2. Run steps in order inside each Phase; `[required]` steps can't be skipped
3. Phases can roll back (e.g., Execute reveals a prd defect → return to Plan to fix, then re-enter Execute)
4. Steps tagged `[once]` are skipped if the output already exists; don't re-run
5. Artifact presence informs the next step; missing `design.md` / `implement.md` is valid for lightweight tasks

### Team Extension Routing

| Situation | Extension | Rule |
|---|---|---|
| Requirements unclear, broad, architectural, cross-module, high-risk | Superpowers | Use before finalizing PRD; persist decisions into `prd.md` or `research/` |
| Check fails repeatedly, fixes conflict, same bug returns | Superpowers + `trellis-break-loop` | Pause implementation, reason about root cause, update PRD/spec |
| Confirmed PRD can be split into independent streams | oh-my-claudecode | Main agent recommends, MUST get explicit user confirmation before spawning |
| OMC parallel agents need different Skills/MCPs | oh-my-claudecode + scenario capability | Main agent assigns per-agent capabilities in dispatch prompt |
| Small, explicit, low-risk task | Neither by default | Keep Trellis path lightweight; do not add ceremony |
| Need external facts, docs, browser, UI/design, tests, debugging, review | MCP / scenario skill | Load only relevant capability; route through `.trellis/spec/index.md` |

### Skill Routing

When a user request matches one of these intents, load the corresponding skill (or dispatch the corresponding sub-agent) first — do not skip skills.

| User intent | Route |
|---|---|
| New feature / unclear requirements | `trellis-brainstorm` |
| PRD needs challenge | `trellis-grill-me` |
| Need execution strategy | `trellis-dev-strategy` |
| About to write code / start implementing | `trellis-before-dev` then dispatch `trellis-implementer` sub-agent |
| Finished writing / want to verify | Dispatch `trellis-checker` sub-agent |
| Need spec compliance review | `trellis-spec-review` |
| Need code quality review | `trellis-code-review` |
| Need architecture review | `trellis-code-architecture-review` |
| Need architecture guidance/deep-review | `trellis-improve-codebase-architecture` |
| Stuck / fixed same bug several times | `trellis-break-loop` |
| Spec needs update | `trellis-update-spec` |
| Multi-agent/OMC/worktree merge | `trellis-merge-review` |
| Task complete, ready to wrap up | `trellis-finish-work` |

### DO NOT skip skills

| What you're thinking | Why it's wrong |
|---|---|
| "This is simple, I'll just code it in the main thread" | Dispatching `trellis-implement` is the cheap path; skipping it loses spec context — sub-agents get `implement.jsonl` injected, you don't |
| "I already thought it through in plan mode" | Plan-mode output lives in memory — sub-agents can't see it; must be persisted to prd.md |
| "I already know the spec" | The spec may have been updated since you last read it; the sub-agent gets the fresh copy |
| "Code first, check later" | `trellis-check` surfaces issues you won't notice yourself; earlier is cheaper |
| "The check passed, so we can skip review" | Review gates are selected in the contract; skipping them violates the task's own plan |
| "One failed review is fine, we can still finish" | Failed gate MUST return to implement. Do not skip. |

### DO NOT misuse workflow extensions

| What you're thinking | Why it's wrong |
|---|---|
| "This is complex, so I'll start coding and let agents figure it out" | Complexity is a reason to strengthen Plan with Superpowers, not a reason to skip PRD |
| "oh-my-claudecode can plan and verify for me" | OMC only provides parallel execution; Trellis owns lifecycle and Check |
| "More agents always means better results" | Parallel agents help only when work is decomposable and integration is controlled |
| "The PRD is clear, so I can start OMC myself" | OMC parallel mode still requires explicit user confirmation before spawning agents |
| "I'll load every MCP and skill just in case" | Scenario tools are triggered by need; global loading wastes context and weakens focus |
| "The check agent passed, so no spec-update judgment is needed" | Finish still requires `trellis-update-spec` judgment, even when no update is made |

### Loading Step Detail

```bash
python3 ./.trellis/scripts/get_context.py --mode phase --step <step>
```

---

## Phase 1: Plan

Goal: classify the request, get task-creation consent when a task is needed, and produce the planning artifacts required before implementation.

#### 1.0 Create task `[required · once]`

Create the task directory only after task-creation consent:

```bash
python3 ./.trellis/scripts/task.py create "<task title>" --slug <name>
```

`--slug` is the human-readable name only. Do NOT include the `MM-DD-` date prefix.

**Run only `create` here — do not also run `start`.** `start` flips status to `in_progress` before planning artifacts are reviewed.

Skip when `python3 ./.trellis/scripts/task.py current --source` already points to a task.

#### 1.1 Requirement exploration `[required · repeatable]`

Load the `trellis-brainstorm` skill and explore requirements interactively.

The brainstorm skill guides you to:
- Ask one question at a time
- Prefer researching over asking the user
- Prefer offering options over open-ended questions
- Update `prd.md` immediately after each user answer
- Split large scopes into parent + child tasks when deliverables can be verified independently

If the task is unclear, complex, architectural, cross-module, high-risk, or has multiple plausible paths, apply Superpowers reasoning before freezing scope.

#### 1.2 Grill PRD `[required · once]`

Load the `trellis-grill-me` skill to challenge the PRD:
- Are acceptance criteria testable?
- Is out of scope explicit?
- Are edge cases covered?
- Are auth/security/performance/compatibility addressed?
- Is migration/rollback considered?
- What risks exist?
- Is there scope creep risk?

Output to `research/grill-me.md` and update `prd.md`.

#### 1.3 Technical design `[conditional · once]`

For L3+ tasks, produce `design.md`. L4/L5 tasks MUST have `design.md`.

Load `trellis-improve-codebase-architecture guidance` for architecture guidance on complex tasks.

#### 1.4 Execution planning `[required · once]`

Load `trellis-dev-strategy` to decide:
1. Execution mode: main-session / subagent / subagent + worktree / OMC
2. Branch strategy: current branch / dedicated worktree
3. TDD: yes / no
4. Parent/child task: yes / no
5. Architecture guidance needed: yes / no
6. Review gates: which to enable
7. Merge-review needed: yes / no

Write to `implement.md` including the Review Gate Contract.

#### 1.5 Research `[optional · repeatable]`

Research at any time during planning. Use `trellis-researcher` subagent. Output MUST be persisted to `{TASK_DIR}/research/`.

#### 1.6 Configure context `[required · once]`

Curate `implement.jsonl` and `check.jsonl` with relevant spec/research files. What to include: spec files, research files. What NOT to include: code files, files about to be modified.

```bash
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" implement "<path>" "<reason>"
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" check "<path>" "<reason>"
```

#### 1.7 Implementation approval `[required · once]`

Present planning artifacts to user. WAIT for explicit approval before `task.py start`.

#### 1.8 Activate task `[required · once]`

```bash
python3 ./.trellis/scripts/task.py start <task-dir>
```

After this command, the breadcrumb switches to `[workflow-state:in_progress]`.

#### Completion criteria

| Condition | Required |
|------|:---:|
| `prd.md` exists with testable AC | ✅ |
| `grill-me.md` completed | ✅ |
| User explicitly approves implementation | ✅ |
| `task.py start` has been run | ✅ |
| `design.md` exists (L4/L5) | ✅ |
| `implement.md` exists with Review Gate Contract | ✅ |
| `research/` has artifacts (complex tasks) | recommended |
| `implement.jsonl` / `check.jsonl` curated | ✅ |

---

## Phase 2: Execute

Goal: turn reviewed planning artifacts into code that passes quality checks and review gates.

#### 2.0 Before-dev `[required · once]`

Load `trellis-before-dev` skill. Before writing any code:
1. Read `prd.md`
2. Read `design.md` if present
3. Read `implement.md`
4. Read `implement.jsonl` entries
5. Read relevant specs
6. Read relevant research
7. Output constraints for this implementation
8. Confirm task is `in_progress`

#### 2.1 Implement `[required · repeatable]`

**Execution mode decision**:

| Mode | Use when | Owner |
|---|---|---|
| Standard Trellis sub-agent | Small, medium, or tightly coupled work | `trellis-implement` |
| oh-my-claudecode parallel agents | Confirmed PRD, clear AC, independent workstreams | Main agent orchestrates; OMC agents execute |
| Inline | Only when platform mode or explicit user override | Main session |

OMC parallel mode requires explicit user confirmation before spawning.

Spawn the implement sub-agent:
- **Agent type**: `trellis-implementer`
- **Task description**: Implement per prd.md, consulting `research/`; finish by running lint and type-check
- **Dispatch prompt guard**: `Active task: <task path>`. Tell the agent it is already `trellis-implementer`.

#### 2.2 Quality check `[required · repeatable]`

Spawn the check sub-agent:
- **Agent type**: `trellis-checker`
- **Task description**: Review all code changes against spec and prd; fix findings directly; ensure lint/type-check pass
- **Dispatch prompt guard**: `Active task: <task path>`. Tell the agent it is already `trellis-checker`.

The check agent outputs: PASS/FAIL, commands run, failures, fixes applied.

#### 2.3 Review gates `[required · repeatable]`

After check PASS, run each selected review gate from the contract. Each reviewer outputs PASS/FAIL with blocking issues.

FAIL → return to IMPLEMENTING → fix → re-check → re-review.

#### 2.4 Rollback `[on demand]`

- check reveals PRD defect → return to Phase 1, fix `prd.md`, then redo 2.1
- Implementation went wrong → revert code, redo 2.1
- Repeated failure → use Superpowers + `trellis-break-loop`
- Parallel agents conflict → main agent resolves against PRD + specs

---

## Phase 3: Finish

Goal: ensure quality, capture lessons, record work.

#### 3.1 Spec update `[required · once]`

Load `trellis-update-spec` skill. Record decision in `finish.md`:

```markdown
## Spec Update Decision

Need spec update?
- [ ] yes
- [ ] no

Reason:

Updated files:
-
```

#### 3.2 Commit changes `[required · once]`

1. **Inspect dirty state**: `git status --porcelain`
2. **Learn commit style**: `git log --oneline -5`
3. **Classify dirty files**: AI-edited vs unrecognized
4. **Draft commit plan** (batched, one-shot confirmation):

```
Proposed commits (in order):
  1. <type>: <description>
     - <file>

Unrecognized dirty files (NOT in any commit — confirm include/exclude):
  - <file>

Reply 'ok' to execute. Reply with edits, or 'manual' to abort.
```

5. **On confirmation**: `git add` + `git commit` for each batch. No amend. No push.

#### 3.3 Merge review `[conditional · once]`

Required for: worktree, multi-subagent, OMC parallel, PR merge, conflict resolution, parent/child task.

Load `trellis-merge-review` skill. Output PASS/FAIL to `review/merge-review.md`.

#### 3.4 Validation `[required · once]`

Run build/test. Record results in `validation/test-results.md`. If cannot execute, record reason.

#### 3.5 Finish work `[required · once]`

Load `trellis-finish-work` skill. Finish-work only does:
1. Verify task can finish (all gates passed)
2. Archive task
3. Update workspace journal
4. Update task index
5. Summarize commits/PR
6. Record follow-ups
7. Mark task done

Finish-work does NOT: write code, fix bugs, bypass failed gates, push.

#### 3.6 Debug retrospective `[on demand]`

If repeated debugging occurred, load `trellis-break-loop` skill:
- Classify root cause
- Explain why earlier fixes failed
- Propose prevention
- At least one durable action: update spec / guide / add regression test / create follow-up task

---

## Parent / Child Task Trees

Use a parent task when one request contains several independently verifiable deliverables.

**Parent task owns**: source requirements, child-task mapping, cross-child acceptance criteria, final integration review, merge-review.

**Child task owns**: independent implementation, independent check, local acceptance, archive.

**Rules**:
- Parent/child is not a dependency system. If child B depends on child A, write ordering in child B's `prd.md` / `implement.md`.
- Start the child that owns the next deliverable. Do not start the parent unless it has direct implementation work.

---

## Worktree Policy

Recommended path: `.trellis/worktrees/<task-slug>/`

Must use worktree when:
1. Multiple subagents in parallel
2. OMC parallel execution
3. Cross-package changes
4. Large refactors
5. PR-type tasks
6. Parent/child tasks

Forbidden:
1. Multiple agents editing same files in same worktree simultaneously
2. Merging worktree without merge-review
3. Unrelated changes in worktree

---

## Finish-Work Preconditions

1. Implementation complete
2. `trellis-check` PASS
3. Selected review gates PASS
4. Spec update decision recorded
5. Code committed or PR created (or explicitly no commit needed)
6. Build/test PASS (or explicitly recorded as not executable)

Any missing precondition → finish-work refuses to execute.

---

## Customizing Trellis (for forks)

### Changing what a step means

Edit the corresponding step's walkthrough body in the Phase 1/2/3 sections above. If you change a step's `[required · once]` marker or add a new step, you MUST also add matching enforcement to that phase's `[workflow-state:STATUS]` tag block.

### Changing the per-turn prompt text

Directly edit the body of the corresponding `[workflow-state:STATUS]` block. After editing, run `trellis update` or restart your AI session.

### Adding a custom status

Add a new block: `[workflow-state:my-status]...[/workflow-state:my-status]`.

Constraints:
- STATUS charset: `[A-Za-z0-9_-]+`
- A lifecycle hook must write `task.json.status` to your custom value
- Lifecycle hooks bind to `after_create / after_start / after_finish / after_archive`
