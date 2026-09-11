from __future__ import annotations

from functools import partial
from typing import Literal

from wilq.connectors.wordpress.authoring import build_wordpress_authoring_profile
from wilq.content.briefs.sales import (
    ContentSalesBriefSeed,
)
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.enrichment.opportunity import (
    ContentOpportunityEnrichment,
    build_content_opportunity_enrichment,
)
from wilq.content.handoff.wordpress import (
    ContentWordPressDraftAuditEnvelope,
)
from wilq.content.handoff.wordpress_authoring import (
    build_content_wordpress_authoring_payload_preview,
)
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionResult,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.inventory.records import (
    ContentInventoryRecord,
)
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
    build_content_work_item_service_profile_context,
)
from wilq.content.quality.review import (
    build_content_quality_review,
)
from wilq.content.quality.revision import (
    build_content_revision_plan,
)
from wilq.content.quality.revision_apply import apply_content_revision_plan
from wilq.content.review.human import (
    ContentHumanReview,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWordPressDraftActivationPacketResponse as ContentWordPressDraftActivationPacketResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWordPressDraftReadback,
    ContentWordPressDraftWriteReadinessBlocker,
    ContentWorkItemBlockedSnapshotResponse,
    ContentWorkItemQualityReviewRequest,
    ContentWorkItemRevisionApplyRequest,
    ContentWorkItemRevisionPlanRequest,
    ContentWorkItemSnapshotAuditRequest,
    ContentWorkItemSnapshotHumanReviewRequest,
    ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
    ContentWorkItemWordPressDraftExecutionRequest,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWordPressDraftWriteReadinessResponse as ContentWordPressDraftWriteReadinessResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWordPressExistingDraftUpdateReadinessResponse as ContentWordPressExistingDraftUpdateReadinessResponse,  # noqa: E501
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemDraftPackageResponse as ContentWorkItemDraftPackageResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemHumanReviewResponse as ContentWorkItemHumanReviewResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemMeasurementOutcomeResponse as ContentWorkItemMeasurementOutcomeResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemMeasurementWindowResponse as ContentWorkItemMeasurementWindowResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemPreflightResponse as ContentWorkItemPreflightResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemQualityReviewResponse as ContentWorkItemQualityReviewResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemRevisionApplyResponse as ContentWorkItemRevisionApplyResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemRevisionPlanResponse as ContentWorkItemRevisionPlanResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemSalesBriefResponse as ContentWorkItemSalesBriefResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemStructuredDraftGenerationResponse as ContentWorkItemStructuredDraftGenerationResponse,  # noqa: E501
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemWordPressAuthoringPayloadPreviewResponse as ContentWorkItemWordPressAuthoringPayloadPreviewResponse,  # noqa: E501
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemWordPressDraftExecutionResponse as ContentWorkItemWordPressDraftExecutionResponse,  # noqa: E501
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemWordPressDraftHandoffResponse as ContentWorkItemWordPressDraftHandoffResponse,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemWorkflowSnapshotResponse as ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.decision_mapping import (
    content_claim_ledger_from_work_item,
    content_inventory_record_from_decision,
    content_sales_brief_seed_from_decision,
    content_work_item_from_decision,
)
from wilq.content.workflow.decisions.inventory_binding import inventory_decision_for_work_item
from wilq.content.workflow.decisions.planning import (
    ContentPlanningDecision,
    ContentPlanningProposal,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionState
from wilq.content.workflow.pipeline_steps.queue import (
    ContentWorkItemQueueCandidate,
    build_content_work_item_queue_candidate,
    build_content_work_item_queue_response,
)
from wilq.content.workflow.pipeline_steps.snapshot_assembly import (
    SnapshotAssemblyCallbacks,
    assemble_content_work_item_snapshot,
)
from wilq.content.workflow.pipeline_steps.stage_activation import (
    ActivationProjectionCallbacks,
    wordpress_draft_activation_missing_labels,
    wordpress_draft_activation_missing_step,
    wordpress_draft_activation_missing_step_label,
    wordpress_draft_human_review_checklist,
    wordpress_draft_readback,
    wordpress_draft_review_preview_status_label,
)
from wilq.content.workflow.pipeline_steps.stage_activation import (
    build_content_wordpress_draft_activation_packet_response as _build_activation_packet,
)
from wilq.content.workflow.pipeline_steps.stage_drafts import (
    build_content_work_item_draft_package_response,
    build_content_work_item_structured_draft_generation_response,
)
from wilq.content.workflow.pipeline_steps.stage_measurement import (
    build_content_work_item_measurement_window_response,
)
from wilq.content.workflow.pipeline_steps.stage_preparation import (
    build_content_work_item_preflight_response,
    build_content_work_item_sales_brief_response,
)
from wilq.content.workflow.pipeline_steps.stage_review import (
    build_content_work_item_human_review_response,
    build_content_work_item_wordpress_draft_handoff_response,
)
from wilq.content.workflow.pipeline_steps.stage_snapshot import (
    SnapshotStageCallbacks,
    snapshot_draft_package,
    snapshot_human_review,
    snapshot_measurement_window,
    snapshot_preflight,
    snapshot_sales_brief,
    snapshot_structured_generation,
    snapshot_wordpress_handoff,
)
from wilq.content.workflow.pipeline_steps.stage_write_readiness import (
    WriteReadinessCallbacks,
)
from wilq.content.workflow.pipeline_steps.stage_write_readiness import (
    build_content_wordpress_draft_write_readiness_response as _build_write_readiness,
)
from wilq.content.workflow.pipeline_steps.stage_write_readiness import (
    wordpress_draft_write_audit_blockers as _wordpress_draft_write_audit_blockers,
)
from wilq.content.workflow.pipeline_steps.stage_write_readiness import (
    wordpress_draft_write_audit_readiness as _wordpress_draft_write_audit_readiness,
)
from wilq.content.workflow.pipeline_steps.stage_write_readiness import (
    wordpress_draft_write_authorization_status as _wordpress_draft_write_authorization_status,
)
from wilq.content.workflow.pipeline_steps.stage_write_readiness import (
    wordpress_draft_write_authorization_verified as _wordpress_draft_write_authorization_verified,
)
from wilq.content.workflow.policies import wordpress_draft_writes_enabled
from wilq.content.workflow.workspace.snapshot_service_selection import (
    gate_snapshot_candidate_on_service_binding,
    resolve_snapshot_service_selection,
)
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    ContentFreshnessAssessment,
    MetricFact,
)


def _gate_candidate_on_service_binding(
    candidate: ContentWorkItemQueueCandidate,
    *,
    service_profile_context: ContentWorkItemServiceProfileContext,
) -> ContentWorkItemQueueCandidate:
    """Compatibility seam for existing callers of the extracted snapshot policy."""
    return gate_snapshot_candidate_on_service_binding(
        candidate,
        service_profile_context=service_profile_context,
    )


def build_content_wordpress_draft_activation_packet_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    action_id: str = "act_apply_wordpress_draft_handoff",
    latest_execution_result: ContentWordPressDraftExecutionResult | None = None,
) -> ContentWordPressDraftActivationPacketResponse:
    return _build_activation_packet(
        snapshot,
        callbacks=ActivationProjectionCallbacks(
            readback=wordpress_draft_readback,
            missing_step=wordpress_draft_activation_missing_step,
            missing_step_label=wordpress_draft_activation_missing_step_label,
            missing_labels=wordpress_draft_activation_missing_labels,
            review_preview_label=wordpress_draft_review_preview_status_label,
            checklist=wordpress_draft_human_review_checklist,
            next_step=_wordpress_draft_activation_next_step,
            steps=_wordpress_draft_activation_steps,
            writes_enabled=_wordpress_draft_writes_enabled,
        ),
        action_id=action_id,
        latest_execution_result=latest_execution_result,
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
            revision=request.revision,
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


def build_content_work_item_revision_apply_response(
    request: ContentWorkItemRevisionApplyRequest,
) -> ContentWorkItemRevisionApplyResponse:
    return ContentWorkItemRevisionApplyResponse(
        item=request.item,
        revision_application=apply_content_revision_plan(
            item=request.item,
            revision_plan=request.revision_plan,
            draft_output=request.draft_output,
            updated_quality_review=request.updated_quality_review,
        ),
    )


def build_content_work_item_wordpress_draft_execution_response(
    request: ContentWorkItemWordPressDraftExecutionRequest,
) -> ContentWorkItemWordPressDraftExecutionResponse:
    live_write_enabled = _wordpress_draft_writes_enabled()
    return ContentWorkItemWordPressDraftExecutionResponse(
        execution_result=execute_content_wordpress_draft_handoff(
            handoff=request.handoff,
            draft_package=request.draft_package,
            mode="dry_run",
            live_write_enabled=live_write_enabled,
            create_draft=None,
            action_apply_authorized=False,
            write_authorization=request.write_authorization,
            write_authorization_verified=_wordpress_draft_write_authorization_verified(
                request.write_authorization
            ),
            section_overrides=request.section_overrides,
        ),
    )


def build_content_wordpress_draft_write_readiness_response(
    action_id: str = "act_prepare_wordpress_draft_handoff",
    connector_id: str = "wordpress_ekologus",
) -> ContentWordPressDraftWriteReadinessResponse:
    return _build_write_readiness(
        callbacks=WriteReadinessCallbacks(
            writes_enabled=_wordpress_draft_writes_enabled,
            authoring_profile=build_wordpress_authoring_profile,
            audit_readiness=_wordpress_draft_write_audit_readiness,
            audit_blockers=_wordpress_draft_write_audit_blockers,
            authorization_status=_wordpress_draft_write_authorization_status,
            next_step=_wordpress_draft_write_next_step,
        ),
        action_id=action_id,
        connector_id=connector_id,
    )


def _wordpress_draft_writes_enabled() -> bool:
    return wordpress_draft_writes_enabled()


def _wordpress_draft_activation_next_step(
    handoff_blockers: list[str],
    execution_blockers: list[str],
    *,
    execution_status: Literal["dry_run_ready", "created", "blocked"],
    draft_readback: ContentWordPressDraftReadback | None,
) -> str:
    blockers = {*handoff_blockers, *execution_blockers}
    if "missing_human_review" in blockers:
        return (
            "Najbliższy krok: zapisz review człowieka dla paczki szkicu. "
            "Bez tego WILQ nie przygotuje handoffu ani dry-run payloadu WordPress."
        )
    if "missing_audit" in blockers:
        return (
            "Najbliższy krok: zapisz audit przekazania do WordPress po review. "
            "Dopiero wtedy dry-run pokaże finalny payload szkicu."
        )
    if blockers:
        return (
            "Najbliższy krok: usuń blokery handoffu/dry-run i wróć do packetu "
            "przed jakimkolwiek live write."
        )
    if execution_status == "created":
        if draft_readback is not None and draft_readback.status == "available":
            return (
                "Szkic istnieje na dev WordPress. Otwórz go, sprawdź realną treść "
                "i przejdź do edycji sekcji zamiast ponownie tworzyć draft."
            )
        return (
            "Szkic został utworzony, ale WILQ nie potwierdził jeszcze jego treści "
            "z WordPress REST. Najpierw sprawdź odczyt szkicu."
        )
    return (
        "Dry-run payload szkicu jest gotowy do review. Live write nadal wymaga "
        "ActionObject preview/review/confirm/audit i jawnie włączonego env."
    )


def _wordpress_draft_activation_steps(
    *,
    draft_package_ready: bool,
    handoff_blockers: list[str],
    execution_blockers: list[str],
    execution_status: Literal["dry_run_ready", "created", "blocked"],
) -> list[str]:
    steps = [
        "Utrzymaj zakres WordPress draft-only: bez publikacji i bez aktualizacji "
        "istniejących wpisów.",
    ]
    if not draft_package_ready:
        steps.append("Przygotuj paczkę szkicu z Claim Ledgerem, sekcjami i dowodami.")
    if "missing_human_review" in handoff_blockers:
        steps.append("Zapisz human review dla tej paczki szkicu.")
    if "missing_audit" in handoff_blockers:
        steps.append("Zapisz audit przekazania do WordPress po review.")
    if "missing_handoff" in execution_blockers:
        steps.append("Wróć do handoffu i dopiero potem sprawdź dry-run execution.")
    if "missing_draft_package" in execution_blockers and draft_package_ready is False:
        steps.append("Podepnij tę samą paczkę szkicu do execution dry-run.")
    if not {*handoff_blockers, *execution_blockers} and execution_status == "created":
        steps.append("Otwórz utworzony szkic na dev WordPress i sprawdź realną treść.")
        steps.append("Kolejny etap: edytuj treść i sekcje ACF na devie, nadal bez publikacji.")
        return steps
    if not {*handoff_blockers, *execution_blockers}:
        steps.append("Sprawdź payload dry-run, a live write zostaw wyłączony do osobnej decyzji.")
    return steps


def _wordpress_draft_write_next_step(
    ready: bool,
    blockers: list[ContentWordPressDraftWriteReadinessBlocker],
) -> str:
    if ready:
        return (
            "Ścieżka zapisu szkicu jest gotowa: użyj suggested_write_authorization "
            "tylko dla trybu live i nadal zapisuj wyłącznie draft."
        )
    if blockers:
        return blockers[0].next_step
    return "Uruchom readiness ponownie po przygotowaniu ścieżki ActionObject."


def build_content_work_item_wordpress_authoring_payload_preview_response(
    request: ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
) -> ContentWorkItemWordPressAuthoringPayloadPreviewResponse:
    profile = request.authoring_profile or build_wordpress_authoring_profile("wordpress_ekologus")
    return ContentWorkItemWordPressAuthoringPayloadPreviewResponse(
        authoring_profile=profile,
        preview_result=build_content_wordpress_authoring_payload_preview(
            handoff=request.handoff,
            draft_package=request.draft_package,
            authoring_profile=profile,
        ),
    )


def build_content_work_item_diagnostics_snapshot_response(
    diagnostics: ContentDiagnosticsResponse,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    planning_decisions: list[ContentPlanningDecision] | None = None,
    generated_planning_proposal: ContentPlanningProposal | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    decision = _select_content_work_item_decision(diagnostics.decision_queue)
    candidate = _queue_candidate_for_decision(diagnostics, decision.id)
    return _build_content_work_item_diagnostics_snapshot_response_from_decision(
        decision,
        freshness_assessment=diagnostics.freshness_assessment,
        candidate=candidate,
        human_review=human_review,
        audit=audit,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
    )


def build_content_work_item_diagnostics_snapshot_response_for_work_item(
    diagnostics: ContentDiagnosticsResponse,
    work_item_id: str,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    planning_decisions: list[ContentPlanningDecision] | None = None,
    generated_planning_proposal: ContentPlanningProposal | None = None,
    service_card_id_override: str | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse | None:
    decision = _select_content_work_item_decision_for_work_item(
        diagnostics.decision_queue,
        work_item_id,
    )
    if decision is None:
        return None
    inventory_decision = inventory_decision_for_work_item(work_item_id)
    if inventory_decision is not None and inventory_decision.status == "ready":
        # The diagnostics queue owns demand identity, while the selected
        # inventory binding owns the freshest dynamic WordPress material.
        # Keep the caller's stable work-item ID when replacing the payload so
        # alias and canonical routes share one workflow identity.
        decision = inventory_decision.model_copy(
            update={"id": work_item_id.removeprefix("content_work_item_")}
        )
        # The selected inventory binding is the fresh WordPress read. Rebuild
        # the compact candidate projection from it instead of reusing the
        # diagnostics queue row, which may carry an older section/ACF shape.
        candidate = build_content_work_item_queue_candidate(
            decision,
            diagnostics.freshness_assessment,
        )
    else:
        candidate = _queue_candidate_for_decision(diagnostics, decision.id)
    return _build_content_work_item_diagnostics_snapshot_response_from_decision(
        decision,
        freshness_assessment=diagnostics.freshness_assessment,
        candidate=candidate,
        human_review=human_review,
        audit=audit,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
        service_card_id_override=service_card_id_override,
    )


def build_content_work_item_snapshot_response_from_selected_decision(
    decision: ContentDecisionItem,
    *,
    freshness_assessment: ContentFreshnessAssessment,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    planning_decisions: list[ContentPlanningDecision] | None = None,
    generated_planning_proposal: ContentPlanningProposal | None = None,
    service_card_id_override: str | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Assemble a selected-page snapshot without rebuilding global diagnostics."""

    candidate = build_content_work_item_queue_candidate(
        decision,
        freshness_assessment,
    )
    return _build_content_work_item_diagnostics_snapshot_response_from_decision(
        decision,
        freshness_assessment=freshness_assessment,
        candidate=candidate,
        human_review=human_review,
        audit=audit,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
        service_card_id_override=service_card_id_override,
    )


def _build_content_work_item_diagnostics_snapshot_response_from_decision(
    decision: ContentDecisionItem,
    *,
    freshness_assessment: ContentFreshnessAssessment,
    candidate: ContentWorkItemQueueCandidate,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    planning_decisions: list[ContentPlanningDecision] | None = None,
    generated_planning_proposal: ContentPlanningProposal | None = None,
    service_card_id_override: str | None = None,
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
        freshness_assessment=freshness_assessment,
        candidate=candidate,
        human_review_record=human_review,
        audit=audit,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
        demand_metric_facts=decision.metric_facts,
        demand_source_page=decision.page,
        service_card_id_override=service_card_id_override,
    )


def build_content_work_item_blocked_snapshot_response_for_work_item(
    diagnostics: ContentDiagnosticsResponse,
    work_item_id: str,
) -> ContentWorkItemBlockedSnapshotResponse | None:
    queue = build_content_work_item_queue_response(diagnostics)
    candidate = next(
        (
            candidate
            for candidate in queue.candidates
            if candidate.work_item_id == work_item_id and candidate.recommended_mode == "block"
        ),
        None,
    )
    if candidate is None:
        return None
    return ContentWorkItemBlockedSnapshotResponse(
        work_item_id=candidate.work_item_id,
        freshness_assessment=diagnostics.freshness_assessment,
        decision_id=candidate.decision_id,
        title=candidate.title,
        topic=candidate.topic,
        status_label=candidate.status_label,
        reason=candidate.reason,
        safe_next_step=candidate.safe_next_step,
        recommended_mode=candidate.recommended_mode,
        preflight_status=candidate.preflight_status,
        blockers=candidate.blockers,
        evidence_ids=candidate.evidence_ids,
        source_connectors=candidate.source_connectors,
        candidate=candidate,
        service_profile_context=ContentWorkItemServiceProfileContext.not_evaluated(
            reason=(
                "Work item jest zablokowany przed snapshotem workflow; WILQ nie "
                "przypisuje usługi z samego tytułu ani kolejki."
            ),
            safe_next_step=candidate.safe_next_step,
        ),
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
    freshness_assessment: ContentFreshnessAssessment,
    candidate: ContentWorkItemQueueCandidate,
    human_review_record: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    planning_decisions: list[ContentPlanningDecision] | None = None,
    generated_planning_proposal: ContentPlanningProposal | None = None,
    demand_metric_facts: list[MetricFact] | None = None,
    demand_source_page: str | None = None,
    service_card_id_override: str | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    service_selection = resolve_snapshot_service_selection(
        item=item,
        candidate=candidate,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
        service_card_id_override=service_card_id_override,
        service_profile_builder=build_content_work_item_service_profile_context,
    )
    stage_callbacks = SnapshotStageCallbacks(
        preflight=build_content_work_item_preflight_response,
        sales_brief=build_content_work_item_sales_brief_response,
        draft_package=build_content_work_item_draft_package_response,
        structured_generation=build_content_work_item_structured_draft_generation_response,
        human_review=build_content_work_item_human_review_response,
        wordpress_handoff=build_content_work_item_wordpress_draft_handoff_response,
        measurement_window=build_content_work_item_measurement_window_response,
    )
    return assemble_content_work_item_snapshot(
        item=item,
        inventory_records=inventory_records,
        claim_ledger=claim_ledger,
        seed=seed,
        enrichment=enrichment,
        freshness_assessment=freshness_assessment,
        candidate=service_selection.candidate,
        knowledge_match=service_selection.knowledge_match,
        service_profile_context=service_selection.service_profile_context,
        measurement_window_id=f"measure_{item.id}",
        callbacks=SnapshotAssemblyCallbacks(
            preflight=partial(snapshot_preflight, callbacks=stage_callbacks),
            sales_brief=partial(snapshot_sales_brief, callbacks=stage_callbacks),
            draft_package=partial(snapshot_draft_package, callbacks=stage_callbacks),
            structured_generation=partial(
                snapshot_structured_generation, callbacks=stage_callbacks
            ),
            human_review=partial(snapshot_human_review, callbacks=stage_callbacks),
            wordpress_handoff=partial(snapshot_wordpress_handoff, callbacks=stage_callbacks),
            measurement_window=partial(snapshot_measurement_window, callbacks=stage_callbacks),
        ),
        human_review_record=human_review_record,
        audit=audit,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
        demand_metric_facts=demand_metric_facts,
        demand_source_page=demand_source_page,
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


def _queue_candidate_for_decision(
    diagnostics: ContentDiagnosticsResponse,
    decision_id: str,
) -> ContentWorkItemQueueCandidate:
    decision = next(
        (item for item in diagnostics.decision_queue if item.id == decision_id),
        None,
    )
    if decision is None:
        raise RuntimeError(f"Content decision {decision_id} has no queue candidate.")
    return build_content_work_item_queue_candidate(
        decision,
        diagnostics.freshness_assessment,
    )
