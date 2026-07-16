from __future__ import annotations

from datetime import date

from wilq.content.measurement.evidence import (
    build_publication_bound_measurement_window,
    load_content_measurement_facts,
    observed_metrics_from_store,
)
from wilq.content.measurement.outcome import interpret_content_measurement_outcome
from wilq.content.measurement.window import (
    ContentMeasurementWindowBuildResult,
    apply_content_measurement_window_to_work_item,
    content_measurement_window_outcome_blockers,
    mark_content_measurement_window_ready,
)
from wilq.content.workflow.contracts import (
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowRequest,
    ContentWorkItemMeasurementWindowResponse,
)
from wilq.content.workflow.store import content_workflow_store


def build_content_work_item_measurement_window_response(
    request: ContentWorkItemMeasurementWindowRequest,
) -> ContentWorkItemMeasurementWindowResponse:
    store = content_workflow_store()
    existing = store.latest_measurement_window(request.item.id)
    measurement_result = (
        ContentMeasurementWindowBuildResult(window=existing)
        if existing is not None
        else build_publication_bound_measurement_window(
            item=request.item,
            handoff=request.handoff,
            execution=store.latest_wordpress_draft_execution(request.item.id),
            metric_facts=load_content_measurement_facts(request.item.final_canonical_url),
        )
    )
    updated_item = (
        apply_content_measurement_window_to_work_item(request.item, measurement_result.window)
        if measurement_result.window is not None
        else request.item
    )
    return ContentWorkItemMeasurementWindowResponse(
        item=request.item,
        updated_item=updated_item,
        measurement_window_result=measurement_result,
        outcome_blockers=(
            content_measurement_window_outcome_blockers(measurement_result.window)
            if measurement_result.window is not None
            else []
        ),
    )


def build_content_work_item_measurement_outcome_response(
    request: ContentWorkItemMeasurementOutcomeRequest,
) -> ContentWorkItemMeasurementOutcomeResponse:
    store = content_workflow_store()
    window = store.latest_measurement_window(request.work_item_id)
    if window is None:
        raise LookupError("Persisted measurement window is missing")
    as_of = date.today()
    window = mark_content_measurement_window_ready(window, as_of=as_of)
    metric_facts = load_content_measurement_facts(window.content_url)
    observed_metrics = observed_metrics_from_store(window, metric_facts)
    outcome = interpret_content_measurement_outcome(
        window=window,
        observed_metrics=observed_metrics,
        as_of=as_of,
    )
    store.save_measurement_window(window)
    store.save_measurement_outcome(outcome)
    return ContentWorkItemMeasurementOutcomeResponse(outcome=outcome)
