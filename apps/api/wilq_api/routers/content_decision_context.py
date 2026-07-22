from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.decision_context import (
    ContentDecisionContext,
    build_content_decision_context,
)


def content_work_item_decision_context(
    work_item_id: str,
) -> ContentDecisionContext:
    context = build_content_decision_context(work_item_id)
    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Content work item is not available for decision context.",
        )
    return context


def register_content_decision_context_route(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/work-items/{work_item_id}/decision-context",
        content_work_item_decision_context,
        methods=["GET"],
        response_model=ContentDecisionContext,
    )


__all__ = [
    "content_work_item_decision_context",
    "register_content_decision_context_route",
]
