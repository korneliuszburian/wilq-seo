from __future__ import annotations

from wilq.content.briefs.sales import ContentSalesBriefSeed, ContentSalesBriefSourceFact
from wilq.content.canonical.urls import CONTENT_SOURCE_SITE_HOSTS, content_url_host
from wilq.content.claims.ledger import ContentClaimLedger, ContentClaimLedgerEntry
from wilq.content.inventory.records import ContentInventoryRecord
from wilq.content.workflow.models import (
    ContentCanonicalStatus,
    ContentDuplicateStatus,
    ContentInventoryStatus,
    ContentWorkItem,
)
from wilq.schemas import ContentDecisionItem


def content_work_item_from_decision(decision: ContentDecisionItem) -> ContentWorkItem:
    final_url = decision.final_canonical_url or decision.intended_final_url
    return ContentWorkItem(
        id=f"content_work_item_{decision.id}",
        topic=decision.title,
        source_public_url=decision.source_public_url or decision.page,
        final_canonical_url=decision.final_canonical_url,
        intended_final_url=decision.intended_final_url or decision.final_canonical_url,
        preview_url=decision.preview_url,
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
        inventory_status=_inventory_status(decision),
        canonical_status=_canonical_status(final_url),
        duplicate_status=_duplicate_status(decision),
    )


def content_inventory_record_from_decision(
    decision: ContentDecisionItem,
) -> ContentInventoryRecord | None:
    final_url = decision.final_canonical_url or decision.intended_final_url
    if final_url is None:
        return None
    return ContentInventoryRecord(
        id=f"inventory_{decision.id}",
        url=decision.source_public_url or decision.page or final_url,
        final_canonical_url=decision.final_canonical_url,
        intended_final_url=decision.intended_final_url or decision.final_canonical_url,
        preview_url=decision.preview_url,
        content_status="published" if decision.wordpress_match == "found" else "unknown",
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        title=decision.title,
        h1=decision.title,
        topic_tags=[decision.primary_query] if decision.primary_query else decision.queries[:3],
    )


def content_claim_ledger_from_work_item(item: ContentWorkItem) -> ContentClaimLedger:
    evidence_id = item.evidence_ids[0]
    return ContentClaimLedger(
        id=f"claim_ledger_{item.id}",
        work_item_id=item.id,
        reviewed_by="wilku",
        entries=[
            ContentClaimLedgerEntry(
                id=f"claim_service_{item.id}",
                claim_text=f"Ekologus może pomóc użytkownikowi w temacie: {item.topic}.",
                claim_type="service_claim",
                status="allowed_with_evidence",
                evidence_ids=[evidence_id],
                reason="Claim jest ogólną deklaracją usługi i ma przypisany dowód źródłowy.",
                reviewer_id="wilku",
            )
        ],
    )


def content_sales_brief_seed_from_decision(
    decision: ContentDecisionItem,
) -> ContentSalesBriefSeed:
    primary_query = decision.primary_query or (
        decision.queries[0] if decision.queries else decision.title
    )
    return ContentSalesBriefSeed(
        target_reader="osoba odpowiedzialna za decyzję środowiskową w firmie",
        buyer_problem=decision.summary or decision.title,
        buyer_trigger=f"użytkownik szuka informacji lub pomocy dla tematu: {primary_query}",
        search_intent="informacyjno-usługowy",
        service_fit="sprawdzenie, czy temat pasuje do usługi Ekologus przed szkicem",
        h1_direction=decision.title,
        h2_direction=_decision_h2_direction(decision),
        faq_direction=[f"Co trzeba sprawdzić przed działaniem w temacie: {primary_query}?"],
        cta_direction="Zaproponuj kontakt w celu sprawdzenia sytuacji firmy bez obietnicy wyniku.",
        internal_link_direction=["https://ekologus.pl/kontakt/"],
        source_facts=[
            ContentSalesBriefSourceFact(
                evidence_id=evidence_id,
                source_connector=_source_connector_for_evidence(decision, index),
                summary=_source_fact_summary(decision, evidence_id),
            )
            for index, evidence_id in enumerate(decision.evidence_ids)
        ],
        missing_evidence=[],
    )


def _inventory_status(decision: ContentDecisionItem) -> ContentInventoryStatus:
    if decision.inventory_gate_status in {"confirmed_current_inventory"}:
        return "resolved"
    if decision.final_canonical_url or decision.intended_final_url:
        return "resolved"
    return "missing"


def _canonical_status(final_url: str | None) -> ContentCanonicalStatus:
    if final_url is None:
        return "missing"
    if content_url_host(final_url) not in CONTENT_SOURCE_SITE_HOSTS:
        return "blocked"
    return "resolved"


def _duplicate_status(decision: ContentDecisionItem) -> ContentDuplicateStatus:
    if decision.duplicate_gate_status in {
        "existing_public_content_requires_refresh_or_merge",
        "no_duplicate_found",
        "checked",
    }:
        return "checked"
    if decision.duplicate_gate_status:
        return "risk_found"
    return "missing"


def _decision_h2_direction(decision: ContentDecisionItem) -> list[str]:
    if decision.queries:
        return [f"Co wiemy z zapytań: {query}" for query in decision.queries[:2]]
    return ["Co pokazują dane", "Co sprawdzić przed publikacją"]


def _source_connector_for_evidence(decision: ContentDecisionItem, index: int) -> str:
    if index < len(decision.source_connectors):
        return decision.source_connectors[index]
    return decision.source_connectors[0]


def _source_fact_summary(decision: ContentDecisionItem, evidence_id: str) -> str:
    return f"Dowód {evidence_id} wspiera decyzję: {decision.title}."
