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
  uv run --extra dev detect-secrets scan . \
    --exclude-files '(^|/)(node_modules|\.venv|dist|\.git|coverage|htmlcov)/|pnpm-lock\.yaml'
else
  echo "Skipping detect-secrets: command unavailable."
fi
