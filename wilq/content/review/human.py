from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.claims.ledger import ContentClaimLedger, claim_ledger_blockers
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.operator_copy import build_blocker
from wilq.content.workflow.contracts.models import ContentHumanReviewStatus, ContentWorkItem

ContentHumanReviewStage = Literal[
    "sales_brief",
    "claim_ledger",
    "draft_package",
    "wordpress_handoff",
]
ContentHumanReviewDecision = Literal[
    "approved",
    "needs_changes",
    "rejected",
    "deferred",
]
ContentHumanReviewBlockerCode = Literal[
    "missing_human_review",
    "wrong_work_item",
    "missing_reviewer",
    "missing_checked_items",
    "missing_evidence",
    "not_approved",
    "missing_draft_package",
    "draft_package_mismatch",
    "draft_package_marked_publish_ready",
    "unhandled_blocked_claims",
]


class ContentHumanReview(BaseModel):
    id: str
    work_item_id: str
    stage: ContentHumanReviewStage
    reviewed_by: str
    decision: ContentHumanReviewDecision
    notes: str = ""
    checked_items: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    blocked_claims_handled: list[str] = Field(default_factory=list)
    sales_brief_id: str | None = None
    claim_ledger_id: str | None = None
    draft_package_id: str | None = None


class ContentHumanReviewBlocker(BaseModel):
    code: ContentHumanReviewBlockerCode
    label: str
    reason: str
    next_step: str


_NON_RECORDABLE_REVIEW_BLOCKERS: frozenset[ContentHumanReviewBlockerCode] = frozenset(
    {
        "missing_human_review",
        "wrong_work_item",
        "missing_reviewer",
        "missing_checked_items",
        "missing_evidence",
        "missing_draft_package",
        "draft_package_mismatch",
    }
)


def content_human_review_is_recordable(
    review: ContentHumanReview | None,
    blockers: list[ContentHumanReviewBlocker],
) -> bool:
    """Keep an exact human decision without confusing it with approval."""
    return review is not None and not any(
        blocker.code in _NON_RECORDABLE_REVIEW_BLOCKERS for blocker in blockers
    )


def content_human_review_blockers(
    *,
    item: ContentWorkItem,
    review: ContentHumanReview | None,
    draft_package: ContentDraftPackage | None = None,
    claim_ledger: ContentClaimLedger | None = None,
) -> list[ContentHumanReviewBlocker]:
    blockers: list[ContentHumanReviewBlocker] = []
    if review is None:
        return [
            build_blocker(
                ContentHumanReviewBlocker,
                code="missing_human_review",
                label="Brakuje decyzji człowieka",
                reason="Snapshot może pokazać przygotowane etapy, ale nie może udawać "
                "zatwierdzenia człowieka.",
                next_step="Zatwierdź brief, ryzykowne twierdzenia i paczkę szkicu przed "
                "przekazaniem do WordPress.",
            )
        ]
    if review.work_item_id != item.id:
        blockers.append(
            build_blocker(
                ContentHumanReviewBlocker,
                code="wrong_work_item",
                label="Sprawdzenie dotyczy innego tematu",
                reason="Decyzja człowieka musi dotyczyć tego samego tematu treści.",
                next_step="Podaj sprawdzenie z poprawnym identyfikatorem tematu.",
            )
        )
    if not review.reviewed_by.strip():
        blockers.append(
            build_blocker(
                ContentHumanReviewBlocker,
                code="missing_reviewer",
                label="Brakuje osoby sprawdzającej",
                reason="Sprawdzenie musi mieć konkretną osobę odpowiedzialną za decyzję.",
                next_step="Uzupełnij osobę sprawdzającą przed zatwierdzeniem.",
            )
        )
    if not review.checked_items:
        blockers.append(
            build_blocker(
                ContentHumanReviewBlocker,
                code="missing_checked_items",
                label="Brakuje checklisty sprawdzenia",
                reason="Decyzja człowieka musi mówić, co zostało sprawdzone.",
                next_step="Zapisz checklistę dla briefu, ryzykownych twierdzeń albo szkicu.",
            )
        )
    if not review.evidence_ids:
        blockers.append(
            build_blocker(
                ContentHumanReviewBlocker,
                code="missing_evidence",
                label="Brakuje dowodów sprawdzenia",
                reason="Sprawdzenie człowieka nie może opierać się wyłącznie na opinii bez dowodów.",  # noqa: E501
                next_step="Powiąż sprawdzenie z dowodami, które sprawdził człowiek.",
            )
        )
    if review.decision != "approved":
        blockers.append(
            build_blocker(
                ContentHumanReviewBlocker,
                code="not_approved",
                label="Sprawdzenie nie zatwierdza dalszego kroku",
                reason="Tylko zatwierdzona decyzja może odblokować następny etap procesu.",
                next_step="Zapisz poprawki albo wróć po nowe zatwierdzenie.",
            )
        )
    blockers.extend(_draft_package_blockers(item, review, draft_package))
    blockers.extend(_claim_handling_blockers(review, draft_package, claim_ledger))
    return blockers


def content_human_review_allows_wordpress_handoff(
    *,
    item: ContentWorkItem,
    review: ContentHumanReview,
    draft_package: ContentDraftPackage | None,
) -> bool:
    if review.stage not in {"draft_package", "wordpress_handoff"}:
        return False
    return not content_human_review_blockers(
        item=item,
        review=review,
        draft_package=draft_package,
    )


def apply_content_human_review_to_work_item(
    item: ContentWorkItem,
    review: ContentHumanReview,
) -> ContentWorkItem:
    status: ContentHumanReviewStatus = review.decision
    return item.model_copy(
        update={
            "human_review_status": status,
            "human_review_id": review.id,
        }
    )


def _draft_package_blockers(
    item: ContentWorkItem,
    review: ContentHumanReview,
    draft_package: ContentDraftPackage | None,
) -> list[ContentHumanReviewBlocker]:
    if review.stage not in {"draft_package", "wordpress_handoff"}:
        return []
    if draft_package is None:
        return [
            build_blocker(
                ContentHumanReviewBlocker,
                code="missing_draft_package",
                label="Brakuje paczki szkicu do sprawdzenia",
                reason="Sprawdzenie szkicu i przekazania do WordPress wymaga konkretnej paczki szkicu.",  # noqa: E501
                next_step="Podaj paczkę szkicu przed sprawdzeniem przekazania do WordPress.",
            )
        ]
    blockers: list[ContentHumanReviewBlocker] = []
    expected_id = item.draft_package_id or review.draft_package_id
    if draft_package.work_item_id != item.id or (
        expected_id is not None and draft_package.id != expected_id
    ):
        blockers.append(
            build_blocker(
                ContentHumanReviewBlocker,
                code="draft_package_mismatch",
                label="Paczka szkicu nie pasuje do sprawdzenia",
                reason="Sprawdzenie człowieka musi dotyczyć paczki szkicu dla tego samego tematu.",
                next_step="Podaj paczkę szkicu zgodną ze sprawdzeniem i tematem.",
            )
        )
    if draft_package.publish_ready:
        blockers.append(
            build_blocker(
                ContentHumanReviewBlocker,
                code="draft_package_marked_publish_ready",
                label="Szkic nie może udawać gotowości do publikacji",
                reason="Paczka szkicu jest materiałem do sprawdzenia, nie zgodą na publikację.",
                next_step="Zatrzymaj status publikacji i przeprowadź sprawdzenie człowieka oraz "
                "przekazanie do WordPress.",
            )
        )
    return blockers


def _claim_handling_blockers(
    review: ContentHumanReview,
    draft_package: ContentDraftPackage | None,
    claim_ledger: ContentClaimLedger | None,
) -> list[ContentHumanReviewBlocker]:
    required_claims = set(draft_package.claims_removed_or_blocked if draft_package else [])
    if claim_ledger is not None:
        required_claims.update(
            _claim_handling_ref(entry.id, entry.claim_text)
            for blocker in claim_ledger_blockers(claim_ledger)
            for entry in claim_ledger.entries
            if entry.id == blocker.claim_id
            and entry.id not in review.blocked_claims_handled
            and entry.claim_text not in review.blocked_claims_handled
        )
    missing = sorted(required_claims.difference(review.blocked_claims_handled))
    if not missing:
        return []
    return [
        build_blocker(
            ContentHumanReviewBlocker,
            code="unhandled_blocked_claims",
            label="Nie rozliczono zablokowanych twierdzeń",
            reason="Sprawdzenie musi pokazać, że ryzykowne twierdzenia zostały usunięte, przepisane albo "  # noqa: E501
            "jawnie obsłużone.",
            next_step="Uzupełnij listę obsłużonych ryzykownych twierdzeń: " + ", ".join(missing),
        )
    ]


def _claim_handling_ref(claim_id: str, claim_text: str) -> str:
    if claim_text:
        return claim_text
    return claim_id
