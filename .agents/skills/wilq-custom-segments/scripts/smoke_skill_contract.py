#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-custom-segments"
REQUIRED_CONNECTORS = ["google_ads", "google_search_console"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "ads_diagnostics",
}
CUSTOM_SEGMENT_ACTION_ID = "act_prepare_custom_segments_from_search_terms"


def request_json(api_base: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    health = request_json(args.api_base, "GET", "/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    pack = request_json(args.api_base, "POST", "/api/codex/context-pack", {"skill": SKILL_NAME})
    missing = sorted(REQUIRED_CONTEXT_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")

    ads_diagnostics = request_json(args.api_base, "GET", "/api/ads/diagnostics")
    if ads_diagnostics.get("language") != "pl-PL":
        raise SystemExit("Ads diagnostics language must be pl-PL")
    pack_ads_diagnostics = pack.get("ads_diagnostics") or {}
    if pack_ads_diagnostics.get("evidence_ids") != ads_diagnostics.get("evidence_ids"):
        raise SystemExit("Context pack ads_diagnostics evidence IDs differ from endpoint")
    pack_ads_action_ids = pack_ads_diagnostics.get("action_ids") or []
    if any(action_id != CUSTOM_SEGMENT_ACTION_ID for action_id in pack_ads_action_ids):
        raise SystemExit(
            "Context pack for custom segments must not expose campaign, recommendation, "
            "negative keyword or business-context actions"
        )
    active_action_ids = [
        item.get("id")
        for item in (pack.get("active_action_objects") or [])
        if item.get("id")
    ]
    if any(action_id != CUSTOM_SEGMENT_ACTION_ID for action_id in active_action_ids):
        raise SystemExit(
            "Active actions for custom segments must not include campaign, "
            "recommendation, negative keyword or business-context actions"
        )
    decision_ids = [
        item.get("id")
        for item in (pack_ads_diagnostics.get("decision_queue") or [])
        if item.get("id")
    ]
    if any(
        decision_id != "ads_prepare_custom_segments_from_search_terms"
        for decision_id in decision_ids
    ):
        raise SystemExit(
            "Context pack for custom segments must not expose campaign, recommendation, "
            "negative keyword or business-context decisions"
        )

    custom_segments_read_contract = ads_diagnostics.get("custom_segments_read_contract") or {}
    pack_custom_segments_read_contract = (
        pack_ads_diagnostics.get("custom_segments_read_contract") or {}
    )
    if pack_custom_segments_read_contract.get("id") != custom_segments_read_contract.get("id"):
        raise SystemExit("Context pack custom_segments_read_contract differs from endpoint")
    if custom_segments_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Custom segments read contract must be ready or blocked")
    if not custom_segments_read_contract.get("blocked_claims"):
        raise SystemExit("Custom segments read contract must expose blocked claims")
    audience_forecast_contract = (
        custom_segments_read_contract.get("audience_forecast_read_contract") or {}
    )
    if audience_forecast_contract.get("id") != (
        "ads_custom_segment_audience_forecast_read_contract"
    ):
        raise SystemExit("Custom segments must expose audience forecast read contract")
    if audience_forecast_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Audience forecast read contract must be ready or blocked")
    if "audience size" not in (audience_forecast_contract.get("blocked_claims") or []):
        raise SystemExit("Audience forecast contract must block audience-size claims")

    custom_segment_candidates = custom_segments_read_contract.get("candidates") or []
    custom_segment_action_validation: dict[str, Any] | None = None
    action_validations = []
    safety_review: dict[str, Any] = {}
    if custom_segment_candidates:
        if not audience_forecast_contract.get("forecast_rows"):
            raise SystemExit(
                "Ready custom segments contract must expose forecast blocker rows"
            )
        first_forecast_row = audience_forecast_contract["forecast_rows"][0]
        if first_forecast_row.get("status") != "missing_forecast":
            raise SystemExit("Audience forecast row must show missing forecast state")
        if first_forecast_row.get("forecast_available") is not False:
            raise SystemExit("Audience forecast row must keep forecast_available=false")
        if first_forecast_row.get("audience_size") is not None:
            raise SystemExit("Audience forecast row must not invent audience_size")
        first_candidate = custom_segment_candidates[0]
        if not first_candidate.get("source_terms"):
            raise SystemExit("Custom segment candidate must expose source_terms")
        if not first_candidate.get("evidence_ids"):
            raise SystemExit("Custom segment candidate must expose evidence_ids")
        if not first_candidate.get("payload_preview"):
            raise SystemExit("Custom segment candidate must expose payload_preview")
        if first_candidate.get("review_priority") not in {
            "pilne",
            "wysokie",
            "normalne",
            "niski sygnał",
        }:
            raise SystemExit("Custom segment candidate must expose review_priority")
        review_score = first_candidate.get("review_score")
        if not isinstance(review_score, int) or not 0 <= review_score <= 100:
            raise SystemExit("Custom segment candidate review_score must be 0-100")
        review_reason = str(first_candidate.get("review_reason") or "")
        if (
            "kolejność oceny segmentu" not in review_reason
            or "nie dowód rozmiaru odbiorców" not in review_reason
        ):
            raise SystemExit("Custom segment candidate must explain validation triage")
        if not first_candidate.get("human_review_gates"):
            raise SystemExit("Custom segment candidate must expose human_review_gates")
        if first_candidate["payload_preview"].get("apply_allowed") is not False:
            raise SystemExit("Custom segment change preview must keep apply_allowed=false")
        if "custom_segment_change_preview" in (
            custom_segments_read_contract.get("missing_read_contracts") or []
        ):
            raise SystemExit("Ready custom segments contract must not miss change preview")
        if not custom_segments_read_contract.get("payload_preview"):
            raise SystemExit("Ready custom segments contract must expose payload_preview")
        payload_preview = custom_segments_read_contract["payload_preview"][0]
        safety_review = payload_preview.get("safety_review") or {}
        if safety_review.get("safety_contract") != "custom_segment_apply_safety_v1":
            raise SystemExit(
                "Custom segment payload_preview must expose apply safety_review"
            )
        if safety_review.get("apply_allowed") is not False:
            raise SystemExit("Custom segment safety_review must keep apply blocked")
        if safety_review.get("api_mutation_ready") is not False:
            raise SystemExit(
                "Custom segment safety_review must keep api_mutation_ready=false"
            )
        if safety_review.get("audit_required") is not True:
            raise SystemExit("Custom segment safety_review must require mutation audit")
        missing_safety = set(safety_review.get("missing_requirements") or [])
        if "forecast_or_audience_size" not in missing_safety:
            raise SystemExit(
                "Custom segment safety_review must require forecast_or_audience_size"
            )
        if "google_ads_mutation_audit" not in missing_safety:
            raise SystemExit(
                "Custom segment safety_review must require google_ads_mutation_audit"
            )
        if CUSTOM_SEGMENT_ACTION_ID not in custom_segments_read_contract.get("action_ids", []):
            raise SystemExit(
                "Custom segments read contract must expose custom segment action"
            )
        if pack_ads_action_ids != [CUSTOM_SEGMENT_ACTION_ID]:
            raise SystemExit(
                "Ready custom segments context must expose custom segment action"
            )
        if active_action_ids != [CUSTOM_SEGMENT_ACTION_ID]:
            raise SystemExit(
                "Ready custom segments active actions must expose custom segment action"
            )
        if decision_ids != ["ads_prepare_custom_segments_from_search_terms"]:
            raise SystemExit(
                "Ready custom segments context must expose the custom segment decision"
            )
        custom_segment_action_validation = request_json(
            args.api_base,
            "POST",
            f"/api/actions/{CUSTOM_SEGMENT_ACTION_ID}/validate",
            {},
        )
        if custom_segment_action_validation.get("valid") is not True:
            raise SystemExit(
                "Custom segment action validation must pass when candidates exist"
            )
        action_validations.append(
            {
                "action_id": custom_segment_action_validation.get("action_id"),
                "valid": custom_segment_action_validation.get("valid"),
                "status": custom_segment_action_validation.get("status"),
                "errors": custom_segment_action_validation.get("errors", []),
            }
        )
    elif not custom_segments_read_contract.get("missing_read_contracts"):
        raise SystemExit("Blocked custom segments contract must list missing read contracts")

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    brief_items = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "kind": item.get("kind"),
            "source_connectors": item.get("source_connectors", []),
            "evidence_ids": item.get("evidence_ids", []),
            "action_ids": item.get("action_ids", []),
            "metric_facts": item.get("metric_facts", []),
        }
        for section in brief.get("sections", [])
        for item in section.get("items", [])
        if any(
            connector in REQUIRED_CONNECTORS
            for connector in item.get("source_connectors", [])
        )
    ][:8]

    connector_results = []
    for connector in REQUIRED_CONNECTORS:
        quoted = urllib.parse.quote(connector, safe="")
        status = request_json(args.api_base, "GET", f"/api/connectors/{quoted}/status")
        connector_results.append(
            {
                "id": status.get("id"),
                "status": status.get("status"),
                "configured": status.get("configured"),
                "missing_credentials": status.get("missing_credentials", []),
                "error": status.get("error"),
            }
        )

    instruction = str(pack.get("strict_instruction", "")).lower()
    if "must not invent metrics" not in instruction or "evidence" not in instruction:
        raise SystemExit("Context pack strict instruction does not include evidence guardrails")

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connector_results,
                "ads_diagnostics": {
                    "live_data_available": ads_diagnostics.get("live_data_available"),
                    "custom_segments_read_contract": {
                        "status": custom_segments_read_contract.get("status"),
                        "summary": custom_segments_read_contract.get("summary"),
                        "candidate_count": len(custom_segment_candidates),
                        "payload_preview_count": len(
                            custom_segments_read_contract.get("payload_preview") or []
                        ),
                        "apply_safety_review": {
                            "status": safety_review.get("status"),
                            "safety_contract": safety_review.get("safety_contract"),
                            "missing_requirements": safety_review.get(
                                "missing_requirements", []
                            ),
                            "audit_required": safety_review.get("audit_required"),
                            "apply_allowed": safety_review.get("apply_allowed"),
                        },
                        "missing_read_contracts": custom_segments_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "audience_forecast_read_contract": {
                            "status": audience_forecast_contract.get("status"),
                            "forecast_row_count": audience_forecast_contract.get(
                                "forecast_row_count"
                            ),
                            "missing_read_contracts": audience_forecast_contract.get(
                                "missing_read_contracts", []
                            ),
                            "blocked_claims": audience_forecast_contract.get(
                                "blocked_claims", []
                            ),
                        },
                        "blocked_claims": custom_segments_read_contract.get(
                            "blocked_claims", []
                        ),
                        "action_ids": custom_segments_read_contract.get("action_ids", []),
                    },
                    "decision_ids": [
                        item.get("id")
                        for item in ads_diagnostics.get("decision_queue", [])
                        if item.get("id")
                    ],
                    "section_ids": [
                        section.get("id")
                        for section in ads_diagnostics.get("sections", [])
                        if section.get("id")
                    ],
                },
                "custom_segment_candidates": [
                    {
                        "id": candidate.get("id"),
                        "name": candidate.get("name"),
                        "review_priority": candidate.get("review_priority"),
                        "review_score": candidate.get("review_score"),
                        "review_reason": candidate.get("review_reason"),
                        "human_review_gates": candidate.get("human_review_gates", []),
                        "source_terms": candidate.get("source_terms", []),
                        "confidence": candidate.get("confidence"),
                        "validation_status": candidate.get("validation_status"),
                        "evidence_ids": candidate.get("evidence_ids", []),
                    }
                    for candidate in custom_segment_candidates[:6]
                ],
                "custom_segment_action_validation": custom_segment_action_validation,
                "action_validations": action_validations,
                "brief_items": brief_items,
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "evidence_ids": [
                    item.get("id")
                    for item in (pack.get("evidence_summaries") or [])
                    if item.get("id")
                ][:20],
                "opportunity_ids": [
                    item.get("id")
                    for item in (pack.get("top_opportunities") or [])
                    if item.get("id")
                ][:20],
                "action_ids": [
                    item.get("id")
                    for item in (pack.get("active_action_objects") or [])
                    if item.get("id")
                ][:20],
                "context_decision_ids": decision_ids,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
