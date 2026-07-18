from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.connectors.vendor import VendorMetricFact
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
    ContentWordPressDraftPayload,
)
from wilq.content.measurement.evidence import build_publication_bound_measurement_window
from wilq.content.measurement.outcome import ContentMeasurementOutcomeInterpretation
from wilq.content.measurement.window import ContentDateRange, ContentMeasurementWindow
from wilq.content.workflow.contracts import (
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementWindowRequest,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.stage_measurement import (
    build_content_work_item_measurement_outcome_response,
    build_content_work_item_measurement_window_response,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.metric_store import metric_store


def _execution_binding(
    *, revision_id: str, handoff_id: str, digest: str
) -> ContentDraftRevisionBinding:
    return ContentDraftRevisionBinding(
        work_item_id="content_work_item_bound_history",
        handoff_id=handoff_id,
        revision_id=revision_id,
        content_digest=digest,
        draft_package_id=f"package-{revision_id}",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        approval_decision_id=f"approval-{revision_id}",
        final_canonical_url="https://ekologus.pl/test/",
    )


def test_wordpress_execution_history_is_exactly_revision_bound_and_keeps_v1_readback(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "execution-history.sqlite3"))
    store = content_workflow_store()
    common = dict(
        status="created",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        wordpress_post_id="888",
        external_write_attempted=True,
    )
    first = ContentWordPressDraftExecutionResult(
        **common,
        revision_binding=_execution_binding(
            revision_id="revision-1",
            handoff_id="handoff-1",
            digest="1" * 64,
        ),
    )
    second_common = {**common, "wordpress_post_id": "889"}
    second = ContentWordPressDraftExecutionResult(
        **second_common,
        revision_binding=_execution_binding(
            revision_id="revision-2",
            handoff_id="handoff-2",
            digest="2" * 64,
        ),
    )
    store.save_wordpress_draft_execution(first.revision_binding.work_item_id, first)
    store.save_wordpress_draft_execution(second.revision_binding.work_item_id, second)

    assert store.latest_wordpress_draft_execution(
        "content_work_item_bound_history",
        handoff_id="handoff-1",
        revision_id="revision-1",
        revision_digest="1" * 64,
    ).wordpress_post_id == "888"
    assert store.latest_wordpress_draft_execution(
        "content_work_item_bound_history",
        handoff_id="handoff-2",
        revision_id="revision-2",
        revision_digest="2" * 64,
    ).wordpress_post_id == "889"
    assert store.latest_wordpress_draft_execution(
        "content_work_item_bound_history",
        handoff_id="handoff-1",
        revision_id="revision-2",
        revision_digest="2" * 64,
    ) is None

    legacy = ContentWordPressDraftExecutionResult(
        **{**common, "wordpress_post_id": "777"}
    )
    store.save_wordpress_draft_execution("legacy-item", legacy)
    assert store.latest_wordpress_draft_execution("legacy-item").wordpress_post_id == "777"
    assert (
        store.latest_wordpress_draft_execution("legacy-item", handoff_id="new-handoff")
        is None
    )


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
            revision_binding=ContentDraftRevisionBinding(
                work_item_id=work_item_id,
                handoff_id="handoff-bdo",
                revision_id="revision-bdo",
                content_digest="a" * 64,
                draft_package_id="package-bdo",
                draft_package_digest="b" * 64,
                planning_digest="c" * 64,
                approval_decision_id="approval-bdo",
                final_canonical_url=content_url,
            ),
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
        ContentWorkItemMeasurementWindowRequest(
            item=item,
            handoff=ContentWordPressDraftHandoff(
                id="handoff-bdo",
                work_item_id=work_item_id,
                draft_package_id="package-bdo",
                title="Testowy szkic",
                final_canonical_url=content_url,
                revision_binding=ContentDraftRevisionBinding(
                    work_item_id=work_item_id,
                    handoff_id="handoff-bdo",
                    revision_id="revision-bdo",
                    content_digest="a" * 64,
                    draft_package_id="package-bdo",
                    draft_package_digest="b" * 64,
                    planning_digest="c" * 64,
                    approval_decision_id="approval-bdo",
                    final_canonical_url=content_url,
                ),
            ),
        )
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


def test_measurement_history_is_idempotent_versioned_and_readable_by_window(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "measurement-history.sqlite3"))
    store = content_workflow_store()

    def window(window_id: str, observation_end: str) -> ContentMeasurementWindow:
        return ContentMeasurementWindow(
            id=window_id,
            work_item_id="content_work_item_history",
            content_url="https://ekologus.pl/history/",
            baseline_period=ContentDateRange(start="2026-01-01", end="2026-01-31"),
            observation_period=ContentDateRange(start="2026-02-01", end=observation_end),
            earliest_verdict_date="2026-03-01",
            allowed_metrics=["gsc_clicks"],
            source_connectors=["google_search_console"],
            evidence_ids=[f"ev_{window_id}"],
        )

    first = window("measurement_window_v1", "2026-02-28")
    second = window("measurement_window_v2", "2026-03-31")
    store.save_measurement_window(first)
    store.save_measurement_window(first)
    store.save_measurement_window(second)

    assert store.latest_measurement_window(first.work_item_id).id == second.id
    assert store.measurement_window(first.work_item_id, first.id).evidence_ids == [
        "ev_measurement_window_v1"
    ]
    assert (
        store.measurement_window(first.work_item_id, second.id).observation_period.end.isoformat()
        == "2026-03-31"
    )

    with store._connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM content_measurement_window_history"
        ).fetchone()["count"]
    assert count == 2

    closed = second.model_copy(update={"status": "closed"})
    first_outcome = ContentMeasurementOutcomeInterpretation(
        id="measurement_outcome_v2",
        work_item_id=second.work_item_id,
        measurement_window_id=second.id,
        status="insufficient_data",
        status_label="Za mało danych",
        conclusion="Jeszcze nie można ocenić.",
        confidence="none",
        safe_next_step="Zbierz dalsze dane.",
    )
    second_outcome = first_outcome.model_copy(
        update={
            "status": "measured_success",
            "status_label": "Sygnał pozytywny",
            "conclusion": "Wynik wymaga review.",
            "confidence": "medium",
        }
    )
    store.save_measurement_completion(closed, first_outcome)
    store.save_measurement_completion(closed, second_outcome)
    assert store.measurement_outcome(second.work_item_id, second.id).status == "measured_success"
    with store._connect() as connection:
        outcome_count = connection.execute(
            "SELECT COUNT(*) AS count FROM content_measurement_outcome_history"
        ).fetchone()["count"]
    assert outcome_count == 2


def test_measurement_rejects_functional_query_and_path_only_fallback() -> None:
    content_url = "https://www.ekologus.pl/oferta/?service=outsourcing"
    item = ContentWorkItem(
        id="content_work_item_outsourcing",
        topic="Outsourcing środowiskowy",
        source_public_url=content_url,
        final_canonical_url=content_url,
        intended_final_url=content_url,
        evidence_ids=["ev_revision"],
        source_connectors=["wordpress_ekologus", "google_search_console"],
        inventory_status="resolved",
        canonical_status="resolved",
        duplicate_status="checked",
    )
    execution = ContentWordPressDraftExecutionResult(
        status="created",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        payload=ContentWordPressDraftPayload(
            title="Outsourcing środowiskowy",
            content_markdown="Treść.",
            final_canonical_url=content_url,
            evidence_ids=["ev_revision"],
        ),
        wordpress_post_id="999",
        external_write_attempted=True,
    )
    publication = _direct_fact(
        connector="wordpress_ekologus",
        name="content_object_seen",
        value=1,
        evidence_id="ev_refresh_wp",
        dimensions={
            "object_id": "999",
            "content_url": content_url,
            "status": "publish",
        },
    )
    unsafe_result = build_publication_bound_measurement_window(
        item=item,
        handoff=None,
        execution=execution,
        metric_facts=[
            publication,
            _direct_fact(
                connector="google_search_console",
                name="clicks",
                value=500,
                evidence_id="ev_wrong_variant",
                dimensions={
                    "page": "https://www.ekologus.pl/oferta/?service=audyt"
                },
            ),
            _direct_fact(
                connector="google_analytics_4",
                name="sessions",
                value=200,
                evidence_id="ev_path_only",
                dimensions={"landing_page_plus_query_string": "/oferta/?service=outsourcing"},
            ),
        ],
    )

    assert unsafe_result.window is None
    assert [blocker.code for blocker in unsafe_result.blockers] == [
        "missing_metric_evidence"
    ]

    conflicting_dimensions = build_publication_bound_measurement_window(
        item=item,
        handoff=None,
        execution=execution,
        metric_facts=[
            publication,
            _direct_fact(
                connector="google_search_console",
                name="clicks",
                value=900,
                evidence_id="ev_conflicting_dimensions",
                dimensions={
                    "page": content_url,
                    "landing_page": "https://www.ekologus.pl/oferta/?service=audyt",
                },
            ),
        ],
    )

    assert conflicting_dimensions.window is None
    assert [blocker.code for blocker in conflicting_dimensions.blockers] == [
        "missing_metric_evidence"
    ]

    safe_result = build_publication_bound_measurement_window(
        item=item,
        handoff=None,
        execution=execution,
        metric_facts=[
            publication,
            _direct_fact(
                connector="google_search_console",
                name="clicks",
                value=50,
                evidence_id="ev_tracking_only",
                dimensions={"page": f"{content_url}&utm_source=search"},
            ),
        ],
    )

    assert safe_result.window is not None
    assert safe_result.window.allowed_metrics == ["gsc_clicks"]


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


def _direct_fact(
    *,
    connector: str,
    name: str,
    value: int,
    evidence_id: str,
    dimensions: dict[str, str],
) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period="2026-05-04/2026-05-31",
        source_connector=connector,
        evidence_id=evidence_id,
        dimensions=dimensions,
        collected_at=datetime(2026, 6, 1, 8, tzinfo=UTC),
    )


def test_unbound_legacy_execution_cannot_unlock_measurement_window(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "legacy-execution.sqlite3"))
    work_item_id = "content_work_item_legacy_execution"
    content_url = "https://ekologus.pl/legacy/"
    item = ContentWorkItem(
        id=work_item_id,
        topic="Stary draft",
        source_public_url=content_url,
        final_canonical_url=content_url,
        intended_final_url=content_url,
        evidence_ids=["ev_legacy"],
        source_connectors=["wordpress_ekologus"],
        inventory_status="resolved",
        canonical_status="resolved",
        duplicate_status="checked",
    )
    content_workflow_store().save_wordpress_draft_execution(
        work_item_id,
        ContentWordPressDraftExecutionResult(
            status="created",
            mode="live",
            boundary=ContentWordPressDraftExecutionBoundary(
                live_write_enabled=True,
                live_adapter_configured=True,
            ),
            wordpress_post_id="777",
            external_write_attempted=True,
        ),
    )

    response = build_content_work_item_measurement_window_response(
        ContentWorkItemMeasurementWindowRequest(item=item)
    )

    assert response.measurement_window_result.window is None
    assert response.measurement_window_result.blockers[0].code == (
        "missing_publication_event"
    )
