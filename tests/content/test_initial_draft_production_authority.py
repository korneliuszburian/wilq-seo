from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from threading import Event, Thread
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter

import apps.api.wilq_api.routers.content_initial_draft as initial_draft_router
import wilq.content.workflow.decisions.production as production_module
import wilq.content.workflow.store.store_initial_draft_authority as authority_store_module
from apps.api.wilq_api.routers.content_initial_draft import (
    register_content_initial_draft_route,
)
from tests.content.initial_draft_authority_fakes import (
    draft_review as _review,
)
from tests.content.initial_draft_authority_fakes import (
    draft_revision as _revision,
)
from tests.content.initial_draft_authority_fakes import (
    exact_public_bdo_run as _exact_public_bdo_run,
)
from tests.content.initial_draft_authority_fakes import (
    insert_review as _insert_review,
)
from tests.content.initial_draft_authority_fakes import (
    insert_revision as _insert_revision,
)
from tests.content.initial_draft_authority_fakes import (
    insert_revision_and_review as _insert_revision_and_review,
)
from tests.content.initial_draft_authority_fakes import (
    nonreuse_run as _nonreuse_run,
)
from tests.content.initial_draft_authority_fakes import (
    ready_store as _ready_store,
)
from tests.content.initial_draft_authority_fakes import (
    retained_missing_run as _retained_missing_run,
)
from tests.content.initial_draft_authority_fakes import (
    seed_reuse_state as _seed_reuse_state,
)
from tests.content.initial_draft_authority_fakes import (
    stale_reuse_run as _stale_reuse_run,
)
from wilq.content.drafts.initial_draft_authority import (
    InitialDraftAuthorityBlocked,
    InitialDraftAuthorityReused,
    StatusRead,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftResponse,
    ContentWorkItemInitialDraftRequest,
)
from wilq.content.workflow.decisions.production import (
    WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionReview,
)
from wilq.content.workflow.store.store import ContentWorkflowStore

HISTORICAL_ID = "content_work_item_historical_bdo"
_SubmitEndpoint = Callable[
    [str, ContentWorkItemInitialDraftRequest],
    ContentInitialDraftResponse | JSONResponse,
]
_ReadEndpoint = Callable[[str], ContentInitialDraftResponse]


@pytest.mark.parametrize(
    ("request_payload", "expected_code"),
    [
        (
            {
                "expected_proposal_id": "proposal",
                "expected_planning_digest": "a" * 64,
                "expected_planning_input_digest": "b" * 64,
                "requested_by": "wilku",
            },
            "production_classification_digest_required",
        ),
        (
            {
                "expected_production_classification_run_digest": "f" * 64,
                "requested_by": "wilku",
            },
            "stale_production_classification",
        ),
    ],
)
def test_missing_or_stale_submit_digest_is_409_before_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request_payload: dict[str, str],
    expected_code: str,
) -> None:
    store = _ready_store(tmp_path / "state.sqlite3")
    _patch_all_legacy_side_effects(monkeypatch)
    submit_endpoint, _read_endpoint = _registered_endpoints(store)

    response = _call_submit(
        submit_endpoint,
        WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding.current_work_item_id,
        request_payload,
    )

    assert response[0] == 409
    assert response[1]["status"] == "conflict"
    assert response[1]["blockers"][0]["code"] == expected_code


def test_reuse_submit_without_any_classification_is_409(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    _patch_all_legacy_side_effects(monkeypatch)

    submit_endpoint, _read_endpoint = _registered_endpoints(store)
    response = _call_submit(
        submit_endpoint,
        "unclassified",
        {
            "expected_production_classification_run_digest": "a" * 64,
            "requested_by": "wilku",
        },
    )

    assert response[0] == 409
    assert response[1]["blockers"][0]["code"] == "production_classification_missing"


@pytest.mark.parametrize(
    ("state", "expected_code"),
    [
        ("missing_revision", "latest_revision_missing"),
        ("later_revision", "latest_revision_drift"),
        ("revision_id_drift", "latest_revision_drift"),
        ("revision_digest_drift", "latest_revision_drift"),
        ("missing_review", "latest_review_missing"),
        ("latest_nonapproved_review", "latest_review_not_approved"),
        ("review_identity_mismatch", "latest_review_mismatch"),
        ("review_digest_mismatch", "latest_review_mismatch"),
    ],
)
def test_reuse_revision_or_review_drift_blocks_without_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    expected_code: str,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = _exact_public_bdo_run()
    store.record_production_classification(run)
    _seed_reuse_state(store, state)
    _patch_all_legacy_side_effects(monkeypatch)
    submit_endpoint, read_endpoint = _registered_endpoints(store)
    work_item_id = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding.current_work_item_id

    read = _call_read(read_endpoint, work_item_id)
    submit = _call_submit(
        submit_endpoint,
        work_item_id,
        {
            "expected_production_classification_run_digest": run.run_digest,
            "requested_by": "wilku",
        },
    )

    assert read[0] == submit[0] == 200
    assert read[1]["status"] == submit[1]["status"] == "blocked"
    assert read[1]["blockers"][0]["code"] == expected_code
    assert submit[1]["blockers"][0]["code"] == expected_code
    assert read[1]["revision"] is None
    assert submit[1]["revision"] is None


def test_retained_missing_without_a_distinct_historical_owner_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = _retained_missing_run(historical_owner=None)
    store.record_production_classification(run)
    _patch_all_legacy_side_effects(monkeypatch)
    current_id = run.rows[0].current_work_item_id
    assert current_id is not None

    _submit_endpoint, read_endpoint = _registered_endpoints(store)
    response = _call_read(read_endpoint, current_id)

    assert response[0] == 200
    assert response[1]["blockers"][0]["code"] == "missing_revision_owner"


def test_stale_accepted_reuse_authority_blocks_with_freshness_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = _stale_reuse_run()
    row = run.rows[0]
    owner = row.reusable_work_item_id
    current_id = row.current_work_item_id
    assert owner is not None and current_id is not None
    revision = _revision(owner, cast(str, row.revision_id), cast(str, row.revision_digest))
    store.record_production_classification(run)
    _insert_revision(store, revision)
    _insert_review(store, _review(revision))
    _patch_all_legacy_side_effects(monkeypatch)
    monkeypatch.setattr(authority_store_module, "latest_draft_revision", _bomb)
    submit_endpoint, read_endpoint = _registered_endpoints(store)

    read = _call_read(read_endpoint, current_id)
    submit = _call_submit(
        submit_endpoint,
        current_id,
        {
            "expected_production_classification_run_digest": run.run_digest,
            "requested_by": "wilku",
        },
    )

    assert read[0] == submit[0] == 200
    assert read[1] == submit[1]
    blocker = cast(dict[str, object], read[1]["blockers"][0])
    assert blocker["code"] == "stale_production_classification"
    assert blocker["source_codes"] == list(run.freshness.connector_ids)


@pytest.mark.parametrize("decision", ["refresh", "write", "blocked"])
def test_nonreuse_classification_disables_generation_with_row_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = _nonreuse_run(cast(production_module.Classification, decision))
    store.record_production_classification(run)
    row = run.rows[1]
    current_id = row.current_work_item_id
    assert current_id is not None
    _patch_all_legacy_side_effects(monkeypatch)

    submit_endpoint, read_endpoint = _registered_endpoints(store)
    response = _call_read(read_endpoint, current_id)
    submit = _call_submit(
        submit_endpoint,
        current_id,
        {
            "expected_production_classification_run_digest": run.run_digest,
            "requested_by": "wilku",
        },
    )

    assert response[0] == submit[0] == 200
    body = response[1]
    assert submit[1] == body
    assert body["status"] == "blocked"
    assert body["blockers"][0]["code"] == "production_generation_disabled"
    assert body["blockers"][0]["reason"] == row.rationale_pl
    assert body["blockers"][0]["next_step"] == row.next_step_pl
    assert body["blockers"][0]["source_codes"] == [item.code for item in row.blockers]


@pytest.mark.parametrize(
    ("alias", "lookup_basis", "retained_missing"),
    [
        ("current", "current", False),
        ("retained", "retained", False),
        ("historical", "historical_action_owner", True),
    ],
)
def test_current_retained_and_historical_aliases_resolve_exactly(
    tmp_path: Path,
    alias: str,
    lookup_basis: str,
    retained_missing: bool,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = (
        _retained_missing_run(historical_owner=HISTORICAL_ID)
        if retained_missing
        else _exact_public_bdo_run()
    )
    row = run.rows[0]
    owner = HISTORICAL_ID if retained_missing else row.retained_work_item_id
    assert owner is not None
    requested = {
        "current": row.current_work_item_id,
        "retained": row.retained_work_item_id,
        "historical": HISTORICAL_ID,
    }[alias]
    assert requested is not None
    store.record_production_classification(run)
    revision = _revision(owner, cast(str, row.revision_id), cast(str, row.revision_digest))
    _insert_revision(store, revision)
    _insert_review(store, _review(revision))

    result = store.resolve_initial_draft_authority(requested, StatusRead())

    assert isinstance(result, InitialDraftAuthorityReused)
    assert result.requested_work_item_id == requested
    assert result.lookup_basis == lookup_basis
    assert result.current_work_item_id == row.current_work_item_id
    assert result.retained_work_item_id == row.retained_work_item_id
    assert result.revision_work_item_id == owner


def test_review_lookup_keeps_the_retained_owners_exact_approved_review(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = _exact_public_bdo_run()
    row = run.rows[0]
    owner = row.reusable_work_item_id
    assert owner is not None
    revision = _revision(owner, cast(str, row.revision_id), cast(str, row.revision_digest))
    approved = _review(revision)
    foreign_review = ContentDraftRevisionReview.model_validate(
        {
            **_review(revision, number=2).model_dump(mode="python"),
            "work_item_id": "content_work_item_other_owner",
        }
    )
    store.record_production_classification(run)
    _insert_revision(store, revision)
    _insert_review(store, approved)
    _insert_review(store, foreign_review)

    result = store.resolve_initial_draft_authority(
        cast(str, row.current_work_item_id),
        StatusRead(),
    )

    assert isinstance(result, InitialDraftAuthorityReused)
    assert result.approved_review == approved
    assert result.approved_review.work_item_id == owner
    assert result.approved_review.decision_number == 1


def test_wal_resolution_uses_one_plain_begin_snapshot_without_torn_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state.sqlite3"
    base_store = _ready_store(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    tracking_store = _TrackingContentWorkflowStore(path)
    selected = Event()
    writer_done = Event()
    original_load = authority_store_module.load_latest_production_classification_from_connection

    def classification_barrier(connection: sqlite3.Connection):
        run = original_load(connection)
        selected.set()
        assert writer_done.wait(timeout=5)
        return run

    monkeypatch.setattr(
        authority_store_module,
        "load_latest_production_classification_from_connection",
        classification_barrier,
    )
    outcomes: list[object] = []
    errors: list[BaseException] = []
    current_id = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding.current_work_item_id

    def resolve() -> None:
        try:
            outcomes.append(
                tracking_store.resolve_initial_draft_authority(current_id, StatusRead())
            )
        except BaseException as error:  # pragma: no cover - asserted below
            errors.append(error)

    thread = Thread(target=resolve)
    thread.start()
    assert selected.wait(timeout=5)
    retained_id = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding.retained_work_item_id
    assert retained_id is not None
    newer = _revision(retained_id, "content_revision_newer", "e" * 64, number=56)
    with sqlite3.connect(path) as writer_connection:
        _insert_revision_and_review(writer_connection, newer, _review(newer))
    writer_done.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == []
    assert len(outcomes) == 1
    old_snapshot = outcomes[0]
    assert isinstance(old_snapshot, InitialDraftAuthorityReused)
    assert old_snapshot.revision.revision_number == 55
    assert tracking_store.connection_count == 1
    begin_statements = [
        statement for statement in tracking_store.statements if "BEGIN" in statement
    ]
    assert begin_statements == ["BEGIN"]
    assert all("IMMEDIATE" not in statement for statement in begin_statements)
    newer_snapshot = base_store.resolve_initial_draft_authority(current_id, StatusRead())
    assert isinstance(newer_snapshot, InitialDraftAuthorityBlocked)
    assert newer_snapshot.code == "latest_revision_drift"


def _patch_all_legacy_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    for target, name in (
        (initial_draft_router, "content_codex_app_server_client"),
        (initial_draft_router, "generate_initial_full_draft"),
        (initial_draft_router, "content_workflow_store"),
        (initial_draft_router, "local_state_store"),
        (initial_draft_router, "content_planning_proposal_store"),
        (initial_draft_router.initial_draft_queue, "can_queue_initial_draft"),
        (initial_draft_router.initial_draft_queue, "submit_initial_draft_to_queue"),
        (initial_draft_router.initial_draft_queue, "run_queued_initial_draft"),
    ):
        monkeypatch.setattr(target, name, _bomb)
    monkeypatch.setattr(initial_draft_router._INITIAL_DRAFT_EXECUTOR, "submit", _bomb)
    monkeypatch.setattr(ContentWorkflowStore, "append_draft_revision", _bomb)


def _registered_endpoints(
    store: ContentWorkflowStore,
) -> tuple[_SubmitEndpoint, _ReadEndpoint]:
    app = FastAPI()
    register_content_initial_draft_route(
        app,
        snapshot_loader=_bomb,
        authority_resolver=store.resolve_initial_draft_authority,
    )
    return _initial_draft_endpoints(app)


def _initial_draft_endpoints(app: FastAPI) -> tuple[_SubmitEndpoint, _ReadEndpoint]:
    routes = [
        route
        for route in app.routes
        if getattr(route, "path", "") == "/api/content/work-items/{work_item_id}/initial-draft"
    ]
    submit = next(route.endpoint for route in routes if "POST" in route.methods)
    read = next(route.endpoint for route in routes if "GET" in route.methods)
    return cast(_SubmitEndpoint, submit), cast(_ReadEndpoint, read)


def _call_submit(
    endpoint: _SubmitEndpoint,
    work_item_id: str,
    payload: dict[str, str],
) -> tuple[int, dict[str, object]]:
    request = TypeAdapter(ContentWorkItemInitialDraftRequest).validate_python(payload)
    result = endpoint(work_item_id, request)
    return _response_payload(result)


def _call_read(endpoint: _ReadEndpoint, work_item_id: str) -> tuple[int, dict[str, object]]:
    result = endpoint(work_item_id)
    return _response_payload(result)


def _response_payload(result: object) -> tuple[int, dict[str, object]]:
    if isinstance(result, JSONResponse):
        return result.status_code, cast(dict[str, object], json.loads(result.body))
    response = cast(ContentInitialDraftResponse, result)
    return 200, response.model_dump(mode="json")


def _bomb(*_args: object, **_kwargs: object) -> object:
    raise AssertionError("classified initial draft reached a forbidden side effect")


class _TrackingContentWorkflowStore(ContentWorkflowStore):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.connection_count = 0
        self.statements: list[str] = []

    def _connect(self) -> sqlite3.Connection:
        self.connection_count += 1
        connection = super()._connect()
        connection.set_trace_callback(self.statements.append)
        return connection
