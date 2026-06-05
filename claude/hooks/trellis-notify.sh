#!/usr/bin/env bash
# trellis-notify.sh — Desktop notifications for Claude Code hooks.
# Supports macOS and Ubuntu/Linux.
# This script must never block or fail Claude Code.

set -uo pipefail

# Allow per-user opt-out:
#   TRELLIS_NOTIFY=0 claude
#   TRELLIS_NOTIFY_SOUND=0 claude
#   TRELLIS_NOTIFY_DESKTOP=0 claude
if [ "${TRELLIS_NOTIFY:-1}" = "0" ]; then
  exit 0
fi

EVENT="${1:-info}"
TITLE="${2:-Claude Code}"
MESSAGE="${3:-需要你的处理}"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

TITLE="$TITLE · $PROJECT_NAME"

DESKTOP_ENABLED="${TRELLIS_NOTIFY_DESKTOP:-1}"
SOUND_ENABLED="${TRELLIS_NOTIFY_SOUND:-1}"

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
  case "$(uname -s)" in
    Darwin) notify_macos ;;
    Linux) notify_linux ;;
    *) exit 0 ;;
  esac
}

main || true
exit 0
