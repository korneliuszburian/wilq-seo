from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import APIRouter, FastAPI
from pydantic import TypeAdapter, ValidationError

import apps.api.wilq_api.routers.content_selected_workspace as selected_workspace_router
import wilq.content.workflow.workspace.selected_workspace as selected_workspace_module
from apps.api.wilq_api.routers.content_selected_workspace import (
    register_content_selected_workspace_route,
)
from tests.content.production_classification_synthetic import (
    REVISION_DIGEST,
    REVISION_ID,
    build_inputs,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    ContentProductionClassificationRow,
    parse_content_production_classification,
    project_content_production_classification,
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
from wilq.content.workflow.workspace.production_decision import (
    ContentProductionDecision,
    ContentProductionDecisionBlocker,
    ContentProductionDecisionMissing,
    ContentProductionDecisionNonReuse,
    ContentProductionDecisionReuse,
    ContentReusableDocumentBlocked,
    ContentReusableDocumentReady,
    build_content_production_decision,
)

AUDIT_TIME = datetime(2026, 8, 30, 10, 5, tzinfo=UTC)
CURRENT_ID = "work_current_1"
RETAINED_ID = "work_retained"
HISTORICAL_ID = "work_historical"


@pytest.mark.parametrize(
    ("alias_kind", "requested_work_item_id", "lookup_basis"),
    [
        ("current", CURRENT_ID, "current"),
        ("retained", RETAINED_ID, "retained"),
        ("historical", HISTORICAL_ID, "historical_action_owner"),
    ],
)
def test_reuse_route_canonicalizes_alias_and_keeps_retained_document_separate(
    alias_kind: str,
    requested_work_item_id: str,
    lookup_basis: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection = _reuse_projection(retained_missing=alias_kind == "historical")
    revision_owner = HISTORICAL_ID if alias_kind == "historical" else RETAINED_ID
    current_state = ContentDraftRevisionState(
        status="unreviewed",
        latest_revision=_revision(CURRENT_ID, "current_revision_2", "c" * 64, number=2),
        revision_count=2,
    )
    retained_revision = _revision(revision_owner, REVISION_ID, REVISION_DIGEST)
    retained_review = _review(retained_revision)
    retained_state = ContentDraftRevisionState(
        status="approved",
        latest_revision=retained_revision,
        latest_review=retained_review,
        revision_count=1,
    )
    current_workspace = _workspace(current_state.latest_revision)
    store = _RouteStore(
        projection=projection,
        states={CURRENT_ID: current_state, revision_owner: retained_state},
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
            preflight=SimpleNamespace(item=ContentWorkItem(id=CURRENT_ID, topic="BDO")),
        )

    def build_document(
        work_item_id: str,
        *,
        revision_state: ContentDraftRevisionState,
        **_kwargs: object,
    ) -> ContentDocumentWorkspace:
        assert work_item_id == CURRENT_ID
        assert revision_state is current_state
        return current_workspace

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

    result = _selected_endpoint()(requested_work_item_id)

    assert factory_calls == [store]
    assert store.classification_calls == [requested_work_item_id]
    assert store.revision_calls == [CURRENT_ID, revision_owner]
    assert snapshot_calls == [(CURRENT_ID, store, current_state)]
    _assert_reuse_route_result(
        result,
        requested_work_item_id=requested_work_item_id,
        lookup_basis=lookup_basis,
        revision_owner=revision_owner,
        projection=projection,
        current_workspace=current_workspace,
        retained_revision=retained_revision,
        retained_review=retained_review,
    )


def _assert_reuse_route_result(
    result: selected_workspace_module.ContentSelectedWorkspace,
    *,
    requested_work_item_id: str,
    lookup_basis: str,
    revision_owner: str,
    projection: ContentProductionClassificationProjection,
    current_workspace: ContentDocumentWorkspace,
    retained_revision: ContentDraftRevision,
    retained_review: ContentDraftRevisionReview,
) -> None:
    assert result.work_item_id == CURRENT_ID
    assert result.requested_work_item_id == requested_work_item_id
    assert result.workspace is not None
    assert result.workspace.work_item_id == CURRENT_ID
    assert result.workspace.canonical_document == current_workspace.canonical_document
    assert result.workspace.canonical_document.revision_id == "current_revision_2"
    assert result.workspace.next_action.kind == "none"
    assert result.workspace.next_action.reason == projection.row.rationale_pl
    assert result.reason == projection.row.rationale_pl
    assert result.safe_next_step == projection.row.next_step_pl
    decision = cast(ContentProductionDecisionReuse, result.production_decision)
    assert decision.status == "available"
    assert decision.decision == "reuse"
    assert decision.lookup_basis == lookup_basis
    assert decision.generation_allowed is False
    assert decision.run_id == projection.run_id
    assert decision.run_digest == projection.run_digest
    assert decision.decision_set_digest == projection.decision_set_digest
    assert decision.revision_binding.current_work_item_id == CURRENT_ID
    assert decision.revision_binding.retained_work_item_id == projection.row.retained_work_item_id
    assert decision.revision_binding.revision_work_item_id == revision_owner
    assert decision.revision_binding.revision_id == REVISION_ID
    assert decision.revision_binding.revision_digest == REVISION_DIGEST
    assert decision.revision_binding.must_not_regenerate is True
    reusable = cast(ContentReusableDocumentReady, decision.reusable_document)
    assert reusable.status == "ready"
    assert reusable.revision is retained_revision
    assert reusable.review is retained_review
    assert reusable.review.decision == "approved"
    assert reusable.review.revision_digest == reusable.revision.content_digest == REVISION_DIGEST

    decision_payload = decision.model_dump(mode="json")
    assert {
        "source_receipt",
        "source_packet_row_digest",
        "verified_actions",
        "verified_drafts",
        "lineage_defects",
    }.isdisjoint(decision_payload)
    serialized = json.dumps(decision_payload)
    assert "mutation_audit_id" not in serialized
    assert "apply_audit_id" not in serialized
    assert "readback_content_digest" not in serialized


@pytest.mark.parametrize(
    ("state_kind", "expected_code"),
    [
        ("missing_revision", "latest_revision_missing"),
        ("drifted_revision", "latest_revision_drift"),
        ("missing_review", "latest_review_missing"),
        ("non_approved_review", "latest_review_not_approved"),
        ("mismatched_review", "latest_review_mismatch"),
    ],
)
def test_reuse_revision_or_review_drift_blocks_without_generation_fallback(
    state_kind: str,
    expected_code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection = _reuse_projection()
    state = _retained_state_for_case(state_kind)
    production = build_content_production_decision(
        CURRENT_ID,
        classification=projection,
        retained_revision_state=state,
    )

    assert isinstance(production, ContentProductionDecisionReuse)
    reusable = production.reusable_document
    assert isinstance(reusable, ContentReusableDocumentBlocked)
    assert reusable.code == expected_code
    assert production.generation_allowed is False

    current_revision = _revision(CURRENT_ID, "current_revision_2", "c" * 64, number=2)
    workspace = _workspace(current_revision)
    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _work_item_id, **_kwargs: workspace,
    )
    selected = selected_workspace_module.build_content_selected_workspace(
        CURRENT_ID,
        requested_work_item_id=CURRENT_ID,
        production_decision=production,
        operator_journey=_operator_journey(),
    )

    assert selected.workspace is not None
    assert selected.workspace.canonical_document.revision is current_revision
    assert selected.workspace.next_action.kind == "none"
    assert selected.workspace.next_action.reason == reusable.reason_pl
    assert selected.reason == reusable.reason_pl
    assert selected.safe_next_step == reusable.safe_next_step_pl


def test_retained_missing_without_one_historical_owner_is_explicitly_blocked() -> None:
    projection = _reuse_projection(retained_missing=True, omit_historical_owner=True)

    production = build_content_production_decision(
        CURRENT_ID,
        classification=projection,
    )

    assert isinstance(production, ContentProductionDecisionReuse)
    assert production.revision_binding.revision_work_item_id is None
    assert isinstance(production.reusable_document, ContentReusableDocumentBlocked)
    assert production.reusable_document.code == "missing_revision_owner"


@pytest.mark.parametrize("decision_name", ["refresh", "blocked"])
def test_non_reuse_projects_typed_blockers_without_retained_data(decision_name: str) -> None:
    projection = _non_reuse_projection(decision_name)

    production = build_content_production_decision(
        projection.row.current_work_item_id or "missing",
        classification=projection,
    )

    assert isinstance(production, ContentProductionDecisionNonReuse)
    assert production.decision == decision_name
    assert production.generation_allowed is False
    assert production.blockers
    assert production.blockers[0].code == "invalid_legacy_evidence_id"
    assert production.blockers[0].blocks_initial_generation is True
    assert "revision_binding" not in production.model_dump()
    assert "reusable_document" not in production.model_dump()
    invalid_url = production.model_dump(mode="json")
    invalid_url["public_url"] = "/relative-only"
    with pytest.raises(ValidationError):
        ContentProductionDecisionNonReuse.model_validate(invalid_url)


@pytest.mark.parametrize("decision_name", ["refresh", "blocked"])
def test_refresh_and_blocked_decisions_reject_empty_source_blockers(
    decision_name: str,
) -> None:
    projection = _non_reuse_projection(decision_name)
    row = projection.row.model_copy(update={"blockers": ()})
    without_blockers = projection.model_copy(update={"row": row})

    with pytest.raises(ValidationError):
        build_content_production_decision(
            row.current_work_item_id or "missing",
            classification=without_blockers,
        )


def test_production_decision_requires_explicit_discriminants_and_arrays() -> None:
    decision = _valid_reuse_decision()
    valid_payload = decision.model_dump(mode="python")
    required_paths = (
        ("status",),
        ("decision",),
        ("current_work_item_id",),
        ("retained_work_item_id",),
        ("blockers",),
        ("primary_evidence_ids",),
        ("lineage_evidence_ids",),
        ("source_connectors",),
        ("freshness", "connector_ids"),
        ("revision_binding", "retained_work_item_id"),
        ("revision_binding", "revision_work_item_id"),
        ("revision_binding", "verified_draft_action_ids"),
        ("revision_binding", "verified_draft_post_ids"),
        ("reusable_document", "status"),
    )

    for path in required_paths:
        payload = deepcopy(valid_payload)
        _remove_path(payload, path)
        with pytest.raises(ValidationError):
            ContentProductionDecisionReuse.model_validate(payload)

    with pytest.raises(ValidationError):
        ContentProductionDecisionMissing.model_validate({})
    with pytest.raises(ValidationError):
        ContentReusableDocumentBlocked.model_validate(
            {
                "code": "latest_revision_missing",
                "reason_pl": "Brakuje rewizji.",
                "safe_next_step_pl": "Sprawdź rewizję.",
            }
        )


def test_production_decision_rejects_blank_optional_ids_and_string_members() -> None:
    valid_payload = _valid_reuse_decision().model_dump(mode="python")
    invalid_values = (
        (("current_work_item_id",), ""),
        (("retained_work_item_id",), ""),
        (("revision_binding", "retained_work_item_id"), ""),
        (("revision_binding", "revision_work_item_id"), ""),
        (("revision_binding", "verified_draft_action_ids"), ("",)),
        (("revision_binding", "verified_draft_post_ids"), ("",)),
        (("primary_evidence_ids",), ("",)),
        (("lineage_evidence_ids",), ("",)),
        (("source_connectors",), ("",)),
    )

    for path, value in invalid_values:
        payload = deepcopy(valid_payload)
        _replace_path(payload, path, value)
        with pytest.raises(ValidationError):
            ContentProductionDecisionReuse.model_validate(payload)

    blocker = ContentProductionDecisionBlocker(
        code="evidence_refresh_required",
        owner="wilku",
        next_step_pl="Odśwież źródła.",
        sources=("gsc",),
        blocks_initial_generation=True,
    ).model_dump(mode="python")
    blocker["sources"] = ("",)
    with pytest.raises(ValidationError):
        ContentProductionDecisionBlocker.model_validate(blocker)


def test_production_decision_outer_any_of_keeps_valid_openapi_and_status_acceptance() -> None:
    app = FastAPI()
    router = APIRouter()
    register_content_selected_workspace_route(router)
    app.include_router(router)

    openapi = app.openapi()
    json.dumps(openapi, allow_nan=False)
    decision_schema = openapi["components"]["schemas"]["ContentSelectedWorkspace"]["properties"][
        "production_decision"
    ]
    assert "anyOf" in decision_schema
    assert "discriminator" not in decision_schema
    available_schema = decision_schema["anyOf"][1]
    assert available_schema["discriminator"]["mapping"] == {
        "blocked": "#/components/schemas/ContentProductionDecisionBlocked",
        "refresh": "#/components/schemas/ContentProductionDecisionRefresh",
        "reuse": "#/components/schemas/ContentProductionDecisionReuse",
        "write": "#/components/schemas/ContentProductionDecisionWrite",
    }
    schemas = openapi["components"]["schemas"]
    assert schemas["ContentProductionDecisionRefresh"]["properties"]["blockers"]["minItems"] == 1
    assert schemas["ContentProductionDecisionBlocked"]["properties"]["blockers"]["minItems"] == 1
    assert "minItems" not in schemas["ContentProductionDecisionWrite"]["properties"]["blockers"]

    adapter = TypeAdapter(ContentProductionDecision)
    missing = adapter.validate_python({"status": "missing"})
    available = adapter.validate_python(_valid_reuse_decision().model_dump(mode="python"))
    assert isinstance(missing, ContentProductionDecisionMissing)
    assert isinstance(available, ContentProductionDecisionReuse)


def test_missing_classification_preserves_existing_workspace_action_and_safe_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(None)
    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _work_item_id, **_kwargs: workspace,
    )

    selected = selected_workspace_module.build_content_selected_workspace(
        CURRENT_ID,
        operator_journey=_operator_journey(),
    )

    assert selected.production_decision.status == "missing"
    assert selected.requested_work_item_id == selected.work_item_id == CURRENT_ID
    assert selected.workspace is workspace
    assert selected.workspace.next_action.kind == "prepare_document"
    assert selected.safe_next_step == workspace.next_action.label


def test_selected_workspace_rejects_mismatched_production_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection = _reuse_projection()
    revision = _revision(RETAINED_ID, REVISION_ID, REVISION_DIGEST)
    production = build_content_production_decision(
        CURRENT_ID,
        classification=projection,
        retained_revision_state=ContentDraftRevisionState(
            status="approved",
            latest_revision=revision,
            latest_review=_review(revision),
            revision_count=1,
        ),
    )
    workspace = _workspace(None)
    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _work_item_id, **_kwargs: workspace,
    )
    selected = selected_workspace_module.build_content_selected_workspace(
        CURRENT_ID,
        requested_work_item_id=CURRENT_ID,
        production_decision=production,
        operator_journey=_operator_journey(),
    )
    mismatched = selected.model_dump(mode="json")
    mismatched["requested_work_item_id"] = "unrelated_work_item"

    with pytest.raises(ValidationError, match="lookup basis"):
        selected_workspace_module.ContentSelectedWorkspace.model_validate(mismatched)

    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _work_item_id, **_kwargs: _workspace(revision),
    )
    with pytest.raises(ValidationError, match="Current canonical document"):
        selected_workspace_module.build_content_selected_workspace(
            CURRENT_ID,
            requested_work_item_id=CURRENT_ID,
            production_decision=production,
            operator_journey=_operator_journey(),
        )


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


def _selected_endpoint() -> object:
    router = APIRouter()
    register_content_selected_workspace_route(router)
    return next(
        route.endpoint
        for route in router.routes
        if getattr(route, "path", "").endswith("/selected-workspace")
    )


def _valid_reuse_decision() -> ContentProductionDecisionReuse:
    revision = _revision(RETAINED_ID, REVISION_ID, REVISION_DIGEST)
    decision = build_content_production_decision(
        CURRENT_ID,
        classification=_reuse_projection(),
        retained_revision_state=ContentDraftRevisionState(
            status="approved",
            latest_revision=revision,
            latest_review=_review(revision),
            revision_count=1,
        ),
    )
    assert isinstance(decision, ContentProductionDecisionReuse)
    return decision


def _remove_path(payload: dict[str, object], path: tuple[str, ...]) -> None:
    target = _nested_payload(payload, path)
    target.pop(path[-1])


def _replace_path(
    payload: dict[str, object],
    path: tuple[str, ...],
    value: object,
) -> None:
    target = _nested_payload(payload, path)
    target[path[-1]] = value


def _nested_payload(
    payload: dict[str, object],
    path: tuple[str, ...],
) -> dict[str, object]:
    target = payload
    for key in path[:-1]:
        nested = target[key]
        assert isinstance(nested, dict)
        target = nested
    return target


def _reuse_projection(
    *,
    retained_missing: bool = False,
    omit_historical_owner: bool = False,
) -> ContentProductionClassificationProjection:
    run = _classification_run()
    row = run.rows[0]
    if not retained_missing:
        return project_content_production_classification(run, row)
    payload = row.model_dump(mode="json")
    payload["retained_work_item_id"] = None
    binding = cast(dict[str, object], payload["retained_binding"])
    binding["retained_work_item_id"] = None
    binding["identity_reconciliation_status"] = "retained_missing"
    actions = cast(list[dict[str, object]], payload["verified_actions"])
    drafts = cast(list[dict[str, object]], payload["verified_drafts"])
    if omit_historical_owner:
        actions.clear()
        drafts.clear()
        binding["verified_draft_action_ids"] = []
        binding["verified_draft_post_ids"] = []
    else:
        actions[0]["bound_work_item_id"] = HISTORICAL_ID
    retained_missing_row = ContentProductionClassificationRow.model_validate(payload)
    return project_content_production_classification(run, retained_missing_row)


def _non_reuse_projection(decision: str) -> ContentProductionClassificationProjection:
    run = _classification_run()
    payload = run.rows[1].model_dump(mode="json")
    payload["decision"] = decision
    row = ContentProductionClassificationRow.model_validate(payload)
    return project_content_production_classification(run, row)


def _classification_run():
    inputs = build_inputs()
    return parse_content_production_classification(
        packet_bytes=inputs.packet_bytes,
        judge_bytes=inputs.judge_bytes,
        acceptance_policy=inputs.policy,
        recorded_by="codex_w2_test",
        reviewed_by="independent_w2_test",
        recorded_at=AUDIT_TIME,
    )


def _retained_state_for_case(state_kind: str) -> ContentDraftRevisionState:
    if state_kind == "missing_revision":
        return ContentDraftRevisionState(status="empty", revision_count=0)
    revision = _revision(RETAINED_ID, REVISION_ID, REVISION_DIGEST)
    if state_kind == "drifted_revision":
        return ContentDraftRevisionState(
            status="unreviewed",
            latest_revision=_revision(RETAINED_ID, "later_revision", "8" * 64, number=2),
            revision_count=2,
        )
    if state_kind == "missing_review":
        return ContentDraftRevisionState(
            status="unreviewed",
            latest_revision=revision,
            revision_count=1,
        )
    if state_kind == "non_approved_review":
        review = _review(revision, decision="needs_changes")
        return ContentDraftRevisionState(
            status="needs_changes",
            latest_revision=revision,
            latest_review=review,
            revision_count=1,
        )
    mismatched_review = _review(revision).model_copy(update={"work_item_id": "wrong_owner"})
    return ContentDraftRevisionState.model_construct(
        status="approved",
        latest_revision=revision,
        latest_review=mismatched_review,
        revision_count=1,
    )


def _revision(
    work_item_id: str,
    revision_id: str,
    digest: str,
    *,
    number: int = 1,
) -> ContentDraftRevision:
    return ContentDraftRevision(
        revision_id=revision_id,
        work_item_id=work_item_id,
        revision_number=number,
        content_digest=digest,
        draft_package_id=f"draft_{revision_id}",
        draft_package_digest="d" * 64,
        final_canonical_url="https://www.ekologus.pl/bdo-test/",
        title="BDO",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres",
                body_markdown="Sprawdź zakres obowiązków.",
            )
        ],
        created_by="wilku",
        created_at=AUDIT_TIME,
    )


def _review(
    revision: ContentDraftRevision,
    *,
    decision: str = "approved",
) -> ContentDraftRevisionReview:
    return ContentDraftRevisionReview(
        decision_id=f"review_{revision.revision_id}",
        decision_number=1,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision=decision,
        reviewed_by="wilku",
        notes="Wymaga korekty." if decision != "approved" else "",
        checked_items=["Treść i źródła"],
        evidence_ids=["ev_review_bdo"],
        created_at=AUDIT_TIME,
    )


def _workspace(revision: ContentDraftRevision | None) -> ContentDocumentWorkspace:
    document = (
        ContentDocumentWorkspaceDocument(
            status="not_created",
            label="Brak dokumentu",
            reason="Nie zapisano bieżącej rewizji.",
        )
        if revision is None
        else ContentDocumentWorkspaceDocument(
            status="unreviewed",
            revision_id=revision.revision_id,
            content_digest=revision.content_digest,
            review_state="unreviewed",
            label="Bieżąca wersja czeka na review",
            reason="To jest bieżący dokument obecnej tożsamości.",
            revision=revision,
        )
    )
    return ContentDocumentWorkspace(
        work_item_id=CURRENT_ID,
        work_kind="refresh_existing",
        source_snapshot=ContentDocumentWorkspaceSourceSnapshot(
            status="unavailable",
            status_label="materiał niedostępny",
            reason="Brak materiału w teście.",
        ),
        canonical_document=document,
        document_lineage=ContentDocumentWorkspaceDocumentLineage(
            status="not_recorded",
            reason="Brak lineage w teście.",
        ),
        comparison=ContentDocumentWorkspaceComparison(
            status="unavailable",
            reason="Brak porównania w teście.",
        ),
        next_action=ContentDocumentWorkspaceNextAction(
            kind="prepare_document",
            label="Przygotuj nową wersję",
            reason="Stary następny krok workspace.",
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
