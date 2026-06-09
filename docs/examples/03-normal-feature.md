# 示例：普通功能开发（L3）

## 场景
在登录表单中添加"记住我"复选框。

## 预期流程

1. 用户："我们开始一个 Trellis 任务，走 B Create a task，不要 inline"
2. AI 判断为 L3 → 请求 task creation consent → 批准
3. AI 运行 `task.py create`
4. AI 加载 `trellis-brainstorm` → 探索现有登录代码 → 询问 cookie 有效期、安全需求
5. AI 写 `prd.md`，含 AC
6. AI 运行 `trellis-grill-me` → 识别 cookie 安全问题
7. AI 加载 `trellis-dev-strategy` → 决定：subagent、当前分支、不用 TDD、启用 code-review
8. AI 写 `implement.md`，含 Review Gate Contract（check + code-review）
9. AI 请求 implementation approval → 用户批准 → `task.py start`
10. AI 运行 `trellis-before-dev` → 写 `before-dev.md` 和 `scope-manifest.json`
11. AI 派发 `trellis-implementer` → 实现复选框 + cookie 逻辑
12. AI 派发 `trellis-checker` → 验证并写 `validation/check-results.md`
13. AI 派发 `trellis-code-reviewer` → 审查代码质量 → PASS
14. 所有 review gates PASS 后，AI 停下来等待用户明确说"进入 Finish 阶段"
15. 用户确认 Finish → AI 按当前模板写完整 `finish.md`（Finish Approval、Task Summary、Observable Outcomes、Changed Files、Acceptance Criteria Coverage、Delivery Sync Check、Guardrail Overrides、Spec Update Decision、Follow-ups、Risks），并运行 `trellis-update-spec`
16. `prepare_finish_workspace.py` → Commit → final validation 写 `validation/test-results.md` → `/trellis:finish-work`

## 预期产物
- `.trellis/tasks/MM-DD-remember-me/task.json`
- `.trellis/tasks/MM-DD-remember-me/prd.md`
- `.trellis/tasks/MM-DD-remember-me/implement.md`（含 Review Gate Contract）
- `.trellis/tasks/MM-DD-remember-me/research/evidence.md`
- `.trellis/tasks/MM-DD-remember-me/research/brainstorm.md`
- `.trellis/tasks/MM-DD-remember-me/research/grill-me.md`
- `.trellis/tasks/MM-DD-remember-me/before-dev.md`
- `.trellis/tasks/MM-DD-remember-me/scope-manifest.json`
- `.trellis/tasks/MM-DD-remember-me/validation/check-results.md`
- `.trellis/tasks/MM-DD-remember-me/review/code-review.md`
- `.trellis/tasks/MM-DD-remember-me/validation/test-results.md`
- `.trellis/tasks/MM-DD-remember-me/finish.md`

## 关键行为
- 任务级别：L3（check + code-review 门禁）
- AI 生成 implement.md，含 Review Gate Contract
- AI 在 checker 通过后派发 code-reviewer
- 无 architecture review（不是 L4+）
