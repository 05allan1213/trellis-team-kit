# Hook 契约

Claude Code hook 事件的统一输出约定。

## Settings Schema

所有 hooks 使用统一结构：

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/example.py"
          }
        ]
      }
    ]
  }
}
```

每个 entry 必须包含 `matcher` 和 `hooks` 列表。每个 hook 必须包含 `type: command` 和 `command`。

## 事件输出语义

### PreToolUse

用于工具权限控制：

- `permissionDecision: "deny"` — 阻断工具调用（硬阻断）
- `permissionDecision: "allow"` — 允许调用，可选 `permissionDecisionReason`
- `additionalContext` — 注入上下文但不影响权限

### UserPromptSubmit

用于注入工作流状态：

- `additionalContext` — 注入面包屑上下文

### SubagentStart

用于注入 subagent 上下文：

- `additionalContext` — 注入 subagent 初始上下文（仅支持此字段，不支持 updatedInput）

### SubagentStop

用于验证 subagent 输出：

- `decision: "block"` + `reason` — 输出不合格，要求 subagent 继续补全
- **不支持 additionalContext** — SubagentStop 使用与 Stop 相同的 decision 控制格式
- 如需注入父会话，使用 PostToolUse matcher: Agent

### Stop

用于阻止过早声称完成：

- `decision: "block"` + `reason` — 硬阻断，未完成不能结束
- `additionalContext` — 软警告，提醒但允许继续

### PostToolUse

用于编辑后提醒：

- `additionalContext` — 提醒工作流约束

### PreCompact

用于压缩前保存状态：

- `additionalContext` — 确认状态已保存

## 硬阻断 vs 软警告

| 类型 | 行为 | 可绕过 |
|------|------|--------|
| 硬阻断 | 返回 deny/block，操作不能继续 | 否 |
| 软警告 | 返回 allow + reason，操作可继续 | 是，`override team-kit guardrail: <reason>` |
| 上下文注入 | 只注入上下文，不影响执行 | 不适用 |

## 输出格式

### 硬阻断 (PreToolUse)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Source edit is blocked in planning phase..."
  }
}
```

### 硬阻断 (Stop/SubagentStop)

```json
{
  "decision": "block",
  "reason": "Cannot mark task done. Selected review gate is missing PASS/FAIL.",
  "hookSpecificOutput": {
    "hookEventName": "Stop"
  }
}
```

### 软警告

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Warning: editing lockfile..."
  }
}
```

### 上下文注入

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "<workflow-state>...</workflow-state>"
  }
}
```

## Hook 辅助库

`claude/hooks/lib/hook_output.py` 提供统一输出函数：

```python
pretool_deny(reason)     # PreToolUse 硬阻断
pretool_allow(reason)    # PreToolUse 允许
pretool_warn(reason)     # PreToolUse 允许但带警告
block(reason)            # Stop/SubagentStop 硬阻断
allow(reason)            # Stop/SubagentStop 允许
warn(context)            # 软警告
additional_context(text) # 上下文注入
```

## 常见问题

**Q: 硬阻断可以 override 吗？**
A: 不可以。硬阻断涉及安全或流程完整性，必须修复问题才能继续。

**Q: 软警告怎么 bypass？**
A: 在 prompt 中说 `override team-kit guardrail: <reason>`。仅对低风险 warning 生效。

**Q: Hook 没触发怎么办？**
A: 检查 `.claude/settings.json` 中 hook schema 是否正确。运行 `python3 .trellis/scripts/validate_claude_settings.py` 检查。
