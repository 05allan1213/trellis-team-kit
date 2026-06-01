# 安装指南 — trellis-team-kit

## 环境要求

- **Node.js 18+** — Trellis CLI 需要
- **Python 3.9+** — hooks 和 validators 需要
- **Git** — task 生命周期和 worktree 需要
- **Claude Code** — 本套件集成的 AI 编程助手

## 一行安装

在项目目录中执行：

```bash
mkdir my-project && cd my-project && git init
bash <(curl -fsSL https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh) 你的名字
```

如果 `raw.githubusercontent.com` 超时，用克隆方式：

```bash
git clone https://github.com/05allan1213/trellis-team-kit.git ~/trellis-team-kit
mkdir your-project && cd your-project && git init
~/trellis-team-kit/bootstrap/init.sh 你的名字
```

## 安装后你会得到什么

### 入口文件
- `AGENTS.md` — AI agent 指令，含 L0-L5 路由和双同意门禁
- `CLAUDE.md` — Claude Code 专用指令和工作流规则

### 工作流
- `.trellis/workflow.md` — 完整状态机，含全部阶段、状态和转换

### Claude Code 资产
- `.claude/settings.json` — hook 配置和权限
- `.claude/skills/` — 14 个可复用 skills
- `.claude/agents/` — 9 个专用 subagents
- `.claude/hooks/` — 9 个工作流守护 hooks（含通知 hook）
- `.claude/commands/trellis/` — slash 命令

### Spec 规范
- `.trellis/spec/` — 分层编码规范（frontend、backend、shared、infra、guides），按需加载

### Task 模板
- `.trellis/templates/` — 各任务级别的产物模板

### 验证器
- `.trellis/scripts/validate_runtime_hardening.py` — 总入口，运行所有静态检查
- `.trellis/scripts/validate_claude_settings.py` — settings.json hook schema 检查
- `.trellis/scripts/validate_naming_map.py` — 命名一致性检查
- `.trellis/scripts/validate_hooks.py` — hook 脚本存在性和结构检查
- `.trellis/scripts/validate_task.py` — task 产物完整性检查
- `.trellis/scripts/validate_review_gates.py` — review gate 完成度检查

## 本地个人配置（可选）

团队初始化后，设置个人工作区：

```bash
~/trellis-team-kit/bootstrap/init-local.sh 你的名字
```

这会创建：
- `.claude/settings.local.json` — 本地权限（gitignored）
- `.trellis/workspace/<你的名字>/` — 个人日志和偏好

## 验证安装

```bash
# 检查 Trellis 是否正常
trellis status

# 验证 spec 索引完整性
python3 .trellis/scripts/validate_runtime_hardening.py

# 开始第一个任务：向 Claude Code 描述你想做什么
```

## 常见问题

### "trellis command not found"
```bash
npm install -g @mindfoldhq/trellis
```

### "Not a git repository"
```bash
git init
git add .
git commit -m "Initial commit"
```

### Hooks 不生效
确保 Python 3.9+ 可用，且 `.claude/settings.json` 中的 hook 路径正确。Hook 脚本通过 `python3` 调用，不需要执行权限。如果 shell hook 不生效，检查执行权限：
```bash
chmod +x .claude/hooks/trellis-notify.sh
```
