# Task Level Routing

## Routing Model

The level hierarchy (L0 → L1 → L2 → L3+) remains unchanged, but the decision mechanism has been migrated from the old **heuristic first-match** to a **scorer-based model**.

### Design Philosophy

The rules engine is a **deterministic signal detector**, not a semantic understander. Its core principle:

- **Rules only judge strong deterministic signals** — structured combinations (e.g., `接口 + 返回字段`, `表 + 新增字段`), not individual high-risk nouns.
- **Ambiguous sentences enter UNCERTAIN** — no more patching boundary cases with additional keywords.
- **UNCERTAIN → AI suggestion → User confirmation** — the AI gives a recommended level with reasoning; the user has the final say.
- **High-risk escalation remains explainable, testable, and regressable.**

This direction explicitly abandons the goal of "making rules correctly guess most natural-language boundary sentences."

### Two-Phase Decision Flow

1. **Intent Gate**: Distinguish pure Q&A / explanation requests (L0) from change requests (L1/L2/L3+). This combines question signals, change-action signals, and code/engineering object signals.

2. **Level Scoring**: Score each level (L1/L2/L3+) for change requests:
   - Rules carry type-based weights (keyword +1, phrase +2, regex +2, pair +3, triple +4)
   - Negative rules can suppress specific levels
   - Final decision compares the top score against the runner-up, combined with risk signals

### Uncertainty (UNCERTAIN)

The router returns `UNCERTAIN` when any of the following conditions are met:

- Top score < `min_score` (signal too weak)
- Gap between top score and runner-up < `min_gap` (conflicting signals)
- High-risk context words present but the direct modification target is unclear
- Multiple levels compete without a decisive gap

When `UNCERTAIN` is returned, the system enters a **three-phase closed loop**:

1. **AI Suggestion**: The main model first gives a suggested level (L1/L2/L3+) with a one-sentence reason. The suggestion must be clearly labeled as a recommendation, not a final decision.
   - Example: 「我倾向按 L2 处理。理由：它看起来更像局部实现改动，目前没有看到明确的 API / DB / shared contract 变更信号。」

2. **User Confirmation**: The user can accept the suggestion, choose a different level (L1/L2/L3+), or provide more context for re-evaluation.

3. **No implementation before confirmation**: The system must NOT start implementing until the user has confirmed the routing level.

**Design principle**: The rules engine is a deterministic signal detector, not a semantic understander. Its job is to route when signals are strong and explicitly admit uncertainty when they are not. The AI provides suggestions only in the UNCERTAIN branch — it does NOT replace the rule engine as the primary router. The user has the final say on routing level in uncertain cases.

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

- **Create task**: Optional (AI should recommend inline when the change is clearly local, reversible, and low-risk)
- **Artifacts**: Skippable
- **Execution**: Main session
- **Gates**: Light check

**Signals**: copy/text tweaks, obvious typos, tiny local style changes, one-file comment or wording updates

**Examples**:
- Fix a typo in copy
- Fix an obvious typo in code
- Adjust a very local style
- Change button text from "Submit" to "Save"
- Adjust a form field placeholder

## L2 — Light Implementation

- **Create task**: Recommended
- **Artifacts**: `prd.md`
- **Execution**: Main session or subagent
- **Gates**: `trellis-check`

**Examples**:
- Add simple form validation
- Fix a clear bug
- Add a utility function
- Add a color conversion function
- Add a date formatting utility

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
- Change API response fields for a user list endpoint

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

## Implementation Details

Routing decisions are implemented in `claude/hooks/lib/prompt_routing.py`, with rule configuration stored in `trellis/config/routing_rules.json`.

### Rule Types

| Type     | Weight | Description                              |
|----------|--------|------------------------------------------|
| keyword  | +1     | Single word match, low-weight signal     |
| phrase   | +2     | Fixed phrase match, medium-weight signal |
| regex    | +2     | Regex pattern match, medium-weight signal|
| pair     | +3     | Verb + object match, higher-weight signal|
| triple   | +4     | Subject + verb + object match, highest-weight signal |
| negative | -2/-3  | Negative rule, suppresses a specific level|

### Rule Loading Order

1. `<workspace-root>/.trellis/config/routing_rules.json` (workspace override)
2. `trellis/config/routing_rules.json` (team-kit default rules)

If the workspace override file exists but contains invalid JSON, the system automatically falls back to the default rules.

### Confidence Levels

- `high`: High score with clear gap to runner-up
- `medium`: Adequate score with moderate gap
- `low`: Marginal classification with weak signals (typically accompanies UNCERTAIN)

### Triage Decision Tree

```
User makes a request
├── Intent gate: question? → L0, answer directly
├── Scorer evaluates change signals:
│   ├── L1 score >> others → L1 tiny inline edit
│   ├── L2 score >> others → L2 light task path
│   ├── L3+ score >> others (strong structured signals) → L3+ standard task
│   ├── Scores too close / weak signals / ambiguous target → UNCERTAIN
│   │   └── AI suggests level → User confirms or changes → proceed at confirmed level
│   └── No signal → generic (answer directly or ask)
```
