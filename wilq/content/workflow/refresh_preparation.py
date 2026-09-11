"""One deep interface for classified refresh preparation and authorization."""

from __future__ import annotations

from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.decisions.inventory_binding import (
    content_kind_inventory_binding_for_work_item,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorizationRequest,
    ContentRefreshPreparationAuthorizationResponse,
    ContentRefreshPreparationPreview,
)
from wilq.content.workflow.refresh_preparation_models import (
    ContentKindInventoryLoader,
    RefreshPreparationRuntimeAuthorized,
    RefreshPreparationRuntimeBlocked,
    RefreshPreparationRuntimeResolution,
    RefreshPreparationSnapshotLoader,
    RefreshPreparationStore,
    RefreshPreparationUnclassified,
)
from wilq.content.workflow.refresh_preparation_operations import (
    authorize,
    initial_draft_block_response,
    planning_block_response,
    preview,
    resolve_initial_draft,
    resolve_planning,
)


class ContentRefreshPreparationAuthority:
    """Hide classification, source rebuild, authorization, and runtime rechecks."""

    def __init__(
        self,
        *,
        store: RefreshPreparationStore,
        snapshot_loader: RefreshPreparationSnapshotLoader,
        proposal_store: ContentPlanningProposalStore,
        content_kind_inventory_loader: ContentKindInventoryLoader = (
            content_kind_inventory_binding_for_work_item
        ),
    ) -> None:
        self._store = store
        self._snapshot_loader = snapshot_loader
        self._proposal_store = proposal_store
        self._content_kind_inventory_loader = content_kind_inventory_loader

    def preview(
        self,
        work_item_id: str,
        *,
        service_card_id: str | None,
    ) -> ContentRefreshPreparationPreview:
        return preview(
            store=self._store,
            snapshot_loader=self._snapshot_loader,
            work_item_id=work_item_id,
            service_card_id=service_card_id,
            content_kind_inventory_loader=self._content_kind_inventory_loader,
        )

    def authorize(
        self,
        work_item_id: str,
        request: ContentRefreshPreparationAuthorizationRequest,
    ) -> ContentRefreshPreparationAuthorizationResponse:
        return authorize(
            store=self._store,
            snapshot_loader=self._snapshot_loader,
            work_item_id=work_item_id,
            request=request,
            content_kind_inventory_loader=self._content_kind_inventory_loader,
        )

    def resolve_planning(
        self,
        work_item_id: str,
        request: ContentPlanningProposalRequest,
    ) -> RefreshPreparationRuntimeResolution:
        return resolve_planning(
            store=self._store,
            snapshot_loader=self._snapshot_loader,
            work_item_id=work_item_id,
            request=request,
            content_kind_inventory_loader=self._content_kind_inventory_loader,
        )

    def resolve_initial_draft(
        self,
        work_item_id: str,
        request: ContentInitialDraftRequest,
    ) -> RefreshPreparationRuntimeResolution:
        return resolve_initial_draft(
            store=self._store,
            snapshot_loader=self._snapshot_loader,
            proposal_store=self._proposal_store,
            work_item_id=work_item_id,
            request=request,
            content_kind_inventory_loader=self._content_kind_inventory_loader,
        )

    def planning_block_response(
        self,
        resolution: RefreshPreparationRuntimeResolution,
        request: ContentPlanningProposalRequest,
    ) -> ContentPlanningProposalResponse | None:
        return planning_block_response(resolution, request)

    def initial_draft_block_response(
        self,
        resolution: RefreshPreparationRuntimeResolution,
        request: ContentInitialDraftRequest,
    ) -> ContentInitialDraftResponse | None:
        return initial_draft_block_response(resolution, request)


__all__ = [
    "ContentRefreshPreparationAuthority",
    "RefreshPreparationRuntimeAuthorized",
    "RefreshPreparationRuntimeBlocked",
    "RefreshPreparationRuntimeResolution",
    "RefreshPreparationSnapshotLoader",
    "RefreshPreparationUnclassified",
]
