from __future__ import annotations

import re

from wilq.content.briefs.sales import ContentSalesBriefSeed, ContentSalesBriefSourceFact
from wilq.content.canonical.urls import (
    CONTENT_SOURCE_SITE_HOSTS,
    content_normalized_path,
    content_url_host,
)
from wilq.content.claims.ledger import ContentClaimLedger, content_claim_entry
from wilq.content.inventory.records import ContentInventoryRecord
from wilq.content.knowledge.source_facts import ekologus_source_fact_registry
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
        wordpress_title_or_h1=decision.wordpress_title_or_h1,
        wordpress_section_headings=decision.wordpress_section_headings,
        wordpress_section_count=decision.wordpress_section_count,
        wordpress_section_inventory_status=decision.wordpress_section_inventory_status,
        wordpress_content_summary=decision.wordpress_content_summary,
        wordpress_content_text=decision.wordpress_content_text,
        wordpress_content_source_kind=decision.wordpress_content_source_kind,
        wordpress_content_extraction_region=decision.wordpress_content_extraction_region,
        wordpress_content_material_confidence=decision.wordpress_content_material_confidence,
        wordpress_content_source_field_lineage=decision.wordpress_content_source_field_lineage,
        wordpress_content_word_count=decision.wordpress_content_word_count,
        wordpress_content_inventory_status=decision.wordpress_content_inventory_status,
        wordpress_content_inventory_note=decision.wordpress_content_inventory_note,
        wordpress_acf_section_inventory_status=decision.wordpress_acf_section_inventory_status,
        wordpress_acf_section_inventory_note=decision.wordpress_acf_section_inventory_note,
        wordpress_acf_field_names=decision.wordpress_acf_field_names,
        wordpress_acf_section_headings=decision.wordpress_acf_section_headings,
        wordpress_acf_section_count=decision.wordpress_acf_section_count,
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
        total_clicks=decision.total_clicks,
        total_impressions=decision.total_impressions,
        aggregate_ctr=decision.aggregate_ctr,
        best_average_position=decision.best_average_position,
        query_count=decision.query_count,
        primary_query=decision.primary_query,
        metric_facts=decision.metric_facts,
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
            content_claim_entry(
                claim_id=f"claim_content_source_{item.id}",
                claim_text=_source_backed_content_claim(item),
                claim_type="service_claim",
                evidence_ids=[evidence_id],
                source_connectors=item.source_connectors,
                reviewer_id="wilku",
                human_reviewed=True,
            ),
            content_claim_entry(
                claim_id=f"claim_no_ranking_guarantee_{item.id}",
                claim_text="Odświeżenie tej treści poprawi pozycje SEO.",
                claim_type="seo_claim",
                evidence_ids=item.evidence_ids[:1],
                source_connectors=item.source_connectors,
            ),
            content_claim_entry(
                claim_id=f"claim_no_lead_growth_{item.id}",
                claim_text="Ta treść zwiększy liczbę leadów.",
                claim_type="business_outcome_claim",
                evidence_ids=item.evidence_ids[:1],
                source_connectors=item.source_connectors,
            ),
            content_claim_entry(
                claim_id=f"claim_no_success_guarantee_{item.id}",
                claim_text="Publikacja gwarantuje wzrost widoczności.",
                claim_type="guarantee_claim",
                evidence_ids=item.evidence_ids[:1],
                source_connectors=item.source_connectors,
            ),
        ],
    )


def _source_backed_content_claim(item: ContentWorkItem) -> str:
    topic = item.topic.strip().rstrip(".")
    if item.final_canonical_url:
        return (
            f"WILQ ma dowody źródłowe, że temat „{topic}” dotyczy istniejącej "
            "publicznej treści Ekologus i wymaga pracy w trybie odświeżenia "
            "albo scalenia, nie automatycznego tworzenia nowej strony."
        )
    return (
        f"WILQ ma dowody źródłowe dla tematu „{topic}”, ale finalny adres "
        "i ryzyko duplikacji muszą zostać sprawdzone przed szkicem."
    )


def content_sales_brief_seed_from_decision(
    decision: ContentDecisionItem,
) -> ContentSalesBriefSeed:
    primary_query = decision.primary_query or (
        decision.queries[0] if decision.queries else decision.title
    )
    source_fact_ids_by_evidence = _source_fact_ids_by_evidence()
    return ContentSalesBriefSeed(
        target_reader="osoba odpowiedzialna za decyzję środowiskową w firmie",
        buyer_problem=decision.summary or decision.title,
        buyer_trigger=f"użytkownik szuka informacji lub pomocy dla tematu: {primary_query}",
        search_intent="informacyjno-usługowy",
        service_fit="sprawdzenie, czy temat pasuje do usługi Ekologus przed szkicem",
        h1_direction=_decision_h1_direction(decision),
        h2_direction=_decision_h2_direction(decision),
        faq_direction=_decision_faq_direction(decision, primary_query),
        cta_direction=_decision_cta_direction(decision),
        internal_link_direction=["https://ekologus.pl/kontakt/"],
        source_facts=[
            ContentSalesBriefSourceFact(
                evidence_id=evidence_id,
                source_connector=_source_connector_for_evidence(decision, index),
                summary=_source_fact_summary(decision, evidence_id),
                source_fact_ids=source_fact_ids_by_evidence.get(evidence_id, []),
            )
            for index, evidence_id in enumerate(decision.evidence_ids)
        ],
        missing_evidence=[],
    )


def _source_fact_ids_by_evidence() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for fact in ekologus_source_fact_registry().facts:
        if fact.review_status != "approved":
            continue
        for evidence_id in fact.evidence_ids:
            mapping.setdefault(evidence_id, []).append(fact.source_id)
    return mapping


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
    existing_headings = _usable_inventory_headings(decision.wordpress_section_headings)
    if existing_headings:
        return existing_headings[:4]
    if _decision_is_homepage(decision):
        return [
            "W czym pomaga Ekologus",
            "Kiedy warto skonsultować obowiązki środowiskowe",
            "Jak przygotować się do rozmowy",
        ]
    if (
        decision.wordpress_content_inventory_status == "available"
        and decision.wordpress_content_text
    ):
        return ["Treść główna (the_content)"]
    return [
        "Najważniejsze pytania odbiorców",
        "Zakres informacji i następny krok",
    ]


def _usable_inventory_headings(headings: list[str]) -> list[str]:
    """Keep content headings while dropping navigation and related-content noise."""
    output: list[str] = []
    ignored_fragments = (
        "zaufali nam",
        "może cię również",
        "powrót",
        "copyright",
        "więcej",
    )
    for raw_heading in headings:
        heading = " ".join(raw_heading.split())
        if not heading or any(fragment in heading.casefold() for fragment in ignored_fragments):
            continue
        # Rendered WordPress content occasionally exposes a full legal or
        # promotional sentence as an H2. It is body copy, not a stable section
        # boundary; keeping it would make the planner invent a section around
        # one sentence instead of working on the source body.
        if len(heading) > 100 or re.search(r"[.!?]$", heading):
            continue
        # Customer stories and testimonial rows often arrive as a heading plus
        # a bracketed year. They belong to page chrome, not to the answer map.
        if re.search(r"\[\s*(?:19|20)\d{2}\s*r?\.?\s*\]", heading, re.IGNORECASE):
            continue
        if heading.casefold().startswith("oferta "):
            continue
        if heading.casefold().startswith("poniżej przedstawiamy często zadawane pytania"):
            heading = "Najczęstsze pytania dotyczące BDO"
        if heading not in output:
            output.append(heading)
        if len(output) == 4:
            break
    return output


def _decision_h1_direction(decision: ContentDecisionItem) -> str:
    if _decision_is_homepage(decision):
        return "Ekologus - doradztwo i outsourcing środowiskowy dla firm"
    return decision.title


def _decision_faq_direction(
    decision: ContentDecisionItem,
    primary_query: str,
) -> list[str]:
    if _decision_is_homepage(decision):
        return [
            "Z jakimi obowiązkami środowiskowymi Ekologus może pomóc firmie?",
            "Jakie informacje przygotować przed kontaktem z Ekologus?",
        ]
    return [f"Co trzeba sprawdzić przed działaniem w temacie: {primary_query}?"]


def _decision_cta_direction(decision: ContentDecisionItem) -> str:
    if _decision_is_homepage(decision):
        return (
            "Zaproponuj kontakt z Ekologus w celu krótkiego opisania sytuacji "
            "firmy i dobrania właściwego obszaru wsparcia, bez obietnicy wyniku."
        )
    return "Zaproponuj kontakt w celu sprawdzenia sytuacji firmy bez obietnicy wyniku."


def _decision_is_homepage(decision: ContentDecisionItem) -> bool:
    urls = (
        decision.final_canonical_url,
        decision.intended_final_url,
        decision.source_public_url,
        decision.page,
    )
    return any(
        content_url_host(url) in {"ekologus.pl", "www.ekologus.pl"}
        and content_normalized_path(url) == "/"
        for url in urls
    )


def _source_connector_for_evidence(decision: ContentDecisionItem, index: int) -> str:
    if index < len(decision.source_connectors):
        return decision.source_connectors[index]
    return decision.source_connectors[0]


def _source_fact_summary(decision: ContentDecisionItem, evidence_id: str) -> str:
    return f"Dowód {evidence_id} wspiera decyzję: {decision.title}."
