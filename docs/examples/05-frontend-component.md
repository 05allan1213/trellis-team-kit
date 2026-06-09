# 示例：前端组件（L3）

## 场景
在共享组件库中添加一个支持分页和搜索的数据表格组件。

## 预期流程

1. AI 判断为 L3（单个 package，中等复杂度）
2. Task creation consent → `task.py create`
3. `trellis-brainstorm` → 探索现有表格/组件模式 → 询问分页样式、搜索行为、列自定义
4. `trellis-grill-me` → 识别空状态、加载状态、响应式设计、无障碍
5. 可选：`design.md` 用于组件 API 设计
6. `trellis-dev-strategy` → 决定：subagent、启用 code-review
7. AI 写 `implement.md`，含 Review Gate Contract
8. Implementation approval → `task.py start`
9. `trellis-before-dev` → 读取 .trellis/spec/frontend/ 相关规范
10. 派发 `trellis-implementer` → 创建组件 + 测试 + stories
11. 派发 `trellis-checker` → 验证
12. 派发 `trellis-code-reviewer` → PASS
13. 所有 review gates PASS 后，AI 停下来等待用户明确说"进入 Finish 阶段"
14. 用户确认 Finish → AI 按当前模板写完整 `finish.md`，并运行 `trellis-update-spec` → 将表格组件模式沉淀到 .trellis/spec/frontend/
15. `prepare_finish_workspace.py` → Commit → final validation 写 `validation/test-results.md` → `/trellis:finish-work`

## 预期产物
- prd.md、implement.md、before-dev.md、scope-manifest.json、可选 design.md
- validation/check-results.md、validation/test-results.md
- review/code-review.md
- finish.md（当前模板章节完整；spec 已更新：是）

## 关键行为
- 任务级别：L3
- design.md 可选（组件 API 设计）
- Spec 更新，沉淀新组件模式
- before-dev 中加载前端专属 specs
