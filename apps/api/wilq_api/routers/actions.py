from __future__ import annotations

from collections.abc import Callable
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
    list_actions,
    mutation_readiness_action,
    mutation_readiness_actions,
    preview_action,
    record_action_review,
    validate_action,
)
from wilq.schemas import (
    ActionApplyRequest,
    ActionConfirmRequest,
    ActionImpactCheckRequest,
    ActionMutationAuditRecord,
    ActionMutationReadinessResponse,
    ActionMutationReadinessSummaryResponse,
    ActionPreviewRequest,
    ActionReviewRequest,
    AdsStrategyReviewRecord,
    AdsTargetGuardrailConfirmation,
    AuditEvent,
)
from wilq.storage.local_state import local_state_store


def create_actions_router(clear_api_view_model_caches: Callable[[], None]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/actions")
    def actions() -> list[dict[str, Any]]:
        return [action.model_dump(mode="json") for action in list_actions()]

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
                    reviewed_by=request.reviewed_by,
                    notes=request.notes,
                    checked_items=request.checked_items,
                    blockers=request.blockers,
                    audit_event_id=result.audit_event.id,
                    evidence_ids=action.evidence_ids,
                )
            )
        clear_api_view_model_caches()
        return result.model_dump(mode="json")

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
                    confirmed_by=request.confirmed_by,
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
