from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage, ContentDraftSection
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationBlocker,
    StructuredDraftGenerationResult,
    build_structured_draft_generation_contract,
)
from wilq.content.workflow.models import ContentWorkItem

ContentDraftVariantKind = Literal[
    "preserve_first_refresh",
    "problem_led",
    "service_led",
    "faq_supporting",
]


class ContentDraftVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    work_item_id: str
    variant_kind: ContentDraftVariantKind
    label: str
    rationale: str
    draft_package_id: str
    generation_result: StructuredDraftGenerationResult
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    claims_removed_or_blocked: list[str] = Field(default_factory=list)
    publish_ready: Literal[False] = False
    wordpress_write_allowed: Literal[False] = False


class ContentDraftVariantsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variants: list[ContentDraftVariant] = Field(default_factory=list)
    blockers: list[StructuredDraftGenerationBlocker] = Field(default_factory=list)


def build_content_draft_variants(
    *,
    item: ContentWorkItem,
    sales_brief: ContentSalesBrief | None,
    claim_ledger: ContentClaimLedger | None,
    draft_package: ContentDraftPackage | None,
) -> ContentDraftVariantsResult:
    base_generation = build_structured_draft_generation_contract(
        item=item,
        sales_brief=sales_brief,
        claim_ledger=claim_ledger,
        draft_package=draft_package,
        draft_kind="section_draft",
    )
    if base_generation.blockers:
        return ContentDraftVariantsResult(blockers=base_generation.blockers)
    if sales_brief is None or claim_ledger is None or draft_package is None:
        raise RuntimeError("Draft variants passed generation blockers with missing input.")

    variants: list[ContentDraftVariant] = []
    for variant_kind in _variant_kinds(sales_brief):
        variant_package = _variant_package(draft_package, sales_brief, variant_kind)
        variant_item = item.model_copy(
            update={
                "draft_package_status": "ready",
                "draft_package_id": variant_package.id,
            }
        )
        generation_result = build_structured_draft_generation_contract(
            item=variant_item,
            sales_brief=sales_brief,
            claim_ledger=claim_ledger,
            draft_package=variant_package,
            draft_kind="section_draft",
        )
        if generation_result.blockers:
            return ContentDraftVariantsResult(blockers=generation_result.blockers)
        variants.append(
            ContentDraftVariant(
                id=f"draft_variant_{variant_kind}_{item.id}",
                work_item_id=item.id,
                variant_kind=variant_kind,
                label=_variant_label(variant_kind),
                rationale=_variant_rationale(sales_brief, variant_kind),
                draft_package_id=variant_package.id,
                generation_result=generation_result,
                evidence_ids=sales_brief.evidence_ids,
                source_connectors=sales_brief.source_connectors,
                claims_removed_or_blocked=draft_package.claims_removed_or_blocked,
            )
        )
    return ContentDraftVariantsResult(variants=variants)


def _variant_kinds(sales_brief: ContentSalesBrief) -> list[ContentDraftVariantKind]:
    kinds: list[ContentDraftVariantKind] = [
        "preserve_first_refresh",
        "problem_led",
        "service_led",
    ]
    if sales_brief.faq_direction:
        kinds.append("faq_supporting")
    return kinds


def _variant_package(
    draft_package: ContentDraftPackage,
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> ContentDraftPackage:
    return draft_package.model_copy(
        update={
            "id": f"{draft_package.id}_{variant_kind}",
            "draft_kind": "outline",
            "title": _variant_title(sales_brief, variant_kind),
            "sections": [
                _variant_section(section, sales_brief, variant_kind)
                for section in draft_package.sections
            ],
            "publish_ready": False,
        }
    )


def _variant_section(
    section: ContentDraftSection,
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> ContentDraftSection:
    return section.model_copy(
        update={
            "draft_notes": [
                *section.draft_notes,
                _variant_note(sales_brief, variant_kind),
            ]
        }
    )


def _variant_title(
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> str:
    if variant_kind == "problem_led":
        return f"{sales_brief.h1_direction}: problem klienta i następny krok"
    if variant_kind == "service_led":
        return f"{sales_brief.h1_direction}: jak Ekologus może pomóc"
    if variant_kind == "faq_supporting":
        return f"{sales_brief.h1_direction}: pytania i odpowiedzi"
    return f"{sales_brief.h1_direction}: odświeżenie istniejącej treści"


def _variant_label(variant_kind: ContentDraftVariantKind) -> str:
    labels = {
        "preserve_first_refresh": "Odświeżenie istniejącej treści",
        "problem_led": "Wariant prowadzony problemem klienta",
        "service_led": "Wariant prowadzony usługą Ekologus",
        "faq_supporting": "Wariant FAQ / treść wspierająca",
    }
    return labels[variant_kind]


def _variant_rationale(
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> str:
    if variant_kind == "problem_led":
        return f"Akcentuje problem: {sales_brief.buyer_problem}"
    if variant_kind == "service_led":
        return f"Akcentuje dopasowanie usługi: {sales_brief.service_fit}"
    if variant_kind == "faq_supporting":
        return "Używa pytań z briefu jako defensywnej treści wspierającej."
    return sales_brief.existing_content_plan


def _variant_note(
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> str:
    if variant_kind == "problem_led":
        return f"Prowadź od problemu kupującego: {sales_brief.buyer_problem}"
    if variant_kind == "service_led":
        return f"Pokaż service fit bez gwarancji: {sales_brief.service_fit}"
    if variant_kind == "faq_supporting":
        return "Odpowiadaj krótko, z dowodami i bez nowych claimów."
    return "Zachowaj preserve-first: ulepsz istniejącą treść zamiast tworzyć duplikat."
