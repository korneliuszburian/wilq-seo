from __future__ import annotations

from datetime import date

from wilq.content.measurement.evidence import (
    load_content_measurement_facts,
    observed_metrics_from_store,
)
from wilq.content.measurement.learning import build_content_learning_proposal
from wilq.content.measurement.outcome import interpret_content_measurement_outcome
from wilq.content.measurement.window import (
    ContentMeasurementWindowBlocker,
    ContentMeasurementWindowBuildResult,
    content_measurement_window_outcome_blockers,
    mark_content_measurement_window_ready,
)
from wilq.content.workflow.contracts import (
    ContentWorkItemLearningProposalRequest,
    ContentWorkItemLearningProposalResponse,
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowRequest,
    ContentWorkItemMeasurementWindowResponse,
)
from wilq.content.workflow.store import content_workflow_store


def build_content_work_item_measurement_window_response(
    request: ContentWorkItemMeasurementWindowRequest,
) -> ContentWorkItemMeasurementWindowResponse:
    measurement_result = ContentMeasurementWindowBuildResult(
        blockers=[
            ContentMeasurementWindowBlocker(
                code="missing_publication_event",
                label="Brakuje potwierdzonego publicznego wdrożenia",
                reason=("Snapshot nie wybiera dokładnej rewizji ani potwierdzenia wdrożenia."),
                next_step=(
                    "Potwierdź publiczne wdrożenie dokładnej rewizji, a następnie "
                    "utwórz jej measurement window."
                ),
            )
        ]
    )
    updated_item = request.item
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
    window = store.measurement_window(request.work_item_id, request.measurement_window_id)
    if window is None:
        raise LookupError("Persisted measurement window is missing")
    if not all(
        [
            window.deployment_id,
            window.deployed_revision_id,
            window.deployed_revision_digest,
        ]
    ):
        raise LookupError(
            "Measurement outcome wymaga okna powiązanego z potwierdzonym publicznym wdrożeniem."
        )
    as_of = date.today()
    window = mark_content_measurement_window_ready(window, as_of=as_of)
    metric_facts = load_content_measurement_facts(window.content_url)
    observed_metrics = observed_metrics_from_store(window, metric_facts)
    outcome = interpret_content_measurement_outcome(
        window=window,
        observed_metrics=observed_metrics,
        as_of=as_of,
    )
    if outcome.status not in {"not_ready", "insufficient_data"}:
        window = window.model_copy(update={"status": "closed"})
    store.save_measurement_completion(window, outcome)
    return ContentWorkItemMeasurementOutcomeResponse(outcome=outcome)


def build_content_work_item_learning_proposal_response(
    request: ContentWorkItemLearningProposalRequest,
) -> ContentWorkItemLearningProposalResponse:
    store = content_workflow_store()
    window = store.measurement_window(request.work_item_id, request.measurement_window_id)
    outcome = store.measurement_outcome(request.work_item_id, request.measurement_window_id)
    if window is None or outcome is None:
        raise LookupError("Wskazane measurement window i outcome są wymagane")
    if not all(
        [
            window.deployment_id,
            window.deployed_revision_id,
            window.deployed_revision_digest,
        ]
    ):
        raise LookupError(
            "Wniosek z pomiaru wymaga okna powiązanego z potwierdzonym publicznym wdrożeniem."
        )
    if (
        outcome.deployment_id != window.deployment_id
        or outcome.deployed_revision_id != window.deployed_revision_id
        or outcome.deployed_revision_digest != window.deployed_revision_digest
    ):
        raise LookupError("Outcome nie odpowiada wdrożeniu wskazanego measurement window.")
    proposal = build_content_learning_proposal(window=window, outcome=outcome)
    store.save_learning_proposal(proposal)
    return ContentWorkItemLearningProposalResponse(proposal=proposal)
