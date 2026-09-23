"""Public typed preview and readback for source-fact authority v2."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.api.wilq_api.routers.content_current_page_identity_v2 import (
    _read_current_page_evidence,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v2 import (
    CurrentPageIdentityBlockerOwner,
    resolve_current_page_identity_v2,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_fact_authority_v2 import (
    ContentSourceFactAuthorityV2BlockerCode,
    ContentSourceFactAuthorityV2PreviewCommand,
    ContentSourceFactAuthorityV2Proposal,
    ContentSourceFactAuthorityV2Receipt,
    SourceFactAuthorityV2Blocked,
    prepare_source_fact_authority_v2,
    source_fact_authority_v2_action,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas import ActionObject

StoreFactory = Callable[[], ContentWorkflowStore]
EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]


class ContentSourceFactAuthorityV2ReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["preview_ready", "current", "blocked"]
    action_id: str | None = None
    action: ActionObject | None = None
    proposal: ContentSourceFactAuthorityV2Proposal | None = None
    receipt: ContentSourceFactAuthorityV2Receipt | None = None
    blocker_code: ContentSourceFactAuthorityV2BlockerCode | None = None
    blocker_owner: CurrentPageIdentityBlockerOwner | None = None
    blocker_evidence_ids: list[str] = Field(default_factory=list)
    safe_next_step: str | None = None

    @model_validator(mode="after")
    def require_typed_blocker(self) -> ContentSourceFactAuthorityV2ReadResponse:
        if self.status == "blocked" and not all(
            (self.blocker_code, self.blocker_owner, self.safe_next_step)
        ):
            raise ValueError("Blocked source fact authority v2 responses require a typed blocker.")
        if self.status != "blocked" and any(
            (self.blocker_code, self.blocker_owner, self.blocker_evidence_ids, self.safe_next_step)
        ):
            raise ValueError("Ready source fact authority v2 responses cannot carry a blocker.")
        return self


def register_content_source_fact_authority_v2_routes(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    evidence_loader: EvidenceLoader | None = None,
) -> None:
    make_store = store_factory or (lambda: content_workflow_store())
    load_evidence = evidence_loader or _read_current_page_evidence
    _register_preview_route(router, make_store, load_evidence)
    _register_read_route(router, make_store, load_evidence)


def _register_preview_route(
    router: APIRouter, store_factory: StoreFactory, evidence_loader: EvidenceLoader
) -> None:
    @router.post(
        "/api/content/source-fact-authorities/preview",
        response_model=ContentSourceFactAuthorityV2ReadResponse,
        responses={409: {"model": ContentSourceFactAuthorityV2ReadResponse}},
    )
    def preview_route(
        command: ContentSourceFactAuthorityV2PreviewCommand,
        response: Response,
    ) -> ContentSourceFactAuthorityV2ReadResponse:
        return _preview_source_fact_authority_v2(
            command, response, store_factory=store_factory, evidence_loader=evidence_loader
        )


def _register_read_route(
    router: APIRouter, store_factory: StoreFactory, evidence_loader: EvidenceLoader
) -> None:
    @router.get(
        "/api/content/source-fact-authorities/{action_id}",
        response_model=ContentSourceFactAuthorityV2ReadResponse,
    )
    def read_route(action_id: str) -> ContentSourceFactAuthorityV2ReadResponse:
        return _read_source_fact_authority_v2(
            action_id, store_factory=store_factory, evidence_loader=evidence_loader
        )


def _preview_source_fact_authority_v2(
    command: ContentSourceFactAuthorityV2PreviewCommand,
    response: Response,
    *,
    store_factory: StoreFactory,
    evidence_loader: EvidenceLoader,
) -> ContentSourceFactAuthorityV2ReadResponse:
    store = store_factory()
    identity = resolve_current_page_identity_v2(
        command.work_item_id,
        store=store,
        evidence=evidence_loader(command.work_item_id),
    )
    try:
        proposal = prepare_source_fact_authority_v2(command, identity=identity)
    except SourceFactAuthorityV2Blocked as blocker:
        response.status_code = 409
        return _blocked_response(blocker)
    except ValueError:
        response.status_code = 409
        return _blocked_response(
            SourceFactAuthorityV2Blocked(
                "source_fact_authority_unavailable",
                "Ponów odczyt bieżącego KEEP i zatwierdzonych kandydatów.",
                tuple(identity.current_evidence_ids),
            )
        )
    stored = store.record_source_fact_authority_v2_proposal(proposal)
    return ContentSourceFactAuthorityV2ReadResponse(
        status="preview_ready",
        action_id=stored.action_id,
        action=source_fact_authority_v2_action(stored),
        proposal=stored,
    )


def _read_source_fact_authority_v2(
    action_id: str,
    *,
    store_factory: StoreFactory,
    evidence_loader: EvidenceLoader,
) -> ContentSourceFactAuthorityV2ReadResponse:
    store = store_factory()
    proposal = store.load_source_fact_authority_v2_proposal(action_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Source fact authority v2 proposal not found.")
    receipt = store.load_source_fact_authority_v2_receipt(action_id)
    identity = resolve_current_page_identity_v2(
        proposal.snapshot.work_item_id,
        store=store,
        evidence=evidence_loader(proposal.snapshot.work_item_id),
    )
    blocker = None
    try:
        current_proposal = prepare_source_fact_authority_v2(
            ContentSourceFactAuthorityV2PreviewCommand(
                work_item_id=proposal.snapshot.work_item_id,
                expected_keep_receipt_id=proposal.snapshot.keep_receipt_id,
                expected_keep_receipt_digest=proposal.snapshot.keep_receipt_digest,
                expected_material_meaning_digest=proposal.snapshot.material_meaning_digest,
                source_fact_ids=tuple(
                    fact.source_fact_id for fact in proposal.snapshot.selected_facts
                ),
                attempt=proposal.attempt,
            ),
            identity=identity,
        )
        current = current_proposal.proposal_digest == proposal.proposal_digest
    except SourceFactAuthorityV2Blocked as error:
        blocker = error
        current = False
    except ValueError:
        current = False
    receipt_current = (
        receipt is not None
        and current
        and receipt.snapshot == proposal.snapshot
        and receipt.action_payload_digest
        == canonical_json_digest(source_fact_authority_v2_action(proposal).payload)
    )
    status: Literal["current", "preview_ready", "blocked"] = (
        "blocked"
        if receipt is not None and not receipt_current
        else "current"
        if receipt_current
        else "preview_ready"
        if current
        else "blocked"
    )
    if status == "blocked" and blocker is None:
        blocker = SourceFactAuthorityV2Blocked(
            "source_fact_authority_receipt_mismatch"
            if receipt is not None
            else "source_fact_authority_unavailable",
            "Odczytaj aktualny KEEP i przygotuj nowy preview.",
            tuple(identity.current_evidence_ids),
        )
    response = ContentSourceFactAuthorityV2ReadResponse(
        status=status,
        action_id=action_id,
        action=source_fact_authority_v2_action(proposal),
        proposal=proposal,
        receipt=receipt,
        blocker_code=None if blocker is None else blocker.code,
        blocker_owner=None if blocker is None else blocker.owner,
        blocker_evidence_ids=[] if blocker is None else list(blocker.evidence_ids),
        safe_next_step=None if blocker is None else blocker.safe_next_step,
    )
    return response


def _blocked_response(
    blocker: SourceFactAuthorityV2Blocked,
) -> ContentSourceFactAuthorityV2ReadResponse:
    return ContentSourceFactAuthorityV2ReadResponse(
        status="blocked",
        blocker_code=blocker.code,
        blocker_owner=blocker.owner,
        blocker_evidence_ids=list(blocker.evidence_ids),
        safe_next_step=blocker.safe_next_step,
    )


__all__ = ["register_content_source_fact_authority_v2_routes"]
