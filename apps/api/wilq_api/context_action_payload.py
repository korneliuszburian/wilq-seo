from __future__ import annotations

from typing import Any

from apps.api.wilq_api import context_action_previews, context_ads, context_compaction
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID


def compact_action_dump_for_context(action: dict[str, Any], *, skill: str) -> dict[str, Any]:
    compact = dict(action)
    if compact.get("id") == KEYWORD_PLANNER_ACCESS_ACTION_ID:
        compact["human_diagnosis"] = (
            "Wzbogacenie Keyword Planner jest zablokowane przez Google Ads API."
        )
        compact["recommended_reason"] = (
            "Odblokuj dostęp tokena deweloperskiego przed użyciem prognoz, "
            "rozmiaru odbiorców i twierdzeń opartych na Keyword Plannerze."
        )
        review_gate = compact.get("review_gate")
        if isinstance(review_gate, dict):
            apply_blockers = review_gate.get("apply_blockers")
            if not isinstance(apply_blockers, list):
                apply_blockers = []
            apply_blocker_labels = review_gate.get("apply_blocker_labels")
            if not isinstance(apply_blocker_labels, list):
                apply_blocker_labels = []
            compact["review_gate"] = {
                "status": review_gate.get("status"),
                "apply_allowed": review_gate.get("apply_allowed"),
                "confirmation_required": review_gate.get("confirmation_required"),
                "apply_blockers_total": len(apply_blockers),
                "apply_blocker_labels": apply_blocker_labels[:4],
                "apply_blockers_included": min(len(apply_blockers), 4),
            }
    if compact.get("id") == SEARCH_TERM_NGRAM_ACTION_ID:
        compact["human_diagnosis"] = (
            "Przegląd tematów zapytań z Google Ads oparty o dowody "
            "z wyszukiwanych haseł; nie wykonuj zmian."
        )
        compact["recommended_reason"] = (
            "Sprawdź intencję tematów i próbki zapytań przed kolejką sprawdzenia wykluczeń."
        )
        compact["evidence_ids"] = compact.get("evidence_ids", [])[:1]
    audit_events = compact.get("audit_events")
    compact["latest_audit_event"] = context_compaction.compact_audit_event_for_skill_context(
        context_compaction.latest_audit_event(audit_events)
    )
    compact.pop("audit_events", None)
    compact_action_review_gate_for_context(compact)
    metrics = compact.get("metrics")
    if isinstance(metrics, list):
        compact["metrics_total"] = len(metrics)
        compact["metrics"] = (
            []
            if compact.get("id") in {SEARCH_TERM_NGRAM_ACTION_ID, "act_review_merchant_feed_issues"}
            else [
                context_compaction.compact_metric_fact_for_context(metric)
                for metric in metrics[:1]
                if isinstance(metric, dict)
            ]
        )
        compact["metrics_included"] = len(compact["metrics"])
    preview_cards = compact.get("preview_cards")
    if isinstance(preview_cards, list):
        compact["preview_cards_total"] = len(preview_cards)
        compact["preview_cards"] = [
            context_action_previews.compact_preview_card_for_skill_context(card)
            for card in preview_cards[:3]
            if isinstance(card, dict)
        ]
        compact["preview_cards_included"] = len(compact["preview_cards"])
    payload = compact.get("payload")
    if isinstance(payload, dict):
        if _action_payload_should_survive_skill_context(
            str(compact.get("id") or ""),
            skill=skill,
        ):
            _compact_action_payload_for_context(
                payload,
                action_id=str(compact.get("id") or ""),
            )
            compact["action_plan"] = payload
            compact.pop("payload", None)
        else:
            compact.pop("payload", None)
    compact["api_endpoint_template"] = "/api/actions/{action_id}"
    return compact


def _action_payload_should_survive_skill_context(action_id: str, *, skill: str) -> bool:
    allowed_by_skill: dict[str, set[str]] = {
        "wilq-content-strategist": {"act_prepare_content_refresh_queue"},
        "wilq-gsc-content-doctor": {"act_prepare_content_refresh_queue"},
        "wilq-ga4-analyst": {"act_review_ga4_tracking_quality"},
        "wilq-localo-operator": {"act_review_localo_visibility_facts"},
        "wilq-ads-doctor": {
            "act_review_ads_search_term_ngrams",
            "act_prepare_ads_campaign_review_queue",
            "act_prepare_custom_segments_from_search_terms",
        },
        "wilq-custom-segments": {"act_prepare_custom_segments_from_search_terms"},
        "wilq-campaign-builder": {"act_prepare_ads_campaign_review_queue"},
        "wilq-demand-gen-operator": {"act_review_demand_gen_readiness"},
    }
    return action_id in allowed_by_skill.get(skill, set())


def _compact_action_payload_for_context(payload: dict[str, Any], *, action_id: str) -> None:
    payload.pop("source_metric_names", None)
    _compact_campaign_candidate_list_for_context(
        payload,
        keep_items=action_id == "act_prepare_ads_campaign_review_queue",
    )
    for key in ("recommendations", "terms", "source_terms", "keyword_match_context"):
        _compact_action_row_list_for_context(payload, key, keep_limit=0)
    _compact_preview_list_for_context(payload, "payload_preview")
    _compact_preview_list_for_context(payload, "budget_payload_preview", limit=0)
    _compact_preview_list_for_context(payload, "custom_segment_payload_preview")
    _compact_preview_list_for_context(payload, "negative_keyword_payload_preview")
    _compact_preview_list_for_context(payload, "ngram_preview")
    _compact_content_action_payload_for_context(payload)
    _label_action_plan_for_context(payload)


def _compact_action_row_list_for_context(
    payload: dict[str, Any],
    key: str,
    *,
    keep_limit: int,
) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        return
    payload[f"{key}_total"] = len(value)
    payload[key] = value[:keep_limit]
    payload[f"{key}_included"] = len(payload[key])


def _compact_campaign_candidate_list_for_context(
    payload: dict[str, Any],
    *,
    keep_items: bool,
) -> None:
    value = payload.get("campaign_candidates")
    if not isinstance(value, list):
        return
    payload["campaign_candidates_total"] = len(value)
    payload["campaign_candidates"] = (
        context_ads.compact_campaign_candidates_for_context(value) if keep_items else []
    )
    payload["campaign_candidates_included"] = len(payload["campaign_candidates"])


def _compact_preview_list_for_context(
    payload: dict[str, Any],
    key: str,
    *,
    limit: int = 4,
) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        return
    payload[f"{key}_total"] = len(value)
    payload[key] = value[:limit]
    payload[f"{key}_included"] = len(payload[key])


def _compact_content_action_payload_for_context(payload: dict[str, Any]) -> None:
    url_contract = payload.pop("content_url_review_contract", None)
    if isinstance(url_contract, dict):
        required_fields = url_contract.get("required_fields")
        allowed_outcomes = url_contract.get("allowed_outcomes")
        payload["content_url_review_summary"] = {
            "required_fields_total": (
                len(required_fields) if isinstance(required_fields, list) else 0
            ),
            "allowed_outcomes_total": (
                len(allowed_outcomes) if isinstance(allowed_outcomes, list) else 0
            ),
            "next_step": "Sprawdź publiczny i kanoniczny URL przed pisaniem.",
        }

    content_preview = payload.get("content_brief_preview")
    if isinstance(content_preview, list):
        payload["content_brief_preview_total"] = len(content_preview)
        payload["content_brief_preview"] = (
            context_action_previews.compact_content_brief_preview_for_context(content_preview)
        )
        payload["content_brief_preview_included"] = len(payload["content_brief_preview"])

    wordpress_preview = payload.get("wordpress_draft_payload_preview")
    if isinstance(wordpress_preview, list):
        payload["wordpress_draft_payload_preview_total"] = len(wordpress_preview)
        payload["wordpress_draft_payload_preview"] = (
            context_action_previews.compact_wordpress_draft_payload_preview_for_context(
                wordpress_preview
            )
        )
        payload["wordpress_draft_payload_preview_included"] = len(
            payload["wordpress_draft_payload_preview"]
        )

    for key in ("content_brief_preview", "wordpress_draft_payload_preview"):
        value = payload.get(key)
        if isinstance(value, list):
            payload.setdefault(f"{key}_total", len(value))
            payload.setdefault(f"{key}_included", len(value))


ACTION_PLAN_LIST_KEY_LABELS = {
    "payload_preview": "preview_items",
    "budget_payload_preview": "budget_preview_items",
    "custom_segment_payload_preview": "custom_segment_preview_items",
    "negative_keyword_payload_preview": "negative_keyword_preview_items",
    "ngram_preview": "search_term_theme_preview_items",
    "content_brief_preview": "content_plan_items",
    "wordpress_draft_payload_preview": "wordpress_draft_preview_items",
}


def _label_action_plan_for_context(value: Any) -> None:
    if isinstance(value, dict):
        _rename_action_plan_list_keys(value)
        _label_action_plan_status_fields(value)
        for child in list(value.values()):
            _label_action_plan_for_context(child)
        return
    if isinstance(value, list):
        for item in value:
            _label_action_plan_for_context(item)


def _rename_action_plan_list_keys(value: dict[str, Any]) -> None:
    for old_key, new_key in ACTION_PLAN_LIST_KEY_LABELS.items():
        if old_key in value:
            value[new_key] = value.pop(old_key)
        total_key = f"{old_key}_total"
        if total_key in value:
            value[f"{new_key}_total"] = value.pop(total_key)
        included_key = f"{old_key}_included"
        if included_key in value:
            value[f"{new_key}_included"] = value.pop(included_key)


def _label_action_plan_status_fields(value: dict[str, Any]) -> None:
    value.pop("id", None)
    value.pop("action_type", None)
    value.pop("connector", None)
    value.pop("mode", None)

    value.pop("operation_type", None)
    value.pop("source_metric_names", None)
    value.pop("campaign_id", None)
    value.pop("campaign_budget_id", None)
    value.pop("custom_segment_preview_id", None)
    value.pop("budget_preview_id", None)
    value.pop("safety_contract", None)
    value.pop("target_scope", None)
    value.pop("audit_required", None)
    for key in list(value):
        if key.endswith("_micros"):
            value.pop(key, None)

    preview_contract_label = value.pop("preview_contract_label", None)
    if isinstance(preview_contract_label, str) and preview_contract_label:
        value.setdefault("review_type_label", preview_contract_label)
    value.pop("preview_contract", None)
    value.pop("source_preview_contract", None)

    required_validation_labels = value.pop("required_validation_labels", None)
    if isinstance(required_validation_labels, list):
        value.setdefault("required_check_labels", required_validation_labels)
    value.pop("required_validation", None)
    required_validation_total = value.pop("required_validation_total", None)
    if isinstance(required_validation_total, int):
        value.setdefault("required_checks_total", required_validation_total)

    required_breakdown_labels = value.pop("required_breakdown_labels", None)
    if isinstance(required_breakdown_labels, list):
        value.setdefault("required_dimension_labels", required_breakdown_labels)
    value.pop("required_breakdowns", None)
    required_breakdowns_total = value.pop("required_breakdowns_total", None)
    if isinstance(required_breakdowns_total, int):
        value.setdefault("required_dimensions_total", required_breakdowns_total)

    if "blocked_claim_labels" in value:
        value.pop("blocked_claims", None)
        value.pop("forbidden_claims", None)
    if "missing_read_contract_labels" in value:
        value.pop("missing_read_contracts", None)
    if "allowed_contract_labels" in value:
        value.pop("allowed_contracts", None)
    if "available_read_contract_labels" in value:
        value.pop("available_read_contracts", None)
    if "operator_review_gate_labels" in value:
        value.pop("operator_review_gates", None)
    if "human_review_gate_labels" in value:
        value.pop("human_review_gates", None)
    if "campaign_status_label" in value:
        value.pop("campaign_status", None)
    if "advertising_channel_type_label" in value:
        value.pop("advertising_channel_type", None)
    if "member_type_label" in value:
        value.pop("member_type", None)
    if "status_label" in value:
        value.pop("status", None)
    if "draft_generation_status_label" in value:
        value.pop("draft_generation_status", None)
    if "target_status_label" in value:
        value.pop("target_status", None)
    if "missing_requirement_labels" in value:
        value.pop("missing_requirements", None)
    if "source_type_label" in value:
        value.pop("source_type", None)
    if "publication_readiness_status_label" in value:
        value.pop("publication_readiness_status", None)
    if "publication_blocker_labels" in value:
        value.pop("publication_blockers", None)
    if "inventory_gate_status_label" in value:
        value.pop("inventory_gate_status", None)
    if "canonical_gate_status_label" in value:
        value.pop("canonical_gate_status", None)
    if "duplicate_gate_status_label" in value:
        value.pop("duplicate_gate_status", None)
    if "wordpress_inventory_match_label" in value:
        value.pop("wordpress_inventory_match", None)
    _label_action_plan_metric_snapshot(value)

    apply_allowed = value.pop("apply_allowed", None)
    if isinstance(apply_allowed, bool):
        value.setdefault(
            "apply_status_label",
            "gotowe do potwierdzenia" if apply_allowed else "zablokowane do sprawdzenia",
        )

    api_mutation_ready = value.pop("api_mutation_ready", None)
    if isinstance(api_mutation_ready, bool):
        value.setdefault(
            "write_status_label",
            "gotowe do zapisu" if api_mutation_ready else "bez zapisu automatycznego",
        )

    destructive = value.pop("destructive", None)
    if isinstance(destructive, bool):
        value.setdefault(
            "change_risk_label",
            "zmiana destrukcyjna" if destructive else "bezpieczny podgląd",
        )


def _label_action_plan_metric_snapshot(value: dict[str, Any]) -> None:
    metric_snapshot = value.get("metric_snapshot")
    metric_snapshot_labels = value.get("metric_snapshot_labels")
    if not isinstance(metric_snapshot, dict) or not isinstance(metric_snapshot_labels, dict):
        return

    metric_tiles: dict[str, Any] = {}
    for metric_name, metric_value in metric_snapshot.items():
        metric_label = metric_snapshot_labels.get(metric_name)
        if isinstance(metric_label, str) and metric_label:
            metric_tiles[metric_label] = metric_value
    if metric_tiles:
        value["metric_tiles"] = metric_tiles
        value.pop("metric_snapshot", None)
        value.pop("metric_snapshot_labels", None)


def compact_action_review_gate_for_context(action: dict[str, Any]) -> None:
    review_gate = action.get("review_gate")
    if not isinstance(review_gate, dict):
        return

    apply_blockers = review_gate.get("apply_blockers")
    if not isinstance(apply_blockers, list):
        apply_blockers = []
    apply_blocker_labels = review_gate.get("apply_blocker_labels")
    if not isinstance(apply_blocker_labels, list):
        apply_blocker_labels = []
    missing_validation = review_gate.get("missing_validation")
    if not isinstance(missing_validation, list):
        missing_validation = []
    blocked_claims = review_gate.get("blocked_claims")
    if not isinstance(blocked_claims, list):
        blocked_claims = []
    warnings = review_gate.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    last_mutation_blockers = review_gate.get("last_mutation_blockers")
    if not isinstance(last_mutation_blockers, list):
        last_mutation_blockers = []
    last_mutation_blocker_labels = review_gate.get("last_mutation_blocker_labels")
    if not isinstance(last_mutation_blocker_labels, list):
        last_mutation_blocker_labels = []

    action["review_gate"] = {
        "status": review_gate.get("status"),
        "risk": review_gate.get("risk"),
        "last_review_outcome": review_gate.get("last_review_outcome"),
        "last_reviewed_by": review_gate.get("last_reviewed_by"),
        "last_confirmation_by": review_gate.get("last_confirmation_by"),
        "last_impact_check_status": review_gate.get("last_impact_check_status"),
        "last_mutation_audit_status": review_gate.get("last_mutation_audit_status"),
        "last_mutation_attempted": review_gate.get("last_mutation_attempted"),
        "apply_allowed": review_gate.get("apply_allowed"),
        "confirmation_required": review_gate.get("confirmation_required"),
        "apply_blockers_total": len(apply_blockers),
        "apply_blocker_labels": apply_blocker_labels[:3],
        "apply_blockers_included": min(len(apply_blockers), 3),
        "missing_validation_total": len(missing_validation),
        "missing_validation": missing_validation[:4],
        "missing_validation_included": min(len(missing_validation), 4),
        "blocked_claims_total": len(blocked_claims),
        "blocked_claims": blocked_claims[:4],
        "blocked_claims_included": min(len(blocked_claims), 4),
        "warnings_total": len(warnings),
        "warnings": warnings[:2],
        "warnings_included": min(len(warnings), 2),
        "last_mutation_blockers_total": len(last_mutation_blockers),
        "last_mutation_blocker_labels": last_mutation_blocker_labels[:3],
        "last_mutation_blockers_included": min(len(last_mutation_blockers), 3),
    }
