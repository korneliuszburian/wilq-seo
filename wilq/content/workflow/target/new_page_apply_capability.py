"""Exact request-to-ActionObject binding for a future new-page dev draft."""

from __future__ import annotations

from dataclasses import dataclass

from wilq.actions.action_chain import ActionChain, revision_bound_action_chain
from wilq.content.operator_copy import build_blocker
from wilq.content.workflow.target.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
from wilq.content.workflow.target.new_page_revision_binding import ContentNewPageDraftBinding
from wilq.schemas import ActionApplyRequest, ActionObject, ActionWordPressDraftApplyBlocker


@dataclass(frozen=True)
class NewPageApplyCapability:
    binding: ContentNewPageDraftBinding
    action_chain: ActionChain


def new_page_apply_binding(
    action: ActionObject,
    request: ActionApplyRequest | None,
) -> tuple[NewPageApplyCapability | None, list[ActionWordPressDraftApplyBlocker]]:
    """Return a request-bound capability with a verified ActionObject chain."""
    if action.payload.get("action_type") != CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE:
        return None, []
    if request is None or request.new_page_draft is None:
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="new_page_revision_binding_required",
                label="Brakuje exact bindingu nowej strony",
                reason="Apply wymaga tożsamości briefu, foundation, usługi i zatwierdzonej rewizji.",  # noqa: E501
                next_step="Odśwież akcję i użyj exact bindingu zwróconego przez WILQ.",
            )
        ]
    persisted = action.payload.get("new_page_draft_binding")
    if not isinstance(persisted, dict):
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="new_page_action_binding_missing",
                label="Akcja nie zawiera zapisanego bindingu",
                reason="Nie można odtworzyć exact identity ActionObjectu przed zapisem.",
                next_step="Odśwież akcję i użyj exact bindingu zwróconego przez WILQ.",
            )
        ]
    try:
        expected = ContentNewPageDraftBinding.model_validate(persisted)
    except ValueError:
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="new_page_action_binding_invalid",
                label="Zapisany binding akcji jest nieprawidłowy",
                reason="Lokalny ActionObject nie spełnia kontraktu exact lineage.",
                next_step="Odśwież akcję i użyj exact bindingu zwróconego przez WILQ.",
            )
        ]
    if request.new_page_draft != expected:
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="new_page_revision_binding_mismatch",
                label="Binding requestu nie pasuje do akcji",
                reason="Klient wskazał inną nową stronę, rewizję albo profil authoringu.",
                next_step="Odśwież akcję i użyj exact bindingu zwróconego przez WILQ.",
            )
        ]
    chain, blockers = revision_bound_action_chain(
        action.audit_events,
        confirmed_by=request.confirmed_by or "",
    )
    if chain is None:
        return None, blockers
    return NewPageApplyCapability(binding=expected, action_chain=chain), []
