#!/usr/bin/env bash
# Usage: scripts/status_snapshot.sh
#
# Jeden punkt widzenia stanu WILQ: git, testy, Beady, API i audit.
# To narzędzie do widzenia stanu dla marketera/ownera, nie nowy ekran.
# Nie uruchamia pełnego verify.sh (koszt); pokazuje ostatni znany wynik
# i bieżące sygnały z repozytorium i API.
set -euo pipefail

API_BASE="${WILQ_HEALTH_BASE_URL:-http://127.0.0.1:8000}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
curl_timeout="--max-time 5"

echo "== WILQ status snapshot: $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
echo

echo "--- git ---"
git -C "$ROOT_DIR" log -1 --format="commit %h | %ci | %s" 2>/dev/null || echo "brak gita"
ahead="$(git -C "$ROOT_DIR" rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
dirty="$(git -C "$ROOT_DIR" status --porcelain 2>/dev/null | grep -cv '^??')" || true
untracked="$(git -C "$ROOT_DIR" status --porcelain 2>/dev/null | grep -c '^??')" || true
echo "ahead of origin/main: ${ahead} | tracked-dirty: ${dirty} | untracked: ${untracked}"
echo

echo "--- Beady (otwarte wg stanu) ---"
uv run python - "$ROOT_DIR" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
issues_path = root / ".beads" / "issues.jsonl"
if not issues_path.exists():
    print("brak pliku .beads/issues.jsonl")
    sys.exit(0)
counts = {"open": 0, "in_progress": 0, "blocked": 0, "deferred": 0, "closed": 0}
p0_open = []
for line in issues_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    try:
        issue = json.loads(line)
    except json.JSONDecodeError:
        continue
    status = issue.get("status", "open")
    counts[status] = counts.get(status, 0) + 1
    if status == "open" and issue.get("priority") == 0:
        p0_open.append(issue.get("id", "?"))
print("open=%d in_progress=%d blocked=%d deferred=%d closed=%d" % (
    counts["open"], counts["in_progress"], counts["blocked"], counts["deferred"], counts["closed"]))
print("open P0: %s" % (", ".join(p0_open) if p0_open else "brak"))
PY
echo

echo "--- API ---"
for endpoint in /api/health /api/system/status /api/jobs/status /api/connectors; do
  code="$(curl $curl_timeout -sS -o /dev/null -w '%{http_code}' "${API_BASE}${endpoint}" 2>/dev/null || echo "ERR")"
  echo "${endpoint}: ${code}"
done
echo

echo "--- testy (ostatni znany pełny przebieg) ---"
last_verify="$(ls -t "$ROOT_DIR"/.local-lab/verify-last.log 2>/dev/null | head -1 || true)"
if [ -n "$last_verify" ]; then
  tail -3 "$last_verify"
else
  echo "brak .local-lab/verify-last.log — uruchom scripts/verify.sh i zapisz wynik jako .local-lab/verify-last.log"
fi
echo

echo "--- audit infra ---"
grep -E "^\| L[0-9]+ \|" "$ROOT_DIR/docs/architecture/production-readiness-audit.md" 2>/dev/null \
  | sed -E 's/\| ([A-Z0-9]+) \| ([^|]+) \| ([^|]+) \|.*/\1: \2 -> \3/' | head -12 || echo "brak auditu"
