# testing.md

## When to Load

Load this guide when a task changes runtime behavior, including:

* application logic
* frontend behavior
* backend behavior
* API contracts
* database queries or migrations
* authentication, authorization, or session behavior
* build, CI, deployment, or runtime configuration
* dependencies that affect application behavior
* bug fixes requiring regression verification

For documentation-only changes, code verification may be skipped, but the final report must say why.

## Purpose

This guide defines the team verification contract for AI-assisted work.

It does not teach testing frameworks.

It tells the agent how to choose, run, and report verification based on the actual Execute result.

## Core Contract

Before selecting tests, inspect:

* PRD acceptance criteria
* actual changed files
* affected language, framework, runtime, or platform
* existing project scripts and CI commands
* affected user flow, API, data path, or integration boundary
* risk level of the change

Select verification based on the implementation, not from a fixed checklist.

Use the smallest verification set that is sufficient to prove the requirement works.

## Project-Native Commands First

Prefer repository-defined commands.

Use, when available:

* package scripts
* Makefile targets
* CI-equivalent commands
* documented test commands
* existing unit, integration, component, or e2e tests
* existing browser or API verification tools

Do not invent commands when the repository does not define them.

Do not add new tooling only to satisfy this guide unless the task requires it.

If no reliable command exists, perform the best available static, manual, or smoke verification and report the limitation.

## Verification Baseline

Every non-trivial code task should consider:

* build, compile, or start check
* lint or formatting check
* typecheck, if the project uses types
* targeted behavior test
* regression test for bug fixes
* integration check when boundaries are affected
* browser or e2e check when user-visible frontend behavior is affected

Not every task requires every check.

The agent must choose and justify the verification level.

## Required Cases

### Logic Change

Verify the changed behavior directly.

Use existing targeted tests when available.

Add or update tests when reasonable and aligned with the project.

### Bug Fix

A bug fix requires regression verification.

Verify that:

* the original failure no longer reproduces, or the suspected failure path is covered
* the intended behavior still works
* nearby behavior was not obviously broken

If the bug cannot be reproduced, do not claim it is fully fixed.

### API Change

Verify the affected contract:

* route and method
* request shape
* response shape
* status codes
* validation behavior
* error behavior
* auth or permission behavior, if relevant
* frontend or client compatibility, if affected

### UI Change

Verify user-visible behavior.

Check relevant states:

* success
* loading
* empty
* error
* disabled
* responsive behavior
* browser rendering

Use `frontend-design.md` for deeper UI/UX quality rules.

### Database or Migration Change

Verify data safety before completion.

Check, when possible:

* migration applies cleanly
* schema assumptions match application code
* affected queries still work
* rollback or recovery path is understood
* destructive data risk is called out

Destructive or production-like data actions require human confirmation.

### Dependency, Build, or Config Change

Verify the affected runtime path.

Check, when possible:

* install still works
* build still works
* affected commands still run
* config is valid
* lockfile changes are intentional
* runtime behavior affected by the config is checked

## Frontend/Backend Integration

When a change affects the boundary between frontend and backend, verify across the boundary.

Prefer the strongest available project-native method:

1. existing e2e or integration test
2. Playwright or equivalent browser automation, if available
3. browser manual verification with DevTools or network inspection
4. API smoke test using curl, httpie, Postman, or equivalent

If frontend behavior is part of the acceptance criteria, API-only verification is not enough.

Verify the relevant real flow:

* frontend calls the intended endpoint
* method, route, query, body, and headers match backend expectations
* auth, cookie, token, or session behavior works
* response shape matches frontend usage
* success, loading, empty, and error states behave correctly
* base URL, proxy, CORS, or environment assumptions are valid

If only API smoke verification is possible, report that frontend integration was not fully verified.

## Risk-Based Escalation

Increase verification strength when the change affects:

* authentication or authorization
* payments, billing, or financial data
* data writes, migrations, or deletion
* security-sensitive behavior
* public API contracts
* cross-service behavior
* production configuration
* complex frontend/backend integration
* code used by many features
* recently broken or fragile areas

High-risk changes usually require more than targeted tests.

Ask for human confirmation when verification would require destructive, irreversible, or production-impacting actions.

## Failure Handling

If a check fails:

* do not ignore it
* do not report success
* determine whether it is related to the task
* fix task-related failures when feasible
* report unrelated or pre-existing failures clearly
* avoid broad unrelated rewrites unless the PRD requires them

If verification cannot run because of missing dependencies, unavailable services, absent commands, or environment issues, report the blocker.

## Honest Reporting

The final task summary must include verification results.

Report:

* commands or checks run
* what passed
* what failed
* what was skipped
* what could not run
* why skipped or unavailable checks were not run
* whether frontend/backend integration was fully verified when relevant
* remaining risk or manual follow-up needed

Never claim verification passed unless the check was actually run and completed successfully.

Do not use vague claims such as:

* should work
* looks good
* probably works
* not tested but should pass

Never describe API-only verification as full end-to-end verification.

Never hide failing checks.

## Definition of Done

A task is not done until verification is appropriate for the implemented change.

Done means:

* acceptance criteria were checked
* relevant verification was completed
* frontend/backend boundaries were verified when affected
* failures were fixed or clearly reported
* skipped checks were explained
* remaining risks are visible
* no false claim of test success was made

## Out of Scope

This guide does not define:

* framework-specific testing tutorials
* detailed mocking strategy
* full testing pyramid theory
* frontend visual design standards
* bug root-cause investigation process
* final code review criteria
* hard command blocking or safety hooks
