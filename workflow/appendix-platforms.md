# 跨平台附录

本文档保存了之前在主工作流中的多平台内容。
主 `workflow.md` 是 Claude Code-first。其他平台在此处归档供参考。

## 支持的平台（历史 / 未来）

当前主线仅支持 **Claude Code**。以下平台文档供未来可能扩展的团队参考：

- Cursor
- OpenCode
- Gemini CLI
- Codex CLI
- Kiro
- Copilot
- Pi

## 各平台的 Agent 派发机制

每个平台有自己的 agent 派发机制。工作流概念
（Plan → Execute → Check → Review → Finish）是通用的，但派发语法不同。

### Cursor

Cursor 使用 `.cursor/agents/` 定义 agent，`.cursor/hooks/` 定义 hooks。

### OpenCode

OpenCode 使用 `.opencode/agents/` 和 `.opencode/plugins/` 定义 hooks。

### Gemini CLI

Gemini CLI 使用 `.gemini/agents/` 和 `.gemini/hooks/`。

### Codex CLI

Codex 使用 `.codex/agents/` 和 `.codex/hooks/`。

## 适配工作流到其他平台

要将 trellis-team-kit 适配到非 Claude Code 平台：

1. 将 hooks 移植到目标平台的 hook 系统
2. 将 agent 定义移植到目标平台的 agent 格式
3. 更新目标平台对应的 `settings.json` 等价配置
4. 更新入口文档（`AGENTS.md` 等价文件）
5. 在目标平台上测试完整状态机

## 为什么选择 Claude Code-first

选择 Claude Code 作为主平台的原因：

- 原生支持 hooks（SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、SubagentStop、Stop、PreCompact）
- 原生 subagent 系统，支持上下文注入
- 基于 settings 的 skill 和权限管理
- 可配合 Superpowers、OMC 等扩展，但主路径不依赖它们
- 团队一致性：单一平台降低认知负担
