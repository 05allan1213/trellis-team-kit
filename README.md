# trellis-team-kit

在 Trellis 官方基础上叠加团队规范，一条命令给新项目装上统一的 AI 开发入口。

## 环境准备

```bash
npm install -g @mindfoldhq/trellis
```

需要 Node.js 18+、Python 3.9+、git。

## 新项目初始化

```bash
mkdir my-project && cd my-project
bash <(curl -fsSL https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh) 你的名字
```

一行搞定。把 `你的名字` 换成你的英文名（如 `ayp`）。

> **不要**在 `~` 目录执行。必须先 `cd` 到项目目录。

如果 `raw.githubusercontent.com` 在你那边超时，用克隆方式：

```bash
git clone https://github.com/05allan1213/trellis-team-kit.git ~/trellis-team-kit
mkdir my-project && cd my-project
~/trellis-team-kit/bootstrap/init-local.sh 你的名字
```

## 初始化后你会得到什么

```
AGENTS.md          ← 团队入口（带 Trellis + Superpowers + OMC 路由）
CLAUDE.md          ← 同上，Claude Code 平台版
.claude/           ← Trellis 官方平台适配层（不改）
.trellis/
  workflow.md      ← 团队魔改版工作流
  spec/            ← 团队编码规范
  .team-kit-version← 记录初始化时用的模板版本
```

## 日常怎么用

启动一个任务只需要这一句话：

> 我们开始一个 Trellis 任务，走 B Create a task，不要 inline。

更多模板（标准任务、小修跳过、OMC 并行确认等）见 `prompt.md`。

核心规则就是三个：

- **实现类工作** → 建 Trellis task，走 Plan → Execute + Check → Finish
- **纯问答 / 讨论** → 直接聊，不开 task
- **极小改动想跳过流程** → 消息里带 "跳过 Trellis" / "no task"

## 常见问题

### `trellis: command not found`

```bash
npm install -g @mindfoldhq/trellis
```

### curl 一直卡在 0%

`raw.githubusercontent.com` 超时，改用上面的克隆方式。

### 提示不能在 home 目录运行

你没进项目目录。必须先 `mkdir my-project && cd my-project`。

## 更新团队模板

团队模板有更新时，用克隆方式安装的团队成员执行：

```bash
cd ~/trellis-team-kit && git pull
```

已初始化项目里的 `.trellis/.team-kit-version` 记录了初始化时的模板版本。对比文件内容可以知道项目用的是哪个版本。

---

## 维护者参考

### 想只装 spec 不覆盖 AGENTS.md / CLAUDE.md / workflow.md

```bash
trellis init -u your-name --claude \
  --registry gh:05allan1213/trellis-team-kit/marketplace \
  --template web-app
```

只会安装 `.trellis/spec/`，适合已有项目只引入团队编码规范。

### 修改哪些文件生效什么

| 修改目标 | 改什么 |
|---|---|
| 团队编码规范 | `marketplace/specs/web-app/` |
| 团队入口文件 | `entry/AGENTS.md` / `entry/CLAUDE.md` |
| 团队工作流 | `workflow/workflow.md` |
| 初始化脚本 | `bootstrap/init.sh` / `bootstrap/init-local.sh` |
| 日常提示词模板 | `prompt.md` |

修改后 `git commit` + `git push` 即生效（克隆方式用户 `git pull` 获取更新）。