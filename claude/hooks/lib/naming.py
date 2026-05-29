"""
Team-kit Canonical Naming Constants.

Single source of truth for agent names, skill names, and hook roles.
"""
from __future__ import annotations

# -- Canonical Agent Names ---------------------------------------------------

AGENT_RESEARCH = "trellis-researcher"
AGENT_IMPLEMENT = "trellis-implementer"
AGENT_CHECK = "trellis-checker"
AGENT_SPEC_REVIEWER = "trellis-spec-reviewer"
AGENT_CODE_REVIEWER = "trellis-code-reviewer"
AGENT_ARCHITECTURE_REVIEWER = "trellis-architecture-reviewer"
AGENT_ARCHITECTURE_DEEP_REVIEWER = "trellis-architecture-deep-reviewer"
AGENT_MERGE_REVIEWER = "trellis-merge-reviewer"
AGENT_SPEC_UPDATER = "trellis-spec-updater"

# All agent groups
AGENTS_REVIEW = (
    AGENT_SPEC_REVIEWER, AGENT_CODE_REVIEWER, AGENT_ARCHITECTURE_REVIEWER,
    AGENT_ARCHITECTURE_DEEP_REVIEWER, AGENT_MERGE_REVIEWER,
)
AGENTS_IMPLEMENT_CHECK = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_RESEARCH)
AGENTS_ALL = AGENTS_IMPLEMENT_CHECK + AGENTS_REVIEW + (AGENT_SPEC_UPDATER,)
AGENTS_REQUIRE_TASK = (AGENT_IMPLEMENT, AGENT_CHECK)

# -- Canonical Skill Names ---------------------------------------------------

SKILL_BRAINSTORM = "trellis-brainstorm"
SKILL_GRILL_ME = "trellis-grill-me"
SKILL_DEV_STRATEGY = "trellis-dev-strategy"
SKILL_BEFORE_DEV = "trellis-before-dev"
SKILL_IMPLEMENT = "trellis-implement"
SKILL_CHECK = "trellis-check"
SKILL_SPEC_REVIEW = "trellis-spec-review"
SKILL_CODE_REVIEW = "trellis-code-review"
SKILL_CODE_ARCHITECTURE_REVIEW = "trellis-code-architecture-review"
SKILL_IMPROVE_CODEBASE_ARCHITECTURE = "trellis-improve-codebase-architecture"
SKILL_UPDATE_SPEC = "trellis-update-spec"
SKILL_BREAK_LOOP = "trellis-break-loop"
SKILL_MERGE_REVIEW = "trellis-merge-review"
SKILL_FINISH_WORK = "trellis-finish-work"

ALL_SKILLS = (
    SKILL_BRAINSTORM, SKILL_GRILL_ME, SKILL_DEV_STRATEGY, SKILL_BEFORE_DEV,
    SKILL_IMPLEMENT, SKILL_CHECK, SKILL_SPEC_REVIEW, SKILL_CODE_REVIEW,
    SKILL_CODE_ARCHITECTURE_REVIEW, SKILL_IMPROVE_CODEBASE_ARCHITECTURE,
    SKILL_UPDATE_SPEC, SKILL_BREAK_LOOP, SKILL_MERGE_REVIEW, SKILL_FINISH_WORK,
)

# -- Hook Role Labels --------------------------------------------------------

ROLE_RESEARCHER = "researcher"
ROLE_IMPLEMENTER = "implementer"
ROLE_CHECKER = "checker"
ROLE_REVIEWER = "reviewer"
ROLE_UPDATER = "updater"
ROLE_ORCHESTRATOR = "orchestrator"

# -- Workflow States ---------------------------------------------------------

STATE_NO_TASK = "NO_TASK"
STATE_PLANNING_PRD = "PLANNING_PRD"
STATE_PLANNING_GRILL = "PLANNING_GRILL"
STATE_PLANNING_DESIGN = "PLANNING_DESIGN"
STATE_PLANNING_IMPLEMENT = "PLANNING_IMPLEMENT"
STATE_WAITING_APPROVAL = "WAITING_IMPLEMENTATION_APPROVAL"
STATE_IN_PROGRESS = "IN_PROGRESS"
STATE_BEFORE_DEV = "BEFORE_DEV"
STATE_IMPLEMENTING = "IMPLEMENTING"
STATE_CHECKING = "CHECKING"
STATE_REVIEWING = "REVIEWING"
STATE_UPDATING_SPEC = "UPDATING_SPEC"
STATE_COMMITTING = "COMMITTING"
STATE_MERGE_REVIEWING = "MERGE_REVIEWING"
STATE_VALIDATING = "VALIDATING"
STATE_FINISHING = "FINISHING"
STATE_DONE = "DONE"

# States where source editing is forbidden
PLANNING_STATES = {
    STATE_PLANNING_PRD, STATE_PLANNING_GRILL, STATE_PLANNING_DESIGN,
    STATE_PLANNING_IMPLEMENT, STATE_WAITING_APPROVAL,
}
