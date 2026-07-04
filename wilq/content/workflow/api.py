from __future__ import annotations

from datetime import date
from typing import Literal

from wilq.connectors.wordpress.authoring import build_wordpress_authoring_profile
from wilq.connectors.wordpress.client import create_wordpress_draft_post
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
from wilq.content.handoff.wordpress_authoring import (
    build_content_wordpress_authoring_payload_preview,
)
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftWriteAuthorization,
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
from wilq.content.measurement.outcome import interpret_content_measurement_outcome
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
from wilq.content.quality.revision_apply import apply_content_revision_plan
from wilq.content.review.human import (
    ContentHumanReview,
    apply_content_human_review_to_work_item,
    content_human_review_allows_wordpress_handoff,
    content_human_review_blockers,
)
from wilq.content.workflow import operator_steps as workflow_steps
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessBlocker,
    ContentWordPressDraftWriteReadinessRequirement,
    ContentWordPressDraftWriteReadinessResponse,
    ContentWorkItemBlockedSnapshotResponse,
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemDraftVariantsRequest,
    ContentWorkItemDraftVariantsResponse,
    ContentWorkItemHumanReviewRequest,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementOutcomeRequest,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowRequest,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightRequest,
    ContentWorkItemPreflightResponse,
    ContentWorkItemQualityReviewRequest,
    ContentWorkItemQualityReviewResponse,
    ContentWorkItemRevisionApplyRequest,
    ContentWorkItemRevisionApplyResponse,
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
    ContentWorkItemWordPressAuthoringPayloadPreviewRequest,
    ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
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
from wilq.content.workflow.queue import build_content_work_item_queue_response
from wilq.credentials.runtime import variable_value
from wilq.schemas import AuditEvent, ContentDecisionItem, ContentDiagnosticsResponse
from wilq.storage.local_state import local_state_store


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
            knowledge_match=request.knowledge_match or match_content_knowledge_cards(request.item),
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
            knowledge_match=request.knowledge_match or match_content_knowledge_cards(request.item),
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
    live_write_enabled = _wordpress_draft_writes_enabled()
    return ContentWorkItemWordPressDraftExecutionResponse(
        execution_result=execute_content_wordpress_draft_handoff(
            handoff=request.handoff,
            draft_package=request.draft_package,
            mode=request.mode,
            live_write_enabled=live_write_enabled,
            create_draft=create_wordpress_draft_post if live_write_enabled else None,
            write_authorization=request.write_authorization,
            write_authorization_verified=_wordpress_draft_write_authorization_verified(
                request.write_authorization
            ),
        ),
    )


def build_content_wordpress_draft_activation_packet_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    action_id: str = "act_apply_wordpress_draft_handoff",
) -> ContentWordPressDraftActivationPacketResponse:
    item = snapshot.preflight.item
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    handoff_result = snapshot.wordpress_handoff.handoff_result
    handoff = handoff_result.handoff
    execution = execute_content_wordpress_draft_handoff(
        handoff=handoff,
        draft_package=draft_package,
        mode="dry_run",
        live_write_enabled=False,
        create_draft=None,
    )
    handoff_blockers = [blocker.code for blocker in handoff_result.blockers]
    execution_blockers = [blocker.code for blocker in execution.blockers]
    human_review_ready = "missing_human_review" not in handoff_blockers
    audit_ready = "missing_audit" not in handoff_blockers
    activation_missing_step = _wordpress_draft_activation_missing_step(
        draft_package_ready=draft_package is not None,
        human_review_ready=human_review_ready,
        audit_ready=audit_ready,
        handoff_ready=handoff is not None,
        dry_run_ready=execution.status == "dry_run_ready",
    )
    return ContentWordPressDraftActivationPacketResponse(
        action_id=action_id,
        work_item_id=item.id,
        topic=item.topic,
        final_canonical_url=item.final_canonical_url,
        draft_package_ready=draft_package is not None,
        draft_package_id=draft_package.id if draft_package is not None else None,
        review_preview_ready=draft_package is not None,
        review_preview_status_label=_wordpress_draft_review_preview_status_label(
            draft_package is not None
        ),
        human_review_checklist=_wordpress_draft_human_review_checklist(
            draft_package_ready=draft_package is not None,
            human_review_ready=human_review_ready,
        ),
        human_review_ready=human_review_ready,
        audit_ready=audit_ready,
        handoff_ready=handoff is not None,
        handoff_id=handoff.id if handoff is not None else None,
        dry_run_ready=execution.status == "dry_run_ready",
        live_write_enabled_by_env=False,
        handoff_blockers=handoff_blockers,
        execution_blockers=execution_blockers,
        activation_missing_step=activation_missing_step,
        activation_missing_step_label=_wordpress_draft_activation_missing_step_label(
            activation_missing_step
        ),
        activation_missing_readiness_labels=_wordpress_draft_activation_missing_labels(
            draft_package_ready=draft_package is not None,
            human_review_ready=human_review_ready,
            audit_ready=audit_ready,
            handoff_ready=handoff is not None,
            dry_run_ready=execution.status == "dry_run_ready",
        ),
        execution_result=execution,
        operator_next_step=_wordpress_draft_activation_next_step(
            handoff_blockers,
            execution_blockers,
        ),
        next_steps=_wordpress_draft_activation_steps(
            draft_package_ready=draft_package is not None,
            handoff_blockers=handoff_blockers,
            execution_blockers=execution_blockers,
        ),
        evidence_ids=item.evidence_ids,
        source_connectors=item.source_connectors,
    )


def _wordpress_draft_activation_missing_step(
    *,
    draft_package_ready: bool,
    human_review_ready: bool,
    audit_ready: bool,
    handoff_ready: bool,
    dry_run_ready: bool,
) -> Literal["draft_package", "human_review", "audit", "handoff", "dry_run", "ready"]:
    if not draft_package_ready:
        return "draft_package"
    if not human_review_ready:
        return "human_review"
    if not audit_ready:
        return "audit"
    if not handoff_ready:
        return "handoff"
    if not dry_run_ready:
        return "dry_run"
    return "ready"


def _wordpress_draft_activation_missing_step_label(step: str) -> str:
    labels = {
        "draft_package": "przygotuj paczkę szkicu",
        "human_review": "zapisz review człowieka",
        "audit": "zapisz audit przekazania do WordPress",
        "handoff": "przygotuj handoff WordPress draft-only",
        "dry_run": "wygeneruj podgląd dry-run payloadu WordPress",
        "ready": "podgląd draft-only jest gotowy do review",
    }
    return labels.get(step, "sprawdź paczkę aktywacji WordPress")


def _wordpress_draft_activation_missing_labels(
    *,
    draft_package_ready: bool,
    human_review_ready: bool,
    audit_ready: bool,
    handoff_ready: bool,
    dry_run_ready: bool,
) -> list[str]:
    labels: list[str] = []
    if not draft_package_ready:
        labels.append("paczka szkicu")
    if not human_review_ready:
        labels.append("review człowieka")
    if not audit_ready:
        labels.append("audit przekazania")
    if not handoff_ready:
        labels.append("handoff WordPress")
    if not dry_run_ready:
        labels.append("podgląd dry-run")
    return labels


def _wordpress_draft_review_preview_status_label(
    draft_package_ready: bool,
) -> str:
    if draft_package_ready:
        return "Paczka szkicu jest gotowa do review człowieka."
    return "Najpierw przygotuj paczkę szkicu z Claim Ledgerem i dowodami."


def _wordpress_draft_human_review_checklist(
    *,
    draft_package_ready: bool,
    human_review_ready: bool,
) -> list[str]:
    if human_review_ready:
        return [
            "Review człowieka jest zapisane; teraz sprawdź audyt i handoff WordPress.",
        ]
    if not draft_package_ready:
        return [
            "Przygotuj paczkę szkicu z tytułem, sekcjami, mapą dowodów i Claim Ledgerem.",
            "Nie oceniaj handoffu WordPress przed paczką szkicu.",
        ]
    return [
        "Czy tytuł, sekcje i kolejność odpowiadają intencji wybranego tematu?",
        "Czy każdy claim ma dowód albo jest jawnie zablokowany w Claim Ledger?",
        "Czy treść brzmi jak Ekologus, a nie jak generyczny artykuł SEO?",
        "Czy CTA jest konsultacyjne i nie obiecuje wyniku, decyzji ani braku kar?",
        "Czy materiał ma zostać tylko szkicem WordPress, bez publikacji i bez "
        "aktualizacji istniejącego wpisu?",
    ]


def build_content_wordpress_draft_write_readiness_response(
    action_id: str = "act_prepare_wordpress_draft_handoff",
    connector_id: str = "wordpress_ekologus",
) -> ContentWordPressDraftWriteReadinessResponse:
    live_write_enabled = _wordpress_draft_writes_enabled()
    profile = build_wordpress_authoring_profile(connector_id)
    rest_adapter_configured = profile.rest_api.status == "configured"
    requirements, authorization = _wordpress_draft_write_audit_readiness(action_id)
    blockers: list[ContentWordPressDraftWriteReadinessBlocker] = []
    if not live_write_enabled:
        blockers.append(
            ContentWordPressDraftWriteReadinessBlocker(
                code="draft_writes_env_disabled",
                label="Zapis szkiców WordPress jest wyłączony",
                reason=(
                    "WILQ może przygotować i sprawdzić szkic, ale live write wymaga "
                    "jawnego włączenia WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES."
                ),
                next_step=(
                    "Zostaw tryb dry-run albo włącz env dopiero po potwierdzeniu "
                    "ścieżki preview, review, confirm i audit."
                ),
            )
        )
    if not rest_adapter_configured:
        blockers.append(
            ContentWordPressDraftWriteReadinessBlocker(
                code="wordpress_rest_adapter_not_configured",
                label="Adapter REST WordPress nie jest gotowy",
                reason=(
                    "Brakuje kompletnej konfiguracji REST: adresu WordPress i "
                    "uwierzytelnienia aplikacyjnego."
                ),
                next_step=(
                    "Uzupełnij konfigurację WordPress REST dla connectora, potem "
                    "sprawdź authoring profile i dopiero wróć do live write."
                ),
            )
        )
    blockers.extend(_wordpress_draft_write_audit_blockers(requirements, authorization))
    missing_audit_event_types = [
        requirement.event_type for requirement in requirements if not requirement.satisfied
    ]
    write_authorization_status = _wordpress_draft_write_authorization_status(
        requirements,
        authorization,
    )
    ready = (
        live_write_enabled
        and rest_adapter_configured
        and authorization is not None
        and not blockers
    )
    return ContentWordPressDraftWriteReadinessResponse(
        connector=connector_id,
        action_id=action_id,
        ready=ready,
        live_write_enabled_by_env=live_write_enabled,
        rest_adapter_configured=rest_adapter_configured,
        required_audit_events=requirements,
        missing_audit_event_types=missing_audit_event_types,
        write_authorization_status=write_authorization_status,
        suggested_write_authorization=authorization if ready else None,
        blockers=blockers,
        operator_next_step=_wordpress_draft_write_next_step(ready, blockers),
        evidence_ids=profile.evidence_ids,
        source_connectors=profile.source_connectors or [connector_id],
    )


def _wordpress_draft_writes_enabled() -> bool:
    return (variable_value("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _wordpress_draft_activation_next_step(
    handoff_blockers: list[str],
    execution_blockers: list[str],
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
    return (
        "Dry-run payload szkicu jest gotowy do review. Live write nadal wymaga "
        "ActionObject preview/review/confirm/audit i jawnie włączonego env."
    )


def _wordpress_draft_activation_steps(
    *,
    draft_package_ready: bool,
    handoff_blockers: list[str],
    execution_blockers: list[str],
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
    if not {*handoff_blockers, *execution_blockers}:
        steps.append("Sprawdź payload dry-run, a live write zostaw wyłączony do osobnej decyzji.")
    return steps


def _wordpress_draft_write_authorization_verified(
    authorization: ContentWordPressDraftWriteAuthorization | None,
) -> bool:
    if authorization is None:
        return False
    events = {
        event.id: event
        for event in local_state_store().list_audit_events(
            action_id=authorization.action_id
        )
    }
    required = {
        authorization.preview_audit_id: "action_preview_generated",
        authorization.review_audit_id: "human_review_",
        authorization.confirmation_audit_id: "action_apply_confirmed",
    }
    if authorization.apply_audit_id:
        required[authorization.apply_audit_id] = "apply_succeeded"
    for event_id, expected_type in required.items():
        event = events.get(event_id)
        if event is None or event.action_id != authorization.action_id:
            return False
        if expected_type.endswith("_"):
            if not event.event_type.startswith(expected_type):
                return False
        elif event.event_type != expected_type:
                return False
    confirmation_event = events.get(authorization.confirmation_audit_id)
    apply_event = (
        events.get(authorization.apply_audit_id)
        if authorization.apply_audit_id is not None
        else None
    )
    confirmed_by = authorization.confirmed_by.strip()
    if not (
        confirmed_by
        and confirmation_event is not None
        and confirmation_event.actor == confirmed_by
    ):
        return False
    if authorization.apply_audit_id is None:
        return True
    return bool(apply_event is not None and apply_event.actor == confirmed_by)


def _wordpress_draft_write_audit_readiness(
    action_id: str,
) -> tuple[
    list[ContentWordPressDraftWriteReadinessRequirement],
    ContentWordPressDraftWriteAuthorization | None,
]:
    events = sorted(
        local_state_store().list_audit_events(action_id=action_id),
        key=lambda event: event.created_at,
        reverse=True,
    )
    preview = _latest_exact_event(events, "action_preview_generated")
    review = _latest_prefix_event(events, "human_review_")
    confirmation = _latest_exact_event(events, "action_apply_confirmed")
    requirements = [
        _readiness_requirement(
            event_type="action_preview_generated",
            label="Podgląd akcji wygenerowany",
            event=preview,
        ),
        _readiness_requirement(
            event_type="human_review_*",
            label="Review człowieka zapisane",
            event=review,
        ),
        _readiness_requirement(
            event_type="action_apply_confirmed",
            label="Potwierdzenie operatora zapisane",
            event=confirmation,
        ),
    ]
    if (
        preview is None
        or review is None
        or confirmation is None
        or not confirmation.actor.strip()
    ):
        return requirements, None
    return requirements, ContentWordPressDraftWriteAuthorization(
        action_id=action_id,
        preview_audit_id=preview.id,
        review_audit_id=review.id,
        confirmation_audit_id=confirmation.id,
        confirmed_by=confirmation.actor,
    )


def _latest_exact_event(
    events: list[AuditEvent],
    event_type: str,
) -> AuditEvent | None:
    return next((event for event in events if event.event_type == event_type), None)


def _latest_prefix_event(
    events: list[AuditEvent],
    event_type_prefix: str,
) -> AuditEvent | None:
    return next(
        (event for event in events if event.event_type.startswith(event_type_prefix)),
        None,
    )


def _readiness_requirement(
    *,
    event_type: str,
    label: str,
    event: AuditEvent | None,
) -> ContentWordPressDraftWriteReadinessRequirement:
    return ContentWordPressDraftWriteReadinessRequirement(
        event_type=event_type,
        label=label,
        satisfied=event is not None,
        audit_event_id=event.id if event is not None else None,
        actor=event.actor if event is not None else None,
    )


def _wordpress_draft_write_audit_blockers(
    requirements: list[ContentWordPressDraftWriteReadinessRequirement],
    authorization: ContentWordPressDraftWriteAuthorization | None,
) -> list[ContentWordPressDraftWriteReadinessBlocker]:
    missing = [requirement for requirement in requirements if not requirement.satisfied]
    blocker_codes = {
        "action_preview_generated": "missing_action_preview_audit",
        "human_review_*": "missing_human_review_audit",
        "action_apply_confirmed": "missing_action_confirmation_audit",
    }
    blockers = [
        ContentWordPressDraftWriteReadinessBlocker(
            code=blocker_codes.get(requirement.event_type, "missing_action_audit"),
            label=f"Brakuje: {requirement.label}",
            reason=(
                "Live write wymaga pełnego śladu ActionObject zanim adapter "
                "WordPress może zapisać szkic."
            ),
            next_step=(
                "Wykonaj validate/preview, review człowieka i confirm/apply "
                "w WILQ, bez ręcznego składania ID."
            ),
        )
        for requirement in missing
    ]
    if not missing and authorization is None:
        blockers.append(
            ContentWordPressDraftWriteReadinessBlocker(
                code="audit_actor_mismatch",
                label="Audit trail nie wskazuje jednego operatora",
                reason=(
                    "Potwierdzenie musi mieć niepustego aktora, "
                    "żeby WILQ mógł zbudować write_authorization."
                ),
                next_step=(
                    "Powtórz confirm jedną ścieżką operatora zamiast "
                    "składać audit ręcznie."
                ),
            )
        )
    return blockers


def _wordpress_draft_write_authorization_status(
    requirements: list[ContentWordPressDraftWriteReadinessRequirement],
    authorization: ContentWordPressDraftWriteAuthorization | None,
) -> Literal["missing_audit_trace", "audit_actor_mismatch", "available"]:
    if any(not requirement.satisfied for requirement in requirements):
        return "missing_audit_trace"
    if authorization is None:
        return "audit_actor_mismatch"
    return "available"


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
    profile = request.authoring_profile or build_wordpress_authoring_profile(
        "wordpress_ekologus"
    )
    return ContentWorkItemWordPressAuthoringPayloadPreviewResponse(
        authoring_profile=profile,
        preview_result=build_content_wordpress_authoring_payload_preview(
            handoff=request.handoff,
            draft_package=request.draft_package,
            authoring_profile=profile,
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


def build_content_work_item_measurement_outcome_response(
    request: ContentWorkItemMeasurementOutcomeRequest,
) -> ContentWorkItemMeasurementOutcomeResponse:
    return ContentWorkItemMeasurementOutcomeResponse(
        outcome=interpret_content_measurement_outcome(
            window=request.window,
            observed_metrics=request.observed_metrics,
            as_of=request.as_of,
        )
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
        claim_ledger=claim_ledger,
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
            knowledge_match=match_content_knowledge_cards(item),
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
            knowledge_match=match_content_knowledge_cards(item),
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
