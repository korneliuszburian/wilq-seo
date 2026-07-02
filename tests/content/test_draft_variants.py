from __future__ import annotations

from typing import cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefSeed,
    ContentSalesBriefSourceFact,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger, content_claim_entry
from wilq.content.drafts.openai_runtime import (
    OpenAIClientProtocol,
    execute_openai_structured_draft_generation,
)
from wilq.content.drafts.package import ContentDraftPackage, build_content_draft_package
from wilq.content.drafts.structured_generation import StructuredDraftGenerationContract
from wilq.content.drafts.variants import build_content_draft_variants
from wilq.content.enrichment.opportunity import (
    ContentOpportunityEnrichment,
    ContentOpportunityMeasurementBaseline,
)
from wilq.content.inventory.records import ContentInventoryRecord, resolve_content_inventory
from wilq.content.knowledge.cards import match_content_knowledge_cards
from wilq.content.preflight.workflow import build_content_preflight_verdict
from wilq.content.workflow.models import ContentWorkItem


def test_draft_variants_build_structured_contracts_without_publish_or_wordpress() -> None:
    item = _item()
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    preflight = build_content_preflight_verdict(item, inventory)
    ledger = _claim_ledger()
    brief_result = build_content_sales_brief(
        item=item,
        preflight=preflight,
        inventory=inventory,
        claim_ledger=ledger,
        seed=_seed(),
        enrichment=_enrichment(),
        knowledge_match=match_content_knowledge_cards(item),
    )
    assert brief_result.brief is not None
    draft_result = build_content_draft_package(
        item=item,
        preflight=preflight,
        sales_brief=brief_result.brief,
        claim_ledger=ledger,
    )
    assert draft_result.draft_package is not None

    result = build_content_draft_variants(
        item=item.model_copy(
            update={
                "sales_brief_status": "approved",
                "sales_brief_id": brief_result.brief.id,
                "draft_package_status": "ready",
                "draft_package_id": draft_result.draft_package.id,
            }
        ),
        sales_brief=brief_result.brief,
        claim_ledger=ledger,
        draft_package=draft_result.draft_package,
    )

    assert result.blockers == []
    assert [variant.variant_kind for variant in result.variants] == [
        "preserve_first_refresh",
        "problem_led",
        "service_led",
        "faq_supporting",
    ]
    assert (
        result.recommended_variant_id
        == "draft_variant_preserve_first_refresh_content_work_item_bdo"
    )
    assert result.selection_policy.magic_score_used is False
    payload = result.model_dump()
    assert "score" not in payload
    assert all("score" not in variant for variant in payload["variants"])
    assert all("variant_score" not in variant for variant in payload["variants"])
    assert result.safe_next_step.startswith(
        "Sprawdź wariant draft_variant_preserve_first_refresh_content_work_item_bdo"
    )
    preserve_dimensions = [
        dimension
        for dimension in result.comparison_dimensions
        if dimension.variant_kind == "preserve_first_refresh"
    ]
    assert {dimension.dimension for dimension in preserve_dimensions} == {
        "evidence_coverage",
        "service_fit",
        "buyer_problem_fit",
        "cta_fit",
        "duplicate_risk",
        "quality_review_dependency",
    }
    assert {
        dimension.dimension
        for dimension in preserve_dimensions
        if dimension.status == "pass"
    } >= {"evidence_coverage", "duplicate_risk"}
    for variant in result.variants:
        assert variant.publish_ready is False
        assert variant.wordpress_write_allowed is False
        assert variant.evidence_ids == brief_result.brief.evidence_ids
        assert variant.source_connectors == brief_result.brief.source_connectors
        assert variant.generation_result.contract is not None
        assert variant.generation_result.contract.publish_ready is False
        assert variant.generation_result.contract.model_input.work_item_id == item.id
        assert variant.generation_result.contract.model_input.source_facts

    contract = result.variants[0].generation_result.contract
    assert contract is not None
    runtime = execute_openai_structured_draft_generation(
        contract=contract,
        model="gpt-5",
        mode="live",
        client=cast(OpenAIClientProtocol, _FakeOpenAIClient(contract)),
        live_generation_enabled=True,
    )
    assert runtime.status == "generated"
    assert runtime.external_call_attempted is True
    assert runtime.output is not None
    assert runtime.output.publish_ready is False


def test_draft_variants_block_without_sales_brief_claim_gate_or_draft_package() -> None:
    result = build_content_draft_variants(
        item=_item(),
        sales_brief=None,
        claim_ledger=None,
        draft_package=None,
    )

    assert result.variants == []
    assert {
        "missing_sales_brief",
        "missing_claim_ledger",
        "missing_draft_package",
    } <= {blocker.code for blocker in result.blockers}
    assert result.recommended_variant_id is None
    assert result.comparison_dimensions == []
    assert result.selection_policy.magic_score_used is False
    assert result.safe_next_step.startswith("Uzupełnij Sales Brief")


def test_draft_variants_api_returns_typed_variants_without_wordpress_write() -> None:
    item, brief, ledger, draft = _ready_variant_inputs()
    client = TestClient(app)

    response = client.post(
        "/api/content/work-items/draft-variants",
        json={
            "item": item.model_dump(mode="json"),
            "sales_brief": brief.model_dump(mode="json"),
            "claim_ledger": ledger.model_dump(mode="json"),
            "draft_package": draft.model_dump(mode="json"),
        },
    )

    assert response.status_code == 200
    data = response.json()["draft_variants_result"]
    assert data["blockers"] == []
    assert len(data["variants"]) == 4
    assert (
        data["recommended_variant_id"]
        == "draft_variant_preserve_first_refresh_content_work_item_bdo"
    )
    assert data["selection_policy"]["magic_score_used"] is False
    assert len(data["comparison_dimensions"]) == 24
    assert all(variant["publish_ready"] is False for variant in data["variants"])
    assert all(variant["wordpress_write_allowed"] is False for variant in data["variants"])


def _ready_variant_inputs() -> tuple[
    ContentWorkItem,
    ContentSalesBrief,
    ContentClaimLedger,
    ContentDraftPackage,
]:
    item = _item()
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    preflight = build_content_preflight_verdict(item, inventory)
    ledger = _claim_ledger()
    brief_result = build_content_sales_brief(
        item=item,
        preflight=preflight,
        inventory=inventory,
        claim_ledger=ledger,
        seed=_seed(),
        enrichment=_enrichment(),
        knowledge_match=match_content_knowledge_cards(item),
    )
    if brief_result.brief is None:
        raise AssertionError("Expected test brief")
    draft_result = build_content_draft_package(
        item=item,
        preflight=preflight,
        sales_brief=brief_result.brief,
        claim_ledger=ledger,
    )
    if draft_result.draft_package is None:
        raise AssertionError("Expected test draft package")
    ready_item = item.model_copy(
        update={
            "sales_brief_status": "approved",
            "sales_brief_id": brief_result.brief.id,
            "draft_package_status": "ready",
            "draft_package_id": draft_result.draft_package.id,
        }
    )
    return ready_item, brief_result.brief, ledger, draft_result.draft_package


def _item() -> ContentWorkItem:
    return ContentWorkItem(
        id="content_work_item_bdo",
        topic="BDO dla firm",
        source_public_url="https://ekologus.pl/bdo/",
        final_canonical_url="https://ekologus.pl/bdo/",
        intended_final_url="https://ekologus.pl/bdo/",
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
        inventory_status="resolved",
        canonical_status="resolved",
        duplicate_status="checked",
        preflight_status="draft_allowed",
        preserve_first_plan_status="approved",
        sales_brief_status="approved",
        sales_brief_id="sales_brief_content_work_item_bdo",
        claim_ledger_status="approved",
        claim_ledger_id="claim_ledger_bdo",
        draft_package_status="missing",
        measurement_window_status="planned",
        measurement_window_id="measure_bdo",
    )


def _inventory() -> ContentInventoryRecord:
    return ContentInventoryRecord(
        id="inventory_bdo",
        url="https://ekologus.pl/bdo/",
        final_canonical_url="https://ekologus.pl/bdo/",
        intended_final_url="https://ekologus.pl/bdo/",
        content_status="published",
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_bdo"],
    )


def _claim_ledger() -> ContentClaimLedger:
    return ContentClaimLedger(
        id="claim_ledger_bdo",
        work_item_id="content_work_item_bdo",
        entries=[
            content_claim_entry(
                claim_id="claim_service_scope",
                claim_text="Ekologus pomaga firmom uporządkować obowiązki BDO.",
                claim_type="service_claim",
                evidence_ids=["ev_wp_bdo"],
                source_connectors=["wordpress_ekologus"],
            )
        ],
    )


def _seed() -> ContentSalesBriefSeed:
    return ContentSalesBriefSeed(
        target_reader="osoba odpowiedzialna za środowisko w firmie",
        buyer_problem="Firma nie wie, czy obowiązki BDO dotyczą jej sytuacji.",
        buyer_trigger="termin, kontrola albo porządkowanie dokumentów",
        search_intent="intencja ryzyka lub obowiązku",
        service_fit="obsługa środowiskowa i zgodność obowiązków",
        h1_direction="BDO dla firm",
        h2_direction=["Kogo dotyczy BDO", "Jak przygotować dokumenty"],
        faq_direction=["Czy każda firma musi mieć BDO?"],
        cta_direction="Zaproponuj konsultację obowiązków bez gwarancji wyniku.",
        internal_link_direction=["https://ekologus.pl/kontakt/"],
        source_facts=[
            ContentSalesBriefSourceFact(
                evidence_id="ev_gsc_bdo",
                source_connector="google_search_console",
                summary="GSC potwierdza popyt na temat BDO.",
            )
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
            reason="GSC daje bazę do późniejszego pomiaru.",
            metrics_to_watch=["gsc_clicks", "gsc_impressions"],
            source_connectors=["google_search_console"],
            evidence_ids=["ev_gsc_bdo"],
        ),
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
        safe_next_step="Przygotuj preserve-first brief.",
    )


class _FakeResponses:
    def __init__(self, contract: StructuredDraftGenerationContract) -> None:
        self._contract = contract

    def create(self, **_payload: object) -> dict[str, object]:
        model_input = self._contract.model_input
        evidence_id = model_input.source_facts[0].evidence_id
        return {
            "output_parsed": {
                "draft_kind": model_input.draft_kind,
                "language": "pl-PL",
                "title": model_input.title,
                "meta_title": model_input.title,
                "meta_description": "Szkic wariantu do sprawdzenia przez człowieka.",
                "h1": model_input.title,
                "sections": [
                    {
                        "heading": model_input.sections[0].heading,
                        "body_markdown": "Szkic oparty wyłącznie na dowodach WILQ.",
                        "evidence_ids": [evidence_id],
                        "claims_used": model_input.claims_allowed[:1],
                    }
                ],
                "faq": [],
                "cta": model_input.cta_direction,
                "internal_links": [],
                "source_facts_used": [evidence_id],
                "claims_needing_review": [],
                "forbidden_claims_avoided": model_input.claims_removed_or_blocked,
                "human_review_checklist": model_input.human_review_questions,
                "publish_ready": False,
            }
        }


class _FakeOpenAIClient:
    def __init__(self, contract: StructuredDraftGenerationContract) -> None:
        self.responses = _FakeResponses(contract)
