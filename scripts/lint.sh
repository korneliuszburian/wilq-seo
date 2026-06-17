#!/usr/bin/env bash
set -euo pipefail

uv run --extra dev ruff check .
if [ -d apps/dashboard/node_modules ]; then
  pnpm lint
else
  echo "Skipping frontend lint: node_modules missing. Run pnpm install."
fi
