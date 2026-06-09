# Trellis Scripts

此目录保存 team-kit 安装到目标项目的 workflow runtime 脚本。

这些脚本负责路由回放、任务校验、scope manifest 校验、agent result 校验、guardrail override 审计、spec 更新候选检测、runtime hardening 和 `/trellis:doctor` 体检。

当前 team-kit 管理 20 个 `.trellis/scripts/*.py` workflow runtime 脚本。安装后还会把
`tests/fixtures/replay/` 的 22 个回放样本复制到目标项目的 `.trellis/replay/`，
因此目标项目可运行 `python3 .trellis/scripts/replay_workflow_cases.py .trellis/replay`。
在 team-kit 源码仓库内维护时，回放路径是 `tests/fixtures/replay`。

官方 Trellis 脚本（例如 `task.py`、`get_context.py`）仍由 `trellis init` 安装。Team-kit 不 fork 也不替换官方脚本，只安装额外的 `.trellis/scripts/*` workflow runtime。
