from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from wilq.codex.prompts import resolve_prompt_template
from wilq.content.drafts import fact_selection, initial_full_draft
from wilq.content.drafts.initial_draft_readability import readability_issues_for_output
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.knowledge.source_facts import ContentSourceFact, SourceFactReviewStatus
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import (
    ContentPlanningInventory,
    ContentPlanningSourceFact,
)
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets


def test_initial_draft_v2_prompt_preserves_copy_and_source_fact_rules() -> None:
    template = resolve_prompt_template("content_initial_draft@v2")

    instruction = template.render(regulatory_draft_directive=" REGULATORY_DIRECTIVE")

    for planning_field in (
        "target_reader",
        "buyer_problem",
        "buyer_trigger",
        "search_intent",
        "angle",
        "value_proposition",
        "reader_question",
        "cta_direction",
        "baseline_cta_direction",
    ):
        assert planning_field in instruction
    assert "Source facts służą wyłącznie do ustalenia treści" in instruction
    assert "approved_source_facts_by_section" in instruction
    assert "co najmniej jeden konkretny fakt" in instruction
    assert "Nie dodawaj faktów" in instruction
    assert "nie powtarzaj tego samego twierdzenia" in instruction
    assert instruction.endswith("REGULATORY_DIRECTIVE")


def _approved_access_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="official_access_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://example.gov.pl/bdo",
        extracted_fact="Użytkownik główny może nadawać uprawnienia w systemie.",
        scope="claim_policy",
        freshness_date="2026-08-01",
        confidence=1,
        review_status="approved",
        reviewer="ekspert",
        evidence_ids=["ev_access"],
        source_connectors=["official_regulatory_review"],
        target_card_id="regulated_service",
        target_card_type="regulatory_source",
        target_card_title="Dostęp do systemu",
        official_source=True,
        regulatory_profile_id="regulated",
        regulatory_profile_version="2026-08",
        regulatory_requirement_ids=["access"],
        applicable_service_card_ids=["service_regulated"],
    )


def test_initial_draft_turn_exposes_server_owned_regulatory_assertions() -> None:
    fact = _approved_access_fact()
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="content_work_item_regulated",
        planning_input_digest="a" * 64,
        confirmed_service_card_id="service_regulated",
        inventory=ContentPlanningInventory(status="available"),
        query_portfolio=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak exact zapytań.",
        ),
        measurement_observation_rule="Porównaj zamknięte okresy.",
        measurement_success_claim_rule="Nie claimuj bez dowodu.",
        source_assessments=[],
        regulatory_coverage=ContentRegulatoryCoverage(
            profile_id="regulated",
            profile_version="2026-08",
            requirements=[
                ContentRegulatoryRequirement(
                    id="access",
                    label="dostęp do konta",
                    reason="Wymaga źródła urzędowego.",
                    document_assertions=[
                        ContentRegulatoryDocumentAssertion(
                            id="roles",
                            label="role lub uprawnienia",
                            required_any_of=["rola", "uprawnien"],
                        )
                    ],
                )
            ],
            source_facts=[fact],
        ),
    )
    proposal = ContentPlanningProposal.model_construct(
        proposal_id="proposal-regulated",
        planning_digest="b" * 64,
        sections=[
            SimpleNamespace(
                section_id="section_access",
                heading="Dostęp",
                purpose="Wyjaśnia dostęp do systemu.",
                reader_question="Kto może nadać dostęp?",
                query_terms=[],
                inventory_disposition="rewrite",
                regulatory_requirement_ids=["access"],
            )
        ],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )
    generation_contract = SimpleNamespace(model_input=SimpleNamespace(model_dump=lambda mode: {}))

    request = initial_full_draft_turn_request(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=generation_contract,
    )

    assert json.loads(request.application_context)["regulatory_document_assertions"] == [
        {
            "requirement_id": "access",
            "assertion_id": "roles",
            "label": "role lub uprawnienia",
            "required_any_of": ["rola", "uprawnien"],
        }
    ]
    compact_proposal = json.loads(request.untrusted_context)["approved_planning_proposal"]
    assert compact_proposal["planning_digest"] == "b" * 64
    assert "page_assets" not in compact_proposal
    assert compact_proposal["sections"][0]["section_id"] == "section_access"
    untrusted_context = json.loads(request.untrusted_context)
    assert untrusted_context["approved_source_facts_by_section"] == [
        {"section_id": "section_access", "source_facts": []}
    ]
    assert untrusted_context["approved_regulatory_facts_by_section"] == [
        {
            "section_id": "section_access",
            "requirement_ids": ["access"],
            "source_facts": [
                {
                    "source_fact_id": "official_access_fact",
                    "summary": "Użytkownik główny może nadawać uprawnienia w systemie.",
                    "evidence_ids": ["ev_access"],
                    "requirement_ids": ["access"],
                }
            ],
        }
    ]
    assert "Source facts służą wyłącznie do ustalenia treści" in request.instruction
    assert "nie powtarzaj tego samego twierdzenia" in request.instruction


def _approved_bdo_fact(
    source_id: str,
    *,
    target_card_id: str,
    target_card_type: str = "evidence_requirement",
    service_fit_terms: list[str] | None = None,
    buyer_problem_terms: list[str] | None = None,
    review_status: SourceFactReviewStatus = "approved",
) -> ContentSourceFact:
    return ContentSourceFact(
        source_id=source_id,
        source_type="public_site",
        privacy_class="commit_safe",
        source_url_or_path=f"https://www.ekologus.pl/{source_id}/",
        extracted_fact=f"Konkretny zatwierdzony fakt BDO: {source_id}.",
        scope="service",
        freshness_date="2026-08-01",
        confidence=1,
        review_status=review_status,
        reviewer="wilku",
        evidence_ids=[f"ev_{source_id}"],
        source_connectors=["public_site"],
        target_card_id=target_card_id,
        target_card_type=target_card_type,
        target_card_title=(
            "BDO i sprawozdawczość środowiskowa"
            if target_card_type == "service"
            else f"Materiał {source_id}"
        ),
        service_fit_terms=service_fit_terms or [],
        buyer_problem_terms=buyer_problem_terms or [],
    )


def _bdo_planning_sections() -> list[ContentPlanningSection]:
    section_specs = [
        ("definition", "Co to jest BDO?", ["bdo definicja"]),
        ("registration", "Kto składa wniosek do BDO?", ["rejestr bdo"]),
        ("exemptions", "Kiedy firma może korzystać ze zwolnienia?", ["zwolnienia bdo"]),
        ("updates", "Jak aktualizować dane w rejestrze?", ["aktualizacja bdo"]),
        ("records", "Jak prowadzić ewidencję odpadów?", ["ewidencja odpadów"]),
        ("reporting", "Jakie sprawozdania składa firma?", ["sprawozdania bdo"]),
        ("access", "Jak nadać uprawnienia w systemie?", ["konto bdo"]),
        ("sanctions", "Jakie konsekwencje wymagają uwagi?", ["kary bdo"]),
    ]
    sections = [
        ContentPlanningSection(
            section_id=f"section_{section_id}",
            heading=heading,
            purpose="Odpowiada na konkretne pytanie przedsiębiorcy.",
            reader_question=heading,
            inventory_disposition="rewrite",
            query_terms=query_terms,
        )
        for section_id, heading, query_terms in section_specs
    ]
    return [
        *sections,
        ContentPlanningSection(
            section_id="section_archival",
            heading="Archiwalne wydarzenie",
            purpose="Wymaga decyzji redakcyjnej.",
            inventory_disposition="remove_review_required",
        ),
    ]


@pytest.fixture
def bdo_source_fact_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ContentPlanningInput, ContentPlanningProposal]:
    service_card_id = "ekologus_service_bdo_reporting"
    direct_fact = _approved_bdo_fact(
        "bdo_records_fact",
        target_card_id="ekologus_evidence_bdo_records",
        service_fit_terms=["ewidencja odpadów"],
    )
    fallback_fact = _approved_bdo_fact(
        "bdo_service_fallback",
        target_card_id=service_card_id,
        target_card_type="service",
        service_fit_terms=["obsługa raportowa"],
    )
    unrelated_facts = [
        _approved_bdo_fact(
            f"unrelated_fact_{index:02d}",
            target_card_id=f"unrelated_card_{index:02d}",
            service_fit_terms=[f"niepowiązany materiał {index}"],
        )
        for index in range(1, 9)
    ]
    colliding_non_service_fact = _approved_bdo_fact(
        "colliding_non_service_fact",
        target_card_id=service_card_id,
        service_fit_terms=["niepowiązany materiał kolizyjny"],
    )
    review_required_fact = _approved_bdo_fact(
        "review_required_records_fact",
        target_card_id="review_required_card",
        service_fit_terms=["ewidencja odpadów"],
        review_status="review_required",
    )
    planning_facts = [
        direct_fact,
        fallback_fact,
        *unrelated_facts,
        colliding_non_service_fact,
        review_required_fact,
    ]
    non_allowlisted_fact = _approved_bdo_fact(
        "non_allowlisted_records_fact",
        target_card_id="non_allowlisted_card",
        service_fit_terms=["ewidencja odpadów"],
    )
    monkeypatch.setattr(
        fact_selection,
        "ekologus_source_facts",
        lambda: (*planning_facts, non_allowlisted_fact),
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="content_work_item_bdo",
        planning_input_digest="a" * 64,
        confirmed_service_card_id=service_card_id,
        service_label="BDO i sprawozdawczość środowiskowa",
        inventory=ContentPlanningInventory(status="available"),
        target_reader="przedsiębiorca",
        buyer_problem="firma musi uporządkować obowiązki BDO",
        buyer_trigger="zbliża się termin rozliczenia",
        search_intent="informational",
        source_facts=[
            ContentPlanningSourceFact(
                fact_id=f"planning_fact_{index:02d}",
                summary=fact.extracted_fact,
                source_connector="public_site",
                evidence_ids=fact.evidence_ids,
                source_fact_ids=[fact.source_id],
            )
            for index, fact in enumerate(planning_facts, start=1)
        ],
        source_assessments=[],
        regulatory_coverage=ContentRegulatoryCoverage(),
        query_portfolio=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak exact zapytań.",
        ),
        measurement_observation_rule="Porównaj zamknięte okresy.",
        measurement_success_claim_rule="Nie claimuj bez dowodu.",
        baseline_cta_direction="Opisz sytuację firmy.",
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=planning_input.work_item_id,
        proposal_id="proposal-bdo",
        planning_digest="b" * 64,
        planning_input_digest=planning_input.planning_input_digest,
        service_card_id=service_card_id,
        service_label=planning_input.service_label,
        target_reader=planning_input.target_reader,
        buyer_problem=planning_input.buyer_problem,
        buyer_trigger=planning_input.buyer_trigger,
        search_intent=planning_input.search_intent,
        cta_direction=planning_input.baseline_cta_direction,
        sections=_bdo_planning_sections(),
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )
    return planning_input, proposal


def test_source_facts_by_section_grounds_every_bdo_section(
    bdo_source_fact_mapping: tuple[ContentPlanningInput, ContentPlanningProposal],
) -> None:
    planning_input, proposal = bdo_source_fact_mapping

    mapping = fact_selection.approved_source_facts_by_section(planning_input, proposal)

    assert len(planning_input.source_facts) == 12
    assert len(mapping) == 8
    assert all(row["source_facts"] for row in mapping)
    assert "section_archival" not in {row["section_id"] for row in mapping}
    definition = next(row for row in mapping if row["section_id"] == "section_definition")
    assert [fact["source_fact_id"] for fact in definition["source_facts"]] == [
        "bdo_service_fallback"
    ]
    mapped_fact_ids = {fact["source_fact_id"] for row in mapping for fact in row["source_facts"]}
    assert mapped_fact_ids == {"bdo_records_fact", "bdo_service_fallback"}


def test_source_facts_by_section_carries_fact_identity_summary_and_evidence(
    bdo_source_fact_mapping: tuple[ContentPlanningInput, ContentPlanningProposal],
) -> None:
    planning_input, proposal = bdo_source_fact_mapping

    mapping = fact_selection.approved_source_facts_by_section(planning_input, proposal)

    for row in mapping:
        for fact in row["source_facts"]:
            assert {"source_fact_id", "summary", "evidence_ids"} <= set(fact)


def test_enrich_benefit_sections_uses_only_missing_benefit_answers() -> None:
    benefit_fact = "pozwala uniknąć kosztów zatrudniania pracowników"
    planning_input = ContentPlanningInput.model_construct(
        source_facts=[
            ContentPlanningSourceFact(
                fact_id="planning_benefit_fact",
                summary=benefit_fact,
                source_connector="public_site",
                evidence_ids=["ev_benefit"],
            )
        ]
    )
    vague_body = "Może obejmować nadzór nad dokumentacją."
    existing_benefit_body = "Stała obsługa zapewnia terminowy nadzór nad dokumentacją."
    non_benefit_body = "Zakres obejmuje nadzór nad dokumentacją."
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Outsourcing środowiskowy",
            meta_title="Outsourcing środowiskowy dla firm",
            meta_description="Zakres i korzyści outsourcingu środowiskowego.",
            h1="Outsourcing środowiskowy",
            lead="Praktyczny opis stałego wsparcia środowiskowego dla firmy.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="benefit_missing",
                heading="Co daje outsourcing?",
                body_markdown=vague_body,
            ),
            ContentInitialDraftSectionOutput(
                section_id="benefit_present",
                heading="Co zyskuje firma?",
                body_markdown=existing_benefit_body,
            ),
            ContentInitialDraftSectionOutput(
                section_id="scope",
                heading="Zakres outsourcingu",
                body_markdown=non_benefit_body,
            ),
        ],
    )

    assert any(
        code == "heading_answer_mismatch" for code, _, _ in readability_issues_for_output(output)
    )
    enriched = initial_full_draft._enrich_benefit_sections(output, planning_input)

    assert "Z korzyści współpracy:" in enriched.sections[0].body_markdown
    assert "koszt" in enriched.sections[0].body_markdown
    assert benefit_fact in enriched.sections[0].body_markdown
    assert not any(
        code == "heading_answer_mismatch" for code, _, _ in readability_issues_for_output(enriched)
    )
    assert enriched.sections[1].body_markdown == existing_benefit_body
    assert enriched.sections[2].body_markdown == non_benefit_body
    assert output.sections[0].body_markdown == vague_body


def test_enrich_benefit_sections_skips_link_bearing_source_fact() -> None:
    safe_fact = "Terminowy nadzór formalno-prawny ogranicza ryzyko opóźnień."
    planning_input = ContentPlanningInput.model_construct(
        source_facts=[
            ContentPlanningSourceFact(
                fact_id="planning_link_benefit_fact",
                summary="Koszt opisano przy [usłudze](https://example.com).",
                source_connector="public_site",
                evidence_ids=["ev_link_benefit"],
            ),
            ContentPlanningSourceFact(
                fact_id="planning_safe_benefit_fact",
                summary=safe_fact,
                source_connector="public_site",
                evidence_ids=["ev_safe_benefit"],
            ),
        ]
    )
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Korzyści outsourcingu",
            meta_title="Korzyści outsourcingu środowiskowego",
            meta_description="Korzyści stałej obsługi środowiskowej dla firmy.",
            h1="Korzyści outsourcingu środowiskowego",
            lead="Praktyczny opis stałego wsparcia środowiskowego dla firmy.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="benefit_missing",
                heading="Co daje outsourcing?",
                body_markdown="Może obejmować nadzór nad dokumentacją.",
            )
        ],
    )

    enriched = initial_full_draft._enrich_benefit_sections(output, planning_input)

    assert safe_fact in enriched.sections[0].body_markdown
    assert "https://example.com" not in enriched.sections[0].body_markdown


def test_initial_draft_turn_exposes_approved_source_facts_by_section(
    bdo_source_fact_mapping: tuple[ContentPlanningInput, ContentPlanningProposal],
) -> None:
    planning_input, proposal = bdo_source_fact_mapping
    generation_contract = SimpleNamespace(model_input=SimpleNamespace(model_dump=lambda mode: {}))

    request = initial_full_draft_turn_request(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=generation_contract,
    )

    context = json.loads(request.untrusted_context)
    assert context["approved_source_facts_by_section"] == (
        fact_selection.approved_source_facts_by_section(planning_input, proposal)
    )


def test_source_facts_by_section_prefers_direct_term_match_over_fallback(
    bdo_source_fact_mapping: tuple[ContentPlanningInput, ContentPlanningProposal],
) -> None:
    planning_input, proposal = bdo_source_fact_mapping

    mapping = fact_selection.approved_source_facts_by_section(planning_input, proposal)
    records = next(row for row in mapping if row["section_id"] == "section_records")

    assert [fact["source_fact_id"] for fact in records["source_facts"]] == ["bdo_records_fact"]
    assert len(records["source_facts"]) <= 4


def test_source_facts_by_section_ranks_and_caps_service_fallback_facts(
    bdo_source_fact_mapping: tuple[ContentPlanningInput, ContentPlanningProposal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planning_input, proposal = bdo_source_fact_mapping
    service_card_id = planning_input.confirmed_service_card_id
    fallback_facts = [
        _approved_bdo_fact(
            "fallback_unrelated",
            target_card_id=service_card_id,
            target_card_type="service",
            service_fit_terms=["audyt instalacji"],
        ),
        _approved_bdo_fact(
            "fallback_overlap_one",
            target_card_id=service_card_id,
            target_card_type="service",
            service_fit_terms=["zus nip"],
        ),
        _approved_bdo_fact(
            "fallback_overlap_two",
            target_card_id=service_card_id,
            target_card_type="service",
            service_fit_terms=["vat bdo"],
        ),
        _approved_bdo_fact(
            "fallback_overlap_two_tie",
            target_card_id=service_card_id,
            target_card_type="service",
            buyer_problem_terms=["pit zus"],
        ),
        _approved_bdo_fact(
            "fallback_overlap_three",
            target_card_id=service_card_id,
            target_card_type="service",
            buyer_problem_terms=["vat pit bdo"],
        ),
        _approved_bdo_fact(
            "fallback_overlap_four",
            target_card_id=service_card_id,
            target_card_type="service",
            service_fit_terms=["vat pit bdo czy"],
        ),
    ]
    monkeypatch.setattr(fact_selection, "ekologus_source_facts", lambda: tuple(fallback_facts))
    planning_input = planning_input.model_copy(
        update={
            "source_facts": [
                ContentPlanningSourceFact(
                    fact_id=f"planning_{fact.source_id}",
                    summary=fact.extracted_fact,
                    source_connector=fact.source_connectors[0],
                    evidence_ids=fact.evidence_ids,
                    source_fact_ids=[fact.source_id],
                )
                for fact in fallback_facts
            ]
        }
    )
    proposal = proposal.model_copy(
        update={
            "sections": [
                ContentPlanningSection(
                    section_id="section_acronyms",
                    heading="Czy BDO ma związek z PIT, VAT i ZUS?",
                    purpose="Porządkuje skróty istotne dla firmy.",
                    reader_question="Które skróty są ważne?",
                    inventory_disposition="rewrite",
                )
            ]
        }
    )

    mapping = fact_selection.approved_source_facts_by_section(planning_input, proposal)
    selected = mapping[0]["source_facts"]

    assert [fact["source_fact_id"] for fact in selected] == [
        "fallback_overlap_four",
        "fallback_overlap_three",
        "fallback_overlap_two",
        "fallback_overlap_two_tie",
    ]
    assert len(selected) <= 4
    assert "fallback_unrelated" not in {fact["source_fact_id"] for fact in selected}


def test_source_facts_by_section_caps_total_facts_across_sections(
    bdo_source_fact_mapping: tuple[ContentPlanningInput, ContentPlanningProposal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planning_input, proposal = bdo_source_fact_mapping
    matching_facts = [
        _approved_bdo_fact(
            f"shared_match_{index}",
            target_card_id=f"shared_card_{index}",
            service_fit_terms=["pytanie przedsiębiorcy"],
        )
        for index in range(1, 6)
    ]
    monkeypatch.setattr(fact_selection, "ekologus_source_facts", lambda: tuple(matching_facts))
    planning_input = planning_input.model_copy(
        update={
            "source_facts": [
                ContentPlanningSourceFact(
                    fact_id=f"planning_{fact.source_id}",
                    summary=fact.extracted_fact,
                    source_connector=fact.source_connectors[0],
                    evidence_ids=fact.evidence_ids,
                    source_fact_ids=[fact.source_id],
                )
                for fact in matching_facts
            ]
        }
    )

    mapping = fact_selection.approved_source_facts_by_section(planning_input, proposal)
    total_facts = sum(len(row["source_facts"]) for row in mapping)

    assert all(
        [fact["source_fact_id"] for fact in row["source_facts"]]
        == ["shared_match_1", "shared_match_2", "shared_match_3", "shared_match_4"]
        for row in mapping
    )
    assert total_facts == 4 * len(mapping)


def test_source_facts_by_section_ranks_direct_matches_by_section_overlap(
    bdo_source_fact_mapping: tuple[ContentPlanningInput, ContentPlanningProposal],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct matches must rank by section overlap, not registry order.

    A broad fact that appears first in the registry must not displace a
    specific sub-process fact (opłata środowiskowa) that overlaps the section
    text more strongly. The generic service fact can still be selected, but
    the most on-topic facts must lead the four delivered to the writer.
    """
    planning_input, proposal = bdo_source_fact_mapping
    service_card_id = planning_input.confirmed_service_card_id
    generic_fact = _approved_bdo_fact(
        "generic_service_fact",
        target_card_id=service_card_id,
        target_card_type="service",
        service_fit_terms=["ewidencja odpadów", "opłata środowiskowa"],
    )
    specific_fact = _approved_bdo_fact(
        "specific_fee_fact",
        target_card_id=service_card_id,
        target_card_type="service",
        service_fit_terms=["opłata środowiskowa", "wykazy korzystania"],
        buyer_problem_terms=["nieobliczona opłata środowiskowa"],
    )
    unrelated_fact = _approved_bdo_fact(
        "registry_ordered_fact",
        target_card_id="unrelated_card_registry",
        service_fit_terms=["sprawozdanie opakowaniowe"],
    )
    planning_input = planning_input.model_copy(
        update={
            "source_facts": [
                ContentPlanningSourceFact(
                    fact_id=f"planning_{fact.source_id}",
                    summary=fact.extracted_fact,
                    source_connector=fact.source_connectors[0],
                    evidence_ids=fact.evidence_ids,
                    source_fact_ids=[fact.source_id],
                )
                for fact in [generic_fact, specific_fact, unrelated_fact]
            ]
        }
    )
    proposal = proposal.model_copy(
        update={
            "sections": [
                ContentPlanningSection(
                    section_id="section_environmental_fees",
                    heading="Jak rozliczyć opłaty środowiskowe i wykazy korzystania?",
                    purpose="Pomaga firmie rozliczyć opłatę środowiskową.",
                    reader_question="Jak wyliczyć opłatę środowiskową?",
                    query_terms=["opłata środowiskowa", "wykazy korzystania"],
                    inventory_disposition="rewrite",
                )
            ]
        }
    )
    monkeypatch.setattr(
        fact_selection,
        "ekologus_source_facts",
        lambda: (generic_fact, specific_fact, unrelated_fact),
    )

    mapping = fact_selection.approved_source_facts_by_section(planning_input, proposal)
    selected = mapping[0]["source_facts"]

    assert selected[0]["source_fact_id"] == "specific_fee_fact"
    assert len(selected) <= 4


def test_benefit_signals_come_from_one_shared_source() -> None:
    from wilq.content.drafts import initial_full_draft as ifd
    from wilq.content.quality import benefit_signal, reading_quality

    assert (
        ifd.BENEFIT_HEADING_SIGNAL
        is reading_quality.BENEFIT_HEADING_SIGNAL
        is benefit_signal.BENEFIT_HEADING_SIGNAL
    )
    assert (
        ifd.BENEFIT_BODY_MARKER
        is reading_quality.BENEFIT_BODY_MARKER
        is benefit_signal.BENEFIT_BODY_MARKER
    )
