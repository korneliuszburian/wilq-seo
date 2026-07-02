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
    "missing_source_connector",
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
    source_connectors: list[str] = Field(default_factory=list)
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
    source_connectors: list[str] | None = None,
    measurement_window_ready: bool = False,
    human_reviewed: bool = False,
    reviewer_id: str | None = None,
) -> ContentClaimLedgerEntry:
    evidence = evidence_ids or []
    connectors = source_connectors or []
    if claim_type == "guarantee_claim":
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="blocked",
            evidence_ids=evidence,
            source_connectors=connectors,
            reason="Gwarancje efektu nie mogą trafić do gotowego języka szkicu.",
            reviewer_id=reviewer_id if human_reviewed else None,
        )
    if claim_type in MEASUREMENT_REQUIRED_CLAIM_TYPES and not measurement_window_ready:
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="blocked_until_measurement",
            evidence_ids=evidence,
            source_connectors=connectors,
            reason="Twierdzenie o skuteczności wymaga zakończonego okna pomiaru.",
            reviewer_id=reviewer_id if human_reviewed else None,
        )
    if claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES and not human_reviewed:
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="needs_human_review",
            evidence_ids=evidence,
            source_connectors=connectors,
            reason="Twierdzenie prawne, ryzyka albo środowiskowe wymaga decyzji człowieka.",
        )
    if claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES and not evidence:
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="needs_human_review",
            evidence_ids=evidence,
            source_connectors=connectors,
            reason=(
                "Decyzja człowieka nie zastępuje dowodu dla twierdzenia prawnego, "
                "ryzyka albo środowiskowego."
            ),
            reviewer_id=reviewer_id if human_reviewed else None,
        )
    if evidence:
        return ContentClaimLedgerEntry(
            id=claim_id,
            claim_text=claim_text,
            claim_type=claim_type,
            status="allowed_with_evidence",
            evidence_ids=evidence,
            source_connectors=connectors,
            reason="Twierdzenie ma przypisane dowody źródłowe.",
            reviewer_id=reviewer_id if human_reviewed else None,
        )
    return ContentClaimLedgerEntry(
        id=claim_id,
        claim_text=claim_text,
        claim_type=claim_type,
        status="allowed_general",
        source_connectors=connectors,
        reason="Twierdzenie jest ogólną informacją bez obietnicy efektu.",
        reviewer_id=reviewer_id if human_reviewed else None,
    )


def claim_ledger_blockers(ledger: ContentClaimLedger) -> list[ContentClaimLedgerBlocker]:
    blockers: list[ContentClaimLedgerBlocker] = []
    for entry in ledger.entries:
        if consistency_blocker := _entry_consistency_blocker(entry):
            blockers.append(consistency_blocker)
            continue
        if entry.status == "allowed_with_evidence" and not entry.evidence_ids:
            blockers.append(
                _blocker(
                    "missing_evidence",
                    entry,
                    "Brakuje dowodu dla twierdzenia",
                    "Twierdzenie oznaczone jako oparte na dowodzie musi mieć podpięty dowód.",
                    "Podłącz dowód albo obniż status twierdzenia.",
                )
            )
        elif (
            entry.claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES
            and entry.status == "needs_human_review"
            and not entry.evidence_ids
        ):
            blockers.append(
                _blocker(
                    "missing_evidence",
                    entry,
                    "Brakuje dowodu dla twierdzenia po review",
                    "Decyzja człowieka nie zastępuje dowodu dla twierdzenia prawnego, "
                    "ryzyka albo środowiskowego.",
                    "Podłącz dowód źródłowy albo zostaw twierdzenie poza szkicem.",
                )
            )
        elif entry.status == "allowed_with_evidence" and not entry.source_connectors:
            blockers.append(
                _blocker(
                    "missing_source_connector",
                    entry,
                    "Brakuje źródła danych dla twierdzenia",
                    "Twierdzenie oparte na dowodzie musi wskazywać źródło danych.",
                    "Podłącz źródło danych dla dowodu albo obniż status twierdzenia.",
                )
            )
        elif entry.status == "needs_human_review":
            blockers.append(
                _blocker(
                    "needs_human_review",
                    entry,
                    "Twierdzenie wymaga decyzji człowieka",
                    "To twierdzenie nie może wejść do gotowego języka szkicu "
                    "bez decyzji człowieka.",
                    "Przekaż twierdzenie do sprawdzenia i zapisz decyzję.",
                )
            )
        elif entry.status == "blocked":
            blockers.append(
                _blocker(
                    "blocked_claim",
                    entry,
                    "Twierdzenie jest zablokowane",
                    "To twierdzenie nie może pojawić się jako gotowe zdanie w szkicu.",
                    "Usuń twierdzenie albo przepisz je na bezpieczną informację edukacyjną.",
                )
            )
        elif entry.status == "blocked_until_measurement":
            blockers.append(
                _blocker(
                    "blocked_until_measurement",
                    entry,
                    "Twierdzenie czeka na pomiar",
                    "Nie wolno twierdzić, że treść dowozi efekt przed końcem okna pomiaru.",
                    "Zostaw twierdzenie poza szkicem do czasu zamknięcia okna pomiaru.",
                )
            )
    return blockers


def _entry_consistency_blocker(
    entry: ContentClaimLedgerEntry,
) -> ContentClaimLedgerBlocker | None:
    if entry.claim_type == "guarantee_claim" and entry.status != "blocked":
        return _blocker(
            "blocked_claim",
            entry,
            "Twierdzenie gwarancyjne jest niedozwolone",
            "Obietnice efektu nie mogą być oznaczone jako gotowe do użycia.",
            "Usuń gwarancję albo przepisz ją na bezpieczną informację bez obietnicy.",
        )
    if (
        entry.claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES
        and entry.status in {"allowed_with_evidence", "allowed_general"}
        and entry.reviewer_id is None
    ):
        return _blocker(
            "needs_human_review",
            entry,
            "Twierdzenie wymaga decyzji człowieka",
            "Twierdzenie prawne, ryzyka albo środowiskowe nie może być ogólnie "
            "dopuszczone bez zapisanej decyzji człowieka.",
            "Przekaż twierdzenie do review i zapisz osobę zatwierdzającą.",
        )
    if (
        entry.claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES
        and entry.status in {"allowed_with_evidence", "allowed_general"}
        and not entry.evidence_ids
    ):
        return _blocker(
            "missing_evidence",
            entry,
            "Brakuje dowodu dla twierdzenia po review",
            "Decyzja człowieka nie zastępuje dowodu dla twierdzenia prawnego, "
            "ryzyka albo środowiskowego.",
            "Podłącz dowód źródłowy albo zostaw twierdzenie poza szkicem.",
        )
    if (
        entry.claim_type in MEASUREMENT_REQUIRED_CLAIM_TYPES
        and entry.status == "allowed_general"
    ):
        return _blocker(
            "blocked_until_measurement",
            entry,
            "Twierdzenie czeka na pomiar",
            "Twierdzenie o SEO, skuteczności albo wyniku biznesowym wymaga "
            "dowodu z zakończonego okna pomiaru.",
            "Zostaw twierdzenie poza szkicem do czasu dostępnego pomiaru.",
        )
    return None


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
