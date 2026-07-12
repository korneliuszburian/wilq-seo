from __future__ import annotations

from datetime import date
from typing import Literal
from urllib.parse import urlparse

from wilq.connectors.wordpress.authoring import build_wordpress_authoring_profile
from wilq.connectors.wordpress.client import (
    WordPressDraftReadError,
    read_wordpress_draft_post,
)
from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefSeed,
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
)
from wilq.content.drafts.preview import (
    build_structured_draft_preview,
)
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
    ContentWordPressDraftWriteAuthorization,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.inventory.records import (
    ContentInventoryRecord,
)
from wilq.content.knowledge.cards import (
    ContentKnowledgeCardMatch,
    match_content_knowledge_cards,
)
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
    build_content_work_item_service_profile_context,
)
from wilq.content.measurement.outcome import interpret_content_measurement_outcome
from wilq.content.measurement.window import (
    ContentDateRange,
    apply_content_measurement_window_to_work_item,
    build_content_measurement_window,
    content_measurement_window_outcome_blockers,
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
from wilq.content.workflow import operator_steps as workflow_steps
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftReadback,
    ContentWordPressDraftReadbackBlocker,
    ContentWordPressDraftWriteReadinessBlocker,
    ContentWordPressDraftWriteReadinessRequirement,
    ContentWordPressDraftWriteReadinessResponse,
    ContentWordPressExistingDraftSectionDiff,
    ContentWordPressExistingDraftUpdateReadinessResponse,
    ContentWorkItemBlockedSnapshotResponse,
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
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
from wilq.content.workflow.queue import (
    ContentWorkItemQueueCandidate,
    build_content_work_item_queue_candidate,
    build_content_work_item_queue_response,
)
from wilq.content.workflow.snapshot_assembly import (
    SnapshotAssemblyCallbacks,
    assemble_content_work_item_snapshot,
)
from wilq.content.workflow.stage_drafts import (
    build_content_work_item_draft_package_response,
    build_content_work_item_draft_variants_response,  # noqa: F401 - router compatibility export
    build_content_work_item_structured_draft_generation_response,
)
from wilq.content.workflow.stage_preparation import (
    build_content_work_item_preflight_response,
    build_content_work_item_sales_brief_response,
)
from wilq.content.workflow.stage_review import (
    build_content_work_item_human_review_response,
    build_content_work_item_wordpress_draft_handoff_response,
)
from wilq.credentials.runtime import variable_value
from wilq.schemas import (
    AuditEvent,
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    ContentFreshnessAssessment,
)
from wilq.storage.local_state import local_state_store


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
            create_draft=None,
            action_apply_authorized=False,
            write_authorization=request.write_authorization,
            write_authorization_verified=_wordpress_draft_write_authorization_verified(
                request.write_authorization
            ),
            section_overrides=request.section_overrides,
        ),
    )


def build_content_wordpress_draft_activation_packet_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    action_id: str = "act_apply_wordpress_draft_handoff",
    latest_execution_result: ContentWordPressDraftExecutionResult | None = None,
) -> ContentWordPressDraftActivationPacketResponse:
    item = snapshot.preflight.item
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    handoff_result = snapshot.wordpress_handoff.handoff_result
    handoff = handoff_result.handoff
    execution = latest_execution_result or execute_content_wordpress_draft_handoff(
        handoff=handoff,
        draft_package=draft_package,
        mode="dry_run",
        live_write_enabled=False,
        create_draft=None,
    )
    handoff_blockers: list[str] = [blocker.code for blocker in handoff_result.blockers]
    execution_blockers: list[str] = [blocker.code for blocker in execution.blockers]
    execution_ready = execution.status in {"dry_run_ready", "created"}
    draft_readback = _wordpress_draft_readback(execution)
    human_review_ready = "missing_human_review" not in handoff_blockers
    audit_ready = "missing_audit" not in handoff_blockers
    activation_missing_step = _wordpress_draft_activation_missing_step(
        draft_package_ready=draft_package is not None,
        human_review_ready=human_review_ready,
        audit_ready=audit_ready,
        handoff_ready=handoff is not None,
        dry_run_ready=execution_ready,
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
        dry_run_ready=execution_ready,
        live_write_enabled_by_env=_wordpress_draft_writes_enabled(),
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
            dry_run_ready=execution_ready,
        ),
        execution_result=execution,
        draft_readback=draft_readback,
        operator_next_step=_wordpress_draft_activation_next_step(
            handoff_blockers,
            execution_blockers,
            execution_status=execution.status,
            draft_readback=draft_readback,
        ),
        next_steps=_wordpress_draft_activation_steps(
            draft_package_ready=draft_package is not None,
            handoff_blockers=handoff_blockers,
            execution_blockers=execution_blockers,
            execution_status=execution.status,
        ),
        evidence_ids=item.evidence_ids,
        source_connectors=item.source_connectors,
    )


def _wordpress_draft_readback(
    execution: ContentWordPressDraftExecutionResult,
) -> ContentWordPressDraftReadback | None:
    if execution.status != "created":
        return None
    post_id = (execution.wordpress_post_id or "").strip()
    if not post_id:
        return ContentWordPressDraftReadback(
            status="blocked",
            wordpress_post_id=None,
            blockers=[
                ContentWordPressDraftReadbackBlocker(
                    code="missing_wordpress_post_id",
                    label="Brak ID szkicu WordPress",
                    reason=(
                        "WILQ zapisał wynik utworzenia szkicu, ale nie ma ID wpisu "
                        "potrzebnego do odczytu z dev WordPressa."
                    ),
                    next_step=(
                        "Utwórz szkic ponownie przez ActionObject albo sprawdź audit "
                        "wykonania zapisu."
                    ),
                )
            ],
        )
    try:
        readback = read_wordpress_draft_post(post_id)
    except WordPressDraftReadError as exc:
        return ContentWordPressDraftReadback(
            status="blocked",
            wordpress_post_id=post_id,
            blockers=[
                ContentWordPressDraftReadbackBlocker(
                    code="wordpress_draft_read_failed",
                    label="Nie udało się odczytać szkicu WordPress",
                    reason=exc.public_message,
                    next_step=(
                        "Sprawdź dostęp REST WordPress i odśwież panel szkicu. "
                        "Nie traktuj samego ID jako potwierdzenia treści."
                    ),
                )
            ],
        )
    return ContentWordPressDraftReadback(
        status="available",
        wordpress_post_id=readback.post_id,
        post_status=readback.status,
        title=readback.title,
        link=readback.link,
        modified_gmt=readback.modified_gmt,
        content_summary=readback.content_summary,
        content_word_count=readback.content_word_count,
        acf_field_count=readback.acf_field_count,
        acf_field_names=readback.acf_field_names,
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
    blockers: list[ContentWordPressDraftWriteReadinessBlocker] = [
        ContentWordPressDraftWriteReadinessBlocker(
            code="actionobject_apply_path_required",
            label="Zapis jest dostępny tylko przez kanoniczną akcję apply",
            reason=(
                "Ślad preview/review/confirm nie upoważnia content endpointu do "
                "samodzielnego wywołania adaptera WordPress."
            ),
            next_step=(
                "Użyj dry-run. Przywrócenie live write wymaga apply-capable "
                "ActionObject, spójnego mutation readiness i ActionMutationAudit."
            ),
        )
    ]
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
    ready = False
    authorization_status: Literal[
        "missing_audit_trace",
        "audit_actor_mismatch",
        "available",
        "blocked_outside_action_apply",
    ] = _wordpress_draft_write_authorization_status(
        requirements,
        authorization,
    )
    if authorization is not None:
        authorization_status = "blocked_outside_action_apply"
    return ContentWordPressDraftWriteReadinessResponse(
        connector=connector_id,
        action_id=action_id,
        ready=ready,
        live_write_enabled_by_env=live_write_enabled,
        rest_adapter_configured=rest_adapter_configured,
        required_audit_events=requirements,
        missing_audit_event_types=missing_audit_event_types,
        write_authorization_status=authorization_status,
        suggested_write_authorization=None,
        blockers=blockers,
        operator_next_step=_wordpress_draft_write_next_step(ready, blockers),
        evidence_ids=profile.evidence_ids,
        source_connectors=profile.source_connectors or [connector_id],
    )


def build_content_wordpress_existing_draft_update_readiness_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentWordPressExistingDraftUpdateReadinessResponse:
    profile = build_wordpress_authoring_profile("wordpress_ekologus", include_dev_content=True)
    draft = snapshot.draft_package.draft_package_result.draft_package
    source_url = snapshot.preflight.item.source_public_url or ""
    source_path = urlparse(source_url).path or "/"
    target = next(
        (
            page
            for page in profile.dev_content.pages
            if (urlparse(page.link).path or "/") == source_path
        ),
        None,
    )
    current_sections = target.sections if target is not None else []
    proposed_sections = draft.sections if draft is not None else []
    current_by_heading = {
        section.title or section.layout_label: section for section in current_sections
    }
    diff_preview: list[ContentWordPressExistingDraftSectionDiff] = []
    for section in proposed_sections[:8]:
        heading = section.heading or "Sekcja bez tytułu"
        current = current_by_heading.get(heading)
        proposed_summary = " ".join(
            [section.purpose, *section.draft_notes]
        ).strip()[:240]
        current_summary = current.text_summary[:240] if current is not None else ""
        diff_preview.append(
            ContentWordPressExistingDraftSectionDiff(
                heading=heading,
                current_summary=current_summary,
                proposed_summary=proposed_summary,
                status=(
                    "missing_current"
                    if current is None
                    else "unchanged"
                    if current_summary == proposed_summary
                    else "changed"
                ),
            )
        )
    blocker = ContentWordPressDraftWriteReadinessBlocker(
        code="existing_draft_update_contract_not_implemented",
        label="Aktualizacja istniejącego draftu wymaga osobnego kontraktu",
        reason=(
            "WILQ ma odczyt dev i podgląd proponowanych sekcji, ale nie wykonuje jeszcze "
            "aktualizacji istniejącego posta ani pól ACF."
        ),
        next_step=(
            "Pozostaw podgląd bez zapisu i przejdź przez review; dopiero po wdrożeniu "
            "ActionObject update preview/review/confirm można odblokować zapis dev."
        ),
    )
    return ContentWordPressExistingDraftUpdateReadinessResponse(
        work_item_id=snapshot.preflight.item.id,
        target_post_id=target.post_id if target is not None else None,
        target_url=target.link if target is not None else None,
        current_state_available=target is not None,
        current_section_count=len(current_sections),
        proposed_section_count=len(draft.sections) if draft is not None else 0,
        section_diff_preview=diff_preview,
        blockers=[blocker],
        operator_next_step=blocker.next_step,
        evidence_ids=[*snapshot.preflight.item.evidence_ids, *profile.evidence_ids],
        source_connectors=list(
            dict.fromkeys(
                [*snapshot.preflight.item.source_connectors, *profile.source_connectors]
            )
        ),
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
    candidate = _queue_candidate_for_decision(diagnostics, decision.id)
    return _build_content_work_item_diagnostics_snapshot_response_from_decision(
        decision,
        freshness_assessment=diagnostics.freshness_assessment,
        candidate=candidate,
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
    candidate = _queue_candidate_for_decision(diagnostics, decision.id)
    return _build_content_work_item_diagnostics_snapshot_response_from_decision(
        decision,
        freshness_assessment=diagnostics.freshness_assessment,
        candidate=candidate,
        human_review=human_review,
        audit=audit,
    )


def _build_content_work_item_diagnostics_snapshot_response_from_decision(
    decision: ContentDecisionItem,
    *,
    freshness_assessment: ContentFreshnessAssessment,
    candidate: ContentWorkItemQueueCandidate,
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
        freshness_assessment=freshness_assessment,
        candidate=candidate,
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
) -> ContentWorkItemWorkflowSnapshotResponse:
    knowledge_match = match_content_knowledge_cards(item)
    service_profile_context = build_content_work_item_service_profile_context(
        item,
        knowledge_match=knowledge_match,
    )
    return assemble_content_work_item_snapshot(
        item=item,
        inventory_records=inventory_records,
        claim_ledger=claim_ledger,
        seed=seed,
        enrichment=enrichment,
        freshness_assessment=freshness_assessment,
        candidate=candidate,
        knowledge_match=knowledge_match,
        service_profile_context=service_profile_context,
        measurement_window_id=f"measure_{item.id}",
        callbacks=SnapshotAssemblyCallbacks(
            preflight=_snapshot_preflight,
            sales_brief=_snapshot_sales_brief,
            draft_package=_snapshot_draft_package,
            structured_generation=_snapshot_structured_generation,
            human_review=_snapshot_human_review,
            wordpress_handoff=_snapshot_wordpress_handoff,
            measurement_window=_snapshot_measurement_window,
            operator_steps=workflow_steps.content_workflow_operator_steps,
        ),
        human_review_record=human_review_record,
        audit=audit,
    )


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
    knowledge_match: ContentKnowledgeCardMatch,
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
            knowledge_match=knowledge_match,
        )
    )


def _snapshot_draft_package(
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    knowledge_match: ContentKnowledgeCardMatch,
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
            knowledge_match=knowledge_match,
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


def _snapshot_wordpress_handoff(
    item: ContentWorkItem,
    draft: ContentDraftPackage | None,
    human_review: ContentHumanReview | None,
    audit: ContentWordPressDraftAuditEnvelope | None,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    return build_content_work_item_wordpress_draft_handoff_response(
        ContentWorkItemWordPressDraftHandoffRequest(
            item=item,
            draft_package=draft,
            human_review=human_review,
            audit=audit,
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
