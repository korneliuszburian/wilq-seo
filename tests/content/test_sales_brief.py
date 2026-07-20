from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from wilq.content.briefs import sales as sales_brief_module
from wilq.content.briefs.sales import (
    ContentSalesBriefBuildResult,
    ContentSalesBriefForbiddenClaim,
    ContentSalesBriefSeed,
    ContentSalesBriefSourceFact,
    _looks_like_product_cta_or_topic,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger, content_claim_entry
from wilq.content.enrichment.opportunity import (
    ContentOpportunityEnrichment,
    ContentOpportunityMeasurementBaseline,
    ContentOpportunitySourceFact,
)
from wilq.content.inventory.records import ContentInventoryRecord, resolve_content_inventory
from wilq.content.knowledge.cards import match_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ContentSourceFactRegistry
from wilq.content.preflight.workflow import build_content_preflight_verdict
from wilq.content.workflow.decision_mapping import content_sales_brief_seed_from_decision
from wilq.content.workflow.models import ContentWorkItem
from wilq.schemas import ContentDecisionItem


def _item(**overrides: object) -> ContentWorkItem:
    payload: dict[str, Any] = {
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
        "preflight_status": "brief_allowed",
        "preserve_first_plan_status": "approved",
        "claim_ledger_status": "approved",
        "claim_ledger_id": "claim_ledger_bdo",
        "measurement_window_status": "planned",
        "measurement_window_id": "measure_bdo",
    }
    payload.update(overrides)
    return ContentWorkItem.model_validate(payload)


def _inventory(**overrides: object) -> ContentInventoryRecord:
    payload: dict[str, Any] = {
        "id": "inventory_bdo",
        "url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "content_status": "published",
        "source_connectors": ["wordpress_ekologus"],
        "evidence_ids": ["ev_wp_bdo"],
    }
    payload.update(overrides)
    return ContentInventoryRecord.model_validate(payload)


def _claim_ledger() -> ContentClaimLedger:
    return ContentClaimLedger(
        id="claim_ledger_bdo",
        work_item_id="content_work_item_bdo",
        entries=[
            content_claim_entry(
                claim_id="claim_service_scope",
                claim_text="Ekologus pomaga firmom w obowiązkach związanych z BDO.",
                claim_type="service_claim",
                evidence_ids=["ev_wp_bdo"],
                source_connectors=["wordpress_ekologus"],
            ),
            content_claim_entry(
                claim_id="claim_more_leads",
                claim_text="Ta treść zwiększy liczbę leadów.",
                claim_type="business_outcome_claim",
                evidence_ids=["ev_gsc_bdo"],
                measurement_window_ready=False,
            ),
        ],
    )


def _seed(**overrides: object) -> ContentSalesBriefSeed:
    payload: dict[str, Any] = {
        "target_reader": "Właściciel lub osoba odpowiedzialna za środowisko w firmie",
        "buyer_problem": "Nie wie, czy obowiązki BDO dotyczą jego firmy i co sprawdzić.",
        "buyer_trigger": "Nowy obowiązek, kontrola, audyt albo porządkowanie dokumentów.",
        "search_intent": "Informacyjno-usługowy: zrozumieć obowiązek i wybrać konsultację.",
        "service_fit": "Konsultacja i obsługa obowiązków środowiskowych Ekologus.",
        "h1_direction": "BDO dla firm: kiedy trzeba działać i co sprawdzić",
        "h2_direction": [
            "Kogo dotyczy BDO",
            "Jakie dokumenty przygotować",
            "Kiedy skonsultować sytuację z ekspertem",
        ],
        "faq_direction": [
            "Czy każda firma musi mieć wpis BDO?",
            "Co sprawdzić przed konsultacją?",
        ],
        "cta_direction": "Zaproponuj konsultację bez obietnicy uniknięcia kar.",
        "internal_link_direction": ["https://ekologus.pl/kontakt/"],
        "source_facts": [
            ContentSalesBriefSourceFact(
                evidence_id="ev_gsc_bdo",
                source_connector="google_search_console",
                summary="GSC potwierdza popyt na temat BDO.",
            ),
            ContentSalesBriefSourceFact(
                evidence_id="ev_wp_bdo",
                source_connector="wordpress_ekologus",
                summary="WordPress potwierdza istniejącą publiczną treść.",
            ),
        ],
        "missing_evidence": ["Dokładny zakres usługi wymaga potwierdzenia w ServiceMap."],
    }
    payload.update(overrides)
    return ContentSalesBriefSeed.model_validate(payload)


def _enrichment(**overrides: object) -> ContentOpportunityEnrichment:
    payload: dict[str, Any] = {
        "id": "content_opportunity_enrichment_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "decision_id": "bdo",
        "status": "ready",
        "title": "BDO dla firm",
        "topic": "BDO dla firm",
        "recommended_mode": "refresh",
        "intent": "compliance_risk",
        "intent_label": "intencja ryzyka lub obowiązku",
        "buyer_problem": "Firma nie wie, czy obowiązki BDO dotyczą jej sytuacji.",
        "buyer_trigger": "obawa przed błędem formalnym, terminem albo kontrolą",
        "service_fit": "obsługa środowiskowa i zgodność obowiązków",
        "cta_hypothesis": "Zaproponuj konsultację obowiązków bez gwarancji wyniku.",
        "source_facts": [
            ContentOpportunitySourceFact(
                id="source_fact_queries_bdo",
                signal_kind="gsc_query",
                label="Zapytania GSC",
                summary="bdo dla firm; obowiązki bdo",
                evidence_ids=["ev_gsc_bdo"],
                source_connectors=["google_search_console"],
            ),
            ContentOpportunitySourceFact(
                id="source_fact_wordpress_bdo",
                signal_kind="wordpress_inventory",
                label="Spis WordPress",
                summary="WordPress potwierdza istniejącą publiczną treść.",
                evidence_ids=["ev_wp_bdo"],
                source_connectors=["wordpress_ekologus"],
            ),
        ],
        "measurement_baseline": ContentOpportunityMeasurementBaseline(
            status="ready_to_plan",
            label="baza pomiaru do zaplanowania",
            reason="WILQ ma GSC i WordPress jako bazę planu pomiaru.",
            metrics_to_watch=["gsc_clicks", "gsc_impressions"],
            source_connectors=["google_search_console"],
            evidence_ids=["ev_gsc_bdo"],
        ),
        "blockers": [],
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "safe_next_step": "Przygotuj preserve-first brief.",
    }
    payload.update(overrides)
    return ContentOpportunityEnrichment.model_validate(payload)


def _brief_result(
    *,
    item: ContentWorkItem | None = None,
    inventory_record: ContentInventoryRecord | None = None,
    seed: ContentSalesBriefSeed | None = None,
    enrichment: ContentOpportunityEnrichment | None = None,
) -> ContentSalesBriefBuildResult:
    work_item = item or _item()
    inventory = resolve_content_inventory(
        [inventory_record or _inventory()],
        duplicate_risk="clear",
    )
    preflight = build_content_preflight_verdict(work_item, inventory)
    return build_content_sales_brief(
        item=work_item,
        preflight=preflight,
        inventory=inventory,
        claim_ledger=_claim_ledger(),
        seed=seed or _seed(),
        enrichment=_enrichment() if enrichment is None else enrichment,
        knowledge_match=match_content_knowledge_cards(work_item),
    )


def test_sales_brief_builds_structured_contract_from_valid_work_item() -> None:
    result = _brief_result()

    assert result.blockers == []
    assert result.brief is not None
    assert result.brief.work_item_id == "content_work_item_bdo"
    assert result.brief.operations_context.enrichment_id == (
        "content_opportunity_enrichment_content_work_item_bdo"
    )
    assert result.brief.operations_context.recommended_mode == "refresh"
    assert result.brief.operations_context.source_fact_ids == [
        "source_fact_queries_bdo",
        "source_fact_wordpress_bdo",
    ]
    assert result.brief.final_canonical_url == "https://ekologus.pl/bdo/"
    assert result.brief.preview_url == "https://ekologus.dev.proudsite.pl/bdo/"
    assert result.brief.buyer_problem.startswith("Firma nie wie")
    assert result.brief.buyer_trigger == "obawa przed błędem formalnym, terminem albo kontrolą"
    assert result.brief.service_fit == "obsługa środowiskowa i zgodność obowiązków"
    assert result.brief.cta_direction == (
        "Zaproponuj konsultację obowiązków bez gwarancji wyniku."
    )
    assert result.brief.h2_direction == [
        "Kogo dotyczy BDO",
        "Jakie dokumenty przygotować",
        "Kiedy skonsultować sytuację z ekspertem",
    ]
    assert result.brief.measurement_plan.measurement_window_id == "measure_bdo"
    assert "ekologus_service_environmental_compliance" in result.brief.knowledge_card_ids
    assert "ekologus_cta_consultation_without_guarantee" in result.brief.knowledge_card_ids
    assert "ekologus_evidence_live_connector_requirement" in result.brief.knowledge_card_ids
    assert result.brief.knowledge_constraints
    assert any(
        constraint.card_id == "ekologus_service_bdo_reporting"
        and constraint.evidence_ids == ["ev_content_service_profile_source_facts"]
        for constraint in result.brief.knowledge_constraints
    )
    assert result.brief.measurement_plan.metrics_to_watch == [
        "GSC: kliknięcia dla strony i klastra zapytań",
        "GSC: wyświetlenia, CTR i pozycja dla klastra",
    ]
    assert result.brief.measurement_plan.baseline_source_connectors == [
        "google_search_console"
    ]
    assert result.brief.measurement_plan.baseline_evidence_ids == ["ev_gsc_bdo"]


def test_sales_brief_does_not_attach_unapproved_source_fact_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fact(source_id: str, review_status: str) -> ContentSourceFact:
        return ContentSourceFact(
            source_id=source_id,
            source_type="reviewed_internal",
            privacy_class="redacted_only",
            source_url_or_path="internal://approved-material",
            extracted_fact="Fakt źródłowy.",
            scope="service",
            freshness_date="2026-07-18",
            confidence=0.9,
            review_status=review_status,
            reviewer="wilku" if review_status == "approved" else None,
            evidence_ids=["ev_gsc_bdo"],
            source_connectors=["approved_materials"],
            blocked_claims=["brak gwarancji"] if review_status != "approved" else [],
            target_card_id="ekologus_service_lineage",
            target_card_type="service",
            target_card_title="Usługa testowa",
            evidence_requirements=["review"] if review_status != "approved" else [],
            usage_notes=["review first"] if review_status != "approved" else [],
        )

    registry = ContentSourceFactRegistry(
        facts=[fact("approved_material", "approved"), fact("pending_material", "review_required")],
        fact_count=2,
    )
    monkeypatch.setattr(sales_brief_module, "ekologus_source_fact_registry", lambda: registry)

    result = _brief_result()

    assert result.brief is not None
    assert result.brief.source_facts[0].source_fact_ids == ["approved_material"]
    assert result.brief.measurement_plan.measurement_readiness_label == (
        "baza pomiaru do zaplanowania"
    )
    assert result.brief.signal_quality.status == "review_required"
    assert result.brief.signal_quality.status_label == (
        "sygnał użyteczny, ale wymaga review"
    )
    assert result.brief.signal_quality.evidence_id_count == 2
    assert result.brief.signal_quality.source_connector_count == 2
    assert result.brief.signal_quality.source_fact_count == 2
    assert result.brief.signal_quality.missing_evidence_count == 1
    assert result.brief.signal_quality.review_required_knowledge_card_count >= 1
    assert result.brief.signal_quality.measurement_baseline_ready is True
    assert "Pokaż brief Wilkowi" in result.brief.signal_quality.safe_next_step
    assert result.brief.draft_allowed is False
    assert [claim.claim_id for claim in result.brief.forbidden_claims] == [
        "claim_more_leads"
    ]


def test_sales_brief_does_not_promote_source_fact_without_evidence_into_model_facts() -> None:
    result = _brief_result(
        enrichment=_enrichment(
            source_facts=[
                ContentOpportunitySourceFact(
                    id="private_review_required_fact",
                    signal_kind="measurement",
                    label="Prywatny materiał Ekologusa",
                    summary="To nie ma jeszcze dowodu do użycia w generowaniu.",
                    evidence_ids=[],
                    source_connectors=["ekologus_ai_private_source_catalog"],
                ),
                ContentOpportunitySourceFact(
                    id="source_fact_queries_bdo",
                    signal_kind="gsc_query",
                    label="Zapytania GSC",
                    summary="bdo dla firm",
                    evidence_ids=["ev_gsc_bdo"],
                    source_connectors=["google_search_console"],
                ),
            ]
        )
    )

    assert result.brief is not None
    assert [fact.evidence_id for fact in result.brief.source_facts] == ["ev_gsc_bdo"]
    assert all("Prywatny materiał" not in fact.summary for fact in result.brief.source_facts)


def test_sales_brief_forbidden_claim_rejects_unknown_claim_enums() -> None:
    payload = {
        "claim_id": "claim_bdo_penalty",
        "claim_text": "Ekologus gwarantuje uniknięcie kar BDO.",
        "claim_type": "guarantee_claim",
        "status": "blocked",
        "evidence_ids": ["ev_content_claim_ledger_bdo"],
        "source_connectors": ["wilq_claim_ledger"],
        "reason": "Claim wymaga blokady w ledgerze.",
    }

    assert ContentSalesBriefForbiddenClaim.model_validate(payload).claim_type == (
        "guarantee_claim"
    )
    with pytest.raises(ValidationError):
        ContentSalesBriefForbiddenClaim.model_validate(
            {**payload, "claim_type": "marketing_vibe_claim"}
        )
    with pytest.raises(ValidationError):
        ContentSalesBriefForbiddenClaim.model_validate(
            {**payload, "status": "approved_by_prompt"}
        )


def test_sales_brief_marks_thin_signal_without_measurement_baseline() -> None:
    result = _brief_result(
        enrichment=_enrichment(
            measurement_baseline=ContentOpportunityMeasurementBaseline(
                status="blocked",
                label="brak bazy pomiaru",
                reason="Brakuje baseline z GSC/GA4.",
                metrics_to_watch=[],
                source_connectors=[],
                evidence_ids=[],
            )
        )
    )

    assert result.blockers == []
    assert result.brief is not None
    assert result.brief.signal_quality.status == "thin"
    assert result.brief.signal_quality.measurement_baseline_ready is False
    assert "zbyt mało dowodów" in result.brief.signal_quality.reason


def test_sales_brief_allows_water_permit_analysis_but_blocks_draft_readiness() -> None:
    result = _brief_result(
        item=_item(
            id="content_work_item_operat_wodnoprawny",
            topic="Operat wodnoprawny",
            source_public_url="https://ekologus.pl/operat-wodnoprawny/",
            final_canonical_url="https://ekologus.pl/operat-wodnoprawny/",
            intended_final_url="https://ekologus.pl/operat-wodnoprawny/",
            evidence_ids=["ev_gsc_operat_wodnoprawny", "ev_wp_operat_wodnoprawny"],
        ),
        inventory_record=_inventory(
            id="inventory_operat_wodnoprawny",
            url="https://ekologus.pl/operat-wodnoprawny/",
            final_canonical_url="https://ekologus.pl/operat-wodnoprawny/",
            intended_final_url="https://ekologus.pl/operat-wodnoprawny/",
            evidence_ids=["ev_wp_operat_wodnoprawny"],
        ),
        seed=_seed(
            source_facts=[
                ContentSalesBriefSourceFact(
                    evidence_id="ev_gsc_operat_wodnoprawny",
                    source_connector="google_search_console",
                    summary="GSC potwierdza popyt na temat operatu wodnoprawnego.",
                ),
                ContentSalesBriefSourceFact(
                    evidence_id="ev_wp_operat_wodnoprawny",
                    source_connector="wordpress_ekologus",
                    summary="WordPress potwierdza publiczną treść o operacie wodnoprawnym.",
                ),
            ],
        ),
        enrichment=_enrichment(
            id="content_opportunity_enrichment_content_work_item_operat_wodnoprawny",
            work_item_id="content_work_item_operat_wodnoprawny",
            decision_id="operat_wodnoprawny",
            title="Operat wodnoprawny",
            topic="Operat wodnoprawny",
            source_facts=[
                ContentOpportunitySourceFact(
                    id="source_fact_queries_operat_wodnoprawny",
                    signal_kind="gsc_query",
                    label="Zapytania GSC",
                    summary="operat wodnoprawny",
                    evidence_ids=["ev_gsc_operat_wodnoprawny"],
                    source_connectors=["google_search_console"],
                ),
                ContentOpportunitySourceFact(
                    id="source_fact_wordpress_operat_wodnoprawny",
                    signal_kind="wordpress_inventory",
                    label="Spis WordPress",
                    summary="WordPress potwierdza publiczną treść o operacie.",
                    evidence_ids=["ev_wp_operat_wodnoprawny"],
                    source_connectors=["wordpress_ekologus"],
                ),
            ],
            measurement_baseline=ContentOpportunityMeasurementBaseline(
                status="ready_to_plan",
                label="baza pomiaru do zaplanowania",
                reason="WILQ ma GSC i WordPress jako bazę planu pomiaru.",
                metrics_to_watch=["gsc_clicks", "gsc_impressions"],
                source_connectors=["google_search_console"],
                evidence_ids=["ev_gsc_operat_wodnoprawny"],
            ),
            evidence_ids=["ev_gsc_operat_wodnoprawny", "ev_wp_operat_wodnoprawny"],
            source_connectors=["google_search_console", "wordpress_ekologus"],
        ),
    )

    assert result.blockers == []
    assert result.brief is not None
    assert "ekologus_service_operat_wodnoprawny" in result.brief.knowledge_card_ids
    assert result.brief.draft_allowed is False
    assert any(
        constraint.card_id == "ekologus_service_operat_wodnoprawny"
        and constraint.constraint_type == "evidence_requirement"
        and "Legal, deadline, fee" in constraint.reason
        for constraint in result.brief.knowledge_constraints
    )
    assert any(
        constraint.card_id == "ekologus_service_operat_wodnoprawny"
        and constraint.constraint_type == "blocked"
        and "gwarancja uzyskania pozwolenia wodnoprawnego" in constraint.reason
        for constraint in result.brief.knowledge_constraints
    )


def test_sales_brief_is_blocked_without_required_evidence() -> None:
    result = _brief_result(
        item=_item(evidence_ids=[]),
        inventory_record=_inventory(evidence_ids=[]),
        seed=_seed(source_facts=[]),
        enrichment=_enrichment(source_facts=[]),
    )

    assert result.brief is None
    assert {blocker.code for blocker in result.blockers} == {
        "missing_evidence",
        "missing_source_fact",
        "preflight_not_ready",
    }


def test_sales_brief_is_blocked_without_final_public_canonical() -> None:
    result = _brief_result(item=_item(final_canonical_url=None))

    assert result.brief is None
    assert "missing_final_canonical" in [blocker.code for blocker in result.blockers]


def test_sales_brief_rejects_dev_preview_as_final_canonical() -> None:
    result = _brief_result(
        item=_item(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/")
    )

    assert result.brief is None
    assert "invalid_final_canonical" in [blocker.code for blocker in result.blockers]


def test_sales_brief_requires_preflight_to_allow_brief_stage() -> None:
    result = _brief_result(item=_item(preserve_first_plan_status="missing"))

    assert result.brief is None
    assert "preflight_not_ready" in [blocker.code for blocker in result.blockers]


def test_sales_brief_requires_measurement_plan_before_brief() -> None:
    result = _brief_result(
        item=_item(measurement_window_status="missing", measurement_window_id=None)
    )

    assert result.brief is None
    assert "missing_measurement_plan" in [blocker.code for blocker in result.blockers]


def test_sales_brief_requires_opportunity_enrichment_before_brief() -> None:
    work_item = _item()
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    preflight = build_content_preflight_verdict(work_item, inventory)

    result = build_content_sales_brief(
        item=work_item,
        preflight=preflight,
        inventory=inventory,
        claim_ledger=_claim_ledger(),
        seed=_seed(),
        knowledge_match=match_content_knowledge_cards(work_item),
    )

    assert result.brief is None
    assert "missing_enrichment" in [blocker.code for blocker in result.blockers]


def test_sales_brief_blocks_when_opportunity_enrichment_is_not_ready() -> None:
    result = _brief_result(
        enrichment=_enrichment(
            status="blocked",
            safe_next_step="Napraw enrichment przed briefem.",
        )
    )

    assert result.brief is None
    assert "enrichment_not_ready" in [blocker.code for blocker in result.blockers]


def test_sales_brief_rejects_source_facts_without_known_evidence_or_connector() -> None:
    result = _brief_result(
        seed=_seed(
            source_facts=[
                ContentSalesBriefSourceFact(
                    evidence_id="ev_unknown",
                    source_connector="unknown_connector",
                    summary="Nieznany fakt.",
                )
            ]
        ),
        enrichment=_enrichment(source_facts=[]),
    )

    assert result.brief is None
    assert {blocker.code for blocker in result.blockers} == {
        "unknown_source_fact_evidence",
        "unknown_source_fact_connector",
    }


def test_sales_brief_blocks_product_cta_without_merchant_or_shop_evidence() -> None:
    result = _brief_result(
        item=_item(topic="Sorbent do oleju"),
        seed=_seed(
            cta_direction="Kup sorbent do oleju w sklepie Ekologus.",
            source_facts=[
                ContentSalesBriefSourceFact(
                    evidence_id="ev_gsc_bdo",
                    source_connector="google_search_console",
                    summary="GSC pokazuje zapytania produktowe o sorbent.",
                )
            ],
        ),
        enrichment=_enrichment(
            title="Sorbent do oleju",
            topic="Sorbent do oleju",
            cta_hypothesis="Kup sorbent do oleju w sklepie Ekologus.",
            source_facts=[],
            source_connectors=["google_search_console"],
            evidence_ids=["ev_gsc_bdo"],
        ),
    )

    assert result.brief is None
    assert "missing_product_evidence" in [blocker.code for blocker in result.blockers]


def test_product_guard_does_not_misclassify_legal_productowa_language() -> None:
    assert not _looks_like_product_cta_or_topic(
        "Informacja o gospodarce opakowaniami i opłacie produktowej"
    )
    assert _looks_like_product_cta_or_topic("Kup sorbent w sklepie Ekologus")


def test_inventory_seed_drops_dated_testimonial_headings() -> None:
    decision = ContentDecisionItem(
        id="inventory_packaging",
        decision_type="refresh_or_merge",
        title="Gospodarka opakowaniami",
        queries=["gospodarka opakowaniami"],
        wordpress_section_headings=[
            "Obowiązki przedsiębiorcy",
            "SERTOP Sp. z o.o. [2013 r.]",
            "Jak przygotować dokumenty?",
        ],
        evidence_ids=["ev_wp"],
        source_connectors=["wordpress_ekologus"],
        rationale="Istniejąca treść wymaga odświeżenia.",
        next_step="Sprawdź materiał.",
        source_public_url="https://www.ekologus.pl/informacja-o-opakowaniach/",
        final_canonical_url="https://www.ekologus.pl/informacja-o-opakowaniach/",
        intended_final_url="https://www.ekologus.pl/informacja-o-opakowaniach/",
        inventory_gate_status="confirmed_current_inventory",
        duplicate_gate_status="checked",
    )

    seed = content_sales_brief_seed_from_decision(decision)

    assert seed.h2_direction == [
        "Obowiązki przedsiębiorcy",
        "Jak przygotować dokumenty?",
    ]


def test_product_guard_ignores_product_words_in_metric_fact_summaries() -> None:
    result = _brief_result(
        item=_item(topic="Gospodarka opakowaniami"),
        seed=_seed(
            cta_direction="Zaproponuj konsultację obowiązków bez gwarancji wyniku.",
            source_facts=[
                ContentSalesBriefSourceFact(
                    evidence_id="ev_gsc_packaging",
                    source_connector="google_search_console",
                    summary="Zapytania: produkty opakowaniowe; odpady opakowaniowe.",
                )
            ],
        ),
        enrichment=_enrichment(
            title="Gospodarka opakowaniami",
            topic="Gospodarka opakowaniami",
            cta_hypothesis="Zaproponuj konsultację obowiązków bez gwarancji wyniku.",
            source_facts=[],
            source_connectors=["google_search_console"],
            evidence_ids=["ev_gsc_packaging"],
        ),
    )

    assert "missing_product_evidence" not in [blocker.code for blocker in result.blockers]


def test_sales_brief_allows_product_cta_with_merchant_evidence() -> None:
    result = _brief_result(
        item=_item(
            topic="Sorbent do oleju",
            evidence_ids=["ev_gsc_bdo", "ev_merchant_sorbent"],
            source_connectors=["google_search_console", "google_merchant_center"],
        ),
        inventory_record=_inventory(
            evidence_ids=["ev_merchant_sorbent"],
            source_connectors=["google_merchant_center"],
        ),
        seed=_seed(
            cta_direction="Kup sorbent do oleju w sklepie Ekologus.",
            source_facts=[
                ContentSalesBriefSourceFact(
                    evidence_id="ev_merchant_sorbent",
                    source_connector="google_merchant_center",
                    summary="Merchant potwierdza produktowy dowód dla sorbentu.",
                )
            ],
        ),
        enrichment=_enrichment(
            title="Sorbent do oleju",
            topic="Sorbent do oleju",
            cta_hypothesis="Kup sorbent do oleju w sklepie Ekologus.",
            source_facts=[],
            source_connectors=["google_search_console", "google_merchant_center"],
            evidence_ids=["ev_gsc_bdo", "ev_merchant_sorbent"],
            measurement_baseline=ContentOpportunityMeasurementBaseline(
                status="ready_to_plan",
                label="baza pomiaru do zaplanowania",
                reason="Merchant daje dowód produktowy, GSC daje popyt.",
                metrics_to_watch=["gsc_clicks", "gsc_impressions"],
                source_connectors=["google_search_console", "google_merchant_center"],
                evidence_ids=["ev_gsc_bdo", "ev_merchant_sorbent"],
            ),
        ),
    )

    assert result.brief is not None
    assert "missing_product_evidence" not in [blocker.code for blocker in result.blockers]


def test_sales_brief_blocks_when_required_knowledge_cards_are_missing() -> None:
    work_item = _item(
        topic="Neutralny temat bez dopasowania",
        source_public_url="https://ekologus.pl/neutralny-temat/",
        final_canonical_url="https://ekologus.pl/neutralny-temat/",
        intended_final_url="https://ekologus.pl/neutralny-temat/",
        evidence_ids=["ev_neutral"],
    )
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    preflight = build_content_preflight_verdict(work_item, inventory)

    result = build_content_sales_brief(
        item=work_item,
        preflight=preflight,
        inventory=inventory,
        claim_ledger=_claim_ledger(),
        seed=_seed(),
        enrichment=_enrichment(),
        knowledge_match=match_content_knowledge_cards(work_item),
    )

    assert result.brief is None
    assert "missing_required_knowledge_card" in [blocker.code for blocker in result.blockers]
    assert any("karty usługi" in blocker.label.lower() for blocker in result.blockers)


def test_sales_brief_blocks_when_knowledge_match_is_not_supplied() -> None:
    work_item = _item()
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    preflight = build_content_preflight_verdict(work_item, inventory)

    result = build_content_sales_brief(
        item=work_item,
        preflight=preflight,
        inventory=inventory,
        claim_ledger=_claim_ledger(),
        seed=_seed(),
        enrichment=_enrichment(),
    )

    assert result.brief is None
    assert [blocker.code for blocker in result.blockers] == ["missing_required_knowledge_card"]
