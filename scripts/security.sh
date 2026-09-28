#!/usr/bin/env bash
set -euo pipefail

bandit_report="$(mktemp)"
detect_secrets_output=""
cleanup_security_outputs() {
  rm -f "$bandit_report"
  if [[ -n "$detect_secrets_output" ]]; then
    rm -f "$detect_secrets_output"
  fi
}
trap cleanup_security_outputs EXIT

set +e
uv run --extra dev python -m bandit -q -r wilq apps/api .codex/hooks -f json -o "$bandit_report"
bandit_status=$?
set -e
uv run python scripts/check_bandit_baseline.py "$bandit_report" "$bandit_status"

if uv run --extra dev python -m pip_audit --version >/dev/null 2>&1; then
  uv run --extra dev python -m pip_audit
else
  echo "Skipping pip-audit: command unavailable."
fi

if command -v semgrep >/dev/null 2>&1; then
  semgrep scan --config auto
else
  echo "Skipping semgrep: command unavailable."
fi

if uv run --extra dev python -m detect_secrets --version >/dev/null 2>&1; then
  detect_secrets_output="$(mktemp)"
  detect_secrets_exclude='(^|/)(node_modules|\.venv|dist|\.git|coverage|htmlcov)/|pnpm-lock\.yaml|(^|/)\.env$|(^|/)\.env\.(?!example$)[^/]+$|(^|/)ekologus-access-pack-[^/]+/|(^|/)credentials/|(^|/)docs/agents/reports/benchmark/|\.manifest\.json$'
  uv run --extra dev python -m detect_secrets scan . \
    --exclude-files "$detect_secrets_exclude" \
    > "$detect_secrets_output"
  uv run python scripts/filter_detect_secrets.py \
    --repository-root . \
    "$detect_secrets_output"
else
  echo "Skipping detect-secrets: command unavailable."
fi
