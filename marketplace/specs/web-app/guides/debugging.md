# debugging.md

## When to Load

Load this guide when a task involves:

* fixing a reported bug
* investigating a possible bug
* resolving a failing test or CI failure
* diagnosing incorrect runtime behavior
* diagnosing API, UI, database, auth, config, or integration issues
* handling regressions, crashes, timeouts, inconsistent data, or production-like incidents

Do not load this guide for normal feature work unless a concrete bug or investigation request exists.

## Purpose

This guide defines the team debugging contract for AI-assisted work.

It does not teach language-specific debugging.

It ensures the agent receives a clear issue, validates it, finds the root cause, applies a minimal fix, verifies the result, and reports honestly.

## Core Contract

Do not fix an unspecified bug.

Before editing code, establish a concrete bug statement from a user report, QA report, failed test, CI failure, error output, log, screenshot, monitoring signal, or explicit investigation request.

Then validate that the issue exists, or that the available evidence reasonably supports it.

Do not guess and patch code before understanding the problem.

## Bug Intake

Capture the bug context when available:

* what is wrong
* expected behavior
* actual behavior
* where it happens
* how to reproduce or observe it
* relevant error, log, screenshot, failed test, or request
* affected environment, branch, device, browser, service, or configuration
* user impact
* known recent changes, if relevant

If the user already provided enough information, proceed to validation.

If critical information is missing, ask only for what is needed to reproduce, observe, or verify the bug.

Do not ask for every field mechanically.

## Investigation Mode

If the user asks the agent to find possible bugs, review suspicious behavior, or investigate instability, start in investigation mode.

In investigation mode:

* inspect before editing
* identify concrete issues first
* provide evidence for each suspected issue
* distinguish confirmed bugs from possible risks
* do not modify code until the issue and intended fix scope are clear

If no concrete bug is found, report what was checked and what remains uncertain.

## Validate Before Fix

Before changing code, validate the reported issue when feasible.

Use the most relevant available evidence:

* reproduce the behavior manually
* run the failing test
* inspect CI output
* inspect logs or error output
* trace the reported code path
* compare expected and actual behavior
* verify the failing API, UI, data path, or integration boundary

If the issue cannot be reproduced, do not claim a confirmed fix.

Report what was checked, what evidence was found, what could not be verified, and what remains uncertain.

## Debugging Flow

Use this order:

1. Confirm the bug statement.
2. Inspect the evidence.
3. Locate the direct failure point.
4. Trace the call chain or data flow.
5. Check inputs, state, configuration, dependencies, and environment.
6. Form a root-cause hypothesis backed by evidence.
7. Plan the minimal fix.
8. Apply the fix.
9. Run regression verification.
10. Report root cause, fix, verification, and remaining risk.

Do not make large changes before tracing the failure path.

## Root Cause Before Patch

Prefer root-cause fixes over symptom masking.

Before patching, identify:

* what fails
* why it fails
* why the current code allows it
* which path is directly responsible
* what minimal change should prevent recurrence

If the root cause cannot be fully confirmed, state the uncertainty.

A partial fix is acceptable only when the limitation is clearly reported.

## Fix Scope

Bug fixes must stay close to the root cause.

Allowed:

* correcting incorrect logic
* fixing missing validation or boundary checks
* fixing incorrect data mapping
* fixing missing error handling
* fixing incorrect configuration usage
* adding useful diagnostic context
* adding or updating regression tests

Avoid:

* broad refactoring
* unrelated cleanup
* dependency upgrades
* public API changes
* config format changes
* directory restructuring
* unrelated abstractions
* rewriting the test framework

If a proper fix requires larger design change, stop and report the required scope instead of silently expanding the task.

## Regression Verification

Every bug fix requires regression verification.

Use `testing.md` to select the right verification method.

At minimum, verify:

* the original failure no longer reproduces, or the failing path is covered
* the expected behavior works
* nearby behavior was not obviously broken
* task-related tests or checks pass when available

Prefer adding or updating a regression test when reasonable.

If no regression test is added, report why.

Do not say “fixed” without verification.

## Integration Bugs

For integration bugs, verify the boundary where the failure occurs.

Check the real connection between affected parts: frontend/backend, API/database, auth/API, service/service, config/runtime, or external dependency/application.

When frontend behavior is involved, API-only verification is usually insufficient.

Prefer browser, Playwright, e2e, or DevTools verification when available.

Use `testing.md` for verification strength and `frontend-design.md` for deeper UI behavior expectations.

## Diagnostics

Add diagnostic logs only when they help future debugging.

Logs must include useful context, avoid sensitive data, avoid noisy temporary output, and follow project conventions.

Remove temporary debugging output before completion.

Do not hide, swallow, or force-success errors as a substitute for proper handling.

## Escalation

Stop patching and re-analyze when:

* the same fix fails repeatedly
* two or more attempted fixes do not resolve the issue
* the bug cannot be reproduced but keeps being reported
* the fix introduces another bug
* the root cause involves unclear ownership or missing spec
* the issue exposes a repeated team mistake
* the issue requires architectural, API, database, or product behavior changes

When this happens, summarize failed attempts, restate the evidence, revise the root-cause hypothesis, identify missing tests or specs, propose the smallest safe next step, and consider whether `update-spec` is needed.

Do not keep guessing.

## Failure Handling

If the fix fails verification:

* do not report success
* inspect whether the failure is related to the current bug
* revise the root-cause hypothesis
* avoid stacking unrelated patches
* report blockers when the environment prevents verification

If a failing check is unrelated or pre-existing, report it clearly with evidence.

## Reporting

The final bug-fix summary must include:

* bug statement
* reproduction or validation result
* root cause
* fix applied
* modified files
* regression verification
* checks run
* checks failed or skipped
* remaining uncertainty or risk
* follow-up needed, if any

Never claim the issue is fixed unless verification supports that claim.

If verification is partial, say so.

If the issue could not be reproduced, say so.

## Forbidden Behaviors

Never:

* fix an unspecified bug
* invent missing bug details
* change code before validation when validation is feasible
* make speculative fixes without evidence
* patch symptoms while ignoring root cause
* delete failing tests to make results pass
* only change tests without fixing the real issue
* comment out core logic to make code compile
* expand a small bug into a refactoring task
* introduce unrelated dependencies
* change API behavior without explanation
* hide failing checks
* claim fixed without regression verification

## Definition of Done

A bug-fix task is done only when the bug statement is clear, the issue was reproduced or evidence boundaries were reported, root cause was identified or uncertainty was stated, the fix is scoped to the cause, regression verification was completed or clearly blocked, failures were reported honestly, and repeated lessons were considered for `update-spec`.

## Out of Scope

This guide does not define framework-specific debugging tutorials, language-specific bug catalogs, full testing strategy, frontend visual design standards, final code review grading, safety hooks, command blocking, or large incident response.
