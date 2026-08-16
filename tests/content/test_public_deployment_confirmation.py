from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_public_deployment as deployment_router
from wilq.content.measurement.deployment import (
    ContentPublicDeployment,
    ContentPublicDeploymentConfirmationCommand,
    confirm_public_deployment,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.store.store_public_deployment import (
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
        revision_digest=revision.content_digest,
    ) == saved

    with pytest.raises(ValueError, match="Nie znaleziono potwierdzonego odczytu"):
        confirm_public_deployment(
            revision=revision,
            command=command.model_copy(update={"wordpress_post_id": "other"}),
            publication_facts=[publication],
            now=datetime(2026, 7, 26, 10, tzinfo=UTC),
        )

    for dimensions in [
        {**publication.dimensions, "status": "draft"},
        {**publication.dimensions, "content_url": "https://ekologus.dev.proudsite.pl/bdo/"},
    ]:
        with pytest.raises(ValueError):
            confirm_public_deployment(
                revision=revision,
                command=command,
                publication_facts=[publication.model_copy(update={"dimensions": dimensions})],
                now=datetime(2026, 7, 26, 10, tzinfo=UTC),
            )

    with pytest.raises(ValueError, match="bezpieczny publiczny adres"):
        confirm_public_deployment(
            revision=revision.model_copy(
                update={"final_canonical_url": "https://ekologus.dev.proudsite.pl/bdo/"}
            ),
            command=command,
            publication_facts=[publication],
            now=datetime(2026, 7, 26, 10, tzinfo=UTC),
        )


def test_new_page_public_deployment_derives_its_url_only_from_selected_public_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "new-page-public-deployment.sqlite3"))
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_new_page",
        work_item_id="content_work_item_new_page",
        content_digest="a" * 64,
        document_kind="new_page",
        final_canonical_url=None,
    )
    command = ContentPublicDeploymentConfirmationCommand(
        expected_revision_digest=revision.content_digest,
        wordpress_post_id="2451",
        publication_evidence_id="ev_public_new_page",
        confirmed_by="Wilku",
    )
    public_fact = MetricFact(
        name="content_object_seen",
        value=1,
        period="2026-07-28/2026-07-28",
        source_connector="wordpress_ekologus",
        evidence_id=command.publication_evidence_id,
        dimensions={
            "object_id": command.wordpress_post_id,
            "status": "publish",
            "content_url": "https://ekologus.pl/audyt-srodowiskowy-inwestycji/",
        },
        collected_at=datetime(2026, 7, 28, 9, tzinfo=UTC),
    )

    deployment = confirm_public_deployment(
        revision=revision,
        command=command,
        publication_facts=[public_fact],
        now=datetime(2026, 7, 28, 10, tzinfo=UTC),
    )

    assert deployment.public_url == public_fact.dimensions["content_url"]
    assert deployment.publication_evidence_id == command.publication_evidence_id
    with pytest.raises(ValueError, match="Nie znaleziono potwierdzonego odczytu"):
        confirm_public_deployment(
            revision=revision,
            command=command,
            publication_facts=[
                public_fact.model_copy(
                    update={
                        "dimensions": {**public_fact.dimensions, "status": "draft"},
                    }
                )
            ],
            now=datetime(2026, 7, 28, 10, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="Nie znaleziono potwierdzonego odczytu"):
        confirm_public_deployment(
            revision=revision,
            command=command,
            publication_facts=[
                public_fact.model_copy(
                    update={
                        "dimensions": {
                            **public_fact.dimensions,
                            "content_url": "https://ekologus.dev.proudsite.pl/audyt-srodowiskowy-inwestycji/",
                        },
                    }
                )
            ],
            now=datetime(2026, 7, 28, 10, tzinfo=UTC),
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
        work_item_id=revision.work_item_id,
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
    path = (
        "/api/content/work-items/content_work_item_bdo/draft-revisions/"
        "revision_bdo/public-deployments"
    )
    request = {
        "expected_revision_digest": revision.content_digest,
        "wordpress_post_id": "1353",
        "publication_evidence_id": "ev_public_bdo",
        "confirmed_by": "operator_local_dashboard",
    }
    client = TestClient(app)

    monkeypatch.setattr(store, "list_draft_revisions", lambda *_: [])
    assert client.post(path, json=request).status_code == 404
    monkeypatch.setattr(store, "list_draft_revisions", lambda *_: [revision])
    monkeypatch.setattr(
        store,
        "load_draft_revision_review",
        lambda **_: review.model_copy(update={"revision_digest": "b" * 64}),
    )
    assert client.post(path, json=request).status_code == 409
    monkeypatch.setattr(
        store,
        "load_draft_revision_review",
        lambda **_: review.model_copy(update={"revision_id": "revision_other"}),
    )
    assert client.post(path, json=request).status_code == 409
    monkeypatch.setattr(
        store,
        "load_draft_revision_review",
        lambda **_: review.model_copy(update={"work_item_id": "other_work_item"}),
    )
    assert client.post(path, json=request).status_code == 409
    monkeypatch.setattr(store, "load_draft_revision_review", lambda **_: review)

    response = client.post(path, json=request)

    assert response.status_code == 200
    payload = response.json()["deployment"]
    assert payload["revision_digest"] == revision.content_digest
    assert payload["public_url"] == revision.final_canonical_url
    assert payload["publication_evidence_id"] == publication.evidence_id
    assert not {
        "baseline_period",
        "observation_period",
        "allowed_metrics",
        "outcome",
        "seo_score",
    } & set(payload)



def test_public_deployment_read_projects_only_exact_public_observations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "public-deployment-read.sqlite3"))
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_bdo",
        work_item_id="content_work_item_bdo",
        content_digest="a" * 64,
        final_canonical_url="https://ekologus.pl/bdo/",
    )
    review = ContentDraftRevisionReview.model_construct(
        decision="approved",
        work_item_id=revision.work_item_id,
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
        def list_metric_facts_for_content_url(
            self, *_: object, **__: object
        ) -> list[MetricFact]:
            return [
                publication,
                publication.model_copy(
                    update={
                        "evidence_id": "ev_draft_bdo",
                        "dimensions": {**publication.dimensions, "status": "draft"},
                    }
                ),
            ]

    monkeypatch.setattr(deployment_router, "metric_store", MetricStoreStub)
    save_public_deployment(
        store,
        ContentPublicDeployment.model_construct(
            deployment_id="deployment_other",
            work_item_id="content_work_item_bdo",
            revision_id="revision_other",
            revision_digest="b" * 64,
            public_url="https://ekologus.pl/other/",
            wordpress_post_id="1354",
            publication_evidence_id="ev_other",
            publication_source_connector="wordpress_ekologus",
            observed_at=datetime(2026, 7, 26, 9, tzinfo=UTC),
            confirmed_by="Wilku",
            confirmed_at=datetime(2026, 7, 26, 10, tzinfo=UTC),
        ),
    )
    client = TestClient(app)
    response = client.get(
        "/api/content/work-items/content_work_item_bdo/draft-revisions/"
        "revision_bdo/public-deployment"
    )

    assert response.status_code == 200
    assert response.json()["publication_observations"] == [
        {
            "wordpress_post_id": "1353",
            "publication_evidence_id": publication.evidence_id,
            "publication_source_connector": "wordpress_ekologus",
            "public_url": revision.final_canonical_url,
            "observed_at": "2026-07-26T09:00:00Z",
        }
    ]
    assert client.get(
        "/api/content/work-items/other/draft-revisions/revision_bdo/public-deployment"
    ).json()["deployment"] is None


def test_new_page_deployment_read_projects_only_safe_public_observations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "new-page-public-deployment-read.sqlite3"))
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_new_page",
        work_item_id="content_work_item_new_page",
        content_digest="a" * 64,
        document_kind="new_page",
        final_canonical_url=None,
    )
    review = ContentDraftRevisionReview.model_construct(
        decision="approved",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
    )
    public_fact = MetricFact(
        name="content_object_seen",
        value=1,
        period="2026-07-28/2026-07-28",
        source_connector="wordpress_ekologus",
        evidence_id="ev_public_new_page",
        dimensions={
            "object_id": "2451",
            "status": "publish",
            "content_url": "https://ekologus.pl/audyt-srodowiskowy-inwestycji/",
        },
        collected_at=datetime(2026, 7, 28, 9, tzinfo=UTC),
    )
    store = content_workflow_store()
    monkeypatch.setattr(deployment_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(store, "list_draft_revisions", lambda *_: [revision])
    monkeypatch.setattr(store, "load_draft_revision_review", lambda **_: review)

    class MetricStoreStub:
        def list_metric_facts(self, *_: object, **__: object) -> list[MetricFact]:
            return [
                public_fact,
                public_fact.model_copy(
                    update={
                        "evidence_id": "ev_dev_new_page",
                        "dimensions": {
                            **public_fact.dimensions,
                            "content_url": "https://ekologus.dev.proudsite.pl/audyt-srodowiskowy-inwestycji/",
                        },
                    }
                ),
            ]

    monkeypatch.setattr(deployment_router, "metric_store", MetricStoreStub)
    response = TestClient(app).get(
        "/api/content/work-items/content_work_item_new_page/draft-revisions/"
        "revision_new_page/public-deployment"
    )

    assert response.status_code == 200
    assert response.json()["publication_observations"] == [
        {
            "wordpress_post_id": "2451",
            "publication_evidence_id": "ev_public_new_page",
            "publication_source_connector": "wordpress_ekologus",
            "public_url": "https://ekologus.pl/audyt-srodowiskowy-inwestycji/",
            "observed_at": "2026-07-28T09:00:00Z",
        }
    ]


def test_public_deployment_read_hides_window_with_other_deployment_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_bdo",
        work_item_id="content_work_item_bdo",
        content_digest="a" * 64,
        final_canonical_url="https://ekologus.pl/bdo/",
    )
    deployment = ContentPublicDeployment.model_construct(
        deployment_id="deployment_current",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
    )
    store = SimpleNamespace(
        list_draft_revisions=lambda _: [revision],
        load_draft_revision_review=lambda **_: ContentDraftRevisionReview.model_construct(
            decision="approved",
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
        ),
        measurement_window=lambda *_: SimpleNamespace(
            deployment_id="deployment_other",
            deployed_revision_id=revision.revision_id,
            deployed_revision_digest=revision.content_digest,
        ),
    )
    monkeypatch.setattr(deployment_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        deployment_router, "public_deployment", lambda *_args, **_kwargs: deployment
    )
    monkeypatch.setattr(
        deployment_router,
        "metric_store",
        lambda: SimpleNamespace(list_metric_facts_for_content_url=lambda *_args, **_kwargs: []),
    )

    response = deployment_router.read_content_public_deployment(
        revision.work_item_id, revision.revision_id
    )

    assert response.measurement_window is None
    assert response.measurement_outcome is None
    assert response.learning_proposal is None
