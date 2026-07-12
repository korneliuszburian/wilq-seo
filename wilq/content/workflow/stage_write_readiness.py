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
