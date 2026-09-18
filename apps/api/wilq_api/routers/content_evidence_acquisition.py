from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from wilq.content.workflow.evidence_acquisition_coordinator import (
    EvidenceAcquisitionCurrentProjection,
    EvidenceAcquisitionStartCommand,
    build_default_evidence_acquisition_coordinator,
)
from wilq.content.workflow.research_promotion_authority import (
    ContentResearchFactPromotionPreviewCommand,
    ContentResearchFactPromotionPreviewRequest,
    ContentResearchFactPromotionPreviewResponse,
    prepare_research_fact_promotion_preview,
)
from wilq.content.workflow.research_promotion_candidate import (
    ResearchPromotionCandidateProjection,
    build_default_research_promotion_candidate,
)
from wilq.content.workflow.research_proposal import (
    ContentResearchProposalCurrentProjection,
    ResearchProposalLegacyUnreadable,
    build_default_evidence_research_coordinator,
)
from wilq.content.workflow.store.store import content_workflow_store


def register_content_evidence_acquisition_routes(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/evidence-acquisition",
        content_evidence_acquisition_start,
        methods=["POST"],
        response_model=EvidenceAcquisitionCurrentProjection,
        tags=["content"],
    )
    router.add_api_route(
        "/api/content/evidence-acquisition/{run_id}",
        content_evidence_acquisition_read,
        methods=["GET"],
        response_model=EvidenceAcquisitionCurrentProjection,
        tags=["content"],
    )
    router.add_api_route(
        "/api/content/evidence-acquisition/{run_id}/research",
        content_evidence_acquisition_research,
        methods=["POST"],
        response_model=ContentResearchProposalCurrentProjection,
        tags=["content"],
    )
    router.add_api_route(
        "/api/content/evidence-acquisition/research/{proposal_id}",
        content_evidence_acquisition_research_read,
        methods=["GET"],
        response_model=ContentResearchProposalCurrentProjection,
        tags=["content"],
    )
    router.add_api_route(
        "/api/content/evidence-acquisition/research/{proposal_id}/promotion-candidate",
        content_research_promotion_candidate_read,
        methods=["GET"],
        response_model=ResearchPromotionCandidateProjection,
        tags=["content"],
    )
    router.add_api_route(
        "/api/content/evidence-acquisition/research/{proposal_id}/promotion-preview",
        content_research_promotion_preview,
        methods=["POST"],
        response_model=ContentResearchFactPromotionPreviewResponse,
        tags=["content"],
    )


def content_evidence_acquisition_start(
    command: EvidenceAcquisitionStartCommand,
) -> EvidenceAcquisitionCurrentProjection:
    """Start a server-owned proposal-only run; no researcher is invoked here."""

    return build_default_evidence_acquisition_coordinator().start(command)


def content_evidence_acquisition_read(
    run_id: Annotated[str, Path(pattern=r"^[a-z][a-z0-9_-]{0,239}$")],
) -> EvidenceAcquisitionCurrentProjection:
    run = build_default_evidence_acquisition_coordinator().read(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="evidence_acquisition_run_not_found")
    return run


def content_evidence_acquisition_research(
    run_id: Annotated[str, Path(pattern=r"^[a-z][a-z0-9_-]{0,239}$")],
) -> ContentResearchProposalCurrentProjection:
    try:
        return build_default_evidence_research_coordinator().start(run_id)
    except ResearchProposalLegacyUnreadable as exc:
        raise _legacy_proposal_http_exception(exc) from exc


def content_evidence_acquisition_research_read(
    proposal_id: Annotated[str, Path(pattern=r"^[a-z][a-z0-9_-]{0,239}$")],
) -> ContentResearchProposalCurrentProjection:
    try:
        proposal = build_default_evidence_research_coordinator().read(proposal_id)
    except ResearchProposalLegacyUnreadable as exc:
        raise _legacy_proposal_http_exception(exc) from exc
    if proposal is None:
        raise HTTPException(status_code=404, detail="research_proposal_not_found")
    return proposal


def content_research_promotion_candidate_read(
    proposal_id: Annotated[str, Path(pattern=r"^[a-z][a-z0-9_-]{0,239}$")],
) -> ResearchPromotionCandidateProjection:
    try:
        return build_default_research_promotion_candidate(proposal_id)
    except ResearchProposalLegacyUnreadable as exc:
        raise _legacy_proposal_http_exception(exc) from exc


def content_research_promotion_preview(
    proposal_id: Annotated[str, Path(pattern=r"^[a-z][a-z0-9_-]{0,239}$")],
    request: ContentResearchFactPromotionPreviewRequest,
) -> ContentResearchFactPromotionPreviewResponse:
    return prepare_research_fact_promotion_preview(
        ContentResearchFactPromotionPreviewCommand(
            proposal_id=proposal_id,
            proposed_scope=request.proposed_scope,
            proposed_confidence=request.proposed_confidence,
        ),
        store=content_workflow_store(),
    )


def _legacy_proposal_http_exception(exc: ResearchProposalLegacyUnreadable) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=exc.diagnostic.model_dump(mode="json"),
    )


__all__ = ["register_content_evidence_acquisition_routes"]
