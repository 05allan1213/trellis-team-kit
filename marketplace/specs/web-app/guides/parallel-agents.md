# Parallel Agents

## Scope

This spec governs oh-my-claudecode parallel agents in Trellis Execute.
It does not replace `.trellis/workflow.md`, define generic multi-agent rules, or teach OMC usage.

## Authority

Trellis owns lifecycle.
`prd.md` owns scope.
Acceptance Criteria own completion.
Specs own team standards.
oh-my-claudecode owns parallel execution only.
The main agent owns orchestration, integration, final check, and final report.

## Core Rules

OMC is an Execute-stage acceleration tool.
OMC must not be used during Plan.
OMC must not create the task, write the initial PRD, decide product direction, skip Check, skip Finish, update specs independently, or mark the task complete.
Before OMC starts, all conditions must be true:

* An active Trellis task exists.
* `prd.md` is confirmed.
* Acceptance Criteria are clear.
* The task is already in Execute.
* Work can be split safely.
* The user explicitly approves parallel mode.
  If the task is unclear, architectural, high-risk, or has multiple possible directions, stay in Plan and use Superpowers reasoning first.

## Trigger Model

The AI may recommend OMC when the task shape fits.
The AI must not start OMC without explicit user confirmation.
Pattern: `AI proposes -> user approves -> OMC executes -> main agent integrates -> Trellis checks`.
Ask once before spawning workers.
Do not ask once per worker.
Ask again only when a later high-risk action needs separate approval.
Before asking, the main agent should state:

* Why OMC helps this task.
* Which workers will be spawned.
* What each worker owns.
* Expected files or modules.
* Known risks.
* That final integration remains with the main agent.

## Good Fits

Recommend OMC when parallelism clearly improves speed, coverage, or confidence.
Good examples:

* Frontend and backend can be implemented separately.
* Code and tests can be developed separately.
* Independent modules need similar changes.
* Multiple bug hypotheses can be investigated separately.
* Research, implementation, and review can be split cleanly.
* UI implementation and browser verification can run separately.
* A refactor has clear file ownership and bounded scope.
  Do not recommend OMC only because a task is large.
  Large unclear work belongs in Plan first.

## Bad Fits

Do not use OMC when:

* PRD is not confirmed.
* Acceptance Criteria are missing.
* Requirements are ambiguous.
* Architecture direction is undecided.
* The task is small and linear.
* Most workers would edit the same files.
* Work has strict step-by-step dependency.
* Integration risk is too high.
* Coordination cost is higher than execution benefit.

## OMC Mode Keywords

Use project-approved OMC mode keywords.
Choose the mode that matches the task shape.
Use parallel execution mode for independent implementation streams.
Use coordinated team mode when workers need orchestration.
Use verification-oriented mode when the work is mainly validation.
Do not invent custom multi-agent behavior when an OMC mode already exists.
If the correct OMC mode is unclear, use standard Trellis execution.

## Worker Assignment

Each worker must receive a bounded assignment.
A valid assignment includes:

* Active Trellis task path.
* Worker role.
* Goal and scope.
* Non-goals.
* Expected files or modules.
* Required specs, skills, or MCPs.
* Validation expectation.
* Reporting requirements.
  Avoid vague assignments:
* "Handle frontend."
* "Fix backend."
* "Review everything."
* "Clean up the codebase."
* "Make it production-ready."

## File Ownership

Prefer OMC when workers touch separate files, modules, or concerns.
Good boundaries:

* Frontend vs backend.
* Code vs tests.
* Research vs implementation.
* Review vs implementation.
* Browser verification vs UI changes.
* Independent modules.
  Avoid OMC when workers would edit:
* The same file.
* Shared types.
* API contracts.
* Database schemas.
* Auth or permission logic.
* Core configuration.
* `.trellis/`, `.claude/`, hooks, specs, workflow, or task state.
  If unexpected overlap appears, stop parallel work and let the main agent integrate manually.

## Interactive Approval

Workers must not depend on interactive user confirmation.
If a worker reaches an action that requires approval, it must stop and report the action to the main agent.
Workers must not block indefinitely waiting for terminal confirmation.
Approval-sensitive actions must return to the main agent:

* Destructive file operations.
* Dependency upgrades.
* Database migrations.
* Auth or permission changes.
* Payment or billing changes.
* Production infrastructure changes.
* Git reset, clean, rebase, amend, or push.
* Changes to `.trellis/`, `.claude/`, hooks, specs, workflow, or task state.
  The main agent decides whether to ask the user, run the action, change the plan, skip the action, or return to Plan.

## Main Agent Responsibilities

The main agent remains responsible for:

* Recommending OMC.
* Getting user approval.
* Assigning bounded worker scopes.
* Passing active task context.
* Preventing unsafe overlap.
* Reviewing worker reports.
* Resolving conflicts.
* Integrating final changes.
* Running Trellis Check.
* Reporting the final result.
  Worker success does not mean task success.

## Worker Report

Each worker must report:

* Assigned role.
* Work completed.
* Files changed or inspected.
* Checks run.
* Assumptions made.
* Blockers or risks.
* Follow-up needed.
  "Done" is not a valid worker report.

## Integrated Check

After OMC finishes, the main agent must verify:

* Final result matches `prd.md`.
* Acceptance Criteria are satisfied.
* Worker outputs do not conflict.
* No unrelated changes were introduced.
* Required checks were run or honestly reported.
* Remaining risks are documented.
  Then run the normal Trellis Check path.

## Stop Conditions

Stop OMC when:

* Workers conflict on scope.
* File ownership overlaps unexpectedly.
* Requirements become unclear.
* Architecture must change.
* A high-risk action is required.
* Tests reveal cross-module failure.
* Scope expands beyond the approved PRD.
* Integration becomes unsafe.
  If scope changes, return to Plan before continuing.

## Related Specs

Use with `.trellis/workflow.md`, `ai-tooling.md`, `testing.md`, `debugging.md`, `code-review.md`, and `frontend-design.md`.

## Definition of Done

OMC parallel execution is done only when workers have reported back, the main agent has integrated outputs, conflicts are resolved, the result matches the PRD, Trellis Check has run, and remaining risks are reported.
