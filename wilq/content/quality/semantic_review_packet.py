"""Semantic adapters for the generic exact review-packet policy."""

from __future__ import annotations

from typing import Literal, cast

from wilq.content.operator_copy import build_blocker
from wilq.content.quality.review_packet_binding import (
    ContentReviewInputResolution,
    ContentReviewInputs,
    content_review_inputs_match_revision,
    same_content_review_inputs,
)
from wilq.content.quality.semantic_inputs import SemanticInputs
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticBlockerCode,
    ContentSemanticReview,
    ContentSemanticReviewBlocker,
    ContentSemanticReviewResponse,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevision

_SEMANTIC_BINDING_BLOCKER_CODES = frozenset(
    {
        "missing_revision",
        "stale_revision",
        "legacy_revision",
        "stale_content_context",
        "missing_planning_input",
        "source_material_review_required",
        "storage_activation_required",
        "runtime_blocked",
        "runtime_failed",
        "invalid_structured_output",
        "semantic_scope_mismatch",
        "deterministic_quality_gate_failed",
        "persistence_failed",
        "review_conflict",
        "generation_in_progress",
        "planning_digest_mismatch",
        "research_packet_missing",
        "research_packet_blocked",
        "research_packet_conflict",
    }
)


def semantic_review_response(
    status: Literal["ready", "idempotent"],
    revision: ContentDraftRevision,
    review: ContentSemanticReview,
) -> ContentSemanticReviewResponse:
    return ContentSemanticReviewResponse(
        status=status,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        research_packet_id=review.research_packet_id,
        research_packet_digest=review.research_packet_digest,
        review=review,
        run_id=review.codex_run_id,
        safe_next_step=review.safe_next_step,
    )


def semantic_binding_blocker(
    resolution: ContentReviewInputResolution,
) -> ContentSemanticReviewBlocker:
    blocker = resolution.blocker
    if blocker is None:
        raise RuntimeError("Semantic binding blocker is missing.")
    code = {
        "wordpress_material_review_required": "source_material_review_required",
        "stale_planning_sources": "stale_content_context",
        "blocked_planning_sources": "missing_planning_input",
    }.get(blocker.code, blocker.code)
    if code not in _SEMANTIC_BINDING_BLOCKER_CODES:
        code = "missing_planning_input"
    return build_blocker(
        ContentSemanticReviewBlocker,
        code=cast(ContentSemanticBlockerCode, code),
        label=blocker.label,
        reason=blocker.reason,
        next_step=blocker.next_step,
        source_codes=list(blocker.source_codes),
    )


def semantic_inputs_binding(inputs: SemanticInputs) -> ContentReviewInputs | None:
    return inputs.review_inputs


def semantic_inputs_match_revision(
    expected: ContentDraftRevision,
    actual: SemanticInputs,
) -> bool:
    binding = semantic_inputs_binding(actual)
    return binding is not None and content_review_inputs_match_revision(expected, binding)


def semantic_inputs_match_token(
    initial: SemanticInputs,
    repeated: SemanticInputs,
) -> bool:
    first = semantic_inputs_binding(initial)
    second = semantic_inputs_binding(repeated)
    return first is not None and second is not None and same_content_review_inputs(first, second)


def semantic_claim_blocker_response(
    revision: ContentDraftRevision,
    blocker: ContentSemanticReviewBlocker,
) -> ContentSemanticReviewResponse:
    return ContentSemanticReviewResponse(
        status="blocked",
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        research_packet_id=getattr(revision, "research_packet_id", None),
        research_packet_digest=getattr(revision, "research_packet_digest", None),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def semantic_queue_revalidation_response(
    revision: ContentDraftRevision,
    actual: SemanticInputs,
) -> ContentSemanticReviewResponse:
    packet_changed = (
        getattr(actual.revision, "research_packet_id", None)
        != getattr(revision, "research_packet_id", None)
        or getattr(actual.revision, "research_packet_digest", None)
        != getattr(revision, "research_packet_digest", None)
    )
    code: ContentSemanticBlockerCode = (
        "research_packet_conflict" if packet_changed else "stale_revision"
    )
    blocker = ContentSemanticReviewBlocker(
        code=code,
        label=(
            "Research packet zmienił się przed uruchomieniem review"
            if packet_changed
            else "Rewizja zmieniła się przed uruchomieniem review"
        ),
        reason=(
            "Świeży preflight zwrócił inne exact inputs niż route preflight; "
            "run nie zostanie zakolejkowany."
        ),
        next_step="Odśwież workspace i uruchom review dla bieżącej exact rewizji.",
    )
    return semantic_claim_blocker_response(revision, blocker)


__all__ = [
    "semantic_binding_blocker",
    "semantic_claim_blocker_response",
    "semantic_inputs_binding",
    "semantic_inputs_match_revision",
    "semantic_inputs_match_token",
    "semantic_queue_revalidation_response",
    "semantic_review_response",
]
