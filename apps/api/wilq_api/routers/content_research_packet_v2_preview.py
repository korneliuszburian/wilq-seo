"""Read-only preview of a research packet from the exact current v2 inputs."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from apps.api.wilq_api.routers.content_source_pack_v2 import read_current_source_pack_v2_preview
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
    build_content_planning_input,
)
from wilq.content.planning.generation_readiness import planning_generation_blockers
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.research_packet_v2_preview import (
    ResearchPacketV2Preview,
    build_research_packet_v2_preview,
)
from wilq.content.workflow.source_pack_v2 import SourcePackV2Blocker, SourcePackV2Preview

SnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
SourcePackLoader = Callable[[str], SourcePackV2Preview]
PlanningInputLoader = Callable[[str], ContentPlanningInput]


def register_content_research_packet_v2_preview_route(
    router: APIRouter,
    *,
    snapshot_loader: SnapshotLoader | None = None,
    source_pack_loader: SourcePackLoader | None = None,
    planning_input_loader: PlanningInputLoader | None = None,
) -> None:
    load_snapshot = snapshot_loader or snapshot_for_work_item_or_404
    load_source_pack = source_pack_loader or read_current_source_pack_v2_preview

    @router.get(
        "/api/content/work-items/{work_item_id}/research-packet-v2-preview",
        response_model=ResearchPacketV2Preview,
    )
    def read_research_packet_v2_preview(work_item_id: str) -> ResearchPacketV2Preview:
        source_pack = load_source_pack(work_item_id)
        if source_pack.status == "blocked":
            return build_research_packet_v2_preview(
                work_item_id, source_pack=source_pack, planning_input=None
            )
        if planning_input_loader is not None:
            return build_research_packet_v2_preview(
                work_item_id,
                source_pack=source_pack,
                planning_input=planning_input_loader(work_item_id),
            )
        snapshot = load_snapshot(work_item_id)
        service_card_id = getattr(snapshot.service_profile_context, "service_card_id", None)
        result = build_content_planning_input(snapshot, service_card_id=service_card_id)
        planning_input = result.planning_input
        blocker = _planning_blocker(
            result,
            tuple(snapshot.preflight.item.evidence_ids),
        )
        return build_research_packet_v2_preview(
            work_item_id,
            source_pack=source_pack,
            planning_input=planning_input,
            planning_blocker=blocker,
        )


def _planning_blocker(
    result: ContentPlanningInputBuildResult,
    evidence_ids: tuple[str, ...],
) -> SourcePackV2Blocker | None:
    applicable = planning_generation_blockers(result.blockers)
    if not applicable:
        return None
    blocker = applicable[0]
    return SourcePackV2Blocker(
        code=blocker.code,
        owner="WILQ content workflow",
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=blocker.next_step,
    )


__all__ = ["register_content_research_packet_v2_preview_route"]
