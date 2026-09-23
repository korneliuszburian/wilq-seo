"""Public read-only v2 candidates from the current page KEEP receipt."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Path

from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.source_fact_candidate_v2 import (
    ContentSourceFactCandidateV2Projection,
    build_content_source_fact_candidates_v2_projection,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store

StoreFactory = Callable[[], ContentWorkflowStore]
EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]


def register_content_source_fact_candidate_v2_route(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    evidence_loader: EvidenceLoader | None = None,
) -> None:
    from apps.api.wilq_api.routers.content_current_page_identity_v2 import (
        _read_current_page_evidence,
        resolve_current_page_identity_v2,
    )

    make_store = store_factory or (lambda: content_workflow_store())
    load_evidence = evidence_loader or _read_current_page_evidence

    @router.get(
        "/api/content/work-items/{work_item_id}/source-fact-candidates",
        response_model=ContentSourceFactCandidateV2Projection,
    )
    def read_content_source_fact_candidates_v2(
        work_item_id: Annotated[str, Path(min_length=1, max_length=240)],
    ) -> ContentSourceFactCandidateV2Projection:
        store = make_store()
        evidence = load_evidence(work_item_id)
        identity = resolve_current_page_identity_v2(
            work_item_id,
            store=store,
            evidence=evidence,
        )
        return build_content_source_fact_candidates_v2_projection(
            identity=identity,
            facts=ekologus_source_facts(),
            cards=ekologus_content_knowledge_cards(),
        )


__all__ = ["register_content_source_fact_candidate_v2_route"]
