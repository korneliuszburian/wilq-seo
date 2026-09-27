#!/usr/bin/env bash
# Bounded long-running delivery loop driver for WILQ.
#
# Runs one `pi --continue --print` iteration per step, stops on an explicit stop
# marker, a non-zero exit, or the hard iteration cap. Never starts a slice the
# tree cannot carry: refuses to run with a dirty tree by default.
#
# Usage:
#   WILQ_LOOP=1 WILQ_LOOP_MAX_ITERS=3 \
#     scripts/long_running_loop.sh .krn/loop/step.md [session-id]
#
# Stop markers printed by the step prompt: LOOP: DONE | LOOP: BLOCKED | LOOP: BUDGET
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

usage() {
  echo "usage: WILQ_LOOP=1 scripts/long_running_loop.sh STEP_PROMPT_FILE [SESSION_ID]" >&2
  echo "env: WILQ_LOOP_MAX_ITERS (default 3), WILQ_LOOP_REQUIRE_CLEAN (default 1), WILQ_LOOP_CMD (default pi)" >&2
}

if [[ "${WILQ_LOOP:-0}" != "1" ]]; then
  echo "refusing to run: export WILQ_LOOP=1 to opt in" >&2
  exit 64
fi

STEP_FILE="${1:-}"
SESSION_ID="${2:-}"
MAX_ITERS="${WILQ_LOOP_MAX_ITERS:-3}"
REQUIRE_CLEAN="${WILQ_LOOP_REQUIRE_CLEAN:-1}"
PI_CMD="${WILQ_LOOP_CMD:-pi}"

if [[ -z "$STEP_FILE" || ! -f "$STEP_FILE" ]]; then
  usage
  exit 64
fi
if ! [[ "$MAX_ITERS" =~ ^[1-9][0-9]*$ ]]; then
  echo "WILQ_LOOP_MAX_ITERS must be a positive integer" >&2
  exit 64
fi

if [[ "$REQUIRE_CLEAN" == "1" ]]; then
  dirty="$(git status --porcelain -- .beads packages apps wilq tests scripts docs | wc -l)"
  if [[ "$dirty" -ne 0 ]]; then
    echo "refusing to run: working tree has $dirty tracked changes; commit or stash first" >&2
    git status --porcelain -- .beads packages apps wilq tests scripts docs | head -20 >&2
    exit 65
  fi
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR=".krn/runs/long-running/$STAMP"
mkdir -p "$RUN_DIR"
cp "$STEP_FILE" "$RUN_DIR/step.md"
printf 'started_at=%s\nroot=%s\nmax_iters=%s\nsession_id=%s\n' \
  "$STAMP" "$ROOT" "$MAX_ITERS" "${SESSION_ID:-<continue-most-recent>}" > "$RUN_DIR/meta.txt"

echo "loop run: $RUN_DIR (max $MAX_ITERS iterations)"

for ((iteration = 1; iteration <= MAX_ITERS; iteration++)); do
  log="$RUN_DIR/iter-$(printf '%02d' "$iteration").txt"
  echo "--- iteration $iteration -> $log"
  args=(--continue --print)
  if [[ -n "$SESSION_ID" ]]; then
    args=(--session-id "$SESSION_ID" --print)
  fi
  set +e
  "$PI_CMD" "${args[@]}" "$(cat "$STEP_FILE")" > "$log" 2>&1
  status=$?
  set -e
  tail -n 40 "$log"
  if [[ "$status" -ne 0 ]]; then
    echo "LOOP: BLOCKED" | tee -a "$log"
    echo "iteration $iteration exited $status; stopping" >&2
    exit "$status"
  fi
  if grep -qE '^LOOP: (DONE|BLOCKED|BUDGET)' "$log"; then
    echo "stop marker found in $log"
    exit 0
  fi
done

echo "LOOP: BUDGET" | tee -a "$RUN_DIR/iter-$(printf '%02d' "$MAX_ITERS").txt"
echo "iteration cap reached ($MAX_ITERS); stopping" >&2
