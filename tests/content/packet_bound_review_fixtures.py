from __future__ import annotations

from types import SimpleNamespace

from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision


def _packet_bound_snapshot(
    *,
    packet_id: str | None = "content_research_packet_current",
    packet_digest: str | None = "d" * 64,
) -> tuple[SimpleNamespace, ContentDraftRevision]:
    revision = ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id="work_packet_review",
        revision_id="revision_packet_review",
        content_digest="a" * 64,
        planning_digest="b" * 64,
        planning_input_digest="c" * 64,
        content_kind="service",
        service_card_id="service_packet_review",
        research_packet_id=packet_id,
        research_packet_digest=packet_digest,
        sections=[],
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=revision.work_item_id,
        planning_digest=revision.planning_digest,
        planning_input_digest=revision.planning_input_digest,
        content_kind=revision.content_kind,
        service_card_id=revision.service_card_id,
        research_packet_id=packet_id,
        research_packet_digest=packet_digest,
    )
    return (
        SimpleNamespace(
            preflight=SimpleNamespace(item=SimpleNamespace(id=revision.work_item_id)),
            revision_workspace=SimpleNamespace(
                latest_revision=revision,
                context_current=True,
            ),
            planning_workspace=SimpleNamespace(proposal=proposal),
        ),
        revision,
    )
