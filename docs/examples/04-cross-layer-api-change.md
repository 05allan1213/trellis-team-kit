# 示例：跨层 API 变更（L4）

## 场景
添加用户头像上传功能：前端上传 UI → 后端 API 接口 → S3 存储 → 数据库 URL 持久化。

## 预期流程

1. AI 判断为 L4（跨层：前端 + API + 存储 + 数据库）
2. Task creation consent → `task.py create`
3. `trellis-brainstorm` → 跨所有层广泛收集证据
4. `trellis-grill-me` → 识别文件大小限制、格式校验、认证问题
5. `trellis-improve-codebase-architecture guidance` → 写 Architecture Guidance
6. AI 写 `design.md`：当前架构、提议架构、数据流（上传 → API → S3 → DB）、API Contract、迁移计划、回滚计划
7. `trellis-dev-strategy` → 决定：subagent + worktree、启用全部审查门禁
8. AI 写 `implement.md`，含完整 Review Gate Contract
9. Implementation approval → `task.py start`
10. `trellis-before-dev` → 读取相关 specs：frontend/component-guidelines.md、frontend/type-safety.md、backend/database-guidelines.md、backend/error-handling.md、guides/cross-layer-thinking-guide.md
11. 派发 `trellis-implementer`（在 worktree 中）
12. 派发 `trellis-checker` → 基础 + 深度检查
13. 派发 `trellis-spec-reviewer` → 对照 frontend + backend specs 检查
14. 派发 `trellis-code-reviewer`
15. 派发 `trellis-architecture-reviewer`
16. 全部 PASS → AI 停下来等待用户明确说"进入 Finish 阶段"
17. 用户确认 Finish → AI 按当前模板写完整 `finish.md`，并运行 `trellis-update-spec` → 将上传 API / storage 模式沉淀到现有 backend/frontend specs；如果没有合适文件，则新建更具体 spec 并更新对应 `index.md`
18. `prepare_finish_workspace.py` → Commit → `trellis-merge-review`（worktree 合并）→ final validation 写 `validation/test-results.md` → `/trellis:finish-work`

## 预期产物
- 完整产物树：prd.md、design.md、implement.md
- research/：evidence.md、brainstorm.md、grill-me.md、architecture-options.md、external-docs.md（S3 SDK）
- review/：spec-review.md、code-review.md、architecture-review.md、merge-review.md
- validation/：check-results.md、test-results.md；可选辅助证据 commands.md、build-results.md
- finish.md（当前模板章节：Finish Approval、Task Summary、Observable Outcomes、Changed Files、Acceptance Criteria Coverage、Delivery Sync Check、Guardrail Overrides、Spec Update Decision、Follow-ups、Risks）

## 关键行为
- 任务级别：L4
- design.md 是必需的
- Architecture guidance 在 design 之前运行
- 全部审查门禁：spec + code + architecture
- 使用 worktree 隔离
- Worktree 合并后进行 merge-review
- Spec 更新，沉淀新模式
