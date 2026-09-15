"""Read-only current projection and revalidation for research packets."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Literal

from wilq.content.planning.dynamic_input import build_content_planning_input
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.research_packet import (
    ContentResearchPacket,
    ContentResearchPacketBlocker,
    ContentResearchPacketCurrentProjection,
    ResearchPacketBlockerReason,
    ResearchPacketBlockerSeam,
)
from wilq.content.workflow.research_packet_preparation import (
    ResearchPacketPreparationStore,
    current_research_packet_blocker,
)
from wilq.content.workflow.source_pack_binding import ContentSourcePackBinding
from wilq.schemas.core import utc_now

CurrentSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def revalidate_content_research_packet(
    *,
    store: ResearchPacketPreparationStore,
    packet: ContentResearchPacket,
    snapshot_loader: CurrentSnapshotLoader,
    now: datetime | None = None,
) -> ContentResearchPacketCurrentProjection:
    """Assess a packet against current authority without persisting anything."""

    assessed_at = (now or utc_now()).astimezone(UTC)
    source_pack = store.load_content_source_pack_binding(packet.source_pack_binding_id)
    latest_source_pack = _latest_source_pack(store, packet.current_work_item_id)
    identity = store.load_content_delivery_identity(packet.identity_binding_id)
    current_fields = {
        "current_source_pack_binding_id": (
            None if latest_source_pack is None else latest_source_pack.binding_id
        ),
        "current_source_pack_binding_digest": (
            None if latest_source_pack is None else latest_source_pack.binding_digest
        ),
        "current_identity_binding_id": None if identity is None else identity.binding_id,
        "current_identity_binding_digest": (
            None if identity is None else identity.binding_digest
        ),
    }

    if packet.status != "exact_current":
        blocker = packet.blocker or _blocker(
            "source_pack_binding",
            "source_pack_binding_blocked",
            packet.evidence_ids,
            "Usuń typed blocker packetu przed użyciem bieżącego planu.",
        )
        return _projection(packet, "blocked", blocker, assessed_at, current_fields)

    if packet.context_receipt is None:
        blocker = _blocker(
            "identity_binding",
            "context_receipt_missing",
            packet.evidence_ids,
            "Historyczny packet nie ma exact context receipt; przygotuj nowy packet.",
        )
        return _projection(packet, "legacy", blocker, assessed_at, current_fields)

    if source_pack is None:
        blocker = _blocker(
            "source_pack_binding",
            "source_pack_binding_missing",
            packet.evidence_ids,
            "Odczytaj bieżący source-pack binding przed użyciem packetu.",
        )
        return _projection(packet, "blocked", blocker, assessed_at, current_fields)
    if identity is None:
        blocker = _blocker(
            "identity_binding",
            "identity_binding_missing",
            packet.evidence_ids,
            "Odczytaj bieżący identity binding przed użyciem packetu.",
        )
        return _projection(packet, "blocked", blocker, assessed_at, current_fields)

    try:
        snapshot = snapshot_loader(packet.current_work_item_id)
        service_card_id = packet.context_receipt.service_card_id
        if service_card_id is None and packet.content_kind == "service":
            service_card_id = getattr(snapshot.service_profile_context, "service_card_id", None)
        planning_result = build_content_planning_input(
            snapshot,
            service_card_id=service_card_id,
        )
    except Exception:
        blocker = _blocker(
            "identity_binding",
            "context_receipt_mismatch",
            packet.evidence_ids,
            "Nie można odtworzyć bieżącego typed context receipt; odśwież packet.",
        )
        return _projection(packet, "blocked", blocker, assessed_at, current_fields)

    planning_input = planning_result.planning_input
    if planning_input is None:
        blocker = _blocker(
            "identity_binding",
            "context_receipt_mismatch",
            packet.evidence_ids,
            "Bieżący typed kontekst nie jest kompletny; odśwież packet.",
        )
        return _projection(packet, "blocked", blocker, assessed_at, current_fields)

    current_blocker = current_research_packet_blocker(
        store=store,
        packet=packet,
        snapshot=snapshot,
        planning_input=planning_input,
    )
    if current_blocker is not None:
        return _projection(packet, "blocked", current_blocker, assessed_at, current_fields)
    return _projection(packet, "current", None, assessed_at, current_fields)


def _latest_source_pack(
    store: ResearchPacketPreparationStore,
    work_item_id: str,
) -> ContentSourcePackBinding | None:
    packs = store.list_content_source_pack_bindings(current_work_item_id=work_item_id)
    return max(packs, key=lambda item: (item.recorded_at, item.binding_id)) if packs else None


def _projection(
    packet: ContentResearchPacket,
    status: Literal["current", "blocked", "legacy"],
    blocker: ContentResearchPacketBlocker | None,
    assessed_at: datetime,
    current_fields: Mapping[str, str | None],
) -> ContentResearchPacketCurrentProjection:
    return ContentResearchPacketCurrentProjection(
        status=status,
        packet_id=packet.packet_id,
        packet_digest=packet.packet_digest,
        current_work_item_id=packet.current_work_item_id,
        current_source_pack_binding_id=current_fields["current_source_pack_binding_id"],
        current_source_pack_binding_digest=current_fields["current_source_pack_binding_digest"],
        current_identity_binding_id=current_fields["current_identity_binding_id"],
        current_identity_binding_digest=current_fields["current_identity_binding_digest"],
        blocker=blocker,
        revalidated_at=assessed_at,
    )


def _blocker(
    seam: ResearchPacketBlockerSeam,
    reason: ResearchPacketBlockerReason,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentResearchPacketBlocker:
    return ContentResearchPacketBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        next_step_pl=next_step,
    )


__all__ = ["CurrentSnapshotLoader", "revalidate_content_research_packet"]
