# Claude Code 运行时 Smoke Test

验证 trellis-team-kit 的 hooks、agents、skills 和护栏在 Claude Code 中正常工作。

## 前提条件

- Trellis 已安装：`npm install -g @mindfoldhq/trellis`
- trellis-team-kit 已通过 `bootstrap/init.sh` 安装
- Claude Code 在项目目录中运行

## 如何运行

在 Claude Code 中手动运行每个场景。每项通过后打勾。
将结果记录到 `docs/smoke-test-results.md`。

---

## 场景 1：安装

**步骤：**
1. 创建一个空仓库
2. 运行 `bootstrap/init.sh <你的名字>`
3. 运行 `bootstrap/init-local.sh`
4. 检查文件结构

**验收标准：**
- [ ] `.trellis/.team-kit-version` 存在
- [ ] `AGENTS.md` 存在
- [ ] `CLAUDE.md` 存在
- [ ] `.claude/settings.json` 存在
- [ ] `.claude/skills/` 有 14 个 skills
- [ ] `.claude/agents/` 有 9 个 agents
- [ ] `.claude/hooks/` 有 9 个 hooks
- [ ] `.trellis/workflow.md` 存在
- [ ] `.trellis/spec/` 存在

---

## 场景 2：SessionStart 注入

**步骤：**
1. 在项目中打开 Claude Code
2. 观察启动上下文

**验收标准：**
- [ ] 注入了仓库/分支/dirty state
- [ ] 注入了活跃 task（如有）
- [ ] 注入了工作流阶段
- [ ] 注入了 spec 索引
- [ ] 上下文不过长

---

## 场景 3：UserPromptSubmit 工作流状态

**步骤：**
1. 用户输入："我需要加一个登录页"
2. Claude 分类并回复

**验收标准：**
- [ ] 注入了工作流状态面包屑
- [ ] Claude 请求 task 创建同意
- [ ] Claude 不直接编辑源码

---

## 场景 4：Task 创建 ≠ 实现

**步骤：**
1. 用户同意创建 task
2. 用户不同意开始实现

**验收标准：**
- [ ] Claude 通过 `task.py create` 创建 task
- [ ] Claude 进入规划阶段
- [ ] Claude 不运行 `task.py start`
- [ ] Claude 不修改源码

---

## 场景 5：规划阶段源码编辑被阻断

**步骤：**
1. Task 处于 WAITING_IMPLEMENTATION_APPROVAL 状态
2. 尝试诱导 Claude 编辑源码文件

**验收标准：**
- [ ] protect-dangerous-actions hook 阻断或强警告
- [ ] Claude 回到规划行为

---

## 场景 6：Subagent 上下文注入

**步骤：**
1. 批准后运行 `task.py start`
2. 派发 implementer subagent

**验收标准：**
- [ ] Subagent 收到 prd.md 上下文
- [ ] L3+ subagent 收到 design.md / implement.md
- [ ] Subagent 收到 implement.jsonl 的 spec 引用
- [ ] Subagent 不需要主会话重复粘贴上下文

---

## 场景 7：SubagentStop 守卫

**步骤：**
1. 派发一个 reviewer subagent
2. Reviewer 输出不含 PASS/FAIL

**验收标准：**
- [ ] subagent-stop-guard 阻止结束或要求补充
- [ ] Review 输出最终包含 PASS/FAIL

---

## 场景 8：Review Gate FAIL → 回流

**步骤：**
1. Reviewer 返回 FAIL
2. 检查工作流行为

**验收标准：**
- [ ] 工作流回到 IMPLEMENTING
- [ ] Finish 被阻止
- [ ] 修复后重新跑 check，再重新 review

---

## 场景 9：Stop 守卫

**步骤：**
1. Check 尚未通过
2. 尝试让 Claude 声称"完成"

**验收标准：**
- [ ] stop-guard 阻止该声明
- [ ] Claude 说明哪些未完成

---

## 场景 10：PreCompact 保存状态

**步骤：**
1. 触发上下文压缩（长对话）

**验收标准：**
- [ ] 生成或更新了 `research/session-state.md`
- [ ] 记录了当前阶段
- [ ] 记录了关键决策
- [ ] 记录了下一步操作

---

## 完整端到端 Smoke Test

跑通一个完整的 L2 任务，经过所有状态：

```
NO_TASK → TRIAGE → TASK_CREATED → PLANNING_PRD → PLANNING_GRILL
→ PLANNING_IMPLEMENT → WAITING_IMPLEMENTATION_APPROVAL
→ IN_PROGRESS → BEFORE_DEV → IMPLEMENTING → CHECKING
→ REVIEWING → UPDATING_SPEC → COMMITTING → VALIDATING
→ FINISHING → DONE
```

**验收标准：**
- [ ] 每个状态转换干净利落
- [ ] 任何状态都没有发生禁止操作
- [ ] 所有 hooks 在适当时机触发
- [ ] 所有 artifacts 已创建
- [ ] Task 已正确归档
