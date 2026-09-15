from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse

from wilq.content.quality.independent_review_contracts import (
    ContentIndependentFindingDispositionRequest,
    ContentIndependentFindingDispositionResponse,
    ContentIndependentReviewBlocker,
    ContentIndependentReviewRunCollection,
    ContentIndependentReviewRunResponse,
    ContentIndependentReviewRunSubmission,
)
from wilq.content.quality.independent_review_service import (
    independent_review_binding_blocker,
    persist_independent_review_run,
    record_independent_finding_disposition,
    resolve_independent_review_context,
)
from wilq.content.quality.independent_review_store import (
    IndependentReviewConflict,
    IndependentReviewNotFound,
    IndependentReviewStorageActivationRequired,
    content_independent_review_store,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.documents.revisions import ContentDraftRevision

IndependentReviewSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def register_content_independent_review_routes(
    router: APIRouter,
    *,
    snapshot_loader: IndependentReviewSnapshotLoader,
) -> None:
    path = (
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/"
        "independent-reviews"
    )

    @router.get(path, response_model=ContentIndependentReviewRunCollection)
    def list_independent_reviews(
        work_item_id: str,
        revision_id: str,
    ) -> ContentIndependentReviewRunCollection:
        revision = _current_revision(snapshot_loader, work_item_id, revision_id)
        store = content_independent_review_store()
        storage_ready = store.write_ready()
        runs = (
            store.for_revision(work_item_id, revision_id, revision.content_digest)
            if storage_ready
            else []
        )
        blockers = _independent_read_blockers(
            snapshot_loader=snapshot_loader,
            work_item_id=work_item_id,
            revision_id=revision_id,
            revision=revision,
            storage_ready=storage_ready,
        )
        return ContentIndependentReviewRunCollection(
            work_item_id=work_item_id,
            revision_id=revision_id,
            revision_digest=revision.content_digest,
            research_packet_id=revision.research_packet_id,
            research_packet_digest=revision.research_packet_digest,
            runs=runs,
            blockers=blockers,
            storage_status="ready" if storage_ready else "activation_required",
            safe_next_step=(
                blockers[0].next_step
                if blockers
                else "Rozlicz wszystkie role niezależnego review; wynik jest advisory "
                "i nie publikuje treści."
                if storage_ready
                else "Aktywuj storage review w zatwierdzonym maintenance window."
            ),
        )

    @router.post(
        path,
        response_model=ContentIndependentReviewRunResponse,
        responses={409: {"model": ContentIndependentReviewRunResponse}},
    )
    def submit_independent_review(
        work_item_id: str,
        revision_id: str,
        request: ContentIndependentReviewRunSubmission,
    ) -> ContentIndependentReviewRunResponse | JSONResponse:
        snapshot = snapshot_loader(work_item_id)
        revision = snapshot.revision_workspace.latest_revision
        packet_id = (
            getattr(revision, "research_packet_id", None) or request.run.research_packet_id
        )
        packet_digest = (
            getattr(revision, "research_packet_digest", None)
            or request.run.research_packet_digest
        )
        try:
            result = persist_independent_review_run(
                snapshot=snapshot,
                revision_id=revision_id,
                expected_revision_digest=request.expected_revision_digest,
                run=request.run,
                store=content_independent_review_store(),
                snapshot_loader=snapshot_loader,
            )
        except IndependentReviewConflict as error:
            return _independent_conflict_response(
                work_item_id=work_item_id,
                revision_id=revision_id,
                revision_digest=request.expected_revision_digest,
                research_packet_id=packet_id,
                research_packet_digest=packet_digest,
                error=error,
            )
        except IndependentReviewStorageActivationRequired as error:
            return _independent_conflict_response(
                work_item_id=work_item_id,
                revision_id=revision_id,
                revision_digest=request.expected_revision_digest,
                research_packet_id=packet_id,
                research_packet_digest=packet_digest,
                error=error,
            )
        return result

    _register_disposition_route(router, path + "/{run_id}/findings/{finding_id}/disposition")


def _independent_read_blockers(
    *,
    snapshot_loader: IndependentReviewSnapshotLoader,
    work_item_id: str,
    revision_id: str,
    revision: ContentDraftRevision,
    storage_ready: bool,
) -> list[ContentIndependentReviewBlocker]:
    if not storage_ready:
        return []
    resolution = resolve_independent_review_context(
        snapshot=snapshot_loader(work_item_id),
        revision_id=revision_id,
        expected_revision_digest=revision.content_digest,
        snapshot_loader=snapshot_loader,
    )
    if resolution is None or resolution.blocker is None:
        return []
    return [independent_review_binding_blocker(resolution)]


def _register_disposition_route(router: APIRouter, path: str) -> None:
    @router.post(
        path,
        response_model=ContentIndependentFindingDispositionResponse,
        responses={409: {"model": ContentIndependentFindingDispositionResponse}},
    )
    def dispose_independent_finding(
        work_item_id: str,
        revision_id: str,
        request: ContentIndependentFindingDispositionRequest,
        run_id: str = Path(..., min_length=1, max_length=160),
        finding_id: str = Path(..., min_length=1, max_length=160),
    ) -> ContentIndependentFindingDispositionResponse | JSONResponse:
        try:
            store = content_independent_review_store()
            if not store.write_ready():
                raise IndependentReviewStorageActivationRequired(
                    "Aktywuj storage review w zatwierdzonym maintenance window."
                )
            return record_independent_finding_disposition(
                work_item_id=work_item_id,
                revision_id=revision_id,
                run_id=run_id,
                finding_id=finding_id,
                request=request,
                store=store,
            )
        except IndependentReviewNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except IndependentReviewConflict as error:
            return JSONResponse(
                status_code=409,
                content={
                    "status": "conflict",
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "revision_digest": request.expected_revision_digest,
                    "finding_id": finding_id,
                    "requires_child_revision": False,
                    "safe_next_step": str(error),
                },
            )
        except IndependentReviewStorageActivationRequired as error:
            return JSONResponse(
                status_code=409,
                content={
                    "status": "conflict",
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "revision_digest": request.expected_revision_digest,
                    "finding_id": finding_id,
                    "requires_child_revision": False,
                    "safe_next_step": str(error),
                },
            )


def _current_revision(
    snapshot_loader: IndependentReviewSnapshotLoader,
    work_item_id: str,
    revision_id: str,
) -> ContentDraftRevision:
    revision = snapshot_loader(work_item_id).revision_workspace.latest_revision
    if revision is None or revision.revision_id != revision_id:
        raise HTTPException(
            status_code=409,
            detail="Independent review requires current exact revision.",
        )
    return revision


def _independent_conflict_response(
    *,
    work_item_id: str,
    revision_id: str,
    revision_digest: str,
    research_packet_id: str | None,
    research_packet_digest: str | None,
    error: Exception,
) -> JSONResponse:
    raw_blocker = getattr(error, "blocker", None)
    blockers = [raw_blocker] if isinstance(raw_blocker, ContentIndependentReviewBlocker) else []
    payload = ContentIndependentReviewRunResponse(
        status="conflict",
        work_item_id=work_item_id,
        revision_id=revision_id,
        revision_digest=revision_digest,
        research_packet_id=research_packet_id,
        research_packet_digest=research_packet_digest,
        blockers=blockers,
        safe_next_step=str(error),
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


__all__ = ["register_content_independent_review_routes"]
