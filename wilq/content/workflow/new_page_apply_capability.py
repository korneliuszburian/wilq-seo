"""Exact request-to-ActionObject binding for a future new-page dev draft."""

from __future__ import annotations

from wilq.content.workflow.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
from wilq.content.workflow.new_page_revision_binding import ContentNewPageDraftBinding
from wilq.schemas import ActionApplyRequest, ActionObject, ActionWordPressDraftApplyBlocker


def new_page_apply_binding(
    action: ActionObject,
    request: ActionApplyRequest | None,
) -> tuple[ContentNewPageDraftBinding | None, list[ActionWordPressDraftApplyBlocker]]:
    """Return only a client request that matches the persisted action lineage."""
    if action.payload.get("action_type") != CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE:
        return None, []
    if request is None or request.new_page_draft is None:
        return None, [_blocker("new_page_revision_binding_required")]
    persisted = action.payload.get("new_page_draft_binding")
    if not isinstance(persisted, dict):
        return None, [_blocker("new_page_action_binding_missing")]
    try:
        expected = ContentNewPageDraftBinding.model_validate(persisted)
    except ValueError:
        return None, [_blocker("new_page_action_binding_invalid")]
    if request.new_page_draft != expected:
        return None, [_blocker("new_page_revision_binding_mismatch")]
    return expected, []


def _blocker(code: str) -> ActionWordPressDraftApplyBlocker:
    messages = {
        "new_page_revision_binding_required": (
            "Brakuje exact bindingu nowej strony",
            "Apply wymaga tożsamości briefu, foundation, usługi i zatwierdzonej rewizji.",
        ),
        "new_page_action_binding_missing": (
            "Akcja nie zawiera zapisanego bindingu",
            "Nie można odtworzyć exact identity ActionObjectu przed zapisem.",
        ),
        "new_page_action_binding_invalid": (
            "Zapisany binding akcji jest nieprawidłowy",
            "Lokalny ActionObject nie spełnia kontraktu exact lineage.",
        ),
        "new_page_revision_binding_mismatch": (
            "Binding requestu nie pasuje do akcji",
            "Klient wskazał inną nową stronę, rewizję albo profil authoringu.",
        ),
    }
    label, reason = messages[code]
    return ActionWordPressDraftApplyBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step="Odśwież akcję i użyj exact bindingu zwróconego przez WILQ.",
    )
