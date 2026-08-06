#!/usr/bin/env bash
set -euo pipefail

test_tmp_root="${WILQ_TEST_TMPDIR:-$PWD/.local-lab/test-tmp}"
mkdir -p "$test_tmp_root"
WILQ_TEST_TMPDIR="$test_tmp_root" uv run --extra dev python -m pytest
if [ -d apps/dashboard/node_modules ]; then
  pnpm test
else
  echo "Skipping frontend tests: node_modules missing. Run pnpm install."
fi
