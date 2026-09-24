"""Public read-only v3 research packet preview from exact current sources."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from apps.api.wilq_api.routers.content_source_pack_v3 import (
    read_current_source_pack_v3_preview,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputBuildResult,
    build_content_planning_input,
)
from wilq.content.workflow.research_packet_v3_preview import (
    ResearchPacketV3Preview,
    build_research_packet_v3_preview,
)
from wilq.content.workflow.source_pack_v3 import SourcePackV3Preview

SourcePackLoader = Callable[[str], SourcePackV3Preview]
PlanningResultLoader = Callable[[str], ContentPlanningInputBuildResult]


def register_content_research_packet_v3_preview_route(
    router: APIRouter,
    *,
    source_pack_loader: SourcePackLoader | None = None,
    planning_result_loader: PlanningResultLoader | None = None,
) -> None:
    load_pack = source_pack_loader or read_current_source_pack_v3_preview
    load_planning = planning_result_loader or _current_planning_result

    @router.get(
        "/api/content/work-items/{work_item_id}/research-packet-v3-preview",
        response_model=ResearchPacketV3Preview,
    )
    def read_research_packet_v3_preview(work_item_id: str) -> ResearchPacketV3Preview:
        pack = load_pack(work_item_id)
        if pack.status == "blocked":
            return build_research_packet_v3_preview(
                work_item_id, source_pack=pack, planning_result=ContentPlanningInputBuildResult()
            )
        try:
            planning = load_planning(work_item_id)
        except (HTTPException, ValueError, RuntimeError):
            planning = ContentPlanningInputBuildResult()
        return build_research_packet_v3_preview(
            work_item_id, source_pack=pack, planning_result=planning
        )


def _current_planning_result(work_item_id: str) -> ContentPlanningInputBuildResult:
    snapshot = snapshot_for_work_item_or_404(work_item_id)
    card_id = getattr(snapshot.service_profile_context, "service_card_id", None)
    return build_content_planning_input(snapshot, service_card_id=card_id)
