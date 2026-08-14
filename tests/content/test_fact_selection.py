from types import SimpleNamespace

import pytest

from wilq.content.drafts import (
    codex_section_proposal_turn,
    fact_selection,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.workflow.decisions.planning import ContentPlanningSection

_TERMS = ["alfa", "beta", "gamma", "delta", "epsilon"]
_SECTION = ContentPlanningSection(
    section_id="section_ranked",
    heading="Ranking faktów",
    purpose="Dobiera fakty do sekcji.",
    query_terms=[" ".join(_TERMS)],
)


def _fact(source_id: str, overlap: int, *, official: bool = False) -> ContentSourceFact:
    return ContentSourceFact.model_construct(
        source_id=source_id,
        review_status="approved",
        official_source=official,
        target_card_id="evidence_card",
        target_card_type="evidence_requirement",
        target_card_title="Materiał dowodowy",
        service_fit_terms=[" ".join(_TERMS[:overlap])],
        buyer_problem_terms=[],
        extracted_fact=f"Zatwierdzony fakt: {source_id}.",
        evidence_ids=[f"ev_{source_id}"],
    )


def _planning_input(facts: list[ContentSourceFact]) -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
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


def _ids(contexts: list[dict[str, object]]) -> list[str]:
    return [str(context["source_fact_id"]) for context in contexts]


def test_initial_and_section_proposal_fact_builders_rank_the_same_direct_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts = [_fact(f"fact_{score}", score) for score in range(1, 6)]
    planning_input = _planning_input(facts)
    proposal = SimpleNamespace(service_card_id="service_card", sections=[_SECTION])
    monkeypatch.setattr(fact_selection, "ekologus_source_facts", lambda: tuple(facts))

    initial_contexts = fact_selection.approved_source_facts_by_section(planning_input, proposal)[
        0
    ]["source_facts"]
    snapshot = SimpleNamespace(planning_workspace=SimpleNamespace(proposal=proposal))
    proposal_contexts = codex_section_proposal_turn._selected_approved_source_facts(
        planning_input, snapshot, [_SECTION.heading]
    )

    expected = ["fact_5", "fact_4", "fact_3", "fact_2"]
    assert _ids(initial_contexts) == _ids(proposal_contexts) == expected


def test_approved_planning_source_facts_requires_official_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary, official = _fact("ordinary", 1), _fact("official", 1, official=True)
    planning_input = _planning_input([ordinary, official])
    monkeypatch.setattr(fact_selection, "ekologus_source_facts", lambda: (official, ordinary))

    without_official = fact_selection.approved_planning_source_facts(
        planning_input, include_official=False
    )
    with_official = fact_selection.approved_planning_source_facts(
        planning_input, include_official=True
    )

    assert [fact.source_id for fact in without_official] == ["ordinary"]
    assert [fact.source_id for fact in with_official] == ["ordinary", "official"]


def test_initial_draft_row_projection_includes_official_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    official = _fact("official", 1, official=True)
    planning_input = _planning_input([official])
    proposal = SimpleNamespace(service_card_id=None, sections=[_SECTION])
    monkeypatch.setattr(fact_selection, "ekologus_source_facts", lambda: (official,))

    rows = fact_selection.approved_source_facts_by_section(planning_input, proposal)

    assert _ids(rows[0]["source_facts"]) == ["official"]


def test_section_proposal_path_excludes_official_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary = _fact("ordinary", 1)
    official = _fact("official", 1, official=True)
    planning_input = _planning_input([ordinary, official])
    proposal = SimpleNamespace(service_card_id="service_card", sections=[_SECTION])
    monkeypatch.setattr(fact_selection, "ekologus_source_facts", lambda: (official, ordinary))

    contexts = codex_section_proposal_turn._selected_approved_source_facts(
        planning_input,
        SimpleNamespace(planning_workspace=SimpleNamespace(proposal=proposal)),
        [_SECTION.heading],
    )

    assert _ids(contexts) == ["ordinary"]
