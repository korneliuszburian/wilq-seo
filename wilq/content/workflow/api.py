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
from wilq.schemas import ContentDecisionItem, ContentDiagnosticsResponse


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
    review: ContentHumanReview | None = None
    draft_package: ContentDraftPackage | None = None
    claim_ledger: ContentClaimLedger | None = None


class ContentWorkItemHumanReviewResponse(BaseModel):
    item: ContentWorkItem
    reviewed_item: ContentWorkItem
    review: ContentHumanReview | None = None
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
        if request.review is not None and not blockers
        else request.item
    )
    return ContentWorkItemHumanReviewResponse(
        item=request.item,
        reviewed_item=reviewed_item,
        review=request.review,
        blockers=blockers,
        wordpress_handoff_allowed=not blockers
        and request.review is not None
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


def build_content_work_item_diagnostics_snapshot_response(
    diagnostics: ContentDiagnosticsResponse,
) -> ContentWorkItemWorkflowSnapshotResponse:
    decision = _select_content_work_item_decision(diagnostics.decision_queue)
    item = _work_item_from_decision(decision)
    return _build_content_work_item_snapshot_response(
        item=item,
        inventory_records=[_inventory_record_from_decision(decision)],
        claim_ledger=_claim_ledger_from_decision(item),
        seed=_sales_brief_seed_from_decision(decision),
    )


def _build_content_work_item_snapshot_response(
    *,
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
) -> ContentWorkItemWorkflowSnapshotResponse:
    measurement_window_id = f"measure_{item.id}"

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
                    "measurement_window_id": measurement_window_id,
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
                    "measurement_window_id": measurement_window_id,
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
                    "measurement_window_status": "planned",
                    "measurement_window_id": measurement_window_id,
                }
            ),
            review=None,
            draft_package=draft,
            claim_ledger=claim_ledger,
        )
    )
    wordpress_handoff = build_content_work_item_wordpress_draft_handoff_response(
        ContentWorkItemWordPressDraftHandoffRequest(
            item=human_review.reviewed_item,
            draft_package=draft,
            human_review=human_review.review,
            audit=None,
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
                    "human_review_status": human_review.reviewed_item.human_review_status,
                    "human_review_id": human_review.reviewed_item.human_review_id,
                    "audit_status": "missing",
                    "audit_id": None,
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


def _select_content_work_item_decision(
    decisions: list[ContentDecisionItem],
) -> ContentDecisionItem:
    return next(
        decision
        for decision in decisions
        if decision.status == "ready"
        and decision.final_canonical_url
        and decision.evidence_ids
        and decision.source_connectors
    )


def _work_item_from_decision(decision: ContentDecisionItem) -> ContentWorkItem:
    return ContentWorkItem(
        id=f"content_work_item_{decision.id}",
        topic=decision.title,
        source_public_url=decision.source_public_url or decision.page,
        final_canonical_url=decision.final_canonical_url,
        intended_final_url=decision.intended_final_url or decision.final_canonical_url,
        preview_url=decision.preview_url,
        evidence_ids=decision.evidence_ids,
        source_connectors=decision.source_connectors,
        inventory_status="resolved",
        canonical_status="resolved",
        duplicate_status="checked",
    )


def _inventory_record_from_decision(decision: ContentDecisionItem) -> ContentInventoryRecord:
    assert decision.final_canonical_url is not None
    return ContentInventoryRecord(
        id=f"inventory_{decision.id}",
        url=decision.source_public_url or decision.page or decision.final_canonical_url,
        final_canonical_url=decision.final_canonical_url,
        intended_final_url=decision.intended_final_url or decision.final_canonical_url,
        preview_url=decision.preview_url,
        content_status="published" if decision.wordpress_match == "found" else "unknown",
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        title=decision.title,
        h1=decision.title,
        topic_tags=[decision.primary_query] if decision.primary_query else decision.queries[:3],
    )


def _claim_ledger_from_decision(item: ContentWorkItem) -> ContentClaimLedger:
    evidence_id = item.evidence_ids[0]
    return ContentClaimLedger(
        id=f"claim_ledger_{item.id}",
        work_item_id=item.id,
        reviewed_by="wilku",
        entries=[
            ContentClaimLedgerEntry(
                id=f"claim_service_{item.id}",
                claim_text=f"Ekologus może pomóc użytkownikowi w temacie: {item.topic}.",
                claim_type="service_claim",
                status="allowed_with_evidence",
                evidence_ids=[evidence_id],
                reason="Claim jest ogólną deklaracją usługi i ma przypisany dowód źródłowy.",
                reviewer_id="wilku",
            )
        ],
    )


def _sales_brief_seed_from_decision(decision: ContentDecisionItem) -> ContentSalesBriefSeed:
    primary_query = decision.primary_query or (
        decision.queries[0] if decision.queries else decision.title
    )
    return ContentSalesBriefSeed(
        target_reader="osoba odpowiedzialna za decyzję środowiskową w firmie",
        buyer_problem=decision.summary or decision.title,
        buyer_trigger=f"użytkownik szuka informacji lub pomocy dla tematu: {primary_query}",
        search_intent="informacyjno-usługowy",
        service_fit="sprawdzenie, czy temat pasuje do usługi Ekologus przed szkicem",
        h1_direction=decision.title,
        h2_direction=_decision_h2_direction(decision),
        faq_direction=[f"Co trzeba sprawdzić przed działaniem w temacie: {primary_query}?"],
        cta_direction="Zaproponuj kontakt w celu sprawdzenia sytuacji firmy bez obietnicy wyniku.",
        internal_link_direction=["https://ekologus.pl/kontakt/"],
        source_facts=[
            ContentSalesBriefSourceFact(
                evidence_id=evidence_id,
                source_connector=_source_connector_for_evidence(decision, index),
                summary=_source_fact_summary(decision, evidence_id),
            )
            for index, evidence_id in enumerate(decision.evidence_ids)
        ],
        missing_evidence=[],
    )


def _decision_h2_direction(decision: ContentDecisionItem) -> list[str]:
    if decision.queries:
        return [f"Co wiemy z zapytań: {query}" for query in decision.queries[:2]]
    return ["Co pokazują dane", "Co sprawdzić przed publikacją"]


def _source_connector_for_evidence(decision: ContentDecisionItem, index: int) -> str:
    if index < len(decision.source_connectors):
        return decision.source_connectors[index]
    return decision.source_connectors[0]


def _source_fact_summary(decision: ContentDecisionItem, evidence_id: str) -> str:
    return f"Dowód {evidence_id} wspiera decyzję: {decision.title}."


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
