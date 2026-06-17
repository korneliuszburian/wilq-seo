#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
ACTION_ID="${ACTION_ID:-act_configure_google_ads_env}"

uv run python - "$API_BASE" "$ACTION_ID" <<'PY'
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


api_base = sys.argv[1].rstrip("/")
action_id = sys.argv[2]


def request_json(path: str, method: str = "GET") -> object:
    request = urllib.request.Request(f"{api_base}{path}", method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {path} failed: HTTP {error.code}: {body}") from error


before_action = request_json(f"/api/actions/{action_id}")
before_audit = request_json(f"/api/audit/events?action_id={action_id}")
validation = request_json(f"/api/actions/{action_id}/validate", method="POST")
after_action = request_json(f"/api/actions/{action_id}")
after_audit = request_json(f"/api/audit/events?action_id={action_id}")

if not isinstance(before_action, dict) or not isinstance(after_action, dict):
    raise SystemExit("Action detail response is not an object.")
if not isinstance(validation, dict):
    raise SystemExit("Validation response is not an object.")
if not isinstance(before_audit, list) or not isinstance(after_audit, list):
    raise SystemExit("Audit event response is not a list.")

expected_evidence = before_action.get("evidence_ids")
if not expected_evidence:
    raise SystemExit("ActionObject has no evidence IDs.")
if validation.get("action_id") != action_id:
    raise SystemExit("Validation response returned a different action ID.")
if validation.get("valid") is not True:
    raise SystemExit(f"Action validation did not pass: {validation}")
if validation.get("status") != "valid":
    raise SystemExit(f"Unexpected validation status: {validation.get('status')}")
if after_action.get("validation_status") != "valid":
    raise SystemExit("ActionObject validation_status was not updated to valid.")
if after_action.get("status") not in {"ready", "ready_to_apply"}:
    raise SystemExit(f"Unexpected post-validation action status: {after_action.get('status')}")
if after_action.get("evidence_ids") != expected_evidence:
    raise SystemExit("Validation changed ActionObject evidence IDs.")
if len(after_audit) != len(before_audit):
    raise SystemExit("Validation created an audit event; audit should be reserved for apply/write.")

print(
    json.dumps(
        {
            "action_id": action_id,
            "api_base": api_base,
            "before_status": before_action.get("status"),
            "after_status": after_action.get("status"),
            "validation_status": after_action.get("validation_status"),
            "valid": validation.get("valid"),
            "evidence_ids": after_action.get("evidence_ids"),
            "audit_events_before": len(before_audit),
            "audit_events_after": len(after_audit),
            "apply_attempted": False,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
)
PY
