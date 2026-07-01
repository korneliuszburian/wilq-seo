from __future__ import annotations

from wilq.content.drafts.preview import build_structured_draft_preview
from wilq.content.drafts.structured_generation import (
    StructuredDraftClaimMarker,
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
    StructuredDraftOutput,
    StructuredDraftOutputSection,
    StructuredDraftSectionInput,
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
            claim_markers=(
                [
                    StructuredDraftClaimMarker(
                        claim_id="claim_general_bdo",
                        claim_text="Ekologus pomaga firmom uporządkować obowiązki BDO.",
                        claim_type="service_claim",
                        status="allowed_with_evidence",
                        evidence_ids=["ev_wp_bdo"],
                        reviewer_id="wilku",
                    )
                ]
                if include_claim_markers
                else []
            ),
            claims_allowed=["Ekologus pomaga firmom uporządkować obowiązki BDO."],
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
    result = build_structured_draft_preview(output=_output(), contract=_contract())

    assert result.blockers == []
    assert result.preview is not None
    assert result.preview.title == "BDO dla firm"
    assert result.preview.publish_ready is False
    assert result.preview.sections[0].heading == "Kogo dotyczy BDO"
    assert result.preview.source_facts_used == ["ev_gsc_bdo", "ev_wp_bdo"]
    assert "Czy to brzmi jak Ekologus?" in result.preview.human_review_checklist


def test_structured_draft_preview_blocks_missing_contract_or_output() -> None:
    result = build_structured_draft_preview(output=None, contract=None)

    assert result.preview is None
    assert {blocker.code for blocker in result.blockers} == {
        "missing_output",
        "missing_contract",
    }


def test_structured_draft_preview_blocks_claims_that_still_need_review() -> None:
    result = build_structured_draft_preview(
        output=_output(claims_needing_review=["Niepotwierdzona obietnica efektu."]),
        contract=_contract(),
    )

    assert result.preview is None
    assert [blocker.code for blocker in result.blockers] == ["claims_need_review"]


def test_structured_draft_preview_blocks_claims_outside_generation_contract() -> None:
    result = build_structured_draft_preview(
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

    assert result.preview is None
    assert [blocker.code for blocker in result.blockers] == ["unknown_claim_reference"]


def test_structured_draft_preview_blocks_claim_marker_without_section_evidence() -> None:
    result = build_structured_draft_preview(
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

    assert result.preview is None
    assert [blocker.code for blocker in result.blockers] == ["claim_missing_required_evidence"]
    assert "ev_wp_bdo" in result.blockers[0].next_step


def test_structured_draft_preview_keeps_text_only_claim_contract_compatible() -> None:
    result = build_structured_draft_preview(
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

    assert result.blockers == []
    assert result.preview is not None


def test_structured_draft_preview_blocks_missing_or_unknown_evidence() -> None:
    missing_evidence = build_structured_draft_preview(
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
        contract=_contract(),
    )
    unknown_evidence = build_structured_draft_preview(
        output=_output(source_facts_used=["ev_fake"]),
        contract=_contract(),
    )

    assert [blocker.code for blocker in missing_evidence.blockers] == ["section_missing_evidence"]
    assert [blocker.code for blocker in unknown_evidence.blockers] == ["unknown_evidence_reference"]
