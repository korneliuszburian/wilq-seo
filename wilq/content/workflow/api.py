from __future__ import annotations

from datetime import date

from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefBuildResult,
    ContentSalesBriefSeed,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.openai_runtime import (
    OpenAIClientProtocol,
    execute_openai_structured_draft_generation,
)
from wilq.content.drafts.openai_sdk import (
    build_openai_sdk_client,
    openai_structured_draft_live_enabled,
)
from wilq.content.drafts.package import (
    ContentDraftPackage,
    build_content_draft_package,
)
from wilq.content.drafts.preview import (
    build_structured_draft_preview,
)
from wilq.content.drafts.structured_generation import (
    build_structured_draft_generation_contract,
)
from wilq.content.drafts.variants import build_content_draft_variants
from wilq.content.enrichment.opportunity import (
    ContentOpportunityEnrichment,
    build_content_opportunity_enrichment,
)
from wilq.content.handoff.wordpress import (
    ContentWordPressDraftAuditEnvelope,
    build_content_wordpress_draft_handoff,
)
from wilq.content.handoff.wordpress_execution import (
    execute_content_wordpress_draft_handoff,
)
from wilq.content.inventory.records import (
    ContentInventoryDuplicateRisk,
    ContentInventoryRecord,
    ContentInventoryResolution,
    resolve_content_inventory,
)
from wilq.content.knowledge.cards import (
    match_content_knowledge_cards,
)
from wilq.content.measurement.window import (
    ContentDateRange,
    apply_content_measurement_window_to_work_item,
    build_content_measurement_window,
    content_measurement_window_outcome_blockers,
)
from wilq.content.preflight.workflow import (
    ContentPreflightVerdict,
    build_content_preflight_verdict,
)
from wilq.content.quality.review import (
    build_content_quality_review,
)
from wilq.content.quality.revision import (
    build_content_revision_plan,
)
from wilq.content.review.human import (
    ContentHumanReview,
    apply_content_human_review_to_work_item,
    content_human_review_allows_wordpress_handoff,
    content_human_review_blockers,
)
from wilq.content.workflow import operator_steps as workflow_steps
from wilq.content.workflow.contracts import (
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemDraftVariantsRequest,
    ContentWorkItemDraftVariantsResponse,
    ContentWorkItemHumanReviewRequest,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementWindowRequest,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightRequest,
    ContentWorkItemPreflightResponse,
    ContentWorkItemQualityReviewRequest,
    ContentWorkItemQualityReviewResponse,
    ContentWorkItemRevisionPlanRequest,
    ContentWorkItemRevisionPlanResponse,
    ContentWorkItemSalesBriefRequest,
    ContentWorkItemSalesBriefResponse,
    ContentWorkItemSnapshotAuditRequest,
    ContentWorkItemSnapshotHumanReviewRequest,
    ContentWorkItemStructuredDraftGenerationRequest,
    ContentWorkItemStructuredDraftGenerationResponse,
    ContentWorkItemStructuredDraftPreviewRequest,
    ContentWorkItemStructuredDraftPreviewResponse,
    ContentWorkItemStructuredDraftRuntimeRequest,
    ContentWorkItemStructuredDraftRuntimeResponse,
    ContentWorkItemWordPressDraftExecutionRequest,
    ContentWorkItemWordPressDraftExecutionResponse,
    ContentWorkItemWordPressDraftHandoffRequest,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.decision_mapping import (
    content_claim_ledger_from_work_item,
    content_inventory_record_from_decision,
    content_sales_brief_seed_from_decision,
    content_work_item_from_decision,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.schemas import ContentDecisionItem, ContentDiagnosticsResponse


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
            enrichment=request.enrichment,
            knowledge_match=request.knowledge_match
            or match_content_knowledge_cards(request.item),
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


def build_content_work_item_structured_draft_runtime_response(
    request: ContentWorkItemStructuredDraftRuntimeRequest,
    *,
    client: OpenAIClientProtocol | None = None,
    live_generation_enabled: bool | None = None,
) -> ContentWorkItemStructuredDraftRuntimeResponse:
    live_enabled = (
        openai_structured_draft_live_enabled()
        if live_generation_enabled is None
        else live_generation_enabled
    )
    runtime_client = (
        client
        if client is not None or request.mode != "live" or not live_enabled
        else build_openai_sdk_client()
    )
    return ContentWorkItemStructuredDraftRuntimeResponse(
        runtime_result=execute_openai_structured_draft_generation(
            contract=request.contract,
            model=request.model,
            mode=request.mode,
            client=runtime_client,
            live_generation_enabled=live_enabled,
        )
    )


def build_content_work_item_structured_draft_preview_response(
    request: ContentWorkItemStructuredDraftPreviewRequest,
) -> ContentWorkItemStructuredDraftPreviewResponse:
    return ContentWorkItemStructuredDraftPreviewResponse(
        preview_result=build_structured_draft_preview(
            contract=request.contract,
            output=request.output,
        )
    )


def build_content_work_item_quality_review_response(
    request: ContentWorkItemQualityReviewRequest,
) -> ContentWorkItemQualityReviewResponse:
    return ContentWorkItemQualityReviewResponse(
        item=request.item,
        quality_review=build_content_quality_review(
            item=request.item,
            draft_package=request.draft_package,
            structured_output=request.structured_output,
            claim_ledger=request.claim_ledger,
            sales_brief=request.sales_brief,
            duplicate_risk=request.duplicate_risk,
        ),
    )


def build_content_work_item_revision_plan_response(
    request: ContentWorkItemRevisionPlanRequest,
) -> ContentWorkItemRevisionPlanResponse:
    return ContentWorkItemRevisionPlanResponse(
        item=request.item,
        revision_plan=build_content_revision_plan(
            item=request.item,
            quality_review=request.quality_review,
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


def build_content_work_item_wordpress_draft_execution_response(
    request: ContentWorkItemWordPressDraftExecutionRequest,
) -> ContentWorkItemWordPressDraftExecutionResponse:
    return ContentWorkItemWordPressDraftExecutionResponse(
        execution_result=execute_content_wordpress_draft_handoff(
            handoff=request.handoff,
            draft_package=request.draft_package,
            mode=request.mode,
            live_write_enabled=False,
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
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    decision = _select_content_work_item_decision(diagnostics.decision_queue)
    return _build_content_work_item_diagnostics_snapshot_response_from_decision(
        decision,
        human_review=human_review,
        audit=audit,
    )


def build_content_work_item_diagnostics_snapshot_response_for_work_item(
    diagnostics: ContentDiagnosticsResponse,
    work_item_id: str,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse | None:
    decision = _select_content_work_item_decision_for_work_item(
        diagnostics.decision_queue,
        work_item_id,
    )
    if decision is None:
        return None
    return _build_content_work_item_diagnostics_snapshot_response_from_decision(
        decision,
        human_review=human_review,
        audit=audit,
    )


def _build_content_work_item_diagnostics_snapshot_response_from_decision(
    decision: ContentDecisionItem,
    *,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    item = content_work_item_from_decision(decision)
    inventory_record = content_inventory_record_from_decision(decision)
    if inventory_record is None:
        raise RuntimeError("Content decision could not be converted to an inventory record.")
    return _build_content_work_item_snapshot_response(
        item=item,
        inventory_records=[inventory_record],
        claim_ledger=content_claim_ledger_from_work_item(item),
        seed=content_sales_brief_seed_from_decision(decision),
        enrichment=build_content_opportunity_enrichment(decision),
        human_review_record=human_review,
        audit=audit,
    )


def build_content_work_item_snapshot_human_review_response(
    diagnostics: ContentDiagnosticsResponse,
    request: ContentWorkItemSnapshotHumanReviewRequest,
) -> ContentWorkItemHumanReviewResponse:
    return build_content_work_item_diagnostics_snapshot_response(
        diagnostics,
        human_review=request.review,
    ).human_review


def build_content_work_item_snapshot_audit_response(
    diagnostics: ContentDiagnosticsResponse,
    request: ContentWorkItemSnapshotAuditRequest,
    *,
    human_review: ContentHumanReview | None,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    return build_content_work_item_diagnostics_snapshot_response(
        diagnostics,
        human_review=human_review,
        audit=request.audit,
    ).wordpress_handoff


def _build_content_work_item_snapshot_response(
    *,
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    human_review_record: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    measurement_window_id = f"measure_{item.id}"
    preflight = _snapshot_preflight(item, inventory_records)
    sales_brief = _snapshot_sales_brief(
        item,
        inventory_records,
        claim_ledger,
        seed,
        enrichment,
        measurement_window_id,
    )
    brief = sales_brief.sales_brief_result.brief
    draft_package = _snapshot_draft_package(
        item,
        inventory_records,
        claim_ledger,
        seed,
        enrichment,
        measurement_window_id,
        None if brief is None else brief.id,
        brief,
    )
    draft = draft_package.draft_package_result.draft_package
    structured_generation = _snapshot_structured_generation(
        item,
        claim_ledger,
        measurement_window_id,
        None if brief is None else brief.id,
        brief,
        draft,
    )
    human_review = _snapshot_human_review(
        item,
        claim_ledger,
        measurement_window_id,
        None if brief is None else brief.id,
        draft,
        human_review_record,
    )
    wordpress_handoff = build_content_work_item_wordpress_draft_handoff_response(
        ContentWorkItemWordPressDraftHandoffRequest(
            item=human_review.reviewed_item,
            draft_package=draft,
            human_review=human_review.review,
            audit=audit,
        )
    )
    measurement_window = _snapshot_measurement_window(
        item,
        claim_ledger,
        wordpress_handoff,
        measurement_window_id,
        None if brief is None else brief.id,
        draft,
        human_review,
    )
    snapshot = ContentWorkItemWorkflowSnapshotResponse(
        preflight=preflight,
        sales_brief=sales_brief,
        draft_package=draft_package,
        structured_generation=structured_generation,
        human_review=human_review,
        wordpress_handoff=wordpress_handoff,
        measurement_window=measurement_window,
    )
    snapshot.operator_steps = workflow_steps.content_workflow_operator_steps(snapshot)
    return snapshot


def _snapshot_preflight(
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
) -> ContentWorkItemPreflightResponse:
    return build_content_work_item_preflight_response(
        ContentWorkItemPreflightRequest(
            item=item,
            inventory_records=inventory_records,
            duplicate_risk="clear",
        )
    )


def _snapshot_sales_brief(
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    measurement_window_id: str,
) -> ContentWorkItemSalesBriefResponse:
    return build_content_work_item_sales_brief_response(
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
            enrichment=enrichment,
        )
    )


def _snapshot_draft_package(
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    measurement_window_id: str,
    brief_id: str | None,
    brief: ContentSalesBrief | None,
) -> ContentWorkItemDraftPackageResponse:
    return build_content_work_item_draft_package_response(
        ContentWorkItemDraftPackageRequest(
            item=_snapshot_item_ready_for_draft(
                item,
                claim_ledger,
                measurement_window_id,
                brief_id,
            ),
            inventory_records=inventory_records,
            duplicate_risk="clear",
            claim_ledger=claim_ledger,
            seed=seed,
            enrichment=enrichment,
            sales_brief=brief,
        )
    )


def _snapshot_structured_generation(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    brief: ContentSalesBrief | None,
    draft: ContentDraftPackage | None,
) -> ContentWorkItemStructuredDraftGenerationResponse:
    return build_content_work_item_structured_draft_generation_response(
        ContentWorkItemStructuredDraftGenerationRequest(
            item=_snapshot_item_ready_for_draft(
                item,
                claim_ledger,
                measurement_window_id,
                brief_id,
                draft,
            ),
            sales_brief=brief,
            claim_ledger=claim_ledger,
            draft_package=draft,
        )
    )


def _snapshot_human_review(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None,
    human_review_record: ContentHumanReview | None,
) -> ContentWorkItemHumanReviewResponse:
    return build_content_work_item_human_review_response(
        ContentWorkItemHumanReviewRequest(
            item=_snapshot_item_ready_for_handoff(
                item,
                claim_ledger,
                measurement_window_id,
                brief_id,
                draft,
            ),
            review=human_review_record,
            draft_package=draft,
            claim_ledger=claim_ledger,
        )
    )


def _snapshot_measurement_window(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponse,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None,
    human_review: ContentWorkItemHumanReviewResponse,
) -> ContentWorkItemMeasurementWindowResponse:
    return build_content_work_item_measurement_window_response(
        ContentWorkItemMeasurementWindowRequest(
            item=_snapshot_item_ready_for_measurement(
                item,
                claim_ledger,
                measurement_window_id,
                brief_id,
                draft,
                human_review,
            ),
            handoff=wordpress_handoff.handoff_result.handoff,
            baseline_period=ContentDateRange(start=date(2026, 5, 1), end=date(2026, 5, 31)),
            observation_period=ContentDateRange(start=date(2026, 7, 1), end=date(2026, 7, 31)),
            allowed_metrics=["gsc_clicks", "gsc_impressions", "ga4_engaged_sessions"],
            source_connectors=["google_search_console", "google_analytics_4"],
        )
    )


def _snapshot_item_ready_for_draft(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None = None,
) -> ContentWorkItem:
    update: dict[str, object] = {
        "preflight_status": "draft_allowed",
        "preserve_first_plan_status": "approved",
        "sales_brief_status": "approved",
        "sales_brief_id": brief_id,
        "claim_ledger_status": "approved",
        "claim_ledger_id": claim_ledger.id,
        "measurement_window_status": "planned",
        "measurement_window_id": measurement_window_id,
    }
    if draft is not None:
        update.update({"draft_package_status": "ready", "draft_package_id": draft.id})
    return item.model_copy(update=update)


def _snapshot_item_ready_for_handoff(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None,
) -> ContentWorkItem:
    return _snapshot_item_ready_for_draft(
        item,
        claim_ledger,
        measurement_window_id,
        brief_id,
        draft,
    ).model_copy(update={"preflight_status": "handoff_allowed"})


def _snapshot_item_ready_for_measurement(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None,
    human_review: ContentWorkItemHumanReviewResponse,
) -> ContentWorkItem:
    return _snapshot_item_ready_for_handoff(
        item,
        claim_ledger,
        measurement_window_id,
        brief_id,
        draft,
    ).model_copy(
        update={
            "human_review_status": human_review.reviewed_item.human_review_status,
            "human_review_id": human_review.reviewed_item.human_review_id,
            "audit_status": "missing",
            "audit_id": None,
            "measurement_window_status": "missing",
            "measurement_window_id": None,
        }
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


def _select_content_work_item_decision_for_work_item(
    decisions: list[ContentDecisionItem],
    work_item_id: str,
) -> ContentDecisionItem | None:
    for decision in decisions:
        if f"content_work_item_{decision.id}" != work_item_id:
            continue
        if (
            decision.status == "ready"
            and decision.final_canonical_url
            and decision.evidence_ids
            and decision.source_connectors
        ):
            return decision
        return None
    return None


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
