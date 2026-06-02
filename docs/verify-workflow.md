# Trellis Team Kit 工作流验证任务

> 从零开始，逐步验证完整的 21 步工作流。每一步可独立检查。

---

## 前置：安装

```bash
# 1. 创建测试项目
mkdir /tmp/ttk-verify && cd /tmp/ttk-verify && git init

# 2. 安装 team-kit（二选一）
# 方式 A — 本地克隆版：
bash ~/trellis-team-kit/bootstrap/init.sh 你的名字
# 方式 B — 远程版：
bash <(curl -fsSL https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh) 你的名字

# 3. 验证安装
python3 .trellis/scripts/validate_runtime_hardening.py
# 预期：OVERALL: PASS
```

---

## 阶段 0：NO_TASK → TRIAGE

**操作**：在 Claude Code 中说 "我需要加一个 hello world 工具函数"

**检查点**：
- [ ] Claude 不直接写代码
- [ ] Claude 分类为 L2（轻量实现）
- [ ] Claude 询问 "要为这个创建 Trellis task 吗？"

---

## 阶段 1：TASK_CREATED

**操作**：回复 "是的，创建 task"

**检查点**：
- [ ] `task.py create` 执行成功
- [ ] `.trellis/tasks/` 下生成 task 目录
- [ ] task.json 存在，status=planning
- [ ] Claude 进入规划阶段，不编辑源码

---

## 阶段 2：PLANNING_PRD

**操作**：Claude 运行 trellis-brainstorm

**检查点**：
- [ ] 生成 `prd.md`，含需求描述和验收标准
- [ ] task.json 添加 `level: "L2"`

---

## 阶段 3：PLANNING_GRILL

**操作**：Claude 运行 trellis-grill-me

**检查点**：
- [ ] 生成 `research/grill-me.md`
- [ ] 对 PRD 挑刺、找漏洞

---

## 阶段 4：PLANNING_IMPLEMENT

**操作**：Claude 编写 implement plan

**检查点**：
- [ ] 生成 `implement.md`，含 Scope、Files to change
- [ ] Review Gate Contract 选中 `trellis-check`

---

## 阶段 5：WAITING_IMPLEMENTATION_APPROVAL

**操作**：Claude 询问 "批准实现吗？"

**护栏测试**：
- [ ] 此时如果尝试编辑源码 → PreToolUse deny（规划期阻断）
- [ ] 此时如果运行 `task.py start` → PreToolUse deny

---

## 阶段 6：IN_PROGRESS

**操作**：回复 "批准实现"

**检查点**：
- [ ] `task.py start` 执行成功
- [ ] task.json status → in_progress
- [ ] `.trellis/active-task` 指向当前 task

---

## 阶段 7：BEFORE_DEV

**操作**：Claude 运行 trellis-before-dev

**检查点**：
- [ ] 生成 `before-dev.md`，含 Scope 和 Files likely touched

**护栏测试**：
- [ ] 删除 before-dev.md → 编辑源码被 PreToolUse deny

---

## 阶段 8：IMPLEMENTING

**操作**：Claude 编写代码

**检查点**：
- [ ] 代码文件创建在声明范围内
- [ ] `implement.jsonl` 记录每个文件操作

**范围守卫测试**：
- [ ] 编辑 implement.md 未声明的文件 → PostToolUse warning

---

## 阶段 9：CHECKING

**操作**：Claude 运行 trellis-check

**检查点**：
- [ ] `check.jsonl` 非空，每行为有效 JSON
- [ ] 自检通过（文件存在、功能正确等）

---

## 阶段 10：REVIEWING

**操作**：Claude 运行 trellis-check review

**检查点**：
- [ ] 生成 `review/check-review.md`
- [ ] 包含 `- [x] PASS` 格式的 verdict

**Review FAIL 回流测试**：
- [ ] 将 verdict 改为 `- [x] FAIL` → `validate_review_gates.py` 报 FAIL
- [ ] `stop-guard` block，要求回到 IMPLEMENTING
- [ ] 恢复为 PASS → 全部 validator PASS

---

## 阶段 11：UPDATING_SPEC

**检查点**：
- [ ] 在 finish.md 中记录 Spec Update Decision

---

## 阶段 12：COMMITTING

**操作**：`git add` + `git commit`

**检查点**：
- [ ] 代码已提交
- [ ] task.json 中 branch 字段已设置

---

## 阶段 13：VALIDATING

**操作**：运行 build 和 test

**检查点**：
- [ ] `validation/test-results.md` 存在
- [ ] Build 和 Test 均为 PASS 或 SKIPPED WITH REASON

---

## 阶段 14：FINISHING → DONE

**操作**：Claude 运行 trellis-finish-work

**检查点**：
- [ ] `finish.md` 存在
- [ ] `validate_task.py` PASS
- [ ] `validate_review_gates.py` PASS
- [ ] Task 已归档
- [ ] Workspace journal 已更新

---

## 最终验证

```bash
# 全部静态验证
python3 .trellis/scripts/validate_runtime_hardening.py
# 预期：OVERALL: PASS

# Task 验证
python3 .trellis/scripts/validate_task.py .trellis/tasks/<task-dir>
# 预期：PASS

# Review gate 验证
python3 .trellis/scripts/validate_review_gates.py .trellis/tasks/<task-dir>
# 预期：PASS
```

---

## 关键护栏速查

| 场景 | 预期行为 |
|------|---------|
| 规划期编辑源码 | PreToolUse deny |
| 无 before-dev.md 编辑源码 | PreToolUse deny |
| rm -rf | PreToolUse deny |
| git push --force | PreToolUse deny |
| 编辑 .env | PreToolUse deny |
| Review FAIL 时 finish | stop-guard block |
| Check 未通过时 finish | stop-guard block |
| 编辑未声明路径 | PostToolUse warning |
| TRELLIS_DISABLE_HOOKS=1 | 所有 hooks 静默 skip |
