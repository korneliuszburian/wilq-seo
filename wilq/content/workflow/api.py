from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefBuildResult,
    ContentSalesBriefSeed,
    build_content_sales_brief,
)
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.openai_runtime import (
    OpenAIClientProtocol,
    OpenAIStructuredDraftRuntimeMode,
    OpenAIStructuredDraftRuntimeResult,
    execute_openai_structured_draft_generation,
)
from wilq.content.drafts.openai_sdk import (
    build_openai_sdk_client,
    openai_structured_draft_live_enabled,
)
from wilq.content.drafts.package import (
    ContentDraftPackage,
    ContentDraftPackageBuildResult,
    build_content_draft_package,
)
from wilq.content.drafts.preview import (
    StructuredDraftPreviewResult,
    build_structured_draft_preview,
)
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationResult,
    StructuredDraftOutput,
    build_structured_draft_generation_contract,
)
from wilq.content.handoff.wordpress import (
    ContentWordPressDraftAuditEnvelope,
    ContentWordPressDraftHandoff,
    ContentWordPressDraftHandoffResult,
    build_content_wordpress_draft_handoff,
)
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionMode,
    ContentWordPressDraftExecutionResult,
    execute_content_wordpress_draft_handoff,
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
from wilq.content.quality.review import (
    ContentQualityReview,
    build_content_quality_review,
)
from wilq.content.review.human import (
    ContentHumanReview,
    ContentHumanReviewBlocker,
    apply_content_human_review_to_work_item,
    content_human_review_allows_wordpress_handoff,
    content_human_review_blockers,
)
from wilq.content.workflow.decision_mapping import (
    content_claim_ledger_from_work_item,
    content_inventory_record_from_decision,
    content_sales_brief_seed_from_decision,
    content_work_item_from_decision,
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


class ContentWorkItemStructuredDraftGenerationRequest(BaseModel):
    item: ContentWorkItem
    sales_brief: ContentSalesBrief | None = None
    claim_ledger: ContentClaimLedger | None = None
    draft_package: ContentDraftPackage | None = None


class ContentWorkItemStructuredDraftGenerationResponse(BaseModel):
    item: ContentWorkItem
    structured_generation_result: StructuredDraftGenerationResult


class ContentWorkItemStructuredDraftRuntimeRequest(BaseModel):
    contract: StructuredDraftGenerationContract | None = None
    model: str | None = None
    mode: OpenAIStructuredDraftRuntimeMode = "dry_run"


class ContentWorkItemStructuredDraftRuntimeResponse(BaseModel):
    runtime_result: OpenAIStructuredDraftRuntimeResult


class ContentWorkItemStructuredDraftPreviewRequest(BaseModel):
    contract: StructuredDraftGenerationContract | None = None
    output: StructuredDraftOutput | None = None


class ContentWorkItemStructuredDraftPreviewResponse(BaseModel):
    preview_result: StructuredDraftPreviewResult


class ContentWorkItemQualityReviewRequest(BaseModel):
    item: ContentWorkItem
    draft_package: ContentDraftPackage | None = None
    structured_output: StructuredDraftOutput | None = None
    claim_ledger: ContentClaimLedger | None = None
    sales_brief: ContentSalesBrief | None = None
    duplicate_risk: ContentInventoryDuplicateRisk = "clear"


class ContentWorkItemQualityReviewResponse(BaseModel):
    item: ContentWorkItem
    quality_review: ContentQualityReview


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


class ContentWorkItemWordPressDraftExecutionRequest(BaseModel):
    handoff: ContentWordPressDraftHandoff | None = None
    draft_package: ContentDraftPackage | None = None
    mode: ContentWordPressDraftExecutionMode = "dry_run"


class ContentWorkItemWordPressDraftExecutionResponse(BaseModel):
    execution_result: ContentWordPressDraftExecutionResult


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


class ContentWorkflowOperatorStep(BaseModel):
    id: str
    title: str
    status_label: str
    summary: str


class ContentWorkItemWorkflowSnapshotResponse(BaseModel):
    preflight: ContentWorkItemPreflightResponse
    sales_brief: ContentWorkItemSalesBriefResponse
    draft_package: ContentWorkItemDraftPackageResponse
    structured_generation: ContentWorkItemStructuredDraftGenerationResponse
    human_review: ContentWorkItemHumanReviewResponse
    wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponse
    measurement_window: ContentWorkItemMeasurementWindowResponse
    operator_steps: list[ContentWorkflowOperatorStep] = Field(default_factory=list)


class ContentWorkItemSnapshotHumanReviewRequest(BaseModel):
    review: ContentHumanReview


class ContentWorkItemSnapshotAuditRequest(BaseModel):
    audit: ContentWordPressDraftAuditEnvelope


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
    assert inventory_record is not None
    return _build_content_work_item_snapshot_response(
        item=item,
        inventory_records=[inventory_record],
        claim_ledger=content_claim_ledger_from_work_item(item),
        seed=content_sales_brief_seed_from_decision(decision),
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
    human_review_record: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
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
    structured_generation = build_content_work_item_structured_draft_generation_response(
        ContentWorkItemStructuredDraftGenerationRequest(
            item=item.model_copy(
                update={
                    "preflight_status": "draft_allowed",
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
            sales_brief=brief,
            claim_ledger=claim_ledger,
            draft_package=draft,
        )
    )
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
            review=human_review_record,
            draft_package=draft,
            claim_ledger=claim_ledger,
        )
    )
    wordpress_handoff = build_content_work_item_wordpress_draft_handoff_response(
        ContentWorkItemWordPressDraftHandoffRequest(
            item=human_review.reviewed_item,
            draft_package=draft,
            human_review=human_review.review,
            audit=audit,
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
    snapshot = ContentWorkItemWorkflowSnapshotResponse(
        preflight=preflight,
        sales_brief=sales_brief,
        draft_package=draft_package,
        structured_generation=structured_generation,
        human_review=human_review,
        wordpress_handoff=wordpress_handoff,
        measurement_window=measurement_window,
    )
    snapshot.operator_steps = _content_workflow_operator_steps(snapshot)
    return snapshot


def _content_workflow_operator_steps(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> list[ContentWorkflowOperatorStep]:
    brief = snapshot.sales_brief.sales_brief_result.brief
    draft = snapshot.draft_package.draft_package_result.draft_package
    structured_contract = snapshot.structured_generation.structured_generation_result.contract
    structured_blocker = snapshot.structured_generation.structured_generation_result.blockers[0:1]
    review = snapshot.human_review.review
    handoff = snapshot.wordpress_handoff.handoff_result.handoff
    handoff_blocker = snapshot.wordpress_handoff.handoff_result.blockers[0:1]
    measurement_window = snapshot.measurement_window.measurement_window_result.window
    return [
        ContentWorkflowOperatorStep(
            id="content_preflight",
            title="Sprawdzenie pisania",
            status_label=_preflight_status_label(snapshot.preflight.preflight_verdict.status),
            summary=snapshot.preflight.preflight_verdict.next_step,
        ),
        ContentWorkflowOperatorStep(
            id="sales_brief",
            title="Plan sprzedażowy",
            status_label="gotowy do sprawdzenia" if brief else "zablokowany",
            summary=brief.buyer_problem if brief else "Brakuje planu sprzedażowego.",
        ),
        ContentWorkflowOperatorStep(
            id="draft_package",
            title="Paczka szkicu",
            status_label="konspekt do sprawdzenia" if draft else "zablokowany",
            summary="WILQ przygotowuje materiał do sprawdzenia człowieka, nie gotową publikację.",
        ),
        ContentWorkflowOperatorStep(
            id="structured_draft",
            title="Szkic treści",
            status_label="gotowy do próby" if structured_contract else "zablokowany",
            summary=(
                "WILQ może sprawdzić przygotowanie szkicu bez pisania na żywo."
                if structured_contract
                else (
                    structured_blocker[0].reason
                    if structured_blocker
                    else (
                        "Szkic pozostaje zablokowany, dopóki plan i twierdzenia "
                        "nie przejdą bramek."
                    )
                )
            ),
        ),
        ContentWorkflowOperatorStep(
            id="human_review",
            title="Sprawdzenie człowieka",
            status_label="zatwierdzone" if review else "wymaga decyzji",
            summary=(
                "Bez zatwierdzenia człowieka przekazanie szkicu do WordPress "
                "pozostaje zablokowane."
            ),
        ),
        ContentWorkflowOperatorStep(
            id="wordpress_handoff",
            title="Szkic w WordPress",
            status_label="szkic" if handoff else "zablokowany",
            summary=(
                "WordPress dostaje tylko szkic po audycie. Publikacja nie jest automatyczna."
                if handoff
                else (
                    handoff_blocker[0].reason
                    if handoff_blocker
                    else "WordPress nie dostaje szkicu bez sprawdzenia człowieka i audytu."
                )
            ),
        ),
        ContentWorkflowOperatorStep(
            id="measurement_window",
            title="Okno pomiaru",
            status_label=_measurement_window_status_label(
                None if measurement_window is None else measurement_window.status
            ),
            summary="WILQ planuje pomiar teraz, ale ocena efektu czeka na koniec obserwacji.",
        ),
    ]


def _preflight_status_label(status: str) -> str:
    labels = {
        "blocked": "zablokowane",
        "plan_allowed": "można planować",
        "brief_allowed": "można przygotować plan",
        "draft_allowed": "można przygotować szkic",
        "handoff_allowed": "można przekazać szkic",
    }
    return labels.get(status, "wymaga sprawdzenia")


def _measurement_window_status_label(status: str | None) -> str:
    if status is None:
        return "brak"
    labels = {
        "planned": "zaplanowane",
        "open": "pomiar trwa",
        "ready_for_review": "gotowe do oceny",
        "closed": "zamknięte",
    }
    return labels.get(status, "brak")


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
