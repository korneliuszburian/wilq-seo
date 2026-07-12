from __future__ import annotations

from wilq.content.briefs.sales import ContentSalesBriefBuildResult, build_content_sales_brief
from wilq.content.drafts.package import build_content_draft_package
from wilq.content.drafts.structured_generation import (
    build_structured_draft_generation_contract,
)
from wilq.content.drafts.variants import build_content_draft_variants
from wilq.content.knowledge.cards import match_content_knowledge_cards
from wilq.content.workflow.contracts import (
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemDraftVariantsRequest,
    ContentWorkItemDraftVariantsResponse,
    ContentWorkItemStructuredDraftGenerationRequest,
    ContentWorkItemStructuredDraftGenerationResponse,
)
from wilq.content.workflow.stage_preparation import inventory_and_preflight


def build_content_work_item_draft_package_response(
    request: ContentWorkItemDraftPackageRequest,
) -> ContentWorkItemDraftPackageResponse:
    inventory_resolution, preflight_verdict = inventory_and_preflight(
        item=request.item,
        inventory_records=request.inventory_records,
        duplicate_risk=request.duplicate_risk,
    )
    sales_brief_result = (
        ContentSalesBriefBuildResult(brief=request.sales_brief)
        if request.sales_brief is not None
        else build_content_sales_brief(
            item=request.item,
            preflight=preflight_verdict,
            inventory=inventory_resolution,
            claim_ledger=request.claim_ledger,
            seed=request.seed,
            enrichment=request.enrichment,
            knowledge_match=request.knowledge_match
            or match_content_knowledge_cards(request.item),
        )
    )
    return ContentWorkItemDraftPackageResponse(
        item=request.item,
        inventory_resolution=inventory_resolution,
        preflight_verdict=preflight_verdict,
        sales_brief_result=sales_brief_result,
        draft_package_result=build_content_draft_package(
            item=request.item,
            preflight=preflight_verdict,
            sales_brief=sales_brief_result.brief,
            claim_ledger=request.claim_ledger,
        ),
    )


def build_content_work_item_structured_draft_generation_response(
    request: ContentWorkItemStructuredDraftGenerationRequest,
) -> ContentWorkItemStructuredDraftGenerationResponse:
    return ContentWorkItemStructuredDraftGenerationResponse(
        item=request.item,
        structured_generation_result=build_structured_draft_generation_contract(
            item=request.item,
            sales_brief=request.sales_brief,
            claim_ledger=request.claim_ledger,
            draft_package=request.draft_package,
        ),
    )


def build_content_work_item_draft_variants_response(
    request: ContentWorkItemDraftVariantsRequest,
) -> ContentWorkItemDraftVariantsResponse:
    return ContentWorkItemDraftVariantsResponse(
        item=request.item,
        draft_variants_result=build_content_draft_variants(
            item=request.item,
            sales_brief=request.sales_brief,
            claim_ledger=request.claim_ledger,
            draft_package=request.draft_package,
        ),
    )
