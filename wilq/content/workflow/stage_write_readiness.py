from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

from wilq.connectors.wordpress.authoring import WordPressAuthoringProfile
from wilq.content.handoff.wordpress_execution import ContentWordPressDraftWriteAuthorization
from wilq.content.workflow.contracts import (
    ContentWordPressDraftWriteReadinessBlocker,
    ContentWordPressDraftWriteReadinessRequirement,
    ContentWordPressDraftWriteReadinessResponse,
)
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.schemas import AuditEvent
from wilq.storage.local_state import local_state_store


@dataclass(frozen=True)
class WriteReadinessCallbacks:
    writes_enabled: Callable[[], bool]
    authoring_profile: Callable[[str], WordPressAuthoringProfile]
    audit_readiness: Callable[
        [str],
        tuple[
            list[ContentWordPressDraftWriteReadinessRequirement],
            ContentWordPressDraftWriteAuthorization | None,
        ],
    ]
    audit_blockers: Callable[..., list[ContentWordPressDraftWriteReadinessBlocker]]
    authorization_status: Callable[
        ...,
        Literal["missing_audit_trace", "audit_actor_mismatch", "available"],
    ]
    next_step: Callable[..., str]


def wordpress_draft_write_authorization_verified(
    authorization: ContentWordPressDraftWriteAuthorization | None,
) -> bool:
    if authorization is None:
        return False
    events = {
        event.id: event
        for event in local_state_store().list_audit_events(action_id=authorization.action_id)
    }
    required = {
        authorization.preview_audit_id: "action_preview_generated",
        authorization.review_audit_id: "human_review_approved_for_prepare",
        authorization.confirmation_audit_id: "action_apply_confirmed",
    }
    if authorization.impact_audit_id:
        required[authorization.impact_audit_id] = "action_impact_check_completed"
    if authorization.apply_audit_id:
        required[authorization.apply_audit_id] = "apply_succeeded"
    for event_id, expected_type in required.items():
        event = events.get(event_id)
        if event is None or event.action_id != authorization.action_id:
            return False
        if event.event_type != expected_type:
            return False
        if authorization.wordpress_draft_binding is not None and (
            _wordpress_draft_binding_from_event(event)
            != authorization.wordpress_draft_binding
        ):
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
        return bool(
            authorization.wordpress_draft_binding is None
            or authorization.impact_audit_id is not None
        )
    return bool(
        apply_event is not None
        and apply_event.actor == confirmed_by
        and (
            authorization.wordpress_draft_binding is None
            or _wordpress_draft_binding_from_event(apply_event)
            == authorization.wordpress_draft_binding
        )
    )


def wordpress_draft_binding_from_audit_event(
    event: AuditEvent,
) -> ContentDraftRevisionBinding | None:
    return _wordpress_draft_binding_from_event(event)


def _wordpress_draft_binding_from_event(
    event: AuditEvent,
) -> ContentDraftRevisionBinding | None:
    raw_binding = event.details.get("wordpress_draft_binding")
    if raw_binding is None:
        return None
    try:
        return ContentDraftRevisionBinding.model_validate(raw_binding)
    except (TypeError, ValueError):
        return None


def wordpress_draft_write_audit_readiness(
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


def _latest_exact_event(events: list[AuditEvent], event_type: str) -> AuditEvent | None:
    return next((event for event in events if event.event_type == event_type), None)


def _latest_prefix_event(
    events: list[AuditEvent], event_type_prefix: str
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


def wordpress_draft_write_audit_blockers(
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


def wordpress_draft_write_authorization_status(
    requirements: list[ContentWordPressDraftWriteReadinessRequirement],
    authorization: ContentWordPressDraftWriteAuthorization | None,
) -> Literal["missing_audit_trace", "audit_actor_mismatch", "available"]:
    if any(not requirement.satisfied for requirement in requirements):
        return "missing_audit_trace"
    if authorization is None:
        return "audit_actor_mismatch"
    return "available"


def build_content_wordpress_draft_write_readiness_response(
    *,
    callbacks: WriteReadinessCallbacks,
    action_id: str = "act_prepare_wordpress_draft_handoff",
    connector_id: str = "wordpress_ekologus",
) -> ContentWordPressDraftWriteReadinessResponse:
    live_write_enabled = callbacks.writes_enabled()
    profile = callbacks.authoring_profile(connector_id)
    rest_adapter_configured = profile.rest_api.status == "configured"
    requirements, authorization = callbacks.audit_readiness(action_id)
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
    blockers.extend(callbacks.audit_blockers(requirements, authorization))
    missing_audit_event_types = [
        requirement.event_type for requirement in requirements if not requirement.satisfied
    ]
    authorization_status = cast(
        Literal[
            "missing_audit_trace",
            "audit_actor_mismatch",
            "available",
            "blocked_outside_action_apply",
        ],
        callbacks.authorization_status(requirements, authorization),
    )
    if authorization is not None:
        authorization_status = "blocked_outside_action_apply"
    return ContentWordPressDraftWriteReadinessResponse(
        connector=connector_id,
        action_id=action_id,
        ready=False,
        live_write_enabled_by_env=live_write_enabled,
        rest_adapter_configured=rest_adapter_configured,
        required_audit_events=requirements,
        missing_audit_event_types=missing_audit_event_types,
        write_authorization_status=authorization_status,
        suggested_write_authorization=None,
        blockers=blockers,
        operator_next_step=callbacks.next_step(False, blockers),
        evidence_ids=profile.evidence_ids,
        source_connectors=profile.source_connectors or [connector_id],
    )
