# 更新日志

## 2026-05-29

### 工作流

- 22 状态显式状态机，每个状态定义进入条件、必需产物、允许/禁止操作、退出条件、下一状态
- L0-L5 任务分级路由，按复杂度匹配流程严格度
- 双同意门禁：创建 task ≠ 开始实现，两阶段独立确认
- Review Gate Contract：串行 PASS/FAIL 强制执行，失败回流到 IMPLEMENTING
- VALIDATING 状态：finish-work 前的硬门禁
- Artifact Matrix：每级任务明确的必需产物和门禁

### Skills（14 个）

brainstorm、grill-me、dev-strategy、before-dev、implement、check、spec-review、code-review、code-architecture-review、improve-codebase-architecture、update-spec、break-loop、merge-review、finish-work

### Subagents（9 个）

researcher、implementer、checker、spec-reviewer、code-reviewer、architecture-reviewer、architecture-deep-reviewer、merge-reviewer、spec-updater

### Hooks（9 个）

session-start、inject-workflow-state、inject-subagent-context、subagent-stop-guard、stop-guard、protect-dangerous-actions、post-edit-reminder、pre-compact-save-state、trellis-notify

### Slash 命令（3 个）

finish-work、continue、create-manifest

### 模板

- Task 产物：prd、design、implement、finish
- Research：architecture-options、brainstorm、break-loop、decision-log、evidence、external-docs、grill-me、spike-results
- Review：spec-review、code-review、architecture-review、merge-review
- Validation：build-results、commands、test-results
- PR 模板

### 文档

- README：项目说明和快速开始
- docs/first-task.md：端到端演示
- docs/naming-map.md：Skills/Agents/Hooks 命名映射
- docs/smoke-test.md：10 场景运行时验证
- docs/team-rollout.md：团队推广指南
- docs/examples/：8 个示例任务（L1-L5）
- examples/：3 个完整产物示例（bugfix/feature/refactor）

### 工具

- 3 个验证器：validate_task.py、validate_workflow_state.py、validate_spec_index.py
- bootstrap/init.sh：一键安装
- bootstrap/init-local.sh：本地个人配置

### Spec 系统

- Marketplace 驱动的分层团队知识库
- 前端/后端/共享/基础设施/指南分类
