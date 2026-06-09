---
name: trellis-merge-review
description: "Review integration after worktree, parallel/workstream multi-subagent execution, OMC parallel, PR merge, conflict resolution, or parent/child integration. Checks conflict resolution logic, duplicate implementations, missing files, and interface inconsistencies between agents. Outputs to review/merge-review.md with PASS/FAIL."
---

# Trellis Merge Review

## Preconditions

One or more trigger conditions are met:
- Worktree used (changes need to merge back to main branch)
- Parallel/workstream multi-subagent execution (multiple agents produced code independently)
- OMC parallel execution (parallel agents worked on different parts)
- PR merge pending
- Conflict resolution was performed
- Parent/child task integration (child outputs need to integrate into parent)

## Core Rules

Merge review is about integration quality - whether the combined output of multiple sources is coherent and complete. It is not about individual code quality (that is `trellis-code-review`).

For L4/L5 tasks, merge review is required when the task used worktree, parallel/workstream multi-subagent execution, OMC, PR merge, conflict resolution, or parent/child structure.

Ordinary serial Trellis implementer/checker/reviewer subagents require
`agent-results/*.json`, but they do not by themselves require merge-review.

OMC is an optional advanced execution path, not the default. If OMC output is present, merge review must confirm that the task has explicit OMC approval before treating those outputs as valid merge sources.

## Workflow

1. **Identify the merge sources** - which worktrees, agents, or child tasks contributed code.
2. **Read all changed files** - `git diff` from the merge base.
3. **Read task artifacts** - `prd.md`, `design.md`, `implement.md`.
4. **Read and aggregate machine-readable task artifacts**:
   - `{TASK_DIR}/agent-results/*.json`
   - `{TASK_DIR}/runtime/guardrail-overrides.jsonl`
   - `{TASK_DIR}/scope-manifest.json`
5. **Check each dimension** below.
6. **Write findings** to `review/merge-review.md`.

### Dimensions

#### Agent Result Aggregation

- Read every `{TASK_DIR}/agent-results/*.json` file and aggregate `agent`, `status`, `changed_files`, `validation`, `blocking_issues`, `non_blocking_issues`, `risks`, `scope_expansion`, and `execution_mode`.
- Report duplicate changed files across agents as an integration risk, including which agents reported each path.
- Report failed validation from any agent result.
- Report unresolved blocking issues from any agent result.
- Treat malformed or missing required result fields as blocking if they prevent reliable aggregation.

#### Scope Manifest Compliance

- Read `{TASK_DIR}/scope-manifest.json`.
- Compare aggregated changed files and `git diff --name-only` against `declared_paths` and `declared_globs`.
- Report any undeclared changed path unless it is explicitly covered by a reviewed scope expansion.

#### Guardrail Override Review

- Read `{TASK_DIR}/runtime/guardrail-overrides.jsonl` when it exists.
- Report any guardrail override that is not explicitly reviewed in the task finish/review artifacts.
- Treat unreviewed guardrail overrides as blocking.

#### OMC Approval Check

- If any merge source, agent result, execution mode, or task artifact indicates OMC output, confirm `implement.md` records explicit OMC approval.
- Report OMC outputs without explicit OMC approval as blocking.
- Do not require OMC for ordinary worktree or Trellis-native multi-agent execution.

#### Conflict Resolution Logic

- Were there merge conflicts? How were they resolved?
- Did conflict resolution preserve the intent of both sides?
- Did conflict resolution introduce logical errors (e.g., kept the wrong branch's code)?
- Are there residual conflict markers (`<<<<<<`, `======`, `>>>>>>`)?

#### Duplicate Implementations

- Did multiple agents implement the same functionality independently?
- Are there two versions of the same utility or type?
- Are there overlapping API endpoints or routes?
- Should duplicate implementations be consolidated?

#### Missing Files

- Did an agent's output fail to get included in the merge?
- Are there files that were created in a worktree but not merged?
- Are there test files missing from the final result?
- Are there config or migration files that were supposed to be included?

#### Interface Inconsistencies

- Do different agents use the same interface differently?
- Are shared types consistent across agent outputs?
- Are API contracts the same between frontend and backend changes?
- Are error handling patterns consistent across merged code?

#### Integration Completeness

- Does the merged result satisfy all acceptance criteria from `prd.md`?
- Are all child task deliverables integrated into the parent?
- Are there orphaned pieces of code that no longer connect to anything?
- Are there TODO items left from individual agents that need resolution?

## Output Format

### review/merge-review.md

```markdown
# Merge Review: [Task Title]

## Merge Sources
- [source]: [what it contributed]
- [source]: [what it contributed]

## Conflict Resolution Logic
- [conflict description]: [how resolved] - [correct?]
- (or "no conflicts")

## Duplicate Implementations
- [duplicate]: [source A vs source B] - [recommended consolidation]
- (or "none")

## Missing Files
- [expected file]: [which source should have produced it] - [status]
- (or "none")

## Agent Results Aggregation
- Results read: [list of agent-results JSON files]
- Duplicate changed files across agents: [path -> agents] (or "none")
- Failed validation: [agent -> validation failure] (or "none")
- Unresolved blocking issues: [agent -> issue] (or "none")

## Scope Manifest Check
- scope-manifest.json: [present / missing / malformed]
- Undeclared changed paths: [paths] (or "none")
- Scope expansions reviewed: [summary]

## Guardrail Override Check
- runtime/guardrail-overrides.jsonl: [absent / present]
- Overrides reviewed: [yes / no / not applicable]
- Unreviewed overrides: [entries] (or "none")

## OMC Approval Check
- OMC outputs detected: [yes / no]
- Explicit OMC approval: [yes / no / not applicable]
- OMC approval issues: [summary] (or "none")

## Interface Inconsistencies
- [interface]: [how sources differ] - [which is correct per design.md]
- (or "none")

## Integration Completeness
- [AC from prd.md]: [satisfied by merged result?]
- [AC from prd.md]: [satisfied by merged result?]

## Blocking Issues
1. [issue]: [why it blocks merge]
(or "none")

## Non-Blocking Issues
1. [suggestion]: [improvement rationale]
(or "none")

## Verdict
- PASS - merge is coherent and complete
- FAIL - must resolve blocking issues:
  1. [blocking issue summary]
```

## Quality Bar

- All merge sources are identified and their contributions mapped.
- Machine-readable agent results, guardrail overrides, and scope manifest are read and aggregated.
- Duplicate changed files across agents are reported.
- Changed paths outside `scope-manifest.json` declarations are reported.
- Failed validation and unresolved blocking issues from agent results are reported.
- Guardrail overrides are confirmed reviewed before PASS.
- OMC outputs are blocked unless explicit OMC approval is present; OMC remains optional and advanced, not default.
- Conflict resolution is checked for correctness, not just absence of markers.
- Duplicate implementations are flagged for consolidation.
- Missing files are identified by comparing expected outputs against actual.
- Integration completeness is verified against `prd.md` acceptance criteria.
- FAIL verdict is honest - incomplete integration will cause problems later.
