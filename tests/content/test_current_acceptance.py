import sqlite3
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_current_acceptance import (
    register_content_current_acceptance_routes,
)
from tests.content.current_acceptance_test_support import _queued_attempt, _snapshot
from wilq.content.workflow.current_acceptance import (
    CurrentAcceptanceRow,
    build_current_acceptance_wave,
    execute_current_acceptance_run,
    observe_current_acceptance_url,
)
from wilq.content.workflow.current_acceptance_contracts import (
    CurrentAcceptanceBlocked,
    CurrentAcceptanceSnapshot,
    CurrentAcceptanceWave,
)
from wilq.content.workflow.current_inventory_reconciliation import (
    CurrentInventoryScopeCounts,
    CurrentInventoryScopeResponse,
    CurrentInventoryScopeRow,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.per_url_disposition_authority import (
    per_url_disposition_blockers,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


@pytest.fixture
def pinned_wordpress_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wilq.content.workflow.store.store_current_acceptance._live_wordpress_generation",
        lambda: ("ev_wp_run",),
    )


def test_current_acceptance_start_validates_request_before_work() -> None:
    response = TestClient(app).post("/api/content/current-acceptance-waves", json={})

    assert response.status_code == 422


def test_current_acceptance_observation_produces_refresh_only_from_exact_reviewed_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, scope_row, page = _snapshot()
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )

    row, observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_test_run",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )

    assert row.decision == "refresh"
    assert row.page_material_status == "observed_material_current"
    assert row.current_work_item_id == "wi_current_acceptance"
    assert row.source_fact_ids == ("synthetic_official_fact",)
    assert row.identity_digest
    assert row.evidence_ids == tuple(sorted(set(row.evidence_ids)))
    assert observation is not None
    assert observation.page_identity.canonical_path == scope_row.canonical_path
    assert observation.source_wave_id == "content_current_acceptance_test_run"
    assert observation.policy_facts.freshness_connector_ids == ("wordpress_ekologus",)


def test_current_acceptance_keep_requires_a_reviewed_exact_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, scope_row, page = _snapshot(page_status="reviewed_material_current")
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )

    row, observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_reviewed",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )

    assert row.decision == "keep"
    assert row.page_material_status == "reviewed_material_current"
    assert observation is not None


def test_current_acceptance_does_not_treat_missing_source_lineage_as_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, scope_row, page = _snapshot(source_facts=(), cards=())
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )

    row, observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_no_sources",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )

    assert row.decision == "blocked"
    assert row.blocker_code
    assert row.observation_id is None
    assert row.source_fact_ids == ()
    assert observation is None


def test_current_acceptance_blocks_wrong_page_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, scope_row, _ = _snapshot()
    wrong_page = CurrentPageEvidenceResponse(
        status="observed_material_current",
        decision="Bieżący materiał odczytany.",
        work_item_id=scope_row.current_work_item_id or "",
        page_url="https://www.ekologus.pl/other-page/",
        material_meaning_digest="b" * 64,
        current_evidence_ids=["ev_current_wrong_page"],
        catalog_evidence_ids=["ev_wp_run"],
        safe_next_step="Sprawdź dokładny adres.",
    )
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: wrong_page,
    )

    row, observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_wrong_page",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )

    assert row.decision == "blocked"
    assert row.blocker_code == "current_acceptance_page_identity_mismatch"
    assert row.observation_id is None
    assert observation is None


def test_current_acceptance_blocks_stale_wordpress_freshness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, scope_row, page = _snapshot()
    snapshot = CurrentAcceptanceSnapshot(
        **{
            **snapshot.__dict__,
            "freshness_assessment": snapshot.freshness_assessment.model_copy(
                update={
                    "state": "stale",
                    "requires_refresh": True,
                    "stale_connector_ids": ["wordpress_ekologus"],
                }
            ),
        }
    )
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )

    row, observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_stale",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )

    assert row.decision == "blocked"
    assert row.blocker_code == "per_url_required_connector_freshness_blocked"
    assert observation is None


def test_current_acceptance_wave_seals_exact_scope_counts() -> None:
    snapshot, scope_row, page = _snapshot()
    current_row = CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="eligible",
        decision="blocked",
        current_work_item_id=scope_row.current_work_item_id,
        blocker_code="synthetic_blocker",
        blocker_owner="Wilku",
        evidence_ids=("ev_wp_run",),
        safe_next_step="Sprawdź exact źródło.",
    )
    wave = build_current_acceptance_wave(
        run_id="content_current_acceptance_test_run",
        snapshot=snapshot,
        rows=(current_row,),
        started_at=snapshot.captured_at,
        completed_at=snapshot.captured_at + timedelta(minutes=1),
    )

    assert wave.counts.rows == 1
    assert wave.counts.scope_eligible == 1
    assert wave.counts.eligible_blocked == 1
    assert wave.counts.keep == 0
    assert wave.rows == (current_row,)
    with pytest.raises(ValueError, match="digest"):
        CurrentAcceptanceWave.model_validate(
            wave.model_dump(mode="json") | {"wave_digest": "f" * 64}
        )


def test_current_acceptance_wave_rejects_duplicate_paths() -> None:
    snapshot, scope_row, _ = _snapshot()
    current_row = CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="eligible",
        decision="blocked",
        current_work_item_id=scope_row.current_work_item_id,
        blocker_code="synthetic_blocker",
        blocker_owner="Wilku",
        safe_next_step="Sprawdź exact źródło.",
    )

    with pytest.raises(ValueError, match="unique canonical paths"):
        build_current_acceptance_wave(
            run_id="content_current_acceptance_duplicate",
            snapshot=snapshot,
            rows=(current_row, current_row),
            started_at=snapshot.captured_at,
            completed_at=snapshot.captured_at + timedelta(minutes=1),
        )


def test_current_acceptance_store_atomically_seals_wave_and_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, page = _snapshot()
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )
    current_row, observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_store_run",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )
    assert observation is not None
    store = ContentWorkflowStore(tmp_path / "current-acceptance.sqlite3")
    request_id = "00000000-0000-4000-8000-000000000001"
    attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_store_run",
        request_id=request_id,
    )
    assert store.create_current_acceptance_attempt(attempt)[0] == "created"
    assert store.create_current_acceptance_attempt(attempt)[0] == "idempotent"
    assert store.mark_current_acceptance_running(attempt.run_id).status == "running"
    wave = build_current_acceptance_wave(
        run_id=attempt.run_id,
        snapshot=snapshot,
        rows=(current_row,),
        started_at=snapshot.captured_at,
        completed_at=snapshot.captured_at + timedelta(minutes=1),
    )

    assert store.record_current_acceptance_wave(wave, (observation,)) == "created"
    assert store.record_current_acceptance_wave(wave, (observation,)) == "idempotent"
    saved_attempt = store.load_current_acceptance_attempt(attempt.run_id)
    assert saved_attempt is not None
    assert saved_attempt.status == "complete"
    assert saved_attempt.wave_digest == wave.wave_digest
    assert store.load_current_acceptance_wave(wave.wave_id) == wave
    assert (
        store.load_content_per_url_decision_observation(observation.observation_id)
        == observation
    )

    with store._connect() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "DELETE FROM content_current_acceptance_waves WHERE wave_id = ?", (wave.wave_id,)
        )


def test_latest_blocked_wave_prevents_disposition_from_a_prior_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, page = _snapshot()
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )
    _, observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_prior_observation",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )
    assert observation is not None
    store = ContentWorkflowStore(tmp_path / "current-acceptance-blocker.sqlite3")
    store.record_content_per_url_decision_observation(observation)
    attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_blocking_wave",
        request_id="00000000-0000-4000-8000-000000000003",
        created_at=snapshot.captured_at + timedelta(minutes=2),
        input_digest="b" * 64,
    )
    store.create_current_acceptance_attempt(attempt)
    store.mark_current_acceptance_running(attempt.run_id)
    row = CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="eligible",
        decision="blocked",
        current_work_item_id=None,
        identity_id=observation.page_identity.identity_id,
        identity_digest=observation.page_identity.identity_digest,
        page_evidence_digest=observation.page_identity.evidence_digest,
        blocker_code="source_fact_lineage_missing",
        blocker_owner="WILQ content workflow",
        evidence_ids=("ev_official_fact", "ev_wp_run"),
        safe_next_step="Uzupełnij exact source-fact lineage.",
    )
    wave = build_current_acceptance_wave(
        run_id=attempt.run_id,
        snapshot=snapshot,
        rows=(row,),
        started_at=attempt.created_at,
        completed_at=attempt.created_at + timedelta(minutes=1),
    )
    store.record_current_acceptance_wave(wave, ())

    blockers = per_url_disposition_blockers(
        store, observation, now=snapshot.captured_at + timedelta(minutes=4)
    )
    assert blockers[0].code == "current_acceptance_blocked"


def test_current_acceptance_path_scope_supersedes_a_rebound_work_item(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, page = _snapshot()
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )
    _, prior_observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_prior_identity",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )
    assert prior_observation is not None
    store = ContentWorkflowStore(tmp_path / "current-acceptance-rebind.sqlite3")
    store.record_content_per_url_decision_observation(prior_observation)
    attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_rebound_wave",
        request_id="00000000-0000-4000-8000-000000000004",
        created_at=snapshot.captured_at + timedelta(minutes=2),
        input_digest="c" * 64,
    )
    store.create_current_acceptance_attempt(attempt)
    store.mark_current_acceptance_running(attempt.run_id)
    rebound_row = CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="eligible",
        decision="blocked",
        current_work_item_id="wi_rebound",
        blocker_code="current_acceptance_work_item_rebound",
        blocker_owner="WILQ content workflow",
        safe_next_step="Użyj bieżącego work-itemu dla tego adresu.",
    )
    wave = build_current_acceptance_wave(
        run_id=attempt.run_id,
        snapshot=snapshot,
        rows=(rebound_row,),
        started_at=attempt.created_at,
        completed_at=attempt.created_at + timedelta(minutes=1),
    )
    store.record_current_acceptance_wave(wave, ())

    latest = store.load_latest_current_acceptance_row_for_path(
        canonical_path=scope_row.canonical_path,
    )
    assert latest is not None
    assert latest.current_work_item_id == "wi_rebound"
    with pytest.raises(TypeError):
        store.load_latest_current_acceptance_row_for_path(
            canonical_path=scope_row.canonical_path,
            current_work_item_id="wi_rebound",
        )

    blockers = per_url_disposition_blockers(
        store, prior_observation, now=snapshot.captured_at + timedelta(minutes=4)
    )
    assert blockers[0].code == "current_acceptance_blocked"


def test_current_acceptance_positive_wave_supersedes_an_older_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, page = _snapshot()
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )
    _, prior_observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_older_observation",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )
    newer_row, newer_observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_newer_observation",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=2),
    )
    assert prior_observation is not None
    assert newer_observation is not None
    assert prior_observation.observation_id != newer_observation.observation_id
    store = ContentWorkflowStore(tmp_path / "current-acceptance-superseded.sqlite3")
    store.record_content_per_url_decision_observation(prior_observation)
    attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_newer_wave",
        request_id="00000000-0000-4000-8000-000000000005",
        created_at=snapshot.captured_at + timedelta(minutes=3),
        input_digest="d" * 64,
    )
    store.create_current_acceptance_attempt(attempt)
    store.mark_current_acceptance_running(attempt.run_id)
    wave = build_current_acceptance_wave(
        run_id=attempt.run_id,
        snapshot=snapshot,
        rows=(newer_row,),
        started_at=attempt.created_at,
        completed_at=attempt.created_at + timedelta(minutes=1),
    )
    store.record_current_acceptance_wave(wave, (newer_observation,))

    blockers = per_url_disposition_blockers(
        store, prior_observation, now=snapshot.captured_at + timedelta(minutes=5)
    )
    assert blockers[0].code == "current_acceptance_observation_superseded"


def test_current_acceptance_newest_path_row_wins_across_waves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, page = _snapshot()
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )
    store = ContentWorkflowStore(tmp_path / "current-acceptance-newest.sqlite3")
    older_row, older_observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_older_matching_wave",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )
    assert older_observation is not None
    store.record_content_per_url_decision_observation(older_observation)
    older_attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_older_matching_wave",
        request_id="00000000-0000-4000-8000-000000000006",
        created_at=snapshot.captured_at + timedelta(minutes=2),
        input_digest="e" * 64,
    )
    store.create_current_acceptance_attempt(older_attempt)
    store.mark_current_acceptance_running(older_attempt.run_id)
    older_wave = build_current_acceptance_wave(
        run_id=older_attempt.run_id,
        snapshot=snapshot,
        rows=(older_row,),
        started_at=older_attempt.created_at,
        completed_at=older_attempt.created_at + timedelta(minutes=1),
    )
    store.record_current_acceptance_wave(older_wave, (older_observation,))
    newer_attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_newer_blocking_wave",
        request_id="00000000-0000-4000-8000-000000000007",
        created_at=snapshot.captured_at + timedelta(minutes=4),
        input_digest="f" * 64,
    )
    store.create_current_acceptance_attempt(newer_attempt)
    store.mark_current_acceptance_running(newer_attempt.run_id)
    newer_blocked_row = CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="eligible",
        decision="blocked",
        current_work_item_id=scope_row.current_work_item_id,
        blocker_code="current_acceptance_source_binding_mismatch",
        blocker_owner="WILQ content workflow",
        safe_next_step="Odczytaj ponownie źródła zatwierdzone dla dokładnej strony.",
    )
    newer_wave = build_current_acceptance_wave(
        run_id=newer_attempt.run_id,
        snapshot=snapshot,
        rows=(newer_blocked_row,),
        started_at=newer_attempt.created_at,
        completed_at=newer_attempt.created_at + timedelta(minutes=1),
    )
    store.record_current_acceptance_wave(newer_wave, ())

    blockers = per_url_disposition_blockers(
        store, older_observation, now=snapshot.captured_at + timedelta(minutes=6)
    )
    assert blockers[0].code == "current_acceptance_blocked"


def test_only_the_claimed_current_acceptance_worker_reads_pages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, _, page = _snapshot()
    reads: list[str] = []

    def read_page(**_kwargs: object) -> CurrentPageEvidenceResponse:
        reads.append("read")
        return page

    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        read_page,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.current_acceptance_snapshot_is_current",
        lambda _snapshot: True,
    )
    store = ContentWorkflowStore(tmp_path / "current-acceptance-claim.sqlite3")
    attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_claim_winner",
        request_id="00000000-0000-4000-8000-000000000008",
        input_digest="1" * 64,
    )
    store.create_current_acceptance_attempt(attempt)
    winner = store.mark_current_acceptance_running(attempt.run_id)
    assert winner is not None
    assert winner.status == "running"

    execute_current_acceptance_run(attempt.run_id, snapshot, store_factory=lambda: store)

    assert reads == []
    saved = store.load_current_acceptance_attempt(attempt.run_id)
    assert saved is not None
    assert saved.status == "running"


def test_current_acceptance_seal_refuses_a_stale_wordpress_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, scope_row, page = _snapshot()
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )
    row, observation = observe_current_acceptance_url(
        run_id="content_current_acceptance_stale_seal",
        scope_row=scope_row,
        snapshot=snapshot,
        store=object(),
        read_time=snapshot.captured_at + timedelta(minutes=1),
    )
    assert observation is not None
    store = ContentWorkflowStore(tmp_path / "current-acceptance-stale-seal.sqlite3")
    attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_stale_seal",
        request_id="00000000-0000-4000-8000-000000000009",
        created_at=snapshot.captured_at + timedelta(minutes=2),
    )
    store.create_current_acceptance_attempt(attempt)
    assert store.mark_current_acceptance_running(attempt.run_id) is not None
    monkeypatch.setattr(
        "wilq.content.workflow.store.store_current_acceptance._live_wordpress_generation",
        lambda: ("ev_new_wordpress_run", "ev_wp_run"),
    )
    wave = build_current_acceptance_wave(
        run_id=attempt.run_id,
        snapshot=snapshot,
        rows=(row,),
        started_at=attempt.created_at,
        completed_at=attempt.created_at + timedelta(minutes=1),
    )

    with pytest.raises(CurrentAcceptanceBlocked) as error:
        store.record_current_acceptance_wave(wave, (observation,))

    assert error.value.code == "current_acceptance_source_superseded"
    saved = store.load_current_acceptance_attempt(attempt.run_id)
    assert saved is not None
    assert saved.status == "running"
    assert store.load_current_acceptance_wave(wave.wave_id) is None


def test_current_acceptance_seal_refuses_missing_scope_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, page = _snapshot()
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )
    second_row = CurrentInventoryScopeRow(
        canonical_path="/candidates-two",
        public_url="https://www.ekologus.pl/candidates-two/",
        disposition="excluded",
        reason_code="commerce_excluded",
        source_evidence_ids=("ev_wp_run",),
        catalog_evidence_ids=("ev_wp_run",),
        safe_next_step="Wykluczony zakres commerce.",
    )
    two_row_scope = CurrentInventoryScopeResponse(
        checked_at=snapshot.scope.checked_at,
        inventory_evidence_ids=snapshot.scope.inventory_evidence_ids,
        counts=CurrentInventoryScopeCounts(rows=2, eligible=1, excluded=1, blocked=0),
        rows=(scope_row, second_row),
    )
    two_row_snapshot = replace(snapshot, scope=two_row_scope)
    blocked_row = CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="eligible",
        decision="blocked",
        current_work_item_id=scope_row.current_work_item_id,
        blocker_code="test_scope_coverage",
        blocker_owner="WILQ content workflow",
        safe_next_step="Sprawdź pełny zakres inventory.",
    )
    store = ContentWorkflowStore(tmp_path / "current-acceptance-scope-coverage.sqlite3")
    attempt = _queued_attempt(
        two_row_snapshot,
        run_id="content_current_acceptance_scope_coverage",
        request_id="00000000-0000-4000-8000-000000000010",
        created_at=two_row_snapshot.captured_at + timedelta(minutes=2),
    )
    store.create_current_acceptance_attempt(attempt)
    assert store.mark_current_acceptance_running(attempt.run_id) is not None
    wave = build_current_acceptance_wave(
        run_id=attempt.run_id,
        snapshot=two_row_snapshot,
        rows=(blocked_row,),
        started_at=attempt.created_at,
        completed_at=attempt.created_at + timedelta(minutes=1),
    )

    with pytest.raises(CurrentAcceptanceBlocked) as error:
        store.record_current_acceptance_wave(wave, ())

    assert error.value.code == "current_acceptance_scope_coverage_mismatch"
    saved = store.load_current_acceptance_attempt(attempt.run_id)
    assert saved is not None
    assert saved.status == "running"
    assert store.load_current_acceptance_wave(wave.wave_id) is None


def test_current_acceptance_seal_refuses_changed_scope_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, _ = _snapshot()
    excluded_row = CurrentAcceptanceRow(
        canonical_path=scope_row.canonical_path,
        public_url=scope_row.public_url,
        scope_disposition="excluded",
        decision="excluded",
        reason_code="commerce_excluded",
        evidence_ids=("ev_wp_run",),
        safe_next_step="Wykluczony zakres commerce.",
    )
    store = ContentWorkflowStore(tmp_path / "current-acceptance-scope-label.sqlite3")
    attempt = _queued_attempt(
        snapshot,
        run_id="content_current_acceptance_scope_label",
        request_id="00000000-0000-4000-8000-000000000011",
        created_at=snapshot.captured_at + timedelta(minutes=2),
    )
    store.create_current_acceptance_attempt(attempt)
    assert store.mark_current_acceptance_running(attempt.run_id) is not None
    wave = build_current_acceptance_wave(
        run_id=attempt.run_id,
        snapshot=snapshot,
        rows=(excluded_row,),
        started_at=attempt.created_at,
        completed_at=attempt.created_at + timedelta(minutes=1),
    )

    with pytest.raises(CurrentAcceptanceBlocked) as error:
        store.record_current_acceptance_wave(wave, ())

    assert error.value.code == "current_acceptance_scope_coverage_mismatch"


def test_current_acceptance_worker_seals_a_full_multi_row_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, page = _snapshot()
    second_row = CurrentInventoryScopeRow(
        canonical_path="/candidates-two",
        public_url="https://www.ekologus.pl/candidates-two/",
        disposition="excluded",
        reason_code="commerce_excluded",
        source_evidence_ids=("ev_wp_run",),
        catalog_evidence_ids=("ev_wp_run",),
        safe_next_step="Wykluczony zakres commerce.",
    )
    two_row_scope = CurrentInventoryScopeResponse(
        checked_at=snapshot.scope.checked_at,
        inventory_evidence_ids=snapshot.scope.inventory_evidence_ids,
        counts=CurrentInventoryScopeCounts(rows=2, eligible=1, excluded=1, blocked=0),
        rows=(scope_row, second_row),
    )
    two_row_snapshot = replace(snapshot, scope=two_row_scope)
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.resolve_current_page_evidence",
        lambda **_: page,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.current_acceptance.current_acceptance_snapshot_is_current",
        lambda _snapshot: True,
    )
    store = ContentWorkflowStore(tmp_path / "current-acceptance-worker-scope.sqlite3")
    attempt = _queued_attempt(
        two_row_snapshot,
        run_id="content_current_acceptance_worker_scope",
        request_id="00000000-0000-4000-8000-000000000012",
        created_at=two_row_snapshot.captured_at,
    )
    store.create_current_acceptance_attempt(attempt)

    execute_current_acceptance_run(attempt.run_id, two_row_snapshot, store_factory=lambda: store)

    saved = store.load_current_acceptance_attempt(attempt.run_id)
    assert saved is not None
    assert saved.status == "complete"
    assert saved.wave_id is not None
    wave = store.load_current_acceptance_wave(saved.wave_id)
    assert wave is not None
    assert wave.counts.rows == 2
    assert wave.counts.scope_eligible == 1
    assert wave.counts.scope_excluded == 1
    assert wave.counts.refresh + wave.counts.keep + wave.counts.eligible_blocked == 1
    assert {
        (row.canonical_path, row.scope_disposition) for row in wave.rows
    } == {
        (scope_row.canonical_path, "eligible"),
        (second_row.canonical_path, "excluded"),
    }


def test_public_current_acceptance_route_starts_and_reads_one_idempotent_wave(
    tmp_path: Path,
    pinned_wordpress_generation: None,
) -> None:
    snapshot, scope_row, _ = _snapshot()
    store = ContentWorkflowStore(tmp_path / "current-acceptance-route.sqlite3")

    def fake_worker(run_id: str, pinned: CurrentAcceptanceSnapshot, *, store_factory) -> None:
        attempt = store_factory().mark_current_acceptance_running(run_id)
        assert attempt is not None
        blocked = CurrentAcceptanceRow(
            canonical_path=scope_row.canonical_path,
            public_url=scope_row.public_url,
            scope_disposition="eligible",
            decision="blocked",
            current_work_item_id=scope_row.current_work_item_id,
            blocker_code="test_source_review_required",
            blocker_owner="Wilku",
            evidence_ids=("ev_wp_run",),
            safe_next_step="Review the exact source.",
        )
        wave = build_current_acceptance_wave(
            run_id=run_id,
            snapshot=pinned,
            rows=(blocked,),
            started_at=attempt.created_at,
            completed_at=attempt.created_at + timedelta(seconds=1),
        )
        store_factory().record_current_acceptance_wave(wave, ())

    router = APIRouter()
    register_content_current_acceptance_routes(
        router,
        snapshot_loader=lambda: snapshot,
        store_factory=lambda: store,
        worker=fake_worker,
    )
    test_app = FastAPI()
    test_app.include_router(router)
    client = TestClient(test_app)
    request_id = str(UUID("00000000-0000-4000-8000-000000000002"))
    start = client.post("/api/content/current-acceptance-waves", json={"request_id": request_id})

    assert start.status_code == 202, start.text
    run_id = start.json()["attempt"]["run_id"]
    readback = client.get(f"/api/content/current-acceptance-waves/{run_id}")
    assert readback.status_code == 200, readback.text
    assert readback.json()["attempt"]["status"] == "complete"
    assert readback.json()["wave"]["counts"]["eligible_blocked"] == 1

    retry = client.post("/api/content/current-acceptance-waves", json={"request_id": request_id})
    assert retry.status_code == 200, retry.text
    assert retry.json()["attempt"]["run_id"] == run_id
