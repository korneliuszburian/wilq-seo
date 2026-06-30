from __future__ import annotations

from datetime import date

from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.measurement.window import (
    ContentDateRange,
    apply_content_measurement_window_to_work_item,
    build_content_measurement_window,
    content_measurement_window_outcome_allowed,
    content_measurement_window_outcome_blockers,
    mark_content_measurement_window_ready,
)
from wilq.content.workflow.models import (
    ContentWorkItem,
    content_workflow_action_allowed,
    content_workflow_blockers,
)


def _item(**overrides: object) -> ContentWorkItem:
    payload: dict[str, object] = {
        "id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "duplicate_status": "checked",
        "preflight_status": "handoff_allowed",
        "preserve_first_plan_status": "approved",
        "sales_brief_status": "approved",
        "sales_brief_id": "sales_brief_bdo",
        "claim_ledger_status": "approved",
        "claim_ledger_id": "claim_ledger_bdo",
        "draft_package_status": "ready",
        "draft_package_id": "draft_package_bdo",
        "human_review_status": "approved",
        "human_review_id": "human_review_bdo",
        "audit_status": "recorded",
        "audit_id": "audit_bdo",
    }
    payload.update(overrides)
    return ContentWorkItem(**payload)


def _handoff() -> ContentWordPressDraftHandoff:
    return ContentWordPressDraftHandoff(
        id="wordpress_draft_handoff_bdo",
        work_item_id="content_work_item_bdo",
        draft_package_id="draft_package_bdo",
        human_review_id="human_review_bdo",
        audit_id="audit_bdo",
        title="BDO dla firm: co sprawdzić",
        final_canonical_url="https://ekologus.pl/bdo/",
        intended_final_url="https://ekologus.pl/bdo/",
        preview_url="https://ekologus.dev.proudsite.pl/bdo/",
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
    )


def _baseline() -> ContentDateRange:
    return ContentDateRange(start=date(2026, 5, 1), end=date(2026, 5, 31))


def _observation() -> ContentDateRange:
    return ContentDateRange(start=date(2026, 7, 1), end=date(2026, 7, 31))


def test_measurement_window_requires_public_url_metrics_and_sources() -> None:
    result = build_content_measurement_window(
        item=_item(final_canonical_url=None, canonical_status="missing"),
        handoff=None,
        baseline_period=_baseline(),
        observation_period=_observation(),
        allowed_metrics=[],
        source_connectors=[],
    )

    assert result.window is None
    assert {blocker.code for blocker in result.blockers} == {
        "missing_final_canonical",
        "missing_allowed_metrics",
        "missing_source_connector",
    }


def test_measurement_window_attaches_to_handoff_and_blocks_early_outcome_claim() -> None:
    result = build_content_measurement_window(
        item=_item(),
        handoff=_handoff(),
        baseline_period=_baseline(),
        observation_period=_observation(),
        allowed_metrics=["gsc_clicks", "gsc_impressions", "ga4_engaged_sessions"],
        source_connectors=["google_search_console", "google_analytics_4"],
    )
    assert result.window is not None

    item_with_window = apply_content_measurement_window_to_work_item(_item(), result.window)

    assert result.window.status == "planned"
    assert result.window.handoff_id == "wordpress_draft_handoff_bdo"
    assert result.window.earliest_verdict_date == date(2026, 8, 1)
    assert result.window.success_claim_allowed is False
    assert "measurement_window_not_ready" in [
        blocker.code
        for blocker in content_workflow_blockers(item_with_window, "claim_measurement_outcome")
    ]


def test_measurement_window_allows_outcome_claim_only_after_ready_date() -> None:
    result = build_content_measurement_window(
        item=_item(),
        handoff=_handoff(),
        baseline_period=_baseline(),
        observation_period=_observation(),
        allowed_metrics=["gsc_clicks"],
        source_connectors=["google_search_console"],
    )
    assert result.window is not None

    too_early = mark_content_measurement_window_ready(result.window, as_of=date(2026, 7, 31))
    ready = mark_content_measurement_window_ready(result.window, as_of=date(2026, 8, 1))

    assert content_measurement_window_outcome_allowed(too_early, as_of=date(2026, 7, 31)) is False
    assert [blocker.code for blocker in content_measurement_window_outcome_blockers(too_early)] == [
        "measurement_window_not_ready"
    ]
    assert ready.status == "ready_for_review"
    assert ready.success_claim_allowed is True
    assert content_measurement_window_outcome_allowed(ready, as_of=date(2026, 8, 1))


def test_wordpress_handoff_requires_or_schedules_measurement_window() -> None:
    item_without_window = _item(measurement_window_status="missing", measurement_window_id=None)
    result = build_content_measurement_window(
        item=item_without_window,
        handoff=_handoff(),
        baseline_period=_baseline(),
        observation_period=_observation(),
        allowed_metrics=["gsc_clicks"],
        source_connectors=["google_search_console"],
    )
    assert result.window is not None

    item_with_window = apply_content_measurement_window_to_work_item(
        item_without_window,
        result.window,
    )

    assert "missing_measurement_window" in [
        blocker.code
        for blocker in content_workflow_blockers(
            item_without_window,
            "create_wordpress_draft",
        )
    ]
    assert content_workflow_action_allowed(item_with_window, "create_wordpress_draft")
