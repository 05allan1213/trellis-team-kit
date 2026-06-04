# 变更记录

## 2026-06-04 — Workflow Artifact Hardening

### 工作流边界

- `prompt.md` 与 `workflow/workflow.md` 现在明确要求：实现批准必须先写回 `implement.md`，Execute + Check + Review 全部通过后必须停下，等待用户显式确认进入 Finish
- OMC 失败回退边界补充为显式说明 + 二次确认；Trellis 原生 reviewer background agents 并行与 OMC 明确区分
- 并行语义进一步收口：默认并行优先使用 Trellis 原生能力；OMC 现在明确指向官方 `ulw/ultrawork` 高级编排模式
- Superpowers / OMC / MCP / scenario skills 明确降级为可选扩展：缺失时必须说明限制并回退到 Trellis 原生路径，不能阻塞主流程

### Hook 与验证器

- `claude/settings.json` 的 hook 命令统一切到 `$CLAUDE_PROJECT_DIR` 绝对路径，修复子目录 CWD 下 hook 失效的问题
- `bootstrap/init.sh` 现在会在 `trellis init --template web-app` 之后补齐缺失的 spec overlay，修复某些 Trellis CLI 版本漏装 `.trellis/spec/index.md`、`guides/architecture-thinking.md`、`guides/review-thinking.md` 导致的 spec 入口缺失与读取循环
- `protect-dangerous-actions.py` 现在把 `implement.md` 的 `Implementation Approval` 和 `finish.md` 的 `Finish Approval` 都当作真正门禁：未完整写回批准信息时，禁止 `task.py start`、后续源码编辑、提前写 `finish.md`、以及过早 `git commit` / `task.py archive`
- `validate_task.py` 收紧了 task 契约：`level` 缺失升级为错误、`Observable Outcomes` 接受表格形式、JSONL 必须是可解析的 spec/research context、实现批准字段必须完整，且 `finish.md` 现在必须包含 `Finish Approval` 与 `Delivery Sync Check`
- `validate_runtime_hardening.py` 新增 `validate_spec_index.py`，现在会直接检查 spec 根索引是否存在以及 spec 链接树是否自洽，避免坏安装进入真实使用
- 新增 `validate_delivery_sync.py`，用于捕获“代码里已移除的公开路径仍残留在 README / docs”这类交付不同步问题
- 新增 `validate_workflow_state.py`，用于检查归档后 journal / workspace index 占位文本、缺失 commit 信息，以及 `.omc/state/*` 运行时状态污染

### Skills 与模板

- `trellis-before-dev` 新增批准记录前置检查，并明确 JSONL 不能重复塞 task artifacts
- `trellis-finish-work` 新增 Finish Approval / Delivery Sync Check 前置要求，并在 archive 后再次跑 task/review/workflow-state validators，确保归档产物本身仍然自洽
- `implement.md.tmpl`、`finish.md.tmpl` 补充了批准回写、Observable Outcomes、以及交付同步检查的书写约束

## 2026-06-03 — Prompt Routing 收口

### 路由

- 无 task 请求的分流正式收口到 scorer 模型：规则只识别强确定性信号，不再试图靠不断补关键词去猜自然语言边界句
- 对边界模糊、竞争信号冲突或高风险对象但修改目标不明确的请求，统一返回 `UNCERTAIN`
- `UNCERTAIN` 分支固定为三段式闭环：AI 先给建议等级和一句理由，用户再确认、改级或补充上下文；未确认前不得开始实现
- 高风险直接升级仅保留给结构化组合信号，像 `schema`、`middleware`、`auth` 这类裸高风险名词不再单独触发 L3+
- 新的路由设计基线以 design2 路线和 `workflow/routing.md` 为准；若与旧描述冲突，以 `UNCERTAIN -> AI 建议 -> 用户确认` 机制为准

### 文档与验证

- `prompt.md`、`README.md` 同步补充了模糊请求的建议与确认流程，确保用户入口文案和实际 hook 行为一致
- 路由 fixtures、hook 文案断言、运行时硬化验证已围绕 `UNCERTAIN` 闭环补齐，本轮收口后可直接进入真实场景测试
- 当前实现保持“强信号直路由，弱信号显式承认不确定”的策略，避免继续围绕单个中文边界句做无限制规则修补

## 2026-05-29 — 初版

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

- Task 产物：prd、design、implement、finish、before-dev
- Research：architecture-options、brainstorm、break-loop、decision-log、evidence、external-docs、grill-me、spike-results
- Review：spec-review、code-review、architecture-review、merge-review
- Validation：build-results、commands、test-results
- PR 模板

### 护栏

- 硬阻断：rm -rf、git reset --hard、force push、规划期源码编辑、未完成时结束、无 before-dev.md 时源码编辑
- 软警告：lockfile 编辑、generated files、shared types、CI config、高风险未声明路径
- 绕过：软警告可通过 `override team-kit guardrail: <reason>` 绕过

### 工作流强制执行

- **Review Gate Contract 不可空** — L3 必选 code-review，L4 必选 spec+code+architecture，L5 必选全部 5 个 gate；未选够 = FAIL
- **Task validators 接入关键路径** — stop-guard 在 finish 前自动运行 validate_task.py 和 validate_review_gates.py，失败即 block
- **Mandatory artifacts by level** — L2+ 必须有 prd.md + grill-me.md + implement.jsonl + check.jsonl；L3+ implement.md；L4/L5 design.md；completed 需要 finish.md
- **Before-dev 门控** — in_progress 但无 before-dev.md 时，protect-dangerous-actions 阻断源码编辑
- **before-dev.md 模板** — task-templates/before-dev.md，init.sh 自动安装
- **Before-dev 内容验证** — Scope 和 Files likely touched 字段必须非空（排除 N/A/TBD/TODO）

### 范围守卫

- **高风险路径 scope guard** — 未在 implement.md 声明的高风险路径（auth/migration/schema/API/shared types）→ soft block（可 override）
- **PostToolUse scope warning** — 编辑了未声明路径 → additionalContext warning
- **Scope 声明质量** — `*`、`src/*` 等过宽声明触发 warning

### 面包屑自动推断

- **子阶段推断** — inject-workflow-state 根据 artifact 存在情况推断精确子阶段（PLANNING_PRD/GRILL/DESIGN/IMPLEMENT 等），不依赖 AI 手动维护 workflow.md
- **Skill 调用引导** — 每个子阶段注入推荐 skill（如 BEFORE_DEV → "Next skill: trellis-before-dev"）

### 运行时硬化

- **Hook 输出契约** — 统一 hook 输出语义：block/deny（硬阻断）、allow+warn（软警告）、additionalContext（上下文注入）
- **Hook 辅助库** (`claude/hooks/lib/`) — hook_output、workflow_state、task_artifacts、naming 四个模块
- **硬阻断语义** — stop-guard、subagent-stop-guard、protect-dangerous-actions 全部具备 block/deny 路径
- **Subagent 输出契约** — 9 个 agent 各有明确的输出格式要求，subagent-stop-guard 强制检查
- **Review gate 完成检测** — stop-guard 解析 Review Gate Contract，检查 selected gates 完成度
- **Validation 完成检测** — stop-guard 检查 build/test/smoke 验证状态

### 文档

- README：项目说明和快速开始
- docs/first-task.md：端到端演示
- docs/naming-map.md：Skills/Agents/Hooks 命名映射
- docs/hook-contract.md：Hook 输出约定
- docs/guardrails.md：护栏规则
- docs/runtime-hardening.md：运行时硬化说明
- docs/validators.md：静态验证器说明
- docs/smoke-test.md：10 场景运行时验证
- docs/team-rollout.md：团队推广指南
- docs/examples/：8 个示例任务（L1-L5）
- examples/：3 个完整产物示例（bugfix/feature/refactor）

### 工具

- 6 个验证器：validate_claude_settings、validate_naming_map、validate_hooks、validate_task、validate_review_gates、validate_runtime_hardening
- bootstrap/init.sh：一键安装
- bootstrap/init-local.sh：本地个人配置

### Spec 系统

- Marketplace 驱动的分层团队知识库
- 前端/后端/共享/基础设施/指南分类

### 已知限制

- 真实 Claude Code smoke test 尚未执行
- 跨平台兼容性未完全验证
