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
- [x] trellis-check
- [x] trellis-code-review

选择理由：L3 任务需要 check + code-review。
```

## review/code-review.md

```markdown
# 代码审查：添加双因素认证（TOTP）

状态：
- [x] PASS

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
# 验证结果

## 构建结果
状态：PASS

## 测试结果
状态：PASS
- 单元测试：187 通过
- 集成测试：12 通过
- TOTP 验证：PASS
- 恢复码流程：PASS
- 频率限制：PASS
```

## final-summary.md

```markdown
# 最终摘要：添加双因素认证（TOTP）

## 结果
基于 TOTP 的 2FA 已添加。用户可在设置中启用 2FA，
启用后登录需要 TOTP 验证码。提供恢复码用于丢失认证器时访问。

## 提交
1. feat: 添加 TOTP 密钥生成和加密存储 (def2345)
2. feat: 添加 2FA 设置和验证端点 (ghi3456)
3. feat: 添加 2FA 登录流程及 challenge token (jkl4567)
4. feat: 添加恢复码生成和验证 (mno5678)
5. feat: 添加 2FA 设置向导和登录流程前端 (pqr6789)

## Review
- code-review：PASS（1 条非阻塞建议）

## 验证
- 构建：PASS
- 测试：PASS（199 个测试）

## Spec 更新
已更新 auth spec，记录 2FA 流程、频率限制和恢复码机制。
```
