from __future__ import annotations

from wilq.content.drafts.preview import structured_draft_preview_blockers
from wilq.content.drafts.structured_generation import (
    StructuredDraftClaimMarker,
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
    StructuredDraftOutput,
    StructuredDraftOutputSection,
    StructuredDraftSectionInput,
    StructuredDraftSignalQuality,
    StructuredDraftSourceFact,
    structured_draft_output_schema,
)


def _contract(*, include_claim_markers: bool = True) -> StructuredDraftGenerationContract:
    return StructuredDraftGenerationContract(
        model_input=StructuredDraftGenerationInput(
            work_item_id="content_work_item_bdo",
            title="BDO dla firm",
            final_canonical_url="https://ekologus.pl/bdo/",
            source_public_url="https://ekologus.pl/bdo/",
            preview_url="https://ekologus.dev.proudsite.pl/bdo/",
            target_reader="właściciel firmy",
            buyer_problem="nie wie, czy BDO go dotyczy",
            buyer_trigger="porządkowanie obowiązków",
            search_intent="informacyjno-usługowy",
            service_fit="obsługa środowiskowa",
            cta_direction="Zaproponuj kontakt bez obietnicy wyniku.",
            sections=[
                StructuredDraftSectionInput(
                    heading="Kogo dotyczy BDO",
                    purpose="Wyjaśnić zakres obowiązków.",
                    evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
                )
            ],
            source_facts=[
                StructuredDraftSourceFact(
                    evidence_id="ev_gsc_bdo",
                    source_connector="google_search_console",
                    summary="GSC potwierdza popyt na temat.",
                )
            ],
            sales_brief_signal_quality=StructuredDraftSignalQuality(
                status="review_required",
                status_label="sygnał użyteczny, ale wymaga review",
                reason="Brief ma ślad dowodowy, ale wiedza wymaga decyzji człowieka.",
                evidence_id_count=2,
                source_connector_count=2,
                source_fact_count=1,
                missing_evidence_count=0,
                knowledge_constraint_count=1,
                review_required_knowledge_card_count=1,
                measurement_baseline_ready=True,
                safe_next_step="Pokaż brief Wilkowi przed finalnym szkicem.",
            ),
            claim_markers=(
                [
                    StructuredDraftClaimMarker(
                        claim_id="claim_general_bdo",
                        claim_text="Ekologus pomaga firmom uporządkować obowiązki BDO.",
                        claim_type="service_claim",
                        status="allowed_with_evidence",
                        strength="weak",
                        required=True,
                        evidence_ids=["ev_wp_bdo"],
                        source_connectors=["wordpress_ekologus"],
                        reviewer_id="wilku",
                    )
                ]
                if include_claim_markers
                else []
            ),
            claims_allowed=["Ekologus pomaga firmom uporządkować obowiązki BDO."],
            claims_removed_or_blocked=["Ta treść zwiększy liczbę leadów."],
            human_review_questions=["Czy to brzmi jak Ekologus?"],
        ),
        output_schema=structured_draft_output_schema(),
        system_instruction="Pisz tylko z dowodów.",
        user_instruction="Przygotuj szkic.",
    )


def _output(**overrides: object) -> StructuredDraftOutput:
    payload = {
        "draft_kind": "section_draft",
        "language": "pl-PL",
        "title": "BDO dla firm",
        "meta_title": "BDO dla firm",
        "meta_description": "Sprawdź, kiedy warto skonsultować BDO.",
        "h1": "BDO dla firm",
        "sections": [
            StructuredDraftOutputSection(
                heading="Kogo dotyczy BDO",
                body_markdown="BDO warto sprawdzić na podstawie sytuacji firmy.",
                evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
                claims_used=["Ekologus pomaga firmom uporządkować obowiązki BDO."],
            )
        ],
        "faq": ["Czy każda firma musi mieć BDO?"],
        "cta": "Skontaktuj się z Ekologus, żeby omówić sytuację firmy.",
        "internal_links": ["https://ekologus.pl/kontakt/"],
        "source_facts_used": ["ev_gsc_bdo", "ev_wp_bdo"],
        "claims_needing_review": [],
        "forbidden_claims_avoided": ["Ta treść zwiększy liczbę leadów."],
        "human_review_checklist": ["Czy to brzmi jak Ekologus?"],
        "publish_ready": False,
    }
    payload.update(overrides)
    return StructuredDraftOutput(**payload)


def test_structured_draft_preview_returns_marketer_preview() -> None:
    blockers = structured_draft_preview_blockers(output=_output(), contract=_contract())

    assert blockers == []


def test_structured_draft_preview_blocks_missing_contract_or_output() -> None:
    blockers = structured_draft_preview_blockers(output=None, contract=None)

    assert {blocker.code for blocker in blockers} == {
        "missing_output",
        "missing_contract",
    }


def test_structured_draft_preview_blocks_claims_that_still_need_review() -> None:
    blockers = structured_draft_preview_blockers(
        output=_output(claims_needing_review=["Niepotwierdzona obietnica efektu."]),
        contract=_contract(),
    )

    assert [blocker.code for blocker in blockers] == ["claims_need_review"]


def test_structured_draft_preview_blocks_claims_outside_generation_contract() -> None:
    blockers = structured_draft_preview_blockers(
        output=_output(
            sections=[
                StructuredDraftOutputSection(
                    heading="Kogo dotyczy BDO",
                    body_markdown="BDO warto sprawdzić na podstawie sytuacji firmy.",
                    evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
                    claims_used=[
                        "Ekologus pomaga firmom uporządkować obowiązki BDO.",
                        "Ekologus gwarantuje pełną zgodność po kontakcie.",
                    ],
                )
            ]
        ),
        contract=_contract(),
    )

    assert [blocker.code for blocker in blockers] == ["unknown_claim_reference"]


def test_structured_draft_preview_blocks_claim_marker_without_section_evidence() -> None:
    blockers = structured_draft_preview_blockers(
        output=_output(
            sections=[
                StructuredDraftOutputSection(
                    heading="Kogo dotyczy BDO",
                    body_markdown="BDO warto sprawdzić na podstawie sytuacji firmy.",
                    evidence_ids=["ev_gsc_bdo"],
                    claims_used=["Ekologus pomaga firmom uporządkować obowiązki BDO."],
                )
            ]
        ),
        contract=_contract(),
    )

    assert [blocker.code for blocker in blockers] == ["claim_missing_required_evidence"]
    assert "ev_wp_bdo" in blockers[0].next_step


def test_structured_draft_preview_blocks_missing_required_claim() -> None:
    blockers = structured_draft_preview_blockers(
        output=_output(
            sections=[
                StructuredDraftOutputSection(
                    heading="Kogo dotyczy BDO",
                    body_markdown="BDO warto sprawdzić na podstawie sytuacji firmy.",
                    evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
                    claims_used=[],
                )
            ]
        ),
        contract=_contract(),
    )

    assert [blocker.code for blocker in blockers] == ["required_claim_missing"]
    assert "Ekologus pomaga firmom uporządkować obowiązki BDO." in blockers[0].next_step


def test_structured_draft_preview_requires_forbidden_claim_acknowledgement() -> None:
    blockers = structured_draft_preview_blockers(
        output=_output(forbidden_claims_avoided=[]),
        contract=_contract(),
    )

    assert [blocker.code for blocker in blockers] == [
        "missing_forbidden_claim_acknowledgement"
    ]
    assert "Ta treść zwiększy liczbę leadów." in blockers[0].next_step


def test_structured_draft_preview_keeps_text_only_claim_contract_compatible() -> None:
    blockers = structured_draft_preview_blockers(
        output=_output(
            sections=[
                StructuredDraftOutputSection(
                    heading="Kogo dotyczy BDO",
                    body_markdown="BDO warto sprawdzić na podstawie sytuacji firmy.",
                    evidence_ids=["ev_gsc_bdo"],
                    claims_used=["Ekologus pomaga firmom uporządkować obowiązki BDO."],
                )
            ]
        ),
        contract=_contract(include_claim_markers=False),
    )

    assert blockers == []


def test_structured_draft_preview_blocks_missing_or_unknown_evidence() -> None:
    missing_evidence = structured_draft_preview_blockers(
        output=_output(
            sections=[
                StructuredDraftOutputSection(
                    heading="Kogo dotyczy BDO",
                    body_markdown="Treść bez mapy dowodów.",
                    evidence_ids=[],
                    claims_used=[],
                )
            ]
        ),
        contract=_contract(include_claim_markers=False),
    )
    unknown_evidence = structured_draft_preview_blockers(
        output=_output(source_facts_used=["ev_fake"]),
        contract=_contract(),
    )

    assert [blocker.code for blocker in missing_evidence] == ["section_missing_evidence"]
    assert [blocker.code for blocker in unknown_evidence] == ["unknown_evidence_reference"]
