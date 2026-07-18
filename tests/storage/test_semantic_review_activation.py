from pathlib import Path

import pytest

from wilq.content.workflow.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore
from wilq.storage.metric_store import DuckDbMetricStore
from wilq.storage.recovery import storage_proof
from wilq.storage.semantic_review_activation import (
    MaintenanceWindowRequired,
    activate_semantic_review_storage,
)


def _stores(tmp_path: Path) -> tuple[Path, Path]:
    state = tmp_path / "source" / "wilq.sqlite3"
    metrics = tmp_path / "source" / "wilq.duckdb"
    LocalStateStore(state).status()
    ContentWorkflowStore(state).list_draft_revisions("missing")
    DuckDbMetricStore(metrics).status()
    return state, metrics


def test_semantic_review_activation_requires_approval_and_preserves_store_proof(
    tmp_path: Path,
) -> None:
    state, metrics = _stores(tmp_path)
    before = storage_proof(state, metrics)
    with pytest.raises(MaintenanceWindowRequired):
        activate_semantic_review_storage(
            state_path=state,
            metric_path=metrics,
            backup_state_path=tmp_path / "backup" / "wilq.sqlite3",
            backup_metric_path=tmp_path / "backup" / "wilq.duckdb",
            approved_maintenance_window=False,
        )
    assert storage_proof(state, metrics) == before

    report = activate_semantic_review_storage(
        state_path=state,
        metric_path=metrics,
        backup_state_path=tmp_path / "backup" / "wilq.sqlite3",
        backup_metric_path=tmp_path / "backup" / "wilq.duckdb",
        approved_maintenance_window=True,
    )
    assert report["status"] == "activated"
    assert report["before"] == report["after"]
    assert report["table_created"] is True
