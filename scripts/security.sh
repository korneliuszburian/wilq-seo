#!/usr/bin/env bash
set -euo pipefail

uv run --extra dev bandit -q -r wilq apps/api .codex/hooks

if uv run --extra dev pip-audit --version >/dev/null 2>&1; then
  uv run --extra dev pip-audit
else
  echo "Skipping pip-audit: command unavailable."
fi

if command -v semgrep >/dev/null 2>&1; then
  semgrep scan --config auto
else
  echo "Skipping semgrep: command unavailable."
fi

if uv run --extra dev detect-secrets --version >/dev/null 2>&1; then
  detect_secrets_output="$(mktemp)"
  trap 'rm -f "${detect_secrets_output:-}"' EXIT
  detect_secrets_exclude='(^|/)(node_modules|\.venv|dist|\.git|coverage|htmlcov)/|pnpm-lock\.yaml|(^|/)\.env$|(^|/)\.env\.(?!example$)[^/]+$|(^|/)ekologus-access-pack-[^/]+/|(^|/)credentials/'
  uv run --extra dev detect-secrets scan . \
    --exclude-files "$detect_secrets_exclude" \
    > "$detect_secrets_output"
  uv run python - "$detect_secrets_output" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text())
results = payload.get("results", {})
if results:
    print(json.dumps({"results": results}, indent=2))
    raise SystemExit("detect-secrets found potential findings")
print(json.dumps({"results": {}}))
PY
else
  echo "Skipping detect-secrets: command unavailable."
fi
