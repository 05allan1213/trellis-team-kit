# 运行时硬化

trellis-team-kit 运行时硬化说明。

## 硬化内容

- **Hook schema** — 所有 hooks 使用统一 `{matcher, hooks: [{type, command}]}` 结构
- **命名一致性** — 所有 agent/skill/hook/workflow 名称一致
- **硬阻断** — stop-guard、subagent-stop-guard、protect-dangerous-actions 返回 block/deny（不只是 additionalContext）
- **Subagent 输出契约** — 每个 agent 类型有明确的输出格式要求
- **Review gate 检测** — runtime 可检测 selected gates 是否完成
- **Validation 检测** — runtime 可检测 build/test 是否完成
- **静态验证器** — 不启动 Claude Code 也能检查配置

## Hook 生命周期

```text
SessionStart → UserPromptSubmit → (PreToolUse → PostToolUse)* → Stop
                                    ↓
                              SubagentStart → SubagentStop
```

每个 hook 事件在特定时机触发，执行对应的 guard/context injection 逻辑。

## 硬阻断 vs 软警告

| 类型 | 机制 | 可绕过 | 示例 |
|------|------|--------|------|
| 硬阻断 | `decision: "block"` 或 `permissionDecision: "deny"` | 否 | 规划期编辑源码、review gate 缺失 |
| 软警告 | `permissionDecision: "allow"` + reason | 是 | 编辑 lockfile、编辑 shared types |
| 上下文注入 | `additionalContext` | 不适用 | 工作流状态面包屑、subagent 上下文 |

## 同意门禁

双同意门禁由 hooks 强制执行：

1. **Task 创建同意** — 用户可以同意创建 task → 进入 planning
2. **实现同意** — 用户必须明确说 "start implementation" / "approve implementation" → 进入 in_progress

Planning 阶段编辑源码、运行 `task.py start`、spawn implementer 都会被 PreToolUse hook deny。

## Review Gates

Review gates 在 `implement.md` 的 Review Gate Contract 中配置：

```md
## Review Gate Contract

Selected gates:
- [ ] trellis-code-review
- [ ] trellis-spec-review

Failure rule:
- Failed gate returns to IMPLEMENTING.
- Do not skip a failed gate.
```

每个 selected gate 必须：
- 对应 review 文件存在
- 文件包含 Status 和 PASS/FAIL
- Blocking issues 为空或明确 none

## Validation Gate

finish 前必须：
- Build result: PASS 或 SKIPPED WITH REASON
- Test result: PASS 或 SKIPPED WITH REASON
- Ready for finish-work: yes

FAIL 或 SKIPPED 无 reason 会 block。

## Subagent 输出契约

每个 subagent 有明确的输出格式要求。SubagentStop hook 检查输出并 block 不合格的输出。

详见 `docs/hook-contract.md`。

## 静态验证器

运行静态验证：

```bash
python3 .trellis/scripts/validate_runtime_hardening.py
```

包含：
- `validate_claude_settings.py` — settings.json schema 检查
- `validate_naming_map.py` — 命名一致性检查
- `validate_hooks.py` — hook 脚本存在性和结构检查

另外可单独运行：
- `validate_task.py <task-dir>` — 任务产物检查
- `validate_review_gates.py <task-dir>` — review gate 完成度检查

## 已知限制

- 真实 Claude Code smoke test 尚未执行
- SubagentStop hook 依赖 Claude Code 传递 subagent 输出文本
- Stop hook 的 done intent 检测基于关键词匹配，可能误判
- 跨平台兼容性未完全验证（当前只针对 Claude Code）

## 后续

- 真实 Claude Code `/hooks` 检查
- 真实 SessionStart / UserPromptSubmit 测试
- 真实 SubagentStart / SubagentStop 测试
- 真实 PreToolUse / Stop 阻断测试
- 端到端 bugfix / feature 任务测试
- Review FAIL 回流测试
