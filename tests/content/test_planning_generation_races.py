from __future__ import annotations

import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_planning_proposals as planning_router
from apps.api.wilq_api.routers.content_selected_workspace import (
    register_content_selected_workspace_route,
)
from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from tests.content.dynamic_planning_test_support import (
    PlanningClient,
    configure_planning_harness,
)
from wilq.content.planning import planning_generation_queue
from wilq.content.planning.dynamic_input import (
    build_content_planning_input,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.planning.generation_claim_store import (
    ContentPlanningGenerationClaimStore,
)
from wilq.content.planning.runtime_contract import planning_job_stale_after_seconds
from wilq.content.workflow.refresh_preparation_contracts import ContentRefreshPreparationBinding
from wilq.content.workflow.workspace.catalog import inventory_work_item_id

BDO_WORK_ITEM_ID = inventory_work_item_id(
    "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
)


@pytest.fixture
def planning_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, PlanningClient]:
    return configure_planning_harness(monkeypatch, tmp_path)


def test_legacy_no_pack_parallel_posts_block_before_worker_submission(
    planning_harness: tuple[TestClient, PlanningClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, _runtime = planning_harness
    snapshot = snapshot_for_work_item_or_404(BDO_WORK_ITEM_ID)
    service_card_id = snapshot.service_profile_context.service_card_id
    assert service_card_id is not None
    planning_input = build_content_planning_input(
        snapshot,
        service_card_id=service_card_id,
    ).planning_input
    assert planning_input is not None
    request = ContentPlanningProposalRequest.model_validate(
        _generation_request(service_card_id, planning_input.planning_input_digest)
    )
    post = _planning_endpoint("POST", snapshot=snapshot)

    class HoldingExecutor:
        def __init__(self) -> None:
            self.calls = 0
            self._lock = Lock()

        def submit(self, *_args: Any, **_kwargs: Any) -> None:
            with self._lock:
                self.calls += 1

    executor = HoldingExecutor()
    monkeypatch.setattr(planning_generation_queue, "_PLANNING_GENERATION_EXECUTOR", executor)

    with ThreadPoolExecutor(max_workers=2) as requests:
        responses = [
            future.result()
            for future in [
                requests.submit(post, BDO_WORK_ITEM_ID, request),
                requests.submit(post, BDO_WORK_ITEM_ID, request),
            ]
        ]

    payloads = [json.loads(response.body) for response in responses]
    assert [response.status_code for response in responses] == [409, 409]
    assert [payload["status"] for payload in payloads] == ["blocked", "blocked"]
    assert all(payload["blockers"][0]["code"] == "research_packet_missing" for payload in payloads)
    assert executor.calls == 0


def test_legacy_no_pack_worker_path_blocks_before_model(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, runtime = planning_harness
    snapshot = snapshot_for_work_item_or_404(BDO_WORK_ITEM_ID)
    service_card_id = snapshot.service_profile_context.service_card_id
    assert service_card_id is not None
    planning_input = build_content_planning_input(
        snapshot, service_card_id=service_card_id
    ).planning_input
    assert planning_input is not None
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json=_generation_request(service_card_id, planning_input.planning_input_digest),
    )

    assert response.status_code == 409
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "research_packet_missing"
    assert runtime.calls == 0


def test_legacy_no_pack_review_regeneration_blocks_before_model(
    planning_harness: tuple[TestClient, PlanningClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, runtime = planning_harness
    path = f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    before = client.get(path).json()
    response = client.post(
        path,
        json=_generation_request(before["service_card_id"], before["planning_input_digest"]),
    )

    assert response.status_code == 409
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "research_packet_missing"
    assert runtime.calls == 0


def test_reclaimed_claim_fences_late_terminal_write_and_keeps_newer_result(
    tmp_path: Path,
) -> None:
    path = tmp_path / "planning.sqlite3"
    store = ContentPlanningProposalStore(path)
    work_item_id = "content_work_item_race"
    service_card_id = "service_bdo"
    digest = "a" * 64
    queued = ContentPlanningProposalResponse(
        status="generating",
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        safe_next_step="Poczekaj na wynik.",
    )
    assert (
        store.enqueue_pending(
            work_item_id=work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=digest,
            response=queued,
        )
        == "queued"
    )
    _create_legacy_claim_table(path)

    now = datetime(2026, 8, 7, 12, tzinfo=UTC)
    clock = SimpleNamespace(current=now)
    claim_store = ContentPlanningGenerationClaimStore(
        path,
        clock=lambda: cast(datetime, clock.current),
    )
    claim_a = claim_store.claim(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="worker-a",
    )
    assert claim_a.outcome == "acquired"
    assert claim_a.claim_version == 1

    clock.current = now + timedelta(seconds=planning_job_stale_after_seconds() + 1)
    claim_b = claim_store.claim(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="worker-b",
    )
    assert claim_b.outcome == "acquired"
    assert claim_b.claim_version == 2

    worker_b_result = _failed_terminal_response(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        label="Wynik workera B",
    )
    assert (
        store.save_terminal_response(
            worker_b_result,
            job_planning_input_digest=digest,
            claim_version=claim_b.claim_version,
        )
        == "saved"
    )

    late_worker_a_result = _failed_terminal_response(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        label="Spóźniony wynik workera A",
    )
    stale = planning_generation_queue.save_terminal_response_safely(
        store,
        late_worker_a_result,
        job_planning_input_digest=digest,
        claim_version=claim_a.claim_version,
    )

    assert stale.status == "blocked"
    assert stale.blockers[0].code == "generation_claim_stale"
    persisted = store.queued_response(work_item_id, service_card_id, digest)
    assert persisted is not None
    assert persisted.blockers[0].label == "Wynik workera B"
    assert claim_store.finish(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="worker-b",
        claim_version=claim_b.claim_version,
        status="failed",
    )
    assert not claim_store.finish(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="worker-a",
        claim_version=claim_a.claim_version,
        status="failed",
    )
    _assert_claim_schema_columns(path)


def test_refresh_binding_claim_rejects_an_unbound_worker_terminal_result(tmp_path: Path) -> None:
    path = tmp_path / "bound-refresh-claim.sqlite3"
    store = ContentPlanningProposalStore(path)
    claim_store = ContentPlanningGenerationClaimStore(path)
    binding = _refresh_preparation_binding()
    work_item_id = "content_work_item_refresh"
    service_card_id = "ekologus_service_operat_wodnoprawny"
    digest = "d" * 64
    queued = ContentPlanningProposalResponse(
        status="generating",
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        refresh_preparation_binding=binding,
        safe_next_step="Plan jest przygotowywany.",
    )
    assert (
        store.enqueue_pending(
            work_item_id=work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=digest,
            response=queued,
        )
        == "queued"
    )
    bound_claim = claim_store.claim(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="authorized-worker",
        refresh_preparation_binding=binding,
    )
    conflicting_claim = claim_store.claim(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="legacy-worker",
    )
    unbound_terminal = _failed_terminal_response(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        label="Wynik starego workera",
    )

    assert bound_claim.outcome == "acquired"
    assert conflicting_claim.outcome == "binding_conflict"
    assert (
        store.save_terminal_response(
            unbound_terminal,
            job_planning_input_digest=digest,
            claim_version=bound_claim.claim_version,
        )
        == "claim_stale"
    )
    assert not claim_store.finish(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="authorized-worker",
        claim_version=bound_claim.claim_version,
        status="failed",
    )
    assert claim_store.finish(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner="authorized-worker",
        claim_version=bound_claim.claim_version,
        status="failed",
        refresh_preparation_binding=binding,
    )
    with sqlite3.connect(path) as connection:
        stored = connection.execute(
            """
            SELECT refresh_preparation_authorization_id,
                   refresh_preparation_authorization_digest
            FROM content_planning_generation_claims
            """
        ).fetchone()
    assert stored == (binding.authorization_id, binding.authorization_digest)


def test_legacy_no_pack_snapshot_reads_and_post_do_not_create_planning_jobs(
    planning_harness: tuple[TestClient, PlanningClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, runtime = planning_harness
    store = content_planning_proposal_store()
    selected_router = APIRouter()
    register_content_selected_workspace_route(selected_router)
    selected_endpoint = next(
        route.endpoint
        for route in selected_router.routes
        if getattr(route, "path", "").endswith("/selected-workspace")
    )
    snapshot = snapshot_for_work_item_or_404(BDO_WORK_ITEM_ID)
    planning_get = _planning_endpoint("GET", snapshot=snapshot)

    selected = selected_endpoint(BDO_WORK_ITEM_ID)
    planning = planning_get(BDO_WORK_ITEM_ID)

    assert selected.work_item_id == BDO_WORK_ITEM_ID
    assert planning.status == "not_generated"
    assert _planning_generation_job_count(store.path) == 0
    assert runtime.calls == 0

    class HoldingExecutor:
        calls = 0

        def submit(self, *_args: Any, **_kwargs: Any) -> None:
            self.calls += 1

    executor = HoldingExecutor()
    monkeypatch.setattr(planning_generation_queue, "_PLANNING_GENERATION_EXECUTOR", executor)
    assert planning.service_card_id is not None
    assert planning.planning_input_digest is not None
    planning_post = _planning_endpoint("POST", snapshot=snapshot)
    created = planning_post(
        BDO_WORK_ITEM_ID,
        ContentPlanningProposalRequest.model_validate(
            _generation_request(
                planning.service_card_id,
                planning.planning_input_digest,
            )
        ),
    )

    created_payload = json.loads(created.body)
    assert created.status_code == 409
    assert created_payload["status"] == "blocked"
    assert created_payload["blockers"][0]["code"] == "research_packet_missing"
    assert _planning_generation_job_count(store.path) == 0
    assert executor.calls == 0


def _planning_endpoint(method: str, *, snapshot: Any) -> Any:
    routes = APIRouter()
    planning_router.register_content_planning_proposal_routes(
        routes,
        snapshot_loader=lambda _work_item_id: snapshot,
    )
    return next(
        route.endpoint for route in routes.routes if method in getattr(route, "methods", set())
    )


def _generation_request(service_card_id: str, digest: str) -> dict[str, str]:
    return {
        "service_card_id": service_card_id,
        "expected_planning_input_digest": digest,
        "operator_hint": "Odpowiedz najpierw na najważniejsze pytanie czytelnika.",
        "requested_by": "wilku",
    }


def _post_and_poll_planning(
    client: TestClient,
    path: str,
    request: dict[str, object],
) -> Any:
    response = client.post(path, json=request)
    for _ in range(200):
        if response.json().get("status") != "generating":
            break
        time.sleep(0.05)
        response = client.get(path)
    return response


def _enqueue_and_claim(
    *,
    response: ContentPlanningProposalResponse,
    claim_store: ContentPlanningGenerationClaimStore,
    claim_owner: str,
) -> int:
    service_card_id = response.service_card_id
    digest = response.planning_input_digest
    assert service_card_id is not None
    assert digest is not None
    store = content_planning_proposal_store()
    assert (
        store.enqueue_pending(
            work_item_id=BDO_WORK_ITEM_ID,
            service_card_id=service_card_id,
            planning_input_digest=digest,
            response=response,
        )
        == "queued"
    )
    claim = claim_store.claim(
        work_item_id=BDO_WORK_ITEM_ID,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        claim_owner=claim_owner,
    )
    assert claim.outcome == "acquired"
    return claim.claim_version


def _failed_terminal_response(
    *,
    work_item_id: str,
    service_card_id: str,
    label: str,
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status="failed",
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        blockers=[
            {
                "code": "runtime_failed",
                "label": label,
                "reason": "Kontrolowany wynik testowego workera.",
                "next_step": "Sprawdź zachowany wynik.",
            }
        ],
        safe_next_step="Sprawdź zachowany wynik.",
    )


def _refresh_preparation_binding() -> ContentRefreshPreparationBinding:
    digest = "a" * 64
    return ContentRefreshPreparationBinding(
        authorization_id=f"content_refresh_preparation_authorization_{digest[:24]}",
        authorization_digest=digest,
        classification_run_id="content_production_classification_test",
        classification_run_digest="b" * 64,
        decision_set_digest="c" * 64,
        source_packet_row_digest="d" * 64,
        current_work_item_id="content_work_item_refresh",
        canonical_path="/analiza-pozwolen-zintegrowanych",
        public_url="https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/",
        service_card_id="ekologus_service_operat_wodnoprawny",
        planning_input_digest="d" * 64,
    )


def _create_legacy_claim_table(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE content_planning_generation_claims (
              claim_key TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              service_card_id TEXT NOT NULL,
              planning_input_digest TEXT NOT NULL,
              status TEXT NOT NULL CHECK (status IN ('claimed', 'finished', 'failed')),
              claim_owner TEXT NOT NULL,
              claimed_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE (work_item_id, service_card_id, planning_input_digest)
            )
            """
        )


def _assert_claim_schema_columns(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(content_planning_generation_claims)")
        }
    assert {
        "claim_version",
        "refresh_preparation_authorization_id",
        "refresh_preparation_authorization_digest",
    }.issubset(columns)


def _planning_generation_job_count(path: Path) -> int:
    if not path.exists():
        return 0
    with sqlite3.connect(path) as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("content_planning_generation_jobs",),
        ).fetchone()
        if table is None:
            return 0
        row = connection.execute("SELECT COUNT(*) FROM content_planning_generation_jobs").fetchone()
    return 0 if row is None else int(row[0])


def _planning_claim_status(path: Path) -> str | None:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            """
            SELECT status FROM content_planning_generation_claims
            ORDER BY updated_at DESC LIMIT 1
            """
        ).fetchone()
    return None if row is None else cast(str, row[0])
