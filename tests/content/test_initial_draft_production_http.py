from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import cast

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from pydantic import TypeAdapter, ValidationError

import apps.api.wilq_api.routers.content_initial_draft as initial_draft_router
from apps.api.wilq_api.routers.content_initial_draft import (
    register_content_initial_draft_route,
)
from apps.api.wilq_api.routers.content_new_page_brief import (
    register_content_new_page_brief_routes,
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
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftConflictResponse,
    ContentInitialDraftGenerationResponse,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
    ContentWorkItemInitialDraftRequest,
    ContentWorkItemInitialDraftResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.decisions.production import WAVE0_PRODUCTION_ACCEPTANCE_POLICY
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


def test_repeated_bdo_post_and_get_reuse_without_any_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state.sqlite3"
    store = ContentWorkflowStore(path)
    run = _exact_public_bdo_run()
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    retained_id = binding.retained_work_item_id
    assert retained_id is not None
    store.record_production_classification(run)
    revision = _revision(retained_id, binding.revision_id, binding.revision_digest)
    _insert_revision(store, revision)
    _insert_review(store, _review(revision))
    _initialize_side_effect_tables(path)
    before = _side_effect_counts(path)

    monkeypatch.setattr(initial_draft_router, "state_db_path", lambda: path)
    _patch_all_legacy_side_effects(monkeypatch)
    app = _initial_draft_asgi_app(snapshot_loader=_bomb)
    request = {
        "expected_production_classification_run_digest": run.run_digest,
        "requested_by": "wilku",
    }

    observer = sqlite3.connect(path, isolation_level=None)
    try:
        version_before = cast(int, observer.execute("PRAGMA data_version").fetchone()[0])
        endpoint = _initial_draft_path(binding.current_work_item_id)
        responses = (
            _asgi_request(app, "POST", endpoint, payload=request),
            _asgi_request(app, "POST", endpoint, payload=request),
            _asgi_request(app, "GET", endpoint),
        )
        version_after = cast(int, observer.execute("PRAGMA data_version").fetchone()[0])
    finally:
        observer.close()

    assert [response.status_code for response in responses] == [200, 200, 200]
    bodies = [cast(dict[str, object], response.json()) for response in responses]
    assert bodies[0] == bodies[1] == bodies[2]
    _assert_exact_reused_body(bodies[0])
    assert version_after == version_before
    assert _side_effect_counts(path) == before


@pytest.mark.parametrize(
    "review_update",
    [
        {"principal_id": "non_local_operator"},
        {"decision_id": "   "},
    ],
)
def test_invalid_generic_review_blocks_protected_reuse_without_any_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    review_update: dict[str, str],
) -> None:
    path = tmp_path / "state.sqlite3"
    store = ContentWorkflowStore(path)
    run = _exact_public_bdo_run()
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    retained_id = binding.retained_work_item_id
    assert retained_id is not None
    store.record_production_classification(run)
    revision = _revision(retained_id, binding.revision_id, binding.revision_digest)
    generic_review = ContentDraftRevisionReview.model_validate(
        {
            **_review(revision).model_dump(mode="python"),
            **review_update,
        }
    )
    _insert_revision(store, revision)
    _insert_review(store, generic_review)
    _initialize_side_effect_tables(path)
    before = _side_effect_counts(path)

    monkeypatch.setattr(initial_draft_router, "state_db_path", lambda: path)
    _patch_all_legacy_side_effects(monkeypatch)
    app = _initial_draft_asgi_app(snapshot_loader=_bomb)
    endpoint = _initial_draft_path(binding.current_work_item_id)
    request = {
        "expected_production_classification_run_digest": run.run_digest,
        "requested_by": "wilku",
    }

    observer = sqlite3.connect(path, isolation_level=None)
    try:
        version_before = cast(int, observer.execute("PRAGMA data_version").fetchone()[0])
        responses = (
            _asgi_request(app, "POST", endpoint, payload=request),
            _asgi_request(app, "GET", endpoint),
        )
        version_after = cast(int, observer.execute("PRAGMA data_version").fetchone()[0])
    finally:
        observer.close()

    assert [response.status_code for response in responses] == [200, 200]
    for response in responses:
        body = cast(dict[str, object], response.json())
        assert body["status"] == "blocked"
        assert cast(list[dict[str, object]], body["blockers"])[0]["code"] == (
            "latest_review_mismatch"
        )
        assert body["revision"] is None
    assert version_after == version_before
    assert _side_effect_counts(path) == before


def test_partial_classification_explicit_reuse_is_409_and_stale_digest_wins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state.sqlite3"
    store = ContentWorkflowStore(path)
    run = _exact_public_bdo_run()
    store.record_production_classification(run)
    _patch_all_legacy_side_effects(monkeypatch)
    monkeypatch.setattr(initial_draft_router, "state_db_path", lambda: path)
    app = _initial_draft_asgi_app(snapshot_loader=_bomb)
    endpoint = _initial_draft_path("outside_latest_classification")

    missing_item = _asgi_request(
        app,
        "POST",
        endpoint,
        payload={
            "expected_production_classification_run_digest": run.run_digest,
            "requested_by": "wilku",
        },
    )
    stale = _asgi_request(
        app,
        "POST",
        endpoint,
        payload={
            "expected_production_classification_run_digest": "f" * 64,
            "requested_by": "wilku",
        },
    )

    assert missing_item.status_code == stale.status_code == 409
    missing_body = ContentInitialDraftConflictResponse.model_validate(missing_item.json())
    stale_body = ContentInitialDraftConflictResponse.model_validate(stale.json())
    assert missing_body.blockers[0].code == "production_classification_item_missing"
    assert stale_body.blockers[0].code == "stale_production_classification"


def test_partial_classification_generation_post_and_get_keep_the_legacy_http_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(_exact_public_bdo_run())
    work_item_id = "outside_latest_classification"
    snapshot = object()
    snapshot_calls: list[str] = []
    client = object()

    def load_snapshot(requested_work_item_id: str) -> object:
        snapshot_calls.append(requested_work_item_id)
        return snapshot

    monkeypatch.setattr(initial_draft_router, "content_codex_app_server_client", lambda: client)
    monkeypatch.setattr(
        initial_draft_router.initial_draft_queue,
        "can_queue_initial_draft",
        lambda actual_snapshot, _request, actual_client: (
            actual_snapshot is snapshot and actual_client is client and False
        ),
    )
    monkeypatch.setattr(
        initial_draft_router,
        "generate_initial_full_draft",
        lambda **_kwargs: _legacy_blocked("legacy_post", work_item_id=work_item_id),
    )
    monkeypatch.setattr(initial_draft_router, "content_workflow_store", lambda: _EmptyWorkflow())
    monkeypatch.setattr(initial_draft_router, "local_state_store", lambda: _EmptyRuns())
    monkeypatch.setattr(
        initial_draft_router,
        "content_planning_proposal_store",
        lambda: _EmptyProposals(),
    )
    app = _initial_draft_asgi_app(
        snapshot_loader=load_snapshot,
        authority_resolver=store.resolve_initial_draft_authority,
    )
    request = {
        "expected_proposal_id": "proposal",
        "expected_planning_digest": "a" * 64,
        "expected_planning_input_digest": "b" * 64,
        "requested_by": "wilku",
    }

    endpoint = _initial_draft_path(work_item_id)
    submit = _asgi_request(app, "POST", endpoint, payload=request)
    read = _asgi_request(app, "GET", endpoint)

    assert submit.status_code == read.status_code == 200
    assert submit.json()["blockers"][0]["code"] == "runtime_blocked"
    assert read.json()["blockers"][0]["code"] == "planning_not_ready"
    assert snapshot_calls == [work_item_id]


def test_python_and_openapi_keep_reused_exact_and_new_page_generation_only() -> None:
    store_app = FastAPI()
    register_content_initial_draft_route(
        store_app,
        snapshot_loader=_bomb,
        authority_resolver=cast(
            initial_draft_router.ContentInitialDraftAuthorityResolver,
            _bomb,
        ),
    )
    new_page_app = FastAPI()
    register_content_new_page_brief_routes(new_page_app)
    store_openapi = store_app.openapi()
    new_page_openapi = new_page_app.openapi()

    _assert_request_and_new_page_openapi(store_openapi, new_page_openapi)
    _assert_existing_work_status_openapi(store_openapi)
    _assert_reuse_binding_openapi(store_openapi["components"]["schemas"])
    _assert_python_response_contracts()


def _assert_exact_reused_body(body: dict[str, object]) -> None:
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    retained_id = binding.retained_work_item_id
    assert retained_id is not None
    strict = TypeAdapter(ContentWorkItemInitialDraftResponse).validate_python(body)
    assert strict.status == "reused"
    assert strict.model_dump(mode="json") == body
    assert body["work_item_id"] == binding.current_work_item_id
    assert body["proposal_id"] is None and body["run_id"] is None
    revision = cast(dict[str, object], body["revision"])
    assert revision["revision_number"] == 55
    assert revision["revision_id"] == binding.revision_id
    assert revision["content_digest"] == binding.revision_digest
    assert body["blockers"] == [] and body["publish_ready"] is False
    assert body["runtime"] == {
        "status": "not_started",
        "run_id": None,
        "thread_id": None,
        "turn_id": None,
        "event_methods": [],
        "item_types": [],
        "external_call_attempted": False,
    }
    reuse = cast(dict[str, object], body["reuse_binding"])
    assert reuse["requested_work_item_id"] == binding.current_work_item_id
    assert reuse["lookup_basis"] == "current"
    assert reuse["current_work_item_id"] == binding.current_work_item_id
    assert reuse["retained_work_item_id"] == retained_id
    assert reuse["revision_work_item_id"] == retained_id
    assert reuse["identity_reconciliation_status"] == "fork"
    assert reuse["revision_digest"] == binding.revision_digest
    review = cast(dict[str, object], reuse["approved_review"])
    assert review["decision"] == "approved"
    assert review["revision_digest"] == binding.revision_digest
    assert reuse["must_not_regenerate"] is True


def _assert_request_and_new_page_openapi(
    store_openapi: dict[str, object],
    new_page_openapi: dict[str, object],
) -> None:
    store_paths = cast(dict[str, object], store_openapi["paths"])
    operation = cast(
        dict[str, object],
        store_paths["/api/content/work-items/{work_item_id}/initial-draft"],
    )
    post = cast(dict[str, object], operation["post"])
    request_body = cast(dict[str, object], post["requestBody"])
    content = cast(dict[str, object], request_body["content"])
    request_schema = cast(
        dict[str, object], cast(dict[str, object], content["application/json"])["schema"]
    )
    refs = {
        cast(str, item["$ref"]).rsplit("/", maxsplit=1)[-1]
        for item in cast(list[dict[str, object]], request_schema["anyOf"])
    }
    assert refs == {"ContentInitialDraftRequest", "ContentInitialDraftReuseRequest"}

    new_paths = cast(dict[str, object], new_page_openapi["paths"])
    new_operation = cast(
        dict[str, object],
        new_paths["/api/content/new-page-briefs/{brief_id}/initial-draft"],
    )
    new_post = cast(dict[str, object], new_operation["post"])
    assert _nested_ref(new_post, "requestBody", "content", "application/json", "schema").endswith(
        "/ContentInitialDraftRequest"
    )
    expected = {
        "blocked": "ContentInitialDraftBlockedResponse",
        "conflict": "ContentInitialDraftConflictResponse",
        "created": "ContentInitialDraftCreatedResponse",
        "failed": "ContentInitialDraftFailedResponse",
        "generating": "ContentInitialDraftGeneratingResponse",
    }
    _assert_status_discriminated_openapi(
        _operation_response_schema(new_operation, "post", "200"),
        expected,
    )
    schemas = cast(
        dict[str, dict[str, object]],
        cast(dict[str, object], new_page_openapi["components"])["schemas"],
    )
    _assert_created_and_nonrevision_openapi(schemas, expected)


def _assert_existing_work_status_openapi(store_openapi: dict[str, object]) -> None:
    paths = cast(dict[str, object], store_openapi["paths"])
    operation = cast(
        dict[str, object],
        paths["/api/content/work-items/{work_item_id}/initial-draft"],
    )
    expected = {
        "blocked": "ContentInitialDraftBlockedResponse",
        "created": "ContentInitialDraftCreatedResponse",
        "failed": "ContentInitialDraftFailedResponse",
        "generating": "ContentInitialDraftGeneratingResponse",
        "reused": "ContentInitialDraftReusedResponse",
    }
    for method in ("post", "get"):
        response = _operation_response_schema(operation, method, "200")
        _assert_status_discriminated_openapi(response, expected)
    conflict = _operation_response_schema(operation, "post", "409")
    assert cast(str, conflict["$ref"]).endswith("/ContentInitialDraftConflictResponse")

    schemas = cast(
        dict[str, dict[str, object]],
        cast(dict[str, object], store_openapi["components"])["schemas"],
    )
    _assert_created_and_nonrevision_openapi(schemas, expected)
    _assert_reused_openapi(schemas)


def _assert_status_discriminated_openapi(
    response: dict[str, object],
    expected: dict[str, str],
) -> None:
    discriminator = cast(dict[str, object], response["discriminator"])
    assert discriminator["propertyName"] == "status"
    mapping = cast(dict[str, str], discriminator["mapping"])
    assert {status: ref.rsplit("/", maxsplit=1)[-1] for status, ref in mapping.items()} == expected
    one_of = cast(list[dict[str, str]], response["oneOf"])
    assert len(one_of) == len(expected)
    assert {item["$ref"].rsplit("/", maxsplit=1)[-1] for item in one_of} == set(expected.values())


def _assert_created_and_nonrevision_openapi(
    schemas: dict[str, dict[str, object]],
    expected: dict[str, str],
) -> None:
    created = cast(
        dict[str, dict[str, object]], schemas["ContentInitialDraftCreatedResponse"]["properties"]
    )
    assert created["run_id"]["minLength"] == 1
    assert cast(str, created["revision"]["$ref"]).endswith("/ContentDraftRevision")
    assert created["reuse_binding"]["type"] == "null"
    assert created["blockers"]["maxItems"] == 0
    for status in ("generating", "blocked", "failed", "conflict"):
        name = "ContentInitialDraftConflictResponse" if status == "conflict" else expected[status]
        properties = cast(dict[str, dict[str, object]], schemas[name]["properties"])
        assert properties["status"]["const"] == status
        assert properties["revision"]["type"] == "null"
        assert properties["reuse_binding"]["type"] == "null"
        assert properties["blockers"]["minItems"] == 1


def _assert_reused_openapi(schemas: dict[str, dict[str, object]]) -> None:
    reused = cast(
        dict[str, dict[str, object]], schemas["ContentInitialDraftReusedResponse"]["properties"]
    )
    assert reused["proposal_id"]["type"] == reused["run_id"]["type"] == "null"
    assert cast(str, reused["revision"]["$ref"]).endswith("/ContentDraftRevision")
    assert cast(str, reused["reuse_binding"]["$ref"]).endswith("/ContentInitialDraftReuseBinding")
    assert cast(str, reused["runtime"]["$ref"]).endswith("/ContentInitialDraftReusedRuntime")
    assert reused["blockers"]["maxItems"] == 0
    runtime = cast(
        dict[str, dict[str, object]], schemas["ContentInitialDraftReusedRuntime"]["properties"]
    )
    assert runtime["status"]["const"] == "not_started"
    assert runtime["external_call_attempted"]["const"] is False


def _assert_reuse_binding_openapi(schemas: dict[str, dict[str, object]]) -> None:
    binding = schemas["ContentInitialDraftReuseBinding"]
    required = cast(list[str], binding["required"])
    assert {
        "classification_run_id",
        "classification_run_digest",
        "decision_set_digest",
        "requested_work_item_id",
        "lookup_basis",
        "current_work_item_id",
        "retained_work_item_id",
        "revision_work_item_id",
        "identity_reconciliation_status",
        "revision_id",
        "revision_digest",
        "approved_review",
        "must_not_regenerate",
    }.issubset(required)
    properties = cast(dict[str, dict[str, object]], binding["properties"])
    assert cast(str, properties["approved_review"]["$ref"]).endswith(
        "/ContentInitialDraftApprovedReview"
    )
    approved = cast(
        dict[str, dict[str, object]], schemas["ContentInitialDraftApprovedReview"]["properties"]
    )
    assert approved["decision"]["const"] == "approved"
    assert approved["principal_id"]["const"] == "local_operator"
    assert approved["workspace_id"]["const"] == "ekologus_local_pilot"
    assert approved["trust_level"]["const"] == "local_unverified"


def _assert_python_response_contracts() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(ContentWorkItemInitialDraftRequest).validate_python(
            {
                "expected_proposal_id": "proposal",
                "expected_planning_digest": "a" * 64,
                "expected_planning_input_digest": "b" * 64,
                "expected_production_classification_run_digest": "c" * 64,
                "requested_by": "wilku",
            }
        )
    with pytest.raises(ValidationError):
        ContentInitialDraftRequest.model_validate(
            {
                "expected_production_classification_run_digest": "a" * 64,
                "requested_by": "wilku",
            }
        )
    valid, retained_id = _valid_reused_response_payload()
    adapter = TypeAdapter(ContentWorkItemInitialDraftResponse)
    generation_adapter = TypeAdapter(ContentInitialDraftGenerationResponse)
    assert ContentInitialDraftResponse.model_validate(valid).status == "reused"
    assert adapter.validate_python(valid).status == "reused"
    with pytest.raises(ValidationError):
        generation_adapter.validate_python(valid)
    _assert_reused_python_mutations(adapter, valid, retained_id)
    _assert_created_and_conflict_python_contracts(
        adapter,
        generation_adapter,
        valid,
        retained_id,
    )


def _assert_reused_python_mutations(
    adapter: TypeAdapter[ContentWorkItemInitialDraftResponse],
    valid: dict[str, object],
    retained_id: str,
) -> None:
    reuse = cast(dict[str, object], valid["reuse_binding"])
    review = cast(dict[str, object], reuse["approved_review"])
    invalid_payloads = (
        {**valid, "reuse_binding": None},
        {**valid, "run_id": "run_forbidden"},
        {**valid, "runtime": {**cast(dict[str, object], valid["runtime"]), "run_id": "run"}},
        {
            **valid,
            "reuse_binding": {
                **reuse,
                "lookup_basis": "historical_action_owner",
                "requested_work_item_id": retained_id,
            },
        },
        {**valid, "reuse_binding": {**reuse, "classification_run_id": "   "}},
        {
            **valid,
            "reuse_binding": {
                **reuse,
                "approved_review": {**review, "principal_id": "another_operator"},
            },
        },
        {
            **valid,
            "reuse_binding": {
                **reuse,
                "approved_review": {**review, "decision_id": "   "},
            },
        },
        {
            **valid,
            "reuse_binding": {
                **reuse,
                "approved_review": {**review, "reviewed_by": "   "},
            },
        },
        {**valid, "reuse_binding": {**reuse, "must_not_regenerate": 1}},
    )
    for invalid in invalid_payloads:
        with pytest.raises(ValidationError):
            adapter.validate_python(invalid)


def _assert_created_and_conflict_python_contracts(
    adapter: TypeAdapter[ContentWorkItemInitialDraftResponse],
    generation_adapter: TypeAdapter[ContentInitialDraftGenerationResponse],
    valid: dict[str, object],
    retained_id: str,
) -> None:
    created = {
        **valid,
        "status": "created",
        "work_item_id": retained_id,
        "proposal_id": "proposal_created",
        "run_id": "run_created",
        "reuse_binding": None,
    }
    assert adapter.validate_python(created).status == "created"
    assert generation_adapter.validate_python(created).status == "created"
    with pytest.raises(ValidationError):
        adapter.validate_python({**created, "run_id": "   "})
    with pytest.raises(ValidationError):
        generation_adapter.validate_python({**created, "run_id": "   "})
    blocked = _legacy_blocked("legacy").model_dump(mode="python")
    for status in ("generating", "blocked", "failed", "conflict"):
        response = generation_adapter.validate_python({**blocked, "status": status})
        assert response.status == status
        assert response.revision is None
        assert response.reuse_binding is None
        assert response.blockers
    conflict = {**blocked, "status": "conflict"}
    assert ContentInitialDraftConflictResponse.model_validate(conflict).status == "conflict"
    with pytest.raises(ValidationError):
        adapter.validate_python(conflict)
    with pytest.raises(ValidationError):
        ContentInitialDraftConflictResponse.model_validate(blocked)


def _valid_reused_response_payload() -> tuple[dict[str, object], str]:
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    retained_id = binding.retained_work_item_id
    assert retained_id is not None
    revision = _revision(retained_id, binding.revision_id, binding.revision_digest)
    review = _review(revision)
    return (_reused_response_payload(binding.current_work_item_id, revision, review), retained_id)


def _asgi_request(
    app: FastAPI,
    method: str,
    path: str,
    *,
    payload: object | None = None,
) -> httpx.Response:
    async def exercise() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await asyncio.wait_for(client.request(method, path, json=payload), timeout=5)

    return asyncio.run(exercise())


def _initial_draft_asgi_app(
    *,
    snapshot_loader: Callable[[str], object],
    authority_resolver: initial_draft_router.ContentInitialDraftAuthorityResolver | None = None,
) -> FastAPI:
    router = APIRouter()
    register_content_initial_draft_route(
        router,
        snapshot_loader=cast(
            initial_draft_router.ContentInitialDraftSnapshotLoader,
            snapshot_loader,
        ),
        authority_resolver=authority_resolver,
    )
    for route in router.routes:
        if isinstance(route, APIRoute):
            route.endpoint = _inline_async_endpoint(route.endpoint)
    app = FastAPI()
    app.include_router(router)
    return app


def _inline_async_endpoint(endpoint: Callable[..., object]) -> Callable[..., object]:
    """Keep real ASGI proof independent of the Python 3.14 AnyIO worker hang."""

    @wraps(endpoint)
    async def call(*args: object, **kwargs: object) -> object:
        return endpoint(*args, **kwargs)

    return call


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


def _initialize_side_effect_tables(path: Path) -> None:
    LocalStateStore(path).status()
    proposal_store = ContentPlanningProposalStore(path)
    with proposal_store._connect():
        pass


def _side_effect_counts(path: Path) -> dict[str, int]:
    tables = (
        "content_production_classifications",
        "content_draft_revisions",
        "content_draft_revision_reviews",
        "codex_runs",
        "audit_events",
        "action_mutation_audits",
        "content_planning_proposals",
        "content_planning_generation_jobs",
    )
    with sqlite3.connect(path) as connection:
        return {
            table: cast(int, connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def _reused_response_payload(
    requested_work_item_id: str,
    revision: ContentDraftRevision,
    review: ContentDraftRevisionReview,
) -> dict[str, object]:
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    retained_id = binding.retained_work_item_id
    assert retained_id is not None
    return {
        "status": "reused",
        "work_item_id": binding.current_work_item_id,
        "proposal_id": None,
        "run_id": None,
        "revision": revision.model_dump(mode="json"),
        "reuse_binding": {
            "classification_run_id": "classification_test",
            "classification_run_digest": "c" * 64,
            "decision_set_digest": "d" * 64,
            "requested_work_item_id": requested_work_item_id,
            "lookup_basis": "current",
            "current_work_item_id": binding.current_work_item_id,
            "retained_work_item_id": retained_id,
            "revision_work_item_id": retained_id,
            "identity_reconciliation_status": "fork",
            "revision_id": revision.revision_id,
            "revision_digest": revision.content_digest,
            "approved_review": review.model_dump(mode="json"),
            "must_not_regenerate": True,
        },
        "runtime": {
            "status": "not_started",
            "run_id": None,
            "thread_id": None,
            "turn_id": None,
            "event_methods": [],
            "item_types": [],
            "external_call_attempted": False,
        },
        "blockers": [],
        "safe_next_step": "Otwórz zachowany dokument.",
        "publish_ready": False,
    }


def _legacy_blocked(
    reason: str, *, work_item_id: str = "unclassified"
) -> ContentInitialDraftResponse:
    blocker = ContentInitialDraftBlocker(
        code="runtime_blocked",
        label="Legacy",
        reason=reason,
        next_step="Sprawdź legacy.",
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=work_item_id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _operation_response_schema(
    operation: dict[str, object],
    method: str,
    status_code: str,
) -> dict[str, object]:
    return cast(
        dict[str, object],
        cast(
            dict[str, object],
            cast(
                dict[str, object],
                cast(dict[str, object], operation[method])["responses"],
            )[status_code],
        )["content"],
    )["application/json"]["schema"]


def _nested_ref(value: dict[str, object], *keys: str) -> str:
    current: object = value
    for key in keys:
        current = cast(dict[str, object], current)[key]
    return cast(str, cast(dict[str, object], current)["$ref"])


def _initial_draft_path(work_item_id: str) -> str:
    return f"/api/content/work-items/{work_item_id}/initial-draft"


def _bomb(*_args: object, **_kwargs: object) -> object:
    raise AssertionError("classified initial draft reached a forbidden side effect")


class _EmptyRuns:
    def list_codex_runs(self) -> list[object]:
        return []


class _EmptyProposals:
    def latest(self, _work_item_id: str) -> None:
        return None


class _EmptyWorkflow:
    def load_draft_revision_state(self, _work_item_id: str) -> object:
        return type("RevisionState", (), {"latest_revision": None})()
