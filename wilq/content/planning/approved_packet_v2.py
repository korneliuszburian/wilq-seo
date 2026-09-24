"""Exact read-only planning view of a reviewed current v2 research packet."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.current_page_evidence import read_current_page_evidence_current
from wilq.content.workflow.current_page_identity_v2 import resolve_current_page_identity_v2
from wilq.content.workflow.research_packet_v2_preview import (
    ResearchPacketV2Preview,
    ResearchPacketV2PreviewBlocker,
    build_research_packet_v2_preview,
)
from wilq.content.workflow.source_pack_v2 import build_source_pack_v2_preview
from wilq.content.workflow.store.store import ContentWorkflowStore

CurrentPreviewLoader = Callable[[str, ContentPlanningInput], ResearchPacketV2Preview]


@dataclass(frozen=True, slots=True)
class ApprovedPacketV2PlanningView:
    packet_id: str
    packet_digest: str
    current_work_item_id: str
    approved_source_fact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    preview: ResearchPacketV2Preview


def resolve_approved_packet_v2_for_planning(
    *,
    store: ContentWorkflowStore,
    packet_id: str,
    expected_digest: str,
    planning_input: ContentPlanningInput,
    current_preview_loader: CurrentPreviewLoader | None = None,
) -> ApprovedPacketV2PlanningView | ResearchPacketV2PreviewBlocker:
    try:
        receipt = store.load_research_packet_v2_approval_receipt(packet_id)
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        return _blocked(
            "research_packet_v2_receipt_unavailable", (), "Odczytaj ponownie receipt pakietu v2."
        )
    if receipt is None:
        return _blocked(
            "research_packet_v2_approval_missing",
            (),
            "Zatwierdź pełny dokładny pakiet v2 przez ActionObject.",
        )
    if receipt.packet_id != packet_id or receipt.packet_digest != expected_digest:
        return _blocked(
            "research_packet_v2_digest_mismatch",
            (),
            "Wybierz receipt zgodny z dokładnym ID i digestem pakietu.",
        )
    try:
        record = store.load_research_packet_v2_preview(receipt.packet_digest)
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        return _blocked(
            "research_packet_v2_snapshot_invalid",
            (),
            "Odczytaj ponownie dokładny zapisany podgląd pakietu.",
        )
    if record is None or record.snapshot.preview_hash != receipt.packet_digest:
        return _blocked(
            "research_packet_v2_snapshot_missing",
            (),
            "Odtwórz dokładny podgląd związany z receipt pakietu.",
        )
    preview = record.snapshot
    evidence_ids = preview.evidence_ids
    if planning_input.work_item_id != preview.work_item_id:
        return _blocked(
            "research_packet_v2_work_item_mismatch",
            evidence_ids,
            "Odtwórz input dla dokładnej strony pakietu.",
        )
    if planning_input.planning_input_digest != preview.planning_input_digest:
        return _blocked(
            "research_packet_v2_planning_input_changed",
            evidence_ids,
            "Przygotuj i przejrzyj nowy pakiet dla aktualnego inputu planowania.",
        )
    loader = current_preview_loader or (
        lambda item_id, current_input: rebuild_current_packet_v2_preview(
            item_id, store=store, planning_input=current_input
        )
    )
    try:
        current = loader(preview.work_item_id, planning_input)
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        return _blocked(
            "research_packet_v2_current_read_unavailable",
            evidence_ids,
            "Ponów odczyt bieżących źródeł pakietu.",
        )
    if current.status == "blocked":
        return current.blocker or _blocked(
            "research_packet_v2_current_blocked",
            evidence_ids,
            "Usuń bieżący blocker pakietu i ponów odczyt.",
        )
    if current.preview_hash != receipt.packet_digest:
        return _blocked(
            "research_packet_v2_current_drift",
            tuple(sorted(set(evidence_ids) | set(current.evidence_ids))),
            "Przygotuj i zatwierdź nowy pakiet dla bieżących źródeł.",
        )
    return ApprovedPacketV2PlanningView(
        packet_id=receipt.packet_id,
        packet_digest=receipt.packet_digest,
        current_work_item_id=preview.work_item_id,
        approved_source_fact_ids=tuple(fact.source_fact_id for fact in preview.selected_facts),
        evidence_ids=evidence_ids,
        preview=preview,
    )


def rebuild_current_packet_v2_preview(
    work_item_id: str,
    *,
    store: ContentWorkflowStore,
    planning_input: ContentPlanningInput,
) -> ResearchPacketV2Preview:
    evidence = read_current_page_evidence_current(work_item_id)
    identity = resolve_current_page_identity_v2(work_item_id, store=store, evidence=evidence)
    receipt = store.load_latest_source_fact_authority_v2_receipt_for_work_item(work_item_id)
    source_pack = build_source_pack_v2_preview(
        work_item_id,
        identity=identity,
        authority_receipts=() if receipt is None else (receipt,),
    )
    return build_research_packet_v2_preview(
        work_item_id,
        source_pack=source_pack,
        planning_input=planning_input,
    )


def _blocked(
    code: str, evidence_ids: tuple[str, ...], next_step: str
) -> ResearchPacketV2PreviewBlocker:
    return ResearchPacketV2PreviewBlocker(
        code=code,
        owner="WILQ content workflow",
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=next_step,
    )


__all__ = [
    "ApprovedPacketV2PlanningView",
    "CurrentPreviewLoader",
    "rebuild_current_packet_v2_preview",
    "resolve_approved_packet_v2_for_planning",
]
