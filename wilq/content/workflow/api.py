from __future__ import annotations

from pydantic import BaseModel, Field

from wilq.content.briefs.sales import (
    ContentSalesBriefBuildResult,
    ContentSalesBriefSeed,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger
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
    inventory_resolution = resolve_content_inventory(
        request.inventory_records,
        duplicate_risk=request.duplicate_risk,
    )
    preflight_verdict = build_content_preflight_verdict(
        request.item,
        inventory_resolution,
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
