from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

import wilq.content.workflow.research_packet_derivation as research_packet_derivation
from tests.content.initial_draft_authority_fakes import draft_review, draft_revision
from tests.content.packet_plan_draft_fixtures import build_packet_preparation_case
from tests.content.test_new_page_canonical_document import _exact_inputs
from wilq.content.drafts.initial_draft_authority import (
    InitialDraftAuthorityReused,
    map_initial_draft_authority_response,
)
from wilq.content.drafts.initial_draft_queue import queued_initial_draft_response
from wilq.content.drafts.initial_draft_response import initial_draft_packet_fields
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.dynamic_input import bind_research_packet_to_planning_input
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.research_packet_current import revalidate_content_research_packet
from wilq.content.workflow.research_packet_preparation import (
    current_research_packet_blocker,
    prepare_content_research_packet,
)
from wilq.schemas import ConnectorCoveredWindow, ContentFreshnessAssessment


def test_initial_draft_response_paths_share_exact_packet_binding() -> None:
    packet_id = "content_research_packet_response_binding"
    packet_digest = "a" * 64
    proposal = ContentPlanningProposal.model_construct(
        research_packet_id=packet_id,
        research_packet_digest=packet_digest,
    )

    assert initial_draft_packet_fields(proposal=proposal) == {
        "research_packet_id": packet_id,
        "research_packet_digest": packet_digest,
    }
    queued = queued_initial_draft_response(
        "content_work_item_response_binding",
        proposal.proposal_id,
        "run_response_binding",
        False,
        proposal=proposal,
    )
    assert queued.research_packet_id == packet_id
    assert queued.research_packet_digest == packet_digest
    with pytest.raises(ValueError, match="packet binding"):
        initial_draft_packet_fields(
            proposal=proposal,
            research_packet_id="content_research_packet_other",
            research_packet_digest=packet_digest,
        )


def test_packet_derivation_does_not_promote_planning_assertion_evidence(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    case.planning_input = case.planning_input.model_copy(
        update={"evidence_ids": ["ev_planning_assertion_outside"]}
    )

    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )

    assert prepared.packet is not None
    assert "ev_planning_assertion_outside" not in prepared.packet.evidence_ids
    assert prepared.packet.context_receipt is not None
    assert (
        "ev_planning_assertion_outside" not in prepared.packet.context_receipt.planning_evidence_ids
    )


def test_packet_binding_rejects_a_different_planning_work_item(tmp_path: Path) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None
    foreign_packet = prepared.packet.model_copy(
        update={"current_work_item_id": "content_work_item_foreign"}
    )

    with pytest.raises(ValueError, match="work item"):
        bind_research_packet_to_planning_input(case.planning_input, foreign_packet)


def test_packet_revalidation_rejects_a_different_planning_work_item(tmp_path: Path) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None
    foreign_input = case.planning_input.model_copy(
        update={"work_item_id": "content_work_item_foreign"}
    )

    blocker = current_research_packet_blocker(
        store=case.store,
        packet=prepared.packet,
        snapshot=case.snapshot,
        planning_input=foreign_input,
    )

    assert blocker is not None
    assert blocker.reason == "work_item_mismatch"


def test_packet_revalidation_reuses_persisted_preparation_receipt(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )
    assert prepared.packet is not None
    assert prepared.packet.preparation_receipt_id is not None
    assert prepared.packet.preparation_receipt_digest is not None

    blocker = current_research_packet_blocker(
        store=case.store,
        packet=prepared.packet,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )

    assert blocker is None


def test_packet_revalidation_ignores_observation_only_freshness_checked_at(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    case.snapshot.freshness_assessment = ContentFreshnessAssessment(
        state="fresh",
        checked_at=datetime(2026, 9, 16, 0, 0, tzinfo=UTC),
        requires_refresh=False,
        summary="Dane świeże.",
        next_step="Można użyć danych.",
    )
    prepared = prepare_content_research_packet(
        store=case.store,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )
    assert prepared.packet is not None

    case.snapshot.freshness_assessment = case.snapshot.freshness_assessment.model_copy(
        update={
            "checked_at": datetime(2026, 9, 16, 0, 1, tzinfo=UTC),
            "state_label": "odświeżony opis",
            "summary": "Inny tekst prezentacyjny.",
            "next_step": "Inny krok prezentacyjny.",
        }
    )

    blocker = current_research_packet_blocker(
        store=case.store,
        packet=prepared.packet,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )

    assert blocker is None


@pytest.mark.parametrize(
    "freshness_update",
    [
        {"state": "stale"},
        {"requires_refresh": True},
        {"connector_labels_requiring_refresh": ["Google Search Console"]},
        {
            "connector_covered_windows": {
                "google_search_console": ConnectorCoveredWindow(
                    date_start="2026-09-01",
                    date_end="2026-09-15",
                    completeness="complete",
                )
            }
        },
    ],
)
def test_packet_revalidation_rejects_semantic_freshness_drift(
    tmp_path: Path,
    freshness_update: dict[str, object],
) -> None:
    case = build_packet_preparation_case(tmp_path)
    case.snapshot.freshness_assessment = ContentFreshnessAssessment(
        state="fresh",
        checked_at=datetime(2026, 9, 16, 0, 0, tzinfo=UTC),
        requires_refresh=False,
        summary="Dane świeże.",
        next_step="Można użyć danych.",
    )
    prepared = prepare_content_research_packet(
        store=case.store,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )
    assert prepared.packet is not None

    case.snapshot.freshness_assessment = case.snapshot.freshness_assessment.model_copy(
        update=freshness_update
    )
    blocker = current_research_packet_blocker(
        store=case.store,
        packet=prepared.packet,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )

    assert blocker is not None
    assert blocker.reason == "context_receipt_mismatch"


def test_packet_revalidation_rejects_source_fact_freshness_date_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )
    assert prepared.packet is not None
    source_fact_ids = set(case.source_pack.source_fact_ids)
    changed_facts = tuple(
        fact.model_copy(update={"freshness_date": "2099-01-01"})
        if fact.source_id in source_fact_ids
        else fact
        for fact in ekologus_source_facts()
    )
    monkeypatch.setattr(
        research_packet_derivation,
        "ekologus_source_facts",
        lambda: changed_facts,
    )

    blocker = current_research_packet_blocker(
        store=case.store,
        packet=prepared.packet,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )

    assert blocker is not None
    assert blocker.reason == "context_receipt_mismatch"


def test_reused_revision_response_propagates_out_of_band_packet_binding() -> None:
    revision = draft_revision(
        "content_work_item_retained",
        "content_revision_retained_packet",
        "d" * 64,
    ).model_copy(
        update={
            "research_packet_id": "content_research_packet_retained",
            "research_packet_digest": "e" * 64,
        }
    )
    resolution = InitialDraftAuthorityReused(
        classification_run_id="classification_run_retained",
        classification_run_digest="a" * 64,
        decision_set_digest="b" * 64,
        requested_work_item_id="content_work_item_retained",
        lookup_basis="retained",
        current_work_item_id="content_work_item_current",
        retained_work_item_id="content_work_item_retained",
        revision_work_item_id=revision.work_item_id,
        identity_reconciliation_status="fork",
        revision=revision,
        approved_review=draft_review(revision),
    )

    response = map_initial_draft_authority_response(resolution)

    assert response is not None
    assert response.research_packet_id == revision.research_packet_id
    assert response.research_packet_digest == revision.research_packet_digest
    assert response.reuse_binding is not None
    assert response.reuse_binding.revision_id == revision.revision_id


def test_new_page_proposal_rejects_a_research_packet_binding() -> None:
    _foundation, proposal = _exact_inputs()
    payload = proposal.model_dump(mode="python")
    payload.update(
        {
            "research_packet_id": "content_research_packet_forbidden",
            "research_packet_digest": "f" * 64,
        }
    )

    with pytest.raises(ValueError, match="New-page planning cannot carry a research packet"):
        type(proposal).model_validate(payload)


def test_packet_read_projection_reports_latest_source_pack_separately_from_bound_packet(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None
    latest = case.source_pack.model_copy(
        update={
            "binding_id": "content_source_pack_binding_latest_projection",
            "binding_digest": "f" * 64,
        }
    )

    class ProjectionStore:
        def list_content_source_pack_bindings(self, *, current_work_item_id: str | None = None):
            del current_work_item_id
            return [latest]

        def load_content_source_pack_binding(self, binding_id: str):
            return case.source_pack if binding_id == case.source_pack.binding_id else None

        def load_content_delivery_identity(self, binding_id: str):
            return case.identity if binding_id == case.identity.binding_id else None

        def load_production_classification_for_work_item(self, work_item_id: str):
            del work_item_id
            return case.store.classification

        def load_content_source_fact_authority_receipt_for_identity(
            self,
            identity_binding_id: str,
            current_work_item_id: str,
            source_fact_ids: tuple[str, ...],
        ):
            del identity_binding_id, current_work_item_id, source_fact_ids
            return case.store.authority

    projection = revalidate_content_research_packet(
        store=ProjectionStore(),
        packet=prepared.packet,
        snapshot_loader=lambda _work_item_id: case.snapshot,
    )

    assert projection.current_source_pack_binding_id == latest.binding_id
    assert projection.current_source_pack_binding_digest == latest.binding_digest
    assert prepared.packet.source_pack_binding_id != projection.current_source_pack_binding_id
