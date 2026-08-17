from __future__ import annotations

from collections.abc import (
    Iterable,
    Mapping,
)
from typing import Any

from wilq.actions.wordpress_payload_preview import build_wordpress_draft_payload_preview
from wilq.content.operator_copy import unique

from .review import (
    _content_contract_label,
    _content_contract_labels,
    _content_gate_status_summary,
    _draft_readiness_review_contract,
    _draft_readiness_review_contract_summary,
    _draft_readiness_review_summary,
    _prefixed_labels,
    _reviewed_candidate_draft_readiness_from_details,
    _reviewed_candidate_ids,
    _reviewed_candidate_ids_from_details,
    _reviewed_candidate_url_reviews,
    _reviewed_candidate_url_reviews_from_details,
)
from .shared import (
    CONTENT_BRIEF_PREVIEW_CONTRACT,
    CONTENT_REFRESH_ACTION_TYPE,
    POST_PUBLICATION_MEASUREMENT_PLAN_CONTRACT,
    WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT,
    _prioritized_content_contract_values,
    _string_list,
)

__all__ = [
    "content_payload_with_reviewed_wordpress_draft_previews",
    "_wordpress_draft_payload_preview",
    "_wordpress_draft_operation",
    "_draft_generation_status",
    "_draft_blockers",
    "_draft_generation_contract",
    "_wordpress_draft_handoff_status",
    "_wordpress_draft_handoff_blockers",
    "_wordpress_draft_handoff_contract",
    "post_publication_measurement_plan",
    "_draft_generation_summary",
    "_wordpress_draft_handoff_summary",
    "_wordpress_draft_handoff_contract_summary",
    "_post_publication_measurement_summary",
    "post_publication_measurement_summary",
    "_content_wordpress_draft_handoff_status_label",
    "_post_publication_measurement_status_label",
    "_draft_title",
    "_draft_excerpt_direction",
    "_draft_content_blocks",
    "_draft_content_block_label",
]


def content_payload_with_reviewed_wordpress_draft_previews(
    payload: dict[str, Any],
    *,
    review_event_summaries: Iterable[str],
    review_event_details: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if payload.get("action_type") != CONTENT_REFRESH_ACTION_TYPE:
        return payload
    enriched_payload = dict(payload)
    enriched_payload.pop("wordpress_draft_payload_preview", None)
    summary_list = list(review_event_summaries)
    detail_list = list(review_event_details or [])
    reviewed_candidate_ids = {
        *_reviewed_candidate_ids(summary_list),
        *_reviewed_candidate_ids_from_details(detail_list),
    }
    url_reviews = {
        **_reviewed_candidate_url_reviews(summary_list),
        **_reviewed_candidate_url_reviews_from_details(detail_list),
    }
    draft_readiness_reviews = _reviewed_candidate_draft_readiness_from_details(detail_list)
    if not reviewed_candidate_ids:
        return enriched_payload
    brief_previews = [
        item for item in enriched_payload.get("content_brief_preview", []) if isinstance(item, dict)
    ]
    draft_previews = [
        _wordpress_draft_payload_preview(
            item,
            url_review=url_reviews.get(str(item.get("candidate_id") or "")),
            draft_readiness_review=draft_readiness_reviews.get(str(item.get("candidate_id") or "")),
        )
        for item in brief_previews
        if isinstance(item.get("candidate_id"), str)
        and item["candidate_id"] in reviewed_candidate_ids
    ]
    if draft_previews:
        enriched_payload["wordpress_draft_payload_preview"] = draft_previews
    return enriched_payload


def _wordpress_draft_payload_preview(
    preview: dict[str, Any],
    *,
    url_review: dict[str, str] | None = None,
    draft_readiness_review: dict[str, str] | None = None,
) -> dict[str, Any]:
    return build_wordpress_draft_payload_preview(
        preview,
        support={
            "preview_contract": WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT,
            "source_preview_contract": CONTENT_BRIEF_PREVIEW_CONTRACT,
            "draft_generation_status": _draft_generation_status,
            "draft_blockers": _draft_blockers,
            "wordpress_draft_handoff_status": _wordpress_draft_handoff_status,
            "wordpress_draft_handoff_blockers": _wordpress_draft_handoff_blockers,
            "draft_generation_contract": _draft_generation_contract,
            "draft_readiness_review_contract": _draft_readiness_review_contract,
            "wordpress_draft_handoff_contract": _wordpress_draft_handoff_contract,
            "post_publication_measurement_plan": post_publication_measurement_plan,
            "unique": unique,
            "wordpress_draft_operation": _wordpress_draft_operation,
            "content_contract_label": _content_contract_label,
            "content_contract_labels": _content_contract_labels,
            "content_gate_status_summary": _content_gate_status_summary,
            "draft_generation_summary": _draft_generation_summary,
            "draft_readiness_review_contract_summary": _draft_readiness_review_contract_summary,
            "draft_readiness_review_summary": _draft_readiness_review_summary,
            "wordpress_draft_handoff_summary": _wordpress_draft_handoff_summary,
            "wordpress_draft_handoff_contract_summary": _wordpress_draft_handoff_contract_summary,
            "post_publication_measurement_summary": _post_publication_measurement_summary,
            "draft_title": _draft_title,
            "draft_excerpt_direction": _draft_excerpt_direction,
            "draft_content_blocks": _draft_content_blocks,
        },
        url_review=url_review,
        draft_readiness_review=draft_readiness_review,
    )


def _wordpress_draft_operation(mode: str) -> str:
    if mode in {"refresh", "merge"}:
        return "prepare_existing_content_draft"
    return "prepare_new_content_draft_review"


def _draft_generation_status(
    *,
    inventory_gate_status: str | None,
    canonical_gate_status: str | None,
    duplicate_gate_status: str | None,
) -> str:
    if inventory_gate_status == "missing_inventory_match":
        return "blocked_missing_public_inventory"
    if canonical_gate_status in {
        "needs_final_canonical_review",
        "blocked_until_content_url_review",
        "blocked_until_inventory_review",
    } or duplicate_gate_status in {
        "existing_public_content_requires_refresh_or_merge",
        "manual_merge_or_create_review",
        "create_blocked_until_duplicate_check",
    }:
        return "blocked_pending_canonical_duplicate_review"
    if inventory_gate_status == "confirmed_current_inventory":
        return "ready_for_review"
    return "blocked_until_content_review"


def _draft_blockers(draft_generation_status: str) -> list[str]:
    blockers = [
        "wordpress_write_not_requested",
        "api_mutation_ready_false",
        "human_confirm_before_wordpress_write",
    ]
    if draft_generation_status == "ready_for_review":
        return [
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_until_content_review":
        return [
            "content_url_preflight_review",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_pending_canonical_duplicate_review":
        return [
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_pending_canonical_duplicate_review_after_url_review":
        return [
            "content_url_review_recorded_review_only",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    if draft_generation_status == "blocked_missing_public_inventory":
        return [
            "public_content_inventory_required",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            *blockers,
        ]
    return [
        "business_relevance_review",
        "wordpress_inventory_check",
        "duplicate_or_cannibalization_check",
        *blockers,
    ]


def _draft_generation_contract(
    *,
    draft_generation_status: str,
    draft_blockers: list[str],
) -> dict[str, Any]:
    output_kind = (
        "reviewable_polish_draft_preview"
        if draft_generation_status == "ready_for_review"
        else "outline_only_until_checks_complete"
    )
    return {
        "contract_version": "content_draft_generation_v1",
        "language": "pl-PL",
        "status": draft_generation_status,
        "allowed_output_kind": output_kind,
        "blocked_until": draft_blockers,
        "requires_passed_gates": [
            "evidence_ids_present",
            "source_connectors_present",
            "content_url_preflight_review",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            "legal_factual_review",
            "human_confirm_before_wordpress_write",
        ],
        "output_must_include": [
            "seo_title_direction",
            "meta_description_direction",
            "h1_direction",
            "h2_direction",
            "faq_direction",
            "cta_direction",
            "internal_link_direction",
            "source_facts",
            "missing_evidence",
            "forbidden_claims",
        ],
        "forbidden_outputs": [
            "publish_ready_claim",
            "automatic_wordpress_write",
            "ranking_guarantee",
            "obietnica wzrostu leadów albo przychodu",
            "legal_compliance_guarantee",
        ],
    }


def _wordpress_draft_handoff_status(
    *,
    draft_generation_status: str,
    draft_readiness_outcome: str | None,
) -> str:
    if draft_generation_status != "ready_for_review":
        return "blocked_until_draft_checks_complete"
    if draft_readiness_outcome != "approve_outline_for_editorial_review":
        return "blocked_until_draft_readiness_review"
    return "blocked_until_wordpress_draft_handoff_action"


def _wordpress_draft_handoff_blockers(wordpress_draft_handoff_status: str) -> list[str]:
    blockers = [
        "wordpress_draft_write_not_requested",
        "api_mutation_ready_false",
        "human_confirm_before_wordpress_write",
    ]
    if wordpress_draft_handoff_status == "blocked_until_draft_checks_complete":
        return [
            "content_url_preflight_review",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            "legal_factual_review",
            *blockers,
        ]
    if wordpress_draft_handoff_status == "blocked_until_draft_readiness_review":
        return [
            "content_draft_readiness_review",
            *blockers,
        ]
    return [
        "wordpress_draft_handoff_action_required",
        "wordpress_draft_payload_preview_required",
        *blockers,
    ]


def _wordpress_draft_handoff_contract(
    *,
    wordpress_draft_handoff_status: str,
    wordpress_draft_handoff_blockers: list[str],
    final_canonical_url: str | None,
) -> dict[str, Any]:
    return {
        "contract_version": "wordpress_draft_handoff_v1",
        "scope": "blocked_preview_only",
        "final_canonical_url": final_canonical_url,
        "status": wordpress_draft_handoff_status,
        "blocked_until": wordpress_draft_handoff_blockers,
        "requires_passed_gates": [
            "content_url_preflight_review",
            "final_canonical_review",
            "duplicate_or_cannibalization_check",
            "legal_factual_review",
            "content_draft_readiness_review",
            "human_confirm_before_wordpress_write",
        ],
        "required_next_action_contract": "wordpress_draft_handoff_v1",
        "blocked_outputs": [
            "wordpress_draft_write",
            "wordpress_publish",
            "production_wordpress_write",
            "publish_ready_claim",
            "obietnica wzrostu pozycji albo leadów",
        ],
    }


def post_publication_measurement_plan(
    *,
    final_canonical_url: str | None,
) -> dict[str, Any]:
    return {
        "contract_version": POST_PUBLICATION_MEASUREMENT_PLAN_CONTRACT,
        "scope": "blocked_preview_only",
        "final_canonical_url": final_canonical_url,
        "status": "blocked_until_publish_and_followup_data",
        "baseline_window": "28d_before_publish",
        "followup_windows": ["7d_after_publish", "28d_after_publish", "90d_after_publish"],
        "required_source_connectors": [
            "google_search_console",
            "google_analytics_4",
            "wordpress_ekologus",
        ],
        "required_metric_groups": [
            "gsc_query_page_clicks_impressions_ctr_position",
            "ga4_landing_engagement_and_key_events",
            "wordpress_publish_metadata",
        ],
        "requires_before_claims": [
            "published_url_confirmed",
            "baseline_window_captured",
            "followup_window_captured",
            "same_url_or_redirect_mapping_confirmed",
            "tracking_quality_review",
        ],
        "blocked_outputs": [
            "ranking_gain_claim",
            "obietnica wzrostu leadów",
            "revenue_impact_claim",
            "content_success_verdict",
            "automatic_refresh_followup",
        ],
    }


def _draft_generation_summary(contract: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    output_kind = contract.get("allowed_output_kind")
    if isinstance(output_kind, str) and output_kind:
        values.append(f"wynik: {_content_contract_label(output_kind)}")
    required_gates = _prioritized_content_contract_values(
        _string_list(contract.get("requires_passed_gates")),
        [
            "duplicate_or_cannibalization_check",
            "final_canonical_review",
            "content_url_preflight_review",
            "legal_factual_review",
            "human_confirm_before_wordpress_write",
        ],
    )
    values.extend(_prefixed_labels("warunek", required_gates[:5]))
    values.extend(_prefixed_labels("zakaz", _string_list(contract.get("forbidden_outputs"))[:3]))
    return values


def _wordpress_draft_handoff_summary(status: str, blockers: Iterable[str]) -> list[str]:
    return [
        f"stan przekazania do WordPress: {_content_wordpress_draft_handoff_status_label(status)}",
        *_prefixed_labels("blokada", list(blockers)[:5]),
    ]


def _wordpress_draft_handoff_contract_summary(contract: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    scope = contract.get("scope")
    if isinstance(scope, str) and scope:
        values.append(f"zakres: {_content_contract_label(scope)}")
    next_action = contract.get("required_next_action_contract")
    if isinstance(next_action, str) and next_action:
        values.append(f"następny krok: {_content_contract_label(next_action)}")
    values.extend(
        _prefixed_labels("warunek", _string_list(contract.get("requires_passed_gates"))[:4])
    )
    values.extend(_prefixed_labels("blokuje", _string_list(contract.get("blocked_outputs"))[:4]))
    return values


def _post_publication_measurement_summary(plan: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    status = plan.get("status")
    if isinstance(status, str) and status:
        values.append(f"stan pomiaru efektu: {_post_publication_measurement_status_label(status)}")
    blocked_outputs = _prioritized_content_contract_values(
        _string_list(plan.get("blocked_outputs")),
        [
            "content_success_verdict",
            "ranking_gain_claim",
            "obietnica wzrostu leadów",
            "revenue_impact_claim",
        ],
    )
    values.extend(_prefixed_labels("blokuje", blocked_outputs[:4]))
    baseline_window = plan.get("baseline_window")
    if isinstance(baseline_window, str) and baseline_window:
        values.append(f"punkt odniesienia: {_content_contract_label(baseline_window)}")
    values.extend(_prefixed_labels("sprawdzenie", _string_list(plan.get("followup_windows"))[:3]))
    values.extend(
        _prefixed_labels("źródło", _string_list(plan.get("required_source_connectors"))[:3])
    )
    return values


def post_publication_measurement_summary(plan: Mapping[str, Any]) -> list[str]:
    return _post_publication_measurement_summary(plan)


def _content_wordpress_draft_handoff_status_label(value: str) -> str:
    labels = {
        "blocked_until_draft_checks_complete": "zablokowany do przejścia kontroli szkicu",
        "blocked_until_draft_readiness_review": "zablokowany do sprawdzenia gotowości szkicu",
        "blocked_until_wordpress_draft_handoff_action": "zablokowany do osobnego kroku WordPress",
    }
    return labels.get(value, _content_contract_label(value))


def _post_publication_measurement_status_label(value: str) -> str:
    labels = {
        "blocked_until_publish_and_followup_data": (
            "zablokowany do publikacji i danych po publikacji"
        ),
    }
    return labels.get(value, _content_contract_label(value))


def _draft_title(topic: str, mode: str) -> str:
    prefix = "Odświeżenie" if mode in {"refresh", "merge"} else "Plan treści"
    return f"{prefix}: {topic}"


def _draft_excerpt_direction(preview: dict[str, Any]) -> str:
    goal = preview.get("brief_goal")
    if isinstance(goal, str) and goal:
        return goal
    return "Szkic planu treści do sprawdzenia. Nie publikować bez sprawdzenia operatora."


def _draft_content_blocks(preview: dict[str, Any]) -> list[dict[str, str]]:
    outline = preview.get("brief_outline")
    if not isinstance(outline, list):
        return []
    blocks: list[dict[str, str]] = []
    for item in outline[:8]:
        if not isinstance(item, dict):
            continue
        section = item.get("section")
        instruction = item.get("instruction")
        if isinstance(section, str) and isinstance(instruction, str):
            blocks.append(
                {
                    "section": section,
                    "section_label": _draft_content_block_label(section),
                    "instruction": instruction,
                }
            )
    return blocks


def _draft_content_block_label(section: str) -> str:
    labels = {
        "intent": "intencja",
        "title_h1": "title i H1",
        "missing_sections": "brakujące sekcje",
        "cta": "wezwanie do działania",
        "faq": "FAQ",
        "internal_links": "linkowanie wewnętrzne",
        "legal_review": "kontrola prawna",
    }
    return labels.get(section, "sekcja do sprawdzenia")
