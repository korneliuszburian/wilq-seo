from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from types import SimpleNamespace

import pytest

import wilq.content.workflow.target.dev_draft_action as dev_draft_action
from tests.content.packet_plan_draft_fixtures import build_packet_preparation_case
from wilq.actions.apply_lifecycle import ApplyDependencies, apply_action
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
)
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.research_packet_preparation import prepare_content_research_packet
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.target.dev_draft_action import CONTENT_DEV_DRAFT_ACTION_TYPE
from wilq.schemas import (
    ActionApplyRequest,
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)


def _approved_binding() -> ContentDraftRevisionBinding:
    store = content_workflow_store()
    created = store.append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id="work_item_dev_claim",
            draft_package_id="draft_package_dev_claim",
            draft_package_digest="b" * 64,
            planning_digest="c" * 64,
            final_canonical_url="https://ekologus.pl/dev-claim/",
            title="Zatwierdzona treść",
            sections=[
                ContentDraftRevisionSection(
                    heading="Zakres",
                    body_markdown="Treść dokładnej rewizji.",
                    evidence_ids=["ev_dev_claim"],
                )
            ],
            created_by="operator_test",
        )
    )
    assert created.revision is not None
    revision = created.revision
    reviewed = store.review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            decision="approved",
            reviewed_by="operator_test",
            checked_items=["tekst", "dowody"],
            evidence_ids=["ev_dev_claim"],
        )
    )
    assert reviewed.review is not None
    return ContentDraftRevisionBinding(
        work_item_id=revision.work_item_id,
        handoff_id=f"wordpress_draft_handoff_{revision.work_item_id}_{revision.revision_id}",
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
        draft_package_id=revision.draft_package_id,
        draft_package_digest=revision.draft_package_digest,
        planning_digest=revision.planning_digest,
        approval_decision_id=reviewed.review.decision_id,
        final_canonical_url=revision.final_canonical_url,
    )


def _action(action_id: str, binding: ContentDraftRevisionBinding) -> ActionObject:
    details = {"wordpress_draft_binding": binding.model_dump(mode="json")}
    events = [
        AuditEvent(
            id=f"{action_id}_{event_type}",
            action_id=action_id,
            event_type=event_type,
            actor="operator_test",
            summary=event_type,
            details=details,
        )
        for event_type in (
            "action_preview_generated",
            "human_review_approved_for_prepare",
            "action_apply_confirmed",
            "action_impact_check_completed",
        )
    ]
    return ActionObject(
        id=action_id,
        title="Utwórz szkic dev",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.ready,
        evidence_ids=["ev_dev_claim"],
        human_diagnosis="Dokładna rewizja jest gotowa.",
        recommended_reason="Utwórz wyłącznie jeden szkic.",
        payload={
            "action_type": CONTENT_DEV_DRAFT_ACTION_TYPE,
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "payload_preview": [{"apply_allowed": True, "api_mutation_ready": True}],
            "content_target_draft_binding": {
                "work_item_id": binding.work_item_id,
                "revision_id": binding.revision_id,
                "revision_digest": binding.content_digest,
                "research_packet_id": None,
                "research_packet_digest": None,
            },
            "wordpress_draft_binding": binding.model_dump(mode="json"),
        },
        validation_status="valid",
        created_by="operator_test",
        audit_events=events,
    )


def test_two_dev_draft_actions_for_one_revision_execute_one_adapter(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "dev_claim.sqlite3"))
    binding = _approved_binding()
    adapter_calls: list[str] = []
    adapter_started = Event()
    release_adapter = Event()

    def execute_adapter(action, _adapter, capability):
        assert isinstance(capability, ContentDraftRevisionBinding)
        adapter_calls.append(action.id)
        adapter_started.set()
        assert release_adapter.wait(timeout=5)
        execution = ContentWordPressDraftExecutionResult(
            status="created",
            mode="live",
            boundary=ContentWordPressDraftExecutionBoundary(
                live_write_enabled=True,
                live_adapter_configured=True,
            ),
            revision_binding=capability,
            wordpress_post_id=str(416 + len(adapter_calls)),
            expected_content_digest="9" * 64,
            observed_content_digest="8" * 64,
            expected_acf_digest="7" * 64,
            observed_acf_digest="6" * 64,
            external_write_attempted=True,
        )
        return {"execution_result": execution.model_dump(mode="json")}, []

    store = content_workflow_store()
    dependencies = ApplyDependencies(
        review_gate=lambda action: action.review_gate,
        wordpress_apply_capability=lambda *_args: (None, []),
        mutation_adapter=lambda _action: "content_dev_draft_execution_boundary",
        execute_mutation_adapter=execute_adapter,
        connector_status=lambda _connector: SimpleNamespace(configured=True),
        impact_status=lambda _event: "checked",
        wordpress_apply_claim=store.claim_wordpress_revision_apply,
        finish_wordpress_apply_claim=store.finish_wordpress_revision_apply_claim,
        status_label=lambda status: status,
        audit_event_label=lambda event: event,
    )
    request = ActionApplyRequest(
        confirm=True,
        confirmed_by="operator_test",
        wordpress_draft=binding,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(
            apply_action,
            _action("act_content_dev_draft_first", binding),
            request,
            dependencies=dependencies,
        )
        assert adapter_started.wait(timeout=5)
        second = executor.submit(
            apply_action,
            _action("act_content_dev_draft_second", binding),
            request,
            dependencies=dependencies,
        ).result(timeout=5)
        release_adapter.set()
        first = first_future.result(timeout=5)

    assert first.applied is True
    assert second.applied is False
    assert [blocker.code for blocker in second.wordpress_revision_blockers] == [
        "wordpress_revision_apply_in_progress"
    ]
    assert adapter_calls == ["act_content_dev_draft_first"]
    restarted_store = content_workflow_store()
    persisted = restarted_store.latest_wordpress_draft_execution(
        binding.work_item_id,
        handoff_id=binding.handoff_id,
        revision_id=binding.revision_id,
        revision_digest=binding.content_digest,
    )
    assert persisted is not None
    assert persisted.wordpress_post_id == "417"
    assert persisted.expected_content_digest == "9" * 64
    assert persisted.observed_content_digest == "8" * 64
    assert persisted.expected_acf_digest == "7" * 64
    assert persisted.observed_acf_digest == "6" * 64

    replay = apply_action(
        _action("act_content_dev_draft_replay", binding),
        request,
        dependencies=dependencies,
    )
    assert replay.applied is False
    assert [blocker.code for blocker in replay.wordpress_revision_blockers] == [
        "wordpress_revision_already_applied"
    ]

    child_created = restarted_store.append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=binding.work_item_id,
            base_revision_id=binding.revision_id,
            draft_package_id=binding.draft_package_id,
            draft_package_digest=binding.draft_package_digest,
            planning_digest=binding.planning_digest,
            final_canonical_url=binding.final_canonical_url,
            title="Osobno zatwierdzona wersja potomna",
            sections=[
                ContentDraftRevisionSection(
                    heading="Zakres",
                    body_markdown="Nowa treść wymagająca osobnego review.",
                    evidence_ids=["ev_dev_claim"],
                )
            ],
            created_by="operator_test",
        )
    )
    assert child_created.revision is not None
    child_revision = child_created.revision
    child_reviewed = restarted_store.review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=child_revision.work_item_id,
            revision_id=child_revision.revision_id,
            revision_digest=child_revision.content_digest,
            decision="approved",
            reviewed_by="operator_test",
            checked_items=["tekst", "dowody"],
            evidence_ids=["ev_dev_claim"],
        )
    )
    assert child_reviewed.review is not None
    child_binding = ContentDraftRevisionBinding(
        work_item_id=child_revision.work_item_id,
        handoff_id=(
            f"wordpress_draft_handoff_{child_revision.work_item_id}_"
            f"{child_revision.revision_id}"
        ),
        revision_id=child_revision.revision_id,
        content_digest=child_revision.content_digest,
        draft_package_id=child_revision.draft_package_id,
        draft_package_digest=child_revision.draft_package_digest,
        planning_digest=child_revision.planning_digest,
        approval_decision_id=child_reviewed.review.decision_id,
        final_canonical_url=child_revision.final_canonical_url,
    )
    child = apply_action(
        _action("act_content_dev_draft_child", child_binding),
        request.model_copy(update={"wordpress_draft": child_binding}),
        dependencies=dependencies,
    )

    assert child.applied is True
    assert adapter_calls == [
        "act_content_dev_draft_first",
        "act_content_dev_draft_child",
    ]


@pytest.mark.parametrize(
    ("fault", "expected_code"),
    [
        ("unbound", "wordpress_action_chain_binding_mismatch"),
        ("mismatched", "wordpress_action_chain_binding_mismatch"),
        ("action_full_mismatch", "wordpress_revision_binding_mismatch"),
        ("wrong_actor", "wordpress_action_actor_mismatch"),
        ("reordered", "wordpress_action_chain_order_invalid"),
    ],
)
def test_invalid_dev_draft_action_chain_stops_before_claim_and_adapter(
    monkeypatch,
    tmp_path,
    fault: str,
    expected_code: str,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "invalid_chain.sqlite3"))
    binding = _approved_binding()
    action = _action("act_content_dev_draft_invalid_chain", binding)
    if fault == "unbound":
        action.audit_events[0].details = {}
    elif fault == "mismatched":
        mismatched = binding.model_copy(update={"content_digest": "d" * 64})
        action.audit_events[0].details = {
            "wordpress_draft_binding": mismatched.model_dump(mode="json")
        }
    elif fault == "wrong_actor":
        action.audit_events[2].actor = "inny_operator"
    elif fault == "action_full_mismatch":
        action.payload["wordpress_draft_binding"] = binding.model_copy(
            update={"approval_decision_id": "inna_decyzja"}
        ).model_dump(mode="json")
    else:
        action.audit_events[1].created_at = action.audit_events[0].created_at - timedelta(
            seconds=1
        )

    claim_calls: list[str] = []
    adapter_calls: list[str] = []
    store = content_workflow_store()

    def claim(*args, **kwargs):
        claim_calls.append("claim")
        return store.claim_wordpress_revision_apply(*args, **kwargs)

    dependencies = ApplyDependencies(
        review_gate=lambda current: current.review_gate,
        wordpress_apply_capability=lambda *_args: (None, []),
        mutation_adapter=lambda _action: "content_dev_draft_execution_boundary",
        execute_mutation_adapter=lambda *_args: (adapter_calls.append("adapter"), [])[1],
        connector_status=lambda _connector: SimpleNamespace(configured=True),
        impact_status=lambda _event: "checked",
        wordpress_apply_claim=claim,
        finish_wordpress_apply_claim=store.finish_wordpress_revision_apply_claim,
        status_label=lambda status: status,
        audit_event_label=lambda event: event,
    )
    result = apply_action(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=binding,
        ),
        dependencies=dependencies,
    )

    assert result.applied is False
    assert [blocker.code for blocker in result.wordpress_revision_blockers] == [
        expected_code
    ]
    assert claim_calls == []
    assert adapter_calls == []


def _packet_bound_revision_and_binding(packet_case, packet):
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_packet_apply",
        work_item_id=packet_case.identity.current_work_item_id,
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="draft_package_packet_apply",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        research_packet_id=packet.packet_id,
        research_packet_digest=packet.packet_digest,
        final_canonical_url=packet_case.identity.public_url,
        title="Packet-bound revision",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres",
                body_markdown="Treść exact.",
                evidence_ids=["ev_packet_apply"],
            )
        ],
        created_by="operator_test",
    )
    return revision, ContentDraftRevisionBinding(
        work_item_id=revision.work_item_id,
        handoff_id=f"wordpress_draft_handoff_{revision.work_item_id}_{revision.revision_id}",
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
        draft_package_id=revision.draft_package_id,
        draft_package_digest=revision.draft_package_digest,
        planning_digest=revision.planning_digest,
        approval_decision_id="decision_packet_apply",
        final_canonical_url=revision.final_canonical_url,
        research_packet_id=packet.packet_id,
        research_packet_digest=packet.packet_digest,
    )


def _packet_bound_action(action_id, binding, packet):
    action = _action(action_id, binding)
    action.payload["content_target_draft_binding"].update(
        {
            "research_packet_id": packet.packet_id,
            "research_packet_digest": packet.packet_digest,
        }
    )
    return action


def test_dev_draft_apply_blocks_when_revision_research_packet_was_superseded(
    monkeypatch,
    tmp_path,
) -> None:
    packet_case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=packet_case.store,
        snapshot=packet_case.snapshot,
        planning_input=packet_case.planning_input,
    )
    assert prepared.packet is not None
    assert prepared.packet.status == "exact_current"
    packet = prepared.packet
    revision, binding = _packet_bound_revision_and_binding(packet_case, packet)
    action = _packet_bound_action("act_content_dev_draft_packet_blocked", binding, packet)

    class EvidenceStore:
        def load_draft_revision_state(self, _work_item_id):
            return SimpleNamespace(latest_revision=revision)

        def __getattr__(self, name):
            return getattr(packet_case.store, name)

    evidence_store = EvidenceStore()
    packet_case.store.source_pack = packet_case.source_pack.model_copy(
        update={
            "binding_id": "content_source_pack_binding_superseding",
            "binding_digest": "e" * 64,
        }
    )
    monkeypatch.setattr(dev_draft_action, "content_workflow_store", lambda: evidence_store)

    claim_calls: list[str] = []
    adapter_calls: list[str] = []

    def claim(*_args, **_kwargs):
        claim_calls.append("claim")
        return "acquired"

    dependencies = ApplyDependencies(
        review_gate=lambda current: current.review_gate,
        wordpress_apply_capability=lambda *_args: (None, []),
        mutation_adapter=lambda _action: "content_dev_draft_execution_boundary",
        execute_mutation_adapter=lambda *_args: (adapter_calls.append("adapter"), ({}, []))[1],
        connector_status=lambda _connector: SimpleNamespace(configured=True),
        impact_status=lambda _event: "checked",
        wordpress_apply_claim=claim,
        finish_wordpress_apply_claim=lambda *_args, **_kwargs: None,
        status_label=lambda status: status,
        audit_event_label=lambda event: event,
        content_snapshot_loader=lambda _work_item_id: packet_case.snapshot,
    )
    result = apply_action(
        action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=binding,
        ),
        dependencies=dependencies,
    )

    assert result.applied is False
    assert [blocker.code for blocker in result.wordpress_revision_blockers] == [
        "research_packet_missing"
    ]
    assert result.wordpress_revision_blockers[0].label == "Research packet nie jest aktualny"
    assert claim_calls == []
    assert adapter_calls == []

    packet_case.store.source_pack = packet_case.source_pack

    def current_packet(*, packet, snapshot_loader, **_kwargs):
        assert packet is prepared.packet
        assert snapshot_loader(packet.current_work_item_id) is packet_case.snapshot
        return SimpleNamespace(status="current", blocker=None)

    monkeypatch.setattr(dev_draft_action, "revalidate_content_research_packet", current_packet)
    current_action = _packet_bound_action("act_content_dev_draft_packet_current", binding, packet)
    current_result = apply_action(
        current_action,
        ActionApplyRequest(
            confirm=True,
            confirmed_by="operator_test",
            wordpress_draft=binding,
        ),
        dependencies=dependencies,
    )

    assert current_result.applied is True
    assert current_result.wordpress_revision_blockers == []
    assert claim_calls == ["claim"]
    assert adapter_calls == ["adapter"]
