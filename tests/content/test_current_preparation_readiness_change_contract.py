"""Parent-safe source observer for exact current refresh preparation."""

from pathlib import Path


def _source(root: Path, relative: str) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def test_current_preparation_source_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    sources = {
        relative: _source(root, relative)
        for relative in (
            "wilq/content/workflow/current_preparation_readiness.py",
            "wilq/content/workflow/current_preparation_readiness_contracts.py",
            "wilq/content/workflow/current_preparation_readiness_support.py",
            "wilq/content/workflow/store/current_preparation_read_adapter.py",
            "wilq/content/workflow/store/store_content_kind_receipt.py",
            "wilq/content/workflow/store/store_refresh_preparation.py",
            "wilq/content/workflow/store/refresh_preparation_atomic.py",
            "wilq/content/workflow/refresh_preparation_resolution.py",
            "wilq/content/workflow/research_packet_preparation.py",
            "wilq/content/workflow/workspace/production_decision.py",
            "wilq/content/workflow/workspace/selected_workspace.py",
            "apps/api/wilq_api/routers/content_selected_workspace.py",
            "apps/api/wilq_api/routers/content_initial_draft.py",
            "apps/api/wilq_api/routers/content_initial_draft_refresh.py",
        )
    }

    assert (
        "ready_for_refresh_authorization"
        in sources["wilq/content/workflow/current_preparation_readiness_contracts.py"]
    )
    assert (
        "current_content_binding_missing"
        in sources["wilq/content/workflow/current_preparation_readiness.py"]
    )
    assert (
        "resolve_current_preparation_readiness"
        in sources["wilq/content/workflow/refresh_preparation_resolution.py"]
    )
    assert (
        "latest_source_pack_for_work_item"
        in sources["wilq/content/workflow/research_packet_preparation.py"]
    )
    assert (
        "source_packet_row_digest"
        in sources["wilq/content/workflow/workspace/production_decision.py"]
    )
    assert (
        "_validate_ready_refresh_state"
        in sources["wilq/content/workflow/workspace/selected_workspace.py"]
    )
    assert (
        "Autoryzuj bieżący refresh"
        in sources["wilq/content/workflow/workspace/selected_workspace.py"]
    )
    assert (
        "current_preparation_readiness"
        in sources["apps/api/wilq_api/routers/content_selected_workspace.py"]
    )
    initial_draft = sources["apps/api/wilq_api/routers/content_initial_draft.py"]
    submit_marker = "def _submit_initial_draft("
    canonical_marker = "def _canonical_refresh_preparation_authority()"
    assert submit_marker in initial_draft
    assert canonical_marker in initial_draft
    submit_start = initial_draft.index(submit_marker)
    submit_end = initial_draft.index(canonical_marker, submit_start)
    submit_source = initial_draft[submit_start:submit_end]
    refresh_resolve_marker = "refresh_authority.resolve_initial_draft(work_item_id, request)"
    canonical_guard_marker = (
        "resolution = (authority_resolver or _canonical_initial_draft_authority_resolver)"
    )
    assert refresh_resolve_marker in submit_source
    assert canonical_guard_marker in submit_source
    assert "isinstance(refresh_resolution, RefreshPreparationRuntimeAuthorized)" in submit_source
    refresh_resolve = submit_source.index(refresh_resolve_marker)
    canonical_guard = submit_source.index(canonical_guard_marker)
    assert refresh_resolve < canonical_guard
    refresh_submit = sources["apps/api/wilq_api/routers/content_initial_draft_refresh.py"]
    use_initial_marker = "use_initial_resolution = [True]"
    initial_guard_marker = "resolved = current[0]"
    runtime_recheck_marker = "resolved = authority.resolve_initial_draft(work_item_id, request)"
    consumed_marker = "use_initial_resolution[0] = False"
    assert use_initial_marker in refresh_submit
    assert initial_guard_marker in refresh_submit
    assert runtime_recheck_marker in refresh_submit
    assert consumed_marker in refresh_submit
    initial_guard = refresh_submit.index(initial_guard_marker)
    runtime_recheck = refresh_submit.index(runtime_recheck_marker)
    assert initial_guard < runtime_recheck
    status_marker = "def _read_initial_draft_status("
    assert status_marker in initial_draft
    status_source = initial_draft[initial_draft.index(status_marker) :]
    blocked_marker = 'classification_decision == "blocked"'
    current_blocker_marker = '("current_content_binding_missing",)'
    assert blocked_marker in status_source
    assert current_blocker_marker in status_source
    adapter = sources["wilq/content/workflow/store/current_preparation_read_adapter.py"]
    assert "TransactionBoundCurrentPreparationReadAdapter" in adapter
    assert "resolve_current_preparation_readiness_from_connection" in adapter
    assert "TransactionBoundCurrentPreparationReadAdapter(connection)" in adapter
    assert "self.connection" in adapter
    assert "_connect(" not in adapter
    assert ".commit(" not in adapter
    for relative in (
        "wilq/content/workflow/store/store_content_kind_receipt.py",
        "wilq/content/workflow/store/store_refresh_preparation.py",
        "wilq/content/workflow/store/refresh_preparation_atomic.py",
    ):
        source = sources[relative]
        assert "resolve_current_preparation_readiness_from_connection" in source
        assert "connection," in source
    assert "run=run" in sources["wilq/content/workflow/store/store_content_kind_receipt.py"]
    assert "row=row" in sources["wilq/content/workflow/store/store_content_kind_receipt.py"]
    assert "run=run" in sources["wilq/content/workflow/store/store_refresh_preparation.py"]
    assert "row=row" in sources["wilq/content/workflow/store/store_refresh_preparation.py"]
    assert (
        "run=classification" in sources["wilq/content/workflow/store/refresh_preparation_atomic.py"]
    )
    assert "row=row" in sources["wilq/content/workflow/store/refresh_preparation_atomic.py"]
