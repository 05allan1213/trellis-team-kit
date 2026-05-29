# 护栏

trellis-team-kit 运行时护栏说明。

## 硬阻断

以下操作会被**不可绕过地阻断**：

### 危险命令

- `rm -rf` — 递归强制删除
- `git reset --hard` — 硬重置
- `git clean -fd` — 强制清理未跟踪文件
- `git push --force` / `git push -f` / `git push --force-with-lease` — 强制推送

### 敏感文件

- `.env` / `.env.local` / `.env.*` — 环境变量文件
- `secrets.*` / `credentials.*` — 密钥/凭证文件
- 删除 `migrations/` 下的迁移文件

### 规划期源码编辑

在以下状态下编辑源码会被阻断：
- `PLANNING_PRD` / `PLANNING_GRILL` / `PLANNING_DESIGN` / `PLANNING_IMPLEMENT`
- `WAITING_IMPLEMENTATION_APPROVAL`

**Task 创建同意 ≠ 实现同意。** 必须等用户明确批准实现后才能编辑源码。

### 未批准的操作

- `task.py start` 在规划期执行
- 在 `WAITING_IMPLEMENTATION_APPROVAL` 状态 spawn implementer

### 未完成时结束

Stop guard 在以下情况会 block：
- Active task 存在但 check 未通过
- Selected review gate 缺失/FAIL/无 PASS/FAIL
- Spec update decision 缺失
- Validation 缺失/FAIL
- Task 未 archive 但声称 done

## 软警告

以下操作会触发警告但**可以继续**：

- 编辑 lockfile（package-lock.json, yarn.lock 等）
- 编辑 generated files
- 编辑 shared/common 目录下的共享类型
- 编辑 .env.example / docker-compose / CI 配置
- 编辑（非删除）migration 文件
- 大范围格式化

## Override 规则

### 可以 override 的

软警告可以通过以下方式 bypass：

```
override team-kit guardrail: <reason>
```

例如：`override team-kit guardrail: updating lockfile after dependency upgrade`

### 不可以 override 的

硬阻断无法 override。包括：
- 密钥/凭证文件编辑
- `rm -rf`
- 强制推送
- 硬重置
- 规划期源码编辑
- 未批准的实现操作

## 绕过所有 hooks

在紧急情况下，可以设置环境变量禁用 hooks：

```bash
export TRELLIS_DISABLE_HOOKS=1
```

或在 `.claude/settings.local.json` 中覆盖 hook 配置。**仅在紧急调试时使用。**

## 故障排除

**Q: Hook 误阻断合法操作**
A: 检查当前 workflow state 是否正确。如果 task status 是 `planning` 但你确实需要编辑源码，先让用户明确说 "approve implementation" / "start implementation" 将状态推进到 `in_progress`。

**Q: 如何查看 guardrail 日志**
A: 每个 hook 输出 JSON 到 stdout。Claude Code 在 hook 触发时显示这些输出。可以通过设置 `TRELLIS_GUARDRAIL_LOG` 环境变量启用文件日志。
