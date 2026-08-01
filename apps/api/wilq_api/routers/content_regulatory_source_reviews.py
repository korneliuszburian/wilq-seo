from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_runtime import content_codex_app_server_client
from wilq.content.regulatory.source_fact_proposals import (
    ContentRegulatorySourceFactProposalResponse,
    ContentRegulatorySourceFactProposalReviewCommand,
    generate_source_fact_proposal,
    read_source_fact_proposal,
    regulatory_source_fact_proposal_store,
    review_source_fact_proposal,
)
from wilq.content.regulatory.source_reviews import (
    ContentRegulatorySourceReview,
    ContentRegulatorySourceReviewCommand,
    ContentRegulatorySourceReviewConflict,
    ContentRegulatorySourceReviewList,
    regulatory_source_review_store,
)
from wilq.content.regulatory.source_snapshots import (
    ContentRegulatorySourceSnapshotReadResponse,
    regulatory_source_snapshot_store,
)
from wilq.storage.local_state import local_state_store


def register_content_regulatory_source_review_routes(router: APIRouter) -> None:
    """Expose the human-only promotion seam for official source candidates.

    This persists a local, append-only review decision. It neither fetches nor
    changes a regulator system and it never creates a content plan by itself.
    """

    _register_candidate_routes(router)
    _register_review_routes(router)


def _register_candidate_routes(router: APIRouter) -> None:
    @router.get(
        "/api/content/regulatory-source-candidates/{candidate_id}/snapshot",
        response_model=ContentRegulatorySourceSnapshotReadResponse,
    )
    def content_regulatory_source_snapshot(
        candidate_id: str,
    ) -> ContentRegulatorySourceSnapshotReadResponse:
        try:
            snapshot = regulatory_source_snapshot_store().capture(candidate_id)
        except (OSError, ValueError):
            return ContentRegulatorySourceSnapshotReadResponse(
                status="blocked",
                reason="Nie udało się odczytać aktualnego materiału urzędowego.",
                safe_next_step=(
                    "Otwórz wskazane źródło urzędowe ponownie i spróbuj odczytu później."
                ),
            )
        return ContentRegulatorySourceSnapshotReadResponse(
            status="captured",
            snapshot=snapshot,
            reason="Pobrano aktualny snapshot oficjalnego źródła do review.",
            safe_next_step="Sprawdź materiał i zapisz decyzję z dokładnym snapshotem.",
        )

    @router.post(
        "/api/content/regulatory-source-candidates/{candidate_id}/fact-proposal",
        response_model=ContentRegulatorySourceFactProposalResponse,
    )
    def content_regulatory_source_fact_proposal(
        candidate_id: str,
    ) -> ContentRegulatorySourceFactProposalResponse:
        return generate_source_fact_proposal(
            candidate_id=candidate_id,
            client=content_codex_app_server_client(),
            proposal_store=regulatory_source_fact_proposal_store(),
            snapshot_store=regulatory_source_snapshot_store(),
            run_store=local_state_store(),
        )

    @router.get(
        "/api/content/regulatory-source-candidates/{candidate_id}/fact-proposal",
        response_model=ContentRegulatorySourceFactProposalResponse,
    )
    def read_content_regulatory_source_fact_proposal(
        candidate_id: str,
    ) -> ContentRegulatorySourceFactProposalResponse:
        return read_source_fact_proposal(
            candidate_id=candidate_id,
            proposal_store=regulatory_source_fact_proposal_store(),
        )


def _register_review_routes(router: APIRouter) -> None:
    @router.get(
        "/api/content/regulatory-source-reviews",
        response_model=ContentRegulatorySourceReviewList,
    )
    def content_regulatory_source_reviews() -> ContentRegulatorySourceReviewList:
        return ContentRegulatorySourceReviewList(
            reviews=regulatory_source_review_store().list_reviews()
        )

    @router.post(
        "/api/content/regulatory-source-reviews",
        response_model=ContentRegulatorySourceReview,
        responses={409: {"model": ContentRegulatorySourceReviewConflict}},
    )
    def content_regulatory_source_review(
        command: ContentRegulatorySourceReviewCommand,
    ) -> ContentRegulatorySourceReview | JSONResponse:
        try:
            return regulatory_source_review_store().record(command)
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content=_review_conflict(str(error)).model_dump(mode="json"),
            )

    @router.post(
        "/api/content/regulatory-source-fact-proposals/{proposal_id}/review",
        response_model=ContentRegulatorySourceReview,
        responses={409: {"model": ContentRegulatorySourceReviewConflict}},
    )
    def content_regulatory_source_fact_proposal_review(
        proposal_id: str,
        command: ContentRegulatorySourceFactProposalReviewCommand,
    ) -> ContentRegulatorySourceReview | JSONResponse:
        try:
            return review_source_fact_proposal(
                proposal_id=proposal_id,
                command=command,
                proposal_store=regulatory_source_fact_proposal_store(),
                review_store=regulatory_source_review_store(),
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content=_review_conflict(str(error)).model_dump(mode="json"),
            )


def _review_conflict(reason: str) -> ContentRegulatorySourceReviewConflict:
    if "snapshot is missing" in reason:
        code = "source_snapshot_missing"
        label = "Brakuje snapshotu źródła"
    elif "snapshot changed" in reason:
        code = "source_snapshot_changed"
        label = "Snapshot źródła jest nieaktualny"
    else:
        code = "candidate_changed"
        label = "Kandydat źródła zmienił się"
    return ContentRegulatorySourceReviewConflict(
        code=code,
        label=label,
        reason=reason,
        safe_next_step="Odczytaj bieżący materiał urzędowy i zapisz review ponownie.",
    )
