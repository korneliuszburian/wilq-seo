from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import wilq.content.quality.review_packet_binding as review_packet_binding
import wilq.content.regulatory.policy as regulatory_policy
import wilq.content.workflow.research_packet_derivation as packet_derivation
from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedgerEntry
from wilq.content.drafts.initial_full_draft_document import (
    official_source_references_for_planning_input,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    _digest,
    bind_research_packet_to_planning_input,
)
from wilq.content.planning.input_sources import (
    PLANNING_SOURCE_NAMES,
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
)
from wilq.content.planning.source_pack_projection import (
    project_research_packet_v2_facts,
    project_selected_source_pack_facts,
)
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.source_pack_v2 import SourcePackV2Fact

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


def test_packet_bound_review_rebuilds_exact_projected_source_pack_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _selected_bdo_facts()
    foreign = _fact("foreign_bdo_fact")
    registry = selected + (foreign,)
    by_evidence = {evidence_id: fact for fact in registry for evidence_id in fact.evidence_ids}
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
    base = _planning_input(*registry)
    approved_source_fact_ids = tuple(sorted(fact.source_id for fact in selected))
    packet = SimpleNamespace(
        status="exact_current",
        packet_id="content_research_packet_bdo_editorial",
        packet_digest="a" * 64,
        current_work_item_id=base.work_item_id,
        approved_source_fact_ids=approved_source_fact_ids,
        evidence_ids=tuple(
            evidence_id for fact in selected for evidence_id in fact.evidence_ids
        ),
    )
    expected = bind_research_packet_to_planning_input(
        project_selected_source_pack_facts(base, approved_source_fact_ids, registry),
        packet,
    )
    revision = ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id=base.work_item_id,
        revision_id="content_revision_bdo_editorial",
        content_digest="b" * 64,
        planning_digest="c" * 64,
        planning_input_digest=expected.planning_input_digest,
        content_kind="editorial",
        service_card_id=None,
        research_packet_id=packet.packet_id,
        research_packet_digest=packet.packet_digest,
        sections=[],
    )
    proposal = ContentPlanningProposal.model_construct(
        proposal_id="content_planning_proposal_bdo_editorial",
        work_item_id=base.work_item_id,
        planning_digest=revision.planning_digest,
        planning_input_digest=expected.planning_input_digest,
        content_kind="editorial",
        service_card_id=None,
        research_packet_id=packet.packet_id,
        research_packet_digest=packet.packet_digest,
    )
    snapshot = SimpleNamespace(
        preflight=SimpleNamespace(item=SimpleNamespace(id=base.work_item_id)),
        revision_workspace=SimpleNamespace(latest_revision=revision, context_current=True),
        planning_workspace=SimpleNamespace(proposal=proposal),
    )

    class Store:
        def load_content_research_packet(self, _packet_id: str) -> SimpleNamespace:
            return packet

    monkeypatch.setattr(
        review_packet_binding,
        "ekologus_source_facts",
        lambda: registry,
        raising=False,
    )
    monkeypatch.setattr(
        review_packet_binding,
        "revalidate_content_research_packet",
        lambda **_kwargs: SimpleNamespace(
            status="current",
            packet_id=packet.packet_id,
            packet_digest=packet.packet_digest,
            current_work_item_id=packet.current_work_item_id,
        ),
    )

    resolution = review_packet_binding.resolve_content_review_inputs(
        snapshot=snapshot,
        revision_id=revision.revision_id,
        expected_revision_digest=revision.content_digest,
        workflow_store=Store(),
        planning_input_builder=lambda _snapshot, **_kwargs: SimpleNamespace(
            planning_input=base,
            blockers=[],
        ),
    )

    assert resolution.inputs is not None, resolution.blocker
    assert resolution.inputs.planning_input.planning_input_digest == expected.planning_input_digest
    assert [
        source_fact.source_fact_ids for source_fact in resolution.inputs.planning_input.source_facts
    ] == [[source_id] for source_id in approved_source_fact_ids]


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


def _v2_packet_fact(fact: ContentSourceFact) -> SourcePackV2Fact:
    return SourcePackV2Fact(
        source_fact_id=fact.source_id,
        fact_digest=canonical_json_digest(fact.model_dump(mode="json")),
        text=fact.extracted_fact,
        source_reference=fact.source_url_or_path,
        freshness_date=fact.freshness_date,
        source_type=fact.source_type,
        source_connectors=tuple(sorted(set(fact.source_connectors))),
        evidence_ids=tuple(sorted(set(fact.evidence_ids))),
    )


def _v2_projection_input(
    content_kind: str, selected: ContentSourceFact, caller_only: ContentSourceFact
) -> ContentPlanningInput:
    return _planning_input(selected, caller_only).model_copy(
        update={
            "content_kind": content_kind,
            "confirmed_service_card_id": "ekologus_service_bdo_reporting",
            "source_facts": [
                fact.model_copy(update={"source_fact_ids": []})
                for fact in _planning_input(selected, caller_only).source_facts
            ],
            "evidence_ids": [
                f"ev_{selected.source_id}",
                f"ev_{caller_only.source_id}",
                "ev_inventory_independent",
                "ev_query_independent",
            ],
            "source_connectors": [
                "public_site",
                "localo",
                "wordpress_ekologus",
                "google_search_console",
            ],
            "inventory": _planning_input(selected).inventory.model_copy(
                update={
                    "evidence_ids": ["ev_inventory_independent"],
                    "source_connectors": ["wordpress_ekologus"],
                }
            ),
            "query_portfolio": _planning_input(selected).query_portfolio.model_copy(
                update={
                    "evidence_ids": ["ev_query_independent"],
                    "source_connectors": ["google_search_console"],
                }
            ),
            "regulatory_coverage": ContentRegulatoryCoverage.model_construct(
                applicability_status="required",
                profile_id="bdo",
                profile_version=BDO_PROFILE_VERSION,
                canonical_path=BDO_EDITORIAL_PATH,
                source_fact_ids=[caller_only.source_id],
                evidence_ids=caller_only.evidence_ids,
                source_facts=[caller_only],
            ),
            "claim_ledger": [
                ContentClaimLedgerEntry(
                    id=f"claim_{fact.source_id}",
                    claim_text=fact.extracted_fact,
                    claim_type="service_claim",
                    status="allowed_with_evidence",
                    evidence_ids=fact.evidence_ids,
                    source_connectors=fact.source_connectors,
                    reason="Synthetic reviewed claim.",
                )
                for fact in (selected, caller_only)
            ],
        }
    )


@pytest.mark.parametrize("content_kind", ["service", "editorial"])
def test_v2_packet_projection_uses_only_exact_selected_facts_for_planning(
    content_kind: str,
) -> None:
    selected = _fact("selected_packet_fact")
    caller_only = _fact("caller_only_fact", connector="localo")
    registry = (selected, caller_only)
    planning_input = _v2_projection_input(content_kind, selected, caller_only)
    projected = project_research_packet_v2_facts(
        planning_input,
        (_v2_packet_fact(selected),),
        registry,
    )

    assert [fact.source_fact_ids for fact in projected.source_facts] == [[selected.source_id]]
    assert [fact.summary for fact in projected.source_facts] == [selected.extracted_fact]
    assert [fact.source_fact_id for fact in projected.source_provenance] == [selected.source_id]
    assert caller_only.source_id not in projected.regulatory_coverage.source_fact_ids
    assert caller_only.source_id not in {
        source_fact.source_id for source_fact in projected.regulatory_coverage.source_facts
    }
    assert f"ev_{caller_only.source_id}" not in projected.evidence_ids
    assert [entry.id for entry in projected.claim_ledger] == [f"claim_{selected.source_id}"]
    assert {"ev_inventory_independent", "ev_query_independent"}.issubset(
        projected.evidence_ids
    )
    assert "localo" not in projected.source_connectors
    assert {"wordpress_ekologus", "google_search_console"}.issubset(
        projected.source_connectors
    )
    assert projected.planning_input_digest != planning_input.planning_input_digest
    digest_payload = projected.model_dump(mode="json")
    digest_payload.pop("planning_input_digest")
    expected_digest = _digest(
        {
            "schema_name": projected.schema_name,
            "criteria_version": projected.criteria_version,
            "inventory_mapping_policy": projected.inventory_mapping_policy,
            **digest_payload,
        }
    )
    assert projected.planning_input_digest == expected_digest

    if content_kind == "service":
        assert (
            project_selected_source_pack_facts(
                planning_input, [selected.source_id], registry
            )
            is planning_input
        )


@pytest.mark.parametrize(
    "drift",
    [
        "id",
        "digest",
        "text",
        "source_reference",
        "source_type",
        "connectors",
        "freshness",
        "evidence",
        "registry_text",
        "review_status",
        "privacy_class",
    ],
)
def test_v2_packet_projection_blocks_any_selected_fact_drift(drift: str) -> None:
    selected = _fact("selected_packet_fact")
    planning_input = _planning_input(selected)
    packet_fact = _v2_packet_fact(selected)
    registry = (selected,)
    if drift == "id":
        packet_fact = packet_fact.model_copy(update={"source_fact_id": "missing_fact"})
    elif drift == "digest":
        packet_fact = packet_fact.model_copy(update={"fact_digest": "0" * 64})
    elif drift == "text":
        packet_fact = packet_fact.model_copy(update={"text": "Different preview text."})
    elif drift == "source_reference":
        packet_fact = packet_fact.model_copy(update={"source_reference": "https://example.org"})
    elif drift == "source_type":
        packet_fact = packet_fact.model_copy(update={"source_type": "reviewed_internal"})
    elif drift == "connectors":
        packet_fact = packet_fact.model_copy(update={"source_connectors": ("other_connector",)})
    elif drift == "freshness":
        packet_fact = packet_fact.model_copy(update={"freshness_date": "2025-01-01"})
    elif drift == "evidence":
        packet_fact = packet_fact.model_copy(update={"evidence_ids": ("ev_other",)})
    elif drift == "registry_text":
        registry = (selected.model_copy(update={"extracted_fact": "Changed registry text."}),)
    elif drift == "review_status":
        registry = (selected.model_copy(update={"review_status": "rejected"}),)
    elif drift == "privacy_class":
        registry = (selected.model_copy(update={"privacy_class": "private_local"}),)

    with pytest.raises(ValueError):
        project_research_packet_v2_facts(planning_input, (packet_fact,), registry)


def test_v2_packet_projection_blocks_required_claim_outside_selected_facts() -> None:
    selected = _fact("selected_packet_fact")
    unselected = _fact("caller_only_fact")
    planning_input = _planning_input(selected, unselected).model_copy(
        update={
            "claim_ledger": [
                ContentClaimLedgerEntry(
                    id="required_unselected_claim",
                    claim_text=unselected.extracted_fact,
                    claim_type="service_claim",
                    status="allowed_with_evidence",
                    required=True,
                    evidence_ids=unselected.evidence_ids,
                    source_connectors=unselected.source_connectors,
                    reason="Synthetic required claim.",
                )
            ]
        }
    )

    with pytest.raises(ValueError, match="Required planning claim"):
        project_research_packet_v2_facts(
            planning_input, (_v2_packet_fact(selected),), (selected, unselected)
        )


@pytest.mark.parametrize("claim_type", ["guarantee_claim", "legal_requirement_claim"])
def test_v2_packet_projection_rejects_ledger_inconsistent_claims(claim_type: str) -> None:
    selected = _fact("selected_packet_fact")
    planning_input = _planning_input(selected).model_copy(
        update={
            "claim_ledger": [
                ContentClaimLedgerEntry(
                    id="inconsistent_claim",
                    claim_text=selected.extracted_fact,
                    claim_type=claim_type,
                    status="allowed_with_evidence",
                    evidence_ids=selected.evidence_ids,
                    source_connectors=selected.source_connectors,
                    reason="Synthetic inconsistent claim.",
                )
            ]
        }
    )

    projected = project_research_packet_v2_facts(
        planning_input, (_v2_packet_fact(selected),), (selected,)
    )
    assert projected.claim_ledger == []
