#!/usr/bin/env bash
set -euo pipefail

verify_tmp_dir="$(mktemp -d)"
skill_api_pid=""
dashboard_api_pid=""
dashboard_dev_pid=""
cleanup() {
  if [ -n "$skill_api_pid" ]; then
    kill "$skill_api_pid" >/dev/null 2>&1 || true
  fi
  if [ -n "$dashboard_dev_pid" ]; then
    kill "$dashboard_dev_pid" >/dev/null 2>&1 || true
  fi
  if [ -n "$dashboard_api_pid" ]; then
    kill "$dashboard_api_pid" >/dev/null 2>&1 || true
  fi
  rm -rf "$verify_tmp_dir"
}
trap cleanup EXIT

verify_state_db="$verify_tmp_dir/wilq-verify.sqlite3"
verify_metric_db="$verify_tmp_dir/wilq-verify.duckdb"
skill_api_port="$(
  uv run python - <<'PY'
import socket

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
dashboard_api_port="$(
  uv run python - <<'PY'
import socket

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
dashboard_dev_port="$(
  uv run python - <<'PY'
import socket

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"

scripts/quality.sh
scripts/security.sh

WILQ_STATE_DB="$verify_state_db" WILQ_METRIC_DB="$verify_metric_db" uv run python - <<'PY'
from fastapi.testclient import TestClient
from apps.api.wilq_api.main import app

client = TestClient(app)
for path in [
    "/api/health",
    "/api/system/status",
    "/api/connectors",
    "/api/dashboard/command-center",
    "/api/codex/context",
    "/api/jobs/status",
    "/api/jobs",
]:
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code, response.text)
print("API smoke passed")
PY

WILQ_STATE_DB="$verify_state_db" WILQ_METRIC_DB="$verify_metric_db" uv run wilq jobs status >/dev/null
WILQ_STATE_DB="$verify_state_db" WILQ_METRIC_DB="$verify_metric_db" uv run wilq jobs list >/dev/null

uv run python - <<'PY'
from pathlib import Path
import re
import yaml

expected = {
    "wilq-daily-command",
    "wilq-ads-doctor",
    "wilq-gsc-content-doctor",
    "wilq-ahrefs-gap-finder",
    "wilq-localo-operator",
    "wilq-content-strategist",
    "wilq-social-publisher",
    "wilq-campaign-builder",
    "wilq-custom-segments",
    "wilq-demand-gen-operator",
    "wilq-ga4-analyst",
    "wilq-merchant-feed-operator",
}
root = Path(".agents/skills")
missing = sorted(name for name in expected if not (root / name / "SKILL.md").exists())
assert not missing, f"Missing skill folders: {missing}"
for name in sorted(expected):
    skill_dir = root / name
    content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match, f"{name}: missing YAML frontmatter"
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter["name"] == name, f"{name}: wrong frontmatter name"
    assert frontmatter.get("description"), f"{name}: missing description"
    assert (skill_dir / "references").is_dir(), f"{name}: missing references/"
    assert (skill_dir / "scripts").is_dir(), f"{name}: missing scripts/"
    assert "invent metrics" in content.lower(), f"{name}: missing no-invented-metrics guardrail"
    assert "Polish language contract" in content, f"{name}: missing Polish response contract"
    output_contract = (skill_dir / "references" / "output-contract.md").read_text(encoding="utf-8")
    for required_label in ["Dowody", "Diagnoza", "Akcje do sprawdzenia", "Sprawdzenie w WILQ", "Następny krok"]:
        assert required_label in output_contract, f"{name}: missing Polish output label {required_label!r}"
print("Skill structure smoke passed")
PY

skill_api_base="http://127.0.0.1:${skill_api_port}"
skill_api_log="${TMPDIR:-/tmp}/wilq-skill-api.log"
WILQ_STATE_DB="$verify_state_db" WILQ_METRIC_DB="$verify_metric_db" \
  .venv/bin/uvicorn apps.api.wilq_api.main:app --host 127.0.0.1 --port "$skill_api_port" >"$skill_api_log" 2>&1 &
skill_api_pid="$!"
for _ in $(seq 1 30); do
  if curl -fsS --max-time 2 "$skill_api_base/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
curl -fsS --max-time 2 "$skill_api_base/api/health" >/dev/null
scripts/eval_marketing_brief.sh --api-base "$skill_api_base" >/dev/null
API_BASE="$skill_api_base" scripts/eval_action_validation.sh >/dev/null
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base "$skill_api_base" >/dev/null
for skill_script in .agents/skills/wilq-*/scripts/smoke_skill_contract.py; do
  timeout 90s uv run python "$skill_script" --api-base "$skill_api_base" >/dev/null
done
echo "Skill API smoke passed"

if [ -n "$skill_api_pid" ]; then
  kill "$skill_api_pid" >/dev/null 2>&1 || true
  wait "$skill_api_pid" >/dev/null 2>&1 || true
  skill_api_pid=""
fi

if [ -d apps/dashboard/node_modules ]; then
  dashboard_api_base="http://127.0.0.1:${dashboard_api_port}"
  dashboard_base="http://127.0.0.1:${dashboard_dev_port}"
  dashboard_api_log="${TMPDIR:-/tmp}/wilq-dashboard-api.log"
  dashboard_dev_log="${TMPDIR:-/tmp}/wilq-dashboard-vite.log"
  uv run uvicorn apps.api.wilq_api.main:app --host 127.0.0.1 --port "$dashboard_api_port" >"$dashboard_api_log" 2>&1 &
  dashboard_api_pid="$!"
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 2 "$dashboard_api_base/api/health" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
  curl -fsS --max-time 2 "$dashboard_api_base/api/health" >/dev/null

  VITE_WILQ_API_BASE_URL="$dashboard_api_base" \
    pnpm --filter @wilq/dashboard dev --host 127.0.0.1 --port "$dashboard_dev_port" --strictPort >"$dashboard_dev_log" 2>&1 &
  dashboard_dev_pid="$!"
  for _ in $(seq 1 40); do
    if curl -fsS --max-time 2 "$dashboard_base/command-center" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
  curl -fsS --max-time 2 "$dashboard_base/command-center" >/dev/null

  WILQ_E2E_API_PORT="$dashboard_api_port" WILQ_E2E_DASHBOARD_PORT="$dashboard_dev_port" CI= \
    pnpm --filter @wilq/dashboard exec playwright test --workers=1
  pnpm --filter @wilq/dashboard build
else
  echo "Skipping dashboard e2e/build: node_modules missing. Run pnpm install."
fi
