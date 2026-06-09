# Cross-Layer Thinking Guide

> **Purpose**: Think through data flow across layers before implementing.

---

## The Problem

**Most bugs happen at layer boundaries**, not within layers.

Common cross-layer bugs:
- API returns format A, frontend expects format B
- Database stores X, service transforms to Y, but loses data
- Multiple layers implement the same logic differently

---

## Before Implementing Cross-Layer Features

### Step 1: Map the Data Flow

Draw out how data moves:

```
Source → Transform → Store → Retrieve → Transform → Display
```

For each arrow, ask:
- What format is the data in?
- What could go wrong?
- Who is responsible for validation?

### Step 2: Identify Boundaries

| Boundary | Common Issues |
|----------|---------------|
| API ↔ Service | Type mismatches, missing fields |
| Service ↔ Database | Format conversions, null handling |
| Backend ↔ Frontend | Serialization, date formats |
| Component ↔ Component | Props shape changes |

### Step 3: Define Contracts

For each boundary:
- What is the exact input format?
- What is the exact output format?
- What errors can occur?

---

## Common Cross-Layer Mistakes

### Mistake 1: Implicit Format Assumptions

**Bad**: Assuming date format without checking

**Good**: Explicit format conversion at boundaries

### Mistake 2: Scattered Validation

**Bad**: Validating the same thing in multiple layers

**Good**: Validate once at the entry point

### Mistake 3: Leaky Abstractions

**Bad**: Component knows about database schema

**Good**: Each layer only knows its neighbors

---

## Checklist for Cross-Layer Features

Before implementation:
- [ ] Mapped the complete data flow
- [ ] Identified all layer boundaries
- [ ] Defined format at each boundary
- [ ] Decided where validation happens

After implementation:
- [ ] Tested with edge cases (null, empty, invalid)
- [ ] Verified error handling at each boundary
- [ ] Checked data survives round-trip

---

## Command And Install Artifact Consistency

In this team kit, command source files live in `claude/commands/trellis/*.md`
and are installed to `.claude/commands/trellis/`. Workflow behavior is also
described in `workflow/`, `entry/`, `prompt.md`, task templates, and
marketplace specs. Treat these as one cross-layer contract.

### Checklist: After Modifying Any Trellis Command Or Workflow Text

- [ ] Update the source command in `claude/commands/trellis/*.md`
- [ ] Update matching workflow docs in `workflow/`, `entry/`, and `prompt.md`
- [ ] Update task templates or examples when artifact expectations changed
- [ ] Run `python3 trellis/scripts/validate_runtime_hardening.py`
- [ ] Run `python3 trellis/scripts/trellis_doctor.py setup` in an installed test project
- [ ] Run `bash bootstrap/smoke-test-install.sh --mode all --developer-name test`
- [ ] After push, run `bash bootstrap/smoke-test-install.sh --mode true-remote --developer-name test`

**Real-world example**: A command can be correct in
`claude/commands/trellis/status.md` but stale in `entry/CLAUDE.md`,
`entry/AGENTS.md`, or `docs/verify-workflow.md`. The installed runtime then
injects mixed guidance even though the command file itself is current.

---

## Generated Runtime Template Upgrade Consistency

Some generated files are both documentation and runtime input. In this team
kit, the installed `.trellis/workflow.md` comes from `workflow/workflow.md` and
is parsed by `claude/hooks/inject-workflow-state.py`, SessionStart behavior,
and helper scripts such as `get_context.py` where available. Runtime blocks
like `[workflow-state:*]` are executable guidance, not prose-only docs.

### Checklist: After Modifying A Runtime-Parsed Template

- [ ] Identify every runtime parser that reads the template, not just the file
  writer that installs it
- [ ] Check whether relevant syntax lives outside obvious managed regions
  such as tag blocks
- [ ] Verify fresh `init` output and the installed
  `.trellis/.team-kit-version` marker
- [ ] Compare local and true-remote installs when published artifacts changed
- [ ] Update the backend spec that owns the runtime contract

**Real-world example**: Adding a new workflow state is not only a prose edit.
The state list, `[workflow-state:*]` blocks, status/continue commands,
validators, examples, and install smoke tests all need to agree, otherwise a
fresh install can tell Claude Code to resume from the wrong phase.

---

## Mode-Detection Probe Checklist

When a CLI auto-detects a mode by probing a remote resource (e.g., checking if `index.json` exists to decide marketplace vs direct download):

### Before implementing:
- [ ] Probe runs in **ALL** code paths that use the result (interactive, `-y`, `--flag` combos)
- [ ] 404 vs transient error are distinguished — don't treat both as "not found"
- [ ] Transient errors **abort or retry**, never silently switch modes
- [ ] Shared state (caches, prefetched data) is **reset** when context changes (e.g., user switches source)
- [ ] **Shortcut paths** (e.g., `--template` skipping picker) must have the same error-handling quality as the probed path — check that downstream functions don't call catch-all wrappers

### After implementing:
- [ ] Trace every path from probe result to the mode-decision branch — no fallthrough
- [ ] External format contracts (giget URI, raw URLs) are tested or at least documented as comments
- [ ] Metadata reads consume a complete response or use a streaming parser — never parse a fixed-size prefix as full JSON
- [ ] When reconstructing a composite identifier from parsed parts, verify **all** fields are included and in the **correct position** (e.g., `provider:repo/path#ref` not `provider:repo#ref/path`)
- [ ] Verify that **action functions** called after a shortcut don't internally use the old catch-all fetch — they must use the probe-quality variant when error distinction matters

**Real-world example**: Custom registry flow had 8 bugs across 3 review rounds: (1) probe only ran in interactive mode, (2) transient errors fell through to wrong mode, (3) giget URI had `#ref` in wrong position, (4) prefetched templates leaked across source switches, (5) `--template` shortcut bypassed probe but `downloadTemplateById` internally used catch-all `fetchTemplateIndex`, turning timeouts into "Template not found".

**Real-world example**: Agent-session update hints fetched npm `latest` metadata with `response.read(4096)` and then parsed it as complete JSON. The `@mindfoldhq/trellis` package metadata exceeded 4 KB, so the JSON was truncated, parse failed silently, and the first session injection showed no update hint. Fix: read the complete response before parsing, and add a regression where `version` is followed by an 8 KB metadata tail.

---

## When to Create Flow Documentation

Create detailed flow docs when:
- Feature spans 3+ layers
- Multiple teams are involved
- Data format is complex
- Feature has caused bugs before
