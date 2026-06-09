# 示例：重构（L4）

## 场景
将分散在 15 个文件中的重复日期格式化逻辑提取到一个共享工具模块中。

## 预期流程

1. AI 判断为 L4（跨文件重构，共享工具变更）
2. Task creation consent → `task.py create`
3. `trellis-brainstorm` → 搜索所有日期格式化调用点 → 分类不同模式
4. `trellis-grill-me` → 识别向后兼容、时区处理、格式字符串差异
5. `trellis-improve-codebase-architecture guidance` → 关于共享模块放置位置的 Architecture Guidance
6. AI 写 `design.md`：当前重复映射、提议的共享模块 API、迁移计划（逐个替换调用点）
7. `trellis-dev-strategy` → 决定：subagent + worktree（大型重构）、全部审查门禁
8. Implementation approval → `task.py start`
9. `trellis-before-dev` → 读取 .trellis/spec/ 相关规范
10. 派发 `trellis-implementer` → 创建共享模块，替换所有调用点
11. 派发 `trellis-checker` → 深度检查：所有调用点是否都替换了？行为有无变化？
12. 派发 `trellis-spec-reviewer`
13. 派发 `trellis-code-reviewer`
14. 派发 `trellis-architecture-reviewer`
15. 全部 PASS → AI 停下来等待用户明确说"进入 Finish 阶段"
16. 用户确认 Finish → AI 写 `finish.md` 的 Finish Approval，并运行 `trellis-update-spec` → 将共享工具模式沉淀到 .trellis/spec/
17. Commit → merge-review → validate（运行全部测试）→ `/trellis:finish-work`

## 预期产物
- 完整产物，design.md 映射所有调用点
- research/evidence.md，含调用点目录
- review/：spec、code、architecture、merge
- validation/test-results.md（完整测试套件）

## 关键行为
- 任务级别：L4
- design.md 映射所有受影响的调用点
- 深度检查验证无行为变化
- Finish 前运行完整测试套件
