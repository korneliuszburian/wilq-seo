"""Record independent advisory reviews only after exact deterministic gates."""

from __future__ import annotations

from typing import Literal

from wilq.content.planning.dynamic_input import build_content_planning_input
from wilq.content.quality.deterministic_revision_gate import deterministic_gate_for_snapshot
from wilq.content.quality.independent_review_contracts import (
    ContentIndependentFindingDispositionRequest,
    ContentIndependentFindingDispositionResponse,
    ContentIndependentReviewRun,
    ContentIndependentReviewRunResponse,
)
from wilq.content.quality.independent_review_store import (
    ContentIndependentReviewStore,
    IndependentReviewConflict,
    IndependentReviewDispositionResult,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.security.redaction import redact_mapping


def persist_independent_review_run(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    expected_revision_digest: str,
    run: ContentIndependentReviewRun,
    store: ContentIndependentReviewStore,
) -> ContentIndependentReviewRunResponse:
    revision = snapshot.revision_workspace.latest_revision
    if revision is None or revision.revision_id != revision_id:
        raise IndependentReviewConflict("Independent review requires the current exact revision.")
    if revision.content_digest != expected_revision_digest:
        raise IndependentReviewConflict("Independent review digest is stale.")
    if run.work_item_id != revision.work_item_id or run.revision_id != revision.revision_id:
        raise IndependentReviewConflict("Independent review run identity is not exact.")
    if run.revision_digest != revision.content_digest:
        raise IndependentReviewConflict("Independent review run digest is not exact.")
    planning = snapshot.planning_workspace
    if planning is None:
        raise IndependentReviewConflict(
            "Independent review requires the current planning workspace."
        )
    planning_input_result = build_content_planning_input(
        snapshot,
        service_card_id=planning.proposal.service_card_id,
    )
    if (
        planning_input_result.planning_input is None
        or planning_input_result.blockers
        or planning_input_result.planning_input.planning_input_digest
        != revision.planning_input_digest
    ):
        raise IndependentReviewConflict("Independent review planning input is stale or incomplete.")
    gate = deterministic_gate_for_snapshot(
        snapshot=snapshot,
        revision=revision,
        planning_input=planning_input_result.planning_input,
        planning_proposal=planning.proposal,
    )
    if gate is None or gate.status != "passed":
        raise IndependentReviewConflict(
            "Deterministic gate must pass before an independent judge run."
        )
    if not run.evidence_ids or not set(run.evidence_ids).issubset(set(gate.evidence_ids)):
        raise IndependentReviewConflict(
            "Independent review evidence must belong to the exact revision gate."
        )
    if not run.source_connectors or not set(run.source_connectors).issubset(
        set(gate.source_connectors)
    ):
        raise IndependentReviewConflict(
            "Independent review connectors must belong to the exact revision gate."
        )
    if not store.write_ready():
        raise IndependentReviewConflict(
            "Independent review storage requires an approved maintenance window."
        )
    safe_run = ContentIndependentReviewRun.model_validate(
        redact_mapping(run.model_dump(mode="json"))
    )
    status = store.save_run(safe_run)
    persisted_run = store.for_run(safe_run.run_id) or safe_run
    return ContentIndependentReviewRunResponse(
        status=status,
        work_item_id=persisted_run.work_item_id,
        revision_id=persisted_run.revision_id,
        revision_digest=persisted_run.revision_digest,
        run=persisted_run,
        safe_next_step=(
            "Rozlicz każde finding exact evidence albo odłóż je do decyzji człowieka."
        ),
    )


def record_independent_finding_disposition(
    *,
    work_item_id: str,
    revision_id: str,
    run_id: str,
    finding_id: str,
    request: ContentIndependentFindingDispositionRequest,
    store: ContentIndependentReviewStore,
) -> ContentIndependentFindingDispositionResponse:
    result = store.record_disposition(
        work_item_id=work_item_id,
        revision_id=revision_id,
        run_id=run_id,
        finding_id=finding_id,
        request=request,
    )
    _require_exact_identity(result, work_item_id, revision_id)
    critical_child = (
        result.finding.severity == "critical"
        and result.finding.disposition == "accept_and_fix"
    )
    status: Literal["recorded", "idempotent", "child_revision_required"] = (
        "child_revision_required"
        if critical_child
        else result.status
    )
    return ContentIndependentFindingDispositionResponse(
        status=status,
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=result.run.revision_digest,
        run=result.run,
        finding_id=finding_id,
        requires_child_revision=critical_child,
        safe_next_step=(
            "Utwórz exact child revision na bazie tego digestu przed kolejnym review."
            if critical_child
            else "Zachowaj decyzję i przejdź do następnego findingu."
        ),
    )


def _require_exact_identity(
    result: IndependentReviewDispositionResult,
    work_item_id: str,
    revision_id: str,
) -> None:
    if result.run.work_item_id != work_item_id or result.run.revision_id != revision_id:
        raise IndependentReviewConflict("Finding disposition identity is not exact.")


__all__ = [
    "persist_independent_review_run",
    "record_independent_finding_disposition",
]
