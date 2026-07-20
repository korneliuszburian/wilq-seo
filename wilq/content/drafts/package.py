from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import (
    ContentClaimLedger,
    claim_ledger_allows_draft,
    claim_ledger_blockers,
    publish_ready_claims,
)
from wilq.content.preflight.workflow import ContentPreflightVerdict
from wilq.content.workflow.models import ContentWorkItem

ContentDraftPackageBlockerCode = Literal[
    "preflight_not_draft_allowed",
    "missing_sales_brief",
    "sales_brief_mismatch",
    "missing_claim_ledger",
    "claim_ledger_blocks_draft",
    "missing_evidence_mapping",
]


class ContentDraftSection(BaseModel):
    heading: str
    purpose: str
    evidence_ids: list[str] = Field(default_factory=list)
    draft_notes: list[str] = Field(default_factory=list)


class ContentDraftEvidenceMap(BaseModel):
    section_heading: str
    evidence_ids: list[str] = Field(default_factory=list)


class ContentDraftPackage(BaseModel):
    id: str
    work_item_id: str
    brief_id: str
    claim_ledger_id: str
    draft_kind: Literal["outline"] = "outline"
    title: str
    sections: list[ContentDraftSection] = Field(default_factory=list)
    section_to_evidence_map: list[ContentDraftEvidenceMap] = Field(default_factory=list)
    claims_used: list[str] = Field(default_factory=list)
    claims_removed_or_blocked: list[str] = Field(default_factory=list)
    human_review_questions: list[str] = Field(default_factory=list)
    publish_ready: bool = False


class ContentDraftPackageBlocker(BaseModel):
    code: ContentDraftPackageBlockerCode
    label: str
    reason: str
    next_step: str


class ContentDraftPackageBuildResult(BaseModel):
    draft_package: ContentDraftPackage | None = None
    blockers: list[ContentDraftPackageBlocker] = Field(default_factory=list)


def build_content_draft_package(
    *,
    item: ContentWorkItem,
    preflight: ContentPreflightVerdict,
    sales_brief: ContentSalesBrief | None,
    claim_ledger: ContentClaimLedger | None,
) -> ContentDraftPackageBuildResult:
    blockers = content_draft_package_blockers(
        item=item,
        preflight=preflight,
        sales_brief=sales_brief,
        claim_ledger=claim_ledger,
    )
    if blockers:
        return ContentDraftPackageBuildResult(blockers=blockers)

    if sales_brief is None:
        raise RuntimeError("Sales brief passed draft package blockers as None.")
    if claim_ledger is None:
        raise RuntimeError("Claim ledger passed draft package blockers as None.")
    sections = _sections_from_brief(sales_brief)
    evidence_map = [
        ContentDraftEvidenceMap(
            section_heading=section.heading,
            evidence_ids=section.evidence_ids,
        )
        for section in sections
    ]
    blocked_claims = [
        entry.claim_text
        for blocker in claim_ledger_blockers(claim_ledger)
        for entry in claim_ledger.entries
        if entry.id == blocker.claim_id
    ]
    sales_brief_forbidden_claims = [claim.claim_text for claim in sales_brief.forbidden_claims]
    return ContentDraftPackageBuildResult(
        draft_package=ContentDraftPackage(
            id=f"draft_package_{item.id}",
            work_item_id=item.id,
            brief_id=sales_brief.id,
            claim_ledger_id=claim_ledger.id,
            title=sales_brief.h1_direction,
            sections=sections,
            section_to_evidence_map=evidence_map,
            claims_used=[entry.claim_text for entry in publish_ready_claims(claim_ledger)],
            claims_removed_or_blocked=_unique(
                [*blocked_claims, *sales_brief_forbidden_claims]
            ),
            human_review_questions=[
                "Czy szkic brzmi jak Ekologus i nie używa generycznego języka?",
                "Czy każde twierdzenie sprzedażowe ma dowód albo zostało usunięte?",
                "Czy CTA pasuje do intencji i nie obiecuje wyniku?",
                "Czy sekcje odpowiadają planowi i zachowują ustalenia dla istniejącej treści?",
            ],
            publish_ready=False,
        )
    )


def content_draft_package_blockers(
    *,
    item: ContentWorkItem,
    preflight: ContentPreflightVerdict,
    sales_brief: ContentSalesBrief | None,
    claim_ledger: ContentClaimLedger | None,
) -> list[ContentDraftPackageBlocker]:
    blockers: list[ContentDraftPackageBlocker] = []
    if not preflight.draft_allowed:
        blockers.append(
            _blocker(
                "preflight_not_draft_allowed",
                "Sprawdzenie wstępne nie pozwala na szkic",
                "Paczka szkicu może powstać dopiero po przejściu bramek bezpieczeństwa.",
                "Doprowadź temat do etapu, w którym szkic jest dozwolony.",
            )
        )
    if sales_brief is None:
        blockers.append(
            _blocker(
                "missing_sales_brief",
                "Brakuje planu sprzedażowego",
                "Szkic bez planu sprzedażowego byłby promptową improwizacją.",
                "Zbuduj i zatwierdź plan sprzedażowy przed szkicem.",
            )
        )
    elif sales_brief.work_item_id != item.id:
        blockers.append(
            _blocker(
                "sales_brief_mismatch",
                "Plan dotyczy innego tematu",
                "Paczka szkicu musi używać planu dla tego samego tematu.",
                "Podaj plan sprzedażowy przypisany do tego tematu.",
            )
        )
    if claim_ledger is None:
        blockers.append(
            _blocker(
                "missing_claim_ledger",
                "Brakuje sprawdzenia twierdzeń",
                "Szkic nie może powstać bez sprawdzenia ryzykownych twierdzeń.",
                "Zbuduj sprawdzenie twierdzeń przed szkicem.",
            )
        )
    elif claim_ledger.work_item_id != item.id or not claim_ledger_allows_draft(claim_ledger):
        blockers.append(
            _blocker(
                "claim_ledger_blocks_draft",
                "Sprawdzenie twierdzeń blokuje szkic",
                "Ryzykowne albo niezweryfikowane twierdzenia muszą zostać "
                "usunięte lub zatwierdzone.",
                "Rozwiąż sprawdzenie twierdzeń przed paczką szkicu.",
            )
        )
    if sales_brief is not None and not sales_brief.source_facts:
        blockers.append(
            _blocker(
                "missing_evidence_mapping",
                "Brakuje mapy dowodów",
                "Paczka szkicu musi mapować sekcje na dowody.",
                "Uzupełnij fakty źródłowe w planie sprzedażowym.",
            )
        )
    return blockers


def _sections_from_brief(sales_brief: ContentSalesBrief) -> list[ContentDraftSection]:
    evidence_ids = _unique(fact.evidence_id for fact in sales_brief.source_facts)
    headings = sales_brief.h2_direction or [sales_brief.h1_direction]
    return [
        ContentDraftSection(
            heading=heading,
            purpose=_section_purpose(heading),
            evidence_ids=evidence_ids,
            draft_notes=[],
        )
        for heading in headings
    ]


def _section_purpose(heading: str) -> str:
    if heading == "Treść główna (the_content)":
        return (
            "Zdecyduj, które informacje z istniejącego tekstu głównego zachować, "
            "uzupełnić albo przepisać."
        )
    return f"Wyjaśnij czytelnikowi, co oznacza temat „{heading}”."


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _blocker(
    code: ContentDraftPackageBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentDraftPackageBlocker:
    return ContentDraftPackageBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
