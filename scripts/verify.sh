#!/usr/bin/env bash
set -euo pipefail

scripts/quality.sh
scripts/security.sh

python3 - <<'PY'
from fastapi.testclient import TestClient
from apps.api.wilq_api.main import app

client = TestClient(app)
for path in ["/api/health", "/api/system/status", "/api/connectors", "/api/dashboard/command-center", "/api/codex/context"]:
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code, response.text)
print("API smoke passed")
PY

if [ -d apps/dashboard/node_modules ]; then
  pnpm --filter @wilq/dashboard build
else
  echo "Skipping dashboard build: node_modules missing. Run pnpm install."
fi

