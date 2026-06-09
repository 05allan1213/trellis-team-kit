# Trellis Team Kit 工作流验证任务

> 从零开始，分阶段验证完整的 17 runtime 状态工作流。分类和 task 创建是前置概念步骤，不是 runtime state 常量。

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
# 可选：本地个性化
bash ~/trellis-team-kit/bootstrap/personalize-local.sh 你的名字

# 3. 验证安装
python3 .trellis/scripts/trellis_doctor.py setup
python3 .trellis/scripts/validate_runtime_hardening.py
# 预期：setup doctor PASS，runtime hardening OVERALL: PASS
# 注意：validate_scope_manifest / validate_guardrail_overrides / validate_agent_results
# 在无 task 参数时只显示 INFO availability check；task-runtime validation 必须传入 task-dir。

# 4. 真实安装 smoke test（验证本地 + 模拟远程路径）
bash ~/trellis-team-kit/bootstrap/smoke-test-install.sh

# 5. 发布分支远程安装对比（push 后验证本地安装与 GitHub main raw 远程安装目录一致）
bash ~/trellis-team-kit/bootstrap/smoke-test-install.sh --mode true-remote --developer-name test
# 如需验证其它已发布分支/URL，可设置 TTK_TRUE_REMOTE_INIT_URL。
# 如果 init URL 不是以 /bootstrap/init.sh 结尾，同时设置 TTK_TRUE_REMOTE_RAW_BASE。
# true-remote 会比较安装后的目录清单和稳定文件内容。
# 刚 push 后 GitHub raw 可能短暂返回旧缓存；若第一次失败且 raw 内容已刷新，重跑同一命令。
```

**Claude Code 真实测试前置**：
- [ ] 安装后从测试项目根目录启动或重启 Claude Code，让 `.claude/settings.json` hooks 生效
- [ ] Claude plugins 是可选 WARN；只有测试 Superpowers / OMC 路径时才需要先 `claude plugin list` 并 install/enable
- [ ] 真实需求测试时记录是否启用了 Superpowers、OMC，以及是否选择了 Trellis-native fallback

---

## 前置阶段 0：NO_TASK + 概念 triage

**操作**：在 Claude Code 中说 "添加用户头像上传功能，包含前端上传 UI、后端 API、对象存储和数据库头像 URL 持久化"

**检查点**：
- [ ] Claude 不直接写代码
- [ ] Claude 分类为 L4（跨层 API / 存储 / 数据持久化变更）
- [ ] Claude 给出标准 Trellis task 建议，并询问是否创建 Trellis task

**补充检查（L1 分流）**：
- [ ] 如果输入 "把按钮文案从提交改成保存"，Claude 建议 L1 inline，不强求 task

**补充检查（L2 分流）**：
- [ ] 如果输入 "修复一个原因明确的登录表单校验 bug"，Claude 分类为 L2，minimal `implement.md` 必需，`grill-me` / JSONL 可选

**补充检查（L3/L4/L5 分流）**：
- [ ] 普通 feature / bugfix → L3，默认 subagent，必须 code-review
- [ ] API / schema / auth / infra 跨层变更 → L4，默认 subagent + worktree，OMC 仅在 explicit OMC approval 后可用
- [ ] 多 agent / parent-child / 大重构 → L5，默认 Trellis-native parallel + worktree，OMC 仅在 explicit OMC approval 后可用，必须 merge-review
- [ ] 旧称 `L3+` 不作为可执行路径；必须落到明确的 L3、L4 或 L5

---

## 前置阶段 1：task.py create（进入 PLANNING_PRD）

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
- [ ] task.json 添加 `level: "L4"`

---

## 阶段 3：PLANNING_GRILL

**操作**：Claude 运行 trellis-grill-me

**检查点**：
- [ ] 生成 `research/grill-me.md`
- [ ] 对 PRD 挑刺、找漏洞

---

## 阶段 4：PLANNING_DESIGN

**操作**：Claude 按任务等级编写 design.md（L4/L5 必需，L3 可选）

**检查点**：
- [ ] L4/L5 生成 `design.md`
- [ ] `design.md` 记录架构、接口、数据或跨层影响
- [ ] L3 若跳过 design，跳过原因已记录在 plan / implement 产物中

---

## 阶段 5：PLANNING_IMPLEMENT

**操作**：Claude 编写 implement plan

**检查点**：
- [ ] 生成 `implement.md`，含 Scope、Files to change
- [ ] Review Gate Contract 选中 `trellis-check`、`trellis-spec-review`、`trellis-code-review`、`trellis-code-architecture-review`

---

## 阶段 6：WAITING_IMPLEMENTATION_APPROVAL

**操作**：Claude 询问 "批准实现吗？"

**护栏测试**：
- [ ] 此时如果尝试编辑源码 → PreToolUse deny（规划期阻断）
- [ ] 此时如果运行 `task.py start` → PreToolUse deny

---

## 阶段 7：IN_PROGRESS

**操作**：回复 "批准实现"

**检查点**：
- [ ] `task.py start` 执行成功
- [ ] task.json status → in_progress
- [ ] `.trellis/active-task` 指向当前 task

---

## 阶段 8：BEFORE_DEV

**操作**：Claude 运行 trellis-before-dev

**检查点**：
- [ ] 生成 `before-dev.md`，含 Scope 和 Files likely touched
- [ ] 同目录生成 `scope-manifest.json`
- [ ] `scope-manifest.json` 含 `declared_paths` / `declared_globs`，且至少一个非空
- [ ] `scope-manifest.json` 含非空 `out_of_scope`
- [ ] 高风险 declared scope 已被 `high_risk_allowed` path/glob 覆盖
- [ ] 高风险目录精确声明（如 `api`、`src/api`、`auth`、`src/auth`、`migrations`、`contracts`）缺少 `high_risk_allowed` 时 FAIL
- [ ] `python3 .trellis/scripts/validate_scope_manifest.py <task-dir>` PASS

**护栏测试**：
- [ ] 删除 before-dev.md → 编辑源码被 PreToolUse deny
- [ ] 删除 scope-manifest.json → `validate_task.py <task-dir>` FAIL

**L4 全流程测试**：
- [ ] 用一条跨层 API/schema 测试任务完整走完 Plan -> Execute -> Check -> Review -> Finish
- [ ] Plan 阶段产出 `prd.md`、`research/grill-me.md`、`design.md`、`implement.md`
- [ ] Execute 前生成 `before-dev.md` 与 `scope-manifest.json`
- [ ] Check 阶段运行 `trellis-check` 并写入 `validation/check-results.md`
- [ ] Review 阶段运行 spec-review、code-review、architecture-review
- [ ] Finish 前 `validate_task.py`、`validate_review_gates.py`、`validate_scope_manifest.py` 均 PASS

---

## 阶段 9：IMPLEMENTING

**操作**：Claude 编写代码

**检查点**：
- [ ] 代码文件创建在声明范围内
- [ ] `implement.jsonl` / `check.jsonl` 只保留 curated spec/research context
- [ ] `implement.jsonl` / `check.jsonl` 不重复 task artifacts（`prd.md`、`design.md`、`implement.md`、`finish.md`）
- [ ] 若使用 trellis-researcher，则写入 `agent-results/trellis-researcher-<timestamp>.json`
- [ ] trellis-implementer 写入 `agent-results/trellis-implementer-<timestamp>.json`
- [ ] agent result 含 `version`、`agent`、`status`、对象化 `changed_files`、列表 `validation`、`blocking_issues`；若 `scope-manifest.json` 声明了 workstreams，则 implementer/checker result 还必须含匹配的 `workstream`
- [ ] `python3 .trellis/scripts/validate_agent_results.py <task-dir>` PASS

**范围守卫测试**：
- [ ] 编辑 `scope-manifest.json` declared_globs 覆盖的文件 → allow
- [ ] 编辑非高风险但未在 scope-manifest.json 声明的源码路径 → PreToolUse warning
- [ ] 编辑高风险且未在 scope-manifest.json 声明的路径 → PreToolUse warning
- [ ] 使用 `override team-kit guardrail: <reason>` 绕过 soft warning → 写入 `runtime/guardrail-overrides.jsonl`
- [ ] 有 override ledger 但 finish.md 未复核 → `validate_guardrail_overrides.py <task-dir>` FAIL
- [ ] `finish.md` 的 Guardrail Overrides `Decision:` 仍为模板 HTML 占位、空值或 `N/A` 时 → `validate_guardrail_overrides.py <task-dir>` FAIL

---

## 阶段 10：CHECKING

**操作**：Claude 运行 trellis-check

**检查点**：
- [ ] `check.jsonl` 非空，每行为有效 JSON
- [ ] 自检通过（文件存在、功能正确等）
- [ ] trellis-checker 写入 `agent-results/trellis-checker-<timestamp>.json`
- [ ] validation 失败或 blocking issue 未清空时 `validate_agent_results.py <task-dir>` FAIL

---

## 阶段 11：REVIEWING

**操作**：Claude 运行选中的 review gates（如 spec / code / architecture）

**检查点**：
- [ ] `trellis-check` 的结果写入 `validation/check-results.md`
- [ ] review gate 结果写入对应的 `review/*.md`
- [ ] 包含 `- [x] PASS` 格式的 verdict
- [ ] review agents 写入对应 `agent-results/*.json`
- [ ] merge-review 聚合 `agent-results/*.json`、`runtime/guardrail-overrides.jsonl`、`scope-manifest.json`
- [ ] 两个 agent 声明修改同一文件时 merge-review / `validate_agent_results.py` FAIL
- [ ] OMC execution result 缺少 explicit OMC approval 时 FAIL
- [ ] 所有 selected review gates PASS 后，Claude 先停下来等待明确 Finish 确认
- [ ] 未收到 Finish 确认前，不写 `finish.md`、不运行 spec update、不 commit、不 archive

**L5 / parallel / OMC 显式批准测试**：
- [ ] L5 parallel 默认选择 Trellis-native parallel + worktree，不启动 OMC
- [ ] L5/orchestrated 选择 `main session` → `validate_task.py` FAIL
- [ ] 使用 OMC `ulw/ultrawork` 前必须记录 explicit OMC approval、user message、timestamp
- [ ] 未批准时启动 `ulw/ultrawork` → PreToolUse deny
- [ ] OMC execution result（含 canonical `OMC ulw/ultrawork + worktree + parent/child`）缺少 explicit OMC approval → `validate_agent_results.py` 或 merge-review FAIL
- [ ] L5、Trellis-native parallel + worktree、OMC、worktree、parent/child、PR merge 或 conflict resolution 等触发条件缺少 merge-review → validator / doctor workflow FAIL
- [ ] merge-review 聚合 `agent-results/*.json`、scope、override ledger、OMC approval 记录后 PASS

**Review FAIL 回流测试**：
- [ ] 将某个已选中的 `review/*.md` verdict 改为 `FAIL` → `validate_review_gates.py` 报 FAIL
- [ ] 删除或改坏 `validation/check-results.md` 的 PASS 证据 → `validate_task.py` 报 FAIL
- [ ] `stop-guard` block，要求回到 IMPLEMENTING
- [ ] 恢复为 PASS → 全部 validator PASS

---

## 阶段 12：UPDATING_SPEC

**操作**：回复 "进入 Finish 阶段"。

**检查点**：
- [ ] `finish.md` 的 `Finish Approval` 已记录用户原话、timestamp、summary，并勾选 `Allowed to proceed with finish? -> yes`
- [ ] 在 finish.md 中记录 Spec Update Decision
- [ ] 在 finish.md 中记录 Observable Outcomes 和 Delivery Sync Check
- [ ] `python3 .trellis/scripts/validate_delivery_sync.py <task-dir>` PASS
- [ ] 若使用 trellis-spec-updater，则写入 `agent-results/trellis-spec-updater-<timestamp>.json`
- [ ] spec-updater 的 `changed_files` 只包含 `.trellis/spec/...` 或为空（no update needed）

---

## 阶段 13：COMMITTING

**操作**：清理本地状态、确认提交计划，然后 `git add` + `git commit`

**检查点**：
- [ ] `python3 ./.trellis/scripts/prepare_finish_workspace.py` 已运行
- [ ] `git status --short` 已检查
- [ ] Claude 先给出提交计划，明确哪些文件会提交、哪些未知/无关 dirty 文件不会提交
- [ ] 未经用户确认，不把未知 dirty 文件或无关文件加入 commit
- [ ] 代码已提交
- [ ] task.json 中 branch 字段已设置

---

## 阶段 14：MERGE_REVIEWING

**操作**：条件触发时运行 trellis-merge-review

**触发条件**：L5；`Execution Mode Decision` 选中 `Trellis-native parallel + worktree`；`Execution Mode Decision` 选中 `OMC ulw/ultrawork + worktree + parent/child`；`Branch strategy` 含 `worktree`；`Parent/child: yes`；`Merge review needed: yes`；PR merge；conflict resolution。

**检查点**：
- [ ] 不触发条件时，记录跳过原因并进入 VALIDATING
- [ ] 触发条件时生成 `review/merge-review.md`
- [ ] merge-review 聚合 `agent-results/*.json`、scope、override ledger、OMC approval、冲突/重复实现风险
- [ ] `review/merge-review.md` 含 `- [x] PASS` 后才能进入 VALIDATING

---

## 阶段 15：VALIDATING

**操作**：运行 build 和 test

**检查点**：
- [ ] `validation/test-results.md` 存在
- [ ] Build、Test 和 Smoke 均为 PASS，或记录 skipped with valid reason
- [ ] `Ready for finish-work?` 勾选 yes
- [ ] Overall verdict 为 PASS，或有明确 skipped-with-reason 证据

---

## 阶段 16：FINISHING → DONE

**操作**：Claude 运行 trellis-finish-work

**检查点**：
- [ ] `finish.md` 存在
- [ ] `finish.md` 含 `Observable Outcomes`，且至少一条为具体可观察结果 + 验证证据
- [ ] `validate_task.py` PASS
- [ ] `validate_review_gates.py` PASS
- [ ] Task 已归档
- [ ] Workspace journal 已更新

---

## 最终验证

```bash
# 安装后项目内验证
python3 .trellis/scripts/trellis_doctor.py setup
python3 .trellis/scripts/validate_runtime_hardening.py
# 预期：setup doctor PASS，runtime hardening OVERALL: PASS
# task-specific validators 无 task-dir 时显示 INFO availability check，不代表具体 task 已通过。

# Task 验证
python3 .trellis/scripts/validate_task.py .trellis/tasks/<task-dir>
# 预期：PASS

# Review gate 验证
python3 .trellis/scripts/validate_review_gates.py .trellis/tasks/<task-dir>
# 预期：PASS

# Scope / guardrail / delivery / workflow 验证
python3 .trellis/scripts/validate_scope_manifest.py .trellis/tasks/<task-dir>
python3 .trellis/scripts/validate_guardrail_overrides.py .trellis/tasks/<task-dir>
python3 .trellis/scripts/validate_delivery_sync.py .trellis/tasks/<task-dir>
python3 .trellis/scripts/validate_workflow_state.py .trellis/tasks/<task-dir>
# 预期：PASS

# Agent result 验证
python3 .trellis/scripts/validate_agent_results.py .trellis/tasks/<task-dir>
# 预期：PASS

# Workflow doctor
python3 .trellis/scripts/trellis_doctor.py workflow .trellis/tasks/<task-dir>
# 预期：PASS，或输出具体 To fix 修复路径

# Replay Lab
python3 .trellis/scripts/replay_workflow_cases.py .trellis/replay
# 预期：22/22 passed

# Spec update candidate detector
python3 .trellis/scripts/detect_spec_update_candidates.py
# 预期：输出 JSON，列出需要同步的 spec/workflow/docs 候选项

# Spec update target validator
python3 .trellis/scripts/validate_spec_update_targets.py
# 预期：PASS
```

维护者在 team-kit 仓库根目录还要跑：

```bash
shellcheck bootstrap/*.sh claude/hooks/trellis-notify.sh
python3 trellis/scripts/replay_workflow_cases.py tests/fixtures/replay
# 预期：22/22 passed
```

**Replay Lab 场景覆盖**：
- [ ] routing fixture 覆盖 L1/L2/L3/L4/L5 分流
- [ ] guardrail fixture 覆盖规划期阻断、scope-manifest.json 缺失、override ledger 复核缺失
- [ ] finish fixture 覆盖 finish-without-approval 必须 FAIL
- [ ] orchestration fixture 覆盖 OMC prompt routes L5 but does not start OMC without explicit OMC approval

**doctor workflow 场景覆盖**：
- [ ] phase mismatch 输出 FAIL 和 To fix
- [ ] missing scope-manifest.json 输出 FAIL 和 To fix
- [ ] missing explicit OMC approval 输出 FAIL 和 To fix
- [ ] missing merge-review 输出 FAIL 和 To fix

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
| 编辑高风险未声明路径 | PreToolUse warning |
| high-risk declared scope 未写 high_risk_allowed | validate_scope_manifest.py FAIL |
| soft warning override | allow + 写 runtime/guardrail-overrides.jsonl |
| override ledger 未复核或 Decision 仍是模板占位 | validate_guardrail_overrides.py FAIL |
| agent result 缺失或结构错误 | validate_agent_results.py FAIL |
| workflow 状态不一致 | trellis_doctor.py workflow FAIL + To fix |
| TRELLIS_DISABLE_HOOKS=1 | 所有 hooks 静默 skip |
