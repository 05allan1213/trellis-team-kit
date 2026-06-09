# Bugfix 示例：修复 Session Token 过期竞态条件

任务级别：L3

## 场景

用户反馈随机被踢出登录。调查发现一个竞态条件：
session token 的刷新和验证同时执行，导致刚刷新的 token
被过期的验证检查拒绝。

## prd.md

```markdown
# 修复 Session Token 过期竞态条件

## 问题
用户活跃使用期间被随机登出。刷新和验证操作存在竞态：
刷新更新了 token，但并发验证读取旧 token 并拒绝。

## 范围
- 修复 session token 刷新/验证的竞态条件
- 添加回归测试
- 无 UI 变更

## 验收标准
1. Session 刷新和验证使用锁防止并发执行
2. 现有 session 测试通过
3. 新测试可复现竞态条件并验证修复
4. 无性能退化（>1000 sessions/sec）

## 不在范围内
- Session 存储后端变更
- UI 登出流程变更
- Token 格式变更
```

## design.md

```markdown
# 设计：修复 Session Token 过期竞态条件

## 当前架构
SessionManager.refresh() 和 SessionManager.validate() 都在没有同步的情况下
读写 session token。高负载下，refresh() 更新 token 时 validate() 正用旧值检查。

## 方案
为每个 session ID 添加 asyncio.Lock。refresh() 和 validate() 在读写 token
之前先获取锁。锁存储在字典中，带 TTL 清理。

## 数据流
1. 请求到达 → 调用 validate()
2. validate() 获取 session 锁
3. 从存储读取 token
4. 如已过期，调用 refresh()（同样获取锁 → 阻塞等待）
5. 验证完成后释放锁

## 回滚方案
移除锁，恢复之前行为。零数据迁移。
```

## implement.md

```markdown
# 实现计划：修复 Session Token 过期竞态条件

## 任务级别
- [x] L3 复杂任务

## 开发策略
- 模式：subagent
- 分支：fix/session-race-condition

## 有序步骤
1. 给 SessionManager 添加 asyncio.Lock 字典
2. 在 refresh() 中添加锁获取/释放
3. 在 validate() 中添加锁获取/释放
4. 添加过期 session 的锁清理
5. 编写并发 refresh/validate 回归测试
6. 运行完整测试套件

## Review Gate Contract
Contract version: team-kit

### Required gates (always run)
- [x] trellis-check

### Selected gates for this task
- [x] trellis-code-review

Selection rationale: L3 任务需要 code-review。

## Implementation Approval

Approval status:
- [x] approved

Approval source:
- user message: "继续开始实现"
- timestamp: 2026-06-09T00:00:00Z
- summary approved: 修复 session token 刷新/验证竞态

Allowed to run task.py start?
- [x] yes
- [ ] no
```

## validation/check-results.md

```markdown
# Check Results

Status: PASS

## Commands
- pytest tests/auth/test_session.py tests/auth/test_session_race.py：PASS
- python -m ruff check src/auth tests/auth：PASS

## Findings
阻塞问题：无

## Fixes Applied During Check
无
```

## review/code-review.md

```markdown
# 代码审查：修复 Session Token 过期竞态条件

## Verdict
- [x] PASS
- [ ] FAIL

审查范围：src/auth/session.py、tests/auth/test_session_race.py

阻塞问题：无

非阻塞问题：
- 可考虑将锁管理提取到独立的 SessionLockManager 类

风险级别：低
需要重新审查：否
```

## validation/test-results.md

```markdown
# Test Results: 修复 Session Token 过期竞态条件

## Build

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | python -m compileall src/auth |
| Build Time | 4s |
| Output | success |

## Test

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | pytest tests/auth/test_session.py tests/auth/test_session_race.py |
| Tests Run | 142 |
| Passed | 142 |
| Failed | 0 |
| Skipped | 0 |
| Coverage | 91% |
| Output | `test_concurrent_refresh_validate` passed |

## Smoke

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | manual login session refresh flow |
| Output | active session remained valid after concurrent refresh/validate |

## Ready for finish-work?

- [x] yes
- [ ] no

## Overall

- [x] PASS — build, regression tests, and smoke validation passed.
- [ ] FAIL — one or more validation steps failed.
```

## finish.md

```markdown
# Finish：修复 Session Token 过期竞态条件

## Finish Approval

Approval status:
- [x] approved

Approval source:
- user message: "进入 Finish 阶段"
- timestamp: 2026-06-09T00:00:00Z
- summary approved: 修复 session token 刷新/验证竞态并完成回归验证

Allowed to proceed with finish?
- [x] yes
- [ ] no

## Task Summary
修复 session token 刷新与验证并发竞态，为每个 session 加锁并补充并发回归测试。

## Observable Outcomes
- Outcome: 用户活跃使用期间不再因刷新/验证并发竞态被随机登出
- Evidence: `pytest tests/auth/test_session.py tests/auth/test_session_race.py` PASS，手动 session refresh smoke PASS
- Remaining gap / risk: none

## Changed Files

| File | Change |
|------|--------|
| `src/auth/session.py` | modified: added per-session lock around refresh/validate critical sections |
| `tests/auth/test_session_race.py` | created: concurrent refresh/validate regression coverage |

## Acceptance Criteria Coverage

| AC | Status | Evidence |
|----|--------|----------|
| AC1: refresh/validate cannot invalidate an active session by racing | PASS | `test_concurrent_refresh_validate` passed |
| AC2: expired session locks are cleaned up | PASS | unit coverage in `tests/auth/test_session.py` |
| AC3: performance remains above target | PASS | 1200 sessions/sec measured, target >1000 |

## Delivery Sync Check
- [x] README / user docs reviewed
- [x] Example commands / scripts reviewed
- [x] Public API paths / contracts reviewed
- [x] Implemented vs planned status reviewed

Files checked:
- README.md - 无需更新，登录 API 未变
- tests/auth/test_session_race.py - 新增回归测试覆盖 AC

## Guardrail Overrides
- [x] override ledger reviewed
- Ledger: runtime/guardrail-overrides.jsonl
- Decision: N/A - no overrides

## Spec Update Decision
- **Need update?**: no
- **Reason**: 现有 session spec 已涵盖线程安全；本次是具体实现修复
- **Updated files**: N/A

## Follow-ups
- 考虑提取 SessionLockManager 使职责更清晰（非阻塞）

## Risks
- None.
```
