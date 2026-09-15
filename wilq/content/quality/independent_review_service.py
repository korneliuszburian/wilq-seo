"""Record independent advisory reviews only after exact deterministic gates."""

from __future__ import annotations

from typing import Literal, cast

from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    build_content_planning_input,
)
from wilq.content.quality.deterministic_revision_gate import deterministic_gate_for_snapshot
from wilq.content.quality.independent_review_contracts import (
    ContentIndependentFindingDispositionRequest,
    ContentIndependentFindingDispositionResponse,
    ContentIndependentReviewBlocker,
    ContentIndependentReviewBlockerCode,
    ContentIndependentReviewRun,
    ContentIndependentReviewRunResponse,
)
from wilq.content.quality.independent_review_store import (
    ContentIndependentReviewStore,
    IndependentReviewConflict,
    IndependentReviewDispositionResult,
)
from wilq.content.quality.review_packet_binding import (
    ContentReviewInputResolution,
    ContentReviewInputs,
    ReviewSnapshotLoader,
    resolve_content_review_inputs,
)
from wilq.content.quality.review_packet_binding import (
    same_content_review_inputs as _same_review_inputs,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.store.store import content_workflow_store
from wilq.security.redaction import redact_mapping

_INDEPENDENT_REVIEW_BLOCKER_CODES = frozenset(
    {
        "missing_revision",
        "stale_revision",
        "legacy_revision",
        "stale_content_context",
        "missing_planning_input",
        "planning_digest_mismatch",
        "research_packet_missing",
        "research_packet_blocked",
        "research_packet_conflict",
    }
)


def persist_independent_review_run(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    expected_revision_digest: str,
    run: ContentIndependentReviewRun,
    store: ContentIndependentReviewStore,
    snapshot_loader: ReviewSnapshotLoader | None = None,
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
    context = _resolve_review_context(
        snapshot=snapshot,
        revision_id=revision_id,
        expected_revision_digest=expected_revision_digest,
        snapshot_loader=snapshot_loader,
    )
    revision, planning_input, proposal, resolved_inputs = context
    _validate_planning_context(
        revision=revision,
        planning_input=planning_input,
        proposal=proposal,
        resolved_inputs=resolved_inputs,
    )
    gate = deterministic_gate_for_snapshot(
        snapshot=snapshot,
        revision=revision,
        planning_input=planning_input,
        planning_proposal=proposal,
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
    if resolved_inputs is not None:
        run = _bind_run_packet(run, resolved_inputs)
        _revalidate_before_independent_persistence(
            snapshot=snapshot,
            revision_id=revision_id,
            expected_revision_digest=expected_revision_digest,
            initial=resolved_inputs,
            snapshot_loader=snapshot_loader,
        )
    elif run.research_packet_id is not None or run.research_packet_digest is not None:
        raise IndependentReviewConflict(
            "Independent review run cannot claim a packet absent from its exact revision."
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
        research_packet_id=persisted_run.research_packet_id,
        research_packet_digest=persisted_run.research_packet_digest,
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
        research_packet_id=result.run.research_packet_id,
        research_packet_digest=result.run.research_packet_digest,
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


def _resolve_packet_bound_context(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    expected_revision_digest: str,
    snapshot_loader: ReviewSnapshotLoader | None,
) -> ContentReviewInputResolution | None:
    revision = snapshot.revision_workspace.latest_revision
    planning = snapshot.planning_workspace
    proposal = None if planning is None else getattr(planning, "proposal", None)
    if revision is None:
        return None
    packet_fields = (
        revision.research_packet_id,
        revision.research_packet_digest,
        None if proposal is None else getattr(proposal, "research_packet_id", None),
        None if proposal is None else getattr(proposal, "research_packet_digest", None),
    )
    if not any(field is not None for field in packet_fields):
        return None
    return resolve_content_review_inputs(
        snapshot=snapshot,
        revision_id=revision_id,
        expected_revision_digest=expected_revision_digest,
        workflow_store=content_workflow_store(),
        snapshot_loader=snapshot_loader,
        planning_input_builder=build_content_planning_input,
    )


def _resolve_review_context(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    expected_revision_digest: str,
    snapshot_loader: ReviewSnapshotLoader | None,
) -> tuple[
    ContentDraftRevision,
    ContentPlanningInput,
    ContentPlanningProposal,
    ContentReviewInputs | None,
]:
    revision = snapshot.revision_workspace.latest_revision
    planning = snapshot.planning_workspace
    if revision is None or planning is None:
        blocker = ContentIndependentReviewBlocker(
            code="missing_planning_input",
            label="Brakuje aktualnego wejścia strategicznego",
            reason="Niezależny review wymaga bieżącego planning workspace.",
            next_step="Odśwież albo wygeneruj aktualny plan przed review.",
        )
        raise IndependentReviewConflict(blocker.next_step, blocker=blocker)
    proposal = getattr(planning, "proposal", None)
    if proposal is None:
        blocker = ContentIndependentReviewBlocker(
            code="missing_planning_input",
            label="Brakuje aktualnego wejścia strategicznego",
            reason="Niezależny review wymaga zapisanego proposal.",
            next_step="Odśwież albo wygeneruj aktualny plan przed review.",
        )
        raise IndependentReviewConflict(blocker.next_step, blocker=blocker)
    resolution = _resolve_packet_bound_context(
        snapshot=snapshot,
        revision_id=revision_id,
        expected_revision_digest=expected_revision_digest,
        snapshot_loader=snapshot_loader,
    )
    if resolution is not None:
        if resolution.blocker is not None:
            raise IndependentReviewConflict(
                resolution.blocker.next_step,
                blocker=_independent_binding_blocker(resolution),
            )
        if resolution.inputs is None:
            raise IndependentReviewConflict("Independent review context is incomplete.")
        inputs = resolution.inputs
        return inputs.revision, inputs.planning_input, inputs.proposal, inputs
    result = build_content_planning_input(
        snapshot,
        service_card_id=getattr(proposal, "service_card_id", None),
    )
    if result.planning_input is None or result.blockers:
        blocker = _independent_planning_blocker(result)
        raise IndependentReviewConflict(blocker.next_step, blocker=blocker)
    return revision, result.planning_input, proposal, None


def _validate_planning_context(
    *,
    revision: ContentDraftRevision,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    resolved_inputs: ContentReviewInputs | None,
) -> None:
    if planning_input.planning_input_digest != revision.planning_input_digest:
        raise IndependentReviewConflict(
            "Independent review planning input is stale or incomplete."
        )
    if resolved_inputs is None:
        return
    if (
        proposal.planning_input_digest != revision.planning_input_digest
        or proposal.planning_digest != revision.planning_digest
    ):
        raise IndependentReviewConflict(
            "Independent review proposal and revision planning digests are not exact."
        )


def _revalidate_before_independent_persistence(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    expected_revision_digest: str,
    initial: ContentReviewInputs,
    snapshot_loader: ReviewSnapshotLoader | None,
) -> None:
    repeated = _resolve_packet_bound_context(
        snapshot=snapshot,
        revision_id=revision_id,
        expected_revision_digest=expected_revision_digest,
        snapshot_loader=snapshot_loader,
    )
    if repeated is None:
        raise IndependentReviewConflict("Independent review context changed before persistence.")
    if repeated.blocker is not None:
        raise IndependentReviewConflict(
            repeated.blocker.next_step,
            blocker=_independent_binding_blocker(repeated),
        )
    if repeated.inputs is None or not _same_review_inputs(initial, repeated.inputs):
        raise IndependentReviewConflict("Independent review context changed before persistence.")


def _bind_run_packet(
    run: ContentIndependentReviewRun,
    inputs: ContentReviewInputs,
) -> ContentIndependentReviewRun:
    packet = inputs.packet
    if packet is None:
        if run.research_packet_id is not None or run.research_packet_digest is not None:
            raise _packet_conflict()
        return run
    if (
        run.research_packet_id is not None
        and (
            run.research_packet_id != packet.packet_id
            or run.research_packet_digest != packet.packet_digest
        )
    ):
        raise _packet_conflict()
    return run.model_copy(
        update={
            "research_packet_id": packet.packet_id,
            "research_packet_digest": packet.packet_digest,
        }
    )


def _independent_binding_blocker(
    resolution: ContentReviewInputResolution,
) -> ContentIndependentReviewBlocker:
    blocker = resolution.blocker
    if blocker is None:
        raise RuntimeError("Independent binding blocker is missing.")
    code = (
        blocker.code
        if blocker.code in _INDEPENDENT_REVIEW_BLOCKER_CODES
        else "missing_planning_input"
    )
    return ContentIndependentReviewBlocker(
        code=cast(ContentIndependentReviewBlockerCode, code),
        label=blocker.label,
        reason=blocker.reason,
        next_step=blocker.next_step,
        source_codes=list(blocker.source_codes),
    )


def resolve_independent_review_context(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    expected_revision_digest: str,
    snapshot_loader: ReviewSnapshotLoader | None = None,
) -> ContentReviewInputResolution | None:
    """Resolve packet context for read routes without any review write."""

    return _resolve_packet_bound_context(
        snapshot=snapshot,
        revision_id=revision_id,
        expected_revision_digest=expected_revision_digest,
        snapshot_loader=snapshot_loader,
    )


def independent_review_binding_blocker(
    resolution: ContentReviewInputResolution,
) -> ContentIndependentReviewBlocker:
    return _independent_binding_blocker(resolution)


def _independent_planning_blocker(
    result: object,
) -> ContentIndependentReviewBlocker:
    raw_blockers = list(getattr(result, "blockers", []))
    raw = raw_blockers[0] if raw_blockers else None
    raw_code = "" if raw is None else str(getattr(raw, "code", ""))
    code_map = {
        "wordpress_material_review_required": "missing_planning_input",
        "stale_planning_sources": "stale_content_context",
        "blocked_planning_sources": "missing_planning_input",
    }
    mapped = code_map.get(raw_code, raw_code)
    code = (
        mapped
        if mapped in _INDEPENDENT_REVIEW_BLOCKER_CODES
        else "missing_planning_input"
    )
    label = (
        "Brakuje aktualnego wejścia strategicznego"
        if raw is None
        else str(getattr(raw, "label", "Brakuje aktualnego wejścia strategicznego"))
    )
    reason = (
        "Wejście planowania niezależnego review jest nieaktualne lub niekompletne."
        if raw is None
        else str(getattr(raw, "reason", "Planning input ma typed blocker przed review."))
    )
    next_step = (
        "Odśwież albo wygeneruj aktualny plan przed review."
        if raw is None
        else str(getattr(raw, "next_step", "Odśwież albo wygeneruj aktualny plan przed review."))
    )
    source_codes = [] if raw is None else [raw_code]
    return ContentIndependentReviewBlocker(
        code=cast(ContentIndependentReviewBlockerCode, code),
        label=label,
        reason=reason,
        next_step=next_step,
        source_codes=source_codes,
    )


def _packet_conflict() -> IndependentReviewConflict:
    blocker = ContentIndependentReviewBlocker(
        code="research_packet_conflict",
        label="Review packet nie odpowiada exact revision",
        reason=(
            "Nadesłany independent review wskazuje inny packet ID albo digest "
            "niż bieżąca revision."
        ),
        next_step="Wyślij wynik dla tego samego exact packetu albo uruchom nowy review.",
    )
    return IndependentReviewConflict(blocker.next_step, blocker=blocker)


__all__ = [
    "persist_independent_review_run",
    "independent_review_binding_blocker",
    "record_independent_finding_disposition",
    "resolve_independent_review_context",
]
