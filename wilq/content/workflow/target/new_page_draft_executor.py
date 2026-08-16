"""Exact new-page ActionObject executor behind the later apply lifecycle."""

from __future__ import annotations

from typing import Any

from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.target.new_page_apply_capability import NewPageApplyCapability
from wilq.content.workflow.target.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
from wilq.content.workflow.target.new_page_draft_execution import create_new_page_dev_draft
from wilq.content.workflow.target.new_page_draft_payload import (
    build_new_page_dev_draft_write_payload,
)
from wilq.credentials.runtime import variable_value
from wilq.schemas import ActionObject

CONTENT_NEW_PAGE_DRAFT_MUTATION_ADAPTER = "content_new_page_draft_execution_boundary"


def execute_new_page_draft_action(
    action: ActionObject,
    capability: NewPageApplyCapability | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Execute one exact dev draft only after canonical lifecycle authorization."""
    if action.payload.get("action_type") != CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE:
        return None, ["Ta akcja nie jest obsługiwaną akcją nowego szkicu na dev."]
    if not _dev_draft_writes_enabled():
        return None, ["Środowisko dev nie zezwala obecnie na utworzenie szkicu WordPress."]
    if capability is None:
        return None, ["Utworzenie szkicu wymaga zweryfikowanego łańcucha ActionObject."]
    binding = capability.binding
    revision = next(
        (
            item
            for item in content_workflow_store().list_draft_revisions(binding.work_item_id)
            if item.revision_id == binding.revision_id
            and item.content_digest == binding.revision_digest
        ),
        None,
    )
    if revision is None:
        return None, ["Dokładna rewizja nowej strony nie jest już dostępna."]
    try:
        payload = build_new_page_dev_draft_write_payload(revision, binding)
        draft = create_new_page_dev_draft(payload, action_apply_authorized=capability is not None)
    except ValueError as error:
        return None, [str(error)]
    return {
        "adapter": CONTENT_NEW_PAGE_DRAFT_MUTATION_ADAPTER,
        "connector": action.connector,
        "allowed_operation": "create_wordpress_draft",
        "endpoint": payload.endpoint,
        "post_status": payload.post_status,
        "created_draft_id": draft.wordpress_post_id,
        "wordpress_post_id": draft.wordpress_post_id,
        "status": draft.status,
        "link": draft.link,
        "edit_link": draft.edit_link,
        "external_write_attempted": True,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "redacted": True,
    }, []


def _dev_draft_writes_enabled() -> bool:
    return (variable_value("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
