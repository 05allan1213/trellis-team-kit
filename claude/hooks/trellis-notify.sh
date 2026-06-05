#!/usr/bin/env bash
# trellis-notify.sh — Desktop notifications for Claude Code hooks.
# Supports macOS and Ubuntu/Linux.
# This script must never block or fail Claude Code.

set -uo pipefail

# Allow per-user opt-out:
#   TRELLIS_NOTIFY=0 claude
#   TRELLIS_NOTIFY_SOUND=0 claude
#   TRELLIS_NOTIFY_DESKTOP=0 claude
#   TRELLIS_NOTIFY_STOP=0 claude
#   TRELLIS_NOTIFY_NOTIFICATION=0 claude
#   TRELLIS_NOTIFY_IN_AUTO=1 claude
#   TRELLIS_NOTIFY_WHEN_OMC_ACTIVE=1 claude
#   TRELLIS_NOTIFY_IDLE=1 claude
#   TRELLIS_NOTIFY_BLOCKED_RETRY_THRESHOLD=3 claude
if [ "${TRELLIS_NOTIFY:-1}" = "0" ]; then
  exit 0
fi

EVENT="${1:-info}"
TITLE="${2:-Claude Code}"
MESSAGE="${3:-需要你的处理}"

HOOK_INPUT=""
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

TITLE="$TITLE · $PROJECT_NAME"

DESKTOP_ENABLED="${TRELLIS_NOTIFY_DESKTOP:-1}"
SOUND_ENABLED="${TRELLIS_NOTIFY_SOUND:-1}"
STOP_ENABLED="${TRELLIS_NOTIFY_STOP:-1}"
NOTIFICATION_ENABLED="${TRELLIS_NOTIFY_NOTIFICATION:-1}"
NOTIFY_IN_AUTO="${TRELLIS_NOTIFY_IN_AUTO:-0}"
NOTIFY_WHEN_OMC_ACTIVE="${TRELLIS_NOTIFY_WHEN_OMC_ACTIVE:-0}"
NOTIFY_IDLE="${TRELLIS_NOTIFY_IDLE:-0}"
BLOCKED_RETRY_THRESHOLD="${TRELLIS_NOTIFY_BLOCKED_RETRY_THRESHOLD:-3}"

if [ ! -t 0 ]; then
  HOOK_INPUT="$(cat 2>/dev/null || true)"
fi

escape_applescript() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

macos_sound_file() {
  case "$EVENT" in
    attention|notification|need_input) echo "/System/Library/Sounds/Ping.aiff" ;;
    done|stop|success) echo "/System/Library/Sounds/Glass.aiff" ;;
    error|fail) echo "/System/Library/Sounds/Basso.aiff" ;;
    *) echo "/System/Library/Sounds/Glass.aiff" ;;
  esac
}

linux_sound_file() {
  case "$EVENT" in
    attention|notification|need_input) echo "/usr/share/sounds/freedesktop/stereo/message.oga" ;;
    done|stop|success) echo "/usr/share/sounds/freedesktop/stereo/complete.oga" ;;
    error|fail) echo "/usr/share/sounds/freedesktop/stereo/dialog-error.oga" ;;
    *) echo "/usr/share/sounds/freedesktop/stereo/complete.oga" ;;
  esac
}

omc_mode_active() {
  local state_dir="$PROJECT_DIR/.omc/state"
  if [ ! -d "$state_dir" ] || ! command -v python3 >/dev/null 2>&1; then
    return 1
  fi

  python3 - "$state_dir" <<'PY' >/dev/null 2>&1
import json
import sys
from pathlib import Path

state_dir = Path(sys.argv[1])
active_files = {
    "autopilot-state.json",
    "pipeline-state.json",
    "ralph-state.json",
    "team-state.json",
    "ultraqa-state.json",
    "ultrawork-state.json",
}
terminal = {"all-done", "cancelled", "complete", "completed", "done", "failed"}

for path in state_dir.rglob("*-state.json"):
    if path.name not in active_files:
        continue
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        continue
    if data.get("active") is not True:
        continue
    phase = str(data.get("phase") or data.get("current_phase") or data.get("status") or "").lower()
    if phase in terminal:
        continue
    raise SystemExit(0)

raise SystemExit(1)
PY
}

resolve_notification_decision() {
  SHOULD_NOTIFY=1

  if ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi

  local omc_active="0"
  if omc_mode_active; then
    omc_active="1"
  fi

  local resolved
  resolved="$(
    TRELLIS_EVENT="$EVENT" \
    TRELLIS_DEFAULT_MESSAGE="$MESSAGE" \
    TRELLIS_PROJECT_DIR="$PROJECT_DIR" \
    TRELLIS_STOP_ENABLED="$STOP_ENABLED" \
    TRELLIS_NOTIFICATION_ENABLED="$NOTIFICATION_ENABLED" \
    TRELLIS_NOTIFY_IN_AUTO="$NOTIFY_IN_AUTO" \
    TRELLIS_NOTIFY_WHEN_OMC_ACTIVE="$NOTIFY_WHEN_OMC_ACTIVE" \
    TRELLIS_NOTIFY_IDLE="$NOTIFY_IDLE" \
    TRELLIS_OMC_ACTIVE="$omc_active" \
    TRELLIS_BLOCKED_RETRY_THRESHOLD="$BLOCKED_RETRY_THRESHOLD" \
    HOOK_INPUT_JSON="$HOOK_INPUT" \
    python3 - <<'PY'
import hashlib
import json
import os
import re
import shlex
from pathlib import Path


DONE_RE = re.compile(
    r"(?:\b(?:done|finished|completed|all set|ready for review|ready to review|wrapped up|resolved)\b|"
    r"(?:已|已经)?完成(?:了)?|任务完成|处理完成|修复完成|可以回来看结果|可以来看结果|全部完成)",
    re.IGNORECASE,
)
BLOCKED_RE = re.compile(
    r"(?:\b(?:blocked|stuck|cannot continue|can't continue|unable to continue|need your help|need you to|"
    r"requires your input|waiting for you|missing credentials|missing api key)\b|"
    r"无法继续|不能继续|没法继续|卡住了|被阻塞|需要你(?:提供|确认|处理|决定|介入)|"
    r"需要用户(?:提供|确认|处理|决定)|等待你(?:提供|确认|处理|决定))",
    re.IGNORECASE,
)


def env_flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default) == "1"


def load_payload() -> dict:
    raw = os.environ.get("HOOK_INPUT_JSON", "")
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def search(obj, keys):
    if isinstance(obj, dict):
        for key in keys:
            value = obj.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, int):
                return str(value)
        for value in obj.values():
            found = search(value, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = search(value, keys)
            if found:
                return found
    return ""


def first_non_empty(*values: str) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def assistant_text(data: dict) -> str:
    top_level = (
        "last_assistant_message",
        "message",
        "text",
        "content",
        "output",
        "transcript",
    )
    nested = (
        "last_assistant_message",
        "message",
        "text",
        "content",
        "output",
    )

    for key in top_level:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_text(value)

    result = data.get("result")
    if isinstance(result, str) and result.strip():
        return normalize_text(result)
    if isinstance(result, dict):
        for key in nested:
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return normalize_text(value)

    return ""


def active_task_ref(project_dir: Path) -> str:
    active_file = project_dir / ".trellis" / "active-task"
    if not active_file.is_file():
        return ""
    try:
        return normalize_text(active_file.read_text(encoding="utf-8").strip())
    except OSError:
        return ""


def load_state(state_path: Path) -> dict:
    if not state_path.is_file():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state_path: Path, state: dict) -> None:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def fingerprint(*parts: str) -> str:
    digest = hashlib.sha1()
    for part in parts:
        digest.update(part.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return digest.hexdigest()


def set_last_state(state: dict, kind: str, current_fingerprint: str) -> None:
    state["last_kind"] = kind
    state["last_fingerprint"] = current_fingerprint


def clear_blocked_state(state: dict) -> None:
    state["blocked"] = {}


def update_blocked_state(state: dict, current_fingerprint: str) -> tuple[int, bool]:
    blocked = state.get("blocked")
    if not isinstance(blocked, dict):
        blocked = {}

    if blocked.get("fingerprint") == current_fingerprint:
        count = int(blocked.get("count", 0)) + 1
        notified = bool(blocked.get("notified", False))
    else:
        count = 1
        notified = False

    state["blocked"] = {
        "fingerprint": current_fingerprint,
        "count": count,
        "notified": notified,
    }
    return count, notified


def action_required_message(notification_type: str, tool_name: str, default_message: str) -> str:
    if notification_type == "permission_prompt":
        if tool_name:
            return f"需要授权执行 {tool_name}"
        return "需要授权后继续"
    if notification_type == "elicitation_dialog":
        return "需要回答问题后继续"
    return default_message or "需要你的处理"


def blocked_message(count: int) -> str:
    return f"连续失败 {count} 次，仍需你处理"


event = os.environ.get("TRELLIS_EVENT", "info")
default_message = os.environ.get("TRELLIS_DEFAULT_MESSAGE", "")
project_dir = Path(os.environ.get("TRELLIS_PROJECT_DIR", "."))
state_path = project_dir / ".omc" / "state" / "trellis-notify-state.json"
threshold_raw = os.environ.get("TRELLIS_BLOCKED_RETRY_THRESHOLD", "3")

try:
    blocked_threshold = max(1, int(threshold_raw))
except ValueError:
    blocked_threshold = 3

data = load_payload()
permission_mode = search(data, ("permission_mode", "permissionMode"))
notification_type = search(data, ("notification_type", "notificationType"))
tool_name = search(data, ("tool_name", "toolName"))
message_text = assistant_text(data)
context_key = first_non_empty(
    active_task_ref(project_dir),
    search(data, ("session_id", "sessionId", "conversation_id", "conversationId", "transcript_path", "transcriptPath", "request_id", "requestId")),
    project_dir.name,
)

state = load_state(state_path)
notify = True
output_event = event
output_message = default_message
should_save = False

if event in {"attention", "notification", "need_input"}:
    if os.environ.get("TRELLIS_NOTIFICATION_ENABLED", "1") == "0":
        notify = False
    elif not env_flag("TRELLIS_NOTIFY_IDLE") and notification_type == "idle_prompt":
        notify = False
    else:
        output_event = "attention"
        output_message = action_required_message(notification_type, tool_name, default_message)
        current_fingerprint = fingerprint("action_required", context_key, notification_type, tool_name, output_message)
        if state.get("last_kind") == "action_required" and state.get("last_fingerprint") == current_fingerprint:
            notify = False
        else:
            set_last_state(state, "action_required", current_fingerprint)
            clear_blocked_state(state)
            should_save = True
elif event in {"done", "stop", "success"}:
    if os.environ.get("TRELLIS_STOP_ENABLED", "1") == "0":
        notify = False
    elif not env_flag("TRELLIS_NOTIFY_IN_AUTO") and permission_mode in {"auto", "acceptEdits", "bypassPermissions"}:
        notify = False
        clear_blocked_state(state)
        set_last_state(state, "suppressed", "")
        should_save = True
    elif not env_flag("TRELLIS_NOTIFY_WHEN_OMC_ACTIVE") and env_flag("TRELLIS_OMC_ACTIVE"):
        notify = False
        clear_blocked_state(state)
        set_last_state(state, "suppressed", "")
        should_save = True
    else:
        if message_text and BLOCKED_RE.search(message_text):
            current_fingerprint = fingerprint("blocked", context_key, message_text[:240])
            count, already_notified = update_blocked_state(state, current_fingerprint)
            set_last_state(state, "blocked_pending", current_fingerprint)
            should_save = True
            if count >= blocked_threshold and not already_notified:
                notify = True
                output_event = "error"
                output_message = blocked_message(count)
                state["blocked"]["notified"] = True
                set_last_state(state, "blocked", current_fingerprint)
            else:
                notify = False
        elif message_text and DONE_RE.search(message_text):
            current_fingerprint = fingerprint("complete", context_key, message_text[:240])
            clear_blocked_state(state)
            if state.get("last_kind") == "complete" and state.get("last_fingerprint") == current_fingerprint:
                notify = False
            else:
                notify = True
                output_event = "done"
                output_message = "主任务已完成，可回来看结果"
                set_last_state(state, "complete", current_fingerprint)
                should_save = True
        else:
            notify = False
            clear_blocked_state(state)
            set_last_state(state, "neutral", "")
            should_save = True

if should_save:
    save_state(state_path, state)

print(f"SHOULD_NOTIFY={1 if notify else 0}")
print(f"EVENT={shlex.quote(output_event)}")
print(f"MESSAGE={shlex.quote(output_message)}")
PY
  )" || return 0

  eval "$resolved"
  return 0
}

notify_macos() {
  if [ "$DESKTOP_ENABLED" = "1" ] && command -v osascript >/dev/null 2>&1; then
    local safe_title safe_message
    safe_title="$(escape_applescript "$TITLE")"
    safe_message="$(escape_applescript "$MESSAGE")"
    osascript -e "display notification \"$safe_message\" with title \"$safe_title\"" >/dev/null 2>&1 || true
  fi

  if [ "$SOUND_ENABLED" = "1" ] && command -v afplay >/dev/null 2>&1; then
    local sound
    sound="$(macos_sound_file)"
    [ -f "$sound" ] && afplay "$sound" >/dev/null 2>&1 &
  fi
}

notify_linux() {
  if [ "$DESKTOP_ENABLED" = "1" ] && command -v notify-send >/dev/null 2>&1; then
    notify-send "$TITLE" "$MESSAGE" >/dev/null 2>&1 || true
  fi

  if [ "$SOUND_ENABLED" = "1" ]; then
    local sound
    sound="$(linux_sound_file)"

    if command -v paplay >/dev/null 2>&1 && [ -f "$sound" ]; then
      paplay "$sound" >/dev/null 2>&1 &
    elif command -v canberra-gtk-play >/dev/null 2>&1; then
      case "$EVENT" in
        attention|notification|need_input) canberra-gtk-play -i message >/dev/null 2>&1 & ;;
        error|fail) canberra-gtk-play -i dialog-error >/dev/null 2>&1 & ;;
        *) canberra-gtk-play -i complete >/dev/null 2>&1 & ;;
      esac
    fi
  fi
}

main() {
  resolve_notification_decision
  if [ "${SHOULD_NOTIFY:-1}" != "1" ]; then
    exit 0
  fi

  case "$(uname -s)" in
    Darwin) notify_macos ;;
    Linux) notify_linux ;;
    *) exit 0 ;;
  esac
}

main || true
exit 0
