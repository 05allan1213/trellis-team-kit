# 团队 Trellis 魔改版日常提示词模板

## 0. 日常分流原则

以后团队统一按这三类使用：

A. 纯问答 / 解释 / 查资料 / 讨论方案
→ 直接问，不开 Trellis task。

B. 任何实现 / 改代码 / 构建 / 重构 / bug 修复 / 联调 / 测试补充 / 文档修改
→ 默认创建 Trellis task，走 Plan → Execute + Check → Finish。

C. 极小改动，想跳过 Trellis
→ 必须在当前消息里明确说：
“跳过 Trellis / 别走流程 / 小修一下 / 直接改 / 先别建任务 / no task / just do it”。

AI 不能自己判断“小所以不建 task”。

---

# 1. 标准任务模板：进入 Plan 阶段

适用场景：

* 新需求
* 功能开发
* bug 修复
* 联调
* 重构
* 测试补充
* 文档整理
* 配置调整
* 自动化脚本
* 工程化优化
* UI 调整
* 数据处理
* API 修改
* 数据库变更
* 架构整理
* 任意需要改动仓库内容的任务

模板：

```text
我们开始一个 Trellis 任务。

请按当前仓库的 `.trellis/workflow.md` 执行，走 B Create a task，不要 inline。

任务类型：
【功能开发 / bug 修复 / 重构 / 联调 / 测试 / 文档 / 配置 / 自动化 / 其他】

任务目标：
【一句话写清楚这次要完成什么】

背景：
【可选：为什么要做；当前问题是什么；来自哪个需求 / 反馈 / bug】

范围：
【这次允许改什么：代码 / 配置 / 接口 / 数据 / 测试 / 文档 / 构建 / CI / UI / 脚本 等】

非目标：
【这次明确不做什么，防止 AI 扩大范围】

输入与约束：
【可选：已有接口、已有架构、已有规范、兼容要求、性能要求、安全要求、技术栈限制等】

验收标准：
1. 【完成后的可观察结果】
2. 【需要覆盖的正常场景】
3. 【需要覆盖的异常场景】
4. 【需要执行的检查：lint / typecheck / test / build / e2e / 手动验证 等】
5. 【是否需要兼容旧逻辑、旧数据或旧接口】

工具策略：
1. Trellis 负责生命周期、PRD、Acceptance Criteria、Check、Finish。
2. PRD 未确认前，不要进入实现。
3. Superpowers 只在需求不清、方案复杂、架构影响、跨模块、高风险或多方案取舍时使用；小而明确的任务保持轻量。
4. oh-my-claudecode 只能在 PRD 确认后、任务可安全拆分时推荐使用；必须先给出并行 agent 拆分方案，等我明确确认后才能启用。
5. MCP、testing、debugging、review、browser 等能力按场景触发，不要全局加载。
6. 需要读取 spec 时，从 `.trellis/spec/index.md` 路由，只加载相关文件。
7. 不要擅自扩大范围、替换技术栈、重写系统或改变核心架构。

Plan 阶段要求：
1. 创建 task。
2. 使用 trellis-brainstorm 产出并迭代 `prd.md`。
3. PRD 写清楚目标、范围、非目标、约束、验收标准。
4. 如有必要，补充 research / info。
5. 配置必要的 implement/check context。
6. Plan 完成后停下来，等待我确认，不要开始改代码。
```

---

# 2. PRD 确认模板：进入 Execute + Check

```text
Plan 阶段已确认。

请进入 Execute + Check。

执行要求：
1. 如果 task 尚未 start，请先按 workflow 执行 `task.py start`，进入 in_progress。
2. 严格按照 `prd.md` 和 Acceptance Criteria 实现。
3. 默认使用标准 Trellis 执行路径：trellis-implement → trellis-check。
4. 不要 main session 直接改代码，除非我明确说“你直接改 / 不用 sub-agent / main session 写就行”。
5. 不要扩大范围，不要实现 PRD 之外的内容。

工具策略：
1. 如果任务可以安全拆分，并且并行能明显提升效率，请先给出 oh-my-claudecode agent 拆分方案，等待我确认后再启用。
2. 如果我没有确认 OMC，就继续使用标准 Trellis sub-agent 路径。
3. 如果 Check 反复失败、修复互相冲突、或发现 PRD 缺陷，请暂停实现，使用 Superpowers 分析根因，并说明是否需要回到 Plan 修改 PRD。
4. 根据任务类型按需使用 testing / debugging / browser / review / MCP 等能力。
5. bug 修复必须说明复现、根因、修复方式和回归验证。
6. 涉及接口、数据或配置变更时，必须说明兼容性和风险。

完成后请给出：
1. 实现了什么
2. 修改了哪些文件
3. 执行了哪些检查
4. 是否满足 Acceptance Criteria
5. 是否存在风险、遗留问题或需要我确认的事项
```

---

# 3. Finish 阶段模板：收尾与沉淀

```text
进入 Finish 阶段。

请按当前仓库 `.trellis/workflow.md` 的 Phase 3 执行。

收尾要求：
1. 做最终质量验证，确认是否满足 `prd.md` 的 Acceptance Criteria。
2. 如果任务中出现重复调试、反复失败或同类问题，请做 debug retrospective。
3. 执行 trellis-update-spec 判断：
   - 如果需要更新 spec，请说明应该沉淀什么规则、经验或约定。
   - 如果不需要更新 spec，请说明理由。
   - 不要为了更新而更新，只有可复用的团队规则才沉淀。
4. 按 workflow 的 Phase 3.4 处理 commit：
   - 先查看 dirty state。
   - 区分本次 AI 修改和未知脏文件。
   - 给出 proposed commit plan。
   - 未经确认，不要提交未知脏文件。
   - 不要 push。
5. commit 处理完成后，执行或提示执行 `/trellis:finish-work` 收尾。

最后总结：
1. 本次完成了什么
2. 修改了哪些文件
3. 执行了哪些检查
4. 是否满足 Acceptance Criteria
5. 是否更新了 spec，或为什么不需要更新
6. 是否还有风险、遗留问题或人工确认项
```

---

# 4. 小修逃逸模板：直接 Inline，不创建 Task

适用场景：

* 改文案
* 改注释
* 改一个明显 typo
* 改一个非常局部的样式
* 临时验证一个小点
* 极小范围配置调整

模板：

```text
小修一下，跳过 Trellis，直接改。

目标：
【例如：把按钮文案从“提交”改成“保存”】

范围：
【只允许修改与该目标直接相关的内容】

要求：
1. 不创建 task。
2. 不扩大范围。
3. 不顺手重构。
4. 改完说明修改了哪些文件。
5. 如发现问题超出“小修”范围，请暂停并提醒我改走标准 Trellis 流程。
```

---

# 5. OMC 并行执行确认模板

适用场景：

* 任务已经完成 Plan
* PRD 已确认
* Acceptance Criteria 清晰
* 可以安全拆分
* 并行执行能明显提升效率

模板：

```text
我确认使用 oh-my-claudecode 并行模式。

请按刚才的拆分方案启动 agents：
1. 每个 agent 必须带上 active task path。
2. 每个 agent 只处理自己的 assigned scope。
3. 需要的 Skills / MCPs 由 main agent 按角色分配。
4. main agent 负责集成、冲突解决和最终结果。
5. 不允许扩大 PRD 范围。
6. 完成后仍然必须走 trellis-check。
```

如果还没给拆分方案，先用：

```text
这个任务看起来可以并行。

请先给出 oh-my-claudecode agent 拆分方案，我确认后再启动。
```

---

# 6. 团队日常最简版

日常只需要记住这四句：

```text
标准任务：
“我们开始一个 Trellis 任务，走 B Create a task，不要 inline。”

PRD 确认：
“Plan 阶段已确认，进入 Execute + Check。”

小修：
“小修一下，跳过 Trellis，直接改。”

结束：
“进入 Finish 阶段，按 workflow Phase 3 收尾，判断 update-spec，处理 commit，然后 finish-work。”
```
