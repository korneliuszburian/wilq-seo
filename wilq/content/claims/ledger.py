from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

ContentClaimType = Literal[
    "service_claim",
    "legal_requirement_claim",
    "risk_claim",
    "guarantee_claim",
    "performance_claim",
    "seo_claim",
    "business_outcome_claim",
    "environmental_claim",
]
ContentClaimStatus = Literal[
    "allowed_with_evidence",
    "allowed_general",
    "needs_human_review",
    "blocked",
    "blocked_until_measurement",
]
ContentClaimLedgerBlockerCode = Literal[
    "missing_evidence",
    "needs_human_review",
    "blocked_claim",
    "blocked_until_measurement",
]

MEASUREMENT_REQUIRED_CLAIM_TYPES = {
    "performance_claim",
    "seo_claim",
    "business_outcome_claim",
}
HUMAN_REVIEW_REQUIRED_CLAIM_TYPES = {
    "legal_requirement_claim",
    "risk_claim",
    "environmental_claim",
}


class ContentClaimLedgerEntry(BaseModel):
    id: str
    claim_text: str
    claim_type: ContentClaimType
    status: ContentClaimStatus
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str
    reviewer_id: str | None = None


class ContentClaimLedger(BaseModel):
    id: str
    work_item_id: str
    entries: list[ContentClaimLedgerEntry] = Field(default_factory=list)
    reviewed_by: str | None = None


class ContentClaimLedgerBlocker(BaseModel):
    code: ContentClaimLedgerBlockerCode
    claim_id: str
    label: str
    reason: str
    next_step: str


def content_claim_entry(
    *,
    claim_id: str,
    claim_text: str,
    claim_type: ContentClaimType,
    evidence_ids: list[str] | None = None,
    measurement_window_ready: bool = False,
    human_reviewed: bool = False,
    reviewer_id: str | None = None,
) -> ContentClaimLedgerEntry:
    evidence = evidence_ids or []
    if claim_type == "guarantee_claim":
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="blocked",
            evidence_ids=evidence,
            reason="Gwarancje efektu nie mogą być użyte jako publish-ready language.",
            reviewer_id=reviewer_id if human_reviewed else None,
        )
    if claim_type in MEASUREMENT_REQUIRED_CLAIM_TYPES and not measurement_window_ready:
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="blocked_until_measurement",
            evidence_ids=evidence,
            reason="Claim skuteczności wymaga zakończonego okna pomiaru.",
            reviewer_id=reviewer_id if human_reviewed else None,
        )
    if claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES and not human_reviewed:
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="needs_human_review",
            evidence_ids=evidence,
            reason="Claim prawny, ryzyka albo środowiskowy wymaga review człowieka.",
        )
    if evidence:
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="allowed_with_evidence",
            evidence_ids=evidence,
            reason="Claim ma przypisane dowody źródłowe.",
            reviewer_id=reviewer_id if human_reviewed else None,
        )
    return ContentClaimLedgerEntry(
        id=claim_id,
        claim_text=claim_text,
        claim_type=claim_type,
        status="allowed_general",
        reason="Claim jest ogólną informacją bez obietnicy efektu.",
        reviewer_id=reviewer_id if human_reviewed else None,
    )


def claim_ledger_blockers(ledger: ContentClaimLedger) -> list[ContentClaimLedgerBlocker]:
    blockers: list[ContentClaimLedgerBlocker] = []
    for entry in ledger.entries:
        if entry.status == "allowed_with_evidence" and not entry.evidence_ids:
            blockers.append(
                _blocker(
                    "missing_evidence",
                    entry,
                    "Brakuje dowodu dla claimu",
                    "Claim oznaczony jako allowed_with_evidence musi mieć evidence ID.",
                    "Podłącz dowód albo obniż status claimu.",
                )
            )
        elif entry.status == "needs_human_review":
            blockers.append(
                _blocker(
                    "needs_human_review",
                    entry,
                    "Claim wymaga review",
                    "Ten claim nie może wejść do publish-ready language bez decyzji człowieka.",
                    "Przekaż claim do review i zapisz decyzję.",
                )
            )
        elif entry.status == "blocked":
            blockers.append(
                _blocker(
                    "blocked_claim",
                    entry,
                    "Claim jest zablokowany",
                    "Ten claim nie może pojawić się jako gotowe twierdzenie w szkicu.",
                    "Usuń claim albo przepisz go na bezpieczną informację edukacyjną.",
                )
            )
        elif entry.status == "blocked_until_measurement":
            blockers.append(
                _blocker(
                    "blocked_until_measurement",
                    entry,
                    "Claim czeka na pomiar",
                    "Nie wolno twierdzić, że treść dowozi efekt przed końcem okna pomiaru.",
                    "Zostaw claim poza szkicem do czasu zamknięcia measurement window.",
                )
            )
    return blockers


def claim_ledger_allows_draft(ledger: ContentClaimLedger) -> bool:
    return not claim_ledger_blockers(ledger)


def publish_ready_claims(ledger: ContentClaimLedger) -> list[ContentClaimLedgerEntry]:
    return [
        entry
        for entry in ledger.entries
        if entry.status in {"allowed_with_evidence", "allowed_general"}
        and entry.id not in _blocked_claim_ids(ledger)
    ]


def _blocked_claim_ids(ledger: ContentClaimLedger) -> set[str]:
    return {blocker.claim_id for blocker in claim_ledger_blockers(ledger)}


def _blocker(
    code: ContentClaimLedgerBlockerCode,
    entry: ContentClaimLedgerEntry,
    label: str,
    reason: str,
    next_step: str,
) -> ContentClaimLedgerBlocker:
    return ContentClaimLedgerBlocker(
        code=code,
        claim_id=entry.id,
        label=label,
        reason=reason,
        next_step=next_step,
    )


def claim_source_connectors_required(entries: Iterable[ContentClaimLedgerEntry]) -> bool:
    return any(entry.status == "allowed_with_evidence" for entry in entries)
