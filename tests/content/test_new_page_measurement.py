from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.api.wilq_api.routers import content_workflow as workflow_router
from wilq.content.measurement.deployment import ContentPublicDeployment
from wilq.content.workflow.contracts import ContentWorkItemMeasurementCommand
from wilq.content.workflow.new_page import ContentNewPageDocumentIdentity
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.store_public_deployment import save_public_deployment
from wilq.schemas import MetricFact


def test_new_page_measurement_uses_persisted_deployment_without_a_diagnostics_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "new-page-measurement.sqlite3"))
    store = content_workflow_store()
    work_item_id = "content_work_item_new_page_measurement"
    revision = ContentDraftRevision.model_construct(
        revision_id="revision_new_page_measurement",
        work_item_id=work_item_id,
        content_digest="b" * 64,
        title="Dokumentacja środowiskowa inwestycji",
        document_kind="new_page",
        final_canonical_url=None,
        new_page_document_identity=ContentNewPageDocumentIdentity(
            work_item_id=work_item_id,
            brief_id="content_new_page_brief_measurement",
            brief_digest="c" * 64,
            foundation_id="content_new_page_foundation_measurement",
            service_card_id="service_environment",
            service_card_digest="d" * 64,
            proposed_ia_location="Usługi → Dokumentacja środowiskowa",
        ),
    )
    deployment = ContentPublicDeployment(
        deployment_id="deployment_new_page_measurement",
        work_item_id=work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        public_url="https://www.ekologus.pl/dokumentacja-srodowiskowa-inwestycji/",
        wordpress_post_id="2468",
        publication_evidence_id="ev_public_new_page",
        publication_source_connector="wordpress_ekologus",
        observed_at=datetime(2026, 6, 1, 8, tzinfo=UTC),
        confirmed_by="operator",
        confirmed_at=datetime(2026, 6, 1, 9, tzinfo=UTC),
    )
    save_public_deployment(store, deployment)
    monkeypatch.setattr(workflow_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(store, "list_draft_revisions", lambda *_: [revision])
    monkeypatch.setattr(
        workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda _: (_ for _ in ()).throw(AssertionError("measurement must not read diagnostics")),
    )
    monkeypatch.setattr(
        "wilq.content.measurement.evidence.load_content_measurement_facts",
        lambda _: [
            MetricFact(
                name="clicks",
                value=10,
                period="2026-05-04/2026-05-31",
                source_connector="google_search_console",
                evidence_id="ev_gsc_new_page",
                dimensions={"page": deployment.public_url},
                collected_at=datetime(2026, 6, 1, 10, tzinfo=UTC),
            )
        ],
    )

    response = workflow_router.content_work_item_measurement_window(
        ContentWorkItemMeasurementCommand(
            work_item_id=work_item_id,
            revision_id=revision.revision_id,
        )
    )

    assert response.measurement_window_result.window is not None
    assert response.item.id == work_item_id
    assert response.item.final_canonical_url == deployment.public_url
    assert response.updated_item.measurement_window_id == (
        "measurement_window_deployment_new_page_measurement"
    )
