from __future__ import annotations

from typing import Any

from wilq.connectors.wordpress.client import (
    WordPressDraftVerificationError,
    WordPressDraftWriteError,
    create_wordpress_acf_draft,
    create_wordpress_draft_post,
)
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
)
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.policies import wordpress_draft_writes_enabled
from wilq.content.workflow.target.dev_draft_action import (
    CONTENT_DEV_DRAFT_ACTION_TYPE,
    ContentDevDraftWritePayload,
    build_content_dev_draft_write_payload,
)
from wilq.schemas import ActionObject

CONTENT_DEV_DRAFT_MUTATION_ADAPTER = "content_dev_draft_execution_boundary"


def execute_content_target_draft_action(
    action: ActionObject,
    *,
    binding: ContentDraftRevisionBinding | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Execute one separately reviewed, create-only draft action on dev.

    The ActionObject lifecycle owns preview, review, confirmation, impact and
    the explicit apply request.  This boundary owns only the exact payload and
    the dev-only WordPress call.
    """

    if action.payload.get("action_type") != CONTENT_DEV_DRAFT_ACTION_TYPE:
        return None, ["Ta akcja nie jest obsługiwaną akcją szkicu treści na dev."]
    if binding is None:
        return None, ["Akcja szkicu dev nie ma atomowo przejętej zatwierdzonej rewizji."]
    if not _dev_draft_writes_enabled():
        return _blocked_execution_result(
            action,
            binding,
            "Środowisko dev nie zezwala obecnie na utworzenie szkicu WordPress.",
            external_write_attempted=False,
            live_write_enabled=False,
        )
    try:
        payload = build_content_dev_draft_write_payload(action)
        draft_id = _create_wordpress_draft(payload, connector_id=action.connector)
    except WordPressDraftVerificationError as error:
        execution = ContentWordPressDraftExecutionResult(
            status="blocked",
            mode="live",
            boundary=ContentWordPressDraftExecutionBoundary(
                live_write_enabled=True,
                live_adapter_configured=True,
            ),
            revision_binding=binding,
            wordpress_post_id=error.post_id,
            external_write_attempted=True,
        )
        return {
            "adapter": CONTENT_DEV_DRAFT_MUTATION_ADAPTER,
            "connector": action.connector,
            "allowed_operation": "create_wordpress_draft",
            "endpoint": payload.endpoint,
            "post_status": payload.post_status,
            "created_draft_id": error.post_id,
            "external_write_attempted": True,
            "verification_status": "blocked",
            "verification_blocker_code": error.code,
            "expected_digest": error.expected_digest,
            "observed_digest": error.observed_digest,
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "redacted": True,
            "execution_result": execution.model_dump(mode="json"),
        }, [error.public_message]
    except ValueError as error:
        return _blocked_execution_result(
            action,
            binding,
            str(error),
            external_write_attempted=False,
        )
    except WordPressDraftWriteError as error:
        return _blocked_execution_result(
            action,
            binding,
            str(error),
            external_write_attempted=error.external_write_attempted,
        )
    execution = ContentWordPressDraftExecutionResult(
        status="created",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        revision_binding=binding,
        wordpress_post_id=draft_id,
        external_write_attempted=True,
    )
    return {
        "adapter": CONTENT_DEV_DRAFT_MUTATION_ADAPTER,
        "connector": action.connector,
        "allowed_operation": "create_wordpress_draft",
        "endpoint": payload.endpoint,
        "post_status": payload.post_status,
        "created_draft_id": draft_id,
        "external_write_attempted": True,
        "verification_status": "verified",
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "redacted": True,
        "execution_result": execution.model_dump(mode="json"),
    }, []


def _dev_draft_writes_enabled() -> bool:
    return wordpress_draft_writes_enabled()


def _create_wordpress_draft(
    payload: ContentDevDraftWritePayload,
    *,
    connector_id: str,
) -> str:
    if payload.authoring_mode == "acf_flexible_content":
        return create_wordpress_acf_draft(
            payload,
            connector_id=connector_id,
            action_apply_authorized=True,
        )
    return create_wordpress_draft_post(
        payload,
        connector_id=connector_id,
        endpoint=payload.endpoint,
    )


def _blocked_execution_result(
    action: ActionObject,
    binding: ContentDraftRevisionBinding,
    error: str,
    *,
    external_write_attempted: bool,
    live_write_enabled: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    execution = ContentWordPressDraftExecutionResult(
        status="blocked",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=live_write_enabled,
            live_adapter_configured=True,
        ),
        revision_binding=binding,
        external_write_attempted=external_write_attempted,
    )
    return {
        "adapter": CONTENT_DEV_DRAFT_MUTATION_ADAPTER,
        "connector": action.connector,
        "external_write_attempted": external_write_attempted,
        "verification_status": "blocked",
        "redacted": True,
        "execution_result": execution.model_dump(mode="json"),
    }, [error]


__all__ = [
    "CONTENT_DEV_DRAFT_MUTATION_ADAPTER",
    "execute_content_target_draft_action",
]
