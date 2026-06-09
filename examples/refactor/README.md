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
- **Branch strategy**: dedicated worktree at .trellis/worktrees/extract-validation-library/
- **Parent/child**: no
- **Architecture guidance**: yes - load trellis-improve-codebase-architecture guidance
- **Merge review needed**: yes

## Execution Mode Decision

Recommended mode:
- [ ] main session
- [ ] single Trellis subagent
- [ ] Trellis subagents
- [x] Trellis-native parallel + worktree
- [ ] OMC ulw/ultrawork + worktree + parent/child

Reason:
- L4 跨模块重构使用 Trellis-native worktree 隔离实现，并触发 merge-review。

Why not heavier:
- 不需要 parent/child 拆分或 OMC 高级并行编排。

OMC approval:
- [x] not applicable
- [ ] user explicitly approved OMC
- user message: N/A
- timestamp: N/A

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
Contract version: team-kit

### Required gates (always run)
- [x] trellis-check

### Selected gates for this task
- [x] trellis-spec-review
- [x] trellis-code-review
- [x] trellis-code-architecture-review
- [x] trellis-merge-review

Selection rationale: L4 worktree 重构需要 spec + code + architecture + merge-review。

## Implementation Approval

Approval status:
- [x] approved

Approval source:
- user message: "继续开始实现"
- timestamp: 2026-06-09T00:00:00Z
- summary approved: 提取共享验证库，迁移 6 个模块并完成架构/代码/spec review

Allowed to run task.py start?
- [x] yes
- [ ] no
```

## validation/check-results.md

```markdown
# Check Results

Status: PASS

## Commands
- pytest tests/auth tests/billing tests/user_profile tests/admin_api tests/onboarding tests/reporting：PASS
- python scripts/check_no_duplicate_validators.py：PASS

## Findings
阻塞问题：无

## Fixes Applied During Check
无
```

## review/architecture-review.md

```markdown
# 架构审查：提取共享验证库

## Verdict
- [x] PASS
- [ ] FAIL

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
# Test Results: 提取共享验证库

## Build

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | npm run build |
| Build Time | 22s |
| Output | success |

## Test

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | pytest tests/auth tests/billing tests/user_profile tests/admin_api tests/onboarding tests/reporting |
| Tests Run | 318 |
| Passed | 318 |
| Failed | 0 |
| Skipped | 0 |
| Coverage | 90% |
| Output | all 6 migrated modules and 45 shared validation tests passed |

## Smoke

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | python scripts/check_no_duplicate_validators.py |
| Output | no duplicate validator implementations found |

## Ready for finish-work?

- [x] yes
- [ ] no

## Overall

- [x] PASS — build, migrated module tests, shared validator tests, and duplicate scan passed.
- [ ] FAIL — one or more validation steps failed.
```

## finish.md

```markdown
# Finish：提取共享验证库

## Finish Approval

Approval status:
- [x] approved

Approval source:
- user message: "进入 Finish 阶段"
- timestamp: 2026-06-09T00:00:00Z
- summary approved: 提取共享验证库，迁移 6 个模块并完成架构/代码/spec review

Allowed to proceed with finish?
- [x] yes
- [ ] no

## Task Summary
提取 `@shared/validation` 共享验证库，迁移 6 个模块并删除重复验证实现。

## Observable Outcomes
- Outcome: `@shared/validation` 包存在，包含 6 个验证器
- Evidence: package export and shared validation unit tests PASS
- Remaining gap / risk: none
- Outcome: 全部 6 个模块已改为从共享验证库导入，重复验证逻辑已移除
- Evidence: migrated module tests PASS and duplicate validator scan PASS

## Changed Files

| File | Change |
|------|--------|
| `packages/shared/validation/*` | created: shared validators and package export |
| `src/auth/*` | modified: import shared validators |
| `src/billing/*` | modified: import shared validators |
| `src/user_profile/*` | modified: import shared validators |
| `src/admin_api/*` | modified: import shared validators |
| `src/onboarding/*` | modified: import shared validators |
| `src/reporting/*` | modified: import shared validators |
| `tests/shared/validation/*` | created: shared validator test coverage |

## Acceptance Criteria Coverage

| AC | Status | Evidence |
|----|--------|----------|
| AC1: shared validation package exposes all 6 validators | PASS | package export check and shared tests PASS |
| AC2: all target modules use shared validators | PASS | migrated module tests PASS |
| AC3: duplicate validator implementations are removed | PASS | `python scripts/check_no_duplicate_validators.py` PASS |
| AC4: existing behavior remains compatible | PASS | existing module tests passed unchanged |

## Delivery Sync Check
- [x] README / user docs reviewed
- [x] Example commands / scripts reviewed
- [x] Public API paths / contracts reviewed
- [x] Implemented vs planned status reviewed

Files checked:
- README.md - 补充共享验证库使用方式
- docs/shared/validation.md - 补充 API 和迁移指南
- package exports - 确认 `@shared/validation` 公开入口

## Guardrail Overrides
- [x] override ledger reviewed
- Ledger: runtime/guardrail-overrides.jsonl
- Decision: N/A - no overrides

## Spec Update Decision
- **Need update?**: yes
- **Reason**: 共享验证包 API 和未来模块迁移指南可复用
- **Updated files**: `.trellis/spec/shared/validation.md`

## Follow-ups
- None.

## Risks
- Shared package coupling risk; mitigated by architecture review and all migrated module tests.
```
