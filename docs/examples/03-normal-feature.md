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
10. AI 派发 `trellis-implementer` → 实现复选框 + cookie 逻辑
11. AI 派发 `trellis-checker` → 验证
12. AI 派发 `trellis-code-reviewer` → 审查代码质量 → PASS
13. AI 运行 `trellis-update-spec` → 记录决策
14. Commit → `/trellis:finish-work`

## 预期产物
- `.trellis/tasks/MM-DD-remember-me/task.json`
- `.trellis/tasks/MM-DD-remember-me/prd.md`
- `.trellis/tasks/MM-DD-remember-me/implement.md`（含 Review Gate Contract）
- `.trellis/tasks/MM-DD-remember-me/research/evidence.md`
- `.trellis/tasks/MM-DD-remember-me/research/brainstorm.md`
- `.trellis/tasks/MM-DD-remember-me/research/grill-me.md`
- `.trellis/tasks/MM-DD-remember-me/review/code-review.md`
- `.trellis/tasks/MM-DD-remember-me/finish.md`

## 关键行为
- 任务级别：L3（check + code-review 门禁）
- AI 生成 implement.md，含 Review Gate Contract
- AI 在 checker 通过后派发 code-reviewer
- 无 architecture review（不是 L4+）
