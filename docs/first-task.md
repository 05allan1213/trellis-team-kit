# 第一个任务演示

跟着这个指南一步步跑通你的第一个端到端 Trellis 任务。

## 前提条件

- trellis-team-kit 已安装（见 README）
- Claude Code 在项目目录中运行
- 有一个真实的功能或 bugfix 要做

## 演示：给登录页加"记住我"复选框

### 第 1 步：说出你的需求

在 Claude Code 中输入：

> 我需要给登录页加一个"记住我"复选框。勾选后 session 保持 30 天，而不是默认的会话时长。

### 第 2 步：分类（Triage）

Claude 将其分类为 L3（普通功能）并询问：

> 这看起来是一个 L3 功能任务。要为此创建 Trellis task 吗？

你回复：

> 是的，创建 task。

Claude 运行 `task.py create "给登录页添加记住我复选框" --slug remember-me-login`。

### 第 3 步：规划 — 头脑风暴（Brainstorm）

Claude 加载 `trellis-brainstorm` 并提出澄清问题：

- "记住我是用持久化 cookie 还是延长 session token 的 TTL？"
- "复选框默认勾选吗？"
- "会影响登出行为吗？"

你逐一回答。Claude 每收到一个答案就更新 `prd.md`。

### 第 4 步：规划 — 挑刺（Grill Me）

Claude 加载 `trellis-grill-me` 对 PRD 挑刺：

- "30 天时长是否可配置？"
- "用户清除 cookie 后会发生什么？"
- "是否需要数据库迁移来改 session 表？"
- "长生命周期 session 有没有安全隐患？"

Claude 把发现写入 `research/grill-me.md` 并更新 `prd.md`。

### 第 5 步：规划 — 设计（Design）

这是 L3 任务，`design.md` 可选但推荐。Claude 产出：

- 当前认证流程 vs. 修改后流程
- Cookie/session token 设计方案
- 前端组件契约
- 后端 API 变更

### 第 6 步：规划 — 实现计划（Implement Plan）

Claude 加载 `trellis-dev-strategy` 并写出 `implement.md`：

- 任务级别：L3
- 执行模式：subagent
- 有序步骤：（1）后端 session TTL 逻辑，（2）API 端点，（3）前端复选框组件，（4）集成，（5）测试
- Review gates：check + code-review
- Implementation Approval：已请求

### 第 7 步：实现批准

Claude 展示计划：

> PRD、design、implement plan 已准备好。
> 任务级别：L3。Review gates：check + code-review。
> 批准实现吗？

你回复：

> 批准实现。

### 第 8 步：实现

Claude 运行 `task.py start`，加载 `trellis-before-dev`，然后派发
`trellis-implementer` subagent。

Implementer：
1. 给后端添加 session TTL 逻辑
2. 更新 API 端点
3. 给登录页添加复选框组件
4. 编写测试
5. 运行 lint 和 type-check

### 第 9 步：检查（Check）

Claude 派发 `trellis-checker` subagent。Checker：
1. 运行 lint → PASS
2. 运行 type-check → PASS
3. 运行测试 → PASS
4. 检查 spec 合规 → PASS
5. 输出：PASS

### 第 10 步：审查（Review）

Claude 派发 `trellis-code-reviewer` subagent。Reviewer：
1. 审查 diff 的正确性、安全性、可维护性
2. 发现一个非阻塞的代码风格建议
3. 输出：PASS

### 第 11 步：更新 Spec

Claude 加载 `trellis-update-spec` 并判断：

> 无需更新 spec — 现有认证 spec 已覆盖 session 时长配置。

将决策记录到 `finish.md`。

### 第 12 步：提交（Commit）

Claude 检查 git 状态，起草提交计划：

```
拟提交：
  1. feat: 给登录页添加记住我复选框，30 天 session TTL
     - src/backend/auth/session.py
     - src/backend/api/auth.py
     - src/frontend/components/LoginForm.tsx
     - tests/auth/test_session.py
     - tests/frontend/LoginForm.test.tsx
```

你确认。Claude 提交。

### 第 13 步：验证（Validate）

Claude 运行构建和测试：

```bash
npm run build   # PASS
npm run test    # PASS
```

将结果记录到 `validation/test-results.md`。

### 第 14 步：收尾（Finish）

Claude 加载 `trellis-finish-work`：
1. 验证所有门禁通过
2. 归档 task 到 `.trellis/archive/`
3. 更新工作区日志
4. 标记任务完成

### 最终结果

```text
任务：给登录页添加记住我复选框
状态：DONE
提交：1 个（abc1234）
Review：PASS（code-review）
验证：PASS（build、test）
Spec 更新：无
归档：.trellis/archive/MM-DD-remember-me-login/
```

## 关键要点

1. **规划先行** — 写任何代码之前有 5 个规划步骤
2. **实现批准是硬门禁** — 批准前不得编辑源码
3. **Subagents 干活** — implementer、checker、reviewer 各司其职
4. **每个门禁必须通过** — 不可跳过，不可"差不多就行"
5. **一切有记录** — PRD、design、implement plan、review、validation、finish 全部留存
