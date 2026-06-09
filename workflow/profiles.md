# Workflow Profiles

Workflow profiles translate task levels into execution friction. Levels answer
"how complex is this request"; profiles answer "how much process is justified".

| Profile | Levels | Task | Execution | Required gates |
|---|---|---|---|---|
| quick | L1 | optional | main session | light-check |
| light | L2 | recommended | single Trellis subagent by default; main session only with explicit inline override | trellis-check |
| standard | L3 | required | Trellis subagents | trellis-check + trellis-code-review |
| strict | L4 | required | Trellis subagents by default; set `Branch strategy` to dedicated worktree when useful | trellis-check + spec-review + code-review + architecture-review + conditional merge-review when the validator trigger contract applies |
| orchestrated | L5 | required | Trellis-native parallel + worktree by default | all selected gates + trellis-merge-review |

## Rules

- L1 stays low-friction unless scope expands.
- L2 keeps planning light: `prd.md` plus minimal `implement.md` can be enough; execution still uses the Trellis subagent path by default.
- L3 uses normal Trellis task flow with code review.
- L4 requires `design.md` and architecture review because API, schema, auth,
  infra, shared types, or cross-layer behavior can break contracts.
- L5 uses parent/child planning and merge review. Prefer Trellis-native
  parallel + worktree first.
- OMC `ulw/ultrawork` is an advanced L4/L5 execution option. It requires
  explicit user approval and never replaces PRD, check, review, merge-review,
  or finish.

The machine-readable profile map lives at `trellis/config/workflow_profiles.json`.
