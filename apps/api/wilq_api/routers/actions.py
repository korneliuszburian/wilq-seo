from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from wilq.actions import ads_external_execution
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
from wilq.audit.trusted_local_confirmation import TrustedLocalConfirmationError
from wilq.content.workflow.current_disposition_authority import (
    CURRENT_DISPOSITION_ACTION_TYPE,
)
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionConfirmRequest,
    ActionConfirmResult,
    ActionImpactCheckRequest,
    ActionImpactCheckResult,
    ActionMutationAuditRecord,
    ActionMutationReadinessResponse,
    ActionMutationReadinessSummaryResponse,
    ActionObject,
    ActionPreviewRequest,
    ActionPreviewResult,
    ActionReviewRequest,
    ActionReviewResult,
    ActionValidationResult,
    AdsExternalExecutionAcknowledgementRequest,
    AdsExternalObservationRequest,
    AuditEvent,
)
from wilq.storage.local_state import local_state_store


def create_actions_router(clear_api_view_model_caches: Callable[[], None]) -> APIRouter:
    router = APIRouter()

    _register_action_query_and_review_routes(
        router,
        clear_api_view_model_caches=clear_api_view_model_caches,
    )
    _register_external_action_routes(
        router,
        clear_api_view_model_caches=clear_api_view_model_caches,
    )
    _register_action_lifecycle_routes(
        router,
        clear_api_view_model_caches=clear_api_view_model_caches,
    )
    _register_action_readiness_and_audit_routes(router)

    return router


def _register_action_query_and_review_routes(
    router: APIRouter,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> None:
    @router.get("/api/actions", response_model=list[ActionObject])
    def actions() -> list[ActionObject]:
        return _actions()

    @router.get(
        "/api/actions/mutation-readiness",
        response_model=ActionMutationReadinessSummaryResponse,
    )
    def actions_mutation_readiness() -> ActionMutationReadinessSummaryResponse:
        return _actions_mutation_readiness()

    @router.get("/api/actions/{action_id}", response_model=ActionObject)
    def action_detail(action_id: str) -> ActionObject:
        return _action_detail(action_id)

    @router.post("/api/actions/{action_id}/validate", response_model=ActionValidationResult)
    def validate_action_endpoint(action_id: str) -> ActionValidationResult:
        return _validate_action_endpoint(
            action_id,
            clear_api_view_model_caches=clear_api_view_model_caches,
        )

    @router.post("/api/actions/{action_id}/review", response_model=ActionReviewResult)
    def review_action_endpoint(
        action_id: str,
        request: ActionReviewRequest,
    ) -> ActionReviewResult:
        return _review_action_endpoint(
            action_id,
            request,
            clear_api_view_model_caches=clear_api_view_model_caches,
        )


def _register_external_action_routes(
    router: APIRouter,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> None:
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

        return _acknowledge_external_ads_execution(
            action_id,
            request,
            clear_api_view_model_caches=clear_api_view_model_caches,
        )

    @router.post(
        "/api/actions/{action_id}/external-observation",
        response_model=AuditEvent,
    )
    def record_external_ads_observation(
        action_id: str,
        request: AdsExternalObservationRequest,
    ) -> AuditEvent:
        """Persist a later observation without converting it into causality."""

        return _record_external_ads_observation(
            action_id,
            request,
            clear_api_view_model_caches=clear_api_view_model_caches,
        )


def _register_action_lifecycle_routes(
    router: APIRouter,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> None:
    @router.post(
        "/api/actions/{action_id}/preview",
        response_model=ActionPreviewResult,
        response_model_exclude_none=True,
    )
    def preview_action_endpoint(
        action_id: str,
        request: ActionPreviewRequest | None = None,
    ) -> ActionPreviewResult:
        return _preview_action_endpoint(
            action_id,
            request,
            clear_api_view_model_caches=clear_api_view_model_caches,
        )

    @router.post("/api/actions/{action_id}/confirm", response_model=ActionConfirmResult)
    def confirm_action_endpoint(
        action_id: str,
        request: ActionConfirmRequest,
    ) -> ActionConfirmResult:
        return _confirm_action_endpoint(
            action_id,
            request,
            clear_api_view_model_caches=clear_api_view_model_caches,
        )

    @router.post(
        "/api/actions/{action_id}/impact-check",
        response_model=ActionImpactCheckResult,
    )
    def impact_check_action_endpoint(
        action_id: str,
        request: ActionImpactCheckRequest,
    ) -> ActionImpactCheckResult:
        return _impact_check_action_endpoint(
            action_id,
            request,
            clear_api_view_model_caches=clear_api_view_model_caches,
        )

    @router.post("/api/actions/{action_id}/apply", response_model=ActionApplyResult)
    def apply_action_endpoint(
        action_id: str,
        request: ActionApplyRequest | None = None,
    ) -> ActionApplyResult:
        return _apply_action_endpoint(
            action_id,
            request,
            clear_api_view_model_caches=clear_api_view_model_caches,
        )


def _register_action_readiness_and_audit_routes(router: APIRouter) -> None:
    @router.get(
        "/api/actions/{action_id}/mutation-readiness",
        response_model=ActionMutationReadinessResponse,
    )
    def action_mutation_readiness(action_id: str) -> ActionMutationReadinessResponse:
        return _action_mutation_readiness(action_id)

    @router.get("/api/audit/events", response_model=list[AuditEvent])
    def audit_events(action_id: str | None = None) -> list[AuditEvent]:
        return _audit_events(action_id)

    @router.get("/api/action-mutation-audits", response_model=list[ActionMutationAuditRecord])
    def action_mutation_audits(
        action_id: str | None = None,
    ) -> list[ActionMutationAuditRecord]:
        return _action_mutation_audits(action_id)

    @router.get(
        "/api/actions/{action_id}/mutation-audits",
        response_model=list[ActionMutationAuditRecord],
    )
    def action_mutation_audits_for_action(action_id: str) -> list[ActionMutationAuditRecord]:
        return _action_mutation_audits_for_action(action_id)


def _actions() -> list[ActionObject]:
    return list_actions_cached()


def _actions_mutation_readiness() -> ActionMutationReadinessSummaryResponse:
    return mutation_readiness_actions()


def _action_detail(action_id: str) -> ActionObject:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    return action


def _validate_action_endpoint(
    action_id: str,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> ActionValidationResult:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = validate_action(action)
    clear_api_view_model_caches()
    return result


def _review_action_endpoint(
    action_id: str,
    request: ActionReviewRequest,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> ActionReviewResult:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    try:
        result = record_action_review(action, request)
    except TrustedLocalConfirmationError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": str(error)},
        ) from error
    clear_api_view_model_caches()
    return result


def _acknowledge_external_ads_execution(
    action_id: str,
    request: AdsExternalExecutionAcknowledgementRequest,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> AuditEvent:
    try:
        event = ads_external_execution.acknowledge_external_ads_execution(action_id, request)
    except ads_external_execution.AdsExternalAuditViolation as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    clear_api_view_model_caches()
    return event


def _record_external_ads_observation(
    action_id: str,
    request: AdsExternalObservationRequest,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> AuditEvent:
    try:
        event = ads_external_execution.record_external_ads_observation(action_id, request)
    except ads_external_execution.AdsExternalAuditViolation as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    clear_api_view_model_caches()
    return event


def _preview_action_endpoint(
    action_id: str,
    request: ActionPreviewRequest | None = None,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> ActionPreviewResult:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = preview_action(action, request)
    clear_api_view_model_caches()
    return result


def _confirm_action_endpoint(
    action_id: str,
    request: ActionConfirmRequest,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> ActionConfirmResult:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    try:
        result = confirm_action(action, request)
    except TrustedLocalConfirmationError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": str(error)},
        ) from error
    clear_api_view_model_caches()
    return result


def _impact_check_action_endpoint(
    action_id: str,
    request: ActionImpactCheckRequest,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> ActionImpactCheckResult:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    try:
        result = impact_check_action(action, request)
    except TrustedLocalConfirmationError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": str(error)},
        ) from error
    clear_api_view_model_caches()
    return result


def _apply_action_endpoint(
    action_id: str,
    request: ActionApplyRequest | None = None,
    *,
    clear_api_view_model_caches: Callable[[], None],
) -> ActionApplyResult:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    if (
        action.payload.get("action_type") == CURRENT_DISPOSITION_ACTION_TYPE
        and action.payload.get("local_authority_only") is True
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "current_disposition_approval_required",
                "status": "blocked",
                "action_id": action.id,
                "message": (
                    "Bieżącą disposition można zatwierdzić wyłącznie przez "
                    "kanoniczny endpoint current-disposition approval."
                ),
                "canonical_endpoint": (
                    f"/api/content/current-disposition-authorities/{action.id}/approve"
                ),
                "external_write_attempted": False,
            },
        )
    try:
        result = apply_action(action, request)
    except TrustedLocalConfirmationError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": str(error)},
        ) from error
    clear_api_view_model_caches()
    if not result.applied:
        raise HTTPException(status_code=409, detail=result.model_dump(mode="json"))
    return result


def _action_mutation_readiness(action_id: str) -> ActionMutationReadinessResponse:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    return mutation_readiness_action(action)


def _audit_events(action_id: str | None = None) -> list[AuditEvent]:
    return local_state_store().list_audit_events(action_id=action_id)


def _action_mutation_audits(
    action_id: str | None = None,
) -> list[ActionMutationAuditRecord]:
    return local_state_store().list_action_mutation_audits(action_id=action_id)


def _action_mutation_audits_for_action(
    action_id: str,
) -> list[ActionMutationAuditRecord]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    return local_state_store().list_action_mutation_audits(action_id=action_id)
