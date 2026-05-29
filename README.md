# trellis-team-kit

Claude Code 优先的 Trellis 团队 AI 编程工作流套件。在官方 Trellis 底座上融合了 Herbivore 风格的工作流纪律、Superpowers 深度推理和 OMC 并行执行。

## 特性

- **完整状态机** — 从 NO_TASK 到 DONE 共 20 个显式状态
- **L0-L5 任务分级** — 从纯问答到多 agent 架构，复杂度逐步递增
- **双同意门禁** — 创建 task ≠ 批准实现，两阶段独立确认
- **14 个阶段 skills** — brainstorm、grill-me、dev-strategy、before-dev、implement、check 以及 8 个 review skills
- **9 个专用 subagents** — researcher、implementer、checker、5 个 reviewer、spec-updater
- **8 个守护 hooks** — session 上下文注入、workflow 状态提醒、subagent 上下文注入、stop 守卫、危险操作保护等
- **Review Gate Contract** — 可配置的逐任务审查门禁，PASS/FAIL 强制执行
- **团队 AI 工作流规范** — marketplace 驱动的 spec 系统，约束 AI 行为而非个人编码风格
- **完整吸收 Herbivore 工作流** — planning-first、artifact-first、gate-first、spec-updating、finish-separated

## 设计哲学

```text
Trellis 掌管任务真相。
Claude Code 掌管运行时。
Superpowers 掌管深度推理。
OMC 掌管执行编排。
Specs 掌管可复用团队知识。
Hooks 掌管状态注入和护栏。
Skills 掌管可重复的阶段流程。
Subagents 掌管隔离执行和审查。
主会话掌管决策、用户沟通和最终合并。
```

## 快速开始

### 环境要求

- Node.js 18+
- Python 3.9+
- git
- 官方 Trellis：`npm install -g @mindfoldhq/trellis`

### 新项目初始化

```bash
mkdir my-project && cd my-project
bash <(curl -fsSL https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh) 你的名字
```

一行搞定。把 `你的名字` 换成你的英文名。

## 初始化后你会得到什么

```
AGENTS.md              ← AI agent 入口
CLAUDE.md              ← Claude Code 入口
.claude/
  settings.json        ← 团队 Claude Code 配置
  skills/              ← 14 个 Trellis 阶段 skills
  agents/              ← 9 个专用 subagents
  hooks/               ← 8 个 workflow 守护 hooks
  commands/            ← Slash 命令
.trellis/
  workflow.md          ← 完整状态机
  spec/                ← 分层团队知识库
  templates/           ← Task 产物模板
  tasks/               ← 活跃和已归档任务
```

## 日常使用

启动一个标准任务：

> 我们开始一个 Trellis 任务，走 B Create a task，不要 inline。

极小改动跳过 Trellis：

> 跳过 Trellis，直接把 README 里的 typo 改掉。

确认规划，批准实现：

> Plan 阶段已确认，批准实现。

完成任务：

> 进入 Finish 阶段，按 workflow Phase 3 收尾。

## 任务分级

| Level | 类型 | 创建 Task | 核心产物 | 门禁 |
|-------|------|----------|---------|------|
| L0 | 纯问答/解释/分析 | 否 | 无 | 无 |
| L1 | typo/极小改动/文案 | 可选 | 可跳过 | 轻量检查 |
| L2 | 轻量实现 | 是 | prd.md | check |
| L3 | 普通 feature/bugfix | 是 | prd.md + implement.md | check + code-review |
| L4 | 复杂跨层任务 | 是 | prd.md + design.md + implement.md | check + spec + code + architecture |
| L5 | 大重构/多 agent | 是 | 全量产物 | 全部门禁 + merge-review |

## 更多模板

详细的分阶段提示词模板见 `prompt.md`（标准任务、PRD 确认、OMC 并行、收尾、小修逃逸等）。

## 维护者参考

| 修改目标 | 改什么 |
|---------|--------|
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
| 文档 | `docs/` |
