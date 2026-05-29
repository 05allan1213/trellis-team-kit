# 命名映射表

Skills、Agents、Hooks 和 Workflow States 之间的一致命名。

## 工作流状态 → Skill → Agent → Hook 角色

| 工作流步骤 | 状态 | Skill | Agent | Hook 角色 | 输出 |
|---|---|---|---|---|---|
| 实现 | IMPLEMENTING | trellis-implement | trellis-implementer | implementer | 实现摘要 |
| 检查 | CHECKING | trellis-check | trellis-checker | checker | validation/check 输出 |
| Spec 审查 | REVIEWING | trellis-spec-review | trellis-spec-reviewer | reviewer | review/spec-review.md |
| 代码审查 | REVIEWING | trellis-code-review | trellis-code-reviewer | reviewer | review/code-review.md |
| 架构审查 | REVIEWING | trellis-code-architecture-review | trellis-architecture-reviewer | reviewer | review/architecture-review.md |
| 深度审查 | REVIEWING | trellis-improve-codebase-architecture | trellis-architecture-deep-reviewer | reviewer | review/architecture-deep-review.md |
| 合并审查 | MERGE_REVIEWING | trellis-merge-review | trellis-merge-reviewer | reviewer | review/merge-review.md |
| 研究 | PLANNING_PRD | trellis-research（通过 brainstorm） | trellis-researcher | researcher | research/ |
| Spec 更新 | UPDATING_SPEC | trellis-update-spec | trellis-spec-updater | updater | finish.md |
| 头脑风暴 | PLANNING_PRD | trellis-brainstorm | — | — | prd.md |
| 挑刺 PRD | PLANNING_GRILL | trellis-grill-me | — | — | research/grill-me.md |
| 开发策略 | PLANNING_IMPLEMENT | trellis-dev-strategy | — | — | implement.md |
| 开发前准备 | BEFORE_DEV | trellis-before-dev | — | — | 约束摘要 |
| 打破循环 | （任意） | trellis-break-loop | — | — | research/break-loop.md |
| 收尾 | FINISHING | trellis-finish-work | — | — | 归档 + 日志 |

## 命名约定

| 类型 | 模式 | 示例 |
|---|---|---|
| Skill | `trellis-<动作>` | `trellis-implement` |
| Agent | `trellis-<角色>-er` 或 `trellis-<角色>-reviewer` | `trellis-implementer`、`trellis-code-reviewer` |
| Hook 角色标签 | `<角色>` | `implementer`、`checker`、`reviewer` |
| Review 输出文件 | `review/<门禁名称>.md` | `review/code-review.md` |
| 工作流状态 | `大写_蛇形命名` | `IMPLEMENTING`、`CHECKING` |

## Hook 事件 → Hook 脚本

| Hook 事件 | 脚本 | 用途 |
|---|---|---|
| SessionStart | session-start.py | 注入仓库/分支/task 上下文 |
| UserPromptSubmit | inject-workflow-state.py | 注入当前工作流状态面包屑 |
| PreToolUse（Task） | inject-subagent-context.py | 向 subagent 派发注入 artifacts |
| PreToolUse（Task） | protect-dangerous-actions.py | 阻断危险操作 |
| PreToolUse（Bash） | protect-dangerous-actions.py | 阻断危险 bash 命令 |
| PostToolUse（Write/Edit） | post-edit-reminder.py | 编辑后提醒工作流约束 |
| SubagentStop | subagent-stop-guard.py | 强制 review 输出含 PASS/FAIL |
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
