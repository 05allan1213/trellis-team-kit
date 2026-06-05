#!/usr/bin/env bash
# trellis-notify.sh — User-facing desktop notifications for Claude Code hooks.
# The script is intentionally quiet for workflow noise and only notifies when
# Claude is waiting on the user or a main turn has stayed idle briefly.

set -uo pipefail

if [ "${TRELLIS_NOTIFY:-1}" = "0" ]; then
  exit 0
fi

EVENT="${1:-info}"
BASE_TITLE="${2:-Claude Code}"
DEFAULT_MESSAGE="${3:-需要你的处理}"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
TITLE="$BASE_TITLE · $PROJECT_NAME"
MESSAGE="$DEFAULT_MESSAGE"

DESKTOP_ENABLED="${TRELLIS_NOTIFY_DESKTOP:-1}"
SOUND_ENABLED="${TRELLIS_NOTIFY_SOUND:-1}"
REMINDER_SECONDS="${TRELLIS_NOTIFY_REMINDER_SECONDS:-3 10 30 60 120}"
MAX_REMINDERS="${TRELLIS_NOTIFY_MAX_REMINDERS:-5}"

PAYLOAD="$(cat 2>/dev/null || true)"

escape_applescript() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

payload_query() {
  local mode="${1:-text}"
  local transcript_path="${2:-}"

  TRELLIS_NOTIFY_PAYLOAD="$PAYLOAD" python3 - "$mode" "$transcript_path" <<'PY'
import json
import os
import sys
from pathlib import Path

mode = sys.argv[1]
transcript_path = sys.argv[2] if len(sys.argv) > 2 else ""
raw = os.environ.get("TRELLIS_NOTIFY_PAYLOAD", "").strip()

try:
    data = json.loads(raw) if raw else {}
except (TypeError, ValueError):
    data = {}


def walk_strings(value):
    if isinstance(value, str):
        if value.strip():
            yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)


RELEVANT_KEYS = {
    "assistant_message",
    "content",
    "event",
    "hookEventName",
    "hook_event_name",
    "last_assistant_message",
    "message",
    "notification",
    "output",
    "reason",
    "result",
    "subtype",
    "text",
    "title",
    "type",
}


def walk_relevant_strings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in RELEVANT_KEYS:
                yield from walk_strings(child)
            elif isinstance(child, (dict, list)):
                yield from walk_relevant_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_relevant_strings(child)


def content_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := content_text(item)))
    if isinstance(value, dict):
        for key in ("text", "content", "message", "output", "result"):
            if key in value:
                text = content_text(value.get(key))
                if text:
                    return text
    return ""


def line_role(item):
    role = item.get("role") or item.get("type") or ""
    message = item.get("message")
    if isinstance(message, dict):
        role = message.get("role") or role
    return str(role).lower()


def line_text(item):
    for key in ("last_assistant_message", "message", "content", "text", "output", "result"):
        if key in item:
            text = content_text(item.get(key))
            if text:
                return text
    return content_text(item)


def transcript_items(path_text):
    if not path_text:
        return []
    path = Path(path_text)
    if not path.is_file():
        return []

    items = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                items.append(item)
    except OSError:
        return []
    return items


def last_assistant_text(path_text):
    for key in ("last_assistant_message", "assistant_message"):
        if key in data:
            text = content_text(data.get(key))
            if text:
                return text

    for item in reversed(transcript_items(path_text)):
        if line_role(item) == "assistant":
            text = line_text(item)
            if text:
                return text

    for key in ("message", "text", "content", "output", "result"):
        if key in data:
            text = content_text(data.get(key))
            if text:
                return text
    return ""


def user_count(path_text):
    count = 0
    for item in transcript_items(path_text):
        if line_role(item) == "user":
            count += 1
    return count


if mode == "event":
    print(data.get("hook_event_name") or data.get("hookEventName") or "")
elif mode == "transcript":
    print(data.get("transcript_path") or data.get("transcriptPath") or "")
elif mode == "text":
    print("\n".join(walk_relevant_strings(data)))
elif mode == "assistant":
    print(last_assistant_text(transcript_path))
elif mode == "user_count":
    print(user_count(transcript_path))
else:
    print("")
PY
}

lower_text() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

is_auto_mode_text() {
  local text
  text="$(lower_text "$1")"
  [[ "$text" =~ auto[[:space:]_-]*mode ]] && return 0
  [[ "$text" =~ auto[[:space:]_-]*accept ]] && return 0
  [[ "$text" =~ auto[[:space:]_-]*approval ]] && return 0
  return 1
}

is_subagent_completion_text() {
  local text
  text="$(lower_text "$1")"
  if [[ "$text" =~ sub[[:space:]_-]*agent|subagent|子[[:space:]]*agent|子代理 ]]; then
    [[ "$text" =~ complete|completed|finish|finished|done|stop|stopped|完成|结束|停止 ]] && return 0
  fi
  return 1
}

is_completion_noise_text() {
  local text
  text="$(lower_text "$1")"
  is_subagent_completion_text "$text" && return 0
  [[ "$text" =~ turn[[:space:]_-]*completed|task[[:space:]_-]*completed|conversation[[:space:]_-]*completed ]] && return 0
  [[ "$text" =~ 本轮已完成|任务已完成|已完成，等你继续 ]] && return 0
  return 1
}

is_waiting_text() {
  local text
  text="$(lower_text "$1")"
  [[ "$text" =~ permission|approval|approve|confirm|confirmation|authorize|authorise|allow ]] && return 0
  [[ "$text" =~ input|required|waiting[[:space:]]+for|needs?[[:space:]]+your|reply|respond|choose|select ]] && return 0
  [[ "$text" =~ blocked|stuck|proceed|continue ]] && return 0
  [[ "$text" =~ 需要你|需要用户|等待你|等你|请确认|确认|是否|要不要|允许|授权|批准|同意|回复|选择|继续|卡住|阻塞 ]] && return 0
  [[ "$text" == *"?"* || "$text" == *"？"* ]] && return 0
  return 1
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

emit_notification() {
  if [ "${TRELLIS_NOTIFY_DRY_RUN:-0}" = "1" ]; then
    printf 'notify\t%s\t%s\t%s\n' "$EVENT" "$TITLE" "$MESSAGE"
    return 0
  fi

  case "$(uname -s)" in
    Darwin) notify_macos ;;
    Linux) notify_linux ;;
    *) return 0 ;;
  esac
}

handle_notification_event() {
  local payload_text transcript_path start_user_count
  payload_text="$(payload_query text)"

  if [ -z "${payload_text//[[:space:]]/}" ]; then
    return 0
  fi

  is_auto_mode_text "$payload_text" && return 0
  is_completion_noise_text "$payload_text" && return 0

  if is_waiting_text "$payload_text"; then
    transcript_path="$(payload_query transcript)"
    start_user_count="$(payload_query user_count "$transcript_path")"
    if [ "${TRELLIS_NOTIFY_TEST_SYNC:-0}" = "1" ]; then
      schedule_reminders "$transcript_path" "$start_user_count" "$payload_text" "waiting"
    else
      (
        schedule_reminders "$transcript_path" "$start_user_count" "$payload_text" "waiting"
      ) >/dev/null 2>&1 &
    fi
  fi
}

user_replied_since_start() {
  local transcript_path="$1"
  local start_user_count="$2"

  local current_user_count
  current_user_count="$(payload_query user_count "$transcript_path")"
  if [[ "$current_user_count" =~ ^[0-9]+$ && "$start_user_count" =~ ^[0-9]+$ ]]; then
    if [ "$current_user_count" -gt "$start_user_count" ]; then
      return 0
    fi
  fi

  return 1
}

emit_context_reminder() {
  local transcript_path="$1"
  local context_text="$2"
  local reminder_kind="$3"

  local assistant_text
  assistant_text="$(payload_query assistant "$transcript_path")"
  context_text="$context_text
$assistant_text"

  is_auto_mode_text "$context_text" && return 0
  is_subagent_completion_text "$context_text" && return 0

  if [ "$reminder_kind" = "waiting" ] || is_waiting_text "$assistant_text"; then
    EVENT="attention"
    MESSAGE="Claude Code 正在等你确认"
  else
    EVENT="done"
    MESSAGE="Claude Code 已停下，等你继续"
  fi

  emit_notification
}

schedule_reminders() {
  local transcript_path="$1"
  local start_user_count="$2"
  local context_text="$3"
  local reminder_kind="$4"
  local previous_delay=0
  local reminder_count=0
  local delay sleep_for

  for delay in $REMINDER_SECONDS; do
    [[ "$delay" =~ ^[0-9]+$ ]] || continue
    [ "$delay" -le 120 ] || break
    [ "$reminder_count" -lt "$MAX_REMINDERS" ] || break

    sleep_for=$((delay - previous_delay))
    [ "$sleep_for" -gt 0 ] || sleep_for=0
    sleep "$sleep_for" || true
    previous_delay="$delay"

    if user_replied_since_start "$transcript_path" "$start_user_count"; then
      return 0
    fi

    emit_context_reminder "$transcript_path" "$context_text" "$reminder_kind"
    reminder_count=$((reminder_count + 1))
  done
}

handle_stop_event() {
  local transcript_path payload_text assistant_text context_text start_user_count

  transcript_path="$(payload_query transcript)"
  payload_text="$(payload_query text)"
  assistant_text="$(payload_query assistant "$transcript_path")"
  context_text="$payload_text
$assistant_text"

  is_auto_mode_text "$context_text" && return 0
  is_subagent_completion_text "$context_text" && return 0

  start_user_count="$(payload_query user_count "$transcript_path")"

  if [ "${TRELLIS_NOTIFY_TEST_SYNC:-0}" = "1" ]; then
    schedule_reminders "$transcript_path" "$start_user_count" "$context_text" "auto"
  else
    (
      schedule_reminders "$transcript_path" "$start_user_count" "$context_text" "auto"
    ) >/dev/null 2>&1 &
  fi
}

main() {
  case "$EVENT" in
    notification|attention|need_input)
      handle_notification_event
      ;;
    stop)
      handle_stop_event
      ;;
    *)
      emit_notification
      ;;
  esac
}

main || true
exit 0
