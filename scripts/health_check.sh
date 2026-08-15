#!/usr/bin/env bash
set -euo pipefail

health_base_url="${WILQ_HEALTH_BASE_URL:-http://127.0.0.1:8000}"
health_base_url="${health_base_url%/}"
curl_options=(--disable --globoff --fail --silent --show-error --max-time 10)
health_status_pattern='^[[:space:]]*\{[^{}]*"status"[[:space:]]*:[[:space:]]*"ok"[^{}]*\}[[:space:]]*$'

if ! health_payload="$(
  curl "${curl_options[@]}" --url "${health_base_url}/api/health" 2>/dev/null
)"; then
  echo "BŁĄD: /api/health nie odpowiada poprawnie." >&2
  exit 1
fi
if [[ ! "$health_payload" =~ $health_status_pattern ]]; then
  echo "BŁĄD: /api/health nie zwrócił statusu ok." >&2
  exit 1
fi

if ! system_status_code="$(
  curl "${curl_options[@]}" \
    --output /dev/null \
    --write-out "%{http_code}" \
    --url "${health_base_url}/api/system/status" \
    2>/dev/null
)"; then
  echo "BŁĄD: /api/system/status nie odpowiada poprawnie." >&2
  exit 1
fi
if [[ "$system_status_code" != "200" ]]; then
  echo "BŁĄD: /api/system/status nie zwrócił HTTP 200." >&2
  exit 1
fi

echo "OK: wymagane endpointy WILQ odpowiadają poprawnie."
