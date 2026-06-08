# Trellis 配置

Trellis 的默认配置文件，安装到目标项目的 `.trellis/` 目录。

## 文件

- `config.json` — Team-kit 默认 Trellis 配置
- `routing_rules.json` — Team-kit 默认路由规则配置
- `workflow_profiles.json` — Team-kit 默认 workflow profile 配置

## routing_rules.json

路由规则配置文件，用于 prompt 路由判定（L0/L1/L2/L3/L4/L5/UNCERTAIN）。

### 作用

- 作为 team-kit 的默认路由规则来源
- 被 `claude/hooks/lib/prompt_routing.py` 加载
- 被 `trellis/scripts/validate_routing_rules.py` 校验
- 支持 workspace 级覆写（放在 `.trellis/config/routing_rules.json`）

### 顶层结构

| 字段             | 类型   | 说明                                          |
|------------------|--------|-----------------------------------------------|
| `version`        | int    | 规则文件版本号                                |
| `intent_gate`    | object | 意图门控配置（区分问答 vs 变更请求）          |
| `levels`         | object | 各级别规则（L1/L2/L3/L4/L5）                 |
| `negative_rules` | array  | 负向规则（抑制特定等级）                      |
| `uncertainty`    | object | 不确定态阈值配置                              |

### 规则类型

每条规则有唯一 `id` 和 `type`，支持的类型：

- `keyword` — 单词匹配，需要 `terms` 字段
- `phrase` — 短语匹配，需要 `patterns` 字段
- `regex` — 正则匹配，需要 `patterns` 字段
- `pair` — 动作词+对象词匹配，需要 `verbs` + `objects`
- `triple` — 主体+动作词+对象词匹配，需要 `subjects` + `verbs` + `objects`

### 加载位置

运行时按以下顺序加载：

1. `<workspace-root>/.trellis/config/routing_rules.json`（覆写）
2. `trellis/config/routing_rules.json`（默认）

### 校验

```bash
# 校验默认规则
python3 trellis/scripts/validate_routing_rules.py

# 校验指定文件
python3 trellis/scripts/validate_routing_rules.py path/to/rules.json
```

校验项包括：JSON 合法性、顶层字段完整性、rule type 合法性、rule id 唯一性、必填字段非空、`apply_against` 引用合法等级。

## workflow_profiles.json

Workflow profile 配置文件，用于把任务等级映射到流程摩擦和门禁：

| Profile | Levels | 用途 |
|---------|--------|------|
| quick | L1 | 极小、局部、可逆改动 |
| light | L2 | 轻量实现 |
| standard | L3 | 普通 feature / bugfix |
| strict | L4 | API / schema / auth / infra / shared contract 等高风险任务 |
| orchestrated | L5 | 多 agent、parent-child、大重构或高级并行 |

OMC `ulw/ultrawork` 只属于高级执行选项，需要明确用户批准；默认多 agent 路径仍是 Trellis-native subagent / worktree / parallel。

## Scope / Override / Agent Result Validators

阶段二和阶段三新增三个 task-level 校验器：

- `validate_scope_manifest.py <task-dir>` — 校验 L2+ task 的 `scope-manifest.json`
- `validate_guardrail_overrides.py <task-dir>` — 校验 `runtime/guardrail-overrides.jsonl` 与 `finish.md` 复核状态
- `validate_agent_results.py <task-dir>` — 校验多 agent / worktree / OMC 任务的 `agent-results/*.json`
- `trellis_doctor.py workflow <task-dir>` — 汇总当前任务的 workflow alignment 并给出 `To fix:` 修复路径

`validate_task.py <task-dir>` 会在 before-dev 后联动 scope/override 校验，
并在需要 merge-review 的并行任务上联动 agent result 校验。全局
`validate_runtime_hardening.py` 只检查脚本可用性；实际 task 状态必须传入 task
目录单独验证。
