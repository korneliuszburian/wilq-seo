from __future__ import annotations

from wilq.content.briefs.sales import (
    ContentSalesBriefSeed,
    ContentSalesBriefSourceFact,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger, content_claim_entry
from wilq.content.inventory.records import ContentInventoryRecord, resolve_content_inventory
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
        "preflight_status": "brief_allowed",
        "preserve_first_plan_status": "approved",
        "claim_ledger_status": "approved",
        "claim_ledger_id": "claim_ledger_bdo",
        "measurement_window_status": "planned",
        "measurement_window_id": "measure_bdo",
    }
    payload.update(overrides)
    return ContentWorkItem(**payload)


def _inventory(**overrides: object) -> ContentInventoryRecord:
    payload: dict[str, object] = {
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
    return ContentInventoryRecord(**payload)


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
    payload: dict[str, object] = {
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
    return ContentSalesBriefSeed(**payload)


def _brief_result(
    *,
    item: ContentWorkItem | None = None,
    inventory_record: ContentInventoryRecord | None = None,
    seed: ContentSalesBriefSeed | None = None,
):
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
    )


def test_sales_brief_builds_structured_contract_from_valid_work_item() -> None:
    result = _brief_result()

    assert result.blockers == []
    assert result.brief is not None
    assert result.brief.work_item_id == "content_work_item_bdo"
    assert result.brief.final_canonical_url == "https://ekologus.pl/bdo/"
    assert result.brief.preview_url == "https://ekologus.dev.proudsite.pl/bdo/"
    assert result.brief.buyer_problem.startswith("Nie wie")
    assert result.brief.h2_direction == [
        "Kogo dotyczy BDO",
        "Jakie dokumenty przygotować",
        "Kiedy skonsultować sytuację z ekspertem",
    ]
    assert result.brief.measurement_plan.measurement_window_id == "measure_bdo"
    assert result.brief.draft_allowed is False
    assert [claim.claim_id for claim in result.brief.forbidden_claims] == [
        "claim_more_leads"
    ]


def test_sales_brief_is_blocked_without_required_evidence() -> None:
    result = _brief_result(
        item=_item(evidence_ids=[]),
        inventory_record=_inventory(evidence_ids=[]),
        seed=_seed(source_facts=[]),
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
        )
    )

    assert result.brief is None
    assert {blocker.code for blocker in result.blockers} == {
        "unknown_source_fact_evidence",
        "unknown_source_fact_connector",
    }
