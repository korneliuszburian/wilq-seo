from __future__ import annotations

from hashlib import sha256

from wilq.content.drafts import initial_draft_run
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
    assert run.prompt_template_id == "content_initial_draft@v1"
    assert run.prompt_digest == sha256(prompt.encode("utf-8")).hexdigest()
    assert run.source_material_ids == ["source_material_bdo"]
