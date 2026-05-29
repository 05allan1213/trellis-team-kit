# 重构示例：提取共享验证库

任务级别：L4（架构 / 跨层任务）

## 场景

验证逻辑在 6 个模块中重复：auth、billing、user-profile、
admin-api、onboarding、reporting。每个模块都有自己的 email 验证器、
phone 验证器、date-range 验证器等。需要提取为共享验证库，提供统一 API。

## prd.md

```markdown
# 提取共享验证库

## 问题
验证逻辑在 6 个模块中重复。当验证规则变更时（如 email RFC 合规更新），
需要改 6 个文件。不一致性已导致 bug：billing 接受的邮箱 auth 却拒绝。

## 范围
- 提取通用验证器：email、phone、date-range、URL、string-length、enum
- 创建 `@shared/validation` 包
- 迁移全部 6 个模块使用共享验证器
- 移除重复验证代码
- 确保 100% 向后兼容

## 验收标准
1. `@shared/validation` 包存在，含 6+ 个验证器
2. 全部 6 个模块从 `@shared/validation` 导入
3. 无残留重复验证逻辑
4. 所有现有测试无需修改即通过
5. 新验证测试覆盖边界情况
6. 所有模块无破坏性 API 变更

## 不在范围内
- 尚未重复的新验证规则
- 验证规则行为变更
- 异步验证框架
```

## design.md

```markdown
# 设计：提取共享验证库

## 当前架构
```
auth/validators.py     ← email、phone、password
billing/validators.py  ← email、phone、amount、date-range
user-profile/validators.py ← email、phone、URL、bio-length
admin-api/validators.py    ← email、date-range、enum
onboarding/validators.py   ← email、phone
reporting/validators.py    ← date-range、enum
```

## 方案
```
@shared/validation/
  __init__.py           ← 公开 API
  email.py              ← EmailValidator
  phone.py              ← PhoneValidator
  date_range.py         ← DateRangeValidator
  url.py                ← URLValidator
  string_length.py      ← StringLengthValidator
  enum_validator.py     ← EnumValidator
  base.py               ← BaseValidator

auth/validators.py      ← 从 @shared/validation 导入（password 保留）
billing/validators.py   ← 从 @shared/validation 导入（amount 保留）
...（所有模块从 shared 导入）
```

## 架构指导
- 单一职责：每个验证器文件只做一件事
- 开闭原则：验证器通过配置扩展，不通过继承
- 依赖规则：@shared/validation 不依赖任何东西；模块依赖它
- 接口隔离：每个模块只导入需要的验证器

## 迁移计划
1. 创建 @shared/validation，包含全部 6 个验证器
2. 逐个模块替换导入，验证测试通过
3. 移除旧重复代码
4. 每次模块迁移之间运行完整测试套件

## 回滚方案
每个模块迁移可独立回滚。如果某模块迁移出问题，回滚该模块，
共享包保留不动。
```

## implement.md

```markdown
# 实现计划：提取共享验证库

## 任务级别
- [x] L4 架构 / 跨层任务

## 开发策略
- 模式：subagent + worktree
- 分支：refactor/extract-validation-library

## 有序步骤
1. 创建 @shared/validation 包结构
2. 实现 BaseValidator 和 6 个验证器
3. 为共享验证器编写完整测试
4. 迁移 auth 模块（最简单，password 保留）
5. 迁移 onboarding 模块
6. 迁移 user-profile 模块
7. 迁移 billing 模块
8. 迁移 admin-api 模块
9. 迁移 reporting 模块
10. 移除重复验证代码
11. 运行完整测试套件

## Review Gate Contract
- [x] trellis-check
- [x] trellis-spec-review
- [x] trellis-code-review
- [x] trellis-code-architecture-review

选择理由：L4 跨层重构需要 spec + code + architecture review。
```

## review/architecture-review.md

```markdown
# 架构审查：提取共享验证库

状态：
- [x] PASS

依赖方向：所有模块 → @shared/validation。正确。
模块边界：每个验证器职责单一。清晰。
抽象层次：合适 — 可配置的验证器，不过度抽象。

阻塞问题：无
非阻塞问题：无
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
- 全部 6 个模块：测试通过
- 新共享验证测试：45 个测试通过
- 无需修改任何测试（向后兼容）
```

## final-summary.md

```markdown
# 最终摘要：提取共享验证库

## 结果
创建了 `@shared/validation` 包，含 6 个验证器。全部 6 个模块已迁移。
零重复验证逻辑残留。所有测试无需修改即通过。

## 提交
1. refactor: 创建 @shared/validation 包及 6 个验证器 (stu7890)
2. refactor: 迁移 auth 到共享验证 (vwx8901)
3. refactor: 迁移 onboarding 到共享验证 (yza9012)
4. refactor: 迁移 user-profile 到共享验证 (bcd0123)
5. refactor: 迁移 billing 到共享验证 (efg1234)
6. refactor: 迁移 admin-api 到共享验证 (hij2345)
7. refactor: 迁移 reporting 到共享验证 (klm3456)
8. refactor: 移除重复验证代码 (nop4567)

## Review
- spec-review：PASS
- code-review：PASS
- architecture-review：PASS

## 验证
- 构建：PASS
- 测试：PASS（全部 6 模块 + 45 个新验证测试）

## Spec 更新
新增 `.trellis/spec/shared/validation.md`，记录共享验证包
API 及未来模块迁移指南。
```
