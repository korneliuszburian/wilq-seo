from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.connectors.vendor import VendorMetricFact
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
    ContentWordPressDraftPayload,
)
from wilq.content.workflow.contracts import (
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementWindowRequest,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.stage_measurement import (
    build_content_work_item_measurement_outcome_response,
    build_content_work_item_measurement_window_response,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus
from wilq.storage.metric_store import metric_store


def test_measurement_uses_bound_publication_and_server_metrics_only(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    client = TestClient(app)
    work_item_id = "content_work_item_bdo"
    content_url = "https://ekologus.pl/bdo/"
    item = ContentWorkItem(
        id=work_item_id,
        topic="BDO dla firm",
        source_public_url=content_url,
        final_canonical_url=content_url,
        intended_final_url=content_url,
        evidence_ids=["ev_reviewed_revision"],
        source_connectors=["wordpress_ekologus", "google_search_console"],
        inventory_status="resolved",
        canonical_status="resolved",
        duplicate_status="checked",
    )

    blocked = build_content_work_item_measurement_window_response(
        ContentWorkItemMeasurementWindowRequest(item=item)
    )
    assert blocked.measurement_window_result.window is None
    assert blocked.measurement_window_result.blockers[0].code == (
        "missing_publication_event"
    )
    assert client.post(
        "/api/content/work-items/learning-proposal",
        json={"work_item_id": work_item_id},
    ).status_code == 409

    content_workflow_store().save_wordpress_draft_execution(
        work_item_id,
        ContentWordPressDraftExecutionResult(
            status="created",
            mode="live",
            boundary=ContentWordPressDraftExecutionBoundary(
                live_write_enabled=True,
                live_adapter_configured=True,
            ),
            payload=ContentWordPressDraftPayload(
                title="Testowy szkic",
                content_markdown="Treść zatwierdzonego szkicu.",
                final_canonical_url=content_url,
                evidence_ids=["ev_reviewed_revision"],
            ),
            wordpress_post_id="888",
            external_write_attempted=True,
        ),
    )
    _save_fact(
        run_id="wp_publish",
        connector_id="wordpress_ekologus",
        collected_at=datetime(2026, 6, 1, 8, tzinfo=UTC),
        fact=VendorMetricFact(
            name="content_object_seen",
            value=1,
            dimensions={
                "object_id": "888",
                "content_url": content_url,
                "status": "publish",
            },
        ),
    )
    _save_fact(
        run_id="gsc_baseline",
        connector_id="google_search_console",
        collected_at=datetime(2026, 5, 31, 8, tzinfo=UTC),
        fact=VendorMetricFact(
            name="clicks",
            value=100,
            dimensions={"page": content_url},
            period="2026-05-04/2026-05-31",
            unit="clicks",
        ),
    )
    _save_fact(
        run_id="gsc_unbounded_observation",
        connector_id="google_search_console",
        collected_at=datetime(2026, 6, 28, 8, tzinfo=UTC),
        fact=VendorMetricFact(
            name="clicks",
            value=999999,
            dimensions={"page": content_url},
            unit="clicks",
        ),
    )
    _save_fact(
        run_id="gsc_segment_observation",
        connector_id="google_search_console",
        collected_at=datetime(2026, 6, 28, 8, 30, tzinfo=UTC),
        fact=VendorMetricFact(
            name="clicks",
            value=999999,
            dimensions={"page": content_url, "query": "segment nieporównywalny"},
            period="2026-06-01/2026-06-28",
            unit="clicks",
        ),
    )

    activated = build_content_work_item_measurement_window_response(
        ContentWorkItemMeasurementWindowRequest(item=item)
    )
    window = activated.measurement_window_result.window
    assert window is not None
    assert window.wordpress_post_id == "888"
    assert window.publication_evidence_id == "ev_refresh_wp_publish"
    assert window.baseline_period.model_dump(mode="json") == {
        "start": "2026-05-04",
        "end": "2026-05-31",
    }
    assert window.observation_period.model_dump(mode="json") == {
        "start": "2026-06-01",
        "end": "2026-06-28",
    }
    assert window.allowed_metrics == ["gsc_clicks"]
    content_workflow_store().save_measurement_window(window)

    caller_scheduled = client.post(
        "/api/content/work-items/measurement-window",
        json={
            "work_item_id": work_item_id,
            "baseline_period": {"start": "2098-01-01", "end": "2098-01-31"},
        },
    )
    assert caller_scheduled.status_code == 422

    caller_declared = client.post(
        "/api/content/work-items/measurement-outcome",
        json={
            "work_item_id": work_item_id,
            "as_of": "2099-01-01",
            "observed_metrics": [{"metric": "gsc_clicks", "observation_value": 999999}],
        },
    )
    assert caller_declared.status_code == 422

    unbounded = build_content_work_item_measurement_outcome_response(
        ContentWorkItemMeasurementOutcomeRequest(work_item_id=work_item_id)
    )
    assert unbounded.outcome.status == "insufficient_data"
    assert client.post(
        "/api/content/work-items/learning-proposal",
        json={"work_item_id": work_item_id},
    ).status_code == 409

    _save_fact(
        run_id="gsc_observation",
        connector_id="google_search_console",
        collected_at=datetime(2026, 6, 28, 9, tzinfo=UTC),
        fact=VendorMetricFact(
            name="clicks",
            value=130,
            dimensions={"page": content_url},
            period="2026-06-01/2026-06-28",
            unit="clicks",
        ),
    )
    measured = build_content_work_item_measurement_outcome_response(
        ContentWorkItemMeasurementOutcomeRequest(work_item_id=work_item_id)
    )
    outcome = measured.outcome
    assert outcome.status == "measured_success"
    assert outcome.evidence_ids == [
        "ev_refresh_gsc_baseline",
        "ev_refresh_gsc_observation",
    ]
    assert outcome.source_connectors == ["google_search_console"]
    assert content_workflow_store().latest_measurement_window(work_item_id) is not None
    assert content_workflow_store().latest_measurement_outcome(work_item_id) is not None

    caller_accepted = client.post(
        "/api/content/work-items/learning-proposal",
        json={"work_item_id": work_item_id, "review_status": "approved"},
    )
    assert caller_accepted.status_code == 422

    proposal_response = client.post(
        "/api/content/work-items/learning-proposal",
        json={"work_item_id": work_item_id},
    )
    assert proposal_response.status_code == 200
    proposal = proposal_response.json()["proposal"]
    assert proposal["verdict"] == "measured_success"
    assert proposal["review_status"] == "review_required"
    assert proposal["human_acceptance_required"] is True
    assert proposal["knowledge_update_allowed"] is False
    assert proposal["queue_update_allowed"] is False
    assert proposal["success_claim_allowed"] is False
    assert proposal["measurement_outcome_id"] == outcome.id
    assert set(outcome.evidence_ids) <= set(proposal["evidence_ids"])
    assert proposal["source_connectors"] == [
        "google_search_console",
        "wordpress_ekologus",
    ]
    assert content_workflow_store().latest_learning_proposal(work_item_id) is not None


def _save_fact(
    *,
    run_id: str,
    connector_id: str,
    collected_at: datetime,
    fact: VendorMetricFact,
) -> None:
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id=run_id,
            connector_id=connector_id,
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=collected_at,
            completed_at=collected_at,
            evidence_ids=[f"ev_refresh_{run_id}"],
            external_call_attempted=True,
            vendor_data_collected=True,
            summary="Synthetic publication-bound measurement proof.",
        ),
        detailed_facts=[fact],
    )
