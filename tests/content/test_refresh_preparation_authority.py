from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import wilq.content.workflow.decisions.production as production_module
import wilq.content.workflow.refresh_preparation_operations as refresh_operations
import wilq.content.workflow.refresh_preparation_resolution as refresh_resolution
from apps.api.wilq_api.routers.content_refresh_preparation import (
    register_content_refresh_preparation_routes,
)
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftRequest,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalRequest,
)
from wilq.content.planning.input_sources import (
    PLANNING_SOURCE_NAMES,
    ContentPlanningSourceAssessment,
)
from wilq.content.planning.input_summary import ContentPlanningInputSummary
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    classification_counts,
)
from wilq.content.workflow.refresh_preparation import (
    ContentRefreshPreparationAuthority,
    RefreshPreparationRuntimeAuthorized,
    RefreshPreparationRuntimeBlocked,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationAuthorizationRecordResult,
    ContentRefreshPreparationAuthorizationRequest,
    ContentRefreshPreparationBlocked,
    ContentRefreshPreparationClassificationBinding,
    ContentRefreshPreparationReadyToAuthorize,
    build_content_refresh_preparation_authorization,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas.core import utc_now

WORK_ITEM_ID = "content_work_item_refresh"
SERVICE_CARD_ID = "ekologus_service_operat_wodnoprawny"
RUN_DIGEST = "a" * 64
DECISION_DIGEST = "b" * 64
ROW_DIGEST = "c" * 64
INPUT_DIGEST = "d" * 64


@dataclass
class _FakeStore:
    run: object | None
    authorizations: dict[str, ContentRefreshPreparationAuthorization] = field(default_factory=dict)
    record_calls: int = 0

    def load_latest_production_classification(self) -> object | None:
        return self.run

    def record_refresh_preparation_authorization(
        self, authorization: ContentRefreshPreparationAuthorization
    ) -> ContentRefreshPreparationAuthorizationRecordResult:
        self.record_calls += 1
        existing = next(
            (
                item
                for item in self.authorizations.values()
                if _same_authorization_context(item, authorization)
            ),
            None,
        )
        if existing is not None:
            return ContentRefreshPreparationAuthorizationRecordResult(
                status=(
                    "idempotent"
                    if existing.authorization_digest == authorization.authorization_digest
                    else "conflict"
                ),
                authorization=existing,
            )
        self.authorizations[authorization.authorization_id] = authorization
        return ContentRefreshPreparationAuthorizationRecordResult(
            status="created", authorization=authorization
        )

    def load_refresh_preparation_authorization(
        self, authorization_id: str
    ) -> ContentRefreshPreparationAuthorization | None:
        return self.authorizations.get(authorization_id)

    def find_refresh_preparation_authorization(
        self, **context: str
    ) -> ContentRefreshPreparationAuthorization | None:
        return next(
            (
                authorization
                for authorization in self.authorizations.values()
                if all(getattr(authorization, field) == value for field, value in context.items())
            ),
            None,
        )


@dataclass
class _FakeProposalStore:
    proposal: object | None = None

    def latest(self, _work_item_id: str) -> object | None:
        return self.proposal


def _authority(
    monkeypatch: pytest.MonkeyPatch,
    *,
    run: object | None = None,
    candidate_status: str = "approved_current",
    with_sources: bool = True,
    with_source_material: bool = True,
    input_blockers: list[object] | None = None,
    planning_input_updates: dict[str, object] | None = None,
    proposal: object | None = None,
) -> tuple[ContentRefreshPreparationAuthority, _FakeStore, list[tuple[str, str | None]], object]:
    row = SimpleNamespace(
        current_work_item_id=WORK_ITEM_ID,
        decision="refresh",
        canonical_path="/analiza-pozwolen-zintegrowanych",
        public_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        source_packet_row_digest=ROW_DIGEST,
        blockers=(SimpleNamespace(code="lineage_needs_review"),),
        next_step_pl="Sprawdź źródła.",
    )
    effective_run = run if run is not None else _run(row=row)
    store = _FakeStore(run=effective_run)
    calls: list[tuple[str, str | None]] = []
    selected_snapshot = _snapshot(
        candidate_status=candidate_status,
        with_sources=with_sources,
        with_source_material=with_source_material,
    )
    baseline_snapshot = _snapshot(
        candidate_status=candidate_status,
        with_sources=with_sources,
        with_source_material=with_source_material,
        selected=False,
    )

    def snapshot_loader(work_item_id: str, service_card_id: str | None) -> object:
        calls.append((work_item_id, service_card_id))
        assert work_item_id == WORK_ITEM_ID
        return selected_snapshot if service_card_id == SERVICE_CARD_ID else baseline_snapshot

    planning_input_values: dict[str, object] = {
        "work_item_id": WORK_ITEM_ID,
        "planning_input_digest": INPUT_DIGEST,
        "confirmed_service_card_id": SERVICE_CARD_ID,
        "final_canonical_url": "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
    }
    planning_input_values.update(planning_input_updates or {})
    planning_input = SimpleNamespace(
        **planning_input_values,
    )
    build_result = SimpleNamespace(planning_input=planning_input, blockers=input_blockers or [])
    monkeypatch.setattr(
        refresh_resolution,
        "build_content_planning_input",
        lambda *_args, **_kwargs: build_result,
    )
    monkeypatch.setattr(
        refresh_resolution,
        "planning_generation_blockers",
        lambda blockers: blockers,
    )
    monkeypatch.setattr(
        refresh_operations,
        "content_planning_input_summary",
        lambda _input: _summary(),
    )
    monkeypatch.setattr(
        refresh_resolution,
        "content_planning_input_summary",
        lambda _input: _summary(),
    )
    authority = ContentRefreshPreparationAuthority(
        store=store,
        snapshot_loader=snapshot_loader,
        proposal_store=_FakeProposalStore(proposal=proposal),  # type: ignore[arg-type]
    )
    return authority, store, calls, selected_snapshot


def test_preview_rebuilds_the_selected_snapshot_without_writing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority, store, calls, selected_snapshot = _authority(monkeypatch)

    selection = authority.preview(WORK_ITEM_ID, service_card_id=None)
    ready = authority.preview(WORK_ITEM_ID, service_card_id=SERVICE_CARD_ID)

    assert selection.status == "selection_required"
    assert isinstance(ready, ContentRefreshPreparationReadyToAuthorize)
    assert ready.planning_input_digest == INPUT_DIGEST
    assert ready.service_candidate.service_card_id == SERVICE_CARD_ID
    assert ready.service_candidate.evidence_ids == ["ev_service"]
    assert store.record_calls == 0
    assert calls[0] == (WORK_ITEM_ID, None)
    assert (WORK_ITEM_ID, SERVICE_CARD_ID) in calls
    assert selected_snapshot.service_profile_context.service_selection_confirmed is True


def test_authorization_is_idempotent_and_acknowledges_the_exact_blocker_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority, store, _calls, _snapshot = _authority(monkeypatch)
    ready = authority.preview(WORK_ITEM_ID, service_card_id=SERVICE_CARD_ID)
    assert isinstance(ready, ContentRefreshPreparationReadyToAuthorize)
    request = _authorization_request(ready)

    created = authority.authorize(WORK_ITEM_ID, request)
    repeated = authority.authorize(WORK_ITEM_ID, request)
    wrong_ack = authority.authorize(
        WORK_ITEM_ID,
        request.model_copy(update={"acknowledged_classification_blocker_codes": []}),
    )
    competing = authority.authorize(
        WORK_ITEM_ID,
        request.model_copy(update={"authorized_by": "inna_osoba"}),
    )

    assert created.status == "created"
    assert repeated.status == "idempotent"
    assert wrong_ack.status == "conflict"
    assert wrong_ack.blockers[0].code == "refresh_preparation_acknowledgement_mismatch"
    assert competing.status == "conflict"
    assert competing.blockers[0].code == "refresh_preparation_authorization_conflict"
    assert store.record_calls == 3
    assert len(store.authorizations) == 1


@pytest.mark.parametrize(
    ("kind", "expected_status", "expected_code"),
    [
        ("alias", "blocked", "refresh_preparation_alias_not_current"),
        ("write", "blocked", "refresh_preparation_decision_not_refresh"),
        ("stale", "stale", "stale_production_classification"),
    ],
)
def test_preview_rejects_alias_nonrefresh_and_stale_classifications(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    expected_status: str,
    expected_code: str,
) -> None:
    run = _run(
        alias=kind == "alias",
        decision="write" if kind == "write" else "refresh",
        stale=kind == "stale",
    )
    authority, store, calls, _snapshot = _authority(monkeypatch, run=run)

    preview = authority.preview(WORK_ITEM_ID, service_card_id=SERVICE_CARD_ID)

    assert preview.status == expected_status
    assert preview.blockers[0].code == expected_code
    assert store.record_calls == 0
    assert calls == []


@pytest.mark.parametrize(
    ("candidate_status", "with_sources", "input_blockers", "expected_code"),
    [
        (
            "source_backed_review_required",
            True,
            None,
            "refresh_preparation_service_sources_missing",
        ),
        ("approved_current", False, None, "refresh_preparation_service_sources_missing"),
        (
            "approved_current",
            True,
            [
                SimpleNamespace(
                    code="missing_wordpress_full_inventory",
                    label="Brakuje inventory",
                    reason="Nie ma pełnego materiału.",
                    next_step="Uzupełnij inventory.",
                )
            ],
            "refresh_preparation_input_blocked",
        ),
    ],
)
def test_preview_rejects_service_and_input_failures(
    monkeypatch: pytest.MonkeyPatch,
    candidate_status: str,
    with_sources: bool,
    input_blockers: list[object] | None,
    expected_code: str,
) -> None:
    authority, store, _calls, _snapshot = _authority(
        monkeypatch,
        candidate_status=candidate_status,
        with_sources=with_sources,
        input_blockers=input_blockers,
    )

    preview = authority.preview(WORK_ITEM_ID, service_card_id=SERVICE_CARD_ID)

    assert isinstance(preview, ContentRefreshPreparationBlocked)
    assert preview.blockers[0].code == expected_code
    assert store.record_calls == 0


def test_approved_service_fact_without_optional_source_material_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority, _store, _calls, _snapshot = _authority(
        monkeypatch,
        with_sources=True,
        with_source_material=False,
    )

    preview = authority.preview(WORK_ITEM_ID, service_card_id=SERVICE_CARD_ID)

    assert isinstance(preview, ContentRefreshPreparationReadyToAuthorize)
    assert preview.service_candidate.source_fact_ids == ["source_fact_operat"]
    assert preview.service_candidate.source_material_ids == []


def test_runtime_requires_exact_authorization_and_proposal_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority, _store, _calls, _snapshot = _authority(monkeypatch)
    preview = authority.preview(WORK_ITEM_ID, service_card_id=SERVICE_CARD_ID)
    assert isinstance(preview, ContentRefreshPreparationReadyToAuthorize)
    receipt = authority.authorize(WORK_ITEM_ID, _authorization_request(preview)).authorization
    assert receipt is not None
    planning_request = ContentPlanningProposalRequest(
        service_card_id=SERVICE_CARD_ID,
        expected_planning_input_digest=INPUT_DIGEST,
        requested_by="wilku",
        refresh_preparation_authorization_id=receipt.authorization_id,
        expected_refresh_preparation_authorization_digest=receipt.authorization_digest,
    )

    authorized = authority.resolve_planning(WORK_ITEM_ID, planning_request)
    no_auth = authority.resolve_planning(
        WORK_ITEM_ID,
        planning_request.model_copy(
            update={
                "refresh_preparation_authorization_id": None,
                "expected_refresh_preparation_authorization_digest": None,
            }
        ),
    )
    stale_input = authority.resolve_planning(
        WORK_ITEM_ID,
        planning_request.model_copy(update={"expected_planning_input_digest": "e" * 64}),
    )

    assert isinstance(authorized, RefreshPreparationRuntimeAuthorized)
    assert isinstance(no_auth, RefreshPreparationRuntimeBlocked)
    assert no_auth.blocker.code == "refresh_preparation_authorization_missing"
    assert isinstance(stale_input, RefreshPreparationRuntimeBlocked)
    assert stale_input.blocker.code == "refresh_preparation_authorization_input_mismatch"


def test_initial_draft_rejects_a_proposal_with_drifted_full_refresh_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority, _store, _calls, _snapshot = _authority(monkeypatch)
    preview = authority.preview(WORK_ITEM_ID, service_card_id=SERVICE_CARD_ID)
    assert isinstance(preview, ContentRefreshPreparationReadyToAuthorize)
    receipt = authority.authorize(WORK_ITEM_ID, _authorization_request(preview)).authorization
    assert receipt is not None
    proposal = SimpleNamespace(
        generation_status="codex_generated",
        proposal_id="content_planning_proposal_test",
        planning_digest="e" * 64,
        planning_input_digest=INPUT_DIGEST,
        service_card_id=SERVICE_CARD_ID,
        refresh_preparation_binding=receipt.binding.model_copy(
            update={"source_packet_row_digest": "f" * 64}
        ),
    )
    authority._proposal_store.proposal = proposal  # noqa: SLF001 -- isolated authority fake.
    request = ContentInitialDraftRequest(
        expected_proposal_id=proposal.proposal_id,
        expected_planning_digest=proposal.planning_digest,
        expected_planning_input_digest=INPUT_DIGEST,
        requested_by="wilku",
        refresh_preparation_authorization_id=receipt.authorization_id,
        expected_refresh_preparation_authorization_digest=receipt.authorization_digest,
    )

    resolution = authority.resolve_initial_draft(WORK_ITEM_ID, request)

    assert isinstance(resolution, RefreshPreparationRuntimeBlocked)
    assert resolution.blocker.code == "refresh_preparation_proposal_binding_mismatch"


def test_authorization_pair_cannot_downgrade_an_unclassified_legacy_request() -> None:
    authority = ContentRefreshPreparationAuthority(
        store=_FakeStore(run=None),
        snapshot_loader=lambda *_args: (_ for _ in ()).throw(
            AssertionError("unclassified request must not rebuild a snapshot")
        ),
        proposal_store=_FakeProposalStore(),  # type: ignore[arg-type]
    )
    planning_request = ContentPlanningProposalRequest(
        service_card_id=SERVICE_CARD_ID,
        expected_planning_input_digest=INPUT_DIGEST,
        requested_by="wilku",
        refresh_preparation_authorization_id="content_refresh_preparation_authorization_test",
        expected_refresh_preparation_authorization_digest="e" * 64,
    )
    initial_request = ContentInitialDraftRequest(
        expected_proposal_id="content_planning_proposal_test",
        expected_planning_digest="f" * 64,
        expected_planning_input_digest=INPUT_DIGEST,
        requested_by="wilku",
        refresh_preparation_authorization_id="content_refresh_preparation_authorization_test",
        expected_refresh_preparation_authorization_digest="e" * 64,
    )

    planning = authority.resolve_planning(WORK_ITEM_ID, planning_request)
    initial = authority.resolve_initial_draft(WORK_ITEM_ID, initial_request)

    assert isinstance(planning, RefreshPreparationRuntimeBlocked)
    assert planning.blocker.code == "refresh_preparation_authorization_foreign"
    assert isinstance(initial, RefreshPreparationRuntimeBlocked)
    assert initial.blocker.code == "refresh_preparation_authorization_foreign"


def test_store_keeps_one_append_only_exact_authorization(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "refresh-preparation.sqlite3")
    run = _stored_refresh_run()
    store.record_production_classification(run)
    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=run.rows[0].source_packet_row_digest,
        current_work_item_id=WORK_ITEM_ID,
        canonical_path=run.rows[0].canonical_path,
        public_url=run.rows[0].public_url,
        classification_blocker_codes=[item.code for item in run.rows[0].blockers],
    )
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=WORK_ITEM_ID,
        classification=classification,
        planning_input_digest=INPUT_DIGEST,
        service_card_id=SERVICE_CARD_ID,
        acknowledged_classification_blocker_codes=classification.classification_blocker_codes,
        authorized_by="wilku",
        authorized_at=utc_now(),
    )

    created = store.record_refresh_preparation_authorization(authorization)
    repeated = store.record_refresh_preparation_authorization(authorization)
    competing = store.record_refresh_preparation_authorization(
        build_content_refresh_preparation_authorization(
            work_item_id=WORK_ITEM_ID,
            classification=classification,
            planning_input_digest=INPUT_DIGEST,
            service_card_id=SERVICE_CARD_ID,
            acknowledged_classification_blocker_codes=classification.classification_blocker_codes,
            authorized_by="inna_osoba",
            authorized_at=utc_now(),
        )
    )
    with sqlite3.connect(store.path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM content_refresh_preparation_authorizations"
        ).fetchone()[0]

    assert created.status == "created"
    assert repeated.status == "idempotent"
    assert competing.status == "conflict"
    assert count == 1

    with pytest.raises(ValueError, match="current classified row"):
        store.record_refresh_preparation_authorization(
            build_content_refresh_preparation_authorization(
                work_item_id=WORK_ITEM_ID,
                classification=classification,
                planning_input_digest=INPUT_DIGEST,
                service_card_id=SERVICE_CARD_ID,
                acknowledged_classification_blocker_codes=["unexpected_classification_blocker"],
                authorized_by="wilku",
                authorized_at=utc_now(),
            )
        )


def test_refresh_preparation_http_contract_is_discriminated_and_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority, _store, _calls, _snapshot = _authority(monkeypatch)
    app = FastAPI()
    router = APIRouter()
    register_content_refresh_preparation_routes(router, authority_factory=lambda: authority)
    app.include_router(router)
    client = TestClient(app)

    selection = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation")
    ready = client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": SERVICE_CARD_ID},
    )
    ready_body = ready.json()
    request = _authorization_request(
        ContentRefreshPreparationReadyToAuthorize.model_validate(ready_body)
    )
    created = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation/authorizations",
        json=request.model_dump(mode="json"),
    )
    repeated = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation/authorizations",
        json=request.model_dump(mode="json"),
    )
    conflict = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation/authorizations",
        json={
            **request.model_dump(mode="json"),
            "acknowledged_classification_blocker_codes": [],
        },
    )
    invalid = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation/authorizations",
        json={**request.model_dump(mode="json"), "unexpected": True},
    )

    assert selection.status_code == 200
    assert selection.json()["status"] == "selection_required"
    assert ready.status_code == 200
    assert ready_body["status"] == "ready_to_authorize"
    assert created.status_code == 201
    assert created.json()["status"] == "created"
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "idempotent"
    assert conflict.status_code == 409
    assert conflict.json()["status"] == "conflict"
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "refresh_preparation_authorization_request_invalid"}
    responses = app.openapi()["paths"][
        "/api/content/work-items/{work_item_id}/refresh-preparation/authorizations"
    ]["post"]["responses"]
    assert responses["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ContentRefreshPreparationAuthorizationIdempotentResponse"
    )
    assert responses["201"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ContentRefreshPreparationAuthorizationCreatedResponse"
    )
    assert responses["409"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ContentRefreshPreparationAuthorizationConflictResponse"
    )
    assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ContentRefreshPreparationAuthorizationValidationErrorResponse"
    )


@pytest.mark.parametrize(
    ("field", "sentinel"),
    [
        ("authorized_by", "Bearer NO_ECHO_SECRET"),
        ("authorized_by", "Basic NO_ECHO_SECRET"),
        ("authorized_by", "/private/NO_ECHO_SECRET"),
        ("authorized_by", "token NO_ECHO_SECRET"),
        ("expected_planning_input_digest", "NO_ECHO_DIGEST"),
    ],
)
def test_authorization_request_validation_never_echoes_submitted_input(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    sentinel: str,
) -> None:
    authority, _store, _calls, _snapshot = _authority(monkeypatch)
    app = FastAPI()
    router = APIRouter()
    register_content_refresh_preparation_routes(router, authority_factory=lambda: authority)
    app.include_router(router)
    ready = authority.preview(WORK_ITEM_ID, service_card_id=SERVICE_CARD_ID)
    assert isinstance(ready, ContentRefreshPreparationReadyToAuthorize)
    payload = _authorization_request(ready).model_dump(mode="json")
    payload[field] = sentinel

    response = TestClient(app).post(
        f"/api/content/work-items/{WORK_ITEM_ID}/refresh-preparation/authorizations",
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "refresh_preparation_authorization_request_invalid"}
    assert sentinel not in response.text


def _authorization_request(
    preview: ContentRefreshPreparationReadyToAuthorize,
) -> ContentRefreshPreparationAuthorizationRequest:
    return ContentRefreshPreparationAuthorizationRequest(
        expected_production_classification_run_digest=preview.classification.classification_run_digest,
        expected_production_classification_decision_set_digest=preview.classification.decision_set_digest,
        expected_production_classification_source_packet_row_digest=(
            preview.classification.source_packet_row_digest
        ),
        expected_planning_input_digest=preview.planning_input_digest,
        service_card_id=preview.service_candidate.service_card_id,
        authorized_by="wilku",
        acknowledged_classification_blocker_codes=preview.classification.classification_blocker_codes,
    )


def _run(
    *,
    alias: bool = False,
    decision: str = "refresh",
    stale: bool = False,
    row: object | None = None,
) -> object:
    value = row or SimpleNamespace(
        current_work_item_id=("other_work_item" if alias else WORK_ITEM_ID),
        decision=decision,
        canonical_path="/analiza-pozwolen-zintegrowanych",
        public_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        source_packet_row_digest=ROW_DIGEST,
        blockers=(SimpleNamespace(code="lineage_needs_review"),),
        next_step_pl="Sprawdź źródła.",
    )
    return SimpleNamespace(
        run_id="content_production_classification_test",
        run_digest=RUN_DIGEST,
        input=SimpleNamespace(decision_set_digest=DECISION_DIGEST),
        freshness=SimpleNamespace(requires_refresh=stale, connector_ids=("gsc",)),
        for_work_item=lambda _work_item_id: value,
    )


def _snapshot(
    *,
    candidate_status: str,
    with_sources: bool,
    with_source_material: bool = True,
    selected: bool = True,
) -> object:
    candidate = SimpleNamespace(
        service_card_id=SERVICE_CARD_ID,
        service_label="Operat wodnoprawny",
        lifecycle_status=candidate_status,
        matched_terms=["operat wodnoprawny"],
        match_reasons=["dokładne dopasowanie"],
    )
    return SimpleNamespace(
        service_profile_context=SimpleNamespace(
            service_card_id=SERVICE_CARD_ID if selected else None,
            service_selection_confirmed=selected,
            binding_status="bound" if selected else "unbound",
            service_candidates=[candidate],
            source_fact_ids=["source_fact_operat"] if with_sources else [],
            source_material_ids=(
                ["source_material_operat"] if with_sources and with_source_material else []
            ),
            evidence_ids=["ev_service"] if with_sources else [],
            source_connectors=["service_profile"] if with_sources else [],
        )
    )


def _classification_binding():
    from wilq.content.workflow.refresh_preparation_contracts import (
        ContentRefreshPreparationClassificationBinding,
    )

    return ContentRefreshPreparationClassificationBinding(
        classification_run_id="content_production_classification_test",
        classification_run_digest=RUN_DIGEST,
        decision_set_digest=DECISION_DIGEST,
        source_packet_row_digest=ROW_DIGEST,
        current_work_item_id=WORK_ITEM_ID,
        canonical_path="/analiza-pozwolen-zintegrowanych",
        public_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        classification_blocker_codes=["lineage_needs_review"],
    )


def _stored_refresh_run():
    run = exact_public_bdo_run()
    payload = run.rows[0].model_dump(mode="python")
    payload.update(
        {
            "canonical_path": "/analiza-pozwolen-zintegrowanych",
            "public_url": "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
            "decision": "refresh",
            "current_work_item_id": WORK_ITEM_ID,
            "retained_work_item_id": None,
            "revision_id": None,
            "revision_digest": None,
            "revision_approved": False,
            "revision_complete": False,
            "retained_binding": None,
            "verified_actions": (),
            "verified_drafts": (),
        }
    )
    row = ContentProductionClassificationRow.model_validate(payload)
    return production_module._build_run(
        input_receipt=run.input,
        counts=classification_counts((row, run.rows[1])),
        freshness=run.freshness,
        source_receipts=run.source_receipts,
        judge_receipt=run.judge_receipt,
        rows=(row, run.rows[1]),
        audit=run.audit,
    )


def _summary() -> ContentPlanningInputSummary:
    return ContentPlanningInputSummary(
        goal="refresh_existing",
        final_canonical_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        service_label="Operat wodnoprawny",
        inventory_status="available",
        content_inventory_status="available",
        acf_section_inventory_status="available",
        source_assessments=[
            ContentPlanningSourceAssessment(
                source=source,
                status="not_applicable",
                reason="Poza zakresem syntetycznego testu.",
            )
            for source in sorted(PLANNING_SOURCE_NAMES)
        ],
        source_fact_count=1,
        source_fact_ids=["source_fact_operat"],
        source_material_ids=["source_material_operat"],
        evidence_id_count=1,
        knowledge_card_count=1,
    )


def _same_authorization_context(
    left: ContentRefreshPreparationAuthorization,
    right: ContentRefreshPreparationAuthorization,
) -> bool:
    return (
        left.work_item_id,
        left.classification_run_digest,
        left.decision_set_digest,
        left.source_packet_row_digest,
        left.planning_input_digest,
        left.service_card_id,
    ) == (
        right.work_item_id,
        right.classification_run_digest,
        right.decision_set_digest,
        right.source_packet_row_digest,
        right.planning_input_digest,
        right.service_card_id,
    )
