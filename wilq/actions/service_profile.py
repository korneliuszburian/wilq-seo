from __future__ import annotations

from typing import Any

from wilq.actions.payloads import (
    SERVICE_PROFILE_KNOWLEDGE_PROMOTION_ACTION_TYPE,
    SERVICE_PROFILE_PRIVATE_PROPOSAL_PROMOTION_ACTION_TYPE,
)
from wilq.evidence.registry import SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID
from wilq.schemas import ActionMode, ActionObject, ActionRisk, ActionStatus, OpportunityDomain


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
