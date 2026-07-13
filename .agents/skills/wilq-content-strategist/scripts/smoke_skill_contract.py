#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from content_action_preview import assert_current_content_url_keys, validate_content_action_preview

from scripts.skill_smoke_harness import has_polish_metric_source_guardrails, request_json

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
WORDPRESS_DRAFT_HANDOFF_ACTION_ID = "act_prepare_wordpress_draft_handoff"
CONTENT_ACTION_DECISION_TYPES = {
    "block_until_vendor_read",
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "review_ahrefs_gap_records",
}
CURRENT_CONTENT_URL_KEYS = frozenset(
    {
        "source_public_url",
        "final_canonical_url",
        "intended_final_url",
        "preview_url",
    }
)
MARKETER_FACING_JARGON = ("action",)


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    args = parser.parse_args()

    health = request_json(
        args.api_base,
        "GET",
        "/api/health",
        timeout_seconds=args.timeout_seconds,
    )
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    pack = request_json(
        args.api_base,
        "POST",
        "/api/codex/context-pack",
        {"skill": SKILL_NAME},
        timeout_seconds=args.timeout_seconds,
    )
    missing = sorted(REQUIRED_CONTEXT_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")
    validate_context_pack_condensation(pack)

    content_diagnostics = request_json(
        args.api_base,
        "GET",
        "/api/content/diagnostics",
        timeout_seconds=args.timeout_seconds,
    )
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
        content_action_id=CONTENT_ACTION_ID,
        require_preview=require_content_preview,
    )
    validate_wordpress_draft_handoff_action_preview(pack.get("active_action_objects"))

    action_validations = []
    for action_id in content_diagnostics.get("action_ids", []):
        quoted_action = urllib.parse.quote(str(action_id), safe="")
        validation = request_json(
            args.api_base,
            "POST",
            f"/api/actions/{quoted_action}/validate",
            timeout_seconds=args.timeout_seconds,
        )
        action_validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"Content action validation failed: {validation}")

    brief = request_json(
        args.api_base,
        "GET",
        "/api/marketing/brief",
        timeout_seconds=args.timeout_seconds,
    )
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
        if any(connector in REQUIRED_CONNECTORS for connector in item.get("source_connectors", []))
    ][:8]

    connector_results = []
    for connector in REQUIRED_CONNECTORS:
        quoted = urllib.parse.quote(connector, safe="")
        status = request_json(
            args.api_base,
            "GET",
            f"/api/connectors/{quoted}/status",
            timeout_seconds=args.timeout_seconds,
        )
        connector_results.append(
            {
                "id": status.get("id"),
                "status": status.get("status"),
                "configured": status.get("configured"),
                "missing_credentials": status.get("missing_credentials", []),
                "error": status.get("error"),
            }
        )

    instruction = str(pack.get("strict_instruction", ""))
    if not has_polish_metric_source_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )

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
                    "content_domain_marker": "ekologus.pl",
                    "measurement_blocker_label": "problem pomiaru, nie temat treści",
                    "required_gate_markers": [
                        "inventory_check_before_create",
                        "merge_create_after_inventory_check",
                    ],
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
                        section.get("id") for section in content_diagnostics.get("sections", [])
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
        raise SystemExit("Content decision_queue lacks content planning decision safe for review")
    for decision in decision_queue:
        if not isinstance(decision, dict):
            continue
        if not decision.get("evidence_ids"):
            raise SystemExit("Content decision_queue item lacks evidence IDs")
        decision_action_ids = set(decision.get("action_ids") or [])
        if not decision_action_ids and decision.get("decision_type") != "review_ahrefs_gap_records":
            raise SystemExit("Content decision_queue item lacks action ID")
        if decision.get("decision_type") == "review_ahrefs_gap_records" and decision_action_ids:
            raise SystemExit("Ahrefs-only content decision must not invent an action ID")
        if (
            decision.get("decision_type") in CONTENT_ACTION_DECISION_TYPES
            and decision.get("decision_type") != "review_ahrefs_gap_records"
            and CONTENT_ACTION_ID not in decision_action_ids
        ):
            raise SystemExit("Content planning decision lacks content action ID")
        if not decision.get("blocked_claims"):
            raise SystemExit("Content decision_queue item lacks blocked claims")
        if decision.get("decision_type") in CONTENT_ACTION_DECISION_TYPES:
            for field in (
                "source_public_url",
                "final_canonical_url",
                "intended_final_url",
            ):
                if field not in decision:
                    raise SystemExit(f"Content planning decision lacks {field}")
            final_url = str(decision.get("final_canonical_url") or "")
            if "ekologus.dev.proudsite.pl" in final_url:
                raise SystemExit("Content final_canonical_url must not point to dev preview")


def validate_content_operator_summary(content_diagnostics: dict[str, Any]) -> None:
    summary = content_diagnostics.get("operator_summary")
    if not isinstance(summary, dict):
        raise SystemExit("Content diagnostics lacks operator_summary")
    assert_current_content_url_keys(summary, "Content operator_summary")
    jargon_fields = ("title", "summary", "next_step")
    jargon_hits = [
        field
        for field in jargon_fields
        if any(term in str(summary.get(field, "")) for term in MARKETER_FACING_JARGON)
    ]
    if jargon_hits:
        raise SystemExit(
            "Content operator_summary exposes internal jargon in marketer-facing fields: "
            + ", ".join(jargon_hits)
        )
    for decision in content_diagnostics.get("decision_queue", []):
        if not isinstance(decision, dict):
            continue
        assert_current_content_url_keys(decision, "Content decision_queue")


def validate_wordpress_draft_handoff_action_preview(active_actions: Any) -> None:
    if not isinstance(active_actions, list):
        raise SystemExit("Context pack active_action_objects must be a list")
    wordpress_draft_action = next(
        (
            action
            for action in active_actions
            if isinstance(action, dict) and action.get("id") == WORDPRESS_DRAFT_HANDOFF_ACTION_ID
        ),
        None,
    )
    if wordpress_draft_action is None:
        return
    if not isinstance(wordpress_draft_action, dict):
        raise SystemExit("WordPress draft handoff action must be an object")
    payload = wordpress_draft_action.get("payload")
    if payload is None:
        preview_cards = wordpress_draft_action.get("preview_cards")
        if not isinstance(preview_cards, list) or not preview_cards:
            raise SystemExit("WordPress draft handoff context-pack lacks preview cards")
        card_text = json.dumps(
            [
                {
                    "title_label": card.get("title_label"),
                    "subtitle_label": card.get("subtitle_label"),
                    "status_label": card.get("status_label"),
                    "rows": card.get("rows"),
                }
                for card in preview_cards
                if isinstance(card, dict)
            ],
            ensure_ascii=False,
        )
        for required_label in (
            "Szkic WordPress do sprawdzenia",
            "URL publiczny",
            "URL kanoniczny",
            "zapis zmian zablokowany",
        ):
            if required_label not in card_text:
                raise SystemExit(
                    f"WordPress draft handoff context-pack preview lacks {required_label!r}"
                )
        for forbidden_marker in (
            "candidate_id",
            "wordpress_draft_handoff_preview_v1",
            "wordpress_draft_handoff_review",
        ):
            if forbidden_marker in card_text:
                raise SystemExit(
                    "WordPress draft handoff context-pack preview exposes "
                    f"technical marker {forbidden_marker!r}"
                )
        return
    if not isinstance(payload, dict):
        raise SystemExit("WordPress draft handoff action payload must be an object")
    if "post_publication_measurement_plan_v1" not in set(
        payload.get("required_input_contracts") or []
    ):
        raise SystemExit(
            "WordPress draft handoff action must require post_publication_measurement_plan_v1"
        )
    previews = payload.get("payload_preview")
    if not isinstance(previews, list) or not previews:
        raise SystemExit("WordPress draft handoff action lacks payload_preview")
    first_preview = next((item for item in previews if isinstance(item, dict)), None)
    if not isinstance(first_preview, dict):
        raise SystemExit("WordPress draft handoff change preview must be an object")
    assert_current_content_url_keys(first_preview, "WordPress draft handoff context-pack preview")
    measurement_plan = first_preview.get("post_publication_measurement_plan")
    if not isinstance(measurement_plan, dict):
        raise SystemExit("WordPress draft handoff preview lacks post_publication_measurement_plan")
    if measurement_plan.get("contract_version") != "post_publication_measurement_plan_v1":
        raise SystemExit("Post-publication measurement plan has invalid contract")
    if measurement_plan.get("scope") != "blocked_preview_only":
        raise SystemExit("Post-publication measurement plan must be blocked_preview_only")
    if "google_search_console" not in set(measurement_plan.get("required_source_connectors") or []):
        raise SystemExit("Post-publication measurement plan must require GSC evidence")
    if "google_analytics_4" not in set(measurement_plan.get("required_source_connectors") or []):
        raise SystemExit("Post-publication measurement plan must require GA4 evidence")
    blocked_outputs = set(measurement_plan.get("blocked_outputs") or [])
    if not {"ranking_gain_claim", "obietnica wzrostu leadów"}.issubset(blocked_outputs):
        raise SystemExit(
            "Post-publication measurement plan must block lead growth and ranking claims"
        )


def validate_context_pack_condensation(pack: dict[str, Any]) -> None:
    compaction = pack.get("context_pack_compaction")
    if not isinstance(compaction, dict):
        raise SystemExit("Context pack must expose compaction metadata")
    required_flags = {
        "connector_refresh_runs_compacted",
        "evidence_summaries_compacted",
        "knowledge_card_summaries_compacted",
        "raw_history_omitted",
    }
    missing_flags = sorted(flag for flag in required_flags if compaction.get(flag) is not True)
    if missing_flags:
        raise SystemExit(
            "Context pack compaction is missing required flags: " + ", ".join(missing_flags)
        )
    operator_context = {
        "connector_status": pack.get("connector_status"),
        "connector_refresh_runs": pack.get("connector_refresh_runs"),
        "evidence_summaries": pack.get("evidence_summaries"),
        "knowledge_card_summaries": pack.get("knowledge_card_summaries"),
        "expert_rule_summaries": pack.get("expert_rule_summaries"),
        "active_action_objects": pack.get("active_action_objects"),
        "content_diagnostics_connectors": (pack.get("content_diagnostics") or {}).get("connectors"),
        "content_diagnostics_latest_refreshes": (pack.get("content_diagnostics") or {}).get(
            "latest_refreshes"
        ),
    }
    serialized = json.dumps(operator_context, ensure_ascii=False)
    forbidden_terms = (
        "vendor_read",
        "Read-only",
        "read-only",
        "review-only",
        "ActionObject",
    )
    leaked_terms = [term for term in forbidden_terms if term in serialized]
    if leaked_terms:
        raise SystemExit(
            "Context pack leaked raw history or technical wording: " + ", ".join(leaked_terms)
        )


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
