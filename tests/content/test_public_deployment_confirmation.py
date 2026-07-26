from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_public_deployment as deployment_router
from wilq.content.measurement.deployment import (
    ContentPublicDeploymentConfirmationCommand,
    confirm_public_deployment,
)
from wilq.content.workflow.revisions import ContentDraftRevision, ContentDraftRevisionReview
from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.store_public_deployment import (
    public_deployment,
    save_public_deployment,
)
from wilq.schemas import MetricFact


def test_public_deployment_requires_the_exact_observed_public_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "public-deployment.sqlite3"))
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_bdo",
        work_item_id="content_work_item_bdo",
        content_digest="a" * 64,
        final_canonical_url="https://ekologus.pl/bdo/",
    )
    command = ContentPublicDeploymentConfirmationCommand(
        expected_revision_digest="a" * 64,
        wordpress_post_id="1353",
        publication_evidence_id="ev_public_bdo",
        confirmed_by="operator_local_dashboard",
    )
    publication = MetricFact(
        name="content_object_seen",
        value=1,
        period="2026-07-26/2026-07-26",
        source_connector="wordpress_ekologus",
        evidence_id="ev_public_bdo",
        dimensions={
            "object_id": "1353",
            "status": "publish",
            "content_url": "https://ekologus.pl/bdo/",
        },
        collected_at=datetime(2026, 7, 26, 9, tzinfo=UTC),
    )

    deployment = confirm_public_deployment(
        revision=revision,
        command=command,
        publication_facts=[publication],
        now=datetime(2026, 7, 26, 10, tzinfo=UTC),
    )
    store = content_workflow_store()
    saved = save_public_deployment(store, deployment)

    assert saved.revision_id == revision.revision_id
    assert saved.revision_digest == revision.content_digest
    assert saved.public_url == revision.final_canonical_url
    assert saved.wordpress_post_id == "1353"
    assert saved.publication_evidence_id == "ev_public_bdo"
    assert public_deployment(
        store,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
    ) == saved

    with pytest.raises(ValueError, match="Nie znaleziono potwierdzonego odczytu"):
        confirm_public_deployment(
            revision=revision,
            command=command.model_copy(update={"wordpress_post_id": "other"}),
            publication_facts=[publication],
            now=datetime(2026, 7, 26, 10, tzinfo=UTC),
        )


def test_public_deployment_api_requires_an_approved_exact_revision_and_public_fact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "public-deployment-api.sqlite3"))
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_bdo",
        work_item_id="content_work_item_bdo",
        content_digest="a" * 64,
        final_canonical_url="https://ekologus.pl/bdo/",
    )
    review = ContentDraftRevisionReview.model_construct(
        decision="approved",
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
    )
    publication = MetricFact(
        name="content_object_seen",
        value=1,
        period="2026-07-26/2026-07-26",
        source_connector="wordpress_ekologus",
        evidence_id="ev_public_bdo",
        dimensions={
            "object_id": "1353",
            "status": "publish",
            "content_url": revision.final_canonical_url,
        },
        collected_at=datetime(2026, 7, 26, 9, tzinfo=UTC),
    )
    store = content_workflow_store()
    monkeypatch.setattr(deployment_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(store, "list_draft_revisions", lambda *_: [revision])
    monkeypatch.setattr(store, "load_draft_revision_review", lambda **_: review)
    class MetricStoreStub:
        def list_metric_facts_by_evidence_ids(self, _: list[str]) -> list[MetricFact]:
            return [publication]

    monkeypatch.setattr(deployment_router, "metric_store", MetricStoreStub)

    response = TestClient(app).post(
        "/api/content/work-items/content_work_item_bdo/draft-revisions/revision_bdo/public-deployments",
        json={
            "expected_revision_digest": revision.content_digest,
            "wordpress_post_id": "1353",
            "publication_evidence_id": "ev_public_bdo",
            "confirmed_by": "operator_local_dashboard",
        },
    )

    assert response.status_code == 200
    payload = response.json()["deployment"]
    assert payload["revision_digest"] == revision.content_digest
    assert payload["public_url"] == revision.final_canonical_url
    assert payload["publication_evidence_id"] == publication.evidence_id
