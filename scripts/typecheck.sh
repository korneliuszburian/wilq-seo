#!/usr/bin/env bash
set -euo pipefail

uv run --extra dev python -m mypy
if [ -d apps/dashboard/node_modules ]; then
  pnpm typecheck
else
  echo "Skipping frontend typecheck: node_modules missing. Run pnpm install."
fi
