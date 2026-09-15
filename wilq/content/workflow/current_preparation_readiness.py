"""Resolve exact current receipts before refresh authorization."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from wilq.content.workflow.current_preparation_readiness_contracts import (
    ContentCurrentPreparationReadiness,
    ContentCurrentPreparationReadinessBlocked,
    ContentCurrentPreparationReadyForRefreshAuthorization,
    CurrentPreparationReadinessStore,
)
from wilq.content.workflow.current_preparation_readiness_support import (
    blocker_copy,
    context,
    identity_id,
    is_safe_blocked_row,
    latest_run,
    latest_source_pack,
    load_identity,
    registered_inventory_is_pending,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
    project_content_production_classification,
)
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    build_content_delivery_identity_current_projection,
)
from wilq.content.workflow.research_packet_preparation import (
    ResearchPacketPreparationStore,
    current_source_pack_blocker,
)


def resolve_current_preparation_readiness(
    store: CurrentPreparationReadinessStore,
    work_item_id: str,
    *,
    run: ContentProductionClassificationRun | None = None,
    row: ContentProductionClassificationRow | None = None,
) -> ContentCurrentPreparationReadiness:
    """Join current receipts; never mutate or relabel classification."""

    current_run = run or latest_run(store)
    if current_run is None:
        return _blocked(work_item_id, "classification_current_missing")
    current_row = row or current_run.for_work_item(work_item_id)
    current_context = context(current_run, current_row)
    if current_row is None:
        return _blocked(work_item_id, "classification_item_missing", **current_context)
    if current_row.current_work_item_id != work_item_id:
        return _blocked(work_item_id, "current_work_item_mismatch", **current_context)
    if not is_safe_blocked_row(current_row):
        return _blocked(work_item_id, "current_content_binding_missing", **current_context)
    if not registered_inventory_is_pending(current_row):
        return _blocked(
            work_item_id,
            "registered_current_inventory_required",
            **current_context,
        )
    if current_run.freshness.state != "fresh" or current_run.freshness.requires_refresh:
        return _blocked(work_item_id, "classification_stale", **current_context)

    binding_id = identity_id(current_run, current_row)
    identity = load_identity(store, binding_id)
    if identity is None:
        return _blocked(
            work_item_id,
            "identity_binding_missing",
            identity_binding_id=binding_id,
            **current_context,
        )
    identity_fields = {
        "identity_binding_id": identity.binding_id,
        "identity_binding_digest": identity.binding_digest,
    }
    if identity.final_disposition != "keep":
        return _blocked(work_item_id, "disposition_not_keep", **identity_fields, **current_context)
    try:
        projection = project_content_production_classification(current_run, current_row)
        current_identity = build_content_delivery_identity_current_projection(
            identity,
            ContentDeliveryClassificationLookup(row_status="exact", run=projection),
            assessed_at=datetime.now(UTC),
        )
    except (TypeError, ValueError):
        return _blocked(
            work_item_id,
            "identity_binding_not_exact_current",
            **identity_fields,
            **current_context,
        )
    if current_identity.current_status != "exact_current":
        return _blocked(
            work_item_id,
            "identity_binding_not_exact_current",
            safe_next_step=current_identity.current_safe_next_step,
            **identity_fields,
            **current_context,
        )

    source_pack = latest_source_pack(store, work_item_id)
    if source_pack is None:
        return _blocked(
            work_item_id,
            "source_pack_binding_missing",
            **identity_fields,
            **current_context,
        )
    pack_fields = {
        "source_pack_binding_id": source_pack.binding_id,
        "source_pack_binding_digest": source_pack.binding_digest,
    }
    if (
        source_pack.current_work_item_id != work_item_id
        or source_pack.identity_binding_id != identity.binding_id
        or source_pack.identity_binding_digest != identity.binding_digest
    ):
        return _blocked(
            work_item_id,
            "source_pack_identity_mismatch",
            **pack_fields,
            **identity_fields,
            **current_context,
        )
    source_blocker = current_source_pack_blocker(
        store=cast(ResearchPacketPreparationStore, store),
        source_pack=source_pack,
        identity=identity,
    )
    if source_blocker is not None:
        return _blocked(
            work_item_id,
            source_blocker.reason,
            reason=(
                "Najnowszy source-pack nie jest exact current dla authority, registry albo context."
            ),
            safe_next_step=source_blocker.next_step_pl,
            **pack_fields,
            **identity_fields,
            **current_context,
        )
    return ContentCurrentPreparationReadyForRefreshAuthorization(
        status="ready_for_refresh_authorization",
        work_item_id=work_item_id,
        **cast(dict[str, str], current_context),
        **identity_fields,
        **pack_fields,
    )


def _blocked(
    work_item_id: str,
    code: str,
    *,
    reason: str | None = None,
    safe_next_step: str | None = None,
    **fields: str | None,
) -> ContentCurrentPreparationReadinessBlocked:
    default_reason, default_next = blocker_copy(code)
    return ContentCurrentPreparationReadinessBlocked(
        status="blocked",
        work_item_id=work_item_id,
        code=code,
        reason_pl=reason or default_reason,
        safe_next_step_pl=safe_next_step or default_next,
        **fields,
    )


__all__ = [
    "ContentCurrentPreparationReadiness",
    "ContentCurrentPreparationReadinessBlocked",
    "ContentCurrentPreparationReadyForRefreshAuthorization",
    "CurrentPreparationReadinessStore",
    "resolve_current_preparation_readiness",
]
