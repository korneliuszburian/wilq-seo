"""Public read-only source-fact candidates bound to receiptless page identity."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Path

from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v3 import resolve_current_page_identity_v3
from wilq.content.workflow.source_fact_candidate_v3 import (
    ContentSourceFactCandidateV3Projection,
    build_content_source_fact_candidates_v3_projection,
)

EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]


def register_content_source_fact_candidate_v3_route(
    router: APIRouter,
    *,
    evidence_loader: EvidenceLoader | None = None,
) -> None:
    load_evidence = evidence_loader or (
        lambda work_item_id: content_current_page_evidence.read_current_page_evidence(
            work_item_id=work_item_id
        )
    )

    @router.get(
        "/api/content/work-items/{work_item_id}/source-fact-candidates-v3",
        response_model=ContentSourceFactCandidateV3Projection,
    )
    def read_content_source_fact_candidates_v3(
        work_item_id: Annotated[str, Path(min_length=1, max_length=240)],
    ) -> ContentSourceFactCandidateV3Projection:
        identity = resolve_current_page_identity_v3(work_item_id, load_evidence(work_item_id))
        return build_content_source_fact_candidates_v3_projection(
            identity=identity,
            facts=ekologus_source_facts(),
            cards=ekologus_content_knowledge_cards(),
        )
