from __future__ import annotations

from _marketer_language import assert_marketer_text_has_no_workflow_jargon

from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefSeed,
    ContentSalesBriefSourceFact,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger, content_claim_entry
from wilq.content.drafts.package import (
    _section_purpose,
    build_content_draft_package,
)
from wilq.content.enrichment.opportunity import (
    ContentOpportunityEnrichment,
    ContentOpportunityMeasurementBaseline,
)
from wilq.content.inventory.records import ContentInventoryRecord, resolve_content_inventory
from wilq.content.knowledge.cards import match_content_knowledge_cards
from wilq.content.preflight.workflow import build_content_preflight_verdict
from wilq.content.workflow.models import ContentWorkItem


def _item(**overrides: object) -> ContentWorkItem:
    payload: dict[str, object] = {
        "id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "duplicate_status": "checked",
        "preflight_status": "draft_allowed",
        "preserve_first_plan_status": "approved",
        "sales_brief_status": "approved",
        "sales_brief_id": "sales_brief_content_work_item_bdo",
        "claim_ledger_status": "approved",
        "claim_ledger_id": "claim_ledger_bdo",
        "measurement_window_status": "planned",
        "measurement_window_id": "measure_bdo",
    }
    payload.update(overrides)
    return ContentWorkItem(**payload)


def _inventory() -> ContentInventoryRecord:
    return ContentInventoryRecord(
        id="inventory_bdo",
        url="https://ekologus.pl/bdo/",
        final_canonical_url="https://ekologus.pl/bdo/",
        intended_final_url="https://ekologus.pl/bdo/",
        preview_url="https://ekologus.dev.proudsite.pl/bdo/",
        content_status="published",
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_bdo"],
    )


def _claim_ledger(*, blocked: bool = False) -> ContentClaimLedger:
    entry = (
        content_claim_entry(
            claim_id="claim_more_leads",
            claim_text="Ta treść zwiększy liczbę leadów.",
            claim_type="business_outcome_claim",
            evidence_ids=["ev_gsc_bdo"],
            source_connectors=["google_search_console"],
            measurement_window_ready=False,
        )
        if blocked
        else content_claim_entry(
            claim_id="claim_service_scope",
            claim_text="Ekologus pomaga firmom w obowiązkach związanych z BDO.",
            claim_type="service_claim",
            evidence_ids=["ev_wp_bdo"],
            source_connectors=["wordpress_ekologus"],
        )
    )
    return ContentClaimLedger(
        id="claim_ledger_bdo",
        work_item_id="content_work_item_bdo",
        entries=[entry],
    )


def _seed() -> ContentSalesBriefSeed:
    return ContentSalesBriefSeed(
        target_reader="Osoba odpowiedzialna za środowisko w firmie",
        buyer_problem="Nie wie, czy obowiązki BDO dotyczą jego firmy.",
        buyer_trigger="Kontrola, audyt albo porządkowanie dokumentów.",
        search_intent="Informacyjno-usługowy.",
        service_fit="Konsultacja i obsługa obowiązków środowiskowych.",
        h1_direction="BDO dla firm: co sprawdzić",
        h2_direction=["Kogo dotyczy BDO", "Kiedy skonsultować sytuację"],
        faq_direction=["Czy każda firma musi mieć BDO?"],
        cta_direction="Zaproponuj konsultację bez obietnicy wyniku.",
        internal_link_direction=["https://ekologus.pl/kontakt/"],
        source_facts=[
            ContentSalesBriefSourceFact(
                evidence_id="ev_gsc_bdo",
                source_connector="google_search_console",
                summary="GSC potwierdza popyt na temat.",
            ),
            ContentSalesBriefSourceFact(
                evidence_id="ev_wp_bdo",
                source_connector="wordpress_ekologus",
                summary="WordPress potwierdza istniejącą treść.",
            ),
        ],
    )


def _enrichment() -> ContentOpportunityEnrichment:
    return ContentOpportunityEnrichment(
        id="content_opportunity_enrichment_content_work_item_bdo",
        work_item_id="content_work_item_bdo",
        decision_id="bdo",
        status="ready",
        title="BDO dla firm",
        topic="BDO dla firm",
        recommended_mode="refresh",
        intent="compliance_risk",
        intent_label="intencja ryzyka lub obowiązku",
        buyer_problem="Firma nie wie, czy obowiązki BDO dotyczą jej sytuacji.",
        buyer_trigger="obawa przed błędem formalnym, terminem albo kontrolą",
        service_fit="obsługa środowiskowa i zgodność obowiązków",
        cta_hypothesis="Zaproponuj konsultację obowiązków bez gwarancji wyniku.",
        measurement_baseline=ContentOpportunityMeasurementBaseline(
            status="ready_to_plan",
            label="baza pomiaru do zaplanowania",
            reason="GSC i WordPress dają bazę do późniejszego pomiaru.",
            metrics_to_watch=["gsc_clicks", "gsc_impressions"],
            source_connectors=["google_search_console"],
            evidence_ids=["ev_gsc_bdo"],
        ),
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
        safe_next_step="Przygotuj preserve-first brief.",
    )


def _preflight(item: ContentWorkItem):
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    return build_content_preflight_verdict(item, inventory)


def _sales_brief(item: ContentWorkItem, ledger: ContentClaimLedger) -> ContentSalesBrief:
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    preflight = build_content_preflight_verdict(item, inventory)
    result = build_content_sales_brief(
        item=item,
        preflight=preflight,
        inventory=inventory,
        claim_ledger=ledger,
        seed=_seed(),
        enrichment=_enrichment(),
        knowledge_match=match_content_knowledge_cards(item),
    )
    assert result.brief is not None
    return result.brief


def test_draft_package_blocks_without_draft_allowed_preflight() -> None:
    item = _item(sales_brief_status="missing", sales_brief_id=None)
    ledger = _claim_ledger()
    brief = _sales_brief(_item(), ledger)

    result = build_content_draft_package(
        item=item,
        preflight=_preflight(item),
        sales_brief=brief,
        claim_ledger=ledger,
    )

    assert result.draft_package is None
    assert "preflight_not_draft_allowed" in [blocker.code for blocker in result.blockers]
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in result.blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )


def test_draft_package_blocks_without_sales_brief() -> None:
    item = _item()
    result = build_content_draft_package(
        item=item,
        preflight=_preflight(item),
        sales_brief=None,
        claim_ledger=_claim_ledger(),
    )

    assert result.draft_package is None
    assert "missing_sales_brief" in [blocker.code for blocker in result.blockers]
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in result.blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )


def test_draft_package_blocks_when_claim_ledger_is_missing_or_blocking() -> None:
    item = _item()
    brief = _sales_brief(item, _claim_ledger())

    missing = build_content_draft_package(
        item=item,
        preflight=_preflight(item),
        sales_brief=brief,
        claim_ledger=None,
    )
    blocked = build_content_draft_package(
        item=item,
        preflight=_preflight(item),
        sales_brief=brief,
        claim_ledger=_claim_ledger(blocked=True),
    )

    assert "missing_claim_ledger" in [blocker.code for blocker in missing.blockers]
    assert "claim_ledger_blocks_draft" in [blocker.code for blocker in blocked.blockers]
    assert_marketer_text_has_no_workflow_jargon(
        text
        for result in (missing, blocked)
        for blocker in result.blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )


def test_draft_package_is_outline_first_and_not_publish_ready() -> None:
    item = _item()
    ledger = _claim_ledger()
    brief = _sales_brief(item, ledger)

    result = build_content_draft_package(
        item=item,
        preflight=_preflight(item),
        sales_brief=brief,
        claim_ledger=ledger,
    )

    assert result.blockers == []
    assert result.draft_package is not None
    assert result.draft_package.draft_kind == "outline"
    assert result.draft_package.publish_ready is False
    assert result.draft_package.brief_id == brief.id
    assert result.draft_package.claim_ledger_id == ledger.id
    assert result.draft_package.section_to_evidence_map
    assert result.draft_package.section_to_evidence_map[0].evidence_ids == [
        "ev_gsc_bdo",
        "ev_wp_bdo",
    ]
    assert result.draft_package.human_review_questions
    assert_marketer_text_has_no_workflow_jargon(result.draft_package.human_review_questions)
    assert result.draft_package.claims_used == [
        "Ekologus pomaga firmom w obowiązkach związanych z BDO."
    ]


def test_draft_outline_for_the_content_does_not_invent_section_purpose() -> None:
    assert _section_purpose("Treść główna (the_content)") == (
        "Zdecyduj, które informacje z istniejącego tekstu głównego zachować, "
        "uzupełnić albo przepisać."
    )


def test_draft_package_carries_sales_brief_forbidden_claims_to_generation_gate() -> None:
    item = _item()
    resolved_ledger = _claim_ledger()
    brief_with_forbidden_claims = _sales_brief(item, _claim_ledger(blocked=True))

    result = build_content_draft_package(
        item=item,
        preflight=_preflight(item),
        sales_brief=brief_with_forbidden_claims,
        claim_ledger=resolved_ledger,
    )

    assert result.blockers == []
    assert result.draft_package is not None
    assert result.draft_package.claims_used == [
        "Ekologus pomaga firmom w obowiązkach związanych z BDO."
    ]
    assert result.draft_package.claims_removed_or_blocked == [
        "Ta treść zwiększy liczbę leadów."
    ]
