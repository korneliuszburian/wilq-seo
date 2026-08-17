from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.operator_copy import build_blocker

ContentClaimType = Literal[
    "service_claim",
    "legal_requirement_claim",
    "risk_claim",
    "guarantee_claim",
    "performance_claim",
    "seo_claim",
    "business_outcome_claim",
    "environmental_claim",
    "product_claim",
]
ContentClaimStatus = Literal[
    "allowed_with_evidence",
    "allowed_general",
    "needs_human_review",
    "blocked",
    "blocked_until_measurement",
]
ContentClaimStrength = Literal["strong", "weak"]
ContentClaimLedgerBlockerCode = Literal[
    "missing_evidence",
    "missing_source_connector",
    "needs_human_review",
    "blocked_claim",
    "blocked_until_measurement",
    "missing_product_evidence",
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
PRODUCT_CLAIM_SOURCE_CONNECTORS = {"google_merchant_center", "wordpress_sklep"}


class ContentClaimLedgerEntry(BaseModel):
    id: str
    claim_text: str
    claim_type: ContentClaimType
    status: ContentClaimStatus
    strength: ContentClaimStrength = "strong"
    required: bool = False
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
    strength: ContentClaimStrength = "strong",
    required: bool = False,
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
            strength=strength,
            required=False,
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
            strength=strength,
            required=False,
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
            strength=strength,
            required=False,
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
            strength=strength,
            required=False,
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
            strength=strength,
            required=required,
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
        strength=strength,
        required=required,
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
        if entry.claim_type == "product_claim" and not PRODUCT_CLAIM_SOURCE_CONNECTORS.intersection(
            entry.source_connectors
        ):
            blockers.append(
                build_blocker(
                    ContentClaimLedgerBlocker,
                    code="missing_product_evidence",
                    claim_id=entry.id,
                    label="Brakuje dowodu produktowego",
                    reason="Twierdzenie produktowe wymaga dowodu z Merchant albo sklepu.",
                    next_step="Podłącz dowód produktowy z Merchant/sklepu albo zmień CTA na konsultację.",  # noqa: E501
                )
            )
        if entry.status == "allowed_with_evidence" and not entry.evidence_ids:
            blockers.append(
                build_blocker(
                    ContentClaimLedgerBlocker,
                    code="missing_evidence",
                    claim_id=entry.id,
                    label="Brakuje dowodu dla twierdzenia",
                    reason="Twierdzenie oznaczone jako oparte na dowodzie musi mieć podpięty dowód.",  # noqa: E501
                    next_step="Podłącz dowód albo obniż status twierdzenia.",
                )
            )
        elif (
            entry.claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES
            and entry.status == "needs_human_review"
            and not entry.evidence_ids
        ):
            blockers.append(
                build_blocker(
                    ContentClaimLedgerBlocker,
                    code="missing_evidence",
                    claim_id=entry.id,
                    label="Brakuje dowodu dla twierdzenia po review",
                    reason="Decyzja człowieka nie zastępuje dowodu dla twierdzenia prawnego, "
                    "ryzyka albo środowiskowego.",
                    next_step="Podłącz dowód źródłowy albo zostaw twierdzenie poza szkicem.",
                )
            )
        elif entry.status == "allowed_with_evidence" and not entry.source_connectors:
            blockers.append(
                build_blocker(
                    ContentClaimLedgerBlocker,
                    code="missing_source_connector",
                    claim_id=entry.id,
                    label="Brakuje źródła danych dla twierdzenia",
                    reason="Twierdzenie oparte na dowodzie musi wskazywać źródło danych.",
                    next_step="Podłącz źródło danych dla dowodu albo obniż status twierdzenia.",
                )
            )
        elif entry.status == "needs_human_review":
            blockers.append(
                build_blocker(
                    ContentClaimLedgerBlocker,
                    code="needs_human_review",
                    claim_id=entry.id,
                    label="Twierdzenie wymaga decyzji człowieka",
                    reason="To twierdzenie nie może wejść do gotowego języka szkicu "
                    "bez decyzji człowieka.",
                    next_step="Przekaż twierdzenie do sprawdzenia i zapisz decyzję.",
                )
            )
        elif entry.status == "blocked":
            blockers.append(
                build_blocker(
                    ContentClaimLedgerBlocker,
                    code="blocked_claim",
                    claim_id=entry.id,
                    label="Twierdzenie jest zablokowane",
                    reason="To twierdzenie nie może pojawić się jako gotowe zdanie w szkicu.",
                    next_step="Usuń twierdzenie albo przepisz je na bezpieczną informację edukacyjną.",  # noqa: E501
                )
            )
        elif entry.status == "blocked_until_measurement":
            blockers.append(
                build_blocker(
                    ContentClaimLedgerBlocker,
                    code="blocked_until_measurement",
                    claim_id=entry.id,
                    label="Twierdzenie czeka na pomiar",
                    reason="Nie wolno twierdzić, że treść dowozi efekt przed końcem okna pomiaru.",
                    next_step="Zostaw twierdzenie poza szkicem do czasu zamknięcia okna pomiaru.",
                )
            )
    return blockers


def _entry_consistency_blocker(
    entry: ContentClaimLedgerEntry,
) -> ContentClaimLedgerBlocker | None:
    if entry.claim_type == "guarantee_claim" and entry.status != "blocked":
        return build_blocker(
            ContentClaimLedgerBlocker,
            code="blocked_claim",
            claim_id=entry.id,
            label="Twierdzenie gwarancyjne jest niedozwolone",
            reason="Obietnice efektu nie mogą być oznaczone jako gotowe do użycia.",
            next_step="Usuń gwarancję albo przepisz ją na bezpieczną informację bez obietnicy.",
        )
    if (
        entry.claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES
        and entry.status in {"allowed_with_evidence", "allowed_general"}
        and entry.reviewer_id is None
    ):
        return build_blocker(
            ContentClaimLedgerBlocker,
            code="needs_human_review",
            claim_id=entry.id,
            label="Twierdzenie wymaga decyzji człowieka",
            reason="Twierdzenie prawne, ryzyka albo środowiskowe nie może być ogólnie "
            "dopuszczone bez zapisanej decyzji człowieka.",
            next_step="Przekaż twierdzenie do review i zapisz osobę zatwierdzającą.",
        )
    if (
        entry.claim_type in HUMAN_REVIEW_REQUIRED_CLAIM_TYPES
        and entry.status in {"allowed_with_evidence", "allowed_general"}
        and not entry.evidence_ids
    ):
        return build_blocker(
            ContentClaimLedgerBlocker,
            code="missing_evidence",
            claim_id=entry.id,
            label="Brakuje dowodu dla twierdzenia po review",
            reason="Decyzja człowieka nie zastępuje dowodu dla twierdzenia prawnego, "
            "ryzyka albo środowiskowego.",
            next_step="Podłącz dowód źródłowy albo zostaw twierdzenie poza szkicem.",
        )
    if entry.claim_type in MEASUREMENT_REQUIRED_CLAIM_TYPES and entry.status == "allowed_general":
        return build_blocker(
            ContentClaimLedgerBlocker,
            code="blocked_until_measurement",
            claim_id=entry.id,
            label="Twierdzenie czeka na pomiar",
            reason="Twierdzenie o SEO, skuteczności albo wyniku biznesowym wymaga "
            "dowodu z zakończonego okna pomiaru.",
            next_step="Zostaw twierdzenie poza szkicem do czasu dostępnego pomiaru.",
        )
    if (
        entry.claim_type == "service_claim"
        and entry.status == "allowed_general"
        and not entry.evidence_ids
    ):
        return build_blocker(
            ContentClaimLedgerBlocker,
            code="missing_evidence",
            claim_id=entry.id,
            label="Brakuje dowodu dla twierdzenia usługowego",
            reason="Ogólne twierdzenie o usłudze nadal musi mieć źródło, zanim trafi do szkicu.",
            next_step="Podłącz dowód źródłowy albo zostaw twierdzenie poza szkicem.",
        )
    return None


def claim_ledger_allows_draft(ledger: ContentClaimLedger) -> bool:
    critical_blocker_codes = {
        "missing_evidence",
        "missing_source_connector",
        "needs_human_review",
        "missing_product_evidence",
    }
    blockers = claim_ledger_blockers(ledger)
    return bool(publish_ready_claims(ledger)) and all(
        blocker.code not in critical_blocker_codes for blocker in blockers
    )


def publish_ready_claims(ledger: ContentClaimLedger) -> list[ContentClaimLedgerEntry]:
    return [
        entry
        for entry in ledger.entries
        if entry.status in {"allowed_with_evidence", "allowed_general"}
        and entry.id not in _blocked_claim_ids(ledger)
    ]


def _blocked_claim_ids(ledger: ContentClaimLedger) -> set[str]:
    return {blocker.claim_id for blocker in claim_ledger_blockers(ledger)}


def claim_source_connectors_required(entries: Iterable[ContentClaimLedgerEntry]) -> bool:
    return any(entry.status == "allowed_with_evidence" for entry in entries)
