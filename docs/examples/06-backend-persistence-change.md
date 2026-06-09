# 示例：后端持久化变更（L4）

## 场景
为审计日志新增数据库表，提供查询 API，以及日志轮转的后台任务。

## 预期流程

1. AI 判断为 L4（schema + API + 后台任务）
2. Task creation consent → `task.py create`
3. `trellis-brainstorm` → 探索现有数据库模式、API 约定、后台任务模式
4. `trellis-grill-me` → 识别数据保留、查询性能、迁移安全
5. `trellis-improve-codebase-architecture guidance` → Architecture Guidance
6. AI 写 `design.md`：schema 设计、API contract、后台任务设计
7. `trellis-dev-strategy` → 决定：subagent + worktree、spec + code + architecture review
8. AI 写 `implement.md`
9. Implementation approval → `task.py start`
10. `trellis-before-dev` → 读取 .trellis/spec/backend/ 相关规范
11. 派发 `trellis-implementer` → migration + API + 任务
12. 派发 `trellis-checker` → 深度检查（schema 一致性、API contract）
13. 派发 `trellis-spec-reviewer`
14. 派发 `trellis-code-reviewer`
15. 派发 `trellis-architecture-reviewer`
16. 全部 PASS → AI 停下来等待用户明确说"进入 Finish 阶段"
17. 用户确认 Finish → AI 按当前模板写完整 `finish.md`，并运行 `trellis-update-spec` → 添加审计日志模式
18. `prepare_finish_workspace.py` → Commit → merge-review → final validation 写 `validation/test-results.md`（运行 migration 测试）→ `/trellis:finish-work`

## 预期产物
- 完整产物：prd.md、design.md、implement.md
- research/：evidence.md、brainstorm.md、grill-me.md
- review/：spec-review.md、code-review.md、architecture-review.md、merge-review.md
- validation/：check-results.md、test-results.md（migration 测试）；可选辅助证据 commands.md、build-results.md
- finish.md（当前模板章节：Finish Approval、Task Summary、Observable Outcomes、Changed Files、Acceptance Criteria Coverage、Delivery Sync Check、Guardrail Overrides、Spec Update Decision、Follow-ups、Risks）

## 关键行为
- 任务级别：L4
- design.md 中检查迁移安全性
- 深度检查包含 schema/API 一致性
- Build/Test/Smoke 包含 migration 测试
