# OMC 策略

oh-my-claudecode 与 trellis-team-kit 集成的策略说明。
这里的 OMC 特指官方 `ulw/ultrawork` 并行模式。

## 何时使用 OMC

- L4/L5 任务，且交付物可独立验证
- Parent/child 任务树
- 跨 package 并行工作
- 用户已明确确认 OMC 并行模式
- Trellis 原生并行（subagent / reviewer background agents / worktree）已经不足以覆盖编排需求

## 何时不使用 OMC

- L0-L3 任务（使用主会话或单个 subagent）
- 紧密耦合、无法拆分的工作
- 用户未明确确认并行模式
- 规划阶段（OMC 仅用于执行）
- 当前环境未安装 OMC，或无法稳定调用 OMC `ulw/ultrawork`

## OMC 不可用时

- 不要阻塞 Trellis 主流程
- 明确告诉用户当前环境无法使用 OMC `ulw/ultrawork`
- 回退到 Trellis 原生路径：subagent、reviewer background agents、worktree
- 如果用户明确批准的是 OMC，而不是泛化的“并行”，则回退前需要重新说明并获得确认

## 规则

1. OMC 不得决定范围 — Trellis PRD 拥有范围
2. OMC 不得绕过 Plan — 规划产物必须完整
3. OMC 不得绕过 Check — 集成后仍需 trellis-check
4. OMC 不得替代 Trellis 任务状态 — Trellis 拥有生命周期
5. 使用 OMC 时 merge-review 是强制的
6. 主 agent 拥有集成、冲突解决和最终报告
