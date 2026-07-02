from __future__ import annotations

import argparse
import json
from typing import Any

from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefSeed,
    ContentSalesBriefSourceFact,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import (
    ContentClaimLedger,
    ContentClaimLedgerEntry,
    claim_ledger_blockers,
    content_claim_entry,
    publish_ready_claims,
)
from wilq.content.drafts.package import ContentDraftPackage, build_content_draft_package
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationResult,
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit WILQ Claim Ledger and structured draft gates for Goal 005/006. "
            "Reports whether unsafe claims and publish-ready generation stay blocked."
        )
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    report = build_report()
    if args.format == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


def build_report() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    guarantee = content_claim_entry(
        claim_id="claim_guarantee",
        claim_text="Gwarantujemy brak problemów podczas kontroli.",
        claim_type="guarantee_claim",
        evidence_ids=["ev_public_service"],
        source_connectors=["wordpress_ekologus"],
    )
    checks.append(
        _check(
            "guarantee_claim_blocked",
            guarantee.status == "blocked",
            "Gwarancje efektu są blokowane.",
            {"status": guarantee.status},
        )
    )

    measurement = content_claim_entry(
        claim_id="claim_more_leads",
        claim_text="Ta treść zwiększy liczbę leadów.",
        claim_type="business_outcome_claim",
        evidence_ids=["ev_gsc_bdo"],
        source_connectors=["google_search_console"],
        measurement_window_ready=False,
    )
    checks.append(
        _check(
            "measurement_claim_waits_for_window",
            measurement.status == "blocked_until_measurement",
            "Twierdzenia o wyniku biznesowym czekają na zakończony pomiar.",
            {"status": measurement.status},
        )
    )

    legal = content_claim_entry(
        claim_id="claim_legal",
        claim_text="Firma ma obowiązek rejestracji w BDO.",
        claim_type="legal_requirement_claim",
        evidence_ids=["ev_public_bdo"],
        source_connectors=["wordpress_ekologus"],
        human_reviewed=False,
    )
    checks.append(
        _check(
            "legal_claim_requires_human_review",
            legal.status == "needs_human_review",
            "Twierdzenia prawne wymagają review człowieka.",
            {"status": legal.status},
        )
    )

    missing_connector = content_claim_entry(
        claim_id="claim_missing_connector",
        claim_text="Ekologus pomaga uporządkować obowiązki środowiskowe.",
        claim_type="service_claim",
        evidence_ids=["ev_public_service"],
        source_connectors=[],
    )
    missing_connector_ledger = _ledger([missing_connector])
    missing_connector_codes = [
        blocker.code for blocker in claim_ledger_blockers(missing_connector_ledger)
    ]
    checks.append(
        _check(
            "evidence_claim_requires_source_connector",
            missing_connector.status == "allowed_with_evidence"
            and "missing_source_connector" in missing_connector_codes,
            "Twierdzenie z dowodem bez źródła danych nadal blokuje szkic.",
            {
                "status": missing_connector.status,
                "blockers": missing_connector_codes,
            },
        )
    )

    product_without_product_source = content_claim_entry(
        claim_id="claim_product_without_merchant",
        claim_text="Kup sorbenty Ekologus jako sprawdzone rozwiązanie dla zakładu.",
        claim_type="product_claim",
        evidence_ids=["ev_public_article"],
        source_connectors=["wordpress_ekologus"],
    )
    product_without_product_source_ledger = _ledger([product_without_product_source])
    product_without_product_source_codes = [
        blocker.code for blocker in claim_ledger_blockers(product_without_product_source_ledger)
    ]
    checks.append(
        _check(
            "product_claim_requires_merchant_or_shop_evidence",
            product_without_product_source.status == "allowed_with_evidence"
            and "missing_product_evidence" in product_without_product_source_codes,
            "Twierdzenie produktowe wymaga dowodu z Merchant albo sklepu.",
            {
                "status": product_without_product_source.status,
                "blockers": product_without_product_source_codes,
            },
        )
    )

    safe_ledger = _safe_claim_ledger()
    safe_blockers = claim_ledger_blockers(safe_ledger)
    checks.append(
        _check(
            "safe_service_claim_can_feed_draft",
            not safe_blockers and len(publish_ready_claims(safe_ledger)) == 1,
            "Bezpieczne twierdzenie usługowe z dowodem może wejść do szkicu.",
            {
                "blockers": [blocker.code for blocker in safe_blockers],
                "publish_ready_claim_count": len(publish_ready_claims(safe_ledger)),
            },
        )
    )

    item, ledger, draft_package = _draft_stack()
    sales_brief = _sales_brief(item, ledger)

    missing_ledger_result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=sales_brief,
        claim_ledger=None,
        draft_package=draft_package,
    )
    checks.append(
        _result_check(
            "structured_generation_requires_claim_ledger",
            missing_ledger_result,
            "missing_claim_ledger",
            "Generowanie nie startuje bez sprawdzenia twierdzeń.",
        )
    )

    blocked_ledger_result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=sales_brief,
        claim_ledger=_blocked_measurement_ledger(),
        draft_package=draft_package,
    )
    checks.append(
        _result_check(
            "structured_generation_respects_ledger_blockers",
            blocked_ledger_result,
            "claim_ledger_blocks_generation",
            "Generowanie nie omija zablokowanych twierdzeń.",
        )
    )

    package_with_unknown_claim = draft_package.model_copy(
        update={
            "claims_used": [
                "Ekologus pomaga firmom w obowiązkach związanych z BDO.",
                "Ekologus gwarantuje pełną zgodność po kontakcie.",
            ]
        }
    )
    unknown_claim_result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=sales_brief,
        claim_ledger=ledger,
        draft_package=package_with_unknown_claim,
    )
    checks.append(
        _result_check(
            "structured_generation_blocks_claims_outside_ledger",
            unknown_claim_result,
            "draft_package_claim_outside_ledger",
            "Paczka szkicu nie może wpuścić claimu spoza Claim Ledger do kontraktu modelu.",
        )
    )

    full_draft_result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=sales_brief,
        claim_ledger=ledger,
        draft_package=draft_package,
        draft_kind="full_draft",
    )
    checks.append(
        _result_check(
            "full_draft_requires_approved_knowledge",
            full_draft_result,
            "review_required_knowledge_for_full_draft",
            "Pełny szkic jest blokowany, gdy wiedza nadal wymaga review.",
        )
    )

    valid_result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=sales_brief,
        claim_ledger=ledger,
        draft_package=draft_package,
    )
    checks.append(
        _check(
            "valid_section_contract_stays_review_only",
            valid_result.contract is not None
            and not valid_result.blockers
            and valid_result.contract.publish_ready is False
            and valid_result.contract.output_schema.get("additionalProperties") is False,
            "Poprawny kontrakt sekcji nadal nie może oznaczyć treści jako gotowej do publikacji.",
            {
                "contract_exists": valid_result.contract is not None,
                "publish_ready": (
                    valid_result.contract.publish_ready if valid_result.contract else None
                ),
                "strict_schema": (
                    valid_result.contract.strict_schema if valid_result.contract else None
                ),
            },
        )
    )

    forbidden_brief = _sales_brief(item, _blocked_measurement_ledger())
    preflight = build_content_preflight_verdict(
        item,
        resolve_content_inventory([_inventory()], duplicate_risk="clear"),
    )
    draft_with_removed_claim = build_content_draft_package(
        item=item,
        preflight=preflight,
        sales_brief=forbidden_brief,
        claim_ledger=ledger,
    )
    removed_claim_result = build_structured_draft_generation_contract(
        item=item,
        sales_brief=forbidden_brief,
        claim_ledger=ledger,
        draft_package=draft_with_removed_claim.draft_package,
    )
    removed_marker_count = (
        len(removed_claim_result.contract.model_input.removed_or_blocked_claim_markers)
        if removed_claim_result.contract
        else 0
    )
    checks.append(
        _check(
            "removed_claims_are_visible_to_model_contract",
            removed_claim_result.contract is not None
            and removed_marker_count == 1
            and removed_claim_result.contract.model_input.removed_or_blocked_claim_markers[
                0
            ].status
            == "blocked_until_measurement",
            "Usunięte twierdzenia trafiają do kontraktu jako zakazane, nie znikają po cichu.",
            {"removed_or_blocked_marker_count": removed_marker_count},
        )
    )

    passed = [check for check in checks if check["pass"]]
    failed = [check for check in checks if not check["pass"]]
    return {
        "pass": not failed,
        "check_count": len(checks),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "checks": checks,
        "claim_ledger_blocks": _unique(
            detail
            for check in checks
            for detail in check.get("details", {}).get("blockers", [])
        ),
        "structured_generation_blocks": _unique(
            detail
            for check in checks
            for detail in check.get("details", {}).get("blocker_codes", [])
        ),
        "publish_ready_locked": True,
        "co_pokazac_wilkowi": (
            "WILQ ma działające sprawdzenie twierdzeń: blokuje gwarancje, "
            "twierdzenia prawne bez review, produktowe oferty bez Merchant/sklepu "
            "i obietnice efektu bez pomiaru. Model dostaje tylko kontrakt "
            "review-only, więc nie może sam oznaczyć treści jako gotowej do publikacji."
        ),
        "co_nadal_brakuje": (
            "Production-depth wymaga zatwierdzonych kart wiedzy, review człowieka "
            "i zamkniętych okien pomiaru dla twierdzeń o wynikach."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# WILQ Claim Ledger gate audit",
        "",
        f"- Wynik: {'PASS' if report['pass'] else 'FAIL'}",
        f"- Checki: {report['passed_count']}/{report['check_count']}",
        f"- Publish-ready zablokowane dla modelu: `{str(report['publish_ready_locked']).lower()}`",
        "",
        "## Co pokazać Wilkowi",
        "",
        report["co_pokazac_wilkowi"],
        "",
        "## Co nadal brakuje",
        "",
        report["co_nadal_brakuje"],
        "",
        "## Checki",
        "",
        "| Status | Check | Wniosek |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            "| {status} | `{name}` | {summary} |".format(
                status="OK" if check["pass"] else "FAIL",
                name=check["name"],
                summary=_markdown_cell(check["summary"]),
            )
        )
    if report["structured_generation_blocks"]:
        lines.extend(["", "## Blokady generowania", ""])
        for blocker in report["structured_generation_blocks"]:
            lines.append(f"- `{blocker}`")
    return "\n".join(lines)


def _draft_stack() -> tuple[ContentWorkItem, ContentClaimLedger, ContentDraftPackage]:
    item = _item()
    ledger = _safe_claim_ledger()
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
    if brief_result.brief is None:
        raise RuntimeError("Sales brief fixture did not pass audit setup.")
    draft_result = build_content_draft_package(
        item=item,
        preflight=preflight,
        sales_brief=brief_result.brief,
        claim_ledger=ledger,
    )
    if draft_result.draft_package is None:
        raise RuntimeError("Draft package fixture did not pass audit setup.")
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
    if result.brief is None:
        raise RuntimeError("Sales brief fixture did not pass audit setup.")
    return result.brief


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


def _safe_claim_ledger() -> ContentClaimLedger:
    return _ledger(
        [
            content_claim_entry(
                claim_id="claim_service_scope",
                claim_text="Ekologus pomaga firmom w obowiązkach związanych z BDO.",
                claim_type="service_claim",
                evidence_ids=["ev_wp_bdo"],
                source_connectors=["wordpress_ekologus"],
            )
        ]
    )


def _blocked_measurement_ledger() -> ContentClaimLedger:
    return _ledger(
        [
            content_claim_entry(
                claim_id="claim_more_leads",
                claim_text="Ta treść zwiększy liczbę leadów.",
                claim_type="business_outcome_claim",
                evidence_ids=["ev_gsc_bdo"],
                source_connectors=["google_search_console"],
                measurement_window_ready=False,
            )
        ]
    )


def _ledger(entries: list[ContentClaimLedgerEntry]) -> ContentClaimLedger:
    return ContentClaimLedger(
        id="claim_ledger_bdo",
        work_item_id="content_work_item_bdo",
        entries=entries,
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


def _result_check(
    name: str,
    result: StructuredDraftGenerationResult,
    expected_blocker: str,
    summary: str,
) -> dict[str, Any]:
    blocker_codes = [blocker.code for blocker in result.blockers]
    return _check(
        name,
        result.contract is None and expected_blocker in blocker_codes,
        summary,
        {"blocker_codes": blocker_codes},
    )


def _check(
    name: str,
    passed: bool,
    summary: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "pass": passed,
        "summary": summary,
        "details": details or {},
    }


def _unique(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    return unique_values


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")[:180]


if __name__ == "__main__":
    raise SystemExit(main())
