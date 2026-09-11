from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from httpx import Response

import apps.api.wilq_api.routers.content_selected_workspace as selected_workspace_router
import wilq.content.workflow.workspace.selected_workspace as selected_workspace_module
from apps.api.wilq_api.routers.content_selected_workspace import (
    register_content_selected_workspace_route,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.production import (
    WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
    ContentProductionAcceptancePolicy,
    ContentProductionClassificationProjection,
    ContentProductionProtectedBindingPolicy,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
    ContentDraftRevisionState,
)
from wilq.content.workflow.pipeline_steps.operator_steps import (
    ContentWorkflowOperatorFacts,
    ContentWorkflowOperatorJourney,
    build_content_workflow_operator_journey,
)
from wilq.content.workflow.workspace.document_lineage import (
    ContentDocumentWorkspaceDocumentLineage,
)
from wilq.content.workflow.workspace.document_workspace import (
    ContentDocumentWorkspace,
    ContentDocumentWorkspaceComparison,
    ContentDocumentWorkspaceDocument,
    ContentDocumentWorkspaceNextAction,
    ContentDocumentWorkspaceSourceSnapshot,
)

AUDIT_TIME = datetime(2026, 8, 30, 10, 5, tzinfo=UTC)


@dataclass(frozen=True)
class _RevisionFixture:
    current_revisions: tuple[ContentDraftRevision, ...]
    current_state: ContentDraftRevisionState
    retained_review: ContentDraftRevisionReview
    retained_state: ContentDraftRevisionState
    current_workspace: ContentDocumentWorkspace


@dataclass(frozen=True)
class _RequestFixture:
    response: Response
    store: _RouteStore
    factory_calls: list[object]
    snapshot_calls: list[tuple[str, object, ContentDraftRevisionState]]


def test_public_get_reuses_exact_bdo_binding_without_changing_current_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = WAVE0_PRODUCTION_ACCEPTANCE_POLICY
    binding = policy.protected_binding
    retained_work_item_id = binding.retained_work_item_id
    assert retained_work_item_id is not None
    revisions = _exact_revision_fixture(
        policy,
        binding,
        retained_work_item_id=retained_work_item_id,
    )
    request = _request_exact_bdo_workspace(
        monkeypatch,
        binding=binding,
        retained_work_item_id=retained_work_item_id,
        revisions=revisions,
    )

    assert request.response.status_code == 200
    payload = request.response.json()
    assert payload["response_type"] == "content_selected_workspace"
    assert payload["contract_version"] == "content_selected_workspace_v2"
    assert payload["status"] == "ready"
    assert payload["requested_work_item_id"] == binding.current_work_item_id
    assert payload["work_item_id"] == binding.current_work_item_id
    workspace = payload["workspace"]
    assert workspace["work_item_id"] == binding.current_work_item_id
    assert workspace["canonical_document"]["revision"]["work_item_id"] == (
        binding.current_work_item_id
    )
    assert workspace["canonical_document"]["revision_id"] == (
        revisions.current_revisions[-1].revision_id
    )
    assert workspace["canonical_document"]["revision_id"] != binding.revision_id
    assert workspace["next_action"]["kind"] == "none"
    assert workspace["next_action"]["kind"] not in {"prepare_document", "generate_document"}

    decision = payload["production_decision"]
    assert decision["status"] == "available"
    assert decision["decision"] == "reuse"
    assert decision["lookup_basis"] == "current"
    assert decision["canonical_path"] == binding.canonical_path
    assert decision["current_work_item_id"] == binding.current_work_item_id
    assert decision["retained_work_item_id"] == retained_work_item_id
    assert decision["generation_allowed"] is False
    revision_binding = decision["revision_binding"]
    assert revision_binding["current_work_item_id"] == binding.current_work_item_id
    assert revision_binding["retained_work_item_id"] == retained_work_item_id
    assert revision_binding["revision_work_item_id"] == retained_work_item_id
    assert revision_binding["revision_id"] == binding.revision_id
    assert revision_binding["revision_digest"] == binding.revision_digest
    assert revision_binding["verified_draft_action_ids"] == list(binding.action_ids)
    assert revision_binding["verified_draft_post_ids"] == list(binding.draft_post_ids)
    assert revision_binding["must_not_regenerate"] is True
    reusable = decision["reusable_document"]
    assert reusable["status"] == "ready"
    assert reusable["revision"]["work_item_id"] == retained_work_item_id
    assert reusable["revision"]["revision_id"] == binding.revision_id
    assert reusable["revision"]["content_digest"] == binding.revision_digest
    assert reusable["review"]["decision"] == "approved"
    assert reusable["review"]["revision_id"] == binding.revision_id
    assert reusable["review"]["revision_digest"] == binding.revision_digest

    assert len(revisions.current_revisions) == revisions.current_state.revision_count == 2
    assert revisions.current_state.latest_review is None
    assert revisions.retained_state.latest_review is revisions.retained_review
    assert request.factory_calls == [request.store]
    assert request.store.classification_calls == [binding.current_work_item_id]
    assert request.store.revision_calls == [binding.current_work_item_id, retained_work_item_id]
    assert request.snapshot_calls == [
        (binding.current_work_item_id, request.store, revisions.current_state)
    ]


class _RouteStore:
    def __init__(
        self,
        *,
        projection: ContentProductionClassificationProjection,
        states: dict[str, ContentDraftRevisionState],
    ) -> None:
        self.projection = projection
        self.states = states
        self.classification_calls: list[str] = []
        self.revision_calls: list[str] = []

    def load_production_classification_for_work_item(
        self,
        work_item_id: str,
    ) -> ContentProductionClassificationProjection:
        self.classification_calls.append(work_item_id)
        return self.projection

    def load_draft_revision_state(self, work_item_id: str) -> ContentDraftRevisionState:
        self.revision_calls.append(work_item_id)
        return self.states[work_item_id]


def _exact_revision_fixture(
    policy: ContentProductionAcceptancePolicy,
    binding: ContentProductionProtectedBindingPolicy,
    *,
    retained_work_item_id: str,
) -> _RevisionFixture:
    public_url = f"{policy.public_origin}{binding.canonical_path}/"
    current_revisions = (
        _revision(
            binding.current_work_item_id,
            f"{binding.current_work_item_id}_old_revision_1",
            policy.packet_sha256,
            public_url=public_url,
            number=1,
        ),
        _revision(
            binding.current_work_item_id,
            f"{binding.current_work_item_id}_old_revision_2",
            policy.judge_sha256,
            public_url=public_url,
            number=2,
        ),
    )
    current_state = ContentDraftRevisionState(
        status="unreviewed",
        latest_revision=current_revisions[-1],
        revision_count=len(current_revisions),
    )
    retained_revision = _revision(
        retained_work_item_id,
        binding.revision_id,
        binding.revision_digest,
        public_url=public_url,
        number=55,
    )
    retained_review = _review(retained_revision)
    retained_state = ContentDraftRevisionState(
        status="approved",
        latest_revision=retained_revision,
        latest_review=retained_review,
        revision_count=55,
    )
    return _RevisionFixture(
        current_revisions=current_revisions,
        current_state=current_state,
        retained_review=retained_review,
        retained_state=retained_state,
        current_workspace=_workspace(current_revisions[-1]),
    )


def _request_exact_bdo_workspace(
    monkeypatch: pytest.MonkeyPatch,
    *,
    binding: ContentProductionProtectedBindingPolicy,
    retained_work_item_id: str,
    revisions: _RevisionFixture,
) -> _RequestFixture:
    store = _RouteStore(
        projection=_exact_bdo_projection(),
        states={
            binding.current_work_item_id: revisions.current_state,
            retained_work_item_id: revisions.retained_state,
        },
    )
    factory_calls: list[object] = []
    snapshot_calls: list[tuple[str, object, ContentDraftRevisionState]] = []

    def store_factory() -> _RouteStore:
        factory_calls.append(store)
        return store

    def load_snapshot(
        work_item_id: str,
        *,
        store: object,
        revision_state: ContentDraftRevisionState,
    ) -> object:
        snapshot_calls.append((work_item_id, store, revision_state))
        journey = _operator_journey()
        return SimpleNamespace(
            current_step_id=journey.current_step_id,
            operator_steps=journey.steps,
            revision_workspace=SimpleNamespace(context_current=True),
            preflight=SimpleNamespace(
                item=ContentWorkItem(id=binding.current_work_item_id, topic="BDO")
            ),
        )

    def build_document(
        work_item_id: str,
        *,
        revision_state: ContentDraftRevisionState,
        **_kwargs: object,
    ) -> ContentDocumentWorkspace:
        assert work_item_id == binding.current_work_item_id
        assert revision_state is revisions.current_state
        return revisions.current_workspace

    monkeypatch.setattr(selected_workspace_router, "content_workflow_store", store_factory)
    monkeypatch.setattr(
        selected_workspace_router,
        "selected_workspace_snapshot_for_work_item_or_404",
        load_snapshot,
    )
    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        build_document,
    )
    app = FastAPI()
    router = APIRouter()
    register_content_selected_workspace_route(router)
    app.include_router(router)
    response = TestClient(app).get(
        f"/api/content/work-items/{binding.current_work_item_id}/selected-workspace"
    )
    return _RequestFixture(
        response=response,
        store=store,
        factory_calls=factory_calls,
        snapshot_calls=snapshot_calls,
    )


def _exact_bdo_projection() -> ContentProductionClassificationProjection:
    policy = WAVE0_PRODUCTION_ACCEPTANCE_POLICY
    binding = policy.protected_binding
    retained_work_item_id = binding.retained_work_item_id
    assert retained_work_item_id is not None
    assert len(binding.action_ids) == len(binding.draft_post_ids) == 1
    action_id = binding.action_ids[0]
    post_id = binding.draft_post_ids[0]
    audit_id = f"mutation_audit_{action_id}"
    public_url = f"{policy.public_origin}{binding.canonical_path}/"
    receipts = {receipt.name: receipt for receipt in policy.source_receipts}
    matched_receipt = receipts["matched_classification"]
    return ContentProductionClassificationProjection.model_validate(
        {
            "run_id": f"content_production_classification_{policy.packet_sha256[:24]}",
            "run_digest": policy.packet_sha256,
            "decision_set_digest": policy.decision_set_digest,
            "freshness": {
                "state": "fresh",
                "checked_at": AUDIT_TIME.isoformat(),
                "requires_refresh": False,
                "connector_ids": policy.freshness_connector_ids,
            },
            "row": {
                "canonical_path": binding.canonical_path,
                "public_url": public_url,
                "decision": "reuse",
                "generation_allowed": False,
                "current_work_item_id": binding.current_work_item_id,
                "retained_work_item_id": retained_work_item_id,
                "revision_id": binding.revision_id,
                "revision_digest": binding.revision_digest,
                "revision_approved": True,
                "revision_complete": True,
                "rationale_pl": "Użyj dokładnej zatwierdzonej rewizji bez regeneracji.",
                "next_step_pl": "Otwórz zachowany dokument do bezpiecznego przeglądu.",
                "blockers": [],
                "retained_binding": {
                    "binding_basis": "exact_normalized_path_with_retained_revision_state",
                    "current_inventory_work_item_id": binding.current_work_item_id,
                    "retained_work_item_id": retained_work_item_id,
                    "retained_revision_id": binding.revision_id,
                    "retained_revision_digest": binding.revision_digest,
                    "identity_reconciliation_status": binding.identity_status,
                    "verified_draft_action_ids": binding.action_ids,
                    "verified_draft_post_ids": binding.draft_post_ids,
                    "must_not_regenerate": True,
                },
                "verified_actions": [
                    {
                        "action_id": action_id,
                        "mutation_audit_id": audit_id,
                        "action_type": "content_dev_draft_create",
                        "status": "applied",
                        "bound_work_item_id": retained_work_item_id,
                        "bound_revision_id": binding.revision_id,
                        "bound_content_digest": binding.revision_digest,
                        "bound_final_canonical_url": public_url,
                        "adapter_reached": True,
                        "external_write_attempted": True,
                    }
                ],
                "verified_drafts": [
                    {
                        "action_id": action_id,
                        "apply_audit_id": audit_id,
                        "post_id": post_id,
                        "revision_id": binding.revision_id,
                        "revision_digest": binding.revision_digest,
                        "readback_content_digest": binding.revision_digest,
                        "state_class": "dev_draft_verified",
                        "wordpress_draft_status": "draft",
                        "readback_status": "verified",
                    }
                ],
                "primary_evidence_ids": [f"policy:{policy.policy_id}"],
                "source_connectors": policy.freshness_connector_ids,
                "lineage_evidence_ids": [],
                "source_receipt": {
                    "authoring_inventory_row_sha256": receipts["authoring_inventory"].sha256,
                    "canonical_ledger_row_sha256": receipts["canonical_ledger"].sha256,
                    "keep_eligibility_row_sha256": receipts["keep_eligibility"].sha256,
                    "state_journal_url_row_sha256": receipts["state_journal"].sha256,
                    "classification_artifact_reference": matched_receipt.reference,
                    "classification_file_sha256": matched_receipt.sha256,
                    "classification_row_sha256": policy.decision_set_digest,
                    "classification_source": "matched",
                    "classification_raw_artifact_retained": False,
                    "classification_retention_status": "external_ephemeral_receipt_only",
                    "source_pack_id": policy.policy_id,
                },
                "source_packet_row_digest": policy.decision_set_digest,
            },
        }
    )


def _revision(
    work_item_id: str,
    revision_id: str,
    digest: str,
    *,
    public_url: str,
    number: int,
) -> ContentDraftRevision:
    return ContentDraftRevision(
        revision_id=revision_id,
        work_item_id=work_item_id,
        revision_number=number,
        content_digest=digest,
        draft_package_id=f"draft_{revision_id}",
        draft_package_digest=WAVE0_PRODUCTION_ACCEPTANCE_POLICY.decision_set_digest,
        final_canonical_url=public_url,
        title="BDO",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres BDO",
                body_markdown="Zachowana treść BDO do dokładnego przeglądu.",
            )
        ],
        created_by="wilku",
        created_at=AUDIT_TIME,
    )


def _review(revision: ContentDraftRevision) -> ContentDraftRevisionReview:
    return ContentDraftRevisionReview(
        decision_id=f"review_{revision.revision_id}",
        decision_number=1,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision="approved",
        reviewed_by="wilku",
        checked_items=["Treść i źródła"],
        evidence_ids=[WAVE0_PRODUCTION_ACCEPTANCE_POLICY.policy_id],
        created_at=AUDIT_TIME,
    )


def _workspace(revision: ContentDraftRevision) -> ContentDocumentWorkspace:
    return ContentDocumentWorkspace(
        work_item_id=revision.work_item_id,
        work_kind="refresh_existing",
        source_snapshot=ContentDocumentWorkspaceSourceSnapshot(
            status="unavailable",
            status_label="materiał niedostępny",
            reason="Publiczny test nie odczytuje WordPressa.",
        ),
        canonical_document=ContentDocumentWorkspaceDocument(
            status="unreviewed",
            revision_id=revision.revision_id,
            content_digest=revision.content_digest,
            review_state="unreviewed",
            label="Bieżąca stara rewizja",
            reason="Bieżąca tożsamość zachowuje własny dokument.",
            revision=revision,
        ),
        document_lineage=ContentDocumentWorkspaceDocumentLineage(
            status="not_recorded",
            reason="Brak lineage dla starej bieżącej rewizji.",
        ),
        comparison=ContentDocumentWorkspaceComparison(
            status="unavailable",
            reason="Brak porównania w kontrakcie HTTP.",
        ),
        next_action=ContentDocumentWorkspaceNextAction(
            kind="prepare_document",
            label="Przygotuj nową wersję",
            reason="Ten krok ma zostać wyłączony przez decyzję reuse.",
        ),
    )


def _operator_journey() -> ContentWorkflowOperatorJourney:
    return build_content_workflow_operator_journey(
        ContentWorkflowOperatorFacts(
            sales_brief_present=True,
            sales_brief_signal_status="strong",
            sales_brief_signal_reason="Zakres ma wystarczające źródła.",
            sales_brief_safe_next_step="Przejdź do planu sekcji.",
            sales_brief_blocker=None,
            section_map_present=True,
            section_map_blocker=None,
            section_map_safe_next_step="Przejdź do szkicu.",
            structured_contract_present=True,
            structured_contract_blocker=None,
            structured_contract_safe_next_step="Sprawdź szkic.",
            revision_workspace_status="unreviewed",
        )
    )
