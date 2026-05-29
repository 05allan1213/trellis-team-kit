# 更新日志

## 首次发布 (2026-05-29)

### 重大变更 — 完整吸收 Herbivore 工作流

- **完整状态机**：将 workflow.md 重写为 20 状态显式状态机，每个状态定义进入条件、允许/禁止动作、退出条件、下一状态
- **L0-L5 任务分级**：从纯问答到多 agent 架构，复杂度逐步递增，每级有明确的产物和门禁要求
- **双同意门禁**：创建 task 的批准 ≠ 开始实现的批准，规划阶段禁止编辑源码
- **Review Gate Contract**：可配置的逐任务审查门禁，PASS/FAIL 强制执行，失败必须打回 IMPLEMENTING

### 新增资产

- **14 个阶段 skills**：brainstorm、grill-me、dev-strategy、before-dev、implement、check、spec-review、code-review、code-architecture-review、improve-codebase-architecture、update-spec、break-loop、merge-review、finish-work
- **9 个专用 subagents**：researcher、implementer、checker、spec-reviewer、code-reviewer、architecture-reviewer、architecture-deep-reviewer、merge-reviewer、spec-updater
- **8 个守护 hooks**：session-start、inject-workflow-state、inject-subagent-context、subagent-stop-guard、stop-guard、protect-dangerous-actions、post-edit-reminder、pre-compact-save-state
- **3 个 slash 命令**：finish-work、continue、create-manifest
- **团队 AI 工作流规范**：marketplace 驱动的 spec 系统
- **17 个 task 产物模板**：prd、design、implement、finish、research（6）、review（4）、validation（3）、PR 模板
- **OMC 策略文件**：orchestration.md、worktree-policy.md、3 个角色定义、policies
- **3 个验证器**：validate_task.py、validate_workflow_state.py、validate_spec_index.py
- **8 个示例任务**：覆盖 L1-L5 全级别

### 项目文件

- `workflow/workflow.md`：完整状态机
- `entry/CLAUDE.md`：L0-L5 路由、双同意门禁、主/subagent 分离
- `entry/AGENTS.md`：同上，多平台兼容
- `prompt.md`：各阶段提示词模板
- `README.md`：项目说明和快速开始
- `bootstrap/init.sh`：一键安装脚本
- `bootstrap/init-local.sh`：本地个人配置
- `VERSION`：版本号

### 设计理念
