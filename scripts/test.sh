#!/usr/bin/env bash
set -euo pipefail

uv run --extra dev python -m pytest
if [ -d apps/dashboard/node_modules ]; then
  pnpm test
else
  echo "Skipping frontend tests: node_modules missing. Run pnpm install."
fi
