from __future__ import annotations

import asyncio
import hmac
import json
import sqlite3
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import httpx
import pytest

from apps.api.wilq_api.main import app
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


def _state_rows(state_path: Path) -> list[tuple[str, str, str]]:
    with sqlite3.connect(state_path) as connection:
        return connection.execute(
            "SELECT id, started_at, payload_json FROM codex_runs ORDER BY id"
        ).fetchall()


def _get(path: str, *, params: dict[str, object] | None = None) -> httpx.Response:
    async def exercise() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 45124))
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1",
        ) as client:
            return await client.get(path, params=params)

    return asyncio.run(exercise())


def _tamper_cursor(cursor: str, *, remove_version: bool = False, **changes: object) -> str:
    payload_segment, signature_segment = cursor.split(".", maxsplit=1)
    padding = "=" * (-len(payload_segment) % 4)
    payload = json.loads(urlsafe_b64decode(f"{payload_segment}{padding}"))
    if remove_version:
        payload.pop("version", None)
    payload.update(changes)
    tampered_payload = urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"{tampered_payload}.{signature_segment}"


def _signed_cursor_payload(payload: bytes) -> str:
    signature = hmac.new(b"test-run-history-key", payload, sha256).digest()
    return f"{_encode_cursor_segment(payload)}.{_encode_cursor_segment(signature)}"


def _encode_cursor_segment(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


def test_run_history_defaults_to_50_and_bounds_explicit_limits(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "codex_history_limits.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    store = LocalStateStore(state_path)
    started_at = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    runs = [
        CodexRun(
            id=f"codex_limit_{index:03d}",
            status="completed",
            started_at=started_at - timedelta(minutes=index),
        )
        for index in range(101)
    ]
    with store.run_transaction() as connection:
        connection.executemany(
            "INSERT INTO codex_runs (id, started_at, payload_json) VALUES (?, ?, ?)",
            [
                (run.id, run.started_at.isoformat(), run.model_dump_json())
                for run in runs
            ],
        )

    default_response = _get("/api/codex/run-history")
    max_response = _get("/api/codex/run-history", params={"limit": 100})

    assert default_response.status_code == 200
    assert len(default_response.json()["items"]) == 50
    assert default_response.json()["total_count"] == 101
    assert default_response.json()["next_cursor"] is not None
    assert max_response.status_code == 200
    assert len(max_response.json()["items"]) == 100
    assert max_response.json()["total_count"] == 101

    for invalid_limit in (0, -1, 101, "not-an-integer"):
        response = _get(
            "/api/codex/run-history",
            params={"limit": invalid_limit},
        )
        assert response.status_code == 422


def test_run_history_total_count_is_page_independent_and_cursor_ends(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_CODEX_RUN_HISTORY_CURSOR_SECRET", "test-run-history-key")
    state_path = tmp_path / "codex_history_pages.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    store = LocalStateStore(state_path)
    shared_started_at = datetime(2026, 8, 22, 9, 0, tzinfo=UTC)
    for run_id in ("codex_alpha", "codex_charlie", "codex_bravo"):
        store.save_codex_run(
            CodexRun(
                id=run_id,
                skill="wilq-content-operator",
                status="failed" if run_id == "codex_alpha" else "completed",
                model="gpt-5.6-sol",
                prompt_template_id="content_initial_draft@v2",
                cost_estimate_pln=1.25,
                source_material_ids=["source_a", "source_b"],
                evidence_ids=["ev_private_trace"],
                started_at=shared_started_at,
            )
        )

    first_response = _get("/api/codex/run-history", params={"limit": 2})

    assert first_response.status_code == 200
    first_page = first_response.json()
    assert [item["id"] for item in first_page["items"]] == [
        "codex_charlie",
        "codex_bravo",
    ]
    assert first_page["total_count"] == 3
    assert first_page["next_cursor"] is not None
    assert set(first_page["items"][0]) == {
        "id",
        "skill",
        "status",
        "model",
        "prompt_template_id",
        "cost_estimate_pln",
        "source_material_count",
        "started_at",
    }

    final_response = _get(
        "/api/codex/run-history",
        params={"limit": 2, "cursor": first_page["next_cursor"]},
    )

    assert final_response.status_code == 200
    final_page = final_response.json()
    assert [item["id"] for item in final_page["items"]] == ["codex_alpha"]
    assert final_page["total_count"] == 3
    assert final_page["next_cursor"] is None


def test_run_history_rejects_a_malformed_opaque_cursor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_CODEX_RUN_HISTORY_CURSOR_SECRET", "test-run-history-key")
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "codex_history_cursor.sqlite3"))

    response = _get(
        "/api/codex/run-history",
        params={"cursor": "not-a-valid-cursor"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("remove_version", "changes"),
    [
        (False, {"run_id": "zzzz"}),
        (False, {"started_at": "2030-01-01T00:00:00+00:00"}),
        (False, {"version": 2}),
        (True, {}),
    ],
    ids=["run-id", "timestamp", "version", "missing-version"],
)
def test_run_history_rejects_semantically_tampered_cursor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    remove_version: bool,
    changes: dict[str, object],
) -> None:
    monkeypatch.setenv("WILQ_CODEX_RUN_HISTORY_CURSOR_SECRET", "test-run-history-key")
    state_path = tmp_path / "codex_history_tampered_cursor.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    store = LocalStateStore(state_path)
    shared_started_at = datetime(2026, 8, 22, 9, 0, tzinfo=UTC)
    for run_id in ("codex_delta", "codex_charlie", "codex_bravo", "codex_alpha"):
        store.save_codex_run(
            CodexRun(id=run_id, status="completed", started_at=shared_started_at)
        )

    first_page = _get("/api/codex/run-history", params={"limit": 2}).json()
    tampered_cursor = _tamper_cursor(
        first_page["next_cursor"],
        remove_version=remove_version,
        **changes,
    )

    response = _get(
        "/api/codex/run-history",
        params={"limit": 2, "cursor": tampered_cursor},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        b'{"started_at":"2026-08-22T09:00:00+00:00","run_id":"codex_alpha"}',
        b'{"version":2,"started_at":"2026-08-22T09:00:00+00:00","run_id":"codex_alpha"}',
        b'{"version":1,"started_at":"2026-08-22T09:00:00","run_id":"codex_alpha"}',
        b'{"version":1,"started_at":',
    ],
    ids=[
        "signed-missing-version",
        "signed-unsupported-version",
        "signed-naive-timestamp",
        "signed-malformed-json",
    ],
)
def test_run_history_rejects_signed_invalid_cursor_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: bytes,
) -> None:
    monkeypatch.setenv("WILQ_CODEX_RUN_HISTORY_CURSOR_SECRET", "test-run-history-key")
    state_path = tmp_path / "codex_history_signed_invalid_cursor.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))

    response = _get(
        "/api/codex/run-history",
        params={"cursor": _signed_cursor_payload(payload)},
    )

    assert response.status_code == 422
    assert not state_path.exists()


def test_codex_run_detail_round_trips_exactly_and_reads_do_not_mutate_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "codex_run_detail.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    store = LocalStateStore(state_path)
    exact_run = CodexRun(
        id="codex_exact_detail",
        skill="wilq-content-operator",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="failed",
        model="gpt-5.6-sol",
        model_reasoning_effort="ultra",
        prompt_digest="a" * 64,
        prompt_template_id="content_initial_draft@v2",
        token_usage_input=1200,
        token_usage_output=451,
        cost_estimate_pln=1.2345,
        used_endpoints=["/api/content/work-items/exact/initial-draft"],
        evidence_ids=["ev_exact"],
        source_material_ids=["source_exact"],
        action_ids=["action_exact"],
        proposal_id="proposal_exact",
        planning_digest="b" * 64,
        planning_input_digest="c" * 64,
        initial_draft_context_digest="d" * 64,
        initial_draft_base_revision_id="revision_exact",
        started_at=datetime(2026, 8, 22, 8, 0, tzinfo=UTC),
        deadline_at=datetime(2026, 8, 22, 8, 5, tzinfo=UTC),
        completed_at=datetime(2026, 8, 22, 8, 1, tzinfo=UTC),
        error="opaque_failure_trace",
    )
    store.save_codex_run(exact_run)
    before_reads = _state_rows(state_path)

    detail_response = _get(f"/api/codex/runs/{exact_run.id}")
    missing_response = _get("/api/codex/runs/codex_missing_detail")
    history_response = _get("/api/codex/run-history")

    assert detail_response.status_code == 200
    assert detail_response.json() == exact_run.model_dump(mode="json")
    assert missing_response.status_code == 404
    assert missing_response.json() == {
        "type": "codex_run_not_found",
        "code": "codex_run_not_found",
        "run_id": "codex_missing_detail",
    }
    assert history_response.status_code == 200
    assert _state_rows(state_path) == before_reads


def test_legacy_full_run_list_remains_available_with_deprecation_header(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "legacy_codex_runs.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    expected = LocalStateStore(state_path).save_codex_run(
        CodexRun(id="codex_legacy_reader", status="started")
    )

    response = _get("/api/codex/runs")

    assert response.status_code == 200
    assert response.headers["Deprecation"] == "true"
    assert response.json() == [expected.model_dump(mode="json")]
