# 验证器

trellis-team-kit 静态验证器说明。

## validate_runtime_hardening.py

总入口，运行所有静态检查：

```bash
python3 .trellis/scripts/validate_runtime_hardening.py
```

输出每个子 validator 的 PASS/FAIL 状态。

## validate_claude_settings.py

检查 `.claude/settings.json` hook 配置：

- settings.json 存在且可解析
- hooks 字段存在
- 每个 event 是 list
- 每个 entry 有 `matcher` 和 `hooks`
- 每个 hook 有 `type: command`
- 每个 command 脚本路径存在
- 推荐的事件都已配置

## validate_naming_map.py

检查命名一致性：

- 所有 agent frontmatter `name` 在 canonical agent 列表中
- Hook 脚本引用的 agent 名称都是 canonical names

## validate_hooks.py

检查 hook 脚本：

- 所有必需 hook 文件存在
- Python 语法正确
- protect-dangerous-actions 包含 deny path
- stop-guard 包含 block path
- subagent-stop-guard 包含 block path
- inject-subagent-context 支持所有 9 个 canonical agents
- lib 模块语法正确

## validate_task.py

检查指定 task 的产物完整性：

```bash
python3 .trellis/scripts/validate_task.py <task-directory>
```

- task.json 存在且有效
- 按 L0-L5 级别检查必需产物
- implement.jsonl / check.jsonl 为有效 JSONL
- Review Gate Contract 存在（L3+）
- finish.md 存在（completed/done 状态）

## validate_review_gates.py

检查 review gate 完成度：

```bash
python3 .trellis/scripts/validate_review_gates.py <task-directory>
```

- 解析 implement.md 中的 selected gates
- 检查每个 gate 对应的 review 文件
- 检查每个文件有 Status 和 PASS/FAIL
- FAIL 状态报告需要回流

## 常见失败和修复

| 失败 | 原因 | 修复 |
|------|------|------|
| "No 'hooks' field in settings.json" | settings.json 格式错误 | 确保使用标准 schema |
| "missing 'matcher' field" | 旧格式 hook | 改为 `{matcher, hooks: [{type, command}]}` |
| "script not found" | hook 脚本路径不对 | 检查 command 中的路径 |
| "missing agent" | hook 未覆盖某 canonical agent | 在 inject-subagent-context.py 中添加 |
| "missing deny path" | protect 没有硬阻断 | 添加 `permissionDecision: deny` 输出 |
| "missing block path" | guard 没有硬阻断 | 添加 `decision: block` 输出 |
