from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import wilq.content.drafts.initial_full_draft as initial_full_draft
from tests.content.test_selected_source_pack_projection import _planning_input
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
    _digest,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.schemas import CodexRun


def test_generated_plan_reuses_frozen_input_but_rechecks_live_packet_lineage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    frozen = _service_input(
        work_item_id="content_work_item_frozen_input",
        research_packet_id="content_research_packet_frozen",
        research_packet_digest="c" * 64,
    )
    live = _with_digest(frozen.model_copy(update={"buyer_problem": "Nowszy problem odbiorcy."}))
    proposal = _proposal(frozen)
    store = ContentPlanningProposalStore(tmp_path / "frozen-input.sqlite3")
    completed_at = datetime(2026, 9, 21, 12, tzinfo=UTC)
    completed_run = CodexRun(
        id="codex_run_frozen_input",
        status="completed",
        started_at=completed_at,
        completed_at=completed_at,
    )

    outcome, stored = store.save_generated(
        proposal,
        completed_run,
        planning_input=frozen,
    )

    assert outcome == "created"
    assert stored.planning_input_digest == frozen.planning_input_digest
    assert store.frozen_planning_input(
        frozen.work_item_id, frozen.planning_input_digest
    ) == frozen

    snapshot = _snapshot(stored)
    request = _request(stored)
    packet_store = _PacketStore(frozen)
    current_packet_blocker = initial_full_draft.current_research_packet_blocker
    monkeypatch.setattr(initial_full_draft, "content_planning_proposal_store", lambda: store)
    monkeypatch.setattr(
        initial_full_draft,
        "_current_planning_input",
        lambda *_args: ContentPlanningInputBuildResult(planning_input=live),
    )
    monkeypatch.setattr(initial_full_draft, "current_research_packet_blocker", lambda **_: None)
    monkeypatch.setattr(
        initial_full_draft,
        "_prepare_generation_contract",
        lambda **kwargs: kwargs["planning_input"],
    )

    resolved = initial_full_draft._prepare_inputs(  # noqa: SLF001
        snapshot,
        request,
        workflow_store=packet_store,
    )

    assert isinstance(resolved, ContentPlanningInput)
    assert resolved == frozen
    assert resolved.planning_input_digest != live.planning_input_digest

    packet_store.drift_source_pack()
    monkeypatch.setattr(
        initial_full_draft,
        "current_research_packet_blocker",
        current_packet_blocker,
    )
    blocked = initial_full_draft._prepare_inputs(  # noqa: SLF001
        snapshot,
        request,
        workflow_store=packet_store,
    )

    assert isinstance(blocked, ContentInitialDraftResponse)
    assert blocked.status == "blocked"
    assert blocked.blockers[0].code == "research_packet_conflict"


def _service_input(
    *,
    work_item_id: str,
    research_packet_id: str,
    research_packet_digest: str,
) -> ContentPlanningInput:
    base = _planning_input()
    payload = base.model_dump(mode="python")
    payload.update(
        {
            "work_item_id": work_item_id,
            "content_kind": "service",
            "service_candidates": [
                ContentWorkItemServiceCandidate(
                    service_card_id="ekologus_service_bdo_reporting",
                    service_label="Raportowanie BDO",
                    lifecycle_status="approved_current",
                    lifecycle_label="Zatwierdzona karta usługi",
                    matched_terms=["bdo"],
                    match_reasons=["Testowe exact wiązanie usługi."],
                    recommended=True,
                )
            ],
            "confirmed_service_card_id": "ekologus_service_bdo_reporting",
            "service_label": "Raportowanie BDO",
            "research_packet_id": research_packet_id,
            "research_packet_digest": research_packet_digest,
        }
    )
    return _with_digest(ContentPlanningInput.model_validate(payload))


def _with_digest(planning_input: ContentPlanningInput) -> ContentPlanningInput:
    payload = planning_input.model_dump(mode="json")
    payload.pop("planning_input_digest")
    digest = _digest(
        {
            "schema_name": planning_input.schema_name,
            "criteria_version": planning_input.criteria_version,
            "inventory_mapping_policy": planning_input.inventory_mapping_policy,
            **payload,
        }
    )
    return planning_input.model_copy(update={"planning_input_digest": digest})


def _proposal(planning_input: ContentPlanningInput) -> ContentPlanningProposal:
    return ContentPlanningProposal(
        work_item_id=planning_input.work_item_id,
        planning_digest="d" * 64,
        proposal_id="content_planning_proposal_frozen_input",
        codex_run_id="codex_run_frozen_input",
        generation_status="codex_generated",
        input_schema_version=planning_input.schema_name,
        criteria_version=planning_input.criteria_version,
        planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=planning_input.research_packet_id,
        research_packet_digest=planning_input.research_packet_digest,
        content_kind=planning_input.content_kind,
        final_canonical_url=planning_input.final_canonical_url,
        service_card_id=planning_input.confirmed_service_card_id,
        service_label=planning_input.service_label,
        service_selection_confirmed=True,
        target_reader=planning_input.target_reader,
        buyer_problem=planning_input.buyer_problem,
        buyer_trigger=planning_input.buyer_trigger,
        search_intent=planning_input.search_intent,
        cta_direction=planning_input.baseline_cta_direction,
        sections=[
            ContentPlanningSection(
                section_id="section_frozen_input",
                heading="Zakres odpowiedzi",
                purpose="Odpowiedz na pytanie czytelnika.",
                inventory_disposition="rewrite",
            )
        ],
        search_demand=planning_input.query_portfolio,
        created_at=datetime(2026, 9, 21, 12, tzinfo=UTC),
    )


def _snapshot(proposal: ContentPlanningProposal) -> SimpleNamespace:
    return SimpleNamespace(
        preflight=SimpleNamespace(item=SimpleNamespace(id=proposal.work_item_id)),
        planning_workspace=SimpleNamespace(section_map_current=True, proposal=proposal),
        revision_workspace=SimpleNamespace(latest_revision=None, context_current=False),
    )


def _request(proposal: ContentPlanningProposal) -> ContentInitialDraftRequest:
    return ContentInitialDraftRequest(
        expected_proposal_id=proposal.proposal_id or "",
        expected_planning_digest=proposal.planning_digest,
        expected_planning_input_digest=proposal.planning_input_digest or "",
        requested_by="wilku",
    )


class _PacketStore:
    def __init__(self, planning_input: ContentPlanningInput) -> None:
        source_fact_id = next(
            fact.source_id for fact in ekologus_source_facts() if fact.review_status == "approved"
        )
        self.packet = SimpleNamespace(
            packet_id=planning_input.research_packet_id,
            packet_digest=planning_input.research_packet_digest,
            current_work_item_id=planning_input.work_item_id,
            status="exact_current",
            context_receipt=object(),
            source_pack_binding_id="content_source_pack_binding_old",
            source_pack_binding_digest="e" * 64,
            identity_binding_id="content_delivery_identity_old",
            evidence_ids=["ev_packet_frozen"],
            approved_source_fact_ids=(source_fact_id,),
        )
        self.packs = [
            SimpleNamespace(
                binding_id=self.packet.source_pack_binding_id,
                binding_digest=self.packet.source_pack_binding_digest,
                status="exact_current",
                recorded_at=datetime(2026, 9, 20, tzinfo=UTC),
                evidence_ids=["ev_packet_frozen"],
            )
        ]

    def load_content_research_packet(self, _packet_id: str) -> object:
        return self.packet

    def list_content_source_pack_bindings(
        self, *, current_work_item_id: str | None = None
    ) -> list[object]:
        del current_work_item_id
        return self.packs

    def drift_source_pack(self) -> None:
        self.packs.append(
            SimpleNamespace(
                binding_id="content_source_pack_binding_new",
                binding_digest="f" * 64,
                status="exact_current",
                recorded_at=datetime(2026, 9, 21, tzinfo=UTC),
                evidence_ids=["ev_packet_frozen_new"],
            )
        )


__all__ = ["test_generated_plan_reuses_frozen_input_but_rechecks_live_packet_lineage"]
