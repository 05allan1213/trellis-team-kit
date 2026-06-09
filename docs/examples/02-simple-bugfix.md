# 示例：简单 Bug 修复（L2）

## 场景
修复登录表单在邮箱为空时不显示验证错误的 bug。

## 预期流程

1. 用户："我们开始一个 Trellis 任务，走 B Create a task，不要 inline"
2. AI 请求 task creation consent → 用户批准
3. AI 运行 `task.py create "Fix login form empty email validation" --slug fix-login-validation`
4. AI 加载 `trellis-brainstorm` → 探索代码库 → 问 1-2 个澄清问题
5. AI 写 `prd.md`，AC："空邮箱显示 'Email is required' 错误"
6. AI 写 minimal `implement.md`；若需求不清或风险升高，再运行 `trellis-grill-me`
7. AI 仅在额外 spec/research context 明显有价值时配置 `implement.jsonl` / `check.jsonl`
8. AI 请求 implementation approval → 用户批准
9. AI 运行 `task.py start`
10. AI 运行 `trellis-before-dev` → 写 `before-dev.md` 和 `scope-manifest.json`
11. AI 派发 `trellis-implementer` subagent → 修复 bug
12. AI 派发 `trellis-checker` subagent → 验证修复并写 `validation/check-results.md`
13. Check PASS 后，AI 停下来等待用户明确说"进入 Finish 阶段"
14. 用户确认 Finish → AI 按当前模板写完整 `finish.md`（Finish Approval、Task Summary、Observable Outcomes、Changed Files、Acceptance Criteria Coverage、Delivery Sync Check、Guardrail Overrides、Spec Update Decision、Follow-ups、Risks），并运行 `trellis-update-spec`
15. AI 运行 `prepare_finish_workspace.py` → 草拟 commit plan → 用户确认 → commit → final validation 写 `validation/test-results.md`
16. AI 运行 `/trellis:finish-work`

## 预期产物
- `.trellis/tasks/MM-DD-fix-login-validation/task.json`
- `.trellis/tasks/MM-DD-fix-login-validation/prd.md`
- `.trellis/tasks/MM-DD-fix-login-validation/implement.md`（minimal plan + Implementation Approval）
- `.trellis/tasks/MM-DD-fix-login-validation/before-dev.md`
- `.trellis/tasks/MM-DD-fix-login-validation/scope-manifest.json`
- `.trellis/tasks/MM-DD-fix-login-validation/validation/check-results.md`
- `.trellis/tasks/MM-DD-fix-login-validation/validation/test-results.md`
- `.trellis/tasks/MM-DD-fix-login-validation/finish.md`

## 关键行为
- 任务级别：L2（仅 check 门禁，无 code-review）
- `research/grill-me.md`、`implement.jsonl`、`check.jsonl` 对 L2 是可选项，不是必需产物
- AI 不会生成 design.md
- AI 不会派发 architecture reviewer
