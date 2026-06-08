#!/usr/bin/env bash
# smoke-test-install.sh — Real end-to-end install smoke test for trellis-team-kit
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEV_NAME="${TTK_SMOKE_DEV_NAME:-smoke}"
MODE="all"

usage() {
  cat <<'EOF'
Usage: smoke-test-install.sh [--mode local|remote|all] [--developer-name <name>]

Runs a real install smoke test against:
  local  - bash bootstrap/init.sh <name>
  remote - simulated-remote path via TTK_INIT_RAW_BASE=file://... and bash <(cat bootstrap/init.sh) <name>
  all    - both modes (default)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --developer-name)
      DEV_NAME="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$MODE" in
  local|remote|all) ;;
  *)
    echo "Invalid mode: $MODE" >&2
    usage >&2
    exit 1
    ;;
esac

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[smoke] ERROR: required command not found: $1" >&2
    exit 1
  fi
}

require_cmd git
require_cmd python3
require_cmd trellis
require_cmd curl

RAW_BASE_URI="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().as_uri())' "$REPO_ROOT")"
run_python_no_bytecode() { PYTHONDONTWRITEBYTECODE=1 python3 -B "$@"; }

assert_file() {
  local path="$1"
  if [ ! -f "$path" ]; then
    echo "[smoke] ERROR: expected file missing: $path" >&2
    exit 1
  fi
}

assert_no_pycache() {
  local root="$1"
  if find "$root/.trellis/scripts" -type d -name '__pycache__' | grep -q .; then
    echo "[smoke] ERROR: unexpected __pycache__ under $root/.trellis/scripts" >&2
    find "$root/.trellis/scripts" -type d -name '__pycache__' >&2
    exit 1
  fi
}

run_case() {
  local case_mode="$1"
  local tmpdir project

  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' RETURN
  project="$tmpdir/project-$case_mode"
  mkdir -p "$project"

  echo "[smoke] =================================================="
  echo "[smoke] Mode: $case_mode"
  echo "[smoke] Project: $project"
  echo "[smoke] =================================================="

  git -C "$project" init >/dev/null

  if [ "$case_mode" = "local" ]; then
    (
      cd "$project"
      bash "$REPO_ROOT/bootstrap/init.sh" "$DEV_NAME" < /dev/null
    )
  else
    (
      cd "$project"
      TTK_INIT_RAW_BASE="$RAW_BASE_URI" bash <(cat "$REPO_ROOT/bootstrap/init.sh") "$DEV_NAME" < /dev/null
    )
  fi

  assert_file "$project/.trellis/.team-kit-version"
  assert_file "$project/.trellis/config/config.json"
  assert_file "$project/.trellis/config/workflow_profiles.json"
  assert_file "$project/.trellis/scripts/validate_scope_manifest.py"
  assert_file "$project/.trellis/scripts/validate_guardrail_overrides.py"
  assert_file "$project/.trellis/scripts/validate_agent_results.py"
  assert_file "$project/.claude/settings.json"
  assert_file "$project/.claude/settings.local.json"
  assert_file "$project/.trellis/workspace/$DEV_NAME/journal-1.md"
  assert_no_pycache "$project"

  (
    cd "$project"
    run_python_no_bytecode .trellis/scripts/validate_runtime_hardening.py >/dev/null
    bash "$REPO_ROOT/bootstrap/personalize-local.sh" "$DEV_NAME" >/dev/null
  )
  assert_file "$project/.trellis/workspace/$DEV_NAME/preferences.md"
  assert_no_pycache "$project"

  echo "[smoke] PASS: $case_mode install path"
  rm -rf "$tmpdir"
  trap - RETURN
}

if [ "$MODE" = "local" ] || [ "$MODE" = "all" ]; then
  run_case "local"
fi

if [ "$MODE" = "remote" ] || [ "$MODE" = "all" ]; then
  run_case "remote"
fi

echo "[smoke] All requested smoke tests passed."
