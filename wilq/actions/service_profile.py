from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.actions.payloads import (
    SERVICE_PROFILE_KNOWLEDGE_PROMOTION_ACTION_TYPE,
    SERVICE_PROFILE_PRIVATE_PROPOSAL_PROMOTION_ACTION_TYPE,
)
from wilq.evidence.registry import SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
StateLabel = Callable[[Any], str]


def knowledge_promotion_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:6]):
        source_fact_ids = string_list(item.get("source_fact_ids"))
        source_connectors = string_list(item.get("source_connector_labels"))
        required_validation = string_list(item.get("required_validation_labels"))
        blocked_claims = string_list(item.get("blocked_claims"))
        rows = [
            preview_row("Karta", str(item.get("target_card_title") or "karta usługi")),
            preview_row(
                "Status teraz",
                str(item.get("current_lifecycle_label") or "wymaga review"),
            ),
            preview_row(
                "Status po decyzji",
                str(item.get("target_lifecycle_label") or "approved-current po review"),
            ),
            preview_row(
                "Review",
                str(item.get("required_human_role") or "Wilku albo owner wiedzy"),
            ),
        ]
        if source_fact_ids:
            rows.append(preview_row("Source facts", ", ".join(source_fact_ids[:3])))
        if source_connectors:
            rows.append(preview_row("Źródła", ", ".join(source_connectors[:3])))
        if required_validation:
            rows.append(preview_row("Warunki", ", ".join(required_validation[:4])))
        if blocked_claims:
            rows.append(preview_row("Claimy blokowane", ", ".join(blocked_claims[:3])))
        blocked_reason = item.get("promotion_blocked_reason")
        if isinstance(blocked_reason, str) and blocked_reason:
            rows.append(preview_row("Blokada", blocked_reason))
        cards.append(
            ActionPreviewCardViewModel(
                id=f"service_profile_knowledge_promotion_{index}",
                kind="service_profile_knowledge_promotion_review",
                title_label="Awans wiedzy Service Profile do sprawdzenia",
                subtitle_label="request po review, bez edycji knowledge base",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def private_proposal_promotion_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:6]):
        required_validation = string_list(item.get("required_validation_labels"))
        blocked_claims = string_list(item.get("blocked_claims"))
        rows = [
            preview_row("Propozycja", str(item.get("target_card_title") or "private proposal")),
            preview_row("Zakres", str(item.get("scope") or "private source")),
            preview_row("Ryzyko", str(item.get("risk_tier") or "unknown")),
            preview_row("Wsparcie", str(item.get("support_level") or "review-required")),
            preview_row(
                "Aktualność źródła",
                str(item.get("freshness_status") or "do potwierdzenia"),
            ),
            preview_row("Zakres dostępu", str(item.get("audience") or "do potwierdzenia")),
            preview_row(
                "Review",
                str(item.get("required_human_role") or "Wilku albo owner wiedzy"),
            ),
            preview_row("Redakcja", "redacted, bez raw private text"),
        ]
        if required_validation:
            rows.append(preview_row("Warunki", ", ".join(required_validation[:5])))
        if blocked_claims:
            rows.append(preview_row("Claimy blokowane", ", ".join(blocked_claims[:4])))
        blocked_reason = item.get("promotion_blocked_reason")
        if isinstance(blocked_reason, str) and blocked_reason:
            rows.append(preview_row("Blokada", blocked_reason))
        cards.append(
            ActionPreviewCardViewModel(
                id=f"service_profile_private_proposal_promotion_{index}",
                kind="service_profile_private_proposal_promotion_review",
                title_label="Prywatna propozycja Service Profile do sprawdzenia",
                subtitle_label="review redacted źródła, bez promocji i bez zapisu",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def knowledge_promotion_action(
    *,
    source_fact_count: int,
    rows: list[dict[str, Any]],
) -> ActionObject:
    return ActionObject(
        id="act_prepare_service_profile_knowledge_promotion",
        title="Przygotuj request awansu wiedzy Service Profile",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=[SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
        human_diagnosis=(
            "Service Profile ma publiczne karty usługowe ze źródłami, ale nadal "
            "są review-required. WILQ może przygotować audytowalny request awansu "
            "po decyzji Wilka/ownera, bez zmiany wiedzy i bez odblokowania "
            "production-depth."
        ),
        recommended_reason=(
            "Po zebraniu decyzji z review kart usługowych sprawdź, które source "
            "facts mają pełny ślad źródła, review twierdzeń i właściciela decyzji. "
            "Dopiero późniejsza osobna ścieżka audytu może zmienić lifecycle."
        ),
        payload={
            "action_type": SERVICE_PROFILE_KNOWLEDGE_PROMOTION_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "prepare_only",
            "preview_contract": "service_profile_knowledge_promotion_preview_v1",
            "source_connectors": ["public_site"],
            "source_fact_count": source_fact_count,
            "target_lifecycle": "approved_current",
            "payload_preview": rows,
            "payload_preview_total": len(rows),
            "payload_preview_included": len(rows),
            "required_validation": [
                "public_source_trace_review",
                "blocked_claims_review",
                "owner_human_review_record",
                "separate_audited_promotion_request",
            ],
            "blocked_claims": [
                "automatyczny awans wiedzy",
                "production-depth bez owner review",
                "edycja source_facts.json z tej akcji",
                "publikacja lub szkic finalny na podstawie review-required",
            ],
            "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_seed",
    )


def private_proposal_promotion_action(
    *,
    proposal_count: int,
    rows: list[dict[str, Any]],
) -> ActionObject:
    return ActionObject(
        id="act_prepare_service_profile_private_proposal_promotion",
        title="Przygotuj review prywatnych propozycji Service Profile",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=[SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
        human_diagnosis=(
            "Service Profile ma redacted propozycje z ekologus-ai dla usług i "
            "claim-policy. WILQ może przygotować ich review, ale nie może "
            "promować prywatnego źródła ani traktować go jako production-depth "
            "bez decyzji człowieka i osobnego audytu."
        ),
        recommended_reason=(
            "Przed użyciem Eko-Opieki, Audytu zgodności, stylu marki albo "
            "legal-safety w treściach sprawdź redacted source trace, blokowane "
            "twierdzenia, rolę review i wymagany follow-up."
        ),
        payload={
            "action_type": SERVICE_PROFILE_PRIVATE_PROPOSAL_PROMOTION_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "prepare_only",
            "preview_contract": "private_source_proposal_promotion_preview_v1",
            "source_connectors": ["wordpress_ekologus"],
            "private_source_labels": ["ekologus_ai_private_source_catalog"],
            "proposal_count": proposal_count,
            "payload_preview": rows,
            "payload_preview_total": len(rows),
            "payload_preview_included": len(rows),
            "required_validation": [
                "redacted_source_trace_review",
                "private_owner_human_review_record",
                "blocked_claims_review",
                "separate_source_fact_promotion_request",
                "focused_eval_before_policy_or_service_use",
            ],
            "blocked_claims": [
                "automatyczny awans prywatnej propozycji",
                "production-depth bez owner review",
                "edycja source_facts.json z tej akcji",
                "użycie raw private text w publicznej treści",
                "automatyczna bramka brand/legal-safety bez review",
            ],
            "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
            "redacted": True,
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_seed",
    )
