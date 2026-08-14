from __future__ import annotations

from pathlib import Path

from wilq.content.drafts.initial_draft_run import start_initial_draft_run
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


def _start_run(
    store: LocalStateStore,
    *,
    work_item_id: str,
    **overrides: str,
) -> CodexRun:
    return start_initial_draft_run(
        store,
        work_item_id=work_item_id,
        evidence_ids=["evidence_initial_draft_run"],
        source_material_ids=["source_initial_draft_run"],
        proposal_id=f"proposal_{work_item_id}",
        planning_digest="a" * 64,
        planning_input_digest="b" * 64,
        **overrides,
    )


def test_start_initial_draft_run_supports_custom_identity_without_changing_defaults(
    tmp_path: Path,
) -> None:
    store = LocalStateStore(tmp_path / "state.sqlite3")

    custom = _start_run(
        store,
        work_item_id="new-page",
        run_id_prefix="codex_content_new_page_draft_",
        hook="content_new_page_initial_draft",
        endpoint_path="/api/content/new-page-briefs/brief-1/initial-draft",
    )
    refresh = _start_run(store, work_item_id="refresh")

    assert custom.id.startswith("codex_content_new_page_draft_")
    assert custom.hook == "content_new_page_initial_draft"
    assert custom.used_endpoints == [
        "/api/content/new-page-briefs/brief-1/initial-draft"
    ]
    assert refresh.id.startswith("codex_content_initial_draft_")
    assert refresh.hook == "content_initial_full_draft"
    assert refresh.used_endpoints == [
        "/api/content/work-items/refresh/initial-draft"
    ]
    assert {run.id for run in store.list_codex_runs()} == {custom.id, refresh.id}
