from types import SimpleNamespace
from typing import get_args

import pytest
from fastapi import FastAPI
from pydantic import BaseModel, ValidationError

from apps.api.wilq_api.routers import content_initial_draft
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.drafts import initial_draft_assurance_repair, initial_full_draft
from wilq.content.drafts.draft_assurance_runtime import ContentDraftAssuranceFailure
from wilq.content.drafts.generated_claim_safety import GeneratedClaimSafetyIssue
from wilq.content.drafts.initial_draft_validation import document_scope_errors
from wilq.content.drafts.initial_full_draft import _planning_input_blocker
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftBlockerCode,
    ContentInitialDraftCtaOutput,
    ContentInitialDraftFaqOutput,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftSectionOutput,
)
from wilq.content.drafts.initial_full_draft_document import (
    official_source_references_for_planning_input,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.initial_full_draft_turn import (
    _regulatory_draft_directive,
    initial_full_draft_output_schema,
    regulatory_assertion_repair_turn_request,
)
from wilq.content.drafts.regulatory_draft_repair import repair_regulatory_assertions
from wilq.content.drafts.regulatory_repair_policy import regulatory_section_repair_modes
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBlocker,
    ContentPlanningInputBlockerCode,
    ContentPlanningInputBuildResult,
)
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            ContentInitialDraftSectionOutput,
            {"section_id": "section", "heading": "Nagłówek", "body_markdown": "   "},
        ),
        (
            ContentInitialDraftFaqOutput,
            {"question": "Pytanie", "answer_markdown": "   "},
        ),
        (ContentInitialDraftCtaOutput, {"body_markdown": "   "}),
    ],
)
def test_initial_draft_model_output_rejects_whitespace_only_content(
    model: type[BaseModel], payload: dict[str, str]
) -> None:
    with pytest.raises(ValidationError, match="cannot be blank"):
        model.model_validate(payload)


def test_generated_claim_blocker_names_the_planned_section_without_claim_text() -> None:
    blocker = initial_full_draft._generated_claim_blocker(
        [
            GeneratedClaimSafetyIssue(
                code="undeclared_high_risk_claim_language",
                heading="Zakres dokumentacji dla inwestycji",
                claim_text="Nie ujawniaj wygenerowanego zdania.",
            )
        ]
    )

    assert blocker.code == "generated_claim_blocked"
    assert blocker.source_codes == ["undeclared_high_risk_claim_language"]
    assert "Zakres dokumentacji dla inwestycji" in blocker.reason
    assert "Nie ujawniaj" not in blocker.reason
    assert "wskazanej sekcji" in blocker.next_step


def _proposal_with_review_required_inventory() -> ContentPlanningProposal:
    return ContentPlanningProposal(
        work_item_id="content_work_item_scope",
        planning_digest="a" * 64,
        proposal_id="content_planning_proposal_scope",
        proposal_version=1,
        generation_status="codex_generated",
        planning_input_digest="b" * 64,
        final_canonical_url="https://www.ekologus.pl/strona/",
        service_card_id="ekologus_service_bdo_reporting",
        service_label="BDO",
        service_selection_confirmed=True,
        target_reader="przedsiębiorca",
        buyer_problem="Nie wie, co sprawdzić.",
        buyer_trigger="Przed decyzją.",
        search_intent="informacyjna",
        cta_direction="Skontaktuj się.",
        sections=[
            ContentPlanningSection(
                section_id="section_keep",
                heading="Sekcja do tekstu",
                purpose="Odpowiedz.",
                reader_question="Co sprawdzić?",
                inventory_disposition="rewrite",
                evidence_ids=["ev_scope"],
            ),
            ContentPlanningSection(
                section_id="section_remove",
                heading="Stary element do review",
                purpose="Nie przenoś automatycznie.",
                reader_question="Czy zachować?",
                inventory_disposition="remove_review_required",
                evidence_ids=["ev_scope"],
            ),
        ],
        search_demand={
            "status": "available",
            "optional_ads_status": "not_exactly_mapped",
            "safe_next_step": "Review",
        },
    )


def test_full_draft_schema_excludes_remove_review_required_sections() -> None:
    proposal = _proposal_with_review_required_inventory()

    assert [item.section_id for item in draftable_planning_sections(proposal.sections)] == [
        "section_keep"
    ]

    schema = initial_full_draft_output_schema(proposal)
    sections = schema["properties"]["sections"]
    section_definition = schema["$defs"]["ContentInitialDraftSectionOutput"]

    assert sections["minItems"] == 1
    assert sections["maxItems"] == 1
    assert section_definition["properties"]["section_id"]["enum"] == ["section_keep"]
    assert section_definition["properties"]["heading"]["enum"] == ["Sekcja do tekstu"]


def test_full_draft_turn_has_section_bound_regulatory_directive() -> None:
    proposal = _proposal_with_review_required_inventory()
    proposal.sections[0].regulatory_requirement_ids = ["bdo_records_and_kpo"]
    requirement = ContentRegulatoryRequirement(
        id="bdo_records_and_kpo",
        label="ewidencja i KPO",
        reason="Wymaga źródła urzędowego.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="kpo_before_transport",
                label="moment sporządzenia KPO",
                required_any_of=["KPO przed transportem"],
            )
        ],
    )

    planning_input = ContentPlanningInput.model_construct(
        regulatory_coverage=ContentRegulatoryCoverage(requirements=[requirement])
    )
    directive = _regulatory_draft_directive(planning_input, proposal)

    assert "section_keep" in directive
    assert "KPO przed transportem" in directive


def test_initial_draft_projects_only_exact_approved_official_sources() -> None:
    requirement = ContentRegulatoryRequirement(
        id="bdo_scope",
        label="zakres BDO",
        reason="Wymaga źródła urzędowego.",
    )
    approved_fact = ContentSourceFact(
        source_id="regulatory_source_fact_bdo_scope",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://bdo.mos.gov.pl/o-systemie-bdo/",
        extracted_fact="Oficjalny opis systemu BDO obejmuje rejestr oraz obowiązki podmiotów.",
        scope="claim_policy",
        freshness_date="2026-07-31",
        confidence=1,
        review_status="approved",
        reviewer="wilku",
        evidence_ids=["ev_regulatory_bdo_scope"],
        source_connectors=["official_regulatory_review"],
        target_card_id="regulatory_bdo",
        target_card_type="regulatory_source",
        target_card_title="Oficjalny opis systemu BDO",
        official_source=True,
        regulatory_profile_id="bdo",
        regulatory_profile_version="2026-07",
        regulatory_requirement_ids=[requirement.id],
        applicable_service_card_ids=["ekologus_service_bdo_reporting"],
    )
    coverage = ContentRegulatoryCoverage(
        profile_id="bdo",
        profile_version="2026-07",
        requirements=[requirement],
        requirement_coverage=[
            {
                "requirement_id": requirement.id,
                "source_fact_ids": [approved_fact.source_id],
                "evidence_ids": approved_fact.evidence_ids,
            }
        ],
        source_fact_ids=[approved_fact.source_id],
        evidence_ids=approved_fact.evidence_ids,
        source_facts=[approved_fact],
    )
    planning_input = ContentPlanningInput.model_construct(regulatory_coverage=coverage)

    references = official_source_references_for_planning_input(planning_input)

    assert [item.model_dump() for item in references] == [
        {
            "source_fact_id": approved_fact.source_id,
            "source_url": approved_fact.source_url_or_path,
            "source_title": approved_fact.target_card_title,
            "verified_on": approved_fact.freshness_date,
            "evidence_ids": approved_fact.evidence_ids,
            "regulatory_requirement_ids": [requirement.id],
        }
    ]

    incomplete = coverage.model_copy(update={"requirement_coverage": []})
    with pytest.raises(ValueError, match="complete official-source coverage"):
        official_source_references_for_planning_input(
            ContentPlanningInput.model_construct(regulatory_coverage=incomplete)
        )


def test_document_scope_accepts_the_same_excluded_section_projection() -> None:
    proposal = _proposal_with_review_required_inventory()
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Tytuł",
            meta_title="Meta",
            meta_description="Opis",
            h1="Nagłówek",
            lead="Lead",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_keep",
                heading="Sekcja do tekstu",
                body_markdown="Odpowiedź.",
            )
        ],
        publish_ready=False,
    )

    assert document_scope_errors(proposal, output) == []


def test_document_scope_rejects_a_regulatory_topic_without_its_required_concept() -> None:
    proposal = _proposal_with_review_required_inventory()
    proposal.sections[0].regulatory_requirement_ids = ["bdo_records_and_kpo"]
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Tytuł",
            meta_title="Meta",
            meta_description="Opis",
            h1="Nagłówek",
            lead="Lead",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_keep",
                heading="Sekcja do tekstu",
                body_markdown="Prowadzenie dokumentacji wymaga sprawdzenia obowiązków.",
            )
        ],
        publish_ready=False,
    )
    requirement = ContentRegulatoryRequirement(
        id="bdo_records_and_kpo",
        label="ewidencja i KPO",
        reason="Wymaga źródła urzędowego.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="kpo_before_transport",
                label="moment sporządzenia KPO",
                required_any_of=["przed transportem"],
            )
        ],
    )

    assert document_scope_errors(
        proposal,
        output,
        regulatory_requirements=[requirement],
    ) == ["regulatory_document_assertion:bdo_records_and_kpo:kpo_before_transport"]


def _regulatory_repair_fixture() -> tuple[
    ContentPlanningProposal,
    ContentPlanningInput,
    ContentInitialDraftModelOutput,
    ContentSourceFact,
    ContentSourceFact,
]:
    proposal = _proposal_with_review_required_inventory()
    proposal.sections[0].regulatory_requirement_ids = ["bdo_exemptions"]
    requirement = ContentRegulatoryRequirement(
        id="bdo_exemptions",
        label="zwolnienia z wpisu",
        reason="Wymaga źródła urzędowego.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="bdo_exemption_condition",
                label="warunkowy charakter zwolnienia",
                required_any_of=["zwolnienie zależy od warunków ustawowych"],
            )
        ],
    )
    fact = ContentSourceFact(
        source_id="regulatory_source_fact_bdo_exemptions",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://bdo.mos.gov.pl/zasady-rejestracji/",
        extracted_fact="Zwolnienie zależy od warunków ustawowych.",
        scope="claim_policy",
        freshness_date="2026-08-02",
        confidence=1,
        review_status="approved",
        reviewer="wilku",
        evidence_ids=["ev_regulatory_bdo_exemptions"],
        source_connectors=["official_regulatory_review"],
        target_card_id="regulatory_bdo",
        target_card_type="regulatory_source",
        target_card_title="Zasady rejestracji BDO",
        official_source=True,
        regulatory_profile_id="bdo",
        regulatory_profile_version="2026-07",
        regulatory_requirement_ids=[requirement.id],
        applicable_service_card_ids=[proposal.service_card_id],
    )
    related_fact = fact.model_copy(
        update={
            "source_id": "regulatory_source_fact_bdo_exemptions_scope",
            "extracted_fact": (
                "Zakres obowiązku należy oceniać dla całej działalności przedsiębiorcy."
            ),
            "evidence_ids": ["ev_regulatory_bdo_exemptions_scope"],
        }
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id=proposal.work_item_id,
        planning_input_digest="b" * 64,
        confirmed_service_card_id=proposal.service_card_id,
        regulatory_coverage=ContentRegulatoryCoverage(
            requirements=[requirement],
            source_facts=[fact, related_fact],
        ),
    )
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Tytuł",
            meta_title="Meta",
            meta_description="Opis",
            h1="Nagłówek",
            lead="Lead",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_keep",
                heading="Sekcja do tekstu",
                body_markdown="Sprawdź obowiązki.",
            )
        ],
        publish_ready=False,
    )

    return proposal, planning_input, output, fact, related_fact


def test_regulatory_repair_falls_back_from_a_duplicate_patch_to_approved_facts() -> None:
    proposal, planning_input, output, fact, related_fact = _regulatory_repair_fixture()
    model_calls = 0

    class DuplicatePatchClient:
        def run_structured_turn(self, _request):
            nonlocal model_calls
            model_calls += 1
            return CodexAppServerTurnResult(
                status="completed",
                output_text=(
                    '{"sections":['
                    '{"section_id":"section_keep","mode":"replace",'
                    '"body_markdown":"Pierwsza wersja."},'
                    '{"section_id":"section_keep","mode":"replace",'
                    '"body_markdown":"Druga wersja."}'
                    "]}"
                ),
            )

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=ContentInitialDraftBlocker(
            code="draft_assurance_failed",
            label="Brakuje wymaganego pojęcia.",
            reason="Wymaganie nie występuje w dokumencie.",
            next_step="Uzupełnij dokument.",
            source_codes=["requirement:bdo_exemptions"],
        ),
        repair_reasons={"requirement:bdo_exemptions": "overbroad_claim"},
        client=DuplicatePatchClient(),
    )

    assert repaired is not None
    assert model_calls == 1
    repaired_output, trace = repaired
    assert trace.status == "completed"
    assert fact.extracted_fact in repaired_output.sections[0].body_markdown
    assert related_fact.extracted_fact in repaired_output.sections[0].body_markdown


@pytest.mark.parametrize(
    "invalid_payload",
    [
        (
            '{"sections":[{"section_id":"section_keep","mode":"replace",'
            '"body_markdown":"[Nieufny link](https://example.com)"}]}'
        ),
        (
            '{"sections":[{"section_id":"section_keep","mode":"replace",'
            '"body_markdown":"Treść warunkowa."}],"publish_ready":true}'
        ),
    ],
)
def test_regulatory_repair_rejects_invalid_model_patch_contract(
    invalid_payload: str,
) -> None:
    proposal, planning_input, output, fact, _ = _regulatory_repair_fixture()
    output = output.model_copy(
        update={
            "sections": [
                output.sections[0].model_copy(
                    update={"body_markdown": "Każda firma zawsze podlega BDO."}
                )
            ]
        }
    )

    class InvalidPatchClient:
        def run_structured_turn(self, _request):
            return CodexAppServerTurnResult(
                status="completed",
                output_text=invalid_payload,
            )

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=ContentInitialDraftBlocker(
            code="draft_assurance_failed",
            label="Twierdzenie wymaga poprawy.",
            reason="Krytyk wykrył nadmierny zakres.",
            next_step="Popraw dokument.",
            source_codes=["requirement:bdo_exemptions"],
        ),
        repair_reasons={"requirement:bdo_exemptions": "overbroad_claim"},
        client=InvalidPatchClient(),
    )

    assert repaired is not None
    assert "Nieufny link" not in repaired[0].sections[0].body_markdown
    assert "Każda firma zawsze podlega BDO." not in repaired[0].sections[0].body_markdown
    assert fact.extracted_fact in repaired[0].sections[0].body_markdown
    ContentInitialDraftModelOutput.model_validate(repaired[0].model_dump(mode="json"))


def test_regulatory_fallback_revalidates_the_complete_patched_document() -> None:
    proposal, planning_input, output, fact, _ = _regulatory_repair_fixture()
    invalid_fact = fact.model_copy(update={"extracted_fact": "[Nieufny link](https://example.com)"})
    planning_input = planning_input.model_copy(
        update={
            "regulatory_coverage": planning_input.regulatory_coverage.model_copy(
                update={"source_facts": [invalid_fact]}
            )
        }
    )

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=ContentInitialDraftBlocker(
            code="document_scope_mismatch",
            label="Brakuje wymaganego pojęcia.",
            reason="Wymaganie nie występuje w dokumencie.",
            next_step="Uzupełnij dokument.",
            source_codes=["requirement:bdo_exemptions"],
        ),
        client=SimpleNamespace(),
    )

    assert repaired is None


def test_regulatory_scope_repair_uses_approved_facts_without_a_second_model_turn() -> None:
    proposal, planning_input, output, fact, _ = _regulatory_repair_fixture()

    class UnexpectedModelClient:
        def run_structured_turn(self, _request):
            raise AssertionError("Deterministic scope repair must not call Codex.")

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=ContentInitialDraftBlocker(
            code="document_scope_mismatch",
            label="Brakuje wymaganego pojęcia.",
            reason="Wymaganie nie występuje w dokumencie.",
            next_step="Uzupełnij dokument.",
            source_codes=["regulatory_document_assertion:bdo_exemptions:bdo_exemption_condition"],
        ),
        client=UnexpectedModelClient(),
    )

    assert repaired is not None
    body = repaired[0].sections[0].body_markdown
    assert "Sprawdź obowiązki." in body
    assert fact.extracted_fact in body


def test_regulatory_scope_repair_accepts_profile_owned_role_variants_in_approved_fact() -> None:
    proposal, planning_input, output, fact, _ = _regulatory_repair_fixture()
    requirement = ContentRegulatoryRequirement(
        id="account_access",
        label="dostęp do konta",
        reason="Wymaga źródła urzędowego.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="roles",
                label="role lub uprawnienia konta",
                required_any_of=[
                    "rola",
                    "uprawnien",
                    "użytkownik główny",
                    "użytkownik podrzędny",
                ],
            )
        ],
    )
    proposal.sections[0].regulatory_requirement_ids = [requirement.id]
    role_fact = fact.model_copy(
        update={
            "source_id": "regulatory_source_fact_account_access",
            "extracted_fact": (
                "Użytkownik główny może dodawać użytkowników, a użytkownik "
                "podrzędny ma dostęp do wskazanego modułu."
            ),
            "regulatory_requirement_ids": [requirement.id],
        }
    )
    planning_input = planning_input.model_copy(
        update={
            "regulatory_coverage": ContentRegulatoryCoverage(
                requirements=[requirement], source_facts=[role_fact]
            )
        }
    )
    missing = document_scope_errors(proposal, output, regulatory_requirements=[requirement])

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=ContentInitialDraftBlocker(
            code="document_scope_mismatch",
            label="Brakuje wymaganego pojęcia.",
            reason="Wymaganie nie występuje w dokumencie.",
            next_step="Uzupełnij dokument.",
            source_codes=missing,
        ),
        client=SimpleNamespace(),
    )

    assert repaired is not None
    assert role_fact.extracted_fact in repaired[0].sections[0].body_markdown
    assert document_scope_errors(proposal, repaired[0], regulatory_requirements=[requirement]) == []


def test_regulatory_repair_replaces_an_overbroad_section_when_critic_requires_it() -> None:
    proposal, planning_input, output, fact, _ = _regulatory_repair_fixture()
    output = output.model_copy(
        update={
            "sections": [
                output.sections[0].model_copy(
                    update={"body_markdown": "Każda firma zawsze podlega BDO."}
                )
            ]
        }
    )

    class ReplacementClient:
        def run_structured_turn(self, _request):
            return CodexAppServerTurnResult(
                status="completed",
                output_text=(
                    '{"sections":[{"section_id":"section_keep","mode":"replace",'
                    '"body_markdown":"Zwolnienie zależy od spełnienia warunków ustawowych."}]}'
                ),
            )

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=ContentInitialDraftBlocker(
            code="draft_assurance_failed",
            label="Twierdzenie jest zbyt szerokie.",
            reason="Krytyk wykrył nadmierny zakres.",
            next_step="Popraw dokument.",
            source_codes=["requirement:bdo_exemptions"],
        ),
        repair_reasons={"requirement:bdo_exemptions": "overbroad_claim"},
        client=ReplacementClient(),
    )

    assert repaired is not None
    body = repaired[0].sections[0].body_markdown
    assert "Każda firma zawsze podlega BDO." not in body
    assert body.startswith("Zwolnienie zależy od spełnienia warunków ustawowych.")
    assert fact.extracted_fact in body


def test_regulatory_repair_replaces_a_section_for_missing_scope() -> None:
    proposal, _, _, _, _ = _regulatory_repair_fixture()

    assert regulatory_section_repair_modes(
        proposal,
        ["requirement:bdo_exemptions"],
        {"requirement:bdo_exemptions": "missing_scope"},
    ) == {"section_keep": "replace"}


def test_regulatory_repair_uses_only_official_facts_when_semantic_repair_is_exhausted() -> None:
    proposal, planning_input, output, fact, related_fact = _regulatory_repair_fixture()
    output = output.model_copy(
        update={
            "sections": [
                output.sections[0].model_copy(
                    update={"body_markdown": "Każda firma zawsze podlega BDO."}
                )
            ]
        }
    )

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=ContentInitialDraftBlocker(
            code="draft_assurance_failed",
            label="Twierdzenie pozostaje zbyt szerokie.",
            reason="Krytyk ponownie wykrył nadmierny zakres.",
            next_step="Zastąp sekcję wyłącznie źródłami urzędowymi.",
            source_codes=["requirement:bdo_exemptions"],
        ),
        client=SimpleNamespace(),
        force_deterministic_replace=True,
    )

    assert repaired is not None
    body = repaired[0].sections[0].body_markdown
    assert "Każda firma zawsze podlega BDO." not in body
    assert body == "\n\n".join([fact.extracted_fact, related_fact.extracted_fact])


def test_semantic_fallback_preserves_every_requirement_bound_to_replaced_section() -> None:
    proposal, planning_input, output, fact, _ = _regulatory_repair_fixture()
    companion = ContentRegulatoryRequirement(
        id="registration_scope",
        label="zakres wpisu",
        reason="Wymaga źródła urzędowego.",
        document_assertions=[],
    )
    companion_fact = fact.model_copy(
        update={
            "source_id": "regulatory_source_fact_registration_scope",
            "extracted_fact": "Wpis zależy od rzeczywistego zakresu działalności.",
            "regulatory_requirement_ids": [companion.id],
            "evidence_ids": ["ev_regulatory_registration_scope"],
        }
    )
    proposal.sections[0].regulatory_requirement_ids = [
        "bdo_exemptions",
        companion.id,
    ]
    planning_input = planning_input.model_copy(
        update={
            "regulatory_coverage": ContentRegulatoryCoverage(
                requirements=[planning_input.regulatory_coverage.requirements[0], companion],
                source_facts=[fact, companion_fact],
            )
        }
    )

    repaired = repair_regulatory_assertions(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        blocker=ContentInitialDraftBlocker(
            code="draft_assurance_failed",
            label="Twierdzenie pozostaje zbyt szerokie.",
            reason="Krytyk ponownie wykrył nadmierny zakres.",
            next_step="Zastąp sekcję wyłącznie źródłami urzędowymi.",
            source_codes=["requirement:bdo_exemptions"],
        ),
        client=SimpleNamespace(),
        force_deterministic_replace=True,
    )

    assert repaired is not None
    assert repaired[0].sections[0].body_markdown == "\n\n".join(
        [fact.extracted_fact, companion_fact.extracted_fact]
    )


def test_assurance_repair_reaches_a_bounded_fixed_point_across_new_failures(
    monkeypatch,
) -> None:
    proposal, planning_input, output, _, _ = _regulatory_repair_fixture()
    proposal = proposal.model_copy(
        update={
            "sections": [
                proposal.sections[0].model_copy(
                    update={
                        "section_id": f"section_{requirement_id}",
                        "regulatory_requirement_ids": [requirement_id],
                    }
                )
                for requirement_id in (
                    "bdo_exemptions",
                    "registration_scope",
                    "records_and_kpo",
                )
            ]
        }
    )
    failures = [
        ContentDraftAssuranceFailure(
            code="draft_assurance_failed",
            label="Pierwsza kontrola nie przeszła",
            reason="Krytyk wskazał pierwsze wymaganie.",
            next_step="Popraw wymaganie.",
            source_codes=["requirement:bdo_exemptions"],
            repair_reasons={"requirement:bdo_exemptions": "overbroad_claim"},
        ),
        ContentDraftAssuranceFailure(
            code="draft_assurance_failed",
            label="Druga kontrola nie przeszła",
            reason="Krytyk wskazał kolejne wymaganie.",
            next_step="Popraw wymaganie.",
            source_codes=["requirement:registration_scope"],
            repair_reasons={"requirement:registration_scope": "missing_scope"},
        ),
        ContentDraftAssuranceFailure(
            code="draft_assurance_failed",
            label="Trzecia kontrola nie przeszła",
            reason="Krytyk wskazał ostatnie wymaganie.",
            next_step="Popraw wymaganie.",
            source_codes=["requirement:records_and_kpo"],
            repair_reasons={"requirement:records_and_kpo": "missing_scope"},
        ),
    ]
    assured = [failures[1], failures[2], None]
    repair_modes: list[bool] = []
    assurance_outputs: list[ContentInitialDraftModelOutput] = []

    def repair(**kwargs):
        force_deterministic = kwargs.get("force_deterministic_replace", False)
        repair_modes.append(force_deterministic)
        candidate = kwargs["output"]
        repaired = candidate.model_copy(
            update={
                "sections": [
                    candidate.sections[0].model_copy(
                        update={
                            "body_markdown": (
                                candidate.sections[0].body_markdown
                                + f"\n\nNaprawa {len(repair_modes)}."
                            )
                        }
                    )
                ]
            }
        )
        return repaired, kwargs.get("trace", SimpleNamespace(status="completed"))

    def assure(candidate, _trace):
        assurance_outputs.append(candidate)
        return assured.pop(0)

    monkeypatch.setattr(
        initial_draft_assurance_repair,
        "repair_regulatory_assertions",
        repair,
    )

    repaired, _, assurance, blocker = initial_draft_assurance_repair.repair_after_assurance_failure(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=SimpleNamespace(status="completed"),
        assurance=failures[0],
        client=SimpleNamespace(),
        assure_draft=assure,
        output_blocker=lambda _candidate: None,
    )

    assert blocker is None
    assert assurance is None
    assert repair_modes == [False, True, True]
    assert len(assurance_outputs) == 3
    assert repaired.sections[0].body_markdown.endswith("Naprawa 3.")


def test_regulatory_repair_turn_allows_only_qualified_approved_source_facts() -> None:
    proposal, planning_input, output, _, _ = _regulatory_repair_fixture()

    request = regulatory_assertion_repair_turn_request(
        planning_input=planning_input,
        proposal=proposal,
        candidate=output,
        missing_assertion_codes=["requirement:bdo_exemptions"],
    )

    assert "approved_official_source_facts" in request.instruction
    assert "server-owned mode" in request.instruction
    assert "Nie rozszerzaj obowiązku" in request.instruction


def test_initial_draft_preserves_the_first_actionable_planning_blocker() -> None:
    blocker = _planning_input_blocker(
        [
            ContentPlanningInputBlocker(
                code="missing_approved_service_fact",
                label="Brakuje zatwierdzonego faktu usługi",
                reason="Karta wskazuje nieznany source fact.",
                next_step="Uzupełnij approved source fact.",
            ),
            ContentPlanningInputBlocker(
                code="stale_planning_sources",
                label="Źródła są nieświeże",
                reason="Odśwież dane.",
                next_step="Uruchom refresh.",
            ),
        ]
    )

    assert blocker.code == "missing_approved_service_fact"
    assert blocker.label == "Brakuje zatwierdzonego faktu usługi"
    assert blocker.reason == "Karta wskazuje nieznany source fact."
    assert blocker.next_step == "Uzupełnij approved source fact."
    assert blocker.source_codes == [
        "missing_approved_service_fact",
        "stale_planning_sources",
    ]


def test_initial_draft_blocker_contract_contains_every_planning_blocker_code() -> None:
    assert set(get_args(ContentPlanningInputBlockerCode)) <= set(
        get_args(ContentInitialDraftBlockerCode)
    )


def test_initial_draft_preserves_source_material_review_blocker() -> None:
    blocker = _planning_input_blocker(
        [
            ContentPlanningInputBlocker(
                code="wordpress_material_review_required",
                label="Materiał strony wymaga potwierdzenia",
                reason="Rendered the_content needs source review.",
                next_step="Potwierdź materiał REST/ACF.",
            )
        ]
    )

    assert blocker.code == "wordpress_material_review_required"
    assert blocker.next_step == "Potwierdź materiał REST/ACF."


def test_initial_draft_reuses_exact_service_binding_from_generated_plan(
    monkeypatch,
) -> None:
    proposal = _proposal_with_review_required_inventory()
    source_snapshot = SimpleNamespace(
        planning_workspace=SimpleNamespace(
            section_map_current=True,
            proposal=proposal,
        ),
        revision_workspace=SimpleNamespace(latest_revision=None, context_current=True),
        preflight=SimpleNamespace(item=SimpleNamespace(id=proposal.work_item_id)),
    )
    selected_snapshot = object()
    captured: dict[str, object] = {}

    def select_exact_service(snapshot, service_card_id: str):
        captured["selection_snapshot"] = snapshot
        captured["service_card_id"] = service_card_id
        return selected_snapshot

    def build_input(snapshot, *, service_card_id: str):
        captured["input_snapshot"] = snapshot
        captured["input_service_card_id"] = service_card_id
        return ContentPlanningInputBuildResult(
            blockers=[
                ContentPlanningInputBlocker(
                    code="service_card_not_approved",
                    label="Usługa wymaga potwierdzenia",
                    reason="Focused sentinel stops before runtime setup.",
                    next_step="Sprawdź usługę.",
                )
            ]
        )

    monkeypatch.setattr(
        initial_full_draft,
        "with_explicit_content_service_selection",
        select_exact_service,
    )
    monkeypatch.setattr(initial_full_draft, "build_content_planning_input", build_input)

    response = initial_full_draft._prepare_inputs(
        source_snapshot,
        ContentInitialDraftRequest(
            expected_proposal_id=proposal.proposal_id,
            expected_planning_digest=proposal.planning_digest,
            expected_planning_input_digest=proposal.planning_input_digest,
            requested_by="wilku",
        ),
    )

    assert response.status == "blocked"
    assert captured == {
        "selection_snapshot": source_snapshot,
        "service_card_id": proposal.service_card_id,
        "input_snapshot": selected_snapshot,
        "input_service_card_id": proposal.service_card_id,
    }


def test_initial_draft_route_returns_emitted_regulatory_planning_blocker(
    monkeypatch,
) -> None:
    proposal = _proposal_with_review_required_inventory()
    snapshot = SimpleNamespace(
        planning_workspace=SimpleNamespace(
            section_map_current=True,
            proposal=proposal,
        ),
        revision_workspace=SimpleNamespace(latest_revision=None, context_current=True),
        preflight=SimpleNamespace(item=SimpleNamespace(id=proposal.work_item_id)),
    )
    selected_snapshot = object()
    monkeypatch.setattr(
        initial_full_draft,
        "with_explicit_content_service_selection",
        lambda _snapshot, _service_card_id: selected_snapshot,
    )
    monkeypatch.setattr(
        initial_full_draft,
        "build_content_planning_input",
        lambda _snapshot, *, service_card_id: ContentPlanningInputBuildResult(
            blockers=[
                ContentPlanningInputBlocker(
                    code="missing_regulatory_source_coverage",
                    label="Brakuje pokrycia źródłem urzędowym",
                    reason="Profil regulacyjny nie ma zatwierdzonego źródła.",
                    next_step="Zatwierdź dokładne źródło urzędowe.",
                )
            ]
        ),
    )
    monkeypatch.setattr(
        content_initial_draft,
        "content_codex_app_server_client",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(content_initial_draft, "content_workflow_store", lambda: object())
    monkeypatch.setattr(content_initial_draft, "local_state_store", lambda: object())
    app = FastAPI()
    content_initial_draft.register_content_initial_draft_route(
        app,
        snapshot_loader=lambda _work_item_id: snapshot,
    )

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", "") == "/api/content/work-items/{work_item_id}/initial-draft"
        and "POST" in getattr(route, "methods", set())
    )
    result = route.endpoint(
        proposal.work_item_id,
        ContentInitialDraftRequest(
            expected_proposal_id=proposal.proposal_id,
            expected_planning_digest=proposal.planning_digest,
            expected_planning_input_digest=proposal.planning_input_digest,
            requested_by="wilku",
        ),
    )
    body = result.model_dump(mode="json")

    assert body["status"] == "blocked"
    assert body["blockers"][0] == {
        "code": "missing_regulatory_source_coverage",
        "label": "Brakuje pokrycia źródłem urzędowym",
        "reason": "Profil regulacyjny nie ma zatwierdzonego źródła.",
        "next_step": "Zatwierdź dokładne źródło urzędowe.",
        "source_codes": ["missing_regulatory_source_coverage"],
        "retry_after_seconds": None,
    }
