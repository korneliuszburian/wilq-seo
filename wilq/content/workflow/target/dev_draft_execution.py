from __future__ import annotations

from typing import Any

from wilq.connectors.wordpress.client import (
    WordPressDraftCreationProof,
    WordPressDraftVerificationError,
    WordPressDraftWriteError,
    _wordpress_draft_value_digest,
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
        digest_fields = _verification_digest_fields(error)
        expected_fields = _creation_digest_fields(payload, "")
        for key in ("expected_content_digest", "expected_acf_digest", "expected_title_digest"):
            digest_fields[key] = digest_fields.get(key) or expected_fields[key]
        execution = ContentWordPressDraftExecutionResult(
            status="blocked",
            mode="live",
            boundary=ContentWordPressDraftExecutionBoundary(
                live_write_enabled=True,
                live_adapter_configured=True,
            ),
            revision_binding=binding,
            wordpress_post_id=error.post_id,
            endpoint=payload.endpoint,
            external_write_attempted=True,
            expected_content_digest=digest_fields.get("expected_content_digest"),
            observed_content_digest=digest_fields.get("observed_content_digest"),
            expected_acf_digest=digest_fields.get("expected_acf_digest"),
            observed_acf_digest=digest_fields.get("observed_acf_digest"),
            expected_title_digest=digest_fields.get("expected_title_digest"),
            observed_title_digest=digest_fields.get("observed_title_digest"),
            verification_expected_digest=digest_fields.get("verification_expected_digest"),
            verification_observed_digest=digest_fields.get("verification_observed_digest"),
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
    digest_fields = _creation_digest_fields(payload, draft_id)
    execution = ContentWordPressDraftExecutionResult(
        status="created",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        revision_binding=binding,
        wordpress_post_id=draft_id,
        endpoint=payload.endpoint,
        external_write_attempted=True,
        expected_content_digest=digest_fields.get("expected_content_digest"),
        observed_content_digest=digest_fields.get("observed_content_digest"),
        expected_acf_digest=digest_fields.get("expected_acf_digest"),
        observed_acf_digest=digest_fields.get("observed_acf_digest"),
        expected_title_digest=digest_fields.get("expected_title_digest"),
        observed_title_digest=digest_fields.get("observed_title_digest"),
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


def _creation_digest_fields(
    payload: ContentDevDraftWritePayload,
    draft_id: str,
) -> dict[str, str | None]:
    fields: dict[str, str | None] = {
        "expected_title_digest": _wordpress_draft_value_digest(payload.title),
        "expected_content_digest": (
            _wordpress_draft_value_digest(payload.content_html)
            if payload.content_html is not None
            else None
        ),
        "expected_acf_digest": (
            _wordpress_draft_value_digest(payload.acf) if payload.acf is not None else None
        ),
    }
    if isinstance(draft_id, WordPressDraftCreationProof):
        fields.update(
            {
                "expected_content_digest": draft_id.expected_content_digest
                or fields["expected_content_digest"],
                "observed_content_digest": draft_id.observed_content_digest,
                "expected_acf_digest": draft_id.expected_acf_digest
                or fields["expected_acf_digest"],
                "observed_acf_digest": draft_id.observed_acf_digest,
                "expected_title_digest": draft_id.expected_title_digest
                or fields["expected_title_digest"],
                "observed_title_digest": draft_id.observed_title_digest,
            }
        )
    return fields


def _verification_digest_fields(
    error: WordPressDraftVerificationError,
) -> dict[str, str | None]:
    code = error.code
    fields: dict[str, str | None] = {
        "verification_expected_digest": error.expected_digest,
        "verification_observed_digest": error.observed_digest,
    }
    if "acf" in code:
        fields.update(
            {
                "expected_acf_digest": error.expected_digest,
                "observed_acf_digest": error.observed_digest,
            }
        )
    elif "title" in code:
        fields.update(
            {
                "expected_title_digest": error.expected_digest,
                "observed_title_digest": error.observed_digest,
            }
        )
    elif "content" in code:
        fields.update(
            {
                "expected_content_digest": error.expected_digest,
                "observed_content_digest": error.observed_digest,
            }
        )
    return fields


__all__ = [
    "CONTENT_DEV_DRAFT_MUTATION_ADAPTER",
    "execute_content_target_draft_action",
]
