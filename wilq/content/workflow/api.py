from __future__ import annotations

from pydantic import BaseModel, Field

from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefBuildResult,
    ContentSalesBriefSeed,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import (
    ContentDraftPackageBuildResult,
    build_content_draft_package,
)
from wilq.content.inventory.records import (
    ContentInventoryDuplicateRisk,
    ContentInventoryRecord,
    ContentInventoryResolution,
    resolve_content_inventory,
)
from wilq.content.preflight.workflow import (
    ContentPreflightVerdict,
    build_content_preflight_verdict,
)
from wilq.content.workflow.models import ContentWorkItem


class ContentWorkItemPreflightRequest(BaseModel):
    item: ContentWorkItem
    inventory_records: list[ContentInventoryRecord] = Field(default_factory=list)
    duplicate_risk: ContentInventoryDuplicateRisk = "unknown"


class ContentWorkItemPreflightResponse(BaseModel):
    item: ContentWorkItem
    inventory_resolution: ContentInventoryResolution
    preflight_verdict: ContentPreflightVerdict


class ContentWorkItemSalesBriefRequest(BaseModel):
    item: ContentWorkItem
    inventory_records: list[ContentInventoryRecord] = Field(default_factory=list)
    duplicate_risk: ContentInventoryDuplicateRisk = "unknown"
    claim_ledger: ContentClaimLedger
    seed: ContentSalesBriefSeed


class ContentWorkItemSalesBriefResponse(BaseModel):
    item: ContentWorkItem
    inventory_resolution: ContentInventoryResolution
    preflight_verdict: ContentPreflightVerdict
    sales_brief_result: ContentSalesBriefBuildResult


class ContentWorkItemDraftPackageRequest(BaseModel):
    item: ContentWorkItem
    inventory_records: list[ContentInventoryRecord] = Field(default_factory=list)
    duplicate_risk: ContentInventoryDuplicateRisk = "unknown"
    claim_ledger: ContentClaimLedger
    seed: ContentSalesBriefSeed
    sales_brief: ContentSalesBrief | None = None


class ContentWorkItemDraftPackageResponse(BaseModel):
    item: ContentWorkItem
    inventory_resolution: ContentInventoryResolution
    preflight_verdict: ContentPreflightVerdict
    sales_brief_result: ContentSalesBriefBuildResult
    draft_package_result: ContentDraftPackageBuildResult


def build_content_work_item_preflight_response(
    request: ContentWorkItemPreflightRequest,
) -> ContentWorkItemPreflightResponse:
    inventory_resolution = resolve_content_inventory(
        request.inventory_records,
        duplicate_risk=request.duplicate_risk,
    )
    return ContentWorkItemPreflightResponse(
        item=request.item,
        inventory_resolution=inventory_resolution,
        preflight_verdict=build_content_preflight_verdict(
            request.item,
            inventory_resolution,
        ),
    )


def build_content_work_item_sales_brief_response(
    request: ContentWorkItemSalesBriefRequest,
) -> ContentWorkItemSalesBriefResponse:
    inventory_resolution, preflight_verdict = _inventory_and_preflight(
        item=request.item,
        inventory_records=request.inventory_records,
        duplicate_risk=request.duplicate_risk,
    )
    return ContentWorkItemSalesBriefResponse(
        item=request.item,
        inventory_resolution=inventory_resolution,
        preflight_verdict=preflight_verdict,
        sales_brief_result=build_content_sales_brief(
            item=request.item,
            preflight=preflight_verdict,
            inventory=inventory_resolution,
            claim_ledger=request.claim_ledger,
            seed=request.seed,
        ),
    )


def build_content_work_item_draft_package_response(
    request: ContentWorkItemDraftPackageRequest,
) -> ContentWorkItemDraftPackageResponse:
    inventory_resolution, preflight_verdict = _inventory_and_preflight(
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


def _inventory_and_preflight(
    *,
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    duplicate_risk: ContentInventoryDuplicateRisk,
) -> tuple[ContentInventoryResolution, ContentPreflightVerdict]:
    inventory_resolution = resolve_content_inventory(
        inventory_records,
        duplicate_risk=duplicate_risk,
    )
    return (
        inventory_resolution,
        build_content_preflight_verdict(
            item,
            inventory_resolution,
        ),
    )
