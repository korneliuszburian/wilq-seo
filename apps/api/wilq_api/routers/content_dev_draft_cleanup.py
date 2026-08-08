from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.actions.service import clear_action_list_cache
from wilq.content.workflow.target.dev_draft_discard_action import (
    ContentDevDraftDiscardActionCommand,
    create_content_dev_draft_discard_action,
    persist_content_dev_draft_discard_action,
)
from wilq.schemas import ActionObject


def register_content_dev_draft_cleanup_route(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/dev-drafts/discard-action",
        create_content_dev_draft_discard_action_endpoint,
        methods=["POST"],
        response_model=ActionObject,
    )


def create_content_dev_draft_discard_action_endpoint(
    command: ContentDevDraftDiscardActionCommand,
) -> ActionObject:
    try:
        action = create_content_dev_draft_discard_action(command)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    persisted = persist_content_dev_draft_discard_action(action)
    clear_action_list_cache()
    return persisted


__all__ = ["register_content_dev_draft_cleanup_route"]
