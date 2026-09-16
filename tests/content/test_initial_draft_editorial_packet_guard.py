from __future__ import annotations

from types import SimpleNamespace

import pytest

import wilq.content.drafts.initial_full_draft as initial_full_draft
from tests.content.test_selected_source_pack_projection import _planning_input
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftRequest
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
)
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)


def _proposal(
    *, packet_id: str | None = None, packet_digest: str | None = None
) -> ContentPlanningProposal:
    return ContentPlanningProposal.model_construct(
        work_item_id="content_work_item_bdo_editorial",
        planning_digest="a" * 64,
        proposal_id="proposal_bdo_editorial",
        generation_status="codex_generated",
        planning_input_digest="b" * 64,
        research_packet_id=packet_id,
        research_packet_digest=packet_digest,
        content_kind="editorial",
        service_card_id=None,
        final_canonical_url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        target_reader="Przedsiębiorca",
        buyer_problem="Brak uporządkowanej informacji.",
        buyer_trigger="Potrzeba sprawdzenia obowiązków.",
        search_intent="informational",
        cta_direction="Przejdź do kontaktu.",
        sections=[
            ContentPlanningSection(
                section_id="section_bdo",
                heading="Zakres BDO",
                purpose="Odpowiedz na pytanie czytelnika.",
                inventory_disposition="rewrite",
            )
        ],
    )


def _snapshot(proposal: ContentPlanningProposal) -> SimpleNamespace:
    return SimpleNamespace(
        preflight=SimpleNamespace(item=SimpleNamespace(id=proposal.work_item_id)),
        planning_workspace=SimpleNamespace(section_map_current=True, proposal=proposal),
        revision_workspace=SimpleNamespace(latest_revision=None, context_current=False),
    )


def _request() -> ContentInitialDraftRequest:
    return ContentInitialDraftRequest(
        expected_proposal_id="proposal_bdo_editorial",
        expected_planning_digest="a" * 64,
        expected_planning_input_digest="b" * 64,
        requested_by="wilku",
    )


class _NoSideEffects:
    def __getattr__(self, name: str):
        raise AssertionError(f"unexpected side effect: {name}")


class _EmptyWorkflowStore:
    pass


@pytest.mark.parametrize("workflow_store", [None, _EmptyWorkflowStore()])
def test_editorial_without_exact_packet_blocks_before_model_or_persistence(
    monkeypatch: pytest.MonkeyPatch,
    workflow_store: object | None,
) -> None:
    proposal = _proposal()
    planning_input = _planning_input().model_copy(update={"planning_input_digest": "b" * 64})
    monkeypatch.setattr(
        initial_full_draft,
        "_current_planning_input",
        lambda *_args: ContentPlanningInputBuildResult(planning_input=planning_input),
    )
    monkeypatch.setattr(
        initial_full_draft,
        "_prepare_generation_contract",
        lambda **_kwargs: pytest.fail("editorial without packet reached generation"),
    )

    response = initial_full_draft.generate_initial_full_draft(
        snapshot=_snapshot(proposal),
        request=_request(),
        client=_NoSideEffects(),
        workflow_store=workflow_store,  # type: ignore[arg-type]
        run_store=_NoSideEffects(),  # type: ignore[arg-type]
    )

    assert response.status == "blocked"
    assert response.blockers[0].code == "research_packet_missing"


def test_editorial_with_current_packet_reaches_generation_preparation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal(
        packet_id="content_research_packet_bdo_editorial",
        packet_digest="c" * 64,
    )
    planning_input = _planning_input()
    source_fact_ids = tuple(
        sorted(
            fact.source_id
            for fact in ekologus_source_facts()
            if fact.source_id == "ekologus_public_bdo_faq_2026_07_01" or fact.official_source
        )
    )
    packet = SimpleNamespace(
        packet_id=proposal.research_packet_id,
        packet_digest=proposal.research_packet_digest,
        current_work_item_id=proposal.work_item_id,
        approved_source_fact_ids=source_fact_ids,
    )

    class CurrentStore:
        def load_content_research_packet(self, _packet_id: str):
            return packet

        def list_content_source_pack_bindings(self, **_kwargs: object):
            return [object()]

    monkeypatch.setattr(
        initial_full_draft,
        "_current_planning_input",
        lambda *_args: ContentPlanningInputBuildResult(planning_input=planning_input),
    )
    monkeypatch.setattr(
        initial_full_draft,
        "current_research_packet_blocker",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        initial_full_draft,
        "_prepare_generation_contract",
        lambda **kwargs: kwargs["planning_input"],
    )

    result = initial_full_draft._prepare_draft_planning_input(
        snapshot=_snapshot(proposal),
        proposal=proposal,
        service_card_id=None,
        workflow_store=CurrentStore(),
    )

    assert isinstance(result, ContentPlanningInput)
    assert result.research_packet_id == proposal.research_packet_id
