# trellis-team-kit — 提示词模板

## 0. 日常分流原则

所有工作分三类：

**A. 纯问答 / 解释 / 查资料 / 讨论方案（L0）**
→ 直接问，不开 Trellis task。

**B. 任何实现 / 改代码 / 构建 / 重构 / bug 修复（L2-L5）**
→ 默认创建 Trellis task，走 Plan → Execute + Check + Review → Finish。

**C. 极小改动，适合直接 Inline（L1）**
→ AI 应先建议 direct inline edit；用户也可以明确说："跳过 Trellis" / "no task" / "别走流程" / "小修一下" / "直接改"。

**AI 可以在明显 L1、局部、可逆、低风险时建议不建 task；一旦范围扩大，立即升级到标准 Trellis 流程。**

**如果请求边界模糊、无法稳定判成某个等级，AI 应先给出建议等级和一句理由，再等我确认、改级或补充上下文；未确认前不要开始实现。**

---

## 1. 标准任务模板：进入 Plan 阶段

适用场景：新功能、bug 修复、重构、测试、文档、配置、自动化、UI、API、数据库变更等任何改动仓库内容的工作。

模板：

```text
我们开始一个 Trellis 任务。

请按当前仓库的 `.trellis/workflow.md` 执行，走 B Create a task，不要 inline。

任务类型：
【功能开发 / bug 修复 / 重构 / 测试 / 文档 / 配置 / 自动化 / 其他】

任务目标：
【一句话写清楚这次要完成什么】

背景：
【可选：为什么要做；当前问题是什么】

范围：
【这次允许改什么：代码 / 配置 / API / 数据 / 测试 / 文档 / 构建 / CI / UI / 脚本】

非目标：
【这次明确不做什么，防止 AI 扩大范围】

约束：
【已有接口、架构、规范、兼容性要求、性能要求、安全要求】

验收标准：
1. 【完成后的可观察结果】
2. 【需要覆盖的正常场景】
3. 【需要覆盖的异常场景】
4. 【需要执行的检查：lint / typecheck / test / build / e2e / 手动验证】
5. 【是否需要兼容旧逻辑、旧数据或旧接口】

工具策略：
1. Trellis 负责生命周期、PRD、Acceptance Criteria、Check、Finish。
2. PRD 未确认前，不要进入实现。
3. Superpowers 只在需求不清、方案复杂、架构影响、跨模块、高风险或多方案取舍时使用；小而明确的任务保持轻量。
4. 默认并行优先用 Trellis 原生能力（subagent、reviewer background agents、worktree）；不要把“并行”默认等同于 OMC。
5. OMC 指的是 oh-my-claudecode 的 `ulw/ultrawork` 并行模式；只有 PRD 确认、任务可安全拆分、且确实需要高级编排时才推荐。
6. 如果 OMC / Superpowers / MCP / 某个 skill 没安装、不可用或当前环境不支持，不应阻塞主流程；说明限制后，回退到可用的 Trellis 原生路径继续。
7. MCP / testing / debugging / review / browser 等能力按场景触发，不要全局加载。
8. 需要读取 spec 时，从 `.trellis/spec/index.md` 路由，只加载相关文件。
9. 不要擅自扩大范围、替换技术栈、重写系统或改变核心架构。

Plan 阶段要求：
1. 创建 task（task.py create）。
2. 使用 trellis-brainstorm 产出并迭代 prd.md。
3. PRD 写清楚目标、范围、非目标、约束、验收标准。
4. L3-L5 运行 trellis-grill-me 挑刺 PRD；L2 仅在需求不清或风险升高时运行。
5. 写 implement.md：L2 用 minimal implement.md；L3-L5 写完整 dev strategy + Review Gate Contract；L4/L5 补充 design.md。
6. L3-L5 配置 implement/check context（JSONL）；L2 可跳过，除非额外上下文能明显降低风险。
7. Plan 完成后停下来，等待我确认，不要开始改代码。
```

---

## 2. PRD 确认模板：进入 Execute + Check + Review

```text
Plan 阶段已确认。

请进入 Execute + Check + Review。

执行要求：
1. 如果 task 尚未 start，先把 `implement.md` 的 `Implementation Approval` 区块写完整：
   - 勾选 `approved`
   - 填写 user message / timestamp / summary approved
   - 勾选 `Allowed to run task.py start? -> yes`
2. 然后再执行 task.py start，进入 in_progress。
3. 运行 trellis-before-dev 读取所有 artifacts，输出 before-dev.md 约束和 scope-manifest.json 范围契约。
4. 严格按照 prd.md 和 Acceptance Criteria 实现。
5. 默认使用 trellis-implement → trellis-check → Review Gates subagent 路径。
6. Check 通过后，按 implement.md 的 Review Gate Contract 执行审查门禁。
7. 所有 selected review gates PASS 后，先停下来汇报结果，等待我明确说“进入 Finish 阶段”。
8. 在我确认 Finish 之前，不要自动写 finish.md、不要自动做 spec update、不要自动 commit、不要自动 archive。
9. 我一旦明确说“进入 Finish 阶段”，先把 `finish.md` 里的 `Finish Approval` 区块按我的原话写完整，再继续后续收尾。
10. `finish.md` 必须填写 `Delivery Sync Check`，明确检查 README / 示例命令 / API 文档 / implemented-vs-planned 状态。
11. Phase 3.2 commit 之前，先运行 `python3 ./.trellis/scripts/prepare_finish_workspace.py`，清理 `.omc/` 等本地运行时状态。
12. 不要直接执行 `task.py archive`；归档必须走 `python3 ./.trellis/scripts/finalize_task_archive.py <task-dir>`。
11. 不要 main session 直接改代码，除非我明确说 "do it inline" / "no sub-agent" / "你直接改"。
12. 不要扩大范围，不要实现 PRD 之外的内容。

工具策略：
1. 默认执行路径是标准 Trellis sub-agent；如果只是 reviewer 并行或 worktree 隔离，不需要把它称为 OMC。
2. 如果任务可以安全拆分，并且并行能明显提升效率，请先判断 Trellis 原生并行是否足够；只有需要更强编排时才提议 OMC `ulw/ultrawork`。
3. 如果要用 OMC `ulw/ultrawork`，先给出 agent 拆分方案，等待我确认后再启用。
4. 如果我没有确认 OMC，就继续使用标准 Trellis 路径。
5. 如果 OMC agent 空转、失败或无法继续推进，不要静默切回串行；先说明情况，再等我确认是重试 OMC 还是回退到 Trellis 原生路径。
6. 如果后续出现 reviewer background agents，要明确说明“这是 Trellis 原生 review gate 并行，不是 OMC”。
7. 如果 OMC / Superpowers / MCP / 某个 skill 当前不可用，不要因为扩展缺失而卡住；说明限制，并使用可用的原生路径继续。
8. 如果 Check 反复失败、修复互相冲突、或发现 PRD 缺陷，请暂停实现；优先使用 Superpowers 分析根因，如不可用则自行显式分析，并说明是否需要回到 Plan 修改 PRD。
9. 根据任务类型按需使用 testing / debugging / browser / review / MCP 等能力。
10. bug 修复必须说明复现、根因、修复方式和回归验证。
11. 涉及接口、数据或配置变更时，必须说明兼容性和风险。
12. Review gate FAIL 时，回到 implement 修复，修复后重新跑 check，再重新跑该 review gate。禁止跳过 failed gate。

完成后请给出：
1. 实现了什么
2. 修改了哪些文件
3. 执行了哪些检查
4. 哪些 review gates 执行了，每个 gate 的 PASS/FAIL 结果
5. 是否满足 Acceptance Criteria
6. 是否存在风险、遗留问题或需要我确认的事项
```

---

## 3. Review 补充模板（仅 Review 阶段需要重跑时使用）

适用场景：Execute + Check + Review 流程中 Review gate FAIL，修复后需要重跑特定 gate。

模板：

```text
重跑 Review gate：【spec-review / code-review / architecture-review / deep-review / merge-review】

修复内容：
【说明刚才修了什么】

请重新执行该 review gate，确认修复是否通过。
```

---

## 4. Finish 阶段模板：收尾与沉淀

```text
进入 Finish 阶段。

请按 `.trellis/workflow.md` 的 Phase 3 执行。

收尾要求：
1. 做最终质量验证，确认是否满足 prd.md 的 Acceptance Criteria。
2. `finish.md` 必须完整记录：
   - Finish Approval（用户进入 Finish 的原始批准）
   - Observable Outcomes
   - Delivery Sync Check
   - Spec Update Decision
3. 如果任务中出现重复调试、反复失败或同类问题，请运行 trellis-break-loop 做 debug retrospective。
4. 执行 trellis-update-spec 判断：
   - 如果需要更新 spec，请说明应该沉淀什么规则、经验或约定。
   - 如果不需要更新 spec，请说明理由。
   - 不要为了更新而更新，只有可复用的团队规则才沉淀。
5. 按 workflow Phase 3.2 处理 commit：
   - 先运行 `python3 ./.trellis/scripts/prepare_finish_workspace.py`，再查看 dirty state。
   - 区分本次 AI 修改和未知脏文件。
   - 给出 proposed commit plan。
   - 未经确认，不要提交未知脏文件。
   - 不要 push。
6. commit 处理完成后，执行 /trellis:finish-work 收尾（内部使用 `finalize_task_archive.py`）。

最后总结：
1. 本次完成了什么
2. 修改了哪些文件
3. 执行了哪些检查
4. 是否满足 Acceptance Criteria
5. 是否更新了 spec，或为什么不需要更新
6. 是否还有风险、遗留问题或人工确认项
```

---

## 5. 小修逃逸模板：直接 Inline，不创建 Task

适用场景：改文案、改注释、改明显 typo、局部样式微调、临时验证、极小配置调整。AI 也可以主动建议你走这条路径。

模板：

```text
小修一下，跳过 Trellis，直接改。

目标：
【例如：把按钮文案从"提交"改成"保存"】

范围：
【只允许修改与该目标直接相关的内容】

要求：
1. 不创建 task。
2. 不扩大范围。
3. 不顺手重构。
4. 改完说明修改了哪些文件。
5. 如发现问题超出"小修"范围，请暂停并提醒我改走标准 Trellis 流程。
```

---

## 6. OMC `ulw/ultrawork` 并行执行确认模板

适用场景：Plan 完成、PRD 已确认、AC 清晰、可安全拆分、并行能明显提升效率，且 Trellis 原生并行已经不足以覆盖编排需求。

拆分方案必须包含：

```text
OMC Agent 拆分方案：

Agent 1: 【名称】
  owns:     【独占修改的文件/目录，其他 agent 不可改】
  readonly:  【只读的文件/目录，用于理解上下文】
  shared:    【需要和其他 agent 协作的接口/类型/契约】

Agent 2: 【名称】
  owns:     【独占修改的文件/目录】
  readonly:  【只读的文件/目录】
  shared:    【协作接口/类型/契约】

Shared Contract:
  【agent 间共享的类型定义、API 接口、事件格式等】
  【谁负责定义，谁负责消费】

Merge-Review 计划:
  【集成后需要检查的冲突点】
  【shared 区域的变更需要哪些 agent 确认】
  【是否需要 trellis-merge-review gate】
```

确认后启动：

```text
我确认使用 OMC `ulw/ultrawork` 并行模式。

请按刚才的拆分方案启动 agents：
1. 每个 agent 必须带上 active task path。
2. 每个 agent 只处理自己的 owns scope，不修改其他 agent 的 owns 区域。
3. shared 区域的变更必须先写入 shared contract，再由消费方 agent 读取。
4. 需要的 Skills / MCPs 由 main agent 按角色分配。
5. main agent 负责集成、冲突解决和最终结果。
6. 不允许扩大 PRD 范围。
7. 集成后仍然必须走 trellis-check。
8. 如果拆分方案中标记了 merge-review，集成后必须走 trellis-merge-review gate。
9. 如果 OMC 执行失败或 agent 空转，先停下来说明情况，等待我确认是重试还是回退；不要静默改成串行实现。
```

如果还没给拆分方案，先用：

```text
这个任务看起来可以并行。

请先给出 OMC `ulw/ultrawork` agent 拆分方案（包含 owns / readonly / shared contract / merge-review 计划），我确认后再启动。
```

---

## 7. 懒人标准任务模板

适用场景：不想填模板，只想说目标，让 AI 自动走完整个流程。

模板：

```text
【一句话目标】
```

AI 会自动：
1. 判断任务等级（L1-L5）
2. 如果明显是 L1，则建议 inline；如果边界模糊，则先给建议等级并等我确认/改级；否则创建 Trellis task
3. 运行 brainstorm → dev-strategy；L3-L5 还要 grill-me，按等级决定是否需要 design.md / JSONL
4. 判断是否需要 Superpowers（需求不清 / 架构权衡 / 多方案取舍时自动启用）
5. 判断是否建议并行：默认先考虑 Trellis 原生并行；只有需要高级编排时才建议 OMC `ulw/ultrawork`，并等待确认
6. 停下来等你确认 Plan
7. 你确认进入 Execute 后，执行 before-dev → implement → check → review gates
8. review 全部通过后停下来，等你明确说“进入 Finish 阶段”
9. 你确认 Finish 后，再执行 update-spec → commit → finish-work

你只需要在两个固定确认门、一个条件确认门操作：
1. **Plan 确认** — PRD/design/implement plan 准备好后，你说"确认"或"改一下 xxx"
2. **OMC 确认** — 如果 AI 建议 OMC `ulw/ultrawork` 并行，你说"确认"或"不用"
3. **Finish 确认** — Execute + Check + Review 全部通过后，你说"进入 Finish 阶段"

除这几个确认门外，其余流程自动推进。

---

## 8. 团队日常最简版

```text
懒人模式（推荐）：
"【一句话目标】"                        ← AI 自动走完全流程

标准任务：
"我们开始一个 Trellis 任务，走 B Create a task，不要 inline。"

PRD 确认：
"Plan 阶段已确认，进入 Execute + Check + Review。"

小修：
"小修一下，直接改。"

结束：
"进入 Finish 阶段，按 workflow Phase 3 收尾：update-spec，commit，finish-work。"
```
