from datetime import UTC, datetime
from pathlib import Path

from wilq.content.measurement.deployment import ContentPublicDeployment
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.store.store_public_deployment import (
    public_deployment,
    save_public_deployment,
)


def _deployment(*, revision_digest: str) -> ContentPublicDeployment:
    return ContentPublicDeployment(
        deployment_id="deployment_store_fence",
        work_item_id="content_work_item_store_fence",
        revision_id="revision_store_fence",
        revision_digest=revision_digest,
        public_url="https://ekologus.pl/store-fence/",
        wordpress_post_id="1353",
        publication_evidence_id="ev_store_fence",
        publication_source_connector="wordpress_ekologus",
        observed_at=datetime(2026, 8, 16, 8, tzinfo=UTC),
        confirmed_by="wilku",
        confirmed_at=datetime(2026, 8, 16, 9, tzinfo=UTC),
    )


def test_public_deployment_read_returns_deployment_for_matching_digest(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    store = content_workflow_store()
    deployment = _deployment(revision_digest="a" * 64)
    save_public_deployment(store, deployment)

    assert (
        public_deployment(
            store,
            work_item_id=deployment.work_item_id,
            revision_id=deployment.revision_id,
            revision_digest=deployment.revision_digest,
        )
        == deployment
    )


def test_public_deployment_read_hides_deployment_for_non_matching_digest(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    store = content_workflow_store()
    deployment = _deployment(revision_digest="a" * 64)
    save_public_deployment(store, deployment)

    assert (
        public_deployment(
            store,
            work_item_id=deployment.work_item_id,
            revision_id=deployment.revision_id,
            revision_digest="b" * 64,
        )
        is None
    )
