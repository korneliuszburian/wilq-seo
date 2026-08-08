"""Decomposed service_profile shared implementation."""

from __future__ import annotations

from collections.abc import Iterable

from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.private_source_proposals import PrivateSourceProposalScope
from wilq.content.knowledge.service_profile.contracts import (
    ServiceProfilePrivateProposalRiskTier,
    ServiceProfileReviewActionPriority,
    ServiceProfileReviewActionScope,
)
from wilq.content.knowledge.source_facts import ContentKnowledgeLifecycleStatus


def _percent(value: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((value / total) * 100)


def _risk_order(value: ServiceProfilePrivateProposalRiskTier) -> int:
    return {"high": 0, "medium": 1, "low": 2, "unknown": 3}[value]


def _priority_order(value: ServiceProfileReviewActionPriority) -> int:
    return {"high": 0, "medium": 1, "low": 2}[value]


def _source_scope_order(value: PrivateSourceProposalScope) -> int:
    return {
        "claim_policy": 0,
        "evidence_requirement": 1,
        "service": 2,
        "buyer_problem": 3,
        "cta": 4,
        "metric_signal": 5,
    }[value]


def _review_scope_order(value: ServiceProfileReviewActionScope) -> int:
    return {
        "private_claim_policy_proposal": 0,
        "private_evidence_policy_proposal": 1,
        "public_service_card": 2,
        "private_service_proposal": 3,
        "coverage_gap": 4,
        "general_knowledge_review": 5,
    }[value]


def _lifecycle(card: ContentKnowledgeCard) -> ContentKnowledgeLifecycleStatus:
    return card.lifecycle_status or "seeded_contract_proof"


def _status_label(status: ContentKnowledgeLifecycleStatus) -> str:
    return {
        "seeded_contract_proof": "seed kontraktu, nie wiedza produkcyjna",
        "source_backed_review_required": "źródło istnieje, wymagane review",
        "approved_current": "zatwierdzone i aktualne",
        "stale": "wymaga odświeżenia",
        "rejected": "odrzucone, nie używać",
    }[status]


def _safe_next_step(status: ContentKnowledgeLifecycleStatus) -> str:
    if status == "approved_current":
        return "Może wspierać production-depth po sprawdzeniu live evidence dla zadania."
    if status == "stale":
        return "Odśwież źródło i poproś o review przed użyciem."
    if status == "rejected":
        return "Nie używaj w treściach."
    return "Użyj do analizy/UAT, ale poproś o review przed finalnym draftem."


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.8:
        return "wysoka"
    if confidence >= 0.65:
        return "średnia"
    return "niska"


def _redacted_lineage(lineage: list[str]) -> list[str]:
    return [
        item
        for item in lineage
        if item.startswith("https://") or item.startswith("docs/") or item.startswith("wilq/")
    ]


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
