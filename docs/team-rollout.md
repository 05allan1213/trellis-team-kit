# 团队推广指南 — trellis-team-kit

## 概述

本指南帮助你将 trellis-team-kit 引入团队，涵盖推广流程、培训计划和常见问题。

## 推广流程

### 第一阶段：试点（1-2 周）

从 1-2 名日常使用该套件的开发者开始，收集反馈。

1. **在单个项目上安装** — 选择有活跃功能开发的项目
2. **运行 init.sh** — 设置开发者工作区
3. **完成 3-5 个任务** — 至少覆盖一个 L2、一个 L3、一个 L4 任务
4. **收集反馈** — 哪些好用、哪些困惑、哪些感觉是多余开销
5. **调整 specs** — 自定义 `.trellis/spec/` 以匹配团队实际约定

### 第二阶段：扩展（2-3 周）

增加 3-5 名开发者。

1. **举行 30 分钟启动会** — 讲解工作流、核心概念、现场演示
2. **结对完成首个任务** — 让试点开发者与新加入者结对
3. **监控常见问题** — spec 缺口、路由理解错误、门禁被跳过
4. **迭代 specs** — 根据实际使用模式更新 specs

### 第三阶段：全团队（持续）

向整个团队推广。

1. **记录团队特定自定义** — 改了哪些 specs、加了哪些模板
2. **建立 spec 维护机制** — 谁更新 spec、什么时候更新、怎么更新
3. **审视指标** — 任务完成质量、spec 合规率、审查门禁有效性
4. **持续改进** — 用 `trellis-update-spec` 和 `trellis-break-loop` 捕获经验

## 培训计划

### 第一课：核心概念（30 分钟）

1. **L0-L5 任务分级** — 任务如何分类，每级需要什么
2. **双同意门禁** — 为什么创建同意和实现同意要分开
3. **工作流状态机** — Plan、Execute、Finish 三个阶段及其状态
4. **Spec 加载** — specs 如何按需注入，而非全局加载

核心理念：工作流的存在是为了防止常见 AI 编程错误（范围蔓延、跳过审查、规划阶段改代码），而不是增加官僚流程。

### 第二课：动手实操（45 分钟）

完整走一遍 L3 任务：

1. 向 Claude Code 描述一个功能需求
2. 观察 brainstorm 阶段产出 PRD
3. 观察 grill-me 阶段挑刺 PRD
4. 审视 implement.md 和 Review Gate Contract
5. 批准实现
6. 观察 before-dev → implement → check 循环
7. 观察 code review 门禁
8. 观察 finish-work 流程

### 第三课：进阶话题（30 分钟）

适用于处理 L4/L5 任务的开发者：

1. **Worktree 使用** — 什么时候用、怎么用
2. **OMC 并行执行** — 什么时候有帮助、什么时候增加开销
3. **Parent/child 任务** — 拆分大型交付物
4. **自定义 specs** — 编写和维护团队特定规范
5. **验证器** — 运行验证脚本

## 常见问题

### 每个任务都需要创建 Trellis task 吗？

不。L0（纯问答）直接回答。L1（极小改动）仅在用户要求时才创建 task。AI 不能自己对 L2+ 任务决定跳过 task 创建。

### AI 在规划阶段试图改代码怎么办？

`protect-dangerous-actions` hook 会在规划阶段警告或阻断源码编辑。这是有意为之 — 防止 PRD 还没确认就开始写代码。

### 可以跳过审查门禁吗？

只有 Review Gate Contract 中未选中的门禁可以跳过。选中的门禁必须通过。如果某个门禁 FAIL，工作流回到 IMPLEMENTING — 不能跳过。

### specs 和我们的项目不匹配怎么办？

`.trellis/spec/` 中的 specs 就是用来定制化的。根据团队约定修改它们。套件为 web-app 项目提供了合理默认值，但你的项目可能有不同需求。

### L4/L5 任务必须用 OMC 吗？

不。OMC 只是执行模式选项之一。L4/L5 任务始终可以使用标准 Trellis subagents。OMC 仅在 PRD 确认了可独立并行的工作流时才推荐。

### 如果我已经有 CLAUDE.md 或 AGENTS.md 怎么办？

init 脚本会覆盖它们。运行 init 前备份现有文件。如果你在 `<!-- TRELLIS:START -->` / `<!-- TRELLIS:END -->` 和 `<!-- TEAM-KIT:START -->` / `<!-- TEAM-KIT:END -->` 标记块之外有自定义内容，会保留这些编辑。

### 如何添加项目特定 specs？

1. 在 `.trellis/spec/` 的相应子目录下创建新的 `.md` 文件
2. 在对应 `index.md` 中添加指向它的链接
3. 运行 `python3 validators/validate_spec_index.py .trellis/spec/` 验证
4. 新的 specs 将可用于 `implement.jsonl` / `check.jsonl`

### 可以自定义工作流吗？

可以。工作流定义在 `.trellis/workflow.md` 中。你可以：
- 编辑现有状态中的步骤描述
- 添加自定义状态（必须使用 `[A-Za-z0-9_-]+` 字符集）
- 在现有阶段中添加自定义步骤
- 详见 `workflow.md` 的"Customizing Trellis"部分

## 成功指标

团队采用 2-4 周后，关注以下方面：

1. **一致的 task 产物** — 每个 L2+ 任务都有含 Acceptance Criteria 的 prd.md
2. **审查门禁通过** — code review 和 spec review 能发现真实问题
3. **Spec 被使用** — 实现过程中引用了 specs，没有被忽略
4. **失败门禁正确处理** — FAIL 导致回到 IMPLEMENTING，而不是跳过
5. **Spec 持续更新** — 每个任务完成后经验被沉淀回 specs
6. **返工减少** — 因为规划充分，任务用更少的循环就完成了
