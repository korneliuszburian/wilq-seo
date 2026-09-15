"""Initial-draft binding helpers for classified refresh preparation."""

from __future__ import annotations

from dataclasses import replace

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftRequest
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    build_content_planning_workspace,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBlocker,
    refresh_preparation_bindings_match_authority,
)
from wilq.content.workflow.refresh_preparation_models import (
    RefreshPreparationRuntimeAuthorized,
    RefreshPreparationRuntimeBlocked,
    RefreshPreparationRuntimeResolution,
    RefreshPreparationStore,
)
from wilq.content.workflow.refresh_preparation_resolution import blocker


def bind_initial_proposal(
    resolved: RefreshPreparationRuntimeResolution,
    proposal: ContentPlanningProposal,
    request: ContentInitialDraftRequest,
) -> RefreshPreparationRuntimeResolution:
    if not isinstance(resolved, RefreshPreparationRuntimeAuthorized):
        return resolved
    if (
        proposal.refresh_preparation_binding is None
        or not refresh_preparation_bindings_match_authority(
            proposal.refresh_preparation_binding, resolved.binding
        )
    ):
        return _blocked_proposal(resolved)
    if (
        proposal.research_packet_id is None
        and resolved.planning_input.planning_input_digest
        != request.expected_planning_input_digest
    ):
        return RefreshPreparationRuntimeBlocked(
            resolved.work_item_id,
            blocker(
                "refresh_preparation_authorization_input_mismatch",
                "Wejście planu zmieniło się po autoryzacji",
                "Żądanie pełnego tekstu wskazuje inny planning_input_digest niż bieżący "
                "autoryzowany snapshot.",
                "Odśwież plan i uruchom draft dla bieżącego exact inputu.",
            ),
        )
    return replace(
        resolved,
        snapshot=resolved.snapshot.model_copy(
            update={"planning_workspace": build_content_planning_workspace(proposal, [])}
        ),
    )


def authorized_planning_input_digest(
    store: RefreshPreparationStore,
    authorization_id: str | None,
) -> str | None:
    if authorization_id is None:
        return None
    try:
        authorization = store.load_refresh_preparation_authorization(authorization_id)
    except ValueError:
        return None
    return None if authorization is None else authorization.planning_input_digest


def proposal_binding_blocker() -> ContentRefreshPreparationBlocker:
    return blocker(
        "refresh_preparation_proposal_binding_mismatch",
        "Plan nie jest związany z autoryzacją refresh",
        "Pełny tekst wymaga dokładnego wygenerowanego planu z tym samym authorization ID "
        "i digestem.",
        "Odśwież plan i użyj wersji wygenerowanej dla bieżącej autoryzacji refresh.",
    )


def _blocked_proposal(
    resolved: RefreshPreparationRuntimeAuthorized,
) -> RefreshPreparationRuntimeResolution:
    return RefreshPreparationRuntimeBlocked(resolved.work_item_id, proposal_binding_blocker())


__all__ = [
    "authorized_planning_input_digest",
    "bind_initial_proposal",
    "proposal_binding_blocker",
]
