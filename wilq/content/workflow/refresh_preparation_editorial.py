"""Editorial preview composition for classified refresh preparation."""

from __future__ import annotations

from wilq.content.planning.dynamic_input import content_planning_input_summary
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorized,
    ContentRefreshPreparationBlocked,
    ContentRefreshPreparationBlocker,
    ContentRefreshPreparationPreview,
    ContentRefreshPreparationReadyToAuthorize,
)
from wilq.content.workflow.refresh_preparation_models import (
    RefreshClassificationContext,
    RefreshPreparationSnapshotLoader,
    RefreshPreparationStore,
)
from wilq.content.workflow.refresh_preparation_resolution import (
    blocker,
    rebuild_preparation,
)


def editorial_preview(
    *,
    store: RefreshPreparationStore,
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
    classified: RefreshClassificationContext,
    inventory_binding: ContentKindInventoryBinding,
) -> ContentRefreshPreparationPreview:
    prepared = rebuild_preparation(
        snapshot_loader=snapshot_loader,
        work_item_id=work_item_id,
        classification=classified,
        service_card_id=None,
        inventory_binding=inventory_binding,
    )
    if isinstance(prepared, ContentRefreshPreparationBlocked):
        return prepared
    receipt = prepared.content_kind_receipt
    if receipt is None or prepared.service_candidate is not None:
        return _blocked(work_item_id, classified, _corrupt_blocker())
    try:
        authorization = store.find_refresh_preparation_authorization(
            work_item_id=work_item_id,
            classification_run_digest=classified.binding.classification_run_digest,
            decision_set_digest=classified.binding.decision_set_digest,
            source_packet_row_digest=classified.binding.source_packet_row_digest,
            canonical_path=classified.binding.canonical_path,
            public_url=classified.binding.public_url,
            planning_input_digest=prepared.planning_input.planning_input_digest,
            service_card_id=None,
            content_kind="editorial",
        )
    except ValueError:
        return _blocked(work_item_id, classified, _corrupt_blocker())
    if authorization is None:
        return ContentRefreshPreparationReadyToAuthorize(
            status="ready_to_authorize",
            work_item_id=work_item_id,
            classification=classified.binding,
            content_kind="editorial",
            service_candidate=None,
            planning_input_digest=prepared.planning_input.planning_input_digest,
            input_summary=content_planning_input_summary(prepared.planning_input),
            blockers=prepared.informational_blockers,
            content_kind_receipt=receipt,
            safe_next_step=(
                "Potwierdź dokładne blockery klasyfikacji, aby zapisać jedną lokalną "
                "autoryzację editorial dla tego refresh i inputu."
            ),
        )
    return ContentRefreshPreparationAuthorized(
        status="authorized",
        work_item_id=work_item_id,
        classification=classified.binding,
        content_kind="editorial",
        service_candidate=None,
        planning_input_digest=prepared.planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(prepared.planning_input),
        blockers=prepared.informational_blockers,
        content_kind_receipt=receipt,
        authorization=authorization,
        safe_next_step=(
            "Autoryzacja editorial jest aktualna dla tego dokładnego inputu; można "
            "przygotować plan tylko z jej bindingiem."
        ),
    )


def _blocked(
    work_item_id: str,
    classified: RefreshClassificationContext,
    item: ContentRefreshPreparationBlocker,
) -> ContentRefreshPreparationBlocked:
    return ContentRefreshPreparationBlocked(
        status="blocked",
        work_item_id=work_item_id,
        classification=classified.binding,
        blockers=[item],
        safe_next_step=item.next_step,
    )


def _corrupt_blocker() -> ContentRefreshPreparationBlocker:
    return blocker(
        "refresh_preparation_authorization_stale",
        "Autoryzacja refresh nie jest czytelna",
        "Zapisany receipt autoryzacji ma uszkodzony payload albo niezgodne "
        "identyfikatory trwałe, więc nie może zostać użyty.",
        "Odśwież przygotowanie refresh i zapisz nową autoryzację dla bieżącego receipt.",
    )


__all__ = ["editorial_preview"]
