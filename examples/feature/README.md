# Feature 示例：添加双因素认证（TOTP）

任务级别：L3

## 场景

为登录流程添加基于 TOTP 的双因素认证。用户可在设置中启用 2FA，
启用后登录需要密码加 TOTP 验证码。

## prd.md

```markdown
# 添加双因素认证（TOTP）

## 问题
当前认证仅靠密码。为满足安全合规要求，需要使用 TOTP（基于时间的一次性密码）实现双因素认证。

## 范围
- 用户设置中的 TOTP 设置流程
- 登录时的 TOTP 验证
- 丢失认证器时的恢复码
- 后端：TOTP 密钥生成、验证、恢复码管理
- 前端：设置向导、登录流程修改

## 验收标准
1. 用户可从设置启用 2FA → 显示二维码 + 手动密钥
2. 用户必须验证 TOTP 码后才能激活 2FA
3. 启用 2FA 后登录需要密码之后输入 TOTP 码
4. 用户设置时获得 8 个恢复码
5. 恢复码可使用一次绕过 2FA
6. TOTP 尝试失败有频率限制（每分钟 5 次）
7. 未启用 2FA 的现有用户不受影响

## 不在范围内
- 短信/邮件 2FA
- 硬件安全密钥（WebAuthn）
- 强制 2FA 注册（管理员策略）
```

## design.md

```markdown
# 设计：添加双因素认证（TOTP）

## 当前架构
认证流程：POST /login → 验证密码 → 签发 session token

## 方案
带 2FA 的认证流程：
1. POST /login → 验证密码
   - 2FA 未启用：签发 session token（保持现有行为）
   - 2FA 已启用：签发临时 challenge token
2. POST /login/verify-2fa → 验证 TOTP + challenge token → 签发 session token

TOTP 设置：
1. GET /user/2fa/setup → 生成密钥，返回二维码 URI + 手动密钥
2. POST /user/2fa/verify → 验证 TOTP 码 → 激活 2FA，返回恢复码

## 数据流
- TOTP 密钥加密存储在用户记录中
- 恢复码以 bcrypt 哈希存储
- Challenge token 为短生命周期 JWT（5 分钟 TTL）
- 频率限制通过 Redis（key：`2fa_attempts:{user_id}`）

## 安全注意事项
- TOTP 密钥使用 AES-256-GCM 静态加密
- 恢复码只展示一次，以哈希存储
- Challenge token 仅可用于 2FA 验证
- 频率限制：每用户每分钟 5 次 TOTP 尝试
```

## implement.md

```markdown
# 实现计划：添加双因素认证（TOTP）

## 任务级别
- [x] L3 复杂任务

## 开发策略
- 模式：subagent
- 分支：feature/two-factor-auth

## 有序步骤
1. 添加 TOTP 密钥生成和加密（后端）
2. 添加 2FA 设置端点（GET /setup、POST /verify）
3. 登录时签发 challenge token（2FA 启用时）
4. 添加 2FA 验证端点（POST /login/verify-2fa）
5. 添加恢复码生成和验证
6. 添加 TOTP 尝试频率限制
7. 创建前端 2FA 设置向导组件
8. 修改登录表单支持 2FA 流程
9. 编写测试（单元 + 集成）

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
- summary approved: 添加 TOTP 2FA 设置、登录验证、恢复码和频率限制

Allowed to run task.py start?
- [x] yes
- [ ] no
```

## validation/check-results.md

```markdown
# Check Results

Status: PASS

## Commands
- pytest tests/auth tests/frontend/two_factor：PASS
- npm run typecheck：PASS
- npm run lint：PASS

## Findings
阻塞问题：无

## Fixes Applied During Check
无
```

## review/code-review.md

```markdown
# 代码审查：添加双因素认证（TOTP）

## Verdict
- [x] PASS
- [ ] FAIL

审查范围：src/auth/*、src/api/auth.py、src/frontend/TwoFactorSetup.tsx

阻塞问题：无

非阻塞问题：
- 恢复码展示可增加适合打印的格式
- 可考虑添加"一键复制全部恢复码"按钮

风险级别：中（涉及认证变更）
需要重新审查：否
```

## validation/test-results.md

```markdown
# Test Results: 添加双因素认证（TOTP）

## Build

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | npm run build |
| Build Time | 18s |
| Output | success |

## Test

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | pytest tests/auth tests/frontend/two_factor |
| Tests Run | 199 |
| Passed | 199 |
| Failed | 0 |
| Skipped | 0 |
| Coverage | 88% |
| Output | TOTP verification, recovery codes, and rate limiting passed |

## Smoke

- [x] pass
- [ ] fail

| Metric | Value |
|--------|-------|
| Command | manual 2FA enable/login/recovery-code flow |
| Output | setup wizard, TOTP challenge, and one-time recovery code flow passed |

## Ready for finish-work?

- [x] yes
- [ ] no

## Overall

- [x] PASS — build, auth tests, frontend tests, and smoke validation passed.
- [ ] FAIL — one or more validation steps failed.
```

## finish.md

```markdown
# Finish：添加双因素认证（TOTP）

## Finish Approval

Approval status:
- [x] approved

Approval source:
- user message: "进入 Finish 阶段"
- timestamp: 2026-06-09T00:00:00Z
- summary approved: 添加 TOTP 2FA 设置、登录验证、恢复码和频率限制

Allowed to proceed with finish?
- [x] yes
- [ ] no

## Task Summary
添加 TOTP 双因素认证，包括设置向导、登录挑战、恢复码和失败尝试频率限制。

## Observable Outcomes
- Outcome: 用户可在设置中启用 2FA 并看到二维码与手动密钥
- Evidence: manual 2FA setup smoke PASS
- Remaining gap / risk: none
- Outcome: 启用 2FA 后登录必须通过 TOTP 验证，恢复码可一次性绕过 2FA
- Evidence: `pytest tests/auth tests/frontend/two_factor` PASS

## Changed Files

| File | Change |
|------|--------|
| `src/auth/two_factor.py` | created: TOTP secret, verification, recovery-code support |
| `src/api/auth.py` | modified: added setup, verify, and recovery endpoints |
| `src/frontend/TwoFactorSetup.tsx` | created: setup wizard UI |
| `tests/auth/test_two_factor.py` | created: backend 2FA coverage |
| `tests/frontend/two_factor.test.tsx` | created: frontend 2FA flow coverage |

## Acceptance Criteria Coverage

| AC | Status | Evidence |
|----|--------|----------|
| AC1: user can enable 2FA with QR/manual key | PASS | setup smoke PASS |
| AC2: login requires valid TOTP after 2FA is enabled | PASS | auth integration tests PASS |
| AC3: recovery codes work once and then expire | PASS | recovery-code tests PASS |
| AC4: failed TOTP attempts are rate limited | PASS | rate-limit tests PASS |

## Delivery Sync Check
- [x] README / user docs reviewed
- [x] Example commands / scripts reviewed
- [x] Public API paths / contracts reviewed
- [x] Implemented vs planned status reviewed

Files checked:
- README.md - 补充 2FA 设置和登录流程
- docs/api/auth.md - 补充 setup、verify、recovery endpoints
- frontend login docs - 补充 challenge token 流程

## Guardrail Overrides
- [x] override ledger reviewed
- Ledger: runtime/guardrail-overrides.jsonl
- Decision: N/A - no overrides

## Spec Update Decision
- **Need update?**: yes
- **Reason**: 2FA 流程、频率限制和恢复码规则可复用
- **Updated files**: `.trellis/spec/backend/auth.md`

## Follow-ups
- 恢复码展示可增加适合打印的格式
- 可考虑添加"一键复制全部恢复码"按钮

## Risks
- Authentication flow changed; mitigated by auth integration tests and manual smoke validation.
```
