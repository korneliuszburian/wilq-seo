from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from wilq.content.workflow.store.store import content_workflow_store
from wilq.schemas.core import utc_now


def _seed_claim(
    path: Path,
    *,
    work_item_id: str,
    claim_key: str = "claim-1",
    claimed_at=None,
    status: str = "claimed",
) -> None:
    store = content_workflow_store()
    store.path = path
    with store._connect() as connection:
        connection.execute(
            """
            INSERT INTO content_wordpress_revision_apply_claims (
              claim_key, work_item_id, revision_id, approval_decision_id,
              action_id, status, claimed_by, claimed_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_key,
                work_item_id,
                f"revision-{claim_key}",
                f"approval-{claim_key}",
                f"action-{claim_key}",
                status,
                "operator",
                (claimed_at or utc_now()).isoformat(),
                utc_now().isoformat(),
            ),
        )


def _store(path: Path):
    store = content_workflow_store()
    store.path = path
    return store


def test_reconcile_requires_a_claim_older_than_the_recovery_window(tmp_path: Path) -> None:
    path = tmp_path / "reconcile-window.sqlite3"
    _seed_claim(path, work_item_id="window-item")
    store = _store(path)

    with pytest.raises(ValueError, match="okna recovery"):
        store.reconcile_wordpress_revision_apply_claim(
            work_item_id="window-item",
            outcome="failed",
            reconciled_by="operator",
            notes="Sprawdzono.",
        )

    path = tmp_path / "reconcile-window-expired.sqlite3"
    _seed_claim(
        path,
        work_item_id="expired-item",
        claimed_at=utc_now() - timedelta(seconds=301),
    )
    assert _store(path).reconcile_wordpress_revision_apply_claim(
        work_item_id="expired-item",
        outcome="failed",
        reconciled_by="operator",
        notes="Sprawdzono.",
    ).event_type == "action_apply_reconciled"


def test_reconcile_requires_exactly_one_claimed_row(tmp_path: Path) -> None:
    path = tmp_path / "reconcile-cardinality.sqlite3"
    _seed_claim(
        path,
        work_item_id="two-claims",
        claim_key="claim-1",
        claimed_at=utc_now() - timedelta(seconds=301),
    )
    _seed_claim(
        path,
        work_item_id="two-claims",
        claim_key="claim-2",
        claimed_at=utc_now() - timedelta(seconds=301),
    )

    with pytest.raises(ValueError, match="dokładnie jednego"):
        _store(path).reconcile_wordpress_revision_apply_claim(
            work_item_id="two-claims",
            outcome="failed",
            reconciled_by="operator",
            notes="Sprawdzono.",
        )


def test_reconcile_applied_persists_synthetic_created_execution(tmp_path: Path) -> None:
    path = tmp_path / "reconcile-created.sqlite3"
    _seed_claim(
        path,
        work_item_id="created-item",
        claimed_at=utc_now() - timedelta(seconds=301),
    )
    store = _store(path)

    store.reconcile_wordpress_revision_apply_claim(
        work_item_id="created-item",
        outcome="applied",
        reconciled_by="operator",
        notes="Szkic potwierdzony w WordPress.",
        wordpress_post_id="1275",
    )

    execution = store.latest_wordpress_draft_execution("created-item")
    assert execution is not None
    assert execution.status == "created"
    assert execution.external_write_attempted is True
    assert execution.wordpress_post_id == "1275"


def test_reconcile_cas_allows_only_one_terminal_transition(tmp_path: Path) -> None:
    path = tmp_path / "reconcile-cas.sqlite3"
    _seed_claim(
        path,
        work_item_id="cas-item",
        claimed_at=utc_now() - timedelta(seconds=301),
    )
    store = _store(path)
    kwargs = dict(
        work_item_id="cas-item",
        outcome="failed",
        reconciled_by="operator",
        notes="Sprawdzono.",
    )

    store.reconcile_wordpress_revision_apply_claim(**kwargs)
    with pytest.raises(ValueError, match="dokładnie jednego"):
        store.reconcile_wordpress_revision_apply_claim(**kwargs)


def test_reconcile_applied_requires_wordpress_post_id(tmp_path: Path) -> None:
    path = tmp_path / "reconcile-post-id.sqlite3"
    _seed_claim(
        path,
        work_item_id="missing-post-id",
        claimed_at=utc_now() - timedelta(seconds=301),
    )

    with pytest.raises(ValueError, match="ID szkicu WordPress"):
        _store(path).reconcile_wordpress_revision_apply_claim(
            work_item_id="missing-post-id",
            outcome="applied",
            reconciled_by="operator",
            notes="Brak ID.",
        )
