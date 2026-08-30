from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

from wilq.content.workflow.decisions.production import (
    ClassificationLookupBasis,
    ContentProductionClassificationProjection,
    ContentProductionClassificationRow,
)
from wilq.content.workflow.decisions.production_reuse import (
    ExactProductionReuseBlocked,
    ProductionReuseBlockCode,
    resolve_exact_production_reuse,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionState,
)

_HEX64 = r"^[0-9a-f]{64}$"
_PUBLIC_URL_VALIDATOR = TypeAdapter(AnyUrl)
_NonEmptyString = Annotated[str, Field(min_length=1)]

ContentReusableDocumentBlockCode = ProductionReuseBlockCode


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentProductionDecisionMissing(_FrozenModel):
    """No accepted production authority exists for this selected item."""

    status: Literal["missing"]


class ContentProductionDecisionBlocker(_FrozenModel):
    code: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    next_step_pl: str = Field(min_length=1)
    sources: tuple[_NonEmptyString, ...] = Field(min_length=1)
    blocks_initial_generation: Literal[True]


class ContentProductionDecisionFreshness(_FrozenModel):
    state: str = Field(min_length=1)
    checked_at: str = Field(min_length=1)
    requires_refresh: bool
    connector_ids: tuple[str, ...]


class ContentProductionRevisionBinding(_FrozenModel):
    current_work_item_id: str = Field(min_length=1)
    retained_work_item_id: _NonEmptyString | None
    revision_work_item_id: _NonEmptyString | None
    identity_reconciliation_status: Literal["fork", "retained_missing"]
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=_HEX64)
    verified_draft_action_ids: tuple[_NonEmptyString, ...]
    verified_draft_post_ids: tuple[_NonEmptyString, ...]
    must_not_regenerate: Literal[True]

    @model_validator(mode="after")
    def require_exact_revision_owner(self) -> Self:
        if len(self.verified_draft_action_ids) != len(set(self.verified_draft_action_ids)):
            raise ValueError("Verified draft action IDs must be unique.")
        if len(self.verified_draft_post_ids) != len(set(self.verified_draft_post_ids)):
            raise ValueError("Verified draft post IDs must be unique.")
        if self.identity_reconciliation_status == "fork":
            if (
                self.retained_work_item_id is None
                or self.revision_work_item_id != self.retained_work_item_id
                or self.retained_work_item_id == self.current_work_item_id
            ):
                raise ValueError("Fork revision owner must be the exact retained work item.")
        elif (
            self.retained_work_item_id is not None
            or self.revision_work_item_id == self.current_work_item_id
        ):
            raise ValueError("Retained-missing binding requires a distinct historical owner.")
        return self


class ContentReusableDocumentReady(_FrozenModel):
    status: Literal["ready"]
    revision: ContentDraftRevision
    review: ContentDraftRevisionReview

    @model_validator(mode="after")
    def require_exact_approved_review(self) -> Self:
        if self.review.decision != "approved":
            raise ValueError("Reusable document requires an approved review.")
        if (
            self.review.work_item_id != self.revision.work_item_id
            or self.review.revision_id != self.revision.revision_id
            or self.review.revision_digest != self.revision.content_digest
        ):
            raise ValueError("Reusable document review must match the exact revision.")
        return self


class ContentReusableDocumentBlocked(_FrozenModel):
    status: Literal["blocked"]
    code: ContentReusableDocumentBlockCode
    reason_pl: str = Field(min_length=1)
    safe_next_step_pl: str = Field(min_length=1)


ContentReusableDocument = Annotated[
    ContentReusableDocumentReady | ContentReusableDocumentBlocked,
    Field(discriminator="status"),
]


class _ContentProductionDecisionAvailable(_FrozenModel):
    status: Literal["available"]
    run_id: str = Field(min_length=1)
    run_digest: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    decision: Literal["reuse", "refresh", "write", "blocked"]
    generation_allowed: Literal[False]
    lookup_basis: ClassificationLookupBasis
    canonical_path: str = Field(min_length=1)
    public_url: str = Field(min_length=1)
    current_work_item_id: _NonEmptyString | None
    retained_work_item_id: _NonEmptyString | None
    reason_pl: str = Field(min_length=1)
    safe_next_step_pl: str = Field(min_length=1)
    blockers: tuple[ContentProductionDecisionBlocker, ...]
    primary_evidence_ids: tuple[_NonEmptyString, ...] = Field(min_length=1)
    lineage_evidence_ids: tuple[_NonEmptyString, ...]
    source_connectors: tuple[_NonEmptyString, ...] = Field(min_length=1)
    freshness: ContentProductionDecisionFreshness

    @field_validator("public_url")
    @classmethod
    def require_absolute_public_url(cls, value: str) -> str:
        _PUBLIC_URL_VALIDATOR.validate_python(value)
        return value


class ContentProductionDecisionReuse(_ContentProductionDecisionAvailable):
    decision: Literal["reuse"]
    revision_binding: ContentProductionRevisionBinding
    reusable_document: ContentReusableDocument

    @model_validator(mode="after")
    def require_exact_reusable_document_binding(self) -> Self:
        binding = self.revision_binding
        if (
            self.current_work_item_id != binding.current_work_item_id
            or self.retained_work_item_id != binding.retained_work_item_id
        ):
            raise ValueError("Production identities must match the reusable revision binding.")
        reusable = self.reusable_document
        if reusable.status == "ready":
            if binding.revision_work_item_id is None:
                raise ValueError("Ready reusable document requires an exact revision owner.")
            if (
                reusable.revision.work_item_id != binding.revision_work_item_id
                or reusable.revision.revision_id != binding.revision_id
                or reusable.revision.content_digest != binding.revision_digest
                or reusable.review.work_item_id != binding.revision_work_item_id
                or reusable.review.revision_id != binding.revision_id
                or reusable.review.revision_digest != binding.revision_digest
            ):
                raise ValueError("Reusable document does not match its production binding.")
        elif (binding.revision_work_item_id is None) != (reusable.code == "missing_revision_owner"):
            raise ValueError("Missing revision owner must use its exact reusable blocker.")
        return self


class ContentProductionDecisionNonReuse(_ContentProductionDecisionAvailable):
    decision: Literal["refresh", "write", "blocked"]

    @model_validator(mode="after")
    def require_decision_blockers(self) -> Self:
        if self.decision in {"refresh", "blocked"} and not self.blockers:
            raise ValueError("Refresh and blocked production decisions require a blocker.")
        return self


class ContentProductionDecisionRefresh(ContentProductionDecisionNonReuse):
    decision: Literal["refresh"]
    blockers: tuple[ContentProductionDecisionBlocker, ...] = Field(min_length=1)


class ContentProductionDecisionWrite(ContentProductionDecisionNonReuse):
    decision: Literal["write"]


class ContentProductionDecisionBlocked(ContentProductionDecisionNonReuse):
    decision: Literal["blocked"]
    blockers: tuple[ContentProductionDecisionBlocker, ...] = Field(min_length=1)


ContentProductionDecisionAvailable = Annotated[
    ContentProductionDecisionReuse
    | ContentProductionDecisionRefresh
    | ContentProductionDecisionWrite
    | ContentProductionDecisionBlocked,
    Field(discriminator="decision"),
]
ContentProductionDecision = ContentProductionDecisionMissing | ContentProductionDecisionAvailable


def canonical_work_item_id_for_classification(
    requested_work_item_id: str,
    classification: ContentProductionClassificationProjection | None,
) -> str:
    if classification is None:
        return requested_work_item_id
    if classification.row.lookup_basis_for_work_item(requested_work_item_id) is None:
        raise ValueError("Production classification does not match the requested work item.")
    return classification.row.current_work_item_id or requested_work_item_id


def reusable_revision_work_item_id(
    classification: ContentProductionClassificationProjection | None,
) -> str | None:
    if classification is None or classification.row.decision != "reuse":
        return None
    return classification.row.reusable_work_item_id


def build_content_production_decision(
    requested_work_item_id: str,
    *,
    classification: ContentProductionClassificationProjection | None,
    retained_revision_state: ContentDraftRevisionState | None = None,
) -> ContentProductionDecision:
    """Project accepted production authority without retaining its internal receipts."""

    if classification is None:
        if retained_revision_state is not None:
            raise ValueError("Missing classification cannot consume retained revision state.")
        return ContentProductionDecisionMissing(status="missing")

    row = classification.row
    lookup_basis = row.lookup_basis_for_work_item(requested_work_item_id)
    if lookup_basis is None:
        raise ValueError("Production classification does not match the requested work item.")
    if lookup_basis == "historical_action_owner" and row.decision != "reuse":
        raise ValueError("Historical action-owner lookup is only valid for reusable content.")

    payload: dict[str, object] = {
        "status": "available",
        "run_id": classification.run_id,
        "run_digest": classification.run_digest,
        "decision_set_digest": classification.decision_set_digest,
        "decision": row.decision,
        "generation_allowed": row.generation_allowed,
        "lookup_basis": lookup_basis,
        "canonical_path": row.canonical_path,
        "public_url": row.public_url,
        "current_work_item_id": row.current_work_item_id,
        "retained_work_item_id": row.retained_work_item_id,
        "reason_pl": row.rationale_pl,
        "safe_next_step_pl": row.next_step_pl,
        "blockers": tuple(
            ContentProductionDecisionBlocker(
                code=blocker.code,
                owner=blocker.owner,
                next_step_pl=blocker.next_step_pl,
                sources=blocker.sources,
                blocks_initial_generation=blocker.blocks_initial_generation,
            )
            for blocker in row.blockers
        ),
        "primary_evidence_ids": row.primary_evidence_ids,
        "lineage_evidence_ids": row.lineage_evidence_ids,
        "source_connectors": row.source_connectors,
        "freshness": ContentProductionDecisionFreshness(
            state=classification.freshness.state,
            checked_at=classification.freshness.checked_at,
            requires_refresh=classification.freshness.requires_refresh,
            connector_ids=classification.freshness.connector_ids,
        ),
    }
    if row.decision != "reuse":
        if retained_revision_state is not None:
            raise ValueError("Only reuse classification may consume retained revision state.")
        if row.decision == "refresh":
            return ContentProductionDecisionRefresh.model_validate(payload)
        if row.decision == "write":
            return ContentProductionDecisionWrite.model_validate(payload)
        return ContentProductionDecisionBlocked.model_validate(payload)

    binding = _revision_binding(row)
    return ContentProductionDecisionReuse.model_validate(
        {
            **payload,
            "revision_binding": binding,
            "reusable_document": _reusable_document(binding, retained_revision_state),
        }
    )


def _revision_binding(
    row: ContentProductionClassificationRow,
) -> ContentProductionRevisionBinding:
    retained = row.retained_binding
    if retained is None or row.current_work_item_id is None:
        raise ValueError("Reuse classification requires its exact retained binding.")
    return ContentProductionRevisionBinding(
        current_work_item_id=row.current_work_item_id,
        retained_work_item_id=row.retained_work_item_id,
        revision_work_item_id=row.reusable_work_item_id,
        identity_reconciliation_status=retained.identity_reconciliation_status,
        revision_id=retained.retained_revision_id,
        revision_digest=retained.retained_revision_digest,
        verified_draft_action_ids=retained.verified_draft_action_ids,
        verified_draft_post_ids=retained.verified_draft_post_ids,
        must_not_regenerate=retained.must_not_regenerate,
    )


def _reusable_document(
    binding: ContentProductionRevisionBinding,
    state: ContentDraftRevisionState | None,
) -> ContentReusableDocument:
    resolution = resolve_exact_production_reuse(
        revision_owner_work_item_id=binding.revision_work_item_id,
        expected_revision_id=binding.revision_id,
        expected_revision_digest=binding.revision_digest,
        latest_revision=None if state is None else state.latest_revision,
        latest_review=None if state is None else state.latest_review,
    )
    if isinstance(resolution, ExactProductionReuseBlocked):
        return _blocked_reusable_document(resolution.code)
    return ContentReusableDocumentReady(
        status="ready",
        revision=resolution.revision,
        review=resolution.review,
    )


_REUSABLE_BLOCK_GUIDANCE: dict[ContentReusableDocumentBlockCode, tuple[str, str]] = {
    "missing_revision_owner": (
        "Nie można jednoznacznie wskazać właściciela zachowanej rewizji.",
        "Uzgodnij tożsamość zachowanej pracy przed ponownym użyciem dokumentu.",
    ),
    "latest_revision_missing": (
        "Pod wskazaną tożsamością nie ma zachowanej rewizji.",
        "Przywróć dokładną zachowaną rewizję albo ponownie oceń decyzję produkcyjną.",
    ),
    "latest_revision_drift": (
        "Najnowsza zachowana rewizja nie odpowiada zaakceptowanej decyzji produkcyjnej.",
        "Sprawdź zmianę rewizji i ponownie zatwierdź klasyfikację przed dalszą pracą.",
    ),
    "latest_review_missing": (
        "Zachowana rewizja nie ma wymaganego review.",
        "Odszukaj dokładne review tej rewizji przed jej ponownym użyciem.",
    ),
    "latest_review_not_approved": (
        "Najnowsze review zachowanej rewizji nie jest zatwierdzeniem.",
        "Wyjaśnij najnowszą decyzję review przed ponownym użyciem dokumentu.",
    ),
    "latest_review_mismatch": (
        "Najnowsze review nie jest związane z dokładną zachowaną rewizją.",
        "Napraw powiązanie review z rewizją przed dalszą pracą.",
    ),
}


def _blocked_reusable_document(
    code: ContentReusableDocumentBlockCode,
) -> ContentReusableDocumentBlocked:
    reason, safe_next_step = _REUSABLE_BLOCK_GUIDANCE[code]
    return ContentReusableDocumentBlocked(
        status="blocked",
        code=code,
        reason_pl=reason,
        safe_next_step_pl=safe_next_step,
    )


__all__ = [
    "ContentProductionDecision",
    "ContentProductionDecisionAvailable",
    "ContentProductionDecisionBlocker",
    "ContentProductionDecisionBlocked",
    "ContentProductionDecisionFreshness",
    "ContentProductionDecisionMissing",
    "ContentProductionDecisionNonReuse",
    "ContentProductionDecisionRefresh",
    "ContentProductionDecisionReuse",
    "ContentProductionDecisionWrite",
    "ContentProductionRevisionBinding",
    "ContentReusableDocument",
    "ContentReusableDocumentBlockCode",
    "ContentReusableDocumentBlocked",
    "ContentReusableDocumentReady",
    "build_content_production_decision",
    "canonical_work_item_id_for_classification",
    "reusable_revision_work_item_id",
]
