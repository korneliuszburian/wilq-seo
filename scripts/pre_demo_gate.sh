#!/usr/bin/env bash
set -euo pipefail

api_base="http://127.0.0.1:8000"
dashboard_port="5173"
run_dashboard=1
run_shared_schema=1
skill_mode="core"

usage() {
  cat <<'EOF'
Usage:
  scripts/pre_demo_gate.sh [--api-base URL] [--dashboard-port PORT]
                           [--skip-dashboard] [--skip-shared-schema]
                           [--core-skills|--all-skills|--no-skills]

Runs the small pre-demo gate against the managed local stack. It checks live API
contract shape, shared dashboard schemas, marketer routes, and selected WILQ
skill smokes. Skill smokes run sequentially because context-pack-heavy checks
can timeout when executed in parallel.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --api-base)
      api_base="${2:?--api-base requires a URL}"
      shift 2
      ;;
    --dashboard-port)
      dashboard_port="${2:?--dashboard-port requires a port}"
      shift 2
      ;;
    --skip-dashboard)
      run_dashboard=0
      shift
      ;;
    --skip-shared-schema)
      run_shared_schema=0
      shift
      ;;
    --core-skills)
      skill_mode="core"
      shift
      ;;
    --all-skills)
      skill_mode="all"
      shift
      ;;
    --no-skills)
      skill_mode="none"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

run_step() {
  local label="$1"
  shift
  echo "==> ${label}"
  "$@"
}

run_quiet_step() {
  local label="$1"
  shift
  echo "==> ${label}"
  "$@" >/dev/null
}

api_port="${api_base##*:}"
api_port="${api_port%%/*}"

core_skill_scripts=(
  ".agents/skills/wilq-daily-command/scripts/smoke_context_pack.py"
  ".agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-ahrefs-gap-finder/scripts/smoke_skill_contract.py"
)

all_skill_scripts=(
  ".agents/skills/wilq-daily-command/scripts/smoke_context_pack.py"
  ".agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-ahrefs-gap-finder/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-campaign-builder/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-demand-gen-operator/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-gsc-content-doctor/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py"
  ".agents/skills/wilq-social-publisher/scripts/smoke_skill_contract.py"
)

run_step "local stack status" scripts/local_stack.sh status
run_step "API health" curl -fsS --max-time 5 "${api_base%/}/api/health"
run_step "live contract smoke" uv run python scripts/live_contract_smoke.py --api-base "$api_base"
run_step "dashboard usefulness audit" uv run python scripts/dashboard_usefulness_audit.py --api-base "$api_base"
run_step "context-pack language guard" uv run python scripts/context_pack_language_guard.py --api-base "$api_base"

if [ "$run_shared_schema" -eq 1 ]; then
  run_step "shared schemas live contracts" env WILQ_API_BASE="$api_base" \
    pnpm --filter @wilq/shared-schemas test:live-contracts
fi

if [ "$run_dashboard" -eq 1 ]; then
  run_step "dashboard API-backed route smoke" env \
    WILQ_E2E_API_PORT="$api_port" \
    WILQ_E2E_DASHBOARD_PORT="$dashboard_port" \
    CI= \
    pnpm --filter @wilq/dashboard exec playwright test \
      apps/dashboard/e2e/dashboard-api.spec.ts --workers=1
fi

case "$skill_mode" in
  core)
    skill_scripts=("${core_skill_scripts[@]}")
    ;;
  all)
    skill_scripts=("${all_skill_scripts[@]}")
    ;;
  none)
    skill_scripts=()
    ;;
esac

for skill_script in "${skill_scripts[@]}"; do
  run_quiet_step "skill smoke ${skill_script}" uv run python "$skill_script" --api-base "$api_base"
done

echo "Pre-demo gate passed."
