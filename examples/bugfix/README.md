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
- [x] trellis-check
- [x] trellis-code-review
```

## review/code-review.md

```markdown
# 代码审查：修复 Session Token 过期竞态条件

状态：
- [x] PASS

审查范围：src/auth/session.py、tests/auth/test_session_race.py

阻塞问题：无

非阻塞问题：
- 可考虑将锁管理提取到独立的 SessionLockManager 类

风险级别：低
需要重新审查：否
```

## validation/test-results.md

```markdown
# 验证结果

## 构建结果
状态：PASS

## 测试结果
状态：PASS
- 单元测试：142 通过
- 新回归测试：test_concurrent_refresh_validate 通过
- 性能：1200 sessions/sec（>1000 目标）
```

## final-summary.md

```markdown
# 最终摘要：修复 Session Token 过期竞态条件

## 结果
竞态条件已修复。Session 刷新和验证现在使用 per-session 锁。

## 提交
1. fix: 添加 per-session 锁防止 token 刷新/验证竞态 (abc1234)

## Review
- code-review：PASS

## 验证
- 构建：PASS
- 测试：PASS（142 测试，含新回归测试）

## Spec 更新
无需更新 spec — 现有 session spec 已涵盖线程安全。

## 后续
- 考虑提取 SessionLockManager 使职责更清晰（非阻塞）
```
