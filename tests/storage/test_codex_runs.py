from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from wilq.content.drafts import initial_draft_run
from wilq.content.drafts.initial_draft_run import _InitialDraftRunMetadata
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


def test_codex_run_round_trip_preserves_ai_trace_fields(tmp_path) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    run = CodexRun(
        id="codex_trace_test",
        skill="wilq-content-operator",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="completed",
        model="gpt-5.6-sol",
        model_reasoning_effort="xhigh",
        prompt_digest="a" * 64,
        prompt_template_id="content_initial_draft@v1",
        token_usage_input=1200,
        token_usage_output=450,
        cost_estimate_pln=1.2345,
        evidence_ids=["ev_content_trace"],
        source_material_ids=["source_material_bdo"],
    )

    saved = store.save_codex_run(run)
    loaded = store.list_codex_runs()[0]

    assert saved == run
    assert loaded.model == "gpt-5.6-sol"
    assert loaded.model_reasoning_effort == "xhigh"
    assert loaded.prompt_digest == "a" * 64
    assert loaded.prompt_template_id == "content_initial_draft@v1"
    assert loaded.token_usage_input == 1200
    assert loaded.token_usage_output == 450
    assert loaded.cost_estimate_pln == 1.2345
    assert loaded.source_material_ids == ["source_material_bdo"]


def test_get_codex_run_returns_exact_run_or_none(tmp_path) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    expected = CodexRun(
        id="codex_exact_lookup",
        status="completed",
        skill="wilq-content-operator",
        proposal_id="content_planning_proposal_exact_lookup",
    )
    store.save_codex_run(CodexRun(id="codex_other_lookup", status="failed"))
    store.save_codex_run(expected)

    assert store.get_codex_run(expected.id) == expected
    assert store.get_codex_run("codex_missing_lookup") is None


def test_codex_run_history_keyset_paginates_equal_timestamps_without_gaps(
    tmp_path,
) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    shared_started_at = datetime(2026, 8, 22, 10, 30, tzinfo=UTC)
    for run_id in ("codex_alpha", "codex_delta", "codex_bravo", "codex_charlie"):
        store.save_codex_run(
            CodexRun(
                id=run_id,
                status="completed",
                started_at=shared_started_at,
                prompt_digest="a" * 64,
                evidence_ids=[f"ev_{run_id}"],
            )
        )

    first_page = store.list_codex_run_history(limit=2)
    second_page = store.list_codex_run_history(
        limit=2,
        cursor=first_page.next_cursor,
    )

    assert [item.id for item in first_page.items] == ["codex_delta", "codex_charlie"]
    assert [item.id for item in second_page.items] == ["codex_bravo", "codex_alpha"]
    assert first_page.total_count == second_page.total_count == 4
    assert first_page.next_cursor is not None
    assert second_page.next_cursor is None
    assert {item.id for item in [*first_page.items, *second_page.items]} == {
        "codex_alpha",
        "codex_bravo",
        "codex_charlie",
        "codex_delta",
    }
    assert all("prompt_digest" not in item.model_dump() for item in first_page.items)


def test_initial_draft_run_records_exact_prompt_policy_and_materials(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(initial_draft_run, "configured_codex_model", lambda: "gpt-5.6-sol")
    monkeypatch.setattr(
        initial_draft_run,
        "configured_codex_reasoning_effort",
        lambda: "xhigh",
    )
    prompt = "Bezpieczna instrukcja pełnego szkicu do review."
    store = LocalStateStore(tmp_path / "state.sqlite3")

    run = initial_draft_run.start_initial_draft_run(
        store,
        work_item_id="content_work_item_bdo",
        evidence_ids=["ev_content_trace"],
        source_material_ids=["source_material_bdo", "source_material_bdo"],
        proposal_id="content_planning_proposal_bdo",
        planning_input_digest="b" * 64,
        planning_digest="c" * 64,
        prompt=prompt,
    )

    assert run.model == "gpt-5.6-sol"
    assert run.model_reasoning_effort == "xhigh"
    assert run.prompt_template_id == "content_initial_draft@v2"
    assert run.prompt_digest == sha256(prompt.encode("utf-8")).hexdigest()
    assert run.source_material_ids == ["source_material_bdo"]


def test_initial_draft_enrichment_redacts_before_fallback_store() -> None:
    class FallbackStore:
        def __init__(self) -> None:
            self.payload_json: str | None = None

        def save_codex_run(self, run: CodexRun) -> CodexRun:
            self.payload_json = json.dumps(run.model_dump(mode="json"))
            return run

    store = FallbackStore()
    run = CodexRun(
        id="codex_fallback_redaction",
        status="started",
        error="failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
    )

    initial_draft_run._enrich_started_initial_draft_run(
        store,
        run,
        metadata=_InitialDraftRunMetadata(
            model=None,
            model_reasoning_effort=None,
            prompt_digest="a" * 64,
            prompt_template_id="content_initial_draft@v2",
        ),
        source_material_ids=[],
    )

    assert store.payload_json is not None
    assert "sk-testsecretvalue1234567890" not in store.payload_json


def test_initial_draft_enrichment_redacts_existing_local_store_payload(tmp_path) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    run = CodexRun(
        id="codex_connect_redaction",
        status="started",
        error="failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
    )
    with store._connect() as connection:
        connection.execute(
            "INSERT INTO codex_runs (id, started_at, payload_json) VALUES (?, ?, ?)",
            (run.id, run.started_at.isoformat(), json.dumps(run.model_dump(mode="json"))),
        )

    initial_draft_run._enrich_started_initial_draft_run(
        store,
        run,
        metadata=_InitialDraftRunMetadata(
            model=None,
            model_reasoning_effort=None,
            prompt_digest="a" * 64,
            prompt_template_id="content_initial_draft@v2",
        ),
        source_material_ids=[],
    )

    stored = store.list_codex_runs()[0]
    assert stored.error == "failure with [REDACTED]"


def test_save_codex_run_redacts_caller_supplied_secret(tmp_path) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")
    run = CodexRun(
        id="codex_store_redaction",
        status="started",
        error="failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
    )

    saved = store.save_codex_run(run)

    assert saved.error == "failure with [REDACTED]"
    assert "sk-testsecretvalue1234567890" not in json.dumps(saved.model_dump(mode="json"))
