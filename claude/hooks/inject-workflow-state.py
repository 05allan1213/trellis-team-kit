#!/usr/bin/env python3
"""
Team-kit Inject Workflow State Hook

Parses workflow.md [workflow-state:STATUS] blocks and emits a short
breadcrumb on each user prompt. Resolves the active task and outputs
the matching workflow-state body.

Key behaviors:
- When status is 'planning', breadcrumb warns: Do NOT edit source code.
  Task creation approval is not implementation approval.
- When WAITING_IMPLEMENTATION_APPROVAL, explicitly forbids source editing,
  implementer spawn, and task.py start.
- When there is no active task, suggests an L0/L1/L2/L3+ route based on the
  current request so tiny edits can move faster without losing the escalation path.

Trigger: UserPromptSubmit
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    import io as _io
    for _stream_name in ("stdin", "stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        elif hasattr(_stream, "detach"):
            try:
                setattr(
                    sys, _stream_name,
                    _io.TextIOWrapper(_stream.detach(), encoding="utf-8", errors="replace"),
                )
            except Exception:
                pass


TRELLIS_DIR = ".trellis"

# Regex for [workflow-state:STATUS]...[/workflow-state:STATUS] blocks
_TAG_RE = re.compile(
    r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n(.*?)\n\s*\[/workflow-state:\1\]",
    re.DOTALL,
)

L0_QUESTION_HINTS = (
    "what", "why", "how", "explain", "介绍", "解释", "是什么", "怎么", "为什么",
)
L1_HINTS = (
    "typo", "copy", "wording", "label", "text", "文案", "错别字", "拼写", "注释",
    "提示语", "文本文字", "样式微调", "样式小改", "按钮文案", "rename label",
    "小修", "直接改", "no task", "skip trellis", "间距", "边距", "字号",
    "颜色", "圆角", "对齐", "占位符", "placeholder", "tooltip", "toast",
)
L1_REGEX_PATTERNS = (
    r"(按钮|卡片|弹窗|页面|表单|列表|表格).*(间距|边距|颜色|字号|字重|对齐|圆角|宽度|高度)",
    r"(间距|边距|颜色|字号|字重|对齐|圆角).*(调|改|微调|优化)",
    r"(调|改|微调|优化).*(间距|边距|颜色|字号|字重|对齐|圆角)",
    r"(文案|提示语|占位符|注释|按钮文字).*(改|调|优化)",
    r"(改|调|优化).*(文案|提示语|占位符|注释|按钮文字)",
)
L2_HINTS = (
    "util", "helper", "tool function", "utility", "validator", "format", "formatter",
    "date format", "工具函数", "辅助函数", "格式化函数", "日期格式化", "校验",
    "简单 bug", "small bug", "简单修复", "lightweight", "light bugfix", "脱敏函数",
    "解析函数", "转换函数", "映射函数",
)
L2_REGEX_PATTERNS = (
    r"(补|加|写|封装).*(工具函数|辅助函数|格式化函数|校验函数|解析函数|转换函数|映射函数)",
    r"(日期|时间|时间戳|手机号|邮箱|金额|脱敏).*(格式化|校验|转换|解析)",
)
L3_PLUS_HINTS = (
    "api", "schema", "migration", "auth", "authentication", "authorization",
    "frontend and backend", "cross-layer", "跨层", "接口", "数据库", "共享类型",
    "shared type", "重构", "refactor", "多模块", "worktree", "多 agent",
    "表结构", "数据表", "索引", "请求参数", "响应字段", "返回字段",
)
L3_REGEX_PATTERNS = (
    r"(接口|api).*(字段|参数|返回值|返回字段|响应字段|请求参数)",
    r"(数据表|表结构|[A-Za-z0-9_\u4e00-\u9fff]+表).*(加|新增|删除|修改|变更|迁移).*(字段|索引|列)",
    r"(新增|删除|修改|变更|迁移).*(数据表|表结构|[A-Za-z0-9_\u4e00-\u9fff]+表).*(字段|索引|列)",
    r"(权限|鉴权|认证|路由|中间件|schema|migration)",
)
CHANGE_HINTS = (
    "fix", "add", "change", "update", "implement", "refactor", "write", "wrap",
    "改", "修", "加", "新增", "实现", "重构", "删除", "调", "调整", "补", "写", "封装",
)


def _find_trellis_root(start: Path) -> Optional[Path]:
    """Walk up from start to find directory containing .trellis/."""
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / TRELLIS_DIR).is_dir():
            return cur
        cur = cur.parent
    return None


def _detect_platform(input_data: dict) -> Optional[str]:
    """Detect the AI platform from hook input or environment."""
    if isinstance(input_data.get("cursor_version"), str):
        return "cursor"
    env_map = {
        "CLAUDE_PROJECT_DIR": "claude",
        "CURSOR_PROJECT_DIR": "cursor",
        "CODEBUDDY_PROJECT_DIR": "codebuddy",
        "FACTORY_PROJECT_DIR": "droid",
        "GEMINI_PROJECT_DIR": "gemini",
        "QODER_PROJECT_DIR": "qoder",
        "KIRO_PROJECT_DIR": "kiro",
        "COPILOT_PROJECT_DIR": "copilot",
    }
    for env_name, platform in env_map.items():
        if os.environ.get(env_name):
            return platform
    script_parts = set(Path(sys.argv[0]).parts)
    if ".claude" in script_parts:
        return "claude"
    if ".cursor" in script_parts:
        return "cursor"
    if ".gemini" in script_parts:
        return "gemini"
    return None



def _extract_user_prompt(input_data: dict) -> str:
    """Return the current user request text when available."""
    for field in ("prompt", "message", "text", "content"):
        value = input_data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    nested = input_data.get("result")
    if isinstance(nested, dict):
        for field in ("prompt", "message", "text", "content"):
            value = nested.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _classify_no_task_prompt(prompt: str) -> str:
    """Classify a prompt into a suggested route when no active task exists."""
    if not prompt:
        return "generic"

    lowered = prompt.lower()
    has_change_hint = _contains_any(lowered, CHANGE_HINTS)

    if not has_change_hint and ("?" in prompt or _contains_any(lowered, L0_QUESTION_HINTS)):
        return "L0"

    if _contains_any(lowered, L3_PLUS_HINTS) or _matches_any(prompt, L3_REGEX_PATTERNS):
        return "L3+"

    if _contains_any(lowered, L2_HINTS) or _matches_any(prompt, L2_REGEX_PATTERNS):
        return "L2"

    if _contains_any(lowered, L1_HINTS) or _matches_any(prompt, L1_REGEX_PATTERNS):
        return "L1"

    if has_change_hint:
        return "L2"

    return "generic"


def _build_no_task_body(input_data: dict) -> str:
    """Build recommendation text for turns without an active task."""
    prompt = _extract_user_prompt(input_data)
    route = _classify_no_task_prompt(prompt)

    if route == "L0":
        return (
            "No active task.\n"
            "Suggested route: L0 discussion.\n"
            "Recommended next step: answer directly. No task is needed unless the request "
            "turns into a repository change."
        )

    if route == "L1":
        return (
            "No active task.\n"
            "Suggested route: L1 tiny inline edit.\n"
            "Recommended next step: direct inline edit without creating a task.\n"
            "If the scope expands, touches shared/high-risk files, or the user wants "
            "traceability, switch to a standard Trellis task."
        )

    if route == "L2":
        return (
            "No active task.\n"
            "Suggested route: L2 lightweight task.\n"
            "Recommended next step: ask for task-creation consent and keep planning light "
            "(prd.md + grill-me + implement.md + trellis-check).\n"
            "Task creation approval is NOT implementation approval."
        )

    if route == "L3+":
        return (
            "No active task.\n"
            "Suggested route: L3+ standard task.\n"
            "Recommended next step: ask for task-creation consent, create a Trellis task, "
            "and plan fully before implementation (PRD, design if needed, implement plan, "
            "review gates).\n"
            "Task creation approval is NOT implementation approval."
        )

    return (
        "No active task. First classify the current turn: "
        "L0 (pure Q&A) -> answer directly. "
        "L1 (typo/tiny edit) -> recommend direct inline edit. "
        "L2 (light implementation) -> recommend a light task path. "
        "L3-L5 (broader implementation) -> ask for task-creation consent. "
        "Task creation approval is NOT implementation approval."
    )


def _resolve_active_task(root: Path, input_data: dict) -> Optional[tuple[str, str, str]]:
    """Return (task_id, status, source) from the current active task."""
    scripts_dir = root / TRELLIS_DIR / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]
        active = resolve_active_task(root, input_data, platform=_detect_platform(input_data))
        if not active.task_path:
            return None
    except Exception:
        # Fallback: read .trellis/active-task
        active_file = root / TRELLIS_DIR / "active-task"
        if active_file.is_file():
            try:
                ref = active_file.read_text(encoding="utf-8").strip()
                if ref:
                    task_dir = root / ref if not Path(ref).is_absolute() else Path(ref)
                    task_json = task_dir / "task.json"
                    if task_json.is_file():
                        try:
                            data = json.loads(task_json.read_text(encoding="utf-8"))
                            task_id = data.get("id") or task_dir.name
                            status = data.get("status", "")
                            if isinstance(status, str) and status:
                                # Return the full relative path so callers can resolve task_dir
                                try:
                                    rel_path = str(task_dir.relative_to(root))
                                except ValueError:
                                    rel_path = str(task_dir)
                                return rel_path, status, "active-task-file"
                        except (json.JSONDecodeError, OSError):
                            pass
            except OSError:
                pass
        return None

    task_dir = Path(active.task_path)
    if not task_dir.is_absolute():
        task_dir = root / task_dir
    if active.stale:
        try:
            rel_path = str(task_dir.relative_to(root))
        except ValueError:
            rel_path = str(task_dir)
        return rel_path, f"stale_{active.source_type}", active.source

    task_json = task_dir / "task.json"
    if not task_json.is_file():
        return None
    try:
        data = json.loads(task_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    task_id = data.get("id") or task_dir.name
    status = data.get("status", "")
    if not isinstance(status, str) or not status:
        return None
    # Return the full relative path so callers can resolve task_dir correctly
    try:
        rel_path = str(task_dir.relative_to(root))
    except ValueError:
        rel_path = str(task_dir)
    return rel_path, status, active.source


def _load_breadcrumbs(root: Path) -> dict[str, str]:
    """Parse workflow.md for [workflow-state:STATUS] blocks.

    Returns {status: body_text}. workflow.md is the single source of truth.
    Missing tags or unreadable file returns empty dict.
    """
    workflow = root / TRELLIS_DIR / "workflow.md"
    if not workflow.is_file():
        return {}
    try:
        content = workflow.read_text(encoding="utf-8")
    except OSError:
        return {}

    result: dict[str, str] = {}
    for match in _TAG_RE.finditer(content):
        status = match.group(1)
        body = match.group(2).strip()
        if body:
            result[status] = body
    return result


def _map_status_to_breadcrumb_key(status: str) -> str:
    """Map task.json status to the workflow-state tag key.

    The workflow.md uses these tag keys:
    - no_task        -> NO_TASK state
    - planning       -> Phase 1 (status='planning')
    - waiting_approval -> WAITING_IMPLEMENTATION_APPROVAL
    - in_progress    -> Phase 2 + Phase 3 (status='in_progress')
    - reviewing      -> REVIEWING
    - finishing      -> FINISHING
    """
    mapping = {
        "planning": "planning",
        "in_progress": "in_progress",
        "completed": "finishing",
        "done": "finishing",
    }
    return mapping.get(status, status)


def _resolve_breadcrumb_key(status: str, task_dir: Path) -> str:
    """Resolve the exact breadcrumb key based on status and artifact presence.

    For 'planning' status, checks artifacts to determine sub-phase:
    - No prd.md -> planning (PLANNING_PRD)
    - prd.md exists but no implement.md -> planning
    - implement.md exists -> waiting_approval
    """
    if status == "planning":
        has_implement = (task_dir / "implement.md").is_file()
        if has_implement:
            return "waiting_approval"
        return "planning"
    return _map_status_to_breadcrumb_key(status)


def _infer_sub_phase(status: str, task_dir: Path) -> Optional[str]:
    """Infer the precise workflow sub-phase from task state + artifacts.

    Returns a human-readable sub-phase string, or None if no inference needed.
    This supplements the breadcrumb when the breadcrumb may be stale.
    """
    if status == "planning":
        has_prd = (task_dir / "prd.md").is_file()
        has_grill = (task_dir / "research" / "grill-me.md").is_file()
        has_design = (task_dir / "design.md").is_file()
        has_implement = (task_dir / "implement.md").is_file()

        if has_implement:
            return "WAITING_IMPLEMENTATION_APPROVAL"
        if has_design:
            return "PLANNING_IMPLEMENT"
        if has_grill:
            return "PLANNING_DESIGN"
        if has_prd:
            return "PLANNING_GRILL"
        return "PLANNING_PRD"

    if status == "in_progress":
        has_before_dev = (task_dir / "before-dev.md").is_file()
        has_check = (task_dir / "validation" / "check-results.md").is_file()
        has_review = (task_dir / "review").is_dir() and any(
            (task_dir / "review").iterdir()
        )
        has_finish = (task_dir / "finish.md").is_file()

        if has_finish:
            return "FINISHING"
        if has_review:
            return "REVIEWING"
        if has_check:
            return "UPDATING_SPEC"
        if has_before_dev:
            return "IMPLEMENTING"
        return "BEFORE_DEV"

    return None


def _build_skill_recommendation(sub_phase: Optional[str], status: str) -> str:
    """Build a skill recommendation line based on the inferred sub-phase."""
    recommendations = {
        "PLANNING_PRD": "Next skill: trellis-brainstorm",
        "PLANNING_GRILL": "Next skill: trellis-grill-me",
        "PLANNING_DESIGN": "Next skill: trellis-improve-codebase-architecture (guidance mode)",
        "PLANNING_IMPLEMENT": "Next skill: trellis-dev-strategy",
        "WAITING_IMPLEMENTATION_APPROVAL": "WAIT for user to approve implementation",
        "BEFORE_DEV": "Next skill: trellis-before-dev (MANDATORY before editing source)",
        "IMPLEMENTING": "Next skill: trellis-implement (dispatch trellis-implementer)",
        "CHECKING": "Next skill: trellis-check (dispatch trellis-checker)",
        "REVIEWING": "Next skill: run selected review gates from contract",
        "UPDATING_SPEC": "Next skill: trellis-update-spec",
        "FINISHING": "Next skill: trellis-finish-work (/trellis:finish-work)",
    }
    if sub_phase and sub_phase in recommendations:
        return recommendations[sub_phase]
    return ""


def _enforce_consent_warnings(breadcrumb_key: str, body: str) -> str:
    """Inject dual consent enforcement warnings into the breadcrumb body.

    For 'planning' status: ensure "Do NOT edit source code" and
    "Task creation approval is not implementation approval" are present.
    For 'waiting_approval': ensure explicit prohibition of source editing,
    implementer spawn, and task.py start.
    """
    if breadcrumb_key == "planning":
        consent_line = (
            "CONSENT ENFORCEMENT: Do NOT edit source code. "
            "Task creation approval is NOT implementation approval."
        )
        if consent_line not in body:
            body = consent_line + "\n" + body
    elif breadcrumb_key == "waiting_approval":
        approval_line = (
            "CONSENT ENFORCEMENT: Do NOT edit source code. "
            "Do NOT spawn implementer. Do NOT run task.py start. "
            "WAIT for user to explicitly approve implementation."
        )
        if approval_line not in body:
            body = approval_line + "\n" + body
    return body


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    cwd_str = data.get("cwd") or os.getcwd()
    cwd = Path(cwd_str)

    root = _find_trellis_root(cwd)
    if root is None:
        return 0  # Not a Trellis project

    templates = _load_breadcrumbs(root)
    task = _resolve_active_task(root, data)

    if task is None:
        # No active task
        body = templates.get("no_task") or _build_no_task_body(data)
        breadcrumb = f"<workflow-state>\nStatus: no_task\n{body}\n</workflow-state>"
    else:
        task_path, status, source = task
        task_dir = root / task_path if not Path(task_path).is_absolute() else Path(task_path)
        task_id = task_dir.name
        breadcrumb_key = _resolve_breadcrumb_key(status, task_dir)
        body = templates.get(breadcrumb_key)
        if body is None:
            body = templates.get(status, "Refer to workflow.md for current step.")
        body = _enforce_consent_warnings(breadcrumb_key, body)

        sub_phase = _infer_sub_phase(status, task_dir)
        skill_rec = _build_skill_recommendation(sub_phase, status)

        header = f"Task: {task_id} ({status})"
        if sub_phase:
            header += f"\nInferred phase: {sub_phase}"
        if skill_rec:
            header += f"\n{skill_rec}"

        breadcrumb = f"<workflow-state>\n{header}\n{body}\n</workflow-state>"

    platform = _detect_platform(data)
    hook_event_name = "BeforeAgent" if platform == "gemini" else "UserPromptSubmit"

    output = {
        "hookSpecificOutput": {
            "hookEventName": hook_event_name,
            "additionalContext": breadcrumb,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
