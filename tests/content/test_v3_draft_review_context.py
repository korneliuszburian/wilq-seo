"""Both content consumers bind the same approved v3 input before a model turn."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.content import test_v3_packet_planning_status_read as status_fixture
from tests.content.initial_draft_readability_fakes import generation_contract
from tests.content.test_frozen_planning_input_draft import _service_input
from tests.content.test_planning_generation_intent_v3 import (
    _approve_exact_packet,
    _with_cta_drift,
)
from tests.content.test_planning_generation_intent_v3_generation import _raw_input
from tests.content.test_v3_packet_planning_status_read import (
    _approved_packet_with_read,
    _patch_registry_fact,
)
from wilq.content.drafts import initial_full_draft
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
    content_planning_inventory_digest,
)
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.quality import review_packet_binding, semantic_review_service
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticReviewRequest,
    ContentSemanticReviewResponse,
)
from wilq.content.quality.semantic_review_queue import _packet_claim_guard
from wilq.content.quality.semantic_review_turn import semantic_review_turn_request
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.research_packet_v3_preview import ResearchPacketV3Preview
from wilq.content.workflow.store.store import ContentWorkflowStore


def _consumers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    original_proposal = status_fixture._proposal

    def document_proposal(**kwargs):
        proposal = original_proposal(**kwargs)
        return proposal.model_copy(
            update={
                "sections": [
                    section.model_copy(update={"section_id": f"section_exact_{index:02d}"})
                    for index, section in enumerate(proposal.sections, start=1)
                ]
            }
        )

    monkeypatch.setattr(status_fixture, "_proposal", document_proposal)
    store, packet, pack, fact, digest = _approved_packet_with_read(tmp_path, monkeypatch)
    proposal = store.for_subject_input(
        packet.work_item_id,
        ContentPlanningSubject(content_kind="editorial", service_card_id=None),
        digest,
    )
    frozen = store.frozen_planning_input(packet.work_item_id, digest)
    assert proposal is not None and frozen is not None
    current = {
        "input": _raw_input(packet).model_copy(
            update={"planning_input_digest": packet.planning_input_digest}
        ),
        "packet": packet,
    }

    def build_input(*_args, **_kwargs):
        return ContentPlanningInputBuildResult(planning_input=current["input"])

    monkeypatch.setattr(initial_full_draft, "_current_planning_input", build_input)
    monkeypatch.setattr(initial_full_draft, "content_planning_proposal_store", lambda: store)
    monkeypatch.setattr(review_packet_binding, "build_content_planning_input", build_input)
    monkeypatch.setattr(semantic_review_service, "build_content_planning_input", build_input)
    monkeypatch.setattr(
        semantic_review_service, "content_workflow_store", lambda: ContentWorkflowStore(store.path)
    )
    # Reuse the existing current-observation seam, without replacing its authority resolver.
    from wilq.content.planning import generation_intent_v3

    monkeypatch.setattr(
        generation_intent_v3,
        "_load_current_packet",
        lambda _work_item_id, _identity_action_id: current["packet"],
    )
    revision = _revision_for_context(proposal, frozen, fact)
    snapshot = SimpleNamespace(
        preflight=SimpleNamespace(
            item=SimpleNamespace(id=proposal.work_item_id, content_kind="editorial")
        ),
        planning_workspace=SimpleNamespace(proposal=proposal, section_map_current=True),
        revision_workspace=SimpleNamespace(latest_revision=None, context_current=False),
        structured_generation=SimpleNamespace(
            structured_generation_result=SimpleNamespace(
                contract=generation_contract(), blockers=[]
            )
        ),
    )
    return SimpleNamespace(
        proposal=proposal,
        frozen=frozen,
        packet=packet,
        pack=pack,
        fact=fact,
        current=current,
        snapshot=snapshot,
        revision=revision,
        store=store,
        workflow_store=ContentWorkflowStore(store.path),
    )


def _revision_for_context(proposal, frozen, fact) -> ContentDraftRevision:
    return ContentDraftRevision(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id=proposal.work_item_id,
        revision_id="revision-v3-context",
        revision_number=1,
        draft_package_id="package-v3-context",
        draft_package_digest="b" * 64,
        title="Dokument testowy",
        final_canonical_url=proposal.final_canonical_url,
        inventory_digest=content_planning_inventory_digest(frozen.inventory),
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Dokument testowy",
            meta_title="Tytuł testowy",
            meta_description="Opis testowy",
            h1="Nagłówek testowy",
            lead="Wprowadzenie testowe.",
        ),
        created_by="synthetic-context-test",
        created_at=datetime(2026, 10, 2, tzinfo=UTC),
        content_digest="a" * 64,
        planning_digest=proposal.planning_digest,
        planning_input_digest=frozen.planning_input_digest,
        research_packet_id=proposal.research_packet_id,
        research_packet_digest=proposal.research_packet_digest,
        content_kind=proposal.content_kind,
        service_card_id=proposal.service_card_id,
        sections=[
            ContentDraftRevisionSection(
                section_id=proposal.sections[0].section_id,
                heading=proposal.sections[0].heading,
                body_markdown=fact.extracted_fact,
                evidence_ids=list(fact.evidence_ids),
            )
        ],
    )

def _draft_request(case):
    proposal = case.snapshot.planning_workspace.proposal
    return ContentInitialDraftRequest(
        expected_proposal_id=proposal.proposal_id,
        expected_planning_digest=proposal.planning_digest,
        expected_planning_input_digest=proposal.planning_input_digest,
        requested_by="synthetic-context-test",
    )


def _draft(case):
    return initial_full_draft._prepare_inputs(
        case.snapshot,
        _draft_request(case),
        workflow_store=case.workflow_store,
    )


def _review_snapshot(case):
    snapshot = SimpleNamespace(**vars(case.snapshot))
    snapshot.revision_workspace = SimpleNamespace(
        latest_revision=case.revision,
        context_current=True,
    )
    return snapshot


def _review(case, **kwargs):
    return review_packet_binding.resolve_content_review_inputs(
        snapshot=_review_snapshot(case),
        revision_id=case.revision.revision_id,
        expected_revision_digest=case.revision.content_digest,
        workflow_store=case.workflow_store,
        **kwargs,
    )


def _persist_revision(case) -> None:
    with sqlite3.connect(case.store.path) as connection:
        connection.execute(
            "INSERT INTO content_draft_revisions "
            "(revision_id, work_item_id, revision_number, content_digest, "
            "created_at, payload_json) "
            "VALUES (?, ?, 1, ?, ?, ?)",
            (
                case.revision.revision_id,
                case.revision.work_item_id,
                case.revision.content_digest,
                case.revision.created_at.isoformat(),
                case.revision.model_dump_json(),
            ),
        )


def test_same_approved_v3_input_reaches_both_consumers_and_model_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _consumers(tmp_path, monkeypatch)
    draft = _draft(case)
    review = _review(case)
    assert not isinstance(draft, ContentInitialDraftResponse), draft
    assert review.blocker is None, review.blocker
    assert review.inputs is not None
    assert draft.planning_input == review.inputs.planning_input == case.frozen
    assert draft.packet_context == review.inputs.packet_context
    context = draft.packet_context
    assert context is not None and context.current_authority
    assert context.proposal == case.proposal
    assert context.packet == case.packet
    assert context.receipt == case.workflow_store.load_research_packet_v3_approval_receipt(
        case.proposal.research_packet_id
    )
    assert context.subject == ContentPlanningSubject(content_kind="editorial", service_card_id=None)

    draft_turn = initial_full_draft_turn_request(
        planning_input=draft.planning_input,
        proposal=draft.proposal,
        generation_contract=draft.generation_contract,
        prepared_plan=draft.draft_plan,
    )
    review_turn = semantic_review_turn_request(
        revision=case.revision,
        planning_input=review.inputs.planning_input,
        proposal=review.inputs.proposal,
    )
    draft_payload = json.loads(draft_turn.untrusted_context)
    review_payload = json.loads(review_turn.untrusted_context)
    assert draft_payload["research_packet_binding"] == review_payload["research_packet_binding"]
    binding = draft_payload["research_packet_binding"]
    assert binding["receipt_digest"] == context.receipt.receipt_digest
    assert binding["subject_key"] == context.subject.subject_key
    assert (
        draft_payload["planning_input"]["source_facts"]
        == (review_payload["planning_input"]["source_facts"])
        == case.frozen.model_dump(mode="json")["source_facts"]
    )
    for turn in (draft_turn, review_turn):
        assert "UNREVIEWED OLD WP" not in turn.untrusted_context
        assert "exact query signal" not in turn.untrusted_context

    _persist_revision(case)
    guard = _packet_claim_guard(SimpleNamespace(review_inputs=review.inputs))
    assert guard is not None
    with sqlite3.connect(case.store.path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert guard(connection) is None


def _inject_context_drift(case, monkeypatch, fault: str) -> None:
    if fault == "subject":
        service = _service_input(
            work_item_id=case.proposal.work_item_id,
            research_packet_id="content_research_packet_unused",
            research_packet_digest="b" * 64,
        )
        case.current["input"] = ContentPlanningInput.model_validate(
            case.current["input"].model_dump()
            | {
                "content_kind": "service",
                "confirmed_service_card_id": service.confirmed_service_card_id,
                "service_candidates": service.service_candidates,
                "service_label": service.service_label,
            }
        )
    elif fault == "packet":
        proposal = case.proposal.model_copy(update={"research_packet_digest": "f" * 64})
        case.snapshot.planning_workspace.proposal = proposal
        case.revision = case.revision.model_copy(update={"research_packet_digest": "f" * 64})
    elif fault == "receipt":
        monkeypatch.setattr(
            ContentWorkflowStore, "load_research_packet_v3_approval_receipt", lambda *_args: None
        )
    elif fault == "foreign_receipt":
        foreign_receipt = _approve_exact_packet(case.workflow_store, _with_cta_drift(case.packet))
        monkeypatch.setattr(
            ContentWorkflowStore,
            "load_research_packet_v3_approval_receipt",
            lambda *_args: foreign_receipt,
        )
    elif fault == "fact":
        _patch_registry_fact(
            monkeypatch,
            case.fact.model_copy(
                update={
                    "extracted_fact": "Zmieniony fakt po zatwierdzeniu.",
                }
            ),
        )
    elif fault in {"identity", "source_pack"}:
        changed = case.packet.model_copy(
            update={
                "identity_digest" if fault == "identity" else "source_pack_hash": "9" * 64,
                **(
                    {"source_pack_id": f"source_pack_v3_{'9' * 64}"}
                    if fault == "source_pack"
                    else {}
                ),
            }
        )
        digest = canonical_json_digest(changed.semantic_payload())
        case.current["packet"] = ResearchPacketV3Preview.model_validate(
            changed.model_dump(mode="python")
            | {"preview_hash": digest, "preview_id": f"content_research_packet_v3_{digest[:24]}"},
        )
    elif fault == "input":
        case.current["input"] = case.current["input"].model_copy(
            update={
                "planning_input_digest": "0" * 64,
            }
        )
    else:
        changed = case.frozen.model_copy(update={"buyer_problem": "Zmieniony problem."})
        monkeypatch.setattr(type(case.store), "frozen_planning_input", lambda *_args: changed)


def _private_rows(case) -> tuple[int, ...]:
    with sqlite3.connect(case.store.path) as connection:
        return tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "codex_runs",
                "content_planning_proposals",
                "content_planning_input_snapshots",
            )
        )


@pytest.mark.parametrize(
    ("fault", "code"),
    [
        ("subject", "research_packet_v3_subject_mismatch"),
        ("packet", "research_packet_v3_digest_mismatch"),
        ("receipt", "research_packet_v3_approval_missing"),
        ("foreign_receipt", "research_packet_v3_digest_mismatch"),
        ("fact", "research_packet_v3_registry_drift"),
        ("identity", "research_packet_v3_identity_mismatch"),
        ("source_pack", "research_packet_v3_current_drift"),
        ("input", "research_packet_v3_input_drift"),
        ("frozen", "research_packet_v3_frozen_input_identity_mismatch"),
    ],
)
def test_v3_drift_blocks_both_consumers_before_model_or_new_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    code: str,
) -> None:
    case = _consumers(tmp_path, monkeypatch)
    _inject_context_drift(case, monkeypatch, fault)

    before = _private_rows(case)
    draft = _draft(case)
    review = _review(case)
    assert isinstance(draft, ContentInitialDraftResponse)
    assert draft.status == "blocked" and draft.runtime.status == "not_started"
    assert code in draft.blockers[0].source_codes
    assert review.blocker is not None and review.inputs is None
    assert code in review.blocker.source_codes

    class NoModelOrWrite:
        def __getattr__(self, name):
            raise AssertionError(f"Blocked context reached model/write: {name}")

    sentinel = NoModelOrWrite()
    generated = initial_full_draft.generate_initial_full_draft(
        snapshot=case.snapshot,
        request=_draft_request(case),
        client=sentinel,
        workflow_store=case.workflow_store,
        run_store=sentinel,
    )
    assert generated.status == "blocked" and code in generated.blockers[0].source_codes
    reviewed = semantic_review_service.generate_content_semantic_review(
        snapshot=_review_snapshot(case),
        revision_id=case.revision.revision_id,
        request=ContentSemanticReviewRequest(
            expected_revision_digest=case.revision.content_digest,
            requested_by="synthetic-test",
        ),
        client=sentinel,
        store=sentinel,
        run_store=sentinel,
    )
    assert isinstance(reviewed, ContentSemanticReviewResponse)
    assert reviewed.status == "blocked" and code in reviewed.blockers[0].source_codes
    assert _private_rows(case) == before


def test_retained_v3_context_is_readable_without_current_identity_permission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _consumers(tmp_path, monkeypatch)
    _patch_registry_fact(
        monkeypatch,
        case.fact.model_copy(
            update={
                "extracted_fact": "Zmieniony fakt po zatwierdzeniu.",
            }
        ),
    )
    historical = _review(case, require_current_authority=False)
    assert historical.inputs is not None, historical.blocker
    assert historical.inputs.planning_input == case.frozen
    assert not historical.inputs.packet_context.current_authority
    assert _review(case).blocker is not None
    assert isinstance(_draft(case), ContentInitialDraftResponse)
    with pytest.raises(ValueError):
        initial_full_draft_turn_request(
            planning_input=case.frozen,
            proposal=case.proposal,
            generation_contract=generation_contract(),
        )
    monkeypatch.setattr(
        ContentWorkflowStore, "load_research_packet_v3_approval_receipt", lambda *_args: None
    )
    assert _review(case, require_current_authority=False).blocker is not None


def test_v3_review_context_is_checked_at_claim_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _consumers(tmp_path, monkeypatch)
    inputs = _review(case).inputs
    assert inputs is not None
    assert review_packet_binding.content_review_inputs_match_revision(case.revision, inputs)
    guard = _packet_claim_guard(SimpleNamespace(review_inputs=inputs))
    assert guard is not None
    _persist_revision(case)
    with sqlite3.connect(case.store.path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert guard(connection) is None
        case.current["packet"] = _with_cta_drift(case.packet)
        blocked = guard(connection)
        assert blocked is not None
        assert "research_packet_v3_current_drift" in blocked.source_codes
        case.current["packet"] = case.packet
        connection.execute(
            "UPDATE content_draft_revisions SET payload_json = '{}' WHERE revision_id = ?",
            (case.revision.revision_id,),
        )
        assert guard(connection) is not None


def test_current_packet_input_drift_blocks_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _consumers(tmp_path, monkeypatch)
    inputs = _review(case).inputs
    assert inputs is not None
    guard = _packet_claim_guard(SimpleNamespace(review_inputs=inputs))
    assert guard is not None
    _persist_revision(case)
    with sqlite3.connect(case.store.path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert guard(connection) is None
        case.current["packet"] = ResearchPacketV3Preview.model_validate(
            case.packet.model_dump(mode="python") | {"planning_input_digest": "0" * 64},
        )
        assert case.current["packet"].preview_hash == case.packet.preview_hash
        blocked = guard(connection)
        assert blocked is not None
        assert "research_packet_v3_input_drift" in blocked.source_codes
