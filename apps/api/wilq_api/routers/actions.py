from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from wilq.actions.google_ads.business_context import (
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
)
from wilq.actions.service import (
    apply_action,
    confirm_action,
    get_action,
    impact_check_action,
    list_actions_cached,
    mutation_readiness_action,
    mutation_readiness_actions,
    preview_action,
    record_action_review,
    validate_action,
)
from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.evidence.registry import list_evidence_by_ids
from wilq.schemas import (
    ActionApplyRequest,
    ActionConfirmRequest,
    ActionImpactCheckRequest,
    ActionMutationAuditRecord,
    ActionMutationReadinessResponse,
    ActionMutationReadinessSummaryResponse,
    ActionPreviewRequest,
    ActionReviewRequest,
    AdsExternalExecutionAcknowledgementRequest,
    AdsExternalObservationRequest,
    AdsStrategyReviewRecord,
    AdsTargetGuardrailConfirmation,
    AuditEvent,
)
from wilq.storage.local_state import local_state_store


def create_actions_router(clear_api_view_model_caches: Callable[[], None]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/actions")
    def actions() -> list[dict[str, Any]]:
        return [action.model_dump(mode="json") for action in list_actions_cached()]

    @router.get(
        "/api/actions/mutation-readiness",
        response_model=ActionMutationReadinessSummaryResponse,
    )
    def actions_mutation_readiness() -> ActionMutationReadinessSummaryResponse:
        return mutation_readiness_actions()

    @router.get("/api/actions/{action_id}")
    def action_detail(action_id: str) -> dict[str, Any]:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        return action.model_dump(mode="json")

    @router.post("/api/actions/{action_id}/validate")
    def validate_action_endpoint(action_id: str) -> dict[str, Any]:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        result = validate_action(action).model_dump(mode="json")
        clear_api_view_model_caches()
        return result

    @router.post("/api/actions/{action_id}/review")
    def review_action_endpoint(
        action_id: str,
        request: ActionReviewRequest,
    ) -> dict[str, Any]:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        result = record_action_review(action, request)
        local_state_store().save_audit_event(result.audit_event)
        if action.id == ADS_STRATEGY_REVIEW_ACTION_ID:
            local_state_store().save_ads_strategy_review(
                AdsStrategyReviewRecord(
                    id=f"ads_strategy_review_{uuid4().hex[:12]}",
                    action_id=action.id,
                    outcome=request.outcome,
                    reviewed_by=result.audit_event.actor,
                    notes=request.notes,
                    checked_items=request.checked_items,
                    blockers=request.blockers,
                    audit_event_id=result.audit_event.id,
                    evidence_ids=action.evidence_ids,
                )
            )
        clear_api_view_model_caches()
        return result.model_dump(mode="json")

    @router.post(
        "/api/actions/{action_id}/external-execution-acknowledgement",
        response_model=AuditEvent,
    )
    def acknowledge_external_ads_execution(
        action_id: str,
        request: AdsExternalExecutionAcknowledgementRequest,
    ) -> AuditEvent:
        """Persist a human report of an Ads change executed outside WILQ.

        This records attribution and the exact measurement-plan binding only;
        it never calls Google Ads and never turns the observation into a
        success claim.
        """

        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        payload = action.payload
        plan = payload.get("measurement_plan")
        if payload.get("action_type") != "campaign_change_review" or not isinstance(plan, dict):
            raise HTTPException(
                status_code=409,
                detail="Ta akcja nie ma zatwierdzonego planu pomiaru Ads.",
            )
        if request.measurement_plan_id != plan.get("id"):
            raise HTTPException(
                status_code=409,
                detail="Potwierdzenie wskazuje inną wersję planu pomiaru.",
            )
        if plan.get("execution_acknowledgement_required") is not True:
            raise HTTPException(
                status_code=409,
                detail="Plan pomiaru nie dopuszcza acknowledgement wykonania.",
            )
        event = AuditEvent(
            id=f"ads_external_execution_{uuid4().hex}",
            action_id=action_id,
            event_type="ads_external_execution_acknowledged",
            event_type_label="Ręczne wykonanie zmiany Ads odnotowane",
            actor=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
            principal_id=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
            workspace_id=LOCAL_PILOT_AUDIT_IDENTITY.workspace_id,
            trust_level=LOCAL_PILOT_AUDIT_IDENTITY.trust_level,
            submitted_actor_label=request.acknowledged_by,
            summary=(
                "WILQ zapisał informację człowieka o wykonaniu zmiany poza API; "
                "nie jest to potwierdzenie vendor write ani sukcesu."
            ),
            evidence_ids=list(plan.get("baseline_evidence_ids", [])),
            details={
                "measurement_plan_id": request.measurement_plan_id,
                "execution_status": request.execution_status,
                "executed_at": request.executed_at.isoformat() if request.executed_at else None,
                "notes": request.notes,
                "observation_required": bool(plan.get("observation_required")),
                "success_claim_allowed": False,
                "vendor_write_attempted": False,
            },
        )
        local_state_store().save_audit_event(event)
        clear_api_view_model_caches()
        return event

    @router.post(
        "/api/actions/{action_id}/external-observation",
        response_model=AuditEvent,
    )
    def record_external_ads_observation(
        action_id: str,
        request: AdsExternalObservationRequest,
    ) -> AuditEvent:
        """Persist a later observation without converting it into causality."""

        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        plan = action.payload.get("measurement_plan")
        if not isinstance(plan, dict) or request.measurement_plan_id != plan.get("id"):
            raise HTTPException(
                status_code=409,
                detail="Observation wskazuje nieaktualny plan pomiaru.",
            )
        acknowledgement = next(
            (
                event
                for event in local_state_store().list_audit_events(action_id=action_id)
                if event.id == request.acknowledgement_event_id
                and event.event_type == "ads_external_execution_acknowledged"
                and event.details.get("measurement_plan_id") == request.measurement_plan_id
            ),
            None,
        )
        if acknowledgement is None:
            raise HTTPException(
                status_code=409,
                detail="Najpierw zapisz acknowledgement ręcznego wykonania dla tego planu.",
            )
        resolved_evidence = list_evidence_by_ids(request.evidence_ids)
        if {evidence.id for evidence in resolved_evidence} != set(request.evidence_ids):
            raise HTTPException(
                status_code=409,
                detail="Obserwacja wskazuje nieznane identyfikatory dowodów.",
            )
        executed_at = acknowledgement.details.get("executed_at")
        if acknowledgement.details.get("execution_status") == "executed" and executed_at:
            try:
                executed_at_value = datetime.fromisoformat(executed_at)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=409,
                    detail="Acknowledgement ma nieprawidłowy czas wykonania.",
                ) from None
            if request.observed_at <= executed_at_value:
                raise HTTPException(
                    status_code=409,
                    detail="Obserwacja musi nastąpić po zgłoszonym wykonaniu zmiany.",
                )
        event = AuditEvent(
            id=f"ads_external_observation_{uuid4().hex}",
            action_id=action_id,
            event_type="ads_external_observation_recorded",
            event_type_label="Obserwacja Ads odnotowana",
            actor=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
            principal_id=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
            workspace_id=LOCAL_PILOT_AUDIT_IDENTITY.workspace_id,
            trust_level=LOCAL_PILOT_AUDIT_IDENTITY.trust_level,
            summary=(
                "WILQ zapisał obserwację po ręcznej zmianie Ads; wynik nie jest "
                "automatycznie sukcesem ani dowodem przyczynowości."
            ),
            evidence_ids=list(request.evidence_ids),
            details={
                "measurement_plan_id": request.measurement_plan_id,
                "acknowledgement_event_id": acknowledgement.id,
                "observation_status": request.observation_status,
                "observed_at": request.observed_at.isoformat(),
                "notes": request.notes,
                "success_claim_allowed": False,
                "causal_claim_allowed": False,
                "vendor_write_attempted": False,
            },
        )
        local_state_store().save_audit_event(event)
        clear_api_view_model_caches()
        return event

    @router.post("/api/actions/{action_id}/preview")
    def preview_action_endpoint(
        action_id: str,
        request: ActionPreviewRequest | None = None,
    ) -> dict[str, Any]:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        result = preview_action(action, request)
        local_state_store().save_audit_event(result.audit_event)
        clear_api_view_model_caches()
        return result.model_dump(mode="json", exclude_none=True)

    @router.post("/api/actions/{action_id}/confirm")
    def confirm_action_endpoint(
        action_id: str,
        request: ActionConfirmRequest,
    ) -> dict[str, Any]:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        result = confirm_action(action, request)
        local_state_store().save_audit_event(result.audit_event)
        if action.id == ADS_TARGET_CONFIRMATION_ACTION_ID and result.confirmed:
            local_state_store().save_ads_target_guardrail_confirmation(
                AdsTargetGuardrailConfirmation(
                    id=f"ads_target_guardrail_{uuid4().hex[:12]}",
                    action_id=action.id,
                    target_roas=request.target_roas,
                    target_cpa_micros=request.target_cpa_micros,
                    confirmed_by=result.audit_event.actor,
                    notes=request.notes,
                    audit_event_id=result.audit_event.id,
                    evidence_ids=action.evidence_ids,
                )
            )
        clear_api_view_model_caches()
        return result.model_dump(mode="json")

    @router.post("/api/actions/{action_id}/impact-check")
    def impact_check_action_endpoint(
        action_id: str,
        request: ActionImpactCheckRequest,
    ) -> dict[str, Any]:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        result = impact_check_action(action, request)
        local_state_store().save_audit_event(result.audit_event)
        clear_api_view_model_caches()
        return result.model_dump(mode="json")

    @router.post("/api/actions/{action_id}/apply")
    def apply_action_endpoint(
        action_id: str,
        request: ActionApplyRequest | None = None,
    ) -> dict[str, Any]:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        result = apply_action(action, request)
        local_state_store().save_audit_event(result.audit_event)
        local_state_store().save_action_mutation_audit(result.mutation_audit)
        clear_api_view_model_caches()
        if not result.applied:
            raise HTTPException(status_code=409, detail=result.model_dump(mode="json"))
        return result.model_dump(mode="json")

    @router.get(
        "/api/actions/{action_id}/mutation-readiness",
        response_model=ActionMutationReadinessResponse,
    )
    def action_mutation_readiness(action_id: str) -> ActionMutationReadinessResponse:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        return mutation_readiness_action(action)

    @router.get("/api/audit/events", response_model=list[AuditEvent])
    def audit_events(action_id: str | None = None) -> list[AuditEvent]:
        return local_state_store().list_audit_events(action_id=action_id)

    @router.get("/api/action-mutation-audits", response_model=list[ActionMutationAuditRecord])
    def action_mutation_audits(
        action_id: str | None = None,
    ) -> list[ActionMutationAuditRecord]:
        return local_state_store().list_action_mutation_audits(action_id=action_id)

    @router.get(
        "/api/actions/{action_id}/mutation-audits",
        response_model=list[ActionMutationAuditRecord],
    )
    def action_mutation_audits_for_action(action_id: str) -> list[ActionMutationAuditRecord]:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
        return local_state_store().list_action_mutation_audits(action_id=action_id)

    return router
