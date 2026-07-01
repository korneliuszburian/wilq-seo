from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import (
    ContentClaimLedger,
    ContentClaimStatus,
    ContentClaimType,
    claim_ledger_allows_draft,
    publish_ready_claims,
)
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.workflow.models import ContentWorkItem, content_workflow_blockers

StructuredDraftGenerationBlockerCode = Literal[
    "missing_evidence",
    "missing_source_connector",
    "missing_final_canonical",
    "invalid_final_canonical",
    "missing_inventory_resolution",
    "duplicate_gate_not_checked",
    "duplicate_or_canonical_risk",
    "missing_preflight",
    "blocked_preflight",
    "missing_preserve_first_plan",
    "missing_draft_package",
    "draft_package_mismatch",
    "draft_package_marked_publish_ready",
    "missing_sales_brief",
    "sales_brief_mismatch",
    "missing_claim_ledger",
    "claim_ledger_blocks_generation",
    "missing_measurement_window",
    "missing_evidence_mapping",
    "missing_human_review_questions",
]


class StructuredDraftGenerationBlocker(BaseModel):
    code: StructuredDraftGenerationBlockerCode
    label: str
    reason: str
    next_step: str


class StructuredDraftSourceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source_connector: str
    summary: str


class StructuredDraftClaimMarker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    claim_text: str
    claim_type: ContentClaimType
    status: ContentClaimStatus
    evidence_ids: list[str] = Field(default_factory=list)
    reviewer_id: str | None = None


class StructuredDraftSectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    purpose: str
    evidence_ids: list[str] = Field(default_factory=list)
    draft_notes: list[str] = Field(default_factory=list)


class StructuredDraftGenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str
    language: Literal["pl-PL"] = "pl-PL"
    draft_kind: Literal["section_draft", "full_draft"] = "section_draft"
    title: str
    final_canonical_url: str
    source_public_url: str | None = None
    preview_url: str | None = None
    target_reader: str
    buyer_problem: str
    buyer_trigger: str
    search_intent: str
    service_fit: str
    cta_direction: str
    sections: list[StructuredDraftSectionInput] = Field(default_factory=list)
    source_facts: list[StructuredDraftSourceFact] = Field(default_factory=list)
    claim_markers: list[StructuredDraftClaimMarker] = Field(default_factory=list)
    claims_allowed: list[str] = Field(default_factory=list)
    claims_removed_or_blocked: list[str] = Field(default_factory=list)
    human_review_questions: list[str] = Field(default_factory=list)


class StructuredDraftOutputSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    body_markdown: str
    evidence_ids: list[str]
    claims_used: list[str]


class StructuredDraftOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_kind: Literal["section_draft", "full_draft"]
    language: Literal["pl-PL"]
    title: str
    meta_title: str
    meta_description: str
    h1: str
    sections: list[StructuredDraftOutputSection]
    faq: list[str]
    cta: str
    internal_links: list[str]
    source_facts_used: list[str]
    claims_needing_review: list[str]
    forbidden_claims_avoided: list[str]
    human_review_checklist: list[str]
    publish_ready: Literal[False]


class StructuredDraftGenerationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["wilq_content_structured_draft_v1"] = "wilq_content_structured_draft_v1"
    strict_schema: bool = True
    model_input: StructuredDraftGenerationInput
    output_schema: dict[str, object]
    system_instruction: str
    user_instruction: str
    publish_ready: Literal[False] = False


class StructuredDraftGenerationResult(BaseModel):
    contract: StructuredDraftGenerationContract | None = None
    blockers: list[StructuredDraftGenerationBlocker] = Field(default_factory=list)


def build_structured_draft_generation_contract(
    *,
    item: ContentWorkItem,
    sales_brief: ContentSalesBrief | None,
    claim_ledger: ContentClaimLedger | None,
    draft_package: ContentDraftPackage | None,
    draft_kind: Literal["section_draft", "full_draft"] = "section_draft",
) -> StructuredDraftGenerationResult:
    blockers = structured_draft_generation_blockers(
        item=item,
        sales_brief=sales_brief,
        claim_ledger=claim_ledger,
        draft_package=draft_package,
    )
    if blockers:
        return StructuredDraftGenerationResult(blockers=blockers)

    if sales_brief is None:
        raise RuntimeError("Sales brief passed structured draft blockers as None.")
    if claim_ledger is None:
        raise RuntimeError("Claim ledger passed structured draft blockers as None.")
    if draft_package is None:
        raise RuntimeError("Draft package passed structured draft blockers as None.")
    final_canonical_url = item.final_canonical_url or item.intended_final_url
    if final_canonical_url is None:
        return StructuredDraftGenerationResult(
            blockers=[
                _blocker(
                    "missing_final_canonical",
                    "Brakuje adresu docelowego",
                    "Generowanie wymaga publicznego adresu docelowego dla treści.",
                    "Uzupełnij publiczny adres docelowy przed generowaniem.",
                )
            ]
        )

    model_input = StructuredDraftGenerationInput(
        work_item_id=item.id,
        draft_kind=draft_kind,
        title=draft_package.title,
        final_canonical_url=final_canonical_url,
        source_public_url=item.source_public_url,
        preview_url=item.preview_url,
        target_reader=sales_brief.target_reader,
        buyer_problem=sales_brief.buyer_problem,
        buyer_trigger=sales_brief.buyer_trigger,
        search_intent=sales_brief.search_intent,
        service_fit=sales_brief.service_fit,
        cta_direction=sales_brief.cta_direction,
        sections=[
            StructuredDraftSectionInput(
                heading=section.heading,
                purpose=section.purpose,
                evidence_ids=section.evidence_ids,
                draft_notes=section.draft_notes,
            )
            for section in draft_package.sections
        ],
        source_facts=[
            StructuredDraftSourceFact(
                evidence_id=fact.evidence_id,
                source_connector=fact.source_connector,
                summary=fact.summary,
            )
            for fact in sales_brief.source_facts
        ],
        claim_markers=[
            StructuredDraftClaimMarker(
                claim_id=entry.id,
                claim_text=entry.claim_text,
                claim_type=entry.claim_type,
                status=entry.status,
                evidence_ids=entry.evidence_ids,
                reviewer_id=entry.reviewer_id,
            )
            for entry in publish_ready_claims(claim_ledger)
        ],
        claims_allowed=draft_package.claims_used,
        claims_removed_or_blocked=draft_package.claims_removed_or_blocked,
        human_review_questions=draft_package.human_review_questions,
    )
    return StructuredDraftGenerationResult(
        contract=StructuredDraftGenerationContract(
            model_input=model_input,
            output_schema=structured_draft_output_schema(),
            system_instruction=_system_instruction(),
            user_instruction=_user_instruction(model_input),
        )
    )


def structured_draft_generation_blockers(
    *,
    item: ContentWorkItem,
    sales_brief: ContentSalesBrief | None,
    claim_ledger: ContentClaimLedger | None,
    draft_package: ContentDraftPackage | None,
) -> list[StructuredDraftGenerationBlocker]:
    blockers: list[StructuredDraftGenerationBlocker] = [
        _blocker(
            cast(StructuredDraftGenerationBlockerCode, blocker.code),
            blocker.label,
            blocker.reason,
            blocker.next_step,
        )
        for blocker in content_workflow_blockers(item, "prepare_draft")
        if blocker.code
        in {
            "missing_evidence",
            "missing_source_connector",
            "missing_final_canonical",
            "invalid_final_canonical",
            "missing_inventory_resolution",
            "duplicate_gate_not_checked",
            "duplicate_or_canonical_risk",
            "missing_preflight",
            "blocked_preflight",
            "missing_preserve_first_plan",
            "missing_sales_brief",
            "missing_claim_ledger",
            "missing_draft_package",
            "missing_measurement_window",
        }
    ]
    if draft_package is None:
        blockers.append(
            _blocker(
                "missing_draft_package",
                "Brakuje paczki szkicu",
                "Model może pisać dopiero z zatwierdzonej paczki szkicu.",
                "Zbuduj paczkę szkicu po planie sprzedażowym i sprawdzeniu twierdzeń.",
            )
        )
    elif draft_package.work_item_id != item.id or (
        item.draft_package_id is not None and draft_package.id != item.draft_package_id
    ):
        blockers.append(
            _blocker(
                "draft_package_mismatch",
                "Paczka szkicu dotyczy innego tematu",
                "Generowanie musi używać paczki przypisanej do tego samego tematu.",
                "Podaj paczkę szkicu dla aktualnego tematu.",
            )
        )
    elif draft_package.publish_ready:
        blockers.append(
            _blocker(
                "draft_package_marked_publish_ready",
                "Paczka szkicu ma zły status",
                "WILQ nie pozwala modelowi oznaczać treści jako gotowej do publikacji.",
                "Utwórz paczkę szkicu w trybie do sprawdzenia.",
            )
        )

    if sales_brief is None:
        blockers.append(
            _blocker(
                "missing_sales_brief",
                "Brakuje planu sprzedażowego",
                "Generowanie bez planu sprzedażowego byłoby promptową improwizacją.",
                "Zbuduj plan sprzedażowy przed generowaniem treści.",
            )
        )
    elif sales_brief.work_item_id != item.id:
        blockers.append(
            _blocker(
                "sales_brief_mismatch",
                "Plan dotyczy innego tematu",
                "Treść musi wynikać z planu sprzedażowego dla tego samego tematu.",
                "Podaj plan sprzedażowy przypisany do aktualnego tematu.",
            )
        )

    if claim_ledger is None:
        blockers.append(
            _blocker(
                "missing_claim_ledger",
                "Brakuje sprawdzenia twierdzeń",
                "Model nie może pisać bez listy dozwolonych i usuniętych twierdzeń.",
                "Zbuduj sprawdzenie twierdzeń przed generowaniem treści.",
            )
        )
    elif claim_ledger.work_item_id != item.id or not claim_ledger_allows_draft(claim_ledger):
        blockers.append(
            _blocker(
                "claim_ledger_blocks_generation",
                "Sprawdzenie twierdzeń blokuje generowanie",
                "Ryzykowne albo niezweryfikowane twierdzenia muszą zostać "
                "usunięte lub zatwierdzone przed pisaniem.",
                "Rozwiąż sprawdzenie twierdzeń przed generowaniem treści.",
            )
        )

    if draft_package is not None:
        if not draft_package.section_to_evidence_map:
            blockers.append(
                _blocker(
                    "missing_evidence_mapping",
                    "Brakuje mapy dowodów",
                    "Każda sekcja musi mieć przypisane dowody źródłowe.",
                    "Uzupełnij mapę sekcji do dowodów przed generowaniem.",
                )
            )
        if not draft_package.human_review_questions:
            blockers.append(
                _blocker(
                    "missing_human_review_questions",
                    "Brakuje pytań do sprawdzenia",
                    "Wygenerowana treść musi wrócić do człowieka z checklistą.",
                    "Dodaj pytania kontrolne do paczki szkicu.",
                )
            )
    return blockers


def structured_draft_output_schema() -> dict[str, object]:
    schema = StructuredDraftOutput.model_json_schema()
    schema["additionalProperties"] = False
    return schema


def _system_instruction() -> str:
    return (
        "Jesteś runtime'em WILQ do przygotowania szkicu treści po polsku. "
        "Pisz wyłącznie z przekazanych faktów, dowodów i dozwolonych twierdzeń. "
        "Nie oznaczaj treści jako gotowej do publikacji. Nie obiecuj pozycji, "
        "leadów, przychodu, pełnej zgodności prawnej ani efektu bez dowodu."
    )


def _user_instruction(model_input: StructuredDraftGenerationInput) -> str:
    return (
        "Przygotuj ustrukturyzowany szkic treści dla WILQ. "
        f"Temat: {model_input.title}. "
        f"Odbiorca: {model_input.target_reader}. "
        f"Problem kupującego: {model_input.buyer_problem}. "
        "Każda sekcja musi wskazywać użyte identyfikatory dowodów. "
        "Używaj wyłącznie claimów z claim_markers/claims_allowed. "
        "Zwróć wynik zgodny ze ścisłym schematem."
    )


def _blocker(
    code: StructuredDraftGenerationBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> StructuredDraftGenerationBlocker:
    return StructuredDraftGenerationBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
