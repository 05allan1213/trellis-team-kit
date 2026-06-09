# 示例：多 Agent Parent/Child 任务（L5）

## 场景
构建通知系统：邮件通知（child 1）、站内通知（child 2）、通知偏好 UI（child 3）、统一通知 API（parent 集成）。

## 预期流程

1. AI 判断为 L5（多交付物、多 agent、跨层）
2. Task creation consent → 创建 parent task：`task.py create "Notification system" --slug notifications`
3. AI 创建 child tasks：
   - `task.py create "Email notification service" --slug email-notify --parent notifications`
   - `task.py create "In-app notification UI" --slug inapp-notify --parent notifications`
   - `task.py create "Notification preferences" --slug notify-prefs --parent notifications`
4. 每个 child：brainstorm → grill-me → design（各为 L4）→ implement plan
5. Parent task `prd.md` 记录：child 映射、跨 child AC、集成 checklist
6. 用户批准所有 child 实现
7. `trellis-dev-strategy` for parent：Trellis-native parallel + worktree + merge-review；如需 OMC，先获得显式批准
8. 用户确认并行拆分；如选择 OMC，则必须显式确认 OMC `ulw/ultrawork`
9. Main agent 通过 Trellis-native parallel 并行派发 3 个 `trellis-implementer` agent（每个 child 一个，各自独立 worktree）
10. 每个 child：implement → check → code-review
11. 每个 child check/code-review PASS 后，AI 停下来等待用户明确说"进入 Finish 阶段"
12. 用户确认 Finish → 每个 child 和 parent 按当前模板完成完整 `finish.md`；Parent 运行共享 `trellis-update-spec` → 将通知模式加入 backend + frontend specs，child 记录是否无需单独更新 spec
13. 每个 task 运行 `prepare_finish_workspace.py` 后完成 Commit → Main agent 集成所有 worktree 分支并解决冲突
14. 派发 `trellis-merge-reviewer` → 检查集成
15. merge-review PASS → validate（集成测试）→ `/trellis:finish-work` 依次完成所有 children，最后 parent

## 预期产物

**Parent task：**
- prd.md（child 映射 + 跨 child AC + 集成 checklist）
- design.md（总体架构）
- implement.md（Trellis-native parallel 编排计划；如使用 OMC，记录显式批准）
- before-dev.md、scope-manifest.json
- validation/check-results.md、validation/test-results.md
- review/merge-review.md

**每个 child task：**
- prd.md、design.md、implement.md
- research/：evidence、brainstorm、grill-me
- before-dev.md、scope-manifest.json、validation/check-results.md、validation/test-results.md
- review/：code-review.md（email-notify child 还需要 architecture-review.md）
- finish.md（当前模板章节：Finish Approval、Task Summary、Observable Outcomes、Changed Files、Acceptance Criteria Coverage、Delivery Sync Check、Guardrail Overrides、Spec Update Decision、Follow-ups、Risks）

## 关键行为
- 任务级别：L5
- Parent 负责集成，不负责实现
- Children 可独立验证
- Trellis-native parallel 是默认路径；OMC 并行执行需用户明确确认
- Merge-review 强制
- 每个 child 独立归档，parent 最后归档
