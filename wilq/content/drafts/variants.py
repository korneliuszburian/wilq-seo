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

ContentDraftVariantSelectionDimensionName = Literal[
    "evidence_coverage",
    "service_fit",
    "buyer_problem_fit",
    "cta_fit",
    "duplicate_risk",
    "quality_review_dependency",
]

ContentDraftVariantSelectionStatus = Literal[
    "pass",
    "review_required",
    "blocked",
    "not_applicable",
]


class ContentDraftVariantSelectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = "content_draft_variant_selection_guard_v1"
    label: str = "Jawny wybór wariantu bez magic score"
    magic_score_used: Literal[False] = False
    rules: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)


class ContentDraftVariantComparisonDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_kind: ContentDraftVariantKind
    dimension: ContentDraftVariantSelectionDimensionName
    status: ContentDraftVariantSelectionStatus
    label: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


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
    recommended_variant_id: str | None = None
    comparison_dimensions: list[ContentDraftVariantComparisonDimension] = Field(
        default_factory=list
    )
    selection_policy: ContentDraftVariantSelectionPolicy = Field(
        default_factory=lambda: ContentDraftVariantSelectionPolicy(
            rules=[
                "Wariant może być rekomendowany tylko z evidence_ids i source_connectors.",
                "Refresh zachowujący canonical wygrywa przy preserve-first plan.",
                "Wariant usługowy wymaga human review, gdy wiedza jest review-required.",
                "FAQ jest wariantem wspierającym, nie domyślnym wariantem głównym.",
                "Żaden wariant nie odblokowuje publikacji ani WordPress write.",
            ],
            blocked_claims=[
                "publish_ready",
                "wordpress_write_allowed",
                "seo_success_before_measurement",
                "service_or_penalty_guarantee",
            ],
        )
    )
    safe_next_step: str = (
        "Wybierz rekomendowany wariant do quality review; publikacja i WordPress write "
        "pozostają zablokowane."
    )


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
        return ContentDraftVariantsResult(
            blockers=base_generation.blockers,
            safe_next_step=(
                "Uzupełnij Sales Brief, Claim Ledger i Draft Package przed wyborem "
                "wariantu."
            ),
        )
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
            return ContentDraftVariantsResult(
                blockers=generation_result.blockers,
                safe_next_step=(
                    "Usuń blokery structured generation przed porównaniem wariantów."
                ),
            )
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
    recommended_variant_id = _recommended_variant_id(
        item=item,
        sales_brief=sales_brief,
        variants=variants,
    )
    return ContentDraftVariantsResult(
        variants=variants,
        recommended_variant_id=recommended_variant_id,
        comparison_dimensions=_comparison_dimensions(
            item=item,
            sales_brief=sales_brief,
            variants=variants,
        ),
        safe_next_step=_safe_next_step(recommended_variant_id),
    )


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


def _recommended_variant_id(
    *,
    item: ContentWorkItem,
    sales_brief: ContentSalesBrief,
    variants: list[ContentDraftVariant],
) -> str | None:
    if not variants:
        return None
    if not sales_brief.evidence_ids or not sales_brief.source_connectors:
        return None

    variant_by_kind = {variant.variant_kind: variant for variant in variants}
    recommended_mode = sales_brief.operations_context.recommended_mode
    if (
        item.preserve_first_plan_status == "approved"
        or recommended_mode == "refresh"
    ) and "preserve_first_refresh" in variant_by_kind:
        return variant_by_kind["preserve_first_refresh"].id
    if sales_brief.buyer_problem and "problem_led" in variant_by_kind:
        return variant_by_kind["problem_led"].id
    return variants[0].id


def _comparison_dimensions(
    *,
    item: ContentWorkItem,
    sales_brief: ContentSalesBrief,
    variants: list[ContentDraftVariant],
) -> list[ContentDraftVariantComparisonDimension]:
    dimensions: list[ContentDraftVariantComparisonDimension] = []
    for variant in variants:
        dimensions.extend(
            [
                _dimension(
                    variant,
                    "evidence_coverage",
                    _evidence_status(sales_brief),
                    "Pokrycie dowodami",
                    _evidence_reason(sales_brief),
                    sales_brief,
                ),
                _dimension(
                    variant,
                    "service_fit",
                    _service_fit_status(sales_brief, variant.variant_kind),
                    "Dopasowanie usługi",
                    _service_fit_reason(sales_brief, variant.variant_kind),
                    sales_brief,
                ),
                _dimension(
                    variant,
                    "buyer_problem_fit",
                    _buyer_problem_status(sales_brief, variant.variant_kind),
                    "Dopasowanie problemu kupującego",
                    _buyer_problem_reason(sales_brief, variant.variant_kind),
                    sales_brief,
                ),
                _dimension(
                    variant,
                    "cta_fit",
                    _cta_status(sales_brief),
                    "CTA bez zakazanych obietnic",
                    _cta_reason(sales_brief),
                    sales_brief,
                ),
                _dimension(
                    variant,
                    "duplicate_risk",
                    _duplicate_risk_status(item, variant.variant_kind),
                    "Ryzyko duplikacji / canonical",
                    _duplicate_risk_reason(item, variant.variant_kind),
                    sales_brief,
                ),
                _dimension(
                    variant,
                    "quality_review_dependency",
                    "review_required",
                    "Zależność od quality review",
                    (
                        "Każdy wariant pozostaje szkicem do kontroli claim ledger, "
                        "human review i bez zapisu do WordPress."
                    ),
                    sales_brief,
                ),
            ]
        )
    return dimensions


def _dimension(
    variant: ContentDraftVariant,
    dimension: ContentDraftVariantSelectionDimensionName,
    status: ContentDraftVariantSelectionStatus,
    label: str,
    reason: str,
    sales_brief: ContentSalesBrief,
) -> ContentDraftVariantComparisonDimension:
    return ContentDraftVariantComparisonDimension(
        variant_id=variant.id,
        variant_kind=variant.variant_kind,
        dimension=dimension,
        status=status,
        label=label,
        reason=reason,
        evidence_ids=sales_brief.evidence_ids,
        source_connectors=sales_brief.source_connectors,
    )


def _evidence_status(
    sales_brief: ContentSalesBrief,
) -> ContentDraftVariantSelectionStatus:
    if sales_brief.missing_evidence:
        return "blocked"
    if not sales_brief.evidence_ids or not sales_brief.source_connectors:
        return "blocked"
    return "pass"


def _evidence_reason(sales_brief: ContentSalesBrief) -> str:
    if sales_brief.missing_evidence:
        return "Brief ma brakujące wymagania dowodowe, więc wariant nie może być wybrany."
    if not sales_brief.evidence_ids or not sales_brief.source_connectors:
        return "Brak evidence_ids albo source_connectors blokuje rekomendację wariantu."
    return "Wariant dziedziczy evidence_ids i source_connectors z Sales Brief."


def _service_fit_status(
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> ContentDraftVariantSelectionStatus:
    if not sales_brief.service_fit:
        return "blocked"
    if _knowledge_needs_review(sales_brief):
        return "review_required"
    if variant_kind == "faq_supporting":
        return "not_applicable"
    return "pass"


def _service_fit_reason(
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> str:
    if not sales_brief.service_fit:
        return "Brak service fit blokuje wariant usługowy."
    if _knowledge_needs_review(sales_brief):
        return "Service fit istnieje, ale knowledge constraints wymagają review ownera."
    if variant_kind == "faq_supporting":
        return "FAQ wspiera temat, ale nie powinien być główną stroną usługową."
    return f"Wariant może korzystać z service fit: {sales_brief.service_fit}"


def _buyer_problem_status(
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> ContentDraftVariantSelectionStatus:
    if not sales_brief.buyer_problem:
        return "blocked"
    if variant_kind in {"problem_led", "preserve_first_refresh"}:
        return "pass"
    return "review_required"


def _buyer_problem_reason(
    sales_brief: ContentSalesBrief,
    variant_kind: ContentDraftVariantKind,
) -> str:
    if not sales_brief.buyer_problem:
        return "Brak problemu kupującego blokuje wybór wariantu."
    if variant_kind == "problem_led":
        return f"Ten wariant bezpośrednio prowadzi od problemu: {sales_brief.buyer_problem}"
    if variant_kind == "preserve_first_refresh":
        return "Refresh może zachować istniejący URL i dopisać problem bez duplikacji."
    return "Wariant nie prowadzi od problemu klienta, więc wymaga kontroli roli w treści."


def _cta_status(sales_brief: ContentSalesBrief) -> ContentDraftVariantSelectionStatus:
    if not sales_brief.cta_direction:
        return "blocked"
    if sales_brief.forbidden_claims:
        return "review_required"
    return "pass"


def _cta_reason(sales_brief: ContentSalesBrief) -> str:
    if not sales_brief.cta_direction:
        return "Brak CTA blokuje wybór wariantu."
    if sales_brief.forbidden_claims:
        return "CTA istnieje, ale forbidden claims muszą zostać sprawdzone w quality review."
    return f"CTA jest dostępne bez odblokowania publikacji: {sales_brief.cta_direction}"


def _duplicate_risk_status(
    item: ContentWorkItem,
    variant_kind: ContentDraftVariantKind,
) -> ContentDraftVariantSelectionStatus:
    if item.duplicate_status != "checked":
        return "review_required"
    if item.preserve_first_plan_status == "approved":
        if variant_kind == "preserve_first_refresh":
            return "pass"
        return "review_required"
    return "pass"


def _duplicate_risk_reason(
    item: ContentWorkItem,
    variant_kind: ContentDraftVariantKind,
) -> str:
    if item.duplicate_status != "checked":
        return "Duplicate/canonical risk nie został w pełni sprawdzony."
    if item.preserve_first_plan_status == "approved":
        if variant_kind == "preserve_first_refresh":
            return "Preserve-first plan jest zatwierdzony, więc refresh jest najbezpieczniejszy."
        return "Nowy układ może zwiększyć ryzyko duplikacji, więc wymaga kontroli."
    return "Duplicate/canonical check nie blokuje tego wariantu."


def _knowledge_needs_review(sales_brief: ContentSalesBrief) -> bool:
    review_markers = {"source_backed_knowledge_claim", "review_required", "stale"}
    return any(
        constraint.constraint_type in review_markers
        or "review" in constraint.reason.lower()
        for constraint in sales_brief.knowledge_constraints
    )


def _safe_next_step(recommended_variant_id: str | None) -> str:
    if recommended_variant_id is None:
        return (
            "Nie wybieraj wariantu: uzupełnij evidence_ids, source_connectors i blokery "
            "briefu przed quality review."
        )
    return (
        f"Sprawdź wariant {recommended_variant_id} w quality review; publikacja i "
        "WordPress write pozostają zablokowane."
    )
