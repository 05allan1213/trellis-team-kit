# 示例任务场景

本目录包含 trellis-team-kit 处理不同类型工作的示例场景。每个场景展示了预期的工作流、产物和审查门禁。

## 场景

### 1. [Typo / 极小改动](./01-typo-tiny-edit.md)

**级别**: L1
**场景**: 修 typo、改注释、改文案
**工作流**: 用户说"跳过 Trellis / 直接改" → 直接编辑 → 轻量检查 → 完成
**产物**: 无
**门禁**: 仅轻量检查

---

### 2. [简单 Bug 修复](./02-simple-bugfix.md)

**级别**: L2
**场景**: 修复原因明确的 bug
**工作流**: 创建 task → prd.md → implement → check → Finish 确认 → finish
**产物**: `prd.md`
**门禁**: `trellis-check`

---

### 3. [普通功能开发](./03-normal-feature.md)

**级别**: L3
**场景**: 在现有模块中添加一个范围明确的功能
**工作流**: 创建 task → prd.md → grill-me → implement.md → implement → check → code-review → Finish 确认 → update-spec → commit → validate → finish
**产物**: `prd.md`、`implement.md`，可选 `design.md`
**门禁**: `trellis-check`、`trellis-code-review`

---

### 4. [跨层 API 变更](./04-cross-layer-api-change.md)

**级别**: L4
**场景**: 修改涉及前端、后端和共享类型的 API
**工作流**: 创建 task → prd.md → grill-me → design.md → implement.md（含 Review Gate Contract）→ before-dev → implement → check → spec-review + code-review + architecture-review → Finish 确认 → update-spec → commit → merge-review → validate → finish
**产物**: `prd.md`、`design.md`、`implement.md`、`research/`
**门禁**: `trellis-check`、`trellis-spec-review`、`trellis-code-review`、`trellis-code-architecture-review`
**执行方式**: Subagent + worktree

---

### 5. [前端组件](./05-frontend-component.md)

**级别**: L3
**场景**: 新增或修改 UI 组件
**工作流**: 创建 task → prd.md → grill-me → implement.md → before-dev（加载组件规范）→ implement → check → code-review → Finish 确认 → update-spec → commit → validate → finish
**产物**: `prd.md`、`implement.md`
**门禁**: `trellis-check`、`trellis-code-review`
**关注 spec**: 前端组件规范、类型安全

---

### 6. [后端持久化变更](./06-backend-persistence-change.md)

**级别**: L4
**场景**: 修改数据库 schema、新增模型、修改数据访问模式
**工作流**: 创建 task → prd.md → grill-me → design.md → implement.md → before-dev（加载数据库规范）→ implement → check → spec-review + code-review + architecture-review → Finish 确认 → update-spec → commit → merge-review → validate → finish
**产物**: `prd.md`、`design.md`、`implement.md`、`research/`
**门禁**: `trellis-check`、`trellis-spec-review`、`trellis-code-review`、`trellis-code-architecture-review`
**关注 spec**: 数据库规范、错误处理、后端目录结构

---

### 7. [重构](./07-refactor.md)

**级别**: L4 或 L5
**场景**: 重组代码结构、提取模块、跨代码库重命名
**工作流**: 创建 task → prd.md → grill-me → design.md → implement.md → before-dev → implement（worktree）→ check → spec-review + code-review + architecture-review → Finish 确认 → update-spec → commit → merge-review → validate → finish
**产物**: `prd.md`、`design.md`、`implement.md`
**门禁**: 所有适用门禁 + merge-review
**执行方式**: Subagent + worktree（L4），Trellis-native parallel + worktree（L5 默认），OMC 仅在显式批准后使用

---

### 8. [多 Agent Parent/Child 任务](./08-multi-agent-parent-child-task.md)

**级别**: L5
**场景**: 包含多个可独立验证交付物的大型功能
**工作流**: 创建 parent task → prd.md（含子任务映射）→ grill-me → design.md → implement.md → 创建 child tasks → 并行实现各 child → 各自 check → 各自 review → parent merge-review → Finish 确认 → validate → finish
**产物**: Parent：`prd.md`、`design.md`、`implement.md`、child 映射。Children：各自的 `prd.md`、`implement.md`
**门禁**: 全部门禁 + merge-review（强制）
**执行方式**: Trellis-native parallel + worktree + parent/child 默认；OMC 仅在显式批准后使用

---

## 速查表

| 场景 | 级别 | PRD | Design | Implement | Check | Spec Review | Code Review | Arch Review | Merge Review |
|------|------|:---:|:------:|:---------:|:-----:|:-----------:|:-----------:|:-----------:|:------------:|
| Typo 修改 | L1 | - | - | - | 轻量 | - | - | - | - |
| 简单 bugfix | L2 | ✓ | - | - | ✓ | - | - | - | - |
| 普通功能 | L3 | ✓ | 可选 | ✓ | ✓ | - | ✓ | - | - |
| 跨层 API | L4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| 前端组件 | L3 | ✓ | 可选 | ✓ | ✓ | - | ✓ | - | - |
| 后端持久化 | L4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| 重构 | L4/L5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 多 agent | L5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
