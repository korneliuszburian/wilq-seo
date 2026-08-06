#!/usr/bin/env bash
set -euo pipefail

test_tmp_root="${WILQ_TEST_TMPDIR:-$PWD/.local-lab/test-tmp}"
mkdir -p "$test_tmp_root"

usage() {
  cat <<'EOF'
Usage:
  scripts/test.sh TEST_SELECTOR [TEST_SELECTOR ...]
  WILQ_TEST_EXCLUSIVE=1 scripts/test.sh --full

Run focused Python tests by naming their selectors. The full backend suite is
an exclusive gate: it is for CI or a machine window reserved for this checkout.
Frontend tests are owned by the separate frontend CI job.
EOF
}

if [ "$#" -eq 0 ]; then
  usage >&2
  exit 64
fi

full_suite=false
if [ "$1" = "--full" ]; then
  if [ "$#" -ne 1 ]; then
    usage >&2
    exit 64
  fi
  full_suite=true
  if [ "${WILQ_TEST_EXCLUSIVE:-}" != "1" ]; then
    echo "Refusing full backend suite without WILQ_TEST_EXCLUSIVE=1." >&2
    echo "Use a focused selector locally or run the full gate in CI/an exclusive window." >&2
    exit 75
  fi
fi

if [ "$full_suite" = true ] && command -v flock >/dev/null 2>&1; then
  lock_path="$test_tmp_root/backend-full-suite.lock"
  exec 9>"$lock_path"
  if ! flock -n 9; then
    echo "Another full backend suite already owns $lock_path." >&2
    exit 75
  fi
fi

if [ "$full_suite" = true ]; then
  set --
fi

WILQ_TEST_TMPDIR="$test_tmp_root" \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 \
  uv run --extra dev python -m pytest "$@"
