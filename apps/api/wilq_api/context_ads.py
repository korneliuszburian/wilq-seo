from __future__ import annotations

from typing import Any

from apps.api.wilq_api import context_compaction
from apps.api.wilq_api.context_scopes import SKILL_ACTION_ID_SCOPES
from wilq.actions.google_ads.business_context import ADS_STRATEGY_REVIEW_ACTION_ID

ADS_CONTEXT_ROW_LIMIT = 3
ADS_CONTEXT_NGRAM_ROW_LIMIT = 3
ADS_CONTEXT_DECISION_ROW_LIMIT = 2
ADS_LITE_DECISION_LIMIT = 5
ACTION_CONTEXT_CAMPAIGN_CANDIDATE_LIMIT = 3

def compact_ads_diagnostics_for_context(ads_diagnostics: dict[str, Any]) -> dict[str, Any]:
    compact = dict(context_compaction.without_metric_facts(ads_diagnostics))
    _compact_latest_refresh_for_context(compact)
    campaign_rows = context_compaction.list_at(compact, "campaign_read_contract", "campaign_rows")
    campaign_triage_rows = context_compaction.list_at(
        compact,
        "campaign_triage_read_contract",
        "triage_rows",
    )
    kpi_rows = context_compaction.list_at(compact, "derived_kpi_read_contract", "kpi_rows")
    budget_rows = context_compaction.list_at(compact, "budget_pacing_read_contract", "budget_rows")
    search_term_rows = context_compaction.list_at(
        compact,
        "search_terms_read_contract",
        "search_term_rows",
    )
    search_term_ngram_rows = context_compaction.list_at(
        compact,
        "search_term_ngram_read_contract",
        "ngram_rows",
    )
    safety_rows = context_compaction.list_at(
        compact,
        "search_term_safety_read_contract",
        "safety_rows",
    )
    keyword_context_rows = context_compaction.list_at(
        compact,
        "keyword_match_context_read_contract",
        "context_rows",
    )
    recommendation_payload_preview = context_compaction.list_at(
        compact,
        "recommendations_read_contract",
        "payload_preview",
    )
    custom_payload_preview = context_compaction.list_at(
        compact,
        "custom_segments_read_contract",
        "payload_preview",
    )
    negative_payload_preview = context_compaction.list_at(
        compact,
        "negative_keywords_read_contract",
        "payload_preview",
    )
    _limit_contract_rows(
        compact,
        ("campaign_read_contract", "campaign_rows"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("campaign_triage_read_contract", "triage_rows"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _compact_campaign_triage_rows_for_context(
        context_compaction.list_at(compact, "campaign_triage_read_contract", "triage_rows")
    )
    _limit_contract_rows(
        compact,
        ("budget_pacing_read_contract", "budget_rows"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    budget_payload_preview = context_compaction.list_at(
        compact,
        "budget_pacing_read_contract",
        "payload_preview",
    )
    _limit_contract_rows(
        compact,
        ("budget_pacing_read_contract", "payload_preview"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _compact_budget_apply_preview_for_context(
        context_compaction.list_at(compact, "budget_pacing_read_contract", "payload_preview")
    )
    _compact_budget_row_payload_preview_for_context(
        context_compaction.list_at(compact, "budget_pacing_read_contract", "budget_rows")
    )
    _limit_contract_rows(
        compact,
        ("search_terms_read_contract", "search_term_rows"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("search_term_ngram_read_contract", "ngram_rows"),
        ADS_CONTEXT_NGRAM_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("search_term_safety_read_contract", "safety_rows"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("keyword_match_context_read_contract", "context_rows"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("recommendations_read_contract", "payload_preview"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_recommendation_rows_for_context(compact)
    _drop_recommendation_row_nested_payload_preview_for_context(compact)
    _limit_contract_rows(
        compact,
        ("custom_segments_read_contract", "payload_preview"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _compact_custom_segment_payload_preview_for_context(compact)
    _limit_contract_rows(
        compact,
        ("negative_keywords_read_contract", "payload_preview"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("negative_keywords_read_contract", "candidates"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _limit_candidate_rows(
        compact,
        ("custom_segments_read_contract", "candidates"),
        "search_term_rows",
        ADS_CONTEXT_ROW_LIMIT,
    )
    _compact_custom_segment_candidate_search_term_rows_for_context(compact)
    _limit_candidate_rows(
        compact,
        ("negative_keywords_read_contract", "candidates"),
        "keyword_context_rows",
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _compact_negative_keyword_candidate_context_rows_for_context(compact)
    _drop_candidate_nested_payload_preview(
        compact,
        ("custom_segments_read_contract", "candidates"),
    )
    _drop_candidate_keys(
        compact,
        ("custom_segments_read_contract", "candidates"),
        ("rejection_reasons",),
    )
    _drop_candidate_nested_payload_preview(
        compact,
        ("negative_keywords_read_contract", "candidates"),
    )
    _compact_ads_strategy_review_readiness_for_context(compact)
    _compact_ads_optimizer_readiness_for_context(compact)
    _limit_decision_rows(compact)
    _omit_decision_row_payloads(compact)
    _drop_empty_decision_row_lists_for_context(compact)
    _compact_ads_decision_queue_for_context(compact)
    sections = compact.pop("sections", [])
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "full_endpoint": "/api/ads/diagnostics",
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "decision_row_payloads_omitted": True,
        "empty_decision_row_lists_omitted": True,
        "campaign_rows_total": len(campaign_rows),
        "campaign_rows_included": len(
            context_compaction.list_at(compact, "campaign_read_contract", "campaign_rows")
        ),
        "campaign_triage_rows_total": len(campaign_triage_rows),
        "campaign_triage_rows_included": len(
            context_compaction.list_at(compact, "campaign_triage_read_contract", "triage_rows")
        ),
        "derived_kpi_rows_total": len(kpi_rows),
        "budget_rows_total": len(budget_rows),
        "budget_rows_included": len(
            context_compaction.list_at(compact, "budget_pacing_read_contract", "budget_rows")
        ),
        "budget_payload_preview_total": len(budget_payload_preview),
        "budget_payload_preview_included": len(
            context_compaction.list_at(compact, "budget_pacing_read_contract", "payload_preview")
        ),
        "search_term_rows_total": len(search_term_rows),
        "search_term_rows_included": len(
            context_compaction.list_at(compact, "search_terms_read_contract", "search_term_rows")
        ),
        "search_term_ngram_rows_total": len(search_term_ngram_rows),
        "search_term_ngram_rows_included": len(
            context_compaction.list_at(compact, "search_term_ngram_read_contract", "ngram_rows")
        ),
        "search_term_safety_rows_total": len(safety_rows),
        "search_term_safety_rows_included": len(
            context_compaction.list_at(compact, "search_term_safety_read_contract", "safety_rows")
        ),
        "keyword_match_context_rows_total": len(keyword_context_rows),
        "keyword_match_context_rows_included": len(
            context_compaction.list_at(
                compact, "keyword_match_context_read_contract", "context_rows"
            )
        ),
        "recommendation_apply_preview_total": len(recommendation_payload_preview),
        "recommendation_apply_preview_included": len(
            context_compaction.list_at(compact, "recommendations_read_contract", "payload_preview")
        ),
        "recommendation_row_payload_previews_omitted": True,
        "custom_segment_payload_preview_total": len(custom_payload_preview),
        "custom_segment_payload_preview_included": len(
            context_compaction.list_at(compact, "custom_segments_read_contract", "payload_preview")
        ),
        "custom_segment_candidate_search_term_rows_compacted": True,
        "negative_keyword_payload_preview_total": len(negative_payload_preview),
        "negative_keyword_payload_preview_included": len(
            context_compaction.list_at(
                compact, "negative_keywords_read_contract", "payload_preview"
            )
        ),
        "negative_keyword_candidates_total": len(
            context_compaction.list_at(
                ads_diagnostics, "negative_keywords_read_contract", "candidates"
            )
        ),
        "negative_keyword_candidates_included": len(
            context_compaction.list_at(compact, "negative_keywords_read_contract", "candidates")
        ),
        "negative_keyword_candidate_context_rows_compacted": True,
        "optimizer_readiness_compacted": isinstance(
            compact.get("optimizer_readiness_contract"),
            dict,
        ),
    }
    return compact


def _compact_ads_strategy_review_readiness_for_context(data: dict[str, Any]) -> None:
    business_context = data.get("business_context_read_contract")
    if not isinstance(business_context, dict):
        return
    contract = business_context.get("strategy_review_readiness_contract")
    if not isinstance(contract, dict):
        return

    required_missing = [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
        "approved_human_strategy_review",
    ]
    required_validation = [
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
        "human_strategy_review",
    ]
    required_blocked = [
        "profitability verdict",
        "target KPI verdict",
        "budget scaling",
        "zmiana budżetu",
        "zapis rekomendacji",
        "automatic optimization",
    ]
    summary = context_compaction.context_pack_text(contract.get("summary"), limit=170)
    next_step = context_compaction.context_pack_text(contract.get("next_step"), limit=160)
    compact_contract = {
        key: contract.get(key)
        for key in (
            "id",
            "status",
            "latest_review_status",
            "latest_review_outcome",
            "apply_allowed",
            "destructive",
        )
        if key in contract
    }
    if summary is not None:
        compact_contract["summary"] = summary
    if next_step is not None:
        compact_contract["next_step"] = next_step
    compact_contract["current_context"] = contract.get("current_context")
    compact_contract["required_validation"] = context_compaction.priority_limited_strings(
        contract.get("required_validation"),
        required_validation,
        limit=5,
    )
    compact_contract["missing_read_contracts"] = context_compaction.priority_limited_strings(
        contract.get("missing_read_contracts"),
        required_missing,
        limit=6,
    )
    compact_contract["blocked_claims"] = context_compaction.priority_limited_strings(
        contract.get("blocked_claims"),
        required_blocked,
        limit=6,
    )
    compact_contract["evidence_ids"] = context_compaction.priority_limited_strings(
        contract.get("evidence_ids"),
        [],
        limit=4,
    )
    compact_contract["action_ids"] = context_compaction.priority_limited_strings(
        contract.get("action_ids"),
        [ADS_STRATEGY_REVIEW_ACTION_ID],
        limit=2,
    )
    business_context["strategy_review_readiness_contract"] = compact_contract


def _compact_ads_optimizer_readiness_for_context(data: dict[str, Any]) -> None:
    contract = data.get("optimizer_readiness_contract")
    if not isinstance(contract, dict):
        return

    required_missing = [
        "change_event_rows",
        "pre_change_performance_window",
        "post_change_performance_window",
        "human_change_impact_review",
        "google_ads_mutation_audit",
        "human_confirm_before_apply",
    ]
    required_blocked = [
        "campaign mutation",
        "change impact",
        "zmiana budżetu",
        "dodanie wykluczających słów kluczowych",
        "targeting applied",
    ]
    contract["allowed_metrics"] = context_compaction.priority_limited_strings(
        contract.get("allowed_metrics"),
        ["clicks", "cost_micros", "conversions", "search_term", "change_event_available"],
        limit=8,
    )
    contract["missing_read_contracts"] = context_compaction.priority_limited_strings(
        contract.get("missing_read_contracts"),
        required_missing,
        limit=10,
    )
    contract["operator_review_gates"] = context_compaction.priority_limited_strings(
        contract.get("operator_review_gates"),
        ["human_strategy_review", "human_confirm_before_apply"],
        limit=6,
    )
    contract["blocked_claims"] = context_compaction.priority_limited_strings(
        contract.get("blocked_claims"),
        required_blocked,
        limit=10,
    )
    contract["evidence_ids"] = context_compaction.priority_limited_strings(
        contract.get("evidence_ids"),
        [],
        limit=4,
    )

    items = contract.get("readiness_items")
    if not isinstance(items, list):
        return

    compact_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        compact_item = {
            key: item.get(key)
            for key in (
                "id",
                "status",
                "source_contract_ids",
                "risk",
            )
            if key in item
        }
        if item.get("status") == "blocked":
            compact_item["next_step"] = context_compaction.context_pack_text(
                item.get("next_step"),
                limit=150,
            )
        compact_item["source_contract_ids"] = context_compaction.priority_limited_strings(
            item.get("source_contract_ids"),
            ["ads_change_history_read_contract", "ads_action_safety_contract"],
            limit=3,
        )
        if item.get("status") == "blocked":
            compact_item["missing_read_contracts"] = context_compaction.priority_limited_strings(
                item.get("missing_read_contracts"),
                required_missing,
                limit=5,
            )
            compact_item["blocked_claims"] = context_compaction.priority_limited_strings(
                item.get("blocked_claims"),
                required_blocked,
                limit=5,
            )
        compact_item["action_ids"] = context_compaction.priority_limited_strings(
            item.get("action_ids"),
            [],
            limit=3,
        )
        compact_items.append(compact_item)
    contract["readiness_items_total"] = len(items)
    contract["readiness_items"] = compact_items


def _compact_ads_decision_queue_for_context(data: dict[str, Any]) -> None:
    required_blocked = [
        "campaign mutation",
        "change impact",
        "zmiana budżetu",
        "dodanie wykluczających słów kluczowych",
        "targeting applied",
    ]
    required_missing = [
        "change_event_rows",
        "pre_change_performance_window",
        "post_change_performance_window",
        "human_confirm_before_apply",
    ]
    for decision in context_compaction.list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        for key, limit in (
            ("summary", 120),
            ("rationale", 125),
            ("next_step", 135),
        ):
            compact_text = context_compaction.context_pack_text(decision.get(key), limit=limit)
            if compact_text is not None:
                decision[key] = compact_text
        decision["allowed_metrics"] = context_compaction.priority_limited_strings(
            decision.get("allowed_metrics"),
            ["clicks", "cost_micros", "conversions", "search_term", "change_event_available"],
            limit=4,
        )
        decision["missing_read_contracts"] = context_compaction.priority_limited_strings(
            decision.get("missing_read_contracts"),
            required_missing,
            limit=5,
        )
        decision["operator_review_gates"] = context_compaction.priority_limited_strings(
            decision.get("operator_review_gates"),
            ["human_strategy_review", "human_confirm_before_apply"],
            limit=3,
        )
        decision["blocked_claims"] = context_compaction.priority_limited_strings(
            decision.get("blocked_claims"),
            required_blocked,
            limit=5,
        )
        decision["evidence_ids"] = context_compaction.priority_limited_strings(
            decision.get("evidence_ids"),
            [],
            limit=4,
        )
        decision["action_ids"] = context_compaction.priority_limited_strings(
            decision.get("action_ids"),
            [],
            limit=4,
        )


def _compact_budget_row_payload_preview_for_context(rows: list[Any]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        payload_preview = row.get("payload_preview")
        if isinstance(payload_preview, dict):
            safety_review = payload_preview.get("safety_review")
            row["payload_preview"] = {
                "id": payload_preview.get("id"),
                "operation_type": payload_preview.get("operation_type"),
                "apply_allowed": payload_preview.get("apply_allowed"),
                "safety_contract": safety_review.get("safety_contract")
                if isinstance(safety_review, dict)
                else None,
                "safety_status": safety_review.get("status")
                if isinstance(safety_review, dict)
                else None,
            }


def _compact_campaign_triage_rows_for_context(rows: list[Any]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        compact_row = {
            "campaign_id": row.get("campaign_id"),
            "campaign_name": row.get("campaign_name"),
            "review_priority": row.get("review_priority"),
            "review_score": row.get("review_score"),
            "target_status": row.get("target_status"),
            "clicks": row.get("clicks"),
            "cost_micros": row.get("cost_micros"),
            "conversions": row.get("conversions"),
            "roas": row.get("roas"),
            "spend_to_budget_ratio_7d": row.get("spend_to_budget_ratio_7d"),
            "search_budget_lost_impression_share": row.get("search_budget_lost_impression_share"),
            "recommendation_count": row.get("recommendation_count"),
            "has_budget_apply_preview": row.get("has_budget_apply_preview"),
            "has_recommendation_apply_preview": row.get("has_recommendation_apply_preview"),
            "next_step": row.get("next_step"),
            "evidence_ids": row.get("evidence_ids"),
            "action_ids": row.get("action_ids"),
            "blocked_claims": row.get("blocked_claims"),
        }
        row.clear()
        row.update({key: value for key, value in compact_row.items() if value is not None})


def _compact_budget_apply_preview_for_context(preview_items: list[Any]) -> None:
    for index, item in enumerate(preview_items):
        if isinstance(item, dict):
            preview_items[index] = _compact_budget_apply_preview_item(item)


def _compact_budget_apply_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = {
        key: item.get(key)
        for key in (
            "id",
            "campaign_id",
            "campaign_name",
            "campaign_budget_id",
            "campaign_budget_name",
            "reason",
            "operation_type",
            "current_budget_amount_micros",
            "proposed_budget_amount_micros",
            "proposed_budget_delta_micros",
            "evidence_ids",
            "required_validation_labels",
            "blocked_claim_labels",
            "api_mutation_ready",
            "apply_allowed",
            "destructive",
        )
        if key in item
    }
    required_validation = item.get("required_validation")
    if isinstance(required_validation, list):
        compact_item["required_validation_total"] = len(required_validation)
    blocked_claims = item.get("blocked_claims")
    if isinstance(blocked_claims, list):
        compact_item["blocked_claims"] = blocked_claims[:4]
    safety_review = item.get("safety_review")
    if isinstance(safety_review, dict):
        compact_item["safety_review"] = _compact_budget_safety_review_item(safety_review)
    return compact_item


def _compact_budget_safety_review_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = {
        key: item.get(key)
        for key in (
            "id",
            "safety_contract",
            "status",
            "status_label",
            "reason",
            "max_allowed_delta_percent",
            "proposed_delta_percent",
            "missing_requirements",
            "missing_requirement_labels",
            "required_validation_labels",
            "blocked_claim_labels",
            "api_mutation_ready",
            "apply_allowed",
            "destructive",
        )
        if key in item
    }
    required_validation = item.get("required_validation")
    if isinstance(required_validation, list):
        compact_item["required_validation_total"] = len(required_validation)
    blocked_claims = item.get("blocked_claims")
    if isinstance(blocked_claims, list):
        compact_item["blocked_claims"] = blocked_claims[:4]
    return compact_item


def _compact_latest_refresh_for_context(compact: dict[str, Any]) -> None:
    latest_refresh = compact.get("latest_refresh")
    if not isinstance(latest_refresh, dict):
        return
    compact["latest_refresh"] = {
        key: latest_refresh.get(key)
        for key in (
            "id",
            "connector_id",
            "mode",
            "status",
            "completed_at",
            "evidence_ids",
            "external_call_attempted",
            "vendor_data_collected",
            "summary",
        )
        if key in latest_refresh
    }


def compact_ads_diagnostics_for_lite_context(
    ads_diagnostics: dict[str, Any],
    *,
    allowed_decision_ids: set[str],
    allowed_action_ids: set[str] | None = None,
    extra_keep_contracts: set[str] | None = None,
) -> dict[str, Any]:
    compact = compact_ads_diagnostics_for_context(ads_diagnostics)
    decision_queue = compact.get("decision_queue")
    if isinstance(decision_queue, list):
        compact["decision_queue"] = [
            decision
            for decision in decision_queue
            if isinstance(decision, dict) and str(decision.get("id")) in allowed_decision_ids
        ][:ADS_LITE_DECISION_LIMIT]
    if allowed_action_ids is not None:
        action_ids = compact.get("action_ids")
        if isinstance(action_ids, list):
            compact["action_ids"] = [
                action_id
                for action_id in action_ids
                if isinstance(action_id, str) and action_id in allowed_action_ids
            ]
        decision_queue = compact.get("decision_queue")
        if isinstance(decision_queue, list):
            for decision in decision_queue:
                if not isinstance(decision, dict):
                    continue
                decision_action_ids = decision.get("action_ids")
                if isinstance(decision_action_ids, list):
                    decision["action_ids"] = [
                        action_id
                        for action_id in decision_action_ids
                        if isinstance(action_id, str) and action_id in allowed_action_ids
                    ]
    keep_contracts = {
        "generated_at",
        "language",
        "strict_instruction",
        "latest_refresh",
        "live_data_available",
        "blocked_handoff",
        "campaign_read_contract",
        "business_context_read_contract",
        "derived_kpi_read_contract",
        "budget_pacing_read_contract",
        "impression_share_read_contract",
        "action_ids",
        "evidence_ids",
        "blocker_count",
        "decision_queue",
        "context_pack_compaction",
    }
    if extra_keep_contracts:
        keep_contracts.update(extra_keep_contracts)
    for key in list(compact):
        if key not in keep_contracts:
            compact.pop(key, None)
    compaction = compact.get("context_pack_compaction")
    if isinstance(compaction, dict):
        decision_queue = compact.get("decision_queue")
        compaction["lite_context"] = True
        compaction["omitted_contracts"] = [
            contract
            for contract in [
                "change_history_read_contract",
                "custom_segments_read_contract",
                "keyword_match_context_read_contract",
                "negative_keywords_read_contract",
                "recommendations_read_contract",
                "search_term_safety_read_contract",
                "search_terms_read_contract",
                "sections",
            ]
            if contract not in keep_contracts
        ]
        compaction["decision_rows_included"] = len(
            decision_queue if isinstance(decision_queue, list) else []
        )
    return compact


def custom_segments_diagnostics_for_context(
    ads_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = compact_ads_diagnostics_for_lite_context(
        ads_diagnostics,
        allowed_decision_ids={"ads_prepare_custom_segments_from_search_terms"},
        allowed_action_ids=SKILL_ACTION_ID_SCOPES["wilq-custom-segments"],
        extra_keep_contracts={
            "custom_segments_read_contract",
            "search_terms_read_contract",
        },
    )
    keep_contracts = {
        "generated_at",
        "language",
        "strict_instruction",
        "latest_refresh",
        "live_data_available",
        "blocked_handoff",
        "search_terms_read_contract",
        "custom_segments_read_contract",
        "action_ids",
        "evidence_ids",
        "blocker_count",
        "decision_queue",
        "context_pack_compaction",
    }
    for key in list(compact):
        if key not in keep_contracts:
            compact.pop(key, None)
    compaction = compact.get("context_pack_compaction")
    if isinstance(compaction, dict):
        compaction["purpose"] = "custom_segments_context"
        compaction["omitted_contracts"] = [
            contract
            for contract in [
                "business_context_read_contract",
                "campaign_read_contract",
                "derived_kpi_read_contract",
                "budget_pacing_read_contract",
                "impression_share_read_contract",
                "change_history_read_contract",
                "keyword_match_context_read_contract",
                "negative_keywords_read_contract",
                "recommendations_read_contract",
                "search_term_safety_read_contract",
                "sections",
            ]
            if contract not in keep_contracts
        ]
    return compact



def compact_campaign_candidates_for_context(
    campaign_candidates: list[Any],
) -> list[dict[str, Any]]:
    compact_candidates: list[dict[str, Any]] = []
    for candidate in campaign_candidates:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = candidate.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            evidence_ids = []
        human_review_gates = candidate.get("human_review_gates")
        if not isinstance(human_review_gates, list):
            human_review_gates = []
        missing_metrics = candidate.get("missing_metrics")
        if not isinstance(missing_metrics, list):
            missing_metrics = []
        compact_candidates.append(
            {
                "campaign_id": candidate.get("campaign_id"),
                "campaign_name": candidate.get("campaign_name"),
                "campaign_status": candidate.get("campaign_status"),
                "campaign_status_label": candidate.get("campaign_status_label"),
                "advertising_channel_type": candidate.get("advertising_channel_type"),
                "advertising_channel_type_label": candidate.get("advertising_channel_type_label"),
                "review_priority": candidate.get("review_priority"),
                "review_score": candidate.get("review_score"),
                "review_reason": candidate.get("review_reason"),
                "human_review_gates": human_review_gates,
                "human_review_gate_labels": candidate.get("human_review_gate_labels"),
                "target_context": candidate.get("target_context"),
                "clicks": candidate.get("clicks"),
                "impressions": candidate.get("impressions"),
                "cost_micros": candidate.get("cost_micros"),
                "conversions": candidate.get("conversions"),
                "conversion_value": candidate.get("conversion_value"),
                "derived_kpis": candidate.get("derived_kpis"),
                "missing_metrics": missing_metrics,
                "required_check_labels": candidate.get("required_check_labels"),
                "blocked_claim_labels": candidate.get("blocked_claim_labels"),
                "budget_preview_items": (
                    _compact_budget_apply_preview_item(candidate["budget_payload_preview"])
                    if isinstance(candidate.get("budget_payload_preview"), dict)
                    else None
                ),
                "evidence_ids": evidence_ids[:4],
                "evidence_ids_total": len(evidence_ids),
                "apply_allowed": candidate.get("apply_allowed"),
            }
        )
        if len(compact_candidates) >= ACTION_CONTEXT_CAMPAIGN_CANDIDATE_LIMIT:
            break
    return compact_candidates


def _limit_contract_rows(
    data: dict[str, Any],
    path: tuple[str, str],
    limit: int,
) -> None:
    contract = data.get(path[0])
    if isinstance(contract, dict) and isinstance(contract.get(path[1]), list):
        contract[path[1]] = contract[path[1]][:limit]


def _limit_recommendation_rows_for_context(data: dict[str, Any]) -> None:
    contract = data.get("recommendations_read_contract")
    if not isinstance(contract, dict) or not isinstance(
        contract.get("recommendation_rows"),
        list,
    ):
        return
    rows = contract["recommendation_rows"]
    selected_indexes = {
        index
        for index, row in enumerate(rows)
        if isinstance(row, dict) and row.get("impact_available")
    }
    for index, _row in enumerate(rows):
        if len(selected_indexes) >= ADS_CONTEXT_DECISION_ROW_LIMIT:
            break
        selected_indexes.add(index)
    contract["recommendation_rows"] = [
        row for index, row in enumerate(rows) if index in selected_indexes
    ]


def _drop_recommendation_row_nested_payload_preview_for_context(data: dict[str, Any]) -> None:
    contract = data.get("recommendations_read_contract")
    if not isinstance(contract, dict):
        return
    rows = contract.get("recommendation_rows")
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        payload_preview = row.pop("payload_preview", None)
        if isinstance(payload_preview, list):
            row["payload_preview_total"] = len(payload_preview)
        elif isinstance(payload_preview, dict):
            row["payload_preview_total"] = 1
        else:
            row["payload_preview_total"] = 0
        row["payload_preview_included"] = 0


def _limit_candidate_rows(
    data: dict[str, Any],
    candidates_path: tuple[str, str],
    rows_key: str,
    limit: int,
) -> None:
    candidates = context_compaction.list_at(data, *candidates_path)
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get(rows_key), list):
            candidate[rows_key] = candidate[rows_key][:limit]


def _drop_candidate_nested_payload_preview(
    data: dict[str, Any],
    candidates_path: tuple[str, str],
) -> None:
    for candidate in context_compaction.list_at(data, *candidates_path):
        if isinstance(candidate, dict):
            candidate.pop("payload_preview", None)


def _compact_negative_keyword_candidate_context_rows_for_context(data: dict[str, Any]) -> None:
    candidates = context_compaction.list_at(data, "negative_keywords_read_contract", "candidates")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        rows = candidate.get("keyword_context_rows")
        if not isinstance(rows, list):
            continue
        candidate["keyword_context_rows_total"] = len(rows)
        compact_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            compact_rows.append(
                {
                    "keyword_text": row.get("keyword_text"),
                    "match_type": row.get("match_type"),
                    "criterion_status": row.get("criterion_status"),
                    "negative": row.get("negative"),
                    "evidence_ids": row.get("evidence_ids") or [],
                }
            )
        candidate["keyword_context_rows"] = compact_rows
        candidate["keyword_context_rows_included"] = len(compact_rows)


def _compact_custom_segment_candidate_search_term_rows_for_context(data: dict[str, Any]) -> None:
    candidates = context_compaction.list_at(data, "custom_segments_read_contract", "candidates")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        rows = candidate.get("search_term_rows")
        if not isinstance(rows, list):
            continue
        candidate["search_term_rows_total"] = len(rows)
        compact_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            compact_rows.append(
                {
                    "search_term": row.get("search_term"),
                    "clicks": row.get("clicks"),
                    "cost_micros": row.get("cost_micros"),
                    "conversions": row.get("conversions"),
                    "evidence_ids": row.get("evidence_ids") or [],
                    "missing_metrics": row.get("missing_metrics") or [],
                }
            )
        candidate["search_term_rows"] = compact_rows
        candidate["search_term_rows_included"] = len(compact_rows)


def _compact_custom_segment_payload_preview_for_context(data: dict[str, Any]) -> None:
    contract = data.get("custom_segments_read_contract")
    if not isinstance(contract, dict):
        return
    payload_preview = contract.get("payload_preview")
    if not isinstance(payload_preview, list):
        return
    compact_items: list[dict[str, Any]] = []
    for item in payload_preview:
        if not isinstance(item, dict):
            continue
        compact_items.append(_compact_custom_segment_payload_preview_item(item))
    contract["payload_preview"] = compact_items


def _compact_custom_segment_payload_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = {
        key: item.get(key)
        for key in (
            "id",
            "custom_segment_name",
            "member_type",
            "source_terms",
            "campaign_id",
            "campaign_name",
            "evidence_ids",
            "required_validation",
            "blocked_claims",
            "api_mutation_ready",
            "apply_allowed",
            "destructive",
        )
        if key in item
    }
    compact_item["targeting_preview"] = _compact_custom_segment_targeting_preview_for_context(
        item.get("targeting_preview")
    )
    safety_review = item.get("safety_review")
    if isinstance(safety_review, dict):
        compact_item["safety_review"] = _compact_custom_segment_safety_review_item(safety_review)
    return compact_item


def _compact_custom_segment_safety_review_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = {
        key: item.get(key)
        for key in (
            "id",
            "safety_contract",
            "status",
            "reason",
            "missing_requirements",
            "audit_required",
            "api_mutation_ready",
            "apply_allowed",
            "destructive",
        )
        if key in item
    }
    required_validation = item.get("required_validation")
    if isinstance(required_validation, list):
        compact_item["required_validation_total"] = len(required_validation)
    blocked_claims = item.get("blocked_claims")
    if isinstance(blocked_claims, list):
        compact_item["blocked_claims"] = blocked_claims[:4]
    return compact_item


def _compact_custom_segment_targeting_preview_for_context(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    compact_targets: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        compact_targets.append(
            {
                key: item.get(key)
                for key in (
                    "id",
                    "custom_segment_preview_id",
                    "target_scope",
                    "campaign_id",
                    "campaign_name",
                    "operation_type",
                    "required_validation",
                    "blocked_claims",
                    "api_mutation_ready",
                    "apply_allowed",
                    "destructive",
                )
                if key in item
            }
        )
    return compact_targets


def _drop_candidate_keys(
    data: dict[str, Any],
    candidates_path: tuple[str, str],
    keys: tuple[str, ...],
) -> None:
    for candidate in context_compaction.list_at(data, *candidates_path):
        if not isinstance(candidate, dict):
            continue
        for key in keys:
            candidate.pop(key, None)


def _limit_decision_rows(data: dict[str, Any]) -> None:
    for decision in context_compaction.list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        for rows_key in (
            "campaign_rows",
            "campaign_triage_rows",
            "derived_kpi_rows",
            "budget_rows",
            "budget_apply_preview",
            "recommendation_rows",
            "recommendation_apply_preview",
            "impression_share_rows",
            "change_history_rows",
            "search_term_rows",
            "search_term_ngram_rows",
            "search_term_safety_rows",
            "keyword_match_context_rows",
            "keyword_planner_idea_rows",
            "custom_segment_candidates",
            "custom_segment_audience_forecast_rows",
            "custom_segment_payload_preview",
            "negative_keyword_candidates",
            "negative_keyword_payload_preview",
        ):
            rows = decision.get(rows_key)
            if isinstance(rows, list):
                decision[rows_key] = rows[:ADS_CONTEXT_DECISION_ROW_LIMIT]
        for candidate in decision.get("custom_segment_candidates", []):
            if isinstance(candidate, dict) and isinstance(
                candidate.get("search_term_rows"),
                list,
            ):
                candidate["search_term_rows"] = candidate["search_term_rows"][
                    :ADS_CONTEXT_DECISION_ROW_LIMIT
                ]
            if isinstance(candidate, dict):
                candidate.pop("payload_preview", None)
        for candidate in decision.get("negative_keyword_candidates", []):
            if isinstance(candidate, dict) and isinstance(
                candidate.get("keyword_context_rows"),
                list,
            ):
                candidate["keyword_context_rows"] = candidate["keyword_context_rows"][
                    :ADS_CONTEXT_DECISION_ROW_LIMIT
                ]
            if isinstance(candidate, dict):
                candidate.pop("payload_preview", None)


def _omit_decision_row_payloads(data: dict[str, Any]) -> None:
    for decision in context_compaction.list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        for rows_key in (
            "campaign_rows",
            "campaign_triage_rows",
            "derived_kpi_rows",
            "budget_rows",
            "budget_apply_preview",
            "recommendation_rows",
            "recommendation_apply_preview",
            "impression_share_rows",
            "change_history_rows",
            "search_term_rows",
            "search_term_ngram_rows",
            "search_term_safety_rows",
            "keyword_match_context_rows",
            "custom_segment_candidates",
            "custom_segment_audience_forecast_rows",
            "custom_segment_payload_preview",
            "negative_keyword_candidates",
            "negative_keyword_payload_preview",
        ):
            rows = decision.get(rows_key)
            if isinstance(rows, list):
                decision[f"{rows_key}_total"] = len(rows)
                decision[rows_key] = []


def _drop_empty_decision_row_lists_for_context(data: dict[str, Any]) -> None:
    row_keys = (
        "campaign_rows",
        "campaign_triage_rows",
        "derived_kpi_rows",
        "budget_rows",
        "budget_apply_preview",
        "recommendation_rows",
        "recommendation_apply_preview",
        "impression_share_rows",
        "change_history_rows",
        "search_term_rows",
        "search_term_ngram_rows",
        "search_term_safety_rows",
        "keyword_match_context_rows",
        "keyword_planner_idea_rows",
        "custom_segment_candidates",
        "custom_segment_audience_forecast_rows",
        "custom_segment_payload_preview",
        "negative_keyword_candidates",
        "negative_keyword_payload_preview",
    )
    for decision in context_compaction.list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        omitted_count = 0
        for rows_key in row_keys:
            rows = decision.get(rows_key)
            if rows == []:
                decision.pop(rows_key, None)
                omitted_count += 1
        if omitted_count:
            decision["omitted_empty_row_lists_count"] = omitted_count
