#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${WILQ_RUNTIME_DIR:-"$ROOT_DIR/.local-lab/runtime"}"
API_HOST="${WILQ_API_HOST:-127.0.0.1}"
API_PORT="${WILQ_API_PORT:-8000}"
DASHBOARD_HOST="${WILQ_DASHBOARD_HOST:-127.0.0.1}"
DASHBOARD_PORT="${WILQ_DASHBOARD_PORT:-5173}"

require_supported_loopback_host() {
  local variable="$1"
  local host="$2"
  case "$host" in
    127.0.0.1|localhost)
      ;;
    *)
      echo "${variable} must be 127.0.0.1 or localhost; refusing non-loopback bind: ${host}" >&2
      exit 2
      ;;
  esac
}

require_supported_loopback_host "WILQ_API_HOST" "$API_HOST"
require_supported_loopback_host "WILQ_DASHBOARD_HOST" "$DASHBOARD_HOST"

API_URL="http://${API_HOST}:${API_PORT}"
DASHBOARD_URL="http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"

mkdir -p "$RUNTIME_DIR"
chmod 700 "$RUNTIME_DIR"

for runtime_file in "$RUNTIME_DIR"/*.pid "$RUNTIME_DIR"/*.log; do
  if [ -e "$runtime_file" ]; then
    chmod 600 "$runtime_file"
  fi
done

usage() {
  cat <<EOF
Usage: scripts/local_stack.sh <start|stop|restart|status|logs>

Manages the canonical local WILQ dev stack:
  API:       ${API_URL}
  Dashboard: ${DASHBOARD_URL}/command-center

Runtime files:
  ${RUNTIME_DIR}
EOF
}

pid_file() {
  printf "%s/%s.pid" "$RUNTIME_DIR" "$1"
}

log_file() {
  printf "%s/%s.log" "$RUNTIME_DIR" "$1"
}

read_pid() {
  local file
  file="$(pid_file "$1")"
  if [ -f "$file" ]; then
    tr -d '[:space:]' <"$file"
  fi
}

is_pid_alive() {
  local pid="${1:-}"
  [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1
}

port_pid() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN -n -P 2>/dev/null | head -n 1 || true
}

pid_args() {
  local pid="$1"
  ps -p "$pid" -o args= 2>/dev/null || true
}

pid_pgid() {
  local pid="$1"
  ps -p "$pid" -o pgid= 2>/dev/null | tr -d '[:space:]' || true
}

safe_to_stop() {
  local service="$1"
  local pid="$2"
  local args
  args="$(pid_args "$pid")"
  case "$service" in
    api)
      [[ "$args" == *"apps.api.wilq_api.main:app"* ]] || [[ "$args" == *"$ROOT_DIR"*"/.venv/bin/uvicorn"* ]]
      ;;
    dashboard)
      [[ "$args" == *"$ROOT_DIR"* ]] && { [[ "$args" == *"vite"* ]] || [[ "$args" == *"@wilq/dashboard"* ]]; }
      ;;
    *)
      return 1
      ;;
  esac
}

kill_process_group() {
  local pid="$1"
  local pgid
  pgid="$(pid_pgid "$pid")"
  if [ -n "$pgid" ]; then
    kill -TERM -- "-$pgid" >/dev/null 2>&1 || true
  else
    kill "$pid" >/dev/null 2>&1 || true
  fi
}

wait_port_free() {
  local port="$1"
  for _ in $(seq 1 40); do
    if [ -z "$(port_pid "$port")" ]; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

wait_url() {
  local url="$1"
  local log="$2"
  for _ in $(seq 1 160); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "Timed out waiting for $url" >&2
  echo "Last log lines from $log:" >&2
  tail -80 "$log" >&2 || true
  return 1
}

stop_service() {
  local service="$1"
  local port="$2"
  local pid
  pid="$(read_pid "$service")"

  if is_pid_alive "$pid"; then
    kill_process_group "$pid"
  fi
  rm -f "$(pid_file "$service")"

  local owner
  owner="$(port_pid "$port")"
  if [ -n "$owner" ]; then
    if safe_to_stop "$service" "$owner"; then
      kill_process_group "$owner"
    else
      echo "Refusing to stop unmanaged process on port $port:" >&2
      echo "  pid=$owner args=$(pid_args "$owner")" >&2
      return 1
    fi
  fi

  wait_port_free "$port"
}

start_api() {
  local log
  log="$(log_file api)"
  if curl -fsS --max-time 2 "${API_URL}/api/health" >/dev/null 2>&1; then
    echo "API already ready: ${API_URL}"
    return 0
  fi
  if [ -n "$(port_pid "$API_PORT")" ]; then
    echo "API port ${API_PORT} is occupied but health is not ready. Run restart." >&2
    return 1
  fi
  : >"$log"
  (
    cd "$ROOT_DIR"
    setsid uv run uvicorn apps.api.wilq_api.main:app --host "$API_HOST" --port "$API_PORT" \
      >>"$log" 2>&1 </dev/null &
    echo "$!" >"$(pid_file api)"
  )
  wait_url "${API_URL}/api/health" "$log"
  echo "API ready: ${API_URL}"
}

start_dashboard() {
  local log
  log="$(log_file dashboard)"
  if curl -fsS --max-time 2 "${DASHBOARD_URL}/command-center" >/dev/null 2>&1; then
    echo "Dashboard already ready: ${DASHBOARD_URL}/command-center"
    return 0
  fi
  if [ -n "$(port_pid "$DASHBOARD_PORT")" ]; then
    echo "Dashboard port ${DASHBOARD_PORT} is occupied but route is not ready. Run restart." >&2
    return 1
  fi
  : >"$log"
  (
    cd "$ROOT_DIR"
    VITE_WILQ_API_BASE_URL="$API_URL" setsid pnpm --filter @wilq/dashboard dev \
      --host "$DASHBOARD_HOST" --port "$DASHBOARD_PORT" --strictPort \
      >>"$log" 2>&1 </dev/null &
    echo "$!" >"$(pid_file dashboard)"
  )
  wait_url "${DASHBOARD_URL}/command-center" "$log"
  echo "Dashboard ready: ${DASHBOARD_URL}/command-center"
}

start_stack() {
  start_api
  start_dashboard
}

stop_stack() {
  stop_service dashboard "$DASHBOARD_PORT" || true
  stop_service api "$API_PORT" || true
  echo "Local WILQ stack stopped."
}

status_service() {
  local service="$1"
  local port="$2"
  local url="$3"
  local pid
  local owner
  pid="$(read_pid "$service")"
  owner="$(port_pid "$port")"
  printf "%s\n" "$service"
  printf "  pid_file: %s\n" "$(pid_file "$service")"
  printf "  managed_pid: %s\n" "${pid:-none}"
  printf "  managed_alive: %s\n" "$(if is_pid_alive "$pid"; then echo yes; else echo no; fi)"
  printf "  port_owner_pid: %s\n" "${owner:-none}"
  if [ -n "$owner" ]; then
    printf "  port_owner_args: %s\n" "$(pid_args "$owner")"
  fi
  printf "  ready: %s\n" "$(if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then echo yes; else echo no; fi)"
}

status_stack() {
  status_service api "$API_PORT" "${API_URL}/api/health"
  status_service dashboard "$DASHBOARD_PORT" "${DASHBOARD_URL}/command-center"
}

logs_stack() {
  echo "== API log: $(log_file api) =="
  tail -80 "$(log_file api)" 2>/dev/null || true
  echo
  echo "== Dashboard log: $(log_file dashboard) =="
  tail -80 "$(log_file dashboard)" 2>/dev/null || true
}

case "${1:-}" in
  start)
    start_stack
    ;;
  stop)
    stop_stack
    ;;
  restart)
    stop_stack
    start_stack
    ;;
  status)
    status_stack
    ;;
  logs)
    logs_stack
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
