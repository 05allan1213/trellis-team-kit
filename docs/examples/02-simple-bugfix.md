# 示例：简单 Bug 修复（L2）

## 场景
修复登录表单在邮箱为空时不显示验证错误的 bug。

## 预期流程

1. 用户："我们开始一个 Trellis 任务，走 B Create a task，不要 inline"
2. AI 请求 task creation consent → 用户批准
3. AI 运行 `task.py create "Fix login form empty email validation" --slug fix-login-validation`
4. AI 加载 `trellis-brainstorm` → 探索代码库 → 问 1-2 个澄清问题
5. AI 写 `prd.md`，AC："空邮箱显示 'Email is required' 错误"
6. AI 运行 `trellis-grill-me` → 写 `research/grill-me.md`
7. AI 配置 `implement.jsonl` / `check.jsonl`
8. AI 请求 implementation approval → 用户批准
9. AI 运行 `task.py start`
10. AI 派发 `trellis-implementer` subagent → 修复 bug
11. AI 派发 `trellis-checker` subagent → 验证修复
12. AI 运行 `trellis-update-spec` → 无需更新（简单 bug）
13. AI 草拟 commit plan → 用户确认 → commit
14. AI 运行 `/trellis:finish-work`

## 预期产物
- `.trellis/tasks/MM-DD-fix-login-validation/task.json`
- `.trellis/tasks/MM-DD-fix-login-validation/prd.md`
- `.trellis/tasks/MM-DD-fix-login-validation/implement.md`
- `.trellis/tasks/MM-DD-fix-login-validation/research/grill-me.md`
- `.trellis/tasks/MM-DD-fix-login-validation/implement.jsonl`
- `.trellis/tasks/MM-DD-fix-login-validation/check.jsonl`
- `.trellis/tasks/MM-DD-fix-login-validation/finish.md`

## 关键行为
- 任务级别：L2（仅 check 门禁，无 code-review）
- AI 不会生成 design.md
- AI 不会派发 architecture reviewer
