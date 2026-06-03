# Trellis Team Kit

Claude Code 优先的 Trellis 团队 AI 编程工作流套件。

## 这是什么

trellis-team-kit 是一个**工作流套件**，架设在官方
[Trellis](https://github.com/mindfoldhq/trellis) 任务管理系统之上，强化 AI 编程体验：

- 明确的 **21 状态工作流状态机**，Claude Code 严格遵循
- **L0-L5 任务分级路由**，按复杂度匹配流程严格度
- **双同意门禁**，把"创建任务"和"开始实现"彻底分开
- **Before-dev 门控**，实现前必须读取所有 artifacts 并声明约束
- **范围守卫**，编辑未声明路径触发 warning，高风险路径触发 block
- **14 个阶段 skills**，覆盖 brainstorm、grill-me、design、implement、check、review 等
- **9 个专用 subagents**，隔离执行研究、实现、检查和审查
- **9 个守护 hooks**，注入工作流状态、阻断危险操作、强制执行门禁
- **Review Gate Contract**，串行 PASS/FAIL 强制执行，失败回流
- **Spec 驱动的团队知识库**，存放在 `.trellis/spec/` 作为持久化项目记忆
- **运行时验证** — 静态验证器 + finish 前自动校验，关键路径全强制

这不是一个 prompt 包。这是一个 **Claude Code-first 的 Trellis 工作流套件**，
hooks 注入状态，门禁可执行，产物一等公民，运行时可验证。

## 为什么需要

AI 编程助手强大但缺乏纪律。没有护栏时它们会：

- 没理解需求就跳进实现
- 跳过质量检查和审查
- 跨会话忘记项目约定
- 分不清 typo 修复和架构变更
- 改爆全仓库而不自知

trellis-team-kit 用**规划优先、产物优先、门禁优先**的工作流解决这个问题，
由 hooks 强制执行，不靠运气。

## 架构

```text
Trellis 掌管任务真相。       → task 状态、PRD、验收标准
Claude Code 掌管运行时。     → 会话、hooks、subagents、skills
Superpowers 掌管深度推理。   → 需求不清、架构权衡
OMC 掌管并行执行。          → 多 agent 编排（可选）
Specs 掌管团队知识。        → 可复用标准、指南、约定
Hooks 掌管状态注入。        → 工作流面包屑、护栏、上下文
Skills 掌管可重复阶段。     → brainstorm、grill、design、implement、check
Subagents 掌管隔离工作。    → 研究、实现、检查、审查
主会话掌管集成。           → 决策、用户沟通、最终合并
```

## 完整工作流（21 步）

```text
用户需求
  → NO_TASK
    → TRIAGE（分类 L0-L5）
      → TASK_CREATED（task.py create）
        → PLANNING_PRD（brainstorm → prd.md）
          → PLANNING_GRILL（grill-me → 挑刺 PRD）
            → PLANNING_DESIGN（L3+ 出 design.md）
              → PLANNING_IMPLEMENT（implement.md + review gate contract）
                → WAITING_IMPLEMENTATION_APPROVAL
                  → IN_PROGRESS（task.py start）
                    → BEFORE_DEV（读取 artifacts/specs → before-dev.md）
                      → IMPLEMENTING
                        → CHECKING
                          → REVIEWING（spec → code → architecture → deep）
                            → UPDATING_SPEC
                              → COMMITTING
                                → MERGE_REVIEWING（L4/L5）
                                  → VALIDATING（build/test）
                                    → FINISHING（归档 + 日志）
                                      → DONE
```

每个状态都有：进入条件、必需产物、允许操作、禁止操作、退出条件、下一状态。

## 任务分级（L0-L5）

| 级别 | 类型 | 创建 Task | 必需产物 | 门禁 |
|------|------|:--------:|---------|------|
| L0 | 纯问答/解释/分析 | 否 | 无 | 无 |
| L1 | typo/极小改动/文案 | 可选 | AI 可建议 inline | 轻量检查 |
| L2 | 轻量实现 | 建议 | prd.md | check |
| L3 | 普通 feature/bugfix | 是 | prd.md + implement.md + JSONLs | check + code-review |
| L4 | 复杂跨层任务 | 是 | prd.md + design.md + implement.md + JSONLs | check + spec-review + code-review + architecture-review |
| L5 | 多 agent/大重构 | 是 | 全量产物 | 全部门禁 + merge-review |

**AI 可以在明显 L1、局部、可逆、低风险时建议 inline；一旦范围扩大、触及共享/高风险区域，立即升级为 task。**

**如果请求边界模糊，路由器不会强行猜级别，而是返回 `UNCERTAIN`：先由 AI 给出建议等级和一句理由，再由用户确认、改级或补充上下文；在用户确认前，不开始实现。**

## 双同意门禁

**创建 task 的同意 ≠ 开始实现的同意。** 两个独立门禁：

1. **Task 创建同意** — 用户同意创建 task → 仅进入规划阶段
2. **实现同意** — 用户明确批准 → `task.py start` 然后写代码

规划阶段：禁止编辑源码、禁止 spawn implementer、禁止 `task.py start`。
Hooks 强制执行这些规则。

## Before-dev 门控

进入实现阶段前，AI 必须运行 `trellis-before-dev` skill，读取所有 artifacts
（prd.md、design.md、implement.md、implement.jsonl、check.jsonl、specs、research），
并输出 `before-dev.md` 约束文件。

**没有 before-dev.md 就不能编辑源码。** `protect-dangerous-actions` hook 强制执行。

before-dev.md 必须填写：
- **Scope** — 实现范围
- **Files likely touched** — 预计修改的文件

## 范围守卫

实现阶段中，hooks 会检查编辑的文件是否在 `implement.md` 声明的范围内：

- **未声明路径** → PostToolUse warning
- **高风险未声明路径**（auth、migration、schema、API、shared types）→ PreToolUse soft block
- **过宽声明**（`*`、`src/*`）→ warning，建议用更具体的路径

Soft block 可通过 `override team-kit guardrail: <reason>` 绕过。

## Review Gates（审查门禁）

串行执行，固定顺序。选中门禁在 `implement.md` 的 Review Gate Contract 中配置：

```text
1. trellis-check          （始终必跑）
2. trellis-spec-review    （L4+）
3. trellis-code-review    （L3+）
4. trellis-code-architecture-review （L4+）
5. trellis-improve-codebase-architecture deep-review （L5）
6. trellis-merge-review   （L5 / worktree / 多 agent）
```

每个 review 输出 PASS/FAIL 及 blocking issues。任何 FAIL → 回到
IMPLEMENTING → 修复 → 重新 check → 重新 review。不可跳过。

**L3+ 必须选择对应级别的 review gate，未选够 = FAIL。**

## Finish 前自动验证

`stop-guard` hook 在任务完成前自动运行：

1. `validate_task.py` — 检查必需产物是否齐全、JSONL 是否非空、finish.md 是否存在，且 `Observable Outcomes` 有具体结果与证据
2. `validate_review_gates.py` — 检查 mandatory gates 是否选中、review 文件是否存在且有结论

任一验证失败 → block finish。

## 面包屑自动推断

`inject-workflow-state` hook 根据 task.json 状态和 artifact 存在情况，
自动推断精确的子阶段（PLANNING_PRD/GRILL/DESIGN/IMPLEMENT 等），
并注入推荐的下一步 skill。不依赖 AI 手动维护 workflow.md 面包屑。

## 安装后你会得到什么

```
AGENTS.md                  ← AI agent 入口
CLAUDE.md                  ← Claude Code 入口
.trellis/.team-kit-version ← 版本标记
.claude/
  settings.json            ← 团队 Claude Code 配置（hooks、skills、权限）
  skills/                  ← 14 个 Trellis 阶段 skills
  agents/                  ← 9 个专用 subagents
  hooks/                   ← 9 个工作流守护 hooks + 6 个 hook libs
  commands/trellis/        ← 7 个 Slash 命令
.trellis/
  workflow.md              ← 完整状态机
  spec/                    ← 分层团队知识库
  templates/               ← Task 产物模板（含 before-dev.md）
  scripts/                 ← 7 个静态验证器
  tasks/                   ← 活跃和已归档任务
  workspace/               ← 个人开发者日志
```

## 安装

### 环境要求

- Node.js 18+
- Python 3.9+
- git
- 官方 Trellis：`npm install -g @mindfoldhq/trellis`

### 新项目初始化

```bash
mkdir my-project && cd my-project && git init
bash <(curl -fsSL https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh) 你的名字
```

### 已有项目

```bash
cd existing-project
bash <(curl -fsSL https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh) 你的名字
```

如果 `raw.githubusercontent.com` 超时，用克隆方式：

```bash
git clone https://github.com/05allan1213/trellis-team-kit.git ~/trellis-team-kit
mkdir my-project && cd my-project && git init
~/trellis-team-kit/bootstrap/init.sh 你的名字
```

### 本地个人配置

团队初始化后，每个开发者在项目目录中运行：

```bash
bash ~/trellis-team-kit/bootstrap/init-local.sh 你的名字
```

这会创建个人工作区和日志文件。


## 安全守卫

hooks 保护工作流：

| Hook | 触发事件 | 作用 |
|------|---------|------|
| session-start | SessionStart | 注入仓库/分支/task 上下文 |
| inject-workflow-state | UserPromptSubmit | 注入当前状态面包屑 + 子阶段推断 + skill 推荐 |
| inject-subagent-context | SubagentStart | 注入 artifacts 到 subagent |
| protect-dangerous-actions | PreToolUse | 阻断危险操作、规划期改源码、无 before-dev 改源码、高风险未声明路径 |
| post-edit-reminder | PostToolUse | 编辑后提醒 + 范围守卫 warning |
| subagent-stop-guard | SubagentStop | 强制 subagent 输出含 PASS/FAIL |
| stop-guard | Stop | 阻止过早声称"完成"，自动运行 validators |
| pre-compact-save-state | PreCompact | 压缩前保存会话状态 |
| trellis-notify | Notification / Stop | 桌面通知提醒 |


## 团队推广

团队推广路径：Dogfood → 试点 → 全团队。第一周检查清单、常见失败模式见 Hook 和护栏的内置错误提示。

## 示例

见 `examples/` 目录：

- `01-typo-tiny-edit.md` — L1：极小改动，推荐 inline
- `02-simple-bugfix.md` — L2：轻量 bugfix
- `03-normal-feature.md` — L3：标准功能，含 design 和 review
- `04-cross-layer-api-change.md` — L4：跨层 API 变更
- `07-refactor.md` — L4：架构重构
- `08-multi-agent-parent-child-task.md` — L5：多 agent parent/child
- `examples/bugfix/` — L3 bugfix 完整产物示例
- `examples/feature/` — L3 feature 完整产物示例
- `examples/refactor/` — L4 重构完整产物示例

## 常见问题

**Q: 什么时候可以跳过 Trellis？**
A: L0 直接问即可。L1 如果是明显局部、可逆、低风险的小改，AI 应先建议 inline；如果范围扩大或你要留痕，再升级成 task。L2+ 默认建议创建 task。

**Q: Hook 阻断了我需要的操作怎么办？**
A: Hooks 区分 hard block（危险操作）和 soft warning（编辑共享类型等）。Soft warning 可带原因绕过。Hard block 不可绕过。

**Q: 必须用 OMC 并行模式吗？**
A: 不。OMC 是可选的，只在 PRD 确认且工作可安全拆分时推荐。

**Q: 怎么知道用哪个任务级别？**
A: 明确信号足够强时，AI 会直接分类：L1 适合明显局部小修，L2 适合轻量实现，L3 适合普通功能/bugfix，L4 适合跨层改动，L5 适合多 agent 工作。边界模糊时不会强行猜，而是进入 `UNCERTAIN`，先给建议等级和理由，再由你确认、改级或补充上下文。

**Q: before-dev.md 是什么？**
A: 实现阶段前的约束文件。AI 必须先运行 trellis-before-dev skill 读取所有 artifacts，填写 scope 和 files likely touched，然后才能编辑源码。这是防止 AI 盲目写代码的门控。

## 运行时验证

运行静态验证：

```bash
python3 .trellis/scripts/validate_runtime_hardening.py
```

验证单个任务：

```bash
python3 .trellis/scripts/validate_task.py .trellis/tasks/T001-xxx
python3 .trellis/scripts/validate_review_gates.py .trellis/tasks/T001-xxx
```

## 维护者参考

| 改什么 | 改哪里 |
|-------|--------|
| 团队 AI 工作流规范 | `marketplace/specs/web-app/` |
| 团队入口文件 | `entry/` |
| 团队工作流 | `workflow/` |
| 日常提示词模板 | `prompt.md` |
| Skills | `claude/skills/` |
| Agents | `claude/agents/` |
| Hooks | `claude/hooks/` |
| 安装脚本 | `bootstrap/` |
| OMC 策略 | `omc/` |
| 验证器 | `validators/` |

## 版本

当前：0.3.0

版本历史见 `CHANGELOG.md`。
