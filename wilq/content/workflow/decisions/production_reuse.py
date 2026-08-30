from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)

ProductionReuseBlockCode = Literal[
    "missing_revision_owner",
    "latest_revision_missing",
    "latest_revision_drift",
    "latest_review_missing",
    "latest_review_not_approved",
    "latest_review_mismatch",
]


@dataclass(frozen=True, slots=True)
class ExactProductionReuseReady:
    revision_owner_work_item_id: str
    revision: ContentDraftRevision
    review: ContentDraftRevisionReview
    status: Literal["ready"] = field(default="ready", init=False)


@dataclass(frozen=True, slots=True)
class ExactProductionReuseBlocked:
    code: ProductionReuseBlockCode
    status: Literal["blocked"] = field(default="blocked", init=False)


ExactProductionReuseResolution = ExactProductionReuseReady | ExactProductionReuseBlocked


def resolve_exact_production_reuse(
    *,
    revision_owner_work_item_id: str | None,
    expected_revision_id: str,
    expected_revision_digest: str,
    latest_revision: ContentDraftRevision | None,
    latest_review: ContentDraftRevisionReview | None,
) -> ExactProductionReuseResolution:
    """Validate one retained owner, latest revision, and latest review exactly."""

    if revision_owner_work_item_id is None:
        return ExactProductionReuseBlocked(code="missing_revision_owner")
    if latest_revision is None:
        return ExactProductionReuseBlocked(code="latest_revision_missing")
    if (
        latest_revision.work_item_id != revision_owner_work_item_id
        or latest_revision.revision_id != expected_revision_id
        or latest_revision.content_digest != expected_revision_digest
    ):
        return ExactProductionReuseBlocked(code="latest_revision_drift")
    if latest_review is None:
        return ExactProductionReuseBlocked(code="latest_review_missing")
    if (
        latest_review.work_item_id != revision_owner_work_item_id
        or latest_review.revision_id != expected_revision_id
        or latest_review.revision_digest != expected_revision_digest
    ):
        return ExactProductionReuseBlocked(code="latest_review_mismatch")
    if latest_review.decision != "approved":
        return ExactProductionReuseBlocked(code="latest_review_not_approved")
    if (
        not latest_review.decision_id.strip()
        or latest_review.principal_id != LOCAL_PILOT_AUDIT_IDENTITY.principal_id
        or latest_review.workspace_id != LOCAL_PILOT_AUDIT_IDENTITY.workspace_id
        or latest_review.trust_level != LOCAL_PILOT_AUDIT_IDENTITY.trust_level
    ):
        return ExactProductionReuseBlocked(code="latest_review_mismatch")
    return ExactProductionReuseReady(
        revision_owner_work_item_id=revision_owner_work_item_id,
        revision=latest_revision,
        review=latest_review,
    )


__all__ = [
    "ExactProductionReuseBlocked",
    "ExactProductionReuseReady",
    "ExactProductionReuseResolution",
    "ProductionReuseBlockCode",
    "resolve_exact_production_reuse",
]
