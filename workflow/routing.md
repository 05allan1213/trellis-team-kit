# Task Level Routing

## L0 — Pure Q&A / Explanation / Analysis

- **Create task**: No
- **Artifacts**: None
- **Execution**: Main session direct answer
- **Gates**: None

**Examples**:
- "What does this function do?"
- "How do I use React useEffect?"
- "What does our database schema look like?"

## L1 — Tiny Change / Typo / Copy

- **Create task**: Optional (user must explicitly say skip)
- **Artifacts**: Skippable
- **Execution**: Main session
- **Gates**: Light check

**Trigger phrases**: "skip trellis" / "no task" / "just do it" / "don't create a task"

**Examples**:
- Fix a typo in copy
- Fix an obvious typo in code
- Adjust a very local style

## L2 — Light Implementation

- **Create task**: Yes
- **Artifacts**: `prd.md`
- **Execution**: Main session or subagent
- **Gates**: `trellis-check`

**Examples**:
- Add simple form validation
- Fix a clear bug
- Add a utility function

## L3 — Normal Feature / Bugfix

- **Create task**: Yes
- **Artifacts**: `prd.md` + `implement.md` + `design.md` (optional)
- **Execution**: subagent
- **Gates**: check + code-review

**Examples**:
- Add a CRUD feature
- Modify an API endpoint
- Add a new page component

## L4 — Complex Cross-Layer Task

- **Create task**: Yes
- **Artifacts**: `prd.md` + `design.md` + `implement.md` + research
- **Execution**: subagent + worktree or OMC
- **Gates**: check + spec-review + code-review + architecture-review

**Examples**:
- Feature spanning frontend + backend API contract
- Database schema + API + frontend changes
- Add auth/authorization system
- Modify shared types/utils/config

## L5 — Multi-Agent / Large Refactor / Architecture

- **Create task**: Yes
- **Artifacts**: Full artifacts
- **Execution**: OMC + worktree + parent/child task
- **Gates**: All gates + merge-review

**Examples**:
- Refactor an entire module
- Multi-service coordinated changes
- Cross-package architecture adjustment
- Complex requirement needing multiple parallel agents

## Triage Decision Tree

```
User makes a request
├── Pure Q&A? → L0, answer directly
├── Typo/copy/tiny change? → Ask if skip Trellis
│   ├── User says skip → L1, inline
│   └── User says create task → classify L2-L5
├── Implementation request → Suggest creating task
│   ├── Single file / simple logic → L2
│   ├── Multiple files / one package → L3
│   ├── Cross-layer / API / schema / auth → L4
│   └── Multi-package / refactor / architecture → L5
└── Unsure → Ask user about scope, then classify
```
