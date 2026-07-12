from __future__ import annotations

from wilq.content.measurement.outcome import interpret_content_measurement_outcome
from wilq.content.measurement.window import (
    apply_content_measurement_window_to_work_item,
    build_content_measurement_window,
    content_measurement_window_outcome_blockers,
)
from wilq.content.workflow.contracts import (
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowRequest,
    ContentWorkItemMeasurementWindowResponse,
)


def build_content_work_item_measurement_window_response(
    request: ContentWorkItemMeasurementWindowRequest,
) -> ContentWorkItemMeasurementWindowResponse:
    measurement_result = build_content_measurement_window(
        item=request.item,
        handoff=request.handoff,
        baseline_period=request.baseline_period,
        observation_period=request.observation_period,
        allowed_metrics=request.allowed_metrics,
        source_connectors=request.source_connectors,
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
    return ContentWorkItemMeasurementOutcomeResponse(
        outcome=interpret_content_measurement_outcome(
            window=request.window,
            observed_metrics=request.observed_metrics,
            as_of=request.as_of,
        )
    )
