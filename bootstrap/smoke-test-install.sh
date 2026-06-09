#!/usr/bin/env bash
# smoke-test-install.sh — Real end-to-end install smoke test for trellis-team-kit
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEV_NAME="${TTK_SMOKE_DEV_NAME:-smoke}"
MODE="all"
TRUE_REMOTE_INIT_URL="${TTK_TRUE_REMOTE_INIT_URL:-https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh}"

usage() {
  cat <<'EOF'
Usage: smoke-test-install.sh [--mode local|remote|true-remote|all] [--developer-name <name>]

Runs a real install smoke test against:
  local       - bash bootstrap/init.sh <name>
  remote      - simulated-remote path via TTK_INIT_RAW_BASE=file://... and bash <(cat bootstrap/init.sh) <name>
  true-remote - local install plus published GitHub main raw install, then compare inventories
  all         - local + simulated-remote modes (default, no network dependency beyond local file://)

True remote URL:
  https://raw.githubusercontent.com/05allan1213/trellis-team-kit/main/bootstrap/init.sh
  Override with TTK_TRUE_REMOTE_INIT_URL to test another published branch or raw URL.
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
  local|remote|true-remote|all) ;;
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
SMOKE_TMP_ROOT=""
LOCAL_PROJECT=""
REMOTE_PROJECT=""
TRUE_REMOTE_PROJECT=""

assert_file() {
  local path="$1"
  if [ ! -f "$path" ]; then
    echo "[smoke] ERROR: expected file missing: $path" >&2
    exit 1
  fi
}

assert_team_specs_match() {
  local project="$1"
  local rel source_path installed_path

  while IFS= read -r rel || [ -n "$rel" ]; do
    [ -n "$rel" ] || continue
    source_path="$REPO_ROOT/marketplace/specs/web-app/$rel"
    installed_path="$project/.trellis/spec/$rel"
    assert_file "$installed_path"
    if ! cmp -s "$source_path" "$installed_path"; then
      echo "[smoke] ERROR: installed spec differs from team template: $rel" >&2
      exit 1
    fi
  done < "$REPO_ROOT/trellis/spec-manifest.txt"
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

  if [ -n "$SMOKE_TMP_ROOT" ]; then
    tmpdir="$SMOKE_TMP_ROOT"
  else
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' RETURN
  fi
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
  elif [ "$case_mode" = "remote" ]; then
    (
      cd "$project"
      TTK_INIT_RAW_BASE="$RAW_BASE_URI" bash <(cat "$REPO_ROOT/bootstrap/init.sh") "$DEV_NAME" < /dev/null
    )
  else
    (
      cd "$project"
      bash <(curl --retry 5 --retry-delay 1 --retry-all-errors -fsSL "$TRUE_REMOTE_INIT_URL") "$DEV_NAME" < /dev/null
    )
  fi

  assert_file "$project/.trellis/.team-kit-version"
  assert_file "$project/.trellis/config/config.json"
  assert_file "$project/.trellis/config/workflow_profiles.json"
  assert_file "$project/.trellis/spec/guides/ai-behavior/agent-results.md"
  assert_file "$project/.trellis/spec/guides/ai-behavior/common-mistakes.md"
  assert_file "$project/.trellis/spec/guides/ai-behavior/guardrails.md"
  assert_file "$project/.trellis/spec/guides/ai-behavior/orchestration.md"
  assert_file "$project/.trellis/spec/guides/ai-behavior/skill-routing.md"
  assert_file "$project/.trellis/scripts/validate_scope_manifest.py"
  assert_file "$project/.trellis/scripts/validate_guardrail_overrides.py"
  assert_file "$project/.trellis/scripts/validate_agent_results.py"
  assert_file "$project/.trellis/scripts/validate_spec_update_targets.py"
  assert_file "$project/.trellis/scripts/replay_workflow_cases.py"
  assert_file "$project/.trellis/scripts/detect_spec_update_candidates.py"
  assert_file "$project/.trellis/scripts/trellis_doctor.py"
  assert_file "$project/.trellis/templates/scope-manifest.json.tmpl"
  assert_file "$project/.trellis/replay/routing/standard-feature-routes-l3.json"
  assert_file "$project/.trellis/replay/routing/l4-api-contract-change.json"
  assert_file "$project/.trellis/replay/guardrails/contains-and-not-contains.json"
  assert_file "$project/.trellis/replay/guardrails/high-risk-allowlist-missing.json"
  assert_file "$project/.trellis/replay/finish/finish-without-approval-blocks.json"
  assert_file "$project/.trellis/replay/finish/finish-with-overrides-requires-review.json"
  assert_file "$project/.trellis/replay/orchestration/omc-prompt-routes-l5-without-start.json"
  assert_file "$project/.trellis/replay/orchestration/agent-results-legacy-changed-files.json"
  assert_file "$project/.claude/settings.json"
  assert_file "$project/.claude/settings.local.json"
  assert_file "$project/.trellis/workspace/$DEV_NAME/journal-1.md"
  assert_team_specs_match "$project"
  assert_no_pycache "$project"

  (
    cd "$project"
    run_python_no_bytecode .trellis/scripts/validate_runtime_hardening.py >/dev/null
    run_python_no_bytecode .trellis/scripts/replay_workflow_cases.py .trellis/replay >/dev/null
    bash "$REPO_ROOT/bootstrap/personalize-local.sh" "$DEV_NAME" >/dev/null
  )
  assert_file "$project/.trellis/workspace/$DEV_NAME/preferences.md"
  assert_no_pycache "$project"

  echo "[smoke] PASS: $case_mode install path"
  if [ "$case_mode" = "local" ]; then
    LOCAL_PROJECT="$project"
  elif [ "$case_mode" = "remote" ]; then
    REMOTE_PROJECT="$project"
  elif [ "$case_mode" = "true-remote" ]; then
    TRUE_REMOTE_PROJECT="$project"
  fi
  if [ -z "$SMOKE_TMP_ROOT" ]; then
    rm -rf "$tmpdir"
    trap - RETURN
  fi
}

assert_install_inventories_match() {
  local local_project="$1" remote_project="$2" left right
  left="$(mktemp)"
  right="$(mktemp)"

  (
    cd "$local_project"
    find . -path './.git' -prune -o -print | sort
  ) > "$left"
  (
    cd "$remote_project"
    find . -path './.git' -prune -o -print | sort
  ) > "$right"

  if ! cmp -s "$left" "$right"; then
    echo "[smoke] ERROR: local and remote install inventories differ" >&2
    diff -u "$left" "$right" >&2 || true
    rm -f "$left" "$right"
    exit 1
  fi

  rm -f "$left" "$right"
  echo "[smoke] PASS: local and remote install inventories match"
}

if [ "$MODE" = "all" ]; then
  SMOKE_TMP_ROOT="$(mktemp -d)"
  trap 'rm -rf "$SMOKE_TMP_ROOT"' EXIT
  run_case "local"
  run_case "remote"
  assert_install_inventories_match "$LOCAL_PROJECT" "$REMOTE_PROJECT"
  rm -rf "$SMOKE_TMP_ROOT"
  trap - EXIT
elif [ "$MODE" = "local" ]; then
  run_case "local"
elif [ "$MODE" = "remote" ]; then
  run_case "remote"
elif [ "$MODE" = "true-remote" ]; then
  SMOKE_TMP_ROOT="$(mktemp -d)"
  trap 'rm -rf "$SMOKE_TMP_ROOT"' EXIT
  run_case "local"
  run_case "true-remote"
  assert_install_inventories_match "$LOCAL_PROJECT" "$TRUE_REMOTE_PROJECT"
  rm -rf "$SMOKE_TMP_ROOT"
  trap - EXIT
fi

echo "[smoke] All requested smoke tests passed."
