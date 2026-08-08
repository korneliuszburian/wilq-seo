from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Lock
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
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning.dynamic_input import (
    build_content_planning_input,
    content_planning_input_summary,
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
    PlanningGenerationClaim,
)
from wilq.content.planning.runtime_contract import planning_job_stale_after_seconds
from wilq.content.workflow.catalog import inventory_work_item_id

BDO_WORK_ITEM_ID = inventory_work_item_id(
    "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
)


@pytest.fixture
def planning_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, PlanningClient]:
    return configure_planning_harness(monkeypatch, tmp_path)


def test_two_parallel_posts_submit_one_worker_and_reclaim_crashed_claim_after_ttl(
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
    now = datetime(2026, 8, 7, 12, tzinfo=UTC)
    clock = SimpleNamespace(current=now)
    claim_store = ContentPlanningGenerationClaimStore(
        content_planning_proposal_store().path,
        clock=lambda: cast(datetime, clock.current),
    )
    claim_barrier = Barrier(2)
    outcome_lock = Lock()
    claim_outcomes: list[str] = []
    durable_claim = claim_store.claim

    def synchronized_claim(**kwargs: str) -> PlanningGenerationClaim:
        claim_barrier.wait(timeout=5)
        claim = durable_claim(**kwargs)
        with outcome_lock:
            claim_outcomes.append(claim.outcome)
        return claim

    monkeypatch.setattr(claim_store, "claim", synchronized_claim)
    monkeypatch.setattr(planning_router, "_PLANNING_GENERATION_EXECUTOR", executor)
    monkeypatch.setattr(
        planning_router,
        "content_planning_generation_claim_store",
        lambda: claim_store,
    )

    with ThreadPoolExecutor(max_workers=2) as requests:
        responses = [
            future.result()
            for future in [
                requests.submit(post, BDO_WORK_ITEM_ID, request),
                requests.submit(post, BDO_WORK_ITEM_ID, request),
            ]
        ]

    assert [response.status for response in responses] == ["generating", "generating"]
    assert sorted(claim_outcomes) == ["acquired", "in_flight"]
    assert executor.calls == 1

    monkeypatch.setattr(claim_store, "claim", durable_claim)
    clock.current = now + timedelta(seconds=planning_job_stale_after_seconds() + 1)
    recovered = post(BDO_WORK_ITEM_ID, request)

    assert recovered.status == "generating"
    assert executor.calls == 2


def test_worker_reloads_digest_before_codex_and_finishes_matching_claim(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    _client, runtime = planning_harness
    original_snapshot = snapshot_for_work_item_or_404(BDO_WORK_ITEM_ID)
    service_card_id = original_snapshot.service_profile_context.service_card_id
    assert service_card_id is not None
    planning_input = build_content_planning_input(
        original_snapshot,
        service_card_id=service_card_id,
    ).planning_input
    assert planning_input is not None
    expected_digest = planning_input.planning_input_digest
    request = ContentPlanningProposalRequest.model_validate(
        _generation_request(service_card_id, expected_digest)
    )
    store = content_planning_proposal_store()
    claim_store = ContentPlanningGenerationClaimStore(store.path)

    def queued_response(run_id: str) -> ContentPlanningProposalResponse:
        return ContentPlanningProposalResponse(
            status="generating",
            work_item_id=BDO_WORK_ITEM_ID,
            service_card_id=service_card_id,
            planning_input_digest=expected_digest,
            input_summary=content_planning_input_summary(planning_input),
            runtime=ContentCodexRuntimeTrace(status="not_started", run_id=run_id),
            safe_next_step="Plan jest przygotowywany.",
        )

    stale_claim_version = _enqueue_and_claim(
        response=queued_response("planning_stale_context"),
        claim_store=claim_store,
        claim_owner="worker-stale",
    )
    item = original_snapshot.preflight.item
    changed_item = item.model_copy(
        update={
            "wordpress_content_text": (
                f"{item.wordpress_content_text or ''} Zmieniony kontekst przed workerem."
            )
        }
    )
    changed_snapshot = original_snapshot.model_copy(
        update={
            "preflight": original_snapshot.preflight.model_copy(
                update={"item": changed_item}
            )
        }
    )

    planning_router._run_queued_planning_generation(
        BDO_WORK_ITEM_ID,
        request,
        lambda _work_item_id: changed_snapshot,
        claim_store,
        "worker-stale",
        stale_claim_version,
    )

    stale = store.queued_response(BDO_WORK_ITEM_ID, service_card_id, expected_digest)
    assert stale is not None
    assert stale.status == "stale"
    assert stale.planning_input_digest != expected_digest
    assert stale.blockers[0].code == "stale_input"
    assert runtime.calls == 0
    assert _planning_claim_status(store.path) == "failed"

    current_claim_version = _enqueue_and_claim(
        response=queued_response("planning_current_context"),
        claim_store=claim_store,
        claim_owner="worker-current",
    )
    planning_router._run_queued_planning_generation(
        BDO_WORK_ITEM_ID,
        request,
        lambda _work_item_id: original_snapshot,
        claim_store,
        "worker-current",
        current_claim_version,
    )

    assert runtime.calls == 1
    assert store.for_input(BDO_WORK_ITEM_ID, service_card_id, expected_digest) is not None
    assert _planning_claim_status(store.path) == "finished"


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
    assert store.enqueue_pending(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        response=queued,
    ) == "queued"
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
    assert store.save_terminal_response(
        worker_b_result,
        job_planning_input_digest=digest,
        claim_version=claim_b.claim_version,
    ) == "saved"

    late_worker_a_result = _failed_terminal_response(
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        label="Spóźniony wynik workera A",
    )
    stale = planning_router._save_terminal_response_safely(
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
    with sqlite3.connect(path) as connection:
        columns = {
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(content_planning_generation_claims)"
            )
        }
    assert "claim_version" in columns


def test_snapshot_and_selected_workspace_reads_do_not_create_planning_jobs(
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
    monkeypatch.setattr(planning_router, "_PLANNING_GENERATION_EXECUTOR", executor)
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

    assert created.status == "generating"
    assert _planning_generation_job_count(store.path) == 1
    assert executor.calls == 1


def _planning_endpoint(method: str, *, snapshot: Any) -> Any:
    routes = APIRouter()
    planning_router.register_content_planning_proposal_routes(
        routes,
        snapshot_loader=lambda _work_item_id: snapshot,
    )
    return next(
        route.endpoint
        for route in routes.routes
        if method in getattr(route, "methods", set())
    )


def _generation_request(service_card_id: str, digest: str) -> dict[str, str]:
    return {
        "service_card_id": service_card_id,
        "expected_planning_input_digest": digest,
        "operator_hint": "Odpowiedz najpierw na najważniejsze pytanie czytelnika.",
        "requested_by": "wilku",
    }


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
    assert store.enqueue_pending(
        work_item_id=BDO_WORK_ITEM_ID,
        service_card_id=service_card_id,
        planning_input_digest=digest,
        response=response,
    ) == "queued"
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
        row = connection.execute(
            "SELECT COUNT(*) FROM content_planning_generation_jobs"
        ).fetchone()
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
