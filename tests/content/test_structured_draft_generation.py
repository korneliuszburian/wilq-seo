from __future__ import annotations

from _marketer_language import assert_marketer_text_has_no_workflow_jargon

from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefSeed,
    ContentSalesBriefSourceFact,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger, content_claim_entry
from wilq.content.drafts.package import ContentDraftPackage, build_content_draft_package
from wilq.content.drafts.structured_generation import (
    build_structured_draft_generation_contract,
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
        "draft_package_status": "ready",
        "draft_package_id": "draft_package_content_work_item_bdo",
        "measurement_window_status": "planned",
        "measurement_window_id": "measure_bdo",
    }
    payload.update(overrides)
    return ContentWorkItem.model_validate(payload)


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
            reason="GSC daje bazę do późniejszego pomiaru.",
            metrics_to_watch=["gsc_clicks", "gsc_impressions"],
            source_connectors=["google_search_console"],
            evidence_ids=["ev_gsc_bdo"],
        ),
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
        safe_next_step="Przygotuj preserve-first brief.",
    )


def _draft_stack() -> tuple[ContentWorkItem, ContentClaimLedger, ContentDraftPackage]:
    item = _item()
    ledger = _claim_ledger()
    inventory = resolve_content_inventory([_inventory()], duplicate_risk="clear")
    preflight = build_content_preflight_verdict(item, inventory)
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
    return item, ledger, draft_result.draft_package


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


def test_structured_generation_blocks_without_required_runtime_inputs() -> None:
    item = _item()
    result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=None,
        claim_ledger=None,
        draft_package=None,
    )

    assert result.contract is None
    codes = {blocker.code for blocker in result.blockers}
    assert {
        "missing_draft_package",
        "missing_sales_brief",
        "missing_claim_ledger",
    } <= codes
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in result.blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )


def test_structured_generation_blocks_mismatched_or_unsafe_inputs() -> None:
    item, ledger, draft_package = _draft_stack()
    brief = _sales_brief(item, ledger)
    mismatched_package = draft_package.model_copy(
        update={"id": "draft_package_other", "work_item_id": "other_item"}
    )
    unsafe_package = draft_package.model_copy(update={"publish_ready": True})
    blocked_ledger = _claim_ledger(blocked=True)

    mismatched = build_structured_draft_generation_contract(
        item=item,
        sales_brief=brief,
        claim_ledger=ledger,
        draft_package=mismatched_package,
    )
    unsafe = build_structured_draft_generation_contract(
        item=item,
        sales_brief=brief,
        claim_ledger=ledger,
        draft_package=unsafe_package,
    )
    blocked = build_structured_draft_generation_contract(
        item=item,
        sales_brief=brief,
        claim_ledger=blocked_ledger,
        draft_package=draft_package,
    )

    assert "draft_package_mismatch" in [blocker.code for blocker in mismatched.blockers]
    assert "draft_package_marked_publish_ready" in [blocker.code for blocker in unsafe.blockers]
    assert "claim_ledger_blocks_generation" in [blocker.code for blocker in blocked.blockers]


def test_structured_generation_returns_strict_schema_contract_for_valid_item() -> None:
    item, ledger, draft_package = _draft_stack()
    brief = _sales_brief(item, ledger)

    result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=brief,
        claim_ledger=ledger,
        draft_package=draft_package,
    )

    assert result.blockers == []
    assert result.contract is not None
    contract = result.contract
    assert contract.schema_name == "wilq_content_structured_draft_v1"
    assert contract.strict_schema is True
    assert contract.publish_ready is False
    assert contract.output_schema["additionalProperties"] is False
    assert contract.output_schema["type"] == "object"
    properties = contract.output_schema["properties"]
    assert isinstance(properties, dict)
    assert "sections" in properties
    assert contract.model_input.language == "pl-PL"
    assert contract.model_input.final_canonical_url == "https://ekologus.pl/bdo/"
    assert contract.model_input.preview_url == "https://ekologus.dev.proudsite.pl/bdo/"
    assert contract.model_input.source_facts[0].evidence_id == "ev_gsc_bdo"
    assert contract.model_input.knowledge_constraints
    assert contract.model_input.sales_brief_signal_quality.status == "review_required"
    assert contract.model_input.sales_brief_signal_quality.evidence_id_count == 2
    assert contract.model_input.sales_brief_signal_quality.source_connector_count == 2
    assert contract.model_input.sales_brief_signal_quality.source_fact_count == 2
    assert (
        contract.model_input.sales_brief_signal_quality.review_required_knowledge_card_count
        >= 1
    )
    assert contract.model_input.sales_brief_signal_quality.measurement_baseline_ready is True
    constraint_types = {
        constraint.constraint_type for constraint in contract.model_input.knowledge_constraints
    }
    assert "evidence_requirement" in constraint_types
    assert constraint_types & {"blocked", "needs_human_review"}
    assert contract.model_input.sections[0].evidence_ids == ["ev_gsc_bdo", "ev_wp_bdo"]
    assert contract.model_input.claims_allowed == [
        "Ekologus pomaga firmom w obowiązkach związanych z BDO."
    ]
    assert len(contract.model_input.claim_markers) == 1
    marker = contract.model_input.claim_markers[0]
    assert marker.claim_id == "claim_service_scope"
    assert marker.claim_text == "Ekologus pomaga firmom w obowiązkach związanych z BDO."
    assert marker.claim_type == "service_claim"
    assert marker.status == "allowed_with_evidence"
    assert marker.strength == "strong"
    assert marker.required is False
    assert marker.evidence_ids == ["ev_wp_bdo"]
    assert marker.source_connectors == ["wordpress_ekologus"]
    assert marker.reviewer_id is None
    assert contract.model_input.human_review_questions
    assert "sales_brief_signal_quality" in contract.system_instruction
    assert "sygnał użyteczny" in contract.user_instruction
    assert "gotowej do publikacji" in contract.system_instruction


def test_structured_generation_blocks_full_draft_on_review_required_knowledge() -> None:
    item, ledger, draft_package = _draft_stack()
    brief = _sales_brief(item, ledger)
    assert {
        constraint.constraint_type for constraint in brief.knowledge_constraints
    } & {"blocked", "needs_human_review"}

    result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=brief,
        claim_ledger=ledger,
        draft_package=draft_package,
        draft_kind="full_draft",
    )

    assert result.contract is None
    assert [blocker.code for blocker in result.blockers] == [
        "review_required_knowledge_for_full_draft"
    ]
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in result.blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )


def test_structured_generation_receives_sales_brief_forbidden_claims() -> None:
    item = _item()
    resolved_ledger = _claim_ledger()
    brief_with_forbidden_claims = _sales_brief(item, _claim_ledger(blocked=True))
    preflight = build_content_preflight_verdict(
        item,
        resolve_content_inventory([_inventory()], duplicate_risk="clear"),
    )
    draft_result = build_content_draft_package(
        item=item,
        preflight=preflight,
        sales_brief=brief_with_forbidden_claims,
        claim_ledger=resolved_ledger,
    )
    assert draft_result.draft_package is not None

    result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=brief_with_forbidden_claims,
        claim_ledger=resolved_ledger,
        draft_package=draft_result.draft_package,
    )

    assert result.blockers == []
    assert result.contract is not None
    assert result.contract.model_input.claims_removed_or_blocked == [
        "Ta treść zwiększy liczbę leadów."
    ]
    assert len(result.contract.model_input.removed_or_blocked_claim_markers) == 1
    marker = result.contract.model_input.removed_or_blocked_claim_markers[0]
    assert marker.claim_id == "claim_more_leads"
    assert marker.claim_text == "Ta treść zwiększy liczbę leadów."
    assert marker.strength == "strong"
    assert marker.required is False
    assert marker.claim_type == "business_outcome_claim"
    assert marker.status == "blocked_until_measurement"
    assert marker.evidence_ids == ["ev_gsc_bdo"]
    assert marker.source_connectors == ["google_search_console"]
