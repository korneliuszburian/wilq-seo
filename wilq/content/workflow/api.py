from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefBuildResult,
    ContentSalesBriefSeed,
    ContentSalesBriefSourceFact,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger, ContentClaimLedgerEntry
from wilq.content.drafts.package import (
    ContentDraftPackage,
    ContentDraftPackageBuildResult,
    build_content_draft_package,
)
from wilq.content.handoff.wordpress import (
    ContentWordPressDraftAuditEnvelope,
    ContentWordPressDraftHandoff,
    ContentWordPressDraftHandoffResult,
    build_content_wordpress_draft_handoff,
)
from wilq.content.inventory.records import (
    ContentInventoryDuplicateRisk,
    ContentInventoryRecord,
    ContentInventoryResolution,
    resolve_content_inventory,
)
from wilq.content.measurement.window import (
    ContentDateRange,
    ContentMeasurementMetric,
    ContentMeasurementWindowBlocker,
    ContentMeasurementWindowBuildResult,
    apply_content_measurement_window_to_work_item,
    build_content_measurement_window,
    content_measurement_window_outcome_blockers,
)
from wilq.content.preflight.workflow import (
    ContentPreflightVerdict,
    build_content_preflight_verdict,
)
from wilq.content.review.human import (
    ContentHumanReview,
    ContentHumanReviewBlocker,
    apply_content_human_review_to_work_item,
    content_human_review_allows_wordpress_handoff,
    content_human_review_blockers,
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


class ContentWorkItemHumanReviewRequest(BaseModel):
    item: ContentWorkItem
    review: ContentHumanReview
    draft_package: ContentDraftPackage | None = None
    claim_ledger: ContentClaimLedger | None = None


class ContentWorkItemHumanReviewResponse(BaseModel):
    item: ContentWorkItem
    reviewed_item: ContentWorkItem
    review: ContentHumanReview
    blockers: list[ContentHumanReviewBlocker] = Field(default_factory=list)
    wordpress_handoff_allowed: bool = False


class ContentWorkItemWordPressDraftHandoffRequest(BaseModel):
    item: ContentWorkItem
    draft_package: ContentDraftPackage | None = None
    human_review: ContentHumanReview | None = None
    audit: ContentWordPressDraftAuditEnvelope | None = None


class ContentWorkItemWordPressDraftHandoffResponse(BaseModel):
    item: ContentWorkItem
    handoff_result: ContentWordPressDraftHandoffResult


class ContentWorkItemMeasurementWindowRequest(BaseModel):
    item: ContentWorkItem
    handoff: ContentWordPressDraftHandoff | None = None
    baseline_period: ContentDateRange
    observation_period: ContentDateRange
    allowed_metrics: list[ContentMeasurementMetric] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentWorkItemMeasurementWindowResponse(BaseModel):
    item: ContentWorkItem
    updated_item: ContentWorkItem
    measurement_window_result: ContentMeasurementWindowBuildResult
    outcome_blockers: list[ContentMeasurementWindowBlocker] = Field(default_factory=list)


class ContentWorkItemWorkflowSnapshotResponse(BaseModel):
    preflight: ContentWorkItemPreflightResponse
    sales_brief: ContentWorkItemSalesBriefResponse
    draft_package: ContentWorkItemDraftPackageResponse
    human_review: ContentWorkItemHumanReviewResponse
    wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponse
    measurement_window: ContentWorkItemMeasurementWindowResponse


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


def build_content_work_item_human_review_response(
    request: ContentWorkItemHumanReviewRequest,
) -> ContentWorkItemHumanReviewResponse:
    blockers = content_human_review_blockers(
        item=request.item,
        review=request.review,
        draft_package=request.draft_package,
        claim_ledger=request.claim_ledger,
    )
    reviewed_item = (
        apply_content_human_review_to_work_item(request.item, request.review)
        if not blockers
        else request.item
    )
    return ContentWorkItemHumanReviewResponse(
        item=request.item,
        reviewed_item=reviewed_item,
        review=request.review,
        blockers=blockers,
        wordpress_handoff_allowed=not blockers
        and content_human_review_allows_wordpress_handoff(
            item=request.item,
            review=request.review,
            draft_package=request.draft_package,
        ),
    )


def build_content_work_item_wordpress_draft_handoff_response(
    request: ContentWorkItemWordPressDraftHandoffRequest,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    return ContentWorkItemWordPressDraftHandoffResponse(
        item=request.item,
        handoff_result=build_content_wordpress_draft_handoff(
            item=request.item,
            draft_package=request.draft_package,
            human_review=request.human_review,
            audit=request.audit,
        ),
    )


def build_content_work_item_measurement_window_response(
    request: ContentWorkItemMeasurementWindowRequest,
) -> ContentWorkItemMeasurementWindowResponse:
    measurement_result = build_content_measurement_window(
        item=request.item,
        handoff=request.handoff,
        baseline_period=request.baseline_period,
        observation_period=request.observation_period,
        allowed_metrics=request.allowed_metrics,
        source_connectors=request.source_connectors,
    )
    updated_item = (
        apply_content_measurement_window_to_work_item(
            request.item,
            measurement_result.window,
        )
        if measurement_result.window is not None
        else request.item
    )
    return ContentWorkItemMeasurementWindowResponse(
        item=request.item,
        updated_item=updated_item,
        measurement_window_result=measurement_result,
        outcome_blockers=(
            content_measurement_window_outcome_blockers(measurement_result.window)
            if measurement_result.window is not None
            else []
        ),
    )


def build_content_work_item_control_snapshot_response() -> ContentWorkItemWorkflowSnapshotResponse:
    item = _control_item()
    inventory_records = [_control_inventory_record()]
    claim_ledger = _control_claim_ledger()
    seed = _control_sales_brief_seed()

    preflight = build_content_work_item_preflight_response(
        ContentWorkItemPreflightRequest(
            item=item,
            inventory_records=inventory_records,
            duplicate_risk="clear",
        )
    )
    sales_brief = build_content_work_item_sales_brief_response(
        ContentWorkItemSalesBriefRequest(
            item=item.model_copy(
                update={
                    "preserve_first_plan_status": "approved",
                    "measurement_window_status": "planned",
                    "measurement_window_id": "measure_bdo",
                }
            ),
            inventory_records=inventory_records,
            duplicate_risk="clear",
            claim_ledger=claim_ledger,
            seed=seed,
        )
    )
    brief = sales_brief.sales_brief_result.brief
    draft_package = build_content_work_item_draft_package_response(
        ContentWorkItemDraftPackageRequest(
            item=item.model_copy(
                update={
                    "preflight_status": "draft_allowed",
                    "preserve_first_plan_status": "approved",
                    "sales_brief_status": "approved",
                    "sales_brief_id": None if brief is None else brief.id,
                    "claim_ledger_status": "approved",
                    "claim_ledger_id": claim_ledger.id,
                    "measurement_window_status": "planned",
                    "measurement_window_id": "measure_bdo",
                }
            ),
            inventory_records=inventory_records,
            duplicate_risk="clear",
            claim_ledger=claim_ledger,
            seed=seed,
            sales_brief=brief,
        )
    )
    draft = draft_package.draft_package_result.draft_package
    human_review_payload = _control_human_review(None if draft is None else draft.id)
    human_review = build_content_work_item_human_review_response(
        ContentWorkItemHumanReviewRequest(
            item=item.model_copy(
                update={
                    "preflight_status": "handoff_allowed",
                    "preserve_first_plan_status": "approved",
                    "sales_brief_status": "approved",
                    "sales_brief_id": None if brief is None else brief.id,
                    "claim_ledger_status": "approved",
                    "claim_ledger_id": claim_ledger.id,
                    "draft_package_status": "ready",
                    "draft_package_id": None if draft is None else draft.id,
                    "audit_status": "recorded",
                    "audit_id": "audit_bdo",
                    "measurement_window_status": "planned",
                    "measurement_window_id": "measure_bdo",
                }
            ),
            review=human_review_payload,
            draft_package=draft,
            claim_ledger=claim_ledger,
        )
    )
    wordpress_handoff = build_content_work_item_wordpress_draft_handoff_response(
        ContentWorkItemWordPressDraftHandoffRequest(
            item=human_review.reviewed_item,
            draft_package=draft,
            human_review=human_review_payload,
            audit=_control_handoff_audit(),
        )
    )
    measurement_window = build_content_work_item_measurement_window_response(
        ContentWorkItemMeasurementWindowRequest(
            item=item.model_copy(
                update={
                    "preflight_status": "handoff_allowed",
                    "preserve_first_plan_status": "approved",
                    "sales_brief_status": "approved",
                    "sales_brief_id": None if brief is None else brief.id,
                    "claim_ledger_status": "approved",
                    "claim_ledger_id": claim_ledger.id,
                    "draft_package_status": "ready",
                    "draft_package_id": None if draft is None else draft.id,
                    "human_review_status": "approved",
                    "human_review_id": human_review_payload.id,
                    "audit_status": "recorded",
                    "audit_id": "audit_bdo",
                    "measurement_window_status": "missing",
                    "measurement_window_id": None,
                }
            ),
            handoff=wordpress_handoff.handoff_result.handoff,
            baseline_period=ContentDateRange(start=date(2026, 5, 1), end=date(2026, 5, 31)),
            observation_period=ContentDateRange(start=date(2026, 7, 1), end=date(2026, 7, 31)),
            allowed_metrics=["gsc_clicks", "gsc_impressions", "ga4_engaged_sessions"],
            source_connectors=["google_search_console", "google_analytics_4"],
        )
    )
    return ContentWorkItemWorkflowSnapshotResponse(
        preflight=preflight,
        sales_brief=sales_brief,
        draft_package=draft_package,
        human_review=human_review,
        wordpress_handoff=wordpress_handoff,
        measurement_window=measurement_window,
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


def _control_item() -> ContentWorkItem:
    return ContentWorkItem(
        id="content_work_item_bdo",
        topic="BDO dla firm",
        source_public_url="https://ekologus.pl/bdo/",
        final_canonical_url="https://ekologus.pl/bdo/",
        intended_final_url="https://ekologus.pl/bdo/",
        preview_url="https://ekologus.dev.proudsite.pl/bdo/",
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
        inventory_status="resolved",
        canonical_status="resolved",
        duplicate_status="checked",
    )


def _control_inventory_record() -> ContentInventoryRecord:
    return ContentInventoryRecord(
        id="inventory_bdo",
        url="https://ekologus.pl/bdo/",
        final_canonical_url="https://ekologus.pl/bdo/",
        intended_final_url="https://ekologus.pl/bdo/",
        preview_url="https://ekologus.dev.proudsite.pl/bdo/",
        content_status="published",
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_bdo"],
        title="BDO dla firm",
        h1="BDO dla firm",
        topic_tags=["bdo"],
    )


def _control_claim_ledger() -> ContentClaimLedger:
    return ContentClaimLedger(
        id="claim_ledger_bdo",
        work_item_id="content_work_item_bdo",
        reviewed_by="wilku",
        entries=[
            ContentClaimLedgerEntry(
                id="claim_general_bdo",
                claim_text="Ekologus pomaga firmom uporządkować obowiązki BDO.",
                claim_type="service_claim",
                status="allowed_with_evidence",
                evidence_ids=["ev_wp_bdo"],
                reason="Claim ma przypisany dowód źródłowy.",
                reviewer_id="wilku",
            )
        ],
    )


def _control_sales_brief_seed() -> ContentSalesBriefSeed:
    return ContentSalesBriefSeed(
        target_reader="właściciel firmy, który musi uporządkować obowiązki BDO",
        buyer_problem="nie wie, czy i jak musi prowadzić ewidencję BDO",
        buyer_trigger="zbliża się kontrola albo termin aktualizacji danych",
        search_intent="informacyjno-usługowy",
        service_fit="konsultacja i obsługa środowiskowa Ekologus",
        h1_direction="BDO dla firm: co trzeba sprawdzić przed działaniem",
        h2_direction=["Kogo dotyczy BDO", "Co warto przygotować przed konsultacją"],
        faq_direction=["Czy każda firma musi mieć BDO?"],
        cta_direction="Zaproponuj kontakt w celu sprawdzenia sytuacji firmy.",
        internal_link_direction=["https://ekologus.pl/kontakt/"],
        source_facts=[
            ContentSalesBriefSourceFact(
                evidence_id="ev_gsc_bdo",
                source_connector="google_search_console",
                summary="GSC pokazuje popyt na temat BDO.",
            ),
            ContentSalesBriefSourceFact(
                evidence_id="ev_wp_bdo",
                source_connector="wordpress_ekologus",
                summary="WordPress inventory potwierdza istniejącą treść BDO.",
            ),
        ],
        missing_evidence=[],
    )


def _control_human_review(draft_package_id: str | None) -> ContentHumanReview:
    return ContentHumanReview(
        id="human_review_bdo",
        work_item_id="content_work_item_bdo",
        stage="draft_package",
        reviewed_by="wilku",
        decision="approved",
        notes="Szkic może iść dalej jako WordPress draft.",
        checked_items=["brief zgodny z dowodami", "claimy bez gwarancji efektu"],
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        blocked_claims_handled=[],
        draft_package_id=draft_package_id,
    )


def _control_handoff_audit() -> ContentWordPressDraftAuditEnvelope:
    return ContentWordPressDraftAuditEnvelope(
        audit_id="audit_bdo",
        actor="wilku",
        reason="Zatwierdzony szkic może trafić do WordPress jako draft.",
        evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
        human_review_id="human_review_bdo",
    )
