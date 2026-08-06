#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${WILQ_RUNTIME_DIR:-"$ROOT_DIR/.local-lab/runtime"}"
API_HOST="${WILQ_API_HOST:-127.0.0.1}"
API_PORT="${WILQ_API_PORT:-8000}"
API_RELOAD="${WILQ_API_RELOAD:-1}"
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

case "$API_RELOAD" in
  0|1)
    ;;
  *)
    echo "WILQ_API_RELOAD must be 0 or 1; got: ${API_RELOAD}" >&2
    exit 2
    ;;
esac

API_URL="http://${API_HOST}:${API_PORT}"
DASHBOARD_URL="http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"

mkdir -p "$RUNTIME_DIR"
chmod 700 "$RUNTIME_DIR"

for runtime_file in "$RUNTIME_DIR"/*.pid "$RUNTIME_DIR"/*.log "$RUNTIME_DIR"/*.port; do
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

API reload:
  WILQ_API_RELOAD=${API_RELOAD} (local development only)
EOF
}

pid_file() {
  printf "%s/%s.pid" "$RUNTIME_DIR" "$1"
}

log_file() {
  printf "%s/%s.log" "$RUNTIME_DIR" "$1"
}

port_file() {
  printf "%s/%s.port" "$RUNTIME_DIR" "$1"
}

is_valid_port() {
  local port="${1:-}"
  [[ "$port" =~ ^[0-9]+$ ]] && ((10#$port >= 1 && 10#$port <= 65535))
}

read_recorded_port() {
  local file
  local port
  file="$(port_file "$1")"
  if [ -f "$file" ]; then
    port="$(tr -d '[:space:]' <"$file")"
    if is_valid_port "$port"; then
      printf "%s" "$port"
    fi
  fi
}

record_service_port() {
  local service="$1"
  local port="$2"
  local file
  is_valid_port "$port" || {
    echo "Refusing to persist invalid ${service} port: ${port}" >&2
    return 1
  }
  file="$(port_file "$service")"
  printf "%s\n" "$port" >"$file"
  chmod 600 "$file"
}

remove_recorded_port() {
  rm -f "$(port_file "$1")"
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

port_from_process_args() {
  local pid="$1"
  local args
  local port
  args="$(pid_args "$pid")"
  if [[ "$args" =~ --port[[:space:]]+([0-9]+) ]]; then
    port="${BASH_REMATCH[1]}"
    if is_valid_port "$port"; then
      printf "%s" "$port"
    fi
  fi
}

runtime_service_port() {
  local service="$1"
  local configured_port="$2"
  local pid
  local port
  pid="$(read_pid "$service")"
  if is_pid_alive "$pid"; then
    port="$(read_recorded_port "$service")"
    if [ -n "$port" ]; then
      printf "%s" "$port"
      return 0
    fi
    # Compatibility for a process that was started before port metadata
    # existed.  This is read-only and lets status/stop target the managed
    # service rather than a default port occupied by another checkout.
    port="$(port_from_process_args "$pid")"
    if [ -n "$port" ]; then
      printf "%s" "$port"
      return 0
    fi
  fi
  printf "%s" "$configured_port"
}

pid_ppid() {
  local pid="$1"
  ps -p "$pid" -o ppid= 2>/dev/null | tr -d '[:space:]' || true
}

pid_cwd() {
  local pid="$1"
  readlink "/proc/$pid/cwd" 2>/dev/null || true
}

pid_pgid() {
  local pid="$1"
  ps -p "$pid" -o pgid= 2>/dev/null | tr -d '[:space:]' || true
}

is_wilq_service_process() {
  local service="$1"
  local pid="$2"
  local args
  args="$(pid_args "$pid")"
  case "$service" in
    api)
      [[ "$args" == *"apps.api.wilq_api.main:app"* ]]
      ;;
    dashboard)
      [[ "$args" == *"@wilq/dashboard"* ]] || [[ "$args" == *"apps/dashboard"*"vite"* ]]
      ;;
    *)
      return 1
      ;;
  esac
}

is_current_wilq_service_process() {
  local service="$1"
  local pid="$2"
  local cwd
  cwd="$(pid_cwd "$pid")"
  is_wilq_service_process "$service" "$pid" && {
    [[ "$cwd" == "$ROOT_DIR" ]] || [[ "$(pid_args "$pid")" == *"$ROOT_DIR"* ]]
  }
}

is_deleted_wilq_worktree_process() {
  local service="$1"
  local cursor="$2"
  local parent
  local cwd

  # The port listener can be a Uvicorn worker whose command line no longer
  # contains WILQ.  Follow only its short parent chain and accept a process
  # exclusively when a WILQ service parent has a deleted working directory.
  for _ in $(seq 1 8); do
    [ -n "$cursor" ] || return 1
    cwd="$(pid_cwd "$cursor")"
    if is_wilq_service_process "$service" "$cursor" && [[ "$cwd" == *" (deleted)"* ]]; then
      return 0
    fi
    parent="$(pid_ppid "$cursor")"
    [ -n "$parent" ] && [ "$parent" != "$cursor" ] || return 1
    cursor="$parent"
  done
  return 1
}

safe_to_stop() {
  local service="$1"
  local pid="$2"
  is_current_wilq_service_process "$service" "$pid" || \
    is_deleted_wilq_worktree_process "$service" "$pid"
}

kill_process_group() {
  local pid="$1"
  local signal="${2:-TERM}"
  local pgid
  pgid="$(pid_pgid "$pid")"
  if [ -n "$pgid" ]; then
    kill -"$signal" -- "-$pgid" >/dev/null 2>&1 || true
  else
    kill -"$signal" "$pid" >/dev/null 2>&1 || true
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
  local configured_port="$2"
  local port
  local pid
  port="$(runtime_service_port "$service" "$configured_port")"
  pid="$(read_pid "$service")"

  if is_pid_alive "$pid"; then
    if safe_to_stop "$service" "$pid"; then
      kill_process_group "$pid"
    else
      echo "Refusing to stop unmanaged pid from $(pid_file "$service"):" >&2
      echo "  pid=$pid args=$(pid_args "$pid")" >&2
      return 1
    fi
  fi
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

  if wait_port_free "$port"; then
    rm -f "$(pid_file "$service")"
    remove_recorded_port "$service"
    return 0
  fi

  # Uvicorn/Vite reloaders can leave a child listener behind after TERM.  Only
  # escalate when the remaining listener still belongs to this repository;
  # an unrelated process remains protected and is reported to the operator.
  owner="$(port_pid "$port")"
  if [ -n "$owner" ] && safe_to_stop "$service" "$owner"; then
    echo "${service} did not release port ${port} after TERM; sending KILL to its process group." >&2
    kill_process_group "$owner" KILL
    if wait_port_free "$port"; then
      return 0
    fi
  fi
  echo "${service} still owns port ${port} after shutdown; refusing to continue." >&2
  return 1
}

start_api() {
  local log
  local managed_port
  local managed_url
  local pid
  log="$(log_file api)"
  managed_port="$(runtime_service_port api "$API_PORT")"
  managed_url="http://${API_HOST}:${managed_port}"
  pid="$(read_pid api)"
  if is_pid_alive "$pid" && [ "$managed_port" != "$API_PORT" ]; then
    if curl -fsS --max-time 2 "${managed_url}/api/health" >/dev/null 2>&1; then
      echo "API already ready: ${managed_url}"
      return 0
    fi
    echo "Managed API pid ${pid} exists on port ${managed_port} but is not ready. Run restart." >&2
    return 1
  fi
  if curl -fsS --max-time 2 "${API_URL}/api/health" >/dev/null 2>&1; then
    echo "API already ready: ${API_URL}"
    return 0
  fi
  if [ -n "$(port_pid "$API_PORT")" ]; then
    echo "API port ${API_PORT} is occupied but health is not ready. Run restart." >&2
    return 1
  fi
  : >"$log"
  local reload_args=()
  if [ "$API_RELOAD" = "1" ]; then
    reload_args+=(--reload --reload-dir "$ROOT_DIR/apps/api" --reload-dir "$ROOT_DIR/wilq")
  fi
  (
    cd "$ROOT_DIR"
    setsid uv run python -m uvicorn apps.api.wilq_api.main:app --host "$API_HOST" --port "$API_PORT" \
      "${reload_args[@]}" \
      >>"$log" 2>&1 </dev/null &
    echo "$!" >"$(pid_file api)"
  )
  record_service_port api "$API_PORT"
  wait_url "${API_URL}/api/health" "$log"
  echo "API ready: ${API_URL}"
}

start_dashboard() {
  local log
  local managed_port
  local managed_url
  local pid
  log="$(log_file dashboard)"
  managed_port="$(runtime_service_port dashboard "$DASHBOARD_PORT")"
  managed_url="http://${DASHBOARD_HOST}:${managed_port}"
  pid="$(read_pid dashboard)"
  if is_pid_alive "$pid" && [ "$managed_port" != "$DASHBOARD_PORT" ]; then
    if curl -fsS --max-time 2 "${managed_url}/command-center" >/dev/null 2>&1; then
      echo "Dashboard already ready: ${managed_url}/command-center"
      return 0
    fi
    echo "Managed dashboard pid ${pid} exists on port ${managed_port} but is not ready. Run restart." >&2
    return 1
  fi
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
  record_service_port dashboard "$DASHBOARD_PORT"
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
  if [ "$service" = "api" ]; then
    printf "  reload_mode: %s\n" "$(if [ "$API_RELOAD" = "1" ]; then echo enabled; else echo disabled; fi)"
  fi
  printf "  ready: %s\n" "$(if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then echo yes; else echo no; fi)"
}

status_stack() {
  local api_port
  local dashboard_port
  api_port="$(runtime_service_port api "$API_PORT")"
  dashboard_port="$(runtime_service_port dashboard "$DASHBOARD_PORT")"
  status_service api "$api_port" "http://${API_HOST}:${api_port}/api/health"
  status_service dashboard "$dashboard_port" "http://${DASHBOARD_HOST}:${dashboard_port}/command-center"
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
