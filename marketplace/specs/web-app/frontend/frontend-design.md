# frontend-design.md

## Purpose

Define the team contract for frontend design decisions.

Frontend work must produce usable, consistent, project-native interfaces.

This guide does not define frontend testing, browser verification, or frontend/backend integration checks. Use `testing.md` for verification rules.

## When to Load

Load when a task involves:

* new frontend page, route, or screen
* frontend component design
* UI/UX improvement
* adding, modifying, or deleting user-facing UI
* dashboard, table, form, detail page, settings page, or workflow page
* layout, visual hierarchy, interaction, or responsive design
* loading, empty, error, success, disabled, or permission states
* choosing or changing frontend stack, UI library, or design system

Skip for backend-only work unless frontend behavior or user experience is affected.

## Core Contract

Do not jump from a vague frontend request directly into code.

Before implementation, identify:

* whether this is a new frontend setup or an existing frontend project
* existing framework, language, UI library, routing, API, state, and style system
* target user and primary user task
* information hierarchy
* required UI states
* available design skill, reference, screenshot, or design source

AI should propose a design direction first.

Ask the user only when the decision is product-level, high-impact, or cannot be inferred from the existing project.

## Project Stage

### New or Early Frontend

If no clear frontend structure exists, propose the frontend foundation before coding.

Cover:

* framework
* language and type system
* UI component library
* styling approach
* routing approach
* API request pattern
* state management approach, if needed
* directory structure

Do not silently introduce a full frontend stack.

Major stack or dependency decisions require user confirmation.

### Existing Frontend

If frontend files already exist, reuse existing choices.

Follow:

* framework
* TypeScript or JavaScript conventions
* UI library
* routing
* API wrapper
* state management
* reusable components
* layouts
* design tokens, theme, CSS variables, or style conventions
* directory structure

For existing frontend projects: extend, do not replace.

New UI must look and behave like part of the current product.

## Add / Modify / Delete Policy

For additions, extend the existing frontend system.

Use existing components, patterns, spacing, typography, colors, icons, interactions, and page density.

For modifications, prefer the smallest change that satisfies the user request.

For deletions, remove only the requested UI, behavior, or entry point unless the user asks for broader cleanup.

Do not redesign the whole page, replace the component structure, change the visual system, or introduce a parallel style for a small add, modify, or delete request.

If a small request exposes a larger design problem, report it as a follow-up instead of silently expanding scope.

## Skill Usage

Use available frontend design skills when useful.

Examples:

* `ui-ux-pro-max` or equivalent for UI/UX analysis
* `frontend-design` or equivalent for visual direction
* frontend implementation skill for page or component execution

Skills are helpers, not replacements for this guide.

If no relevant skill is available, still follow this contract.

## Existing Stack First

Default to the project’s existing frontend system.

Prefer:

* existing components over new components
* existing UI library over new dependencies
* existing layout patterns over new layouts
* existing API wrappers over direct fetch calls
* existing type definitions over ad-hoc shapes
* existing styles, tokens, and theme variables over custom styling
* existing routing and state patterns over new abstractions

Do not introduce a new framework, UI library, CSS framework, router, state library, form library, or animation library for visual preference.

New dependencies require justification and, when significant, user confirmation.

## Design Before Code

For meaningful frontend work, create a short design plan before implementation.

Include:

* user goal
* page or component purpose
* primary action
* information hierarchy
* main sections or zones
* relevant data sources
* key UI states
* responsive considerations, if relevant
* files expected to change
* whether this is add, modify, or delete work

Keep it concise.

Do not turn it into a long design document unless the task is large.

## User-Centered Design

Do not design pages by dumping backend response fields.

Design around:

* what the user needs to understand first
* what decision the user needs to make
* what action the user needs to complete
* what information is primary or secondary
* what can be hidden, collapsed, filtered, paginated, or deferred
* what helps the user recover from empty or error states

After that, map backend data into the page.

## UI State Design

Do not design only the happy path.

Consider relevant states:

* loading
* empty
* error
* success
* disabled
* permission denied
* submitting
* partial data
* stale data

For forms, include validation and submit feedback.

For dangerous actions, include confirmation, clear labels, cancel path, and failure handling.

## Visual Quality

Frontend design should feel professional, domain-appropriate, and consistent with the product.

Prefer:

* clear visual hierarchy
* readable spacing
* consistent alignment
* predictable interactions
* accessible labels and controls
* meaningful empty and error states
* restrained motion
* mobile and desktop awareness when relevant

Avoid generic template-like UI when project style exists.

## Human Confirmation Required

Ask for confirmation before:

* introducing a new frontend framework
* introducing a new UI library or CSS framework
* adding major frontend dependencies
* changing routing architecture
* changing global state architecture
* changing theme or design system foundation
* replacing existing component patterns
* redesigning an existing page beyond the requested change
* making product-level visual direction decisions
* designing destructive or high-risk user actions

Do not silently make these decisions.

## Reporting

Final summary should include:

* design approach
* whether the task added, modified, or deleted UI
* existing stack or patterns reused
* key UI states considered
* major design decisions
* files changed
* dependency or stack changes, if any
* remaining UX risks or follow-up

Use `testing.md` to report browser, e2e, and integration verification.

## Never

Never:

* start meaningful frontend work without a design plan
* switch frameworks or UI libraries by default
* introduce dependencies only for visual preference
* ignore existing components and style patterns
* create a parallel design style inside an existing product
* dump backend fields directly onto the page
* implement only the happy path
* skip important UI states
* replace a page or component wholesale for a small request
* delete more UI than requested
* redesign surrounding UI unless the task requires it
* build forms without validation or submit feedback
* create dangerous actions without confirmation
* make product-level visual decisions silently
* perform broad unrelated refactors
* make the page look like a generic template when project style exists

## Definition of Done

A frontend design task is done only when:

* the design matches the user goal
* add, modify, or delete scope was respected
* existing frontend stack and style were reused when present
* the interface has clear information hierarchy
* key UI states were considered
* major frontend decisions were justified
* high-impact design or dependency choices were confirmed
* remaining UX risks are visible
