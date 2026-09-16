from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import wilq.content.regulatory.policy as regulatory_policy
import wilq.content.workflow.research_packet_derivation as packet_derivation
from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.drafts.initial_full_draft_document import (
    official_source_references_for_planning_input,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import (
    PLANNING_SOURCE_NAMES,
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
)
from wilq.content.planning.source_pack_projection import (
    project_selected_source_pack_facts,
)
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence

BDO_EDITORIAL_PATH = "/bdo-co-musi-wiedziec-przedsiebiorca"
BDO_PROFILE_VERSION = "2026-07-31-r2"


def _fact(
    source_id: str,
    *,
    requirement_ids: list[str] | None = None,
    official: bool = False,
    canonical_paths: list[str] | None = None,
    connector: str = "public_site",
) -> ContentSourceFact:
    return ContentSourceFact(
        source_id=source_id,
        source_type="legal_update" if official else "public_site",
        privacy_class="commit_safe",
        source_url_or_path=(
            "https://bdo.mos.gov.pl/o-systemie-bdo/"
            if official
            else "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
        ),
        extracted_fact=f"Zatwierdzony fakt {source_id}.",
        scope="claim_policy" if official else "service",
        freshness_date="2026-09-01",
        confidence=1,
        review_status="approved",
        reviewer="wilku",
        evidence_ids=[f"ev_{source_id}"],
        source_connectors=[connector],
        target_card_id="regulatory_bdo" if official else "ekologus_service_bdo_reporting",
        target_card_type="regulatory_source" if official else "service",
        target_card_title="Oficjalne źródło BDO" if official else "BDO",
        official_source=official,
        regulatory_profile_id="bdo" if official else None,
        regulatory_profile_version=BDO_PROFILE_VERSION if official else None,
        regulatory_requirement_ids=requirement_ids or [],
        applicable_canonical_paths=canonical_paths or [],
    )


def _planning_input(*facts: ContentSourceFact) -> ContentPlanningInput:
    return ContentPlanningInput.model_validate(
        {
            "planning_input_digest": "0" * 64,
            "work_item_id": "content_work_item_bdo_editorial",
            "content_kind": "editorial",
            "final_canonical_url": "https://www.ekologus.pl" + BDO_EDITORIAL_PATH + "/",
            "inventory": ContentPlanningInventory(
                status="available",
                content_status="available",
                acf_section_status="missing",
            ),
            "target_reader": "Przedsiębiorca",
            "buyer_problem": "Brak uporządkowanej informacji o BDO.",
            "buyer_trigger": "Potrzeba sprawdzenia obowiązków.",
            "search_intent": "informational",
            "source_facts": [
                ContentPlanningSourceFact(
                    fact_id=f"caller_{fact.source_id}",
                    summary="caller summary must not win",
                    source_connector=fact.source_connectors[0],
                    evidence_ids=fact.evidence_ids,
                    source_fact_ids=[fact.source_id],
                    source_material_ids=["caller_material"],
                )
                for fact in facts
            ],
            "source_assessments": [
                ContentPlanningSourceAssessment(
                    source=source,
                    status="missing",
                    reason="Test source assessment.",
                )
                for source in sorted(PLANNING_SOURCE_NAMES)
            ],
            "query_portfolio": ContentSearchDemandEvidence(
                status="missing",
                optional_ads_status="not_exactly_mapped",
                safe_next_step="Brak exact zapytań.",
            ),
            "measurement_observation_rule": "Nie przypisuj skutku bez pomiaru.",
            "measurement_success_claim_rule": "Wynik wymaga zamkniętego okna pomiaru.",
            "baseline_cta_direction": "Przejdź do kontaktu.",
        }
    )


def _selected_bdo_facts() -> tuple[ContentSourceFact, ...]:
    requirements = [
        "bdo_definition",
        "bdo_registration_scope",
        "bdo_exemptions",
        "bdo_registration_and_updates",
        "bdo_records_and_kpo",
        "bdo_reporting",
        "bdo_access_and_account",
        "bdo_risks_and_sanctions",
    ]
    return (
        _fact("ekologus_public_bdo_faq_2026_07_01"),
        *(
            _fact(
                f"regulatory_source_fact_bdo_{index:02d}",
                requirement_ids=[requirement],
                official=True,
                canonical_paths=[BDO_EDITORIAL_PATH],
                connector="official_regulatory_review",
            )
            for index, requirement in enumerate(
                [*requirements, "bdo_records_and_kpo", "bdo_exemptions"], start=1
            )
        ),
    )


def test_exact_bdo_editorial_pack_hydrates_authoritative_facts_and_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requirements = {
        "bdo_definition",
        "bdo_registration_scope",
        "bdo_exemptions",
        "bdo_registration_and_updates",
        "bdo_records_and_kpo",
        "bdo_reporting",
        "bdo_access_and_account",
        "bdo_risks_and_sanctions",
    }
    selected = _selected_bdo_facts()
    foreign = _fact("ekologus_public_consulting_outsourcing_offer_2026_07_01")
    by_evidence = {evidence_id: fact for fact in selected for evidence_id in fact.evidence_ids}
    monkeypatch.setattr(
        regulatory_policy,
        "list_evidence_by_ids",
        lambda ids: [
            SimpleNamespace(
                id=evidence_id,
                source_id=by_evidence[evidence_id].source_id,
                raw_ref=by_evidence[evidence_id].source_url_or_path,
            )
            for evidence_id in ids
        ],
    )
    projected = project_selected_source_pack_facts(
        _planning_input(*selected, foreign),
        source_fact_ids=[fact.source_id for fact in selected],
        source_facts=selected + (foreign,),
    )

    assert [fact.source_fact_ids[0] for fact in projected.source_facts] == [
        fact.source_id for fact in selected
    ]
    assert len(projected.source_provenance) == 11
    assert {item.source_fact_id for item in projected.source_provenance} == {
        fact.source_id for fact in selected
    }
    assert projected.regulatory_coverage.profile_id == "bdo"
    assert projected.regulatory_coverage.profile_version == BDO_PROFILE_VERSION
    assert {
        item.requirement_id
        for item in projected.regulatory_coverage.requirement_coverage
        if item.evidence_ids
    } == set(requirements)
    assert len(projected.regulatory_coverage.source_facts) == 10
    assert all(
        not fact.source_material_ids
        for fact in projected.source_facts
        if fact.source_fact_ids[0].startswith("regulatory_source_fact_")
    )
    assert projected.planning_input_digest != "0" * 64


def test_projected_bdo_editorial_coverage_builds_exact_official_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _selected_bdo_facts()
    by_evidence = {evidence_id: fact for fact in selected for evidence_id in fact.evidence_ids}
    monkeypatch.setattr(
        regulatory_policy,
        "list_evidence_by_ids",
        lambda ids: [
            SimpleNamespace(
                id=evidence_id,
                source_id=by_evidence[evidence_id].source_id,
                raw_ref=by_evidence[evidence_id].source_url_or_path,
            )
            for evidence_id in ids
        ],
    )
    projected = project_selected_source_pack_facts(
        _planning_input(*selected),
        [fact.source_id for fact in selected],
        selected,
    )

    references = official_source_references_for_planning_input(projected)

    assert len(references) == 10
    assert {reference.source_fact_id for reference in references} == {
        fact.source_id for fact in selected if fact.official_source
    }
    assert all(reference.evidence_ids for reference in references)
    assert all(reference.regulatory_requirement_ids for reference in references)


def test_packet_context_excludes_foreign_regulatory_evidence_after_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _selected_bdo_facts()
    foreign = _fact("foreign_bdo_fact", official=False)
    registry = (*selected, foreign)
    selected_ids = tuple(sorted(fact.source_id for fact in selected))
    selected_evidence = tuple(
        sorted(evidence_id for fact in selected for evidence_id in fact.evidence_ids)
    )
    by_evidence = {evidence_id: fact for fact in registry for evidence_id in fact.evidence_ids}
    monkeypatch.setattr(packet_derivation, "ekologus_source_facts", lambda: registry)
    monkeypatch.setattr(
        regulatory_policy,
        "list_evidence_by_ids",
        lambda ids: [
            SimpleNamespace(
                id=evidence_id,
                source_id=by_evidence[evidence_id].source_id,
                raw_ref=by_evidence[evidence_id].source_url_or_path,
            )
            for evidence_id in ids
        ],
    )
    planning_input = _planning_input(*selected, foreign).model_copy(
        update={
            "evidence_ids": ["ev_foreign_bdo_fact"],
            "regulatory_coverage": ContentRegulatoryCoverage.model_construct(
                applicability_status="required",
                profile_id="bdo",
                profile_version=BDO_PROFILE_VERSION,
                canonical_path=BDO_EDITORIAL_PATH,
                evidence_ids=["ev_foreign_bdo_fact"],
            ),
        }
    )
    identity = SimpleNamespace(
        binding_id="content_delivery_identity_bdo_editorial",
        binding_digest="a" * 64,
        current_work_item_id=planning_input.work_item_id,
        canonical_path=BDO_EDITORIAL_PATH,
        public_url="https://www.ekologus.pl" + BDO_EDITORIAL_PATH + "/",
        classification_run_id="classification_bdo_editorial",
        classification_run_digest="b" * 64,
        classification_decision_set_digest="c" * 64,
        classification_source_row_digest="d" * 64,
        inventory_evidence_ids=("ev_inventory_bdo",),
    )
    source_pack = SimpleNamespace(
        binding_id="content_source_pack_binding_bdo_editorial",
        binding_digest="e" * 64,
        identity_binding_id=identity.binding_id,
        identity_binding_digest=identity.binding_digest,
        current_work_item_id=identity.current_work_item_id,
        source_fact_ids=selected_ids,
        evidence_ids=selected_evidence,
        source_fact_registry_receipt=SimpleNamespace(
            evidence_ids=("ev_registry_bdo",),
            checked_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
        source_fact_authority_receipt_id=None,
        source_fact_authority_receipt_digest=None,
        source_fact_authority_snapshot_digest=None,
        source_fact_authority_provenance_digest=None,
    )
    brief = ContentSalesBrief.model_construct(
        id="brief_bdo_editorial",
        work_item_id=planning_input.work_item_id,
        evidence_ids=["ev_brief_bdo"],
        cta_destination="/kontakt/",
    )
    snapshot = SimpleNamespace(
        sales_brief=SimpleNamespace(sales_brief_result=SimpleNamespace(brief=brief)),
        service_profile_context={},
        freshness_assessment={},
        preflight=SimpleNamespace(item=SimpleNamespace(evidence_ids=["ev_inventory_bdo"])),
    )

    command = packet_derivation.build_server_owned_research_packet_command(
        snapshot=snapshot,
        planning_input=planning_input,
        source_pack=source_pack,
        identity=identity,
        now=datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert not isinstance(command, packet_derivation.ContentResearchPacketBlocker)
    assert command.context_receipt is not None
    assert "ev_foreign_bdo_fact" not in command.context_receipt.regulatory_evidence_ids
    assert set(command.context_receipt.regulatory_evidence_ids) == set(selected_evidence[1:])
