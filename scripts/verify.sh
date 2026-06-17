#!/usr/bin/env bash
set -euo pipefail

scripts/quality.sh
scripts/security.sh

uv run python - <<'PY'
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

uv run wilq jobs status >/dev/null
uv run wilq jobs list >/dev/null

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
    for required_label in ["Dowody", "Diagnoza", "Kandydaci działań", "Walidacja", "Następny krok"]:
        assert required_label in output_contract, f"{name}: missing Polish output label {required_label!r}"
print("Skill structure smoke passed")
PY

skill_api_base="http://127.0.0.1:8765"
skill_api_pid=""
skill_api_log="${TMPDIR:-/tmp}/wilq-skill-api.log"
if ! curl -fsS --max-time 2 "$skill_api_base/api/health" >/dev/null 2>&1; then
  .venv/bin/uvicorn apps.api.wilq_api.main:app --host 127.0.0.1 --port 8765 >"$skill_api_log" 2>&1 &
  skill_api_pid="$!"
  trap 'if [ -n "$skill_api_pid" ]; then kill "$skill_api_pid" >/dev/null 2>&1 || true; fi' EXIT
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 2 "$skill_api_base/api/health" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi
curl -fsS --max-time 2 "$skill_api_base/api/health" >/dev/null
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base "$skill_api_base" >/dev/null
for skill_script in .agents/skills/wilq-*/scripts/smoke_skill_contract.py; do
  uv run python "$skill_script" --api-base "$skill_api_base" >/dev/null
done
echo "Skill API smoke passed"

if [ -d apps/dashboard/node_modules ]; then
  pnpm --filter @wilq/dashboard test:e2e
  pnpm --filter @wilq/dashboard build
else
  echo "Skipping dashboard e2e/build: node_modules missing. Run pnpm install."
fi
