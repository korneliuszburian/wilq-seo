from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def validate_content_decision_queue(
    content_diagnostics: dict[str, Any],
    *,
    content_action_id: str,
    decision_types: set[str],
    assert_url_keys: Callable[[dict[str, Any], str], None],
) -> None:
    decisions = content_diagnostics.get("decision_queue", [])
    if not decisions or not all(isinstance(item, dict) for item in decisions):
        raise SystemExit("Content diagnostics decision_queue must contain objects")
    action_ids = set(content_diagnostics.get("action_ids") or [])
    if content_action_id not in action_ids:
        raise SystemExit(f"Content diagnostics missing {content_action_id}")
    live = bool(content_diagnostics.get("live_data_available"))
    if not live and int(content_diagnostics.get("query_page_count") or 0) == 0:
        if not any(
            item.get("decision_type") == "block_until_vendor_read"
            and item.get("status") == "blocked"
            for item in decisions
        ):
            raise SystemExit(
                "Content diagnostics must expose blocked vendor-read decision "
                "without live content facts"
            )
    elif not any(item.get("decision_type") in decision_types for item in decisions):
        raise SystemExit("Content decision_queue lacks content planning decision safe for review")
    for decision in decisions:
        assert_url_keys(decision, "Content decision_queue")
        if not decision.get("evidence_ids"):
            raise SystemExit("Content decision_queue item lacks evidence IDs")
        decision_action_ids = set(decision.get("action_ids") or [])
        decision_type = decision.get("decision_type")
        if not decision_action_ids and decision_type != "review_ahrefs_gap_records":
            raise SystemExit("Content decision_queue item lacks action ID")
        if decision_type == "review_ahrefs_gap_records" and decision_action_ids:
            raise SystemExit("Ahrefs-only content decision must not invent an action ID")
        if decision_type in decision_types and decision_type != "review_ahrefs_gap_records":
            if content_action_id not in decision_action_ids:
                raise SystemExit("Content planning decision lacks content action ID")
            if not decision.get("blocked_claims"):
                raise SystemExit("Content decision_queue item lacks blocked claims")
            for field in ("source_public_url", "final_canonical_url", "intended_final_url"):
                if field not in decision:
                    raise SystemExit(f"Content planning decision lacks {field}")
            if "ekologus.dev.proudsite.pl" in str(decision.get("final_canonical_url") or ""):
                raise SystemExit("Content final_canonical_url must not point to dev preview")


def validate_wordpress_draft_handoff_action_preview(
    active_actions: Any, *, assert_url_keys: Callable[[dict[str, Any], str], None]
) -> None:
    if not isinstance(active_actions, list):
        raise SystemExit("Context pack active_action_objects must be a list")
    action = next(
        (
            item
            for item in active_actions
            if isinstance(item, dict) and item.get("id") == "act_prepare_wordpress_draft_handoff"
        ),
        None,
    )
    if action is None:
        return
    if not isinstance(action, dict):
        raise SystemExit("WordPress draft handoff action must be an object")
    payload = action.get("payload")
    if payload is None:
        _validate_preview_cards(action.get("preview_cards"))
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
    first = next((item for item in previews or [] if isinstance(item, dict)), None)
    if not isinstance(previews, list) or not previews or not isinstance(first, dict):
        raise SystemExit("WordPress draft handoff action lacks payload_preview")
    assert_url_keys(first, "WordPress draft handoff context-pack preview")
    plan = first.get("post_publication_measurement_plan")
    if not isinstance(plan, dict):
        raise SystemExit("WordPress draft handoff preview lacks post_publication_measurement_plan")
    if (
        plan.get("contract_version") != "post_publication_measurement_plan_v1"
        or plan.get("scope") != "blocked_preview_only"
    ):
        raise SystemExit("Post-publication measurement plan has invalid blocked-preview contract")
    required = set(plan.get("required_source_connectors") or [])
    if not {"google_search_console", "google_analytics_4"}.issubset(required):
        raise SystemExit("Post-publication measurement plan must require GSC and GA4 evidence")
    if not {"ranking_gain_claim", "obietnica wzrostu leadów"}.issubset(
        set(plan.get("blocked_outputs") or [])
    ):
        raise SystemExit(
            "Post-publication measurement plan must block lead growth and ranking claims"
        )


def _validate_preview_cards(cards: Any) -> None:
    if not isinstance(cards, list) or not cards:
        raise SystemExit("WordPress draft handoff context-pack lacks preview cards")
    card_text = json.dumps(
        [
            {
                key: card.get(key)
                for key in ("title_label", "subtitle_label", "status_label", "rows")
            }
            for card in cards
            if isinstance(card, dict)
        ],
        ensure_ascii=False,
    )
    for required in (
        "Szkic WordPress do sprawdzenia",
        "URL publiczny",
        "URL kanoniczny",
        "zapis zmian zablokowany",
    ):
        if required not in card_text:
            raise SystemExit(f"WordPress draft handoff context-pack preview lacks {required!r}")
    for forbidden in (
        "candidate_id",
        "wordpress_draft_handoff_preview_v1",
        "wordpress_draft_handoff_review",
    ):
        if forbidden in card_text:
            raise SystemExit(
                "WordPress draft handoff context-pack preview exposes "
                f"technical marker {forbidden!r}"
            )
