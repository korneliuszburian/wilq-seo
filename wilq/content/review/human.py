from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.claims.ledger import ContentClaimLedger, claim_ledger_blockers
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.workflow.models import ContentHumanReviewStatus, ContentWorkItem

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
            _blocker(
                "missing_human_review",
                "Brakuje decyzji człowieka",
                "Snapshot może pokazać przygotowane etapy, ale nie może udawać "
                "zatwierdzenia człowieka.",
                "Zatwierdź brief, ryzykowne twierdzenia i paczkę szkicu przed "
                "przekazaniem do WordPress.",
            )
        ]
    if review.work_item_id != item.id:
        blockers.append(
            _blocker(
                "wrong_work_item",
                "Sprawdzenie dotyczy innego tematu",
                "Decyzja człowieka musi dotyczyć tego samego tematu treści.",
                "Podaj sprawdzenie z poprawnym identyfikatorem tematu.",
            )
        )
    if not review.reviewed_by.strip():
        blockers.append(
            _blocker(
                "missing_reviewer",
                "Brakuje osoby sprawdzającej",
                "Sprawdzenie musi mieć konkretną osobę odpowiedzialną za decyzję.",
                "Uzupełnij osobę sprawdzającą przed zatwierdzeniem.",
            )
        )
    if not review.checked_items:
        blockers.append(
            _blocker(
                "missing_checked_items",
                "Brakuje checklisty sprawdzenia",
                "Decyzja człowieka musi mówić, co zostało sprawdzone.",
                "Zapisz checklistę dla briefu, ryzykownych twierdzeń albo szkicu.",
            )
        )
    if not review.evidence_ids:
        blockers.append(
            _blocker(
                "missing_evidence",
                "Brakuje dowodów sprawdzenia",
                "Sprawdzenie człowieka nie może opierać się wyłącznie na opinii bez dowodów.",
                "Powiąż sprawdzenie z dowodami, które sprawdził człowiek.",
            )
        )
    if review.decision != "approved":
        blockers.append(
            _blocker(
                "not_approved",
                "Sprawdzenie nie zatwierdza dalszego kroku",
                "Tylko zatwierdzona decyzja może odblokować następny etap procesu.",
                "Zapisz poprawki albo wróć po nowe zatwierdzenie.",
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
            _blocker(
                "missing_draft_package",
                "Brakuje paczki szkicu do sprawdzenia",
                "Sprawdzenie szkicu i przekazania do WordPress wymaga konkretnej paczki szkicu.",
                "Podaj paczkę szkicu przed sprawdzeniem przekazania do WordPress.",
            )
        ]
    blockers: list[ContentHumanReviewBlocker] = []
    expected_id = item.draft_package_id or review.draft_package_id
    if draft_package.work_item_id != item.id or (
        expected_id is not None and draft_package.id != expected_id
    ):
        blockers.append(
            _blocker(
                "draft_package_mismatch",
                "Paczka szkicu nie pasuje do sprawdzenia",
                "Sprawdzenie człowieka musi dotyczyć paczki szkicu dla tego samego tematu.",
                "Podaj paczkę szkicu zgodną ze sprawdzeniem i tematem.",
            )
        )
    if draft_package.publish_ready:
        blockers.append(
            _blocker(
                "draft_package_marked_publish_ready",
                "Szkic nie może udawać gotowości do publikacji",
                "Paczka szkicu jest materiałem do sprawdzenia, nie zgodą na publikację.",
                "Zatrzymaj status publikacji i przeprowadź sprawdzenie człowieka oraz "
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
        _blocker(
            "unhandled_blocked_claims",
            "Nie rozliczono zablokowanych twierdzeń",
            "Sprawdzenie musi pokazać, że ryzykowne twierdzenia zostały usunięte, przepisane albo "
            "jawnie obsłużone.",
            "Uzupełnij listę obsłużonych ryzykownych twierdzeń: " + ", ".join(missing),
        )
    ]


def _claim_handling_ref(claim_id: str, claim_text: str) -> str:
    if claim_text:
        return claim_text
    return claim_id


def _blocker(
    code: ContentHumanReviewBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentHumanReviewBlocker:
    return ContentHumanReviewBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
