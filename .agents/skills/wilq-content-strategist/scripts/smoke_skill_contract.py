#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-content-strategist"
REQUIRED_CONNECTORS = [
    "google_search_console",
    "google_analytics_4",
    "ahrefs",
    "wordpress_ekologus",
    "wordpress_sklep",
]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "content_diagnostics",
}
CONTENT_ACTION_ID = "act_prepare_content_refresh_queue"
CONTENT_ACTION_DECISION_TYPES = {
    "block_until_vendor_read",
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "review_ahrefs_gap_records",
}


def request_json(api_base: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
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

    content_diagnostics = request_json(args.api_base, "GET", "/api/content/diagnostics")
    if content_diagnostics.get("language") != "pl-PL":
        raise SystemExit("Content diagnostics language must be pl-PL")
    sections = content_diagnostics.get("sections")
    if not isinstance(sections, list) or not sections:
        raise SystemExit("Content diagnostics must expose sections")
    if pack.get("content_diagnostics", {}).get("evidence_ids") != content_diagnostics.get(
        "evidence_ids"
    ):
        raise SystemExit("Context pack content_diagnostics evidence IDs differ from endpoint")
    if pack.get("content_diagnostics", {}).get("action_ids") != content_diagnostics.get(
        "action_ids"
    ):
        raise SystemExit("Context pack content_diagnostics action IDs differ from endpoint")
    if decision_trace(pack.get("content_diagnostics", {}).get("decision_queue")) != decision_trace(
        content_diagnostics.get("decision_queue")
    ):
        raise SystemExit("Context pack content_diagnostics decision_queue differs from endpoint")
    decision_queue = content_diagnostics.get("decision_queue", [])
    validate_content_decision_queue(content_diagnostics)
    validate_content_operator_summary(content_diagnostics)
    require_content_preview = bool(
        content_diagnostics.get("live_data_available") and decision_queue
    )
    content_brief_preview = validate_content_action_preview(
        pack.get("active_action_objects"),
        require_preview=require_content_preview,
    )

    action_validations = []
    for action_id in content_diagnostics.get("action_ids", []):
        quoted_action = urllib.parse.quote(str(action_id), safe="")
        validation = request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")
        action_validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"Content ActionObject validation failed: {validation}")

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
                "brief_items": brief_items,
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "content_diagnostics": {
                    "live_data_available": content_diagnostics.get("live_data_available"),
                    "query_page_count": content_diagnostics.get("query_page_count"),
                    "matched_inventory_count": content_diagnostics.get("matched_inventory_count"),
                    "blocker_count": content_diagnostics.get("blocker_count"),
                    "operator_summary": content_diagnostics.get("operator_summary", {}),
                    "decision_queue": decision_queue,
                    "decision_types": [
                        item.get("decision_type")
                        for item in decision_queue
                        if isinstance(item, dict)
                    ],
                    "section_ids": [
                        section.get("id")
                        for section in content_diagnostics.get("sections", [])
                    ],
                    "evidence_ids": content_diagnostics.get("evidence_ids", [])[:20],
                    "action_ids": content_diagnostics.get("action_ids", []),
                    "content_brief_preview_type": "content_brief_preview_v1",
                    "content_brief_preview": content_brief_preview,
                    "tactical_item_ids": [
                        item.get("id")
                        for section in content_diagnostics.get("sections", [])
                        for item in section.get("tactical_items", [])
                        if item.get("id")
                    ][:20],
                    "blocked_claims": [
                        claim
                        for section in content_diagnostics.get("sections", [])
                        for claim in section.get("blocked_claims", [])
                    ][:20],
                },
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
                "action_validations": action_validations,
                "action_ids": [
                    item.get("id")
                    for item in (pack.get("active_action_objects") or [])
                    if item.get("id")
                ][:20],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def validate_content_decision_queue(content_diagnostics: dict[str, Any]) -> None:
    decision_queue = content_diagnostics.get("decision_queue", [])
    live_data_available = bool(content_diagnostics.get("live_data_available"))
    query_page_count = int(content_diagnostics.get("query_page_count") or 0)
    if not decision_queue:
        raise SystemExit("Content diagnostics decision_queue is empty")
    if not all(isinstance(item, dict) for item in decision_queue):
        raise SystemExit("Content diagnostics decision_queue must contain objects")
    action_ids = set(content_diagnostics.get("action_ids") or [])
    if CONTENT_ACTION_ID not in action_ids:
        raise SystemExit(f"Content diagnostics missing {CONTENT_ACTION_ID}")
    if not live_data_available and query_page_count == 0:
        if not any(
            decision.get("decision_type") == "block_until_vendor_read"
            and decision.get("status") == "blocked"
            for decision in decision_queue
        ):
            raise SystemExit(
                "Content diagnostics must expose blocked vendor-read decision "
                "without live content facts"
            )
    elif not any(
        decision.get("decision_type") in CONTENT_ACTION_DECISION_TYPES
        for decision in decision_queue
    ):
        raise SystemExit("Content decision_queue lacks review-safe content planning decision")
    for decision in decision_queue:
        if not isinstance(decision, dict):
            continue
        if not decision.get("evidence_ids"):
            raise SystemExit("Content decision_queue item lacks evidence IDs")
        decision_action_ids = set(decision.get("action_ids") or [])
        if not decision_action_ids:
            raise SystemExit("Content decision_queue item lacks ActionObject ID")
        if (
            decision.get("decision_type") in CONTENT_ACTION_DECISION_TYPES
            and CONTENT_ACTION_ID not in decision_action_ids
        ):
            raise SystemExit("Content planning decision lacks content ActionObject ID")
        if not decision.get("blocked_claims"):
            raise SystemExit("Content decision_queue item lacks blocked claims")


def validate_content_operator_summary(content_diagnostics: dict[str, Any]) -> None:
    summary = content_diagnostics.get("operator_summary")
    if not isinstance(summary, dict):
        raise SystemExit("Content diagnostics lacks operator_summary")
    decisions = [
        item
        for item in content_diagnostics.get("decision_queue", [])
        if isinstance(item, dict)
    ]
    expected_confirmed = sum(
        1
        for decision in decisions
        if decision.get("target_site_migration_candidate_inventory_status")
        == "confirmed_target_inventory"
    )
    expected_missing = sum(
        1
        for decision in decisions
        if decision.get("target_site_migration_candidate_inventory_status")
        == "missing_target_inventory"
    )
    if summary.get("target_site_confirmed_candidate_inventory_count") != expected_confirmed:
        raise SystemExit(
            "Content operator_summary confirmed candidate inventory count differs from decision_queue"
        )
    if summary.get("target_site_missing_candidate_inventory_count") != expected_missing:
        raise SystemExit(
            "Content operator_summary missing candidate inventory count differs from decision_queue"
        )


def validate_content_action_preview(
    active_actions: Any,
    *,
    require_preview: bool,
) -> list[dict[str, Any]]:
    if not isinstance(active_actions, list):
        raise SystemExit("Context pack active_action_objects must be a list")
    content_action = next(
        (
            action
            for action in active_actions
            if isinstance(action, dict) and action.get("id") == CONTENT_ACTION_ID
        ),
        None,
    )
    if not isinstance(content_action, dict):
        raise SystemExit(f"Context pack missing active {CONTENT_ACTION_ID}")
    payload = content_action.get("payload")
    if not isinstance(payload, dict):
        raise SystemExit("Content ActionObject payload must be an object")
    previews = payload.get("content_brief_preview")
    if not require_preview and previews is None:
        return []
    if not isinstance(previews, list) or not previews:
        raise SystemExit("Content ActionObject lacks content_brief_preview")
    if int(payload.get("content_brief_preview_included") or 0) <= 0:
        raise SystemExit("Content ActionObject context omits content_brief_preview")
    first_preview = previews[0]
    if not isinstance(first_preview, dict):
        raise SystemExit("Content brief preview must be an object")
    if first_preview.get("apply_allowed") is not False:
        raise SystemExit("Content brief preview must keep apply_allowed=false")
    if first_preview.get("api_mutation_ready") is not False:
        raise SystemExit("Content brief preview must keep api_mutation_ready=false")
    if not first_preview.get("evidence_ids"):
        raise SystemExit("Content brief preview lacks evidence IDs")
    if "ranking guarantee" not in set(first_preview.get("blocked_claims") or []):
        raise SystemExit("Content brief preview must block ranking guarantee claims")
    required_string_fields = [
        "intent",
        "content_angle",
        "audience",
        "h1_direction",
        "seo_title_direction",
        "meta_description_direction",
        "schema_direction",
        "cta_direction",
        "publication_readiness_status",
        "inventory_gate_status",
        "canonical_gate_status",
        "duplicate_gate_status",
        "content_gate_summary",
    ]
    for field in required_string_fields:
        if not str(first_preview.get(field) or "").strip():
            raise SystemExit(f"Content brief preview lacks {field}")
    required_list_fields = [
        "key_objections",
        "h2_direction",
        "faq_direction",
        "internal_link_direction",
        "source_facts",
        "missing_evidence",
        "forbidden_claims",
        "legal_review_notes",
        "brand_voice_notes",
        "publication_blockers",
    ]
    for field in required_list_fields:
        value = first_preview.get(field)
        if not isinstance(value, list) or not value:
            raise SystemExit(f"Content brief preview lacks {field}")
    if "ranking guarantee" not in set(first_preview.get("forbidden_claims") or []):
        raise SystemExit("Content brief preview forbidden_claims must block ranking guarantee")
    if "target_site_migration_status" not in first_preview:
        raise SystemExit("Content brief preview lacks target_site_migration_status")
    if "target_site_migration_summary" not in first_preview:
        raise SystemExit("Content brief preview lacks target_site_migration_summary")
    if "target_site_migration_candidate_inventory_status" not in first_preview:
        raise SystemExit(
            "Content brief preview lacks target_site_migration_candidate_inventory_status"
        )
    if "target_site_migration_candidate_inventory_summary" not in first_preview:
        raise SystemExit(
            "Content brief preview lacks target_site_migration_candidate_inventory_summary"
        )
    if "target_site_alternative_candidate_urls" not in first_preview:
        raise SystemExit("Content brief preview lacks target_site_alternative_candidate_urls")
    if not isinstance(first_preview.get("target_site_alternative_candidate_urls"), list):
        raise SystemExit("Content brief preview target_site_alternative_candidate_urls must be a list")
    if "target_site_alternative_candidate_summary" not in first_preview:
        raise SystemExit("Content brief preview lacks target_site_alternative_candidate_summary")
    if "target_site_mapping_review_status" not in first_preview:
        raise SystemExit("Content brief preview lacks target_site_mapping_review_status")
    if "target_site_mapping_review_summary" not in first_preview:
        raise SystemExit("Content brief preview lacks target_site_mapping_review_summary")
    if "target_site_mapping_review_candidate_urls" not in first_preview:
        raise SystemExit("Content brief preview lacks target_site_mapping_review_candidate_urls")
    if not isinstance(first_preview.get("target_site_mapping_review_candidate_urls"), list):
        raise SystemExit("Content brief preview target_site_mapping_review_candidate_urls must be a list")
    requirements = first_preview.get("target_site_review_requirements")
    if not isinstance(requirements, list) or not requirements:
        raise SystemExit("Content brief preview lacks target_site_review_requirements")
    if "duplicate_or_cannibalization_check" not in set(requirements):
        raise SystemExit(
            "Content brief preview target_site_review_requirements must include duplicate_or_cannibalization_check"
        )
    gsc_preview = next(
        (
            item
            for item in previews
            if isinstance(item, dict) and item.get("source_type") == "gsc_query_page"
        ),
        None,
    )
    if isinstance(gsc_preview, dict):
        for field in (
            "source_url",
            "source_site_host",
            "target_site_adaptation_status",
        ):
            if not str(gsc_preview.get(field) or "").strip():
                raise SystemExit(f"GSC content brief preview lacks {field}")
        if gsc_preview.get("target_site_adaptation_status") != "needs_inventory_match":
            for field in ("target_site_url", "target_site_host"):
                if not str(gsc_preview.get(field) or "").strip():
                    raise SystemExit(f"GSC content brief preview lacks {field}")
        if gsc_preview.get("target_site_url") == "[REDACTED]":
            raise SystemExit("GSC content brief target_site_url must not be redacted")
        if "target_site_inventory_summary" not in gsc_preview:
            raise SystemExit("GSC content brief preview lacks target_site_inventory_summary")
        candidate_inventory_status = str(
            gsc_preview.get("target_site_migration_candidate_inventory_status") or ""
        )
        if candidate_inventory_status not in {
            "confirmed_target_inventory",
            "missing_target_inventory",
            "not_applicable",
        }:
            raise SystemExit(
                "GSC content brief preview has invalid target_site_migration_candidate_inventory_status"
            )
        inventory_missing = gsc_preview.get("target_site_inventory_missing_fields")
        canonical_url = str(gsc_preview.get("target_site_inventory_canonical_url") or "")
        canonical_missing = (
            isinstance(inventory_missing, list)
            and "canonical_url" in set(inventory_missing)
        )
        if not canonical_missing and not canonical_url:
            raise SystemExit(
                "GSC content brief preview must expose canonical_url or mark it missing"
            )
    return [
        {
            "topic": preview.get("topic"),
            "source_type": preview.get("source_type"),
            "content_angle": preview.get("content_angle"),
            "intent": preview.get("intent"),
            "audience": preview.get("audience"),
            "h1_direction": preview.get("h1_direction"),
            "seo_title_direction": preview.get("seo_title_direction"),
            "meta_description_direction": preview.get("meta_description_direction"),
            "h2_direction": (preview.get("h2_direction") or [])[:4],
            "faq_direction": (preview.get("faq_direction") or [])[:4],
            "schema_direction": preview.get("schema_direction"),
            "inventory_gate_status": preview.get("inventory_gate_status"),
            "canonical_gate_status": preview.get("canonical_gate_status"),
            "duplicate_gate_status": preview.get("duplicate_gate_status"),
            "content_gate_summary": preview.get("content_gate_summary"),
            "cta_direction": preview.get("cta_direction"),
            "publication_readiness_status": preview.get(
                "publication_readiness_status"
            ),
            "publication_blockers": (preview.get("publication_blockers") or [])[:6],
            "source_facts": (preview.get("source_facts") or [])[:4],
            "missing_evidence": (preview.get("missing_evidence") or [])[:3],
            "forbidden_claims": (preview.get("forbidden_claims") or [])[:6],
            "target_site_inventory_summary": preview.get(
                "target_site_inventory_summary"
            ),
            "target_site_migration_candidate_url": preview.get(
                "target_site_migration_candidate_url"
            ),
            "target_site_migration_candidate_inventory_status": preview.get(
                "target_site_migration_candidate_inventory_status"
            ),
            "target_site_migration_candidate_inventory_summary": preview.get(
                "target_site_migration_candidate_inventory_summary"
            ),
            "target_site_inventory_missing_fields": (
                preview.get("target_site_inventory_missing_fields") or []
            )[:6],
            "target_site_inventory_title_or_h1": preview.get(
                "target_site_inventory_title_or_h1"
            ),
            "target_site_inventory_canonical_url": preview.get(
                "target_site_inventory_canonical_url"
            ),
            "evidence_ids": (preview.get("evidence_ids") or [])[:5],
        }
        for preview in previews[:3]
        if isinstance(preview, dict)
    ]


def decision_trace(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [
        {
            "id": item.get("id"),
            "decision_type": item.get("decision_type"),
            "source_connectors": item.get("source_connectors", []),
            "evidence_ids": item.get("evidence_ids", []),
            "action_ids": item.get("action_ids", []),
        }
        for item in value
        if isinstance(item, dict)
    ]


if __name__ == "__main__":
    raise SystemExit(main())
