# Trellis 配置

Trellis 的默认配置文件，安装到目标项目的 `.trellis/` 目录。

## 文件

- `config.json` — Team-kit 默认 Trellis 配置
- `routing_rules.json` — Team-kit 默认路由规则配置

## routing_rules.json

路由规则配置文件，用于 prompt 路由判定（L0/L1/L2/L3+/UNCERTAIN）。

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
| `levels`         | object | 各级别规则（L1/L2/L3+）                       |
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
