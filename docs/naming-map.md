# Canonical Naming Map

Skills、Agents、Hooks 和 Workflow States 之间的一致命名。v0.3 硬化版本。

## 完整映射表

| Workflow Step | State | Skill | Agent | Hook Role | Output |
|---|---|---|---|---|---|
| Research | PLANNING_PRD | trellis-brainstorm | trellis-researcher | researcher | research/evidence.md |
| Grill PRD | PLANNING_GRILL | trellis-grill-me | trellis-researcher | researcher | research/grill-me.md |
| Dev Strategy | PLANNING_IMPLEMENT | trellis-dev-strategy | main-session | orchestrator | implement.md |
| Before Dev | BEFORE_DEV | trellis-before-dev | main-session | orchestrator | context summary |
| Implementation | IMPLEMENTING | trellis-implement | trellis-implementer | implementer | implementation summary |
| Check | CHECKING | trellis-check | trellis-checker | checker | validation/check-results.md |
| Spec Review | REVIEWING | trellis-spec-review | trellis-spec-reviewer | reviewer | review/spec-review.md |
| Code Review | REVIEWING | trellis-code-review | trellis-code-reviewer | reviewer | review/code-review.md |
| Architecture Review | REVIEWING | trellis-code-architecture-review | trellis-architecture-reviewer | reviewer | review/architecture-review.md |
| Deep Architecture Review | REVIEWING | trellis-improve-codebase-architecture deep-review | trellis-architecture-deep-reviewer | reviewer | review/architecture-deep-review.md |
| Spec Update | UPDATING_SPEC | trellis-update-spec | trellis-spec-updater | updater | spec update decision |
| Merge Review | MERGE_REVIEWING | trellis-merge-review | trellis-merge-reviewer | reviewer | review/merge-review.md |
| Finish | FINISHING | trellis-finish-work | main-session | orchestrator | finish.md |

## 命名约定

| 类型 | 规范 | 示例 |
|---|---|---|
| Workflow state | 全大写动名词 | `IMPLEMENTING` |
| Skill | 动词流程名 | `trellis-implement` |
| Agent | 角色名 | `trellis-implementer` |
| Hook role | 短角色名 | `implementer` |
| Output file | 结果语义名 | `review/code-review.md` |
| Template | artifact 名 | `implement.md.tmpl` |

## Hook 事件 → Hook 脚本

| Hook 事件 | 脚本 | 用途 |
|---|---|---|
| SessionStart | session-start.py | 注入仓库/分支/task 上下文 |
| UserPromptSubmit | inject-workflow-state.py | 注入当前工作流状态面包屑 |
| SubagentStart | inject-subagent-context.py | 向 subagent 注入 artifacts 上下文 |
| PreToolUse (Edit\|Write\|Bash) | protect-dangerous-actions.py | 阻断危险操作 |
| PostToolUse (Write\|Edit) | post-edit-reminder.py | 编辑后提醒工作流约束 |
| SubagentStop | subagent-stop-guard.py | 强制 subagent 输出含 PASS/FAIL |
| Stop | stop-guard.py | 阻止过早声称"完成" |
| PreCompact | pre-compact-save-state.py | 压缩前保存会话状态 |
| Notification | trellis-notify.sh | 桌面通知（Stop/Notification 事件触发） |

## Agent Frontmatter 名称

| 文件 | frontmatter `name` |
|---|---|
| claude/agents/trellis-researcher.md | trellis-researcher |
| claude/agents/trellis-implementer.md | trellis-implementer |
| claude/agents/trellis-checker.md | trellis-checker |
| claude/agents/trellis-spec-reviewer.md | trellis-spec-reviewer |
| claude/agents/trellis-code-reviewer.md | trellis-code-reviewer |
| claude/agents/trellis-architecture-reviewer.md | trellis-architecture-reviewer |
| claude/agents/trellis-architecture-deep-reviewer.md | trellis-architecture-deep-reviewer |
| claude/agents/trellis-merge-reviewer.md | trellis-merge-reviewer |
| claude/agents/trellis-spec-updater.md | trellis-spec-updater |

## Gate 文件映射

| Gate | File |
|---|---|
| trellis-spec-review | review/spec-review.md |
| trellis-code-review | review/code-review.md |
| trellis-code-architecture-review | review/architecture-review.md |
| trellis-improve-codebase-architecture deep-review | review/architecture-deep-review.md |
| trellis-merge-review | review/merge-review.md |
