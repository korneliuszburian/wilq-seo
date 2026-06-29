#!/usr/bin/env bash
set -euo pipefail

api_base="${WILQ_API_BASE:-http://127.0.0.1:8000}"

usage() {
  cat <<'EOF'
Usage:
  scripts/eval_marketing_brief.sh [--api-base URL]

Checks /api/marketing/brief without running Codex. This is a fast deterministic
gate for the Polish marketer-facing brief contract.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --api-base)
      api_base="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

uv run python - "$api_base" <<'PY'
from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from typing import Any

api_base = sys.argv[1].rstrip("/")
required_sections = {
    "what_we_know",
    "what_blocks_us",
    "safe_next_actions",
    "recommended_focus",
}
required_diacritics = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
secret_markers = re.compile(
    r"(ya29\.|gho_|sk-[A-Za-z0-9]|Bearer\s+|refresh-token|GOOGLE_ADS_REFRESH_TOKEN=)"
)


def request_json(path: str) -> Any:
    request = urllib.request.Request(f"{api_base}{path}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def collect_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        texts: list[str] = []
        for item in value:
            texts.extend(collect_text(item))
        return texts
    if isinstance(value, dict):
        texts = []
        for item in value.values():
            texts.extend(collect_text(item))
        return texts
    return []


def normalize_for_marker_check(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    ).replace("ł", "l")


health = request_json("/api/health")
if health.get("status") != "ok":
    raise SystemExit(f"/api/health returned non-ok status: {health!r}")

brief = request_json("/api/marketing/brief")
errors: list[str] = []

if brief.get("language") != "pl-PL":
    errors.append(f"language must be pl-PL, got {brief.get('language')!r}")

instruction = normalize_for_marker_check(str(brief.get("strict_instruction", "")))
if "metryk" not in instruction or "dowod" not in instruction or "zrodl" not in instruction:
    errors.append("strict_instruction musi wymagać metryk i dowodów źródłowych")

sections = brief.get("sections")
if not isinstance(sections, list):
    errors.append("sections must be a list")
    sections = []

section_ids = {section.get("id") for section in sections if isinstance(section, dict)}
missing_sections = sorted(required_sections - section_ids)
if missing_sections:
    errors.append(f"missing sections: {', '.join(missing_sections)}")

items = [
    item
    for section in sections
    if isinstance(section, dict)
    for item in section.get("items", [])
    if isinstance(item, dict)
]
if not items:
    errors.append("marketing brief must contain at least one item")

if not brief.get("evidence_ids"):
    errors.append("marketing brief must expose evidence_ids")

action_ids = brief.get("action_ids") or []
if not action_ids:
    errors.append("marketing brief must expose safe action_ids")
elif not any(
    str(action_id).startswith(("act_prepare_", "act_review_", "act_configure_"))
    for action_id in action_ids
):
    errors.append("marketing brief action_ids must expose safe prepare/review/configure actions")

for item in items:
    item_id = item.get("id", "<missing>")
    if item.get("kind") not in {"metric", "blocker", "action", "recommendation"}:
        errors.append(f"{item_id}: invalid kind {item.get('kind')!r}")
    if not item.get("source_connectors"):
        errors.append(f"{item_id}: missing source_connectors")
    if not item.get("evidence_ids"):
        errors.append(f"{item_id}: missing evidence_ids")
    if item.get("kind") == "recommendation" and not item.get("blocker_reason"):
        if not item.get("metric_facts") and not item.get("evidence_ids"):
            errors.append(f"{item_id}: recommendation lacks metric/evidence support")

texts = " ".join(collect_text(brief))
if not required_diacritics.search(texts):
    errors.append("brief has no Polish diacritics in operator-facing text")
if secret_markers.search(texts):
    errors.append("brief appears to contain secret-like marker")

if errors:
    raise SystemExit("; ".join(errors))

summary = {
    "api_base": api_base,
    "language": brief["language"],
    "section_ids": [section.get("id") for section in sections],
    "item_count": len(items),
    "evidence_count": len(brief.get("evidence_ids") or []),
    "action_ids": brief.get("action_ids") or [],
    "blocker_count": brief.get("blocker_count"),
    "recommendation_count": brief.get("recommendation_count"),
}
print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
PY
