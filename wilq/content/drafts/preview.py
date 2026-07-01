from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
)

StructuredDraftPreviewBlockerCode = Literal[
    "missing_output",
    "missing_contract",
    "claims_need_review",
    "missing_source_facts",
    "section_missing_evidence",
    "unknown_evidence_reference",
    "unknown_claim_reference",
]


class StructuredDraftPreviewBlocker(BaseModel):
    code: StructuredDraftPreviewBlockerCode
    label: str
    reason: str
    next_step: str


class StructuredDraftPreviewSection(BaseModel):
    heading: str
    body_markdown: str
    evidence_ids: list[str] = Field(default_factory=list)
    claims_used: list[str] = Field(default_factory=list)


class StructuredDraftPreview(BaseModel):
    title: str
    meta_title: str
    meta_description: str
    h1: str
    sections: list[StructuredDraftPreviewSection] = Field(default_factory=list)
    faq: list[str] = Field(default_factory=list)
    cta: str
    internal_links: list[str] = Field(default_factory=list)
    source_facts_used: list[str] = Field(default_factory=list)
    forbidden_claims_avoided: list[str] = Field(default_factory=list)
    human_review_checklist: list[str] = Field(default_factory=list)
    publish_ready: Literal[False] = False


class StructuredDraftPreviewResult(BaseModel):
    preview: StructuredDraftPreview | None = None
    blockers: list[StructuredDraftPreviewBlocker] = Field(default_factory=list)


def build_structured_draft_preview(
    *,
    output: StructuredDraftOutput | None,
    contract: StructuredDraftGenerationContract | None,
) -> StructuredDraftPreviewResult:
    blockers = structured_draft_preview_blockers(output=output, contract=contract)
    if blockers:
        return StructuredDraftPreviewResult(blockers=blockers)

    if output is None:
        raise RuntimeError("Structured draft output passed preview blockers as None.")
    return StructuredDraftPreviewResult(
        preview=StructuredDraftPreview(
            title=output.title,
            meta_title=output.meta_title,
            meta_description=output.meta_description,
            h1=output.h1,
            sections=[
                StructuredDraftPreviewSection(
                    heading=section.heading,
                    body_markdown=section.body_markdown,
                    evidence_ids=section.evidence_ids,
                    claims_used=section.claims_used,
                )
                for section in output.sections
            ],
            faq=output.faq,
            cta=output.cta,
            internal_links=output.internal_links,
            source_facts_used=output.source_facts_used,
            forbidden_claims_avoided=output.forbidden_claims_avoided,
            human_review_checklist=output.human_review_checklist,
        )
    )


def structured_draft_preview_blockers(
    *,
    output: StructuredDraftOutput | None,
    contract: StructuredDraftGenerationContract | None,
) -> list[StructuredDraftPreviewBlocker]:
    blockers: list[StructuredDraftPreviewBlocker] = []
    if output is None:
        blockers.append(
            _blocker(
                "missing_output",
                "Brakuje szkicu",
                "Podgląd wymaga ustrukturyzowanego szkicu z runtime WILQ.",
                "Najpierw wygeneruj albo wczytaj ustrukturyzowany szkic.",
            )
        )
    if contract is None:
        blockers.append(
            _blocker(
                "missing_contract",
                "Brakuje kontraktu szkicu",
                "Nie można sprawdzić szkicu bez kontraktu, z którego powstał.",
                "Użyj kontraktu generowania powiązanego z tym szkicem.",
            )
        )
    if output is None or contract is None:
        return blockers

    if output.claims_needing_review:
        blockers.append(
            _blocker(
                "claims_need_review",
                "Szkic ma twierdzenia do sprawdzenia",
                "WILQ nie pokaże szkicu jako gotowego do przekazania, gdy są "
                "twierdzenia wymagające decyzji człowieka.",
                "Usuń albo zatwierdź wskazane twierdzenia przed kolejnym krokiem.",
            )
        )
    if not output.source_facts_used:
        blockers.append(
            _blocker(
                "missing_source_facts",
                "Szkic nie wskazuje użytych dowodów",
                "Każdy szkic musi pokazać, z których dowodów korzysta.",
                "Wygeneruj szkic ponownie z mapą dowodów.",
            )
        )

    allowed_evidence_ids = _contract_evidence_ids(contract)
    referenced_evidence_ids = _output_evidence_ids(output)
    missing_section_evidence = any(not section.evidence_ids for section in output.sections)
    if missing_section_evidence:
        blockers.append(
            _blocker(
                "section_missing_evidence",
                "Sekcja nie ma dowodów",
                "Każda sekcja szkicu musi zachować powiązanie z dowodami.",
                "Uzupełnij mapę dowodów dla każdej sekcji.",
            )
        )

    unknown_ids = sorted(referenced_evidence_ids.difference(allowed_evidence_ids))
    if unknown_ids:
        blockers.append(
            _blocker(
                "unknown_evidence_reference",
                "Szkic wskazuje obcy dowód",
                "Szkic może używać tylko dowodów z kontraktu WILQ.",
                "Usuń obce dowody ze szkicu: " + ", ".join(unknown_ids),
            )
        )

    allowed_claims = set(contract.model_input.claims_allowed)
    used_claims = _output_claims(output)
    unknown_claims = sorted(used_claims.difference(allowed_claims))
    if unknown_claims:
        blockers.append(
            _blocker(
                "unknown_claim_reference",
                "Szkic używa claimu spoza kontraktu",
                "Podgląd może pokazać tylko twierdzenia dopuszczone przez kontrakt WILQ.",
                "Usuń obce twierdzenia ze szkicu: " + "; ".join(unknown_claims),
            )
        )
    return blockers


def _contract_evidence_ids(contract: StructuredDraftGenerationContract) -> set[str]:
    values = {fact.evidence_id for fact in contract.model_input.source_facts}
    for section in contract.model_input.sections:
        values.update(section.evidence_ids)
    return {value for value in values if value}


def _output_evidence_ids(output: StructuredDraftOutput) -> set[str]:
    values = set(output.source_facts_used)
    for section in output.sections:
        values.update(section.evidence_ids)
    return {value for value in values if value}


def _output_claims(output: StructuredDraftOutput) -> set[str]:
    values: set[str] = set()
    for section in output.sections:
        values.update(section.claims_used)
    return {value for value in values if value}


def _blocker(
    code: StructuredDraftPreviewBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> StructuredDraftPreviewBlocker:
    return StructuredDraftPreviewBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )
