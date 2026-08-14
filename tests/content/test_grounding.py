import pytest

from wilq.content.drafts import fact_selection, grounding
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets

_FACT_TEXTS = [
    "Źródło podaje, że pomiary emisji pyłu wykonuje się impaktorem kaskadowym. "
    "Wymaga weryfikacji przez człowieka.",
    "Źródło podaje, że pomiary emisji gazów wykonuje się analizatorem FID. "
    "Wymaga weryfikacji przez człowieka.",
    "Źródło podaje, że pomiary emisji hałasu wykonuje się sonometrem całkującym. "
    "Wymaga weryfikacji przez człowieka.",
]


@pytest.fixture
def grounding_case(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    ContentPlanningInput,
    ContentPlanningProposal,
    ContentInitialDraftModelOutput,
    list[ContentSourceFact],
]:
    facts = [
        ContentSourceFact.model_construct(
            source_id=f"fact_{index}",
            review_status="approved",
            official_source=False,
            target_card_id="service_emissions",
            target_card_type="service",
            target_card_title="Pomiary emisji",
            service_fit_terms=["emisje"],
            buyer_problem_terms=[],
            extracted_fact=text,
            evidence_ids=[f"ev_fact_{index}"],
        )
        for index, text in enumerate(_FACT_TEXTS, start=1)
    ]
    planning_input = ContentPlanningInput.model_construct(
        source_facts=[
            ContentPlanningSourceFact(
                fact_id=f"planning_{fact.source_id}",
                summary=fact.extracted_fact,
                source_connector="test",
                evidence_ids=fact.evidence_ids,
                source_fact_ids=[fact.source_id],
            )
            for fact in facts
        ]
    )
    proposal = ContentPlanningProposal.model_construct(
        service_card_id="service_emissions",
        sections=[
            ContentPlanningSection(
                section_id="section_01",
                heading="Emisje",
                purpose="Wyjaśnij pomiary emisji.",
                query_terms=["emisje"],
            )
        ],
    )
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Emisje",
            meta_title="Emisje",
            meta_description="Opis pomiarów emisji.",
            h1="Pomiary emisji",
            lead="Praktyczne informacje.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_01",
                heading="Emisje",
                body_markdown="Pomiary emisji trzeba zaplanować.",
            )
        ],
    )
    monkeypatch.setattr(fact_selection, "ekologus_source_facts", lambda: tuple(facts))
    return planning_input, proposal, output, facts


def test_source_fact_signal_errors_flags_generic_section(grounding_case: tuple) -> None:
    _, proposal, output, facts = grounding_case
    summaries = [fact.extracted_fact for fact in facts]

    assert grounding.source_fact_signal_errors(
        proposal,
        output,
        source_facts_by_section={"section_01": summaries},
        source_fact_corpus=summaries,
    ) == ["missing_source_fact_signal:section_01"]


def test_source_fact_signal_errors_passes_concrete_section(grounding_case: tuple) -> None:
    _, proposal, output, facts = grounding_case
    summaries = [fact.extracted_fact for fact in facts]
    concrete = output.model_copy(
        update={
            "sections": [
                output.sections[0].model_copy(
                    update={"body_markdown": "Pył mierzy się impaktorem kaskadowym."}
                )
            ]
        }
    )

    assert grounding.source_fact_signal_errors(
        proposal,
        concrete,
        source_facts_by_section={"section_01": summaries},
        source_fact_corpus=summaries,
    ) == []


def test_repair_missing_source_fact_signals_appends_document_ready_facts(
    grounding_case: tuple,
) -> None:
    planning_input, proposal, output, _ = grounding_case

    repaired = grounding.repair_missing_source_fact_signals(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        missing_codes=["missing_source_fact_signal:section_01"],
    )
    repaired_again = grounding.repair_missing_source_fact_signals(
        planning_input=planning_input,
        proposal=proposal,
        output=repaired,
        missing_codes=["missing_source_fact_signal:section_01"],
    )

    body = repaired.sections[0].body_markdown
    assert "impaktorem kaskadowym" in body
    assert "Wymaga weryfikacji przez człowieka" not in body
    assert "Źródło podaje" not in body
    assert repaired_again == repaired


def test_repair_skips_reappend_when_patch_is_already_in_body(
    grounding_case: tuple,
) -> None:
    planning_input, proposal, output, facts = grounding_case
    already_grounded = output.model_copy(
        update={
            "sections": [
                output.sections[0].model_copy(
                    update={
                        "body_markdown": (
                            output.sections[0].body_markdown
                            + "\n\n"
                            + grounding.document_ready_fact_text(
                                facts[0].extracted_fact,
                                protected_terms=None,
                            ).strip()
                        )
                    }
                )
            ]
        }
    )

    repaired = grounding.repair_missing_source_fact_signals(
        planning_input=planning_input,
        proposal=proposal,
        output=already_grounded,
        missing_codes=["missing_source_fact_signal:section_01"],
    )

    assert repaired == already_grounded


def test_repair_without_distinctive_tokens_is_idempotent(
    grounding_case: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planning_input, proposal, output, _ = grounding_case
    monkeypatch.setattr(grounding, "distinctive_fact_tokens", lambda _corpus: frozenset())

    repaired = grounding.repair_missing_source_fact_signals(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        missing_codes=["missing_source_fact_signal:section_01"],
    )
    repaired_again = grounding.repair_missing_source_fact_signals(
        planning_input=planning_input,
        proposal=proposal,
        output=repaired,
        missing_codes=["missing_source_fact_signal:section_01"],
    )

    assert repaired_again == repaired


def test_gate_and_repair_share_one_matcher(
    grounding_case: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planning_input, proposal, output, facts = grounding_case
    summaries = [fact.extracted_fact for fact in facts]
    calls: list[tuple[str, list[str], frozenset[str]]] = []

    def matcher(
        body_markdown: str,
        fact_summaries: list[str],
        *,
        distinctive_tokens: frozenset[str],
    ) -> bool:
        calls.append((body_markdown, fact_summaries, distinctive_tokens))
        return False

    monkeypatch.setattr(grounding, "body_has_source_fact_signal", matcher)
    grounding.source_fact_signal_errors(
        proposal,
        output,
        source_facts_by_section={"section_01": summaries},
        source_fact_corpus=summaries,
    )
    grounding.repair_missing_source_fact_signals(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        missing_codes=["missing_source_fact_signal:section_01"],
    )

    expected = (
        output.sections[0].body_markdown,
        summaries,
        grounding.distinctive_fact_tokens(summaries),
    )
    assert calls == [expected, expected]
