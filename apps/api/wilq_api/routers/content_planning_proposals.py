from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_refresh_preparation_authority import (
    content_refresh_preparation_authority,
)
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.planning import planning_generation_queue
from wilq.content.planning.generated_proposal import (
    read_content_planning_proposal,
    with_current_planning_workspace,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.planning.subject import ContentPlanningSubject, PlanningContentKind
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.refresh_preparation import (
    ContentRefreshPreparationAuthority,
    RefreshPreparationRuntimeAuthorized,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBinding,
    ContentRefreshPreparationBlocked,
)
from wilq.content.workflow.store.store import content_workflow_store

ContentPlanningSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
ContentRefreshPreparationAuthorityFactory = Callable[[], ContentRefreshPreparationAuthority]


@dataclass(frozen=True)
class _LegacyUnboundRefreshPlanningContext:
    service_card_id: str
    planning_input_digest: str


def register_content_planning_proposal_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentPlanningSnapshotLoader,
    refresh_authority_factory: ContentRefreshPreparationAuthorityFactory | None = None,
) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/planning-proposals",
        response_model=ContentPlanningProposalResponse,
    )
    def content_work_item_planning_proposal_status(
        work_item_id: str,
    ) -> ContentPlanningProposalResponse:
        return _get_content_work_item_planning_proposal_status(
            work_item_id=work_item_id,
            snapshot_loader=snapshot_loader,
            refresh_authority=(
                refresh_authority_factory()
                if refresh_authority_factory is not None
                else _canonical_refresh_preparation_authority()
            ),
        )

    @router.post(
        "/api/content/work-items/{work_item_id}/planning-proposals",
        response_model=ContentPlanningProposalResponse,
        responses={
            409: {"model": ContentPlanningProposalResponse},
            422: {"model": ContentPlanningProposalResponse},
        },
    )
    def content_work_item_planning_proposal_generate(
        work_item_id: str,
        request: ContentPlanningProposalRequest,
    ) -> ContentPlanningProposalResponse | JSONResponse:
        return _generate_content_work_item_planning_proposal(
            work_item_id=work_item_id,
            request=request,
            snapshot_loader=snapshot_loader,
            refresh_authority=(
                refresh_authority_factory()
                if refresh_authority_factory is not None
                else _canonical_refresh_preparation_authority()
            ),
        )


def _get_content_work_item_planning_proposal_status(
    *,
    work_item_id: str,
    snapshot_loader: ContentPlanningSnapshotLoader,
    refresh_authority: ContentRefreshPreparationAuthority | None = None,
) -> ContentPlanningProposalResponse:
    store = content_planning_proposal_store()
    authority = refresh_authority or _canonical_refresh_preparation_authority()
    reconciliation = _legacy_unbound_refresh_reconciliation_status(
        store=store,
        work_item_id=work_item_id,
        authority=authority,
    )
    if reconciliation is not None:
        return reconciliation
    binding = _latest_refresh_preparation_binding(store, work_item_id)
    if binding is not None:
        authorized = _authorized_refresh_planning_status(
            work_item_id=work_item_id,
            binding=binding,
            authority=authority,
            store=store,
        )
        if authorized is not None:
            return with_current_planning_workspace(
                authorized,
                content_workflow_store().load_planning_decisions(work_item_id),
            )
    snapshot = snapshot_loader(work_item_id)
    response = read_content_planning_proposal(
        snapshot=snapshot,
        store=store,
    )
    return with_current_planning_workspace(
        response, content_workflow_store().load_planning_decisions(work_item_id)
    )


def _latest_refresh_preparation_binding(
    store: ContentPlanningProposalStore,
    work_item_id: str,
) -> ContentRefreshPreparationBinding | None:
    try:
        queued = store.latest_generation_response(work_item_id)
    except ValueError:
        queued = None
    if queued is not None:
        binding = queued.refresh_preparation_binding
        if binding is None and queued.proposal is not None:
            binding = queued.proposal.refresh_preparation_binding
        if binding is not None:
            return binding
    proposal = store.latest(work_item_id)
    return None if proposal is None else proposal.refresh_preparation_binding


def _legacy_unbound_refresh_reconciliation_status(
    *,
    store: ContentPlanningProposalStore,
    work_item_id: str,
    authority: ContentRefreshPreparationAuthority,
) -> ContentPlanningProposalResponse | None:
    context = _latest_unbound_refresh_planning_context(store, work_item_id)
    if context is None:
        return None
    preview = authority.preview(work_item_id, service_card_id=context.service_card_id)
    if _is_unclassified_refresh_preview(preview):
        return None
    return _legacy_unbound_refresh_reconciliation_block(
        work_item_id=work_item_id,
        content_kind="service",
        service_card_id=context.service_card_id,
    )


def _is_unclassified_refresh_preview(preview: object) -> bool:
    return bool(
        isinstance(preview, ContentRefreshPreparationBlocked)
        and preview.classification is None
        and preview.blockers[0].code == "production_classification_missing"
    )


def _latest_unbound_refresh_planning_context(
    store: ContentPlanningProposalStore,
    work_item_id: str,
) -> _LegacyUnboundRefreshPlanningContext | None:
    try:
        queued = store.latest_generation_response(work_item_id)
    except ValueError:
        queued = None
    queued_binding = (
        None
        if queued is None
        else (
            queued.refresh_preparation_binding
            if queued.refresh_preparation_binding is not None
            else None if queued.proposal is None else queued.proposal.refresh_preparation_binding
        )
    )
    if (
        queued is not None
        and queued_binding is None
        and queued.service_card_id is not None
        and queued.planning_input_digest is not None
    ):
        return _LegacyUnboundRefreshPlanningContext(
            service_card_id=queued.service_card_id,
            planning_input_digest=queued.planning_input_digest,
        )
    try:
        proposal = store.latest(work_item_id)
    except ValueError:
        proposal = None
    if (
        proposal is None
        or proposal.refresh_preparation_binding is not None
        or proposal.service_card_id is None
        or proposal.planning_input_digest is None
    ):
        return None
    return _LegacyUnboundRefreshPlanningContext(
        service_card_id=proposal.service_card_id,
        planning_input_digest=proposal.planning_input_digest,
    )


def _legacy_unbound_refresh_reconciliation_block(
    *,
    work_item_id: str,
    content_kind: PlanningContentKind,
    service_card_id: str | None,
) -> ContentPlanningProposalResponse:
    blocker = ContentPlanningProposalBlocker(
        code="refresh_preparation_proposal_binding_mismatch",
        label="Zachowany plan V1 nie ma receiptu refresh",
        reason=(
            "Ten sam exact input ma zachowany plan albo job V1 bez authorization ID i "
            "digesta. Nie ponawiaj: V1 nie zastąpi zachowanego planu bez receipt; "
            "wymagana jest osobna re-adjudykacja/reconciliation albo zmiana inputu."
        ),
        next_step=(
            "Nie ponawiaj generowania. Wykonaj osobną re-adjudykację/reconciliation "
            "zachowanego planu albo zmień input refresh."
        ),
    )
    return ContentPlanningProposalResponse(
        status="blocked",
        content_kind=content_kind,
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _has_exact_unbound_refresh_legacy_plan(
    store: ContentPlanningProposalStore,
    request: ContentPlanningProposalRequest,
    work_item_id: str,
) -> bool:
    subject = ContentPlanningSubject(
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
    )
    proposal = store.for_subject_input(
        work_item_id,
        subject,
        request.expected_planning_input_digest,
    )
    if proposal is not None and proposal.refresh_preparation_binding is None:
        return True
    try:
        queued = store.queued_subject_response(
            work_item_id,
            subject,
            request.expected_planning_input_digest,
        )
    except ValueError:
        return False
    if queued is None:
        return False
    queued_binding = queued.refresh_preparation_binding
    if queued_binding is None and queued.proposal is not None:
        queued_binding = queued.proposal.refresh_preparation_binding
    return queued_binding is None


def _authorized_refresh_planning_status(
    *,
    work_item_id: str,
    binding: ContentRefreshPreparationBinding,
    authority: ContentRefreshPreparationAuthority,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse | None:
    if binding.service_card_id is None:
        return _bound_refresh_status_block(work_item_id, binding)
    request = ContentPlanningProposalRequest(
        service_card_id=binding.service_card_id,
        expected_planning_input_digest=binding.planning_input_digest,
        requested_by="status_read",
        refresh_preparation_authorization_id=binding.authorization_id,
        expected_refresh_preparation_authorization_digest=binding.authorization_digest,
    )
    resolution = authority.resolve_planning(work_item_id, request)
    blocked = authority.planning_block_response(resolution, request)
    if blocked is not None:
        return blocked
    if not isinstance(resolution, RefreshPreparationRuntimeAuthorized):
        return _bound_refresh_status_block(work_item_id, binding)
    response = read_content_planning_proposal(snapshot=resolution.snapshot, store=store)
    return response.model_copy(update={"refresh_preparation_binding": resolution.binding})


def _bound_refresh_status_block(
    work_item_id: str,
    binding: ContentRefreshPreparationBinding,
) -> ContentPlanningProposalResponse:
    blocker = ContentPlanningProposalBlocker(
        code="refresh_preparation_authorization_foreign",
        label="Plan refresh nie ma już bieżącej autoryzacji",
        reason=(
            "Trwały plan wskazuje receipt refresh, którego nie można odtworzyć dla "
            "bieżącej klasyfikacji i wybranej usługi."
        ),
        next_step="Odśwież przygotowanie refresh i wygeneruj plan dla bieżącego receipt.",
    )
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=work_item_id,
        content_kind=binding.content_kind,
        service_card_id=binding.service_card_id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _generate_content_work_item_planning_proposal(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    snapshot_loader: ContentPlanningSnapshotLoader,
    refresh_authority: ContentRefreshPreparationAuthority | None = None,
) -> ContentPlanningProposalResponse | JSONResponse:
    authority = refresh_authority or _canonical_refresh_preparation_authority()
    refresh_resolution = authority.resolve_planning(work_item_id, request)
    refresh_block = authority.planning_block_response(refresh_resolution, request)
    if refresh_block is not None:
        return JSONResponse(status_code=409, content=refresh_block.model_dump(mode="json"))
    if isinstance(refresh_resolution, RefreshPreparationRuntimeAuthorized):
        return _generate_authorized_refresh_planning_proposal(
            work_item_id=work_item_id,
            request=request,
            authority=authority,
            initial_resolution=refresh_resolution,
        )
    store = content_planning_proposal_store()
    unknown_response = _unknown_service_card_response(work_item_id=work_item_id, request=request)
    if unknown_response is not None:
        return unknown_response
    zero_digest_response = _zero_digest_response(work_item_id=work_item_id, request=request)
    if zero_digest_response is not None:
        return zero_digest_response
    planning_input, request, early_response = planning_generation_queue.prepare_planning_generation(
        work_item_id=work_item_id,
        request=request,
        snapshot_loader=snapshot_loader,
        store=store,
    )
    if early_response is not None:
        return early_response
    if planning_input is None:
        raise RuntimeError("Planning preparation returned no input or blocker.")
    return planning_generation_queue.enqueue_planning_generation(
        planning_input=planning_input,
        work_item_id=work_item_id,
        request=request,
        snapshot_loader=snapshot_loader,
        store=store,
    )


def _generate_authorized_refresh_planning_proposal(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    authority: ContentRefreshPreparationAuthority,
    initial_resolution: RefreshPreparationRuntimeAuthorized,
) -> ContentPlanningProposalResponse | JSONResponse:
    store = content_planning_proposal_store()
    if _has_exact_unbound_refresh_legacy_plan(store, request, work_item_id):
        response = _legacy_unbound_refresh_reconciliation_block(
            work_item_id=work_item_id,
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
        )
        return JSONResponse(status_code=409, content=response.model_dump(mode="json"))
    snapshot = initial_resolution.snapshot
    existing_snapshot, effective_request, existing_response = (
        planning_generation_queue.existing_planning_generation_state(
            work_item_id=work_item_id,
            request=request,
            snapshot_loader=lambda _work_item_id: snapshot,
            store=store,
            allow_automatic_stale_mapping_regeneration=False,
        )
    )
    if existing_response is not None:
        if _is_stale_mapping_response(existing_response):
            response = _authorized_stale_mapping_reconciliation_block(
                work_item_id=work_item_id,
                content_kind=request.content_kind,
                service_card_id=request.service_card_id,
            )
            return JSONResponse(status_code=409, content=response.model_dump(mode="json"))
        proposal = existing_response.proposal
        if (
            proposal is not None
            and proposal.refresh_preparation_binding == initial_resolution.binding
        ) or (
            proposal is None
            and existing_response.refresh_preparation_binding == initial_resolution.binding
        ):
            return existing_response
        blocker = ContentPlanningProposalBlocker(
            code="refresh_preparation_proposal_binding_mismatch",
            label="Istniejący plan nie jest związany z autoryzacją refresh",
            reason=(
                "Dokładny input ma zapisany plan bez bieżącego authorization ID i "
                "digesta; WILQ nie użyje go jako planu refresh."
            ),
            next_step="Odśwież kontekst i wygeneruj plan związany z bieżącą autoryzacją refresh.",
        )
        response = ContentPlanningProposalResponse(
            status="blocked",
            work_item_id=work_item_id,
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
            blockers=[blocker],
            safe_next_step=blocker.next_step,
        )
        return JSONResponse(status_code=409, content=response.model_dump(mode="json"))
    source_snapshot = existing_snapshot or snapshot
    planning_input, early_response = (
        planning_generation_queue.prepare_planning_generation_from_snapshot(
            snapshot=source_snapshot,
            request=effective_request,
            store=store,
        )
    )
    if early_response is not None:
        return early_response
    if planning_input is None:
        return planning_generation_queue.planning_generation_failure_response(
            work_item_id=work_item_id,
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            input_summary=None,
            error=RuntimeError("Authorized refresh planning preparation returned no input."),
        )

    def guard() -> ContentPlanningProposalResponse | None:
        return authority.planning_block_response(
            authority.resolve_planning(work_item_id, request), request
        )

    def current_snapshot(_work_item_id: str) -> ContentWorkItemWorkflowSnapshotResponse:
        current = authority.resolve_planning(work_item_id, request)
        if not isinstance(current, RefreshPreparationRuntimeAuthorized):
            raise RuntimeError("refresh_preparation_authority_changed")
        return current.snapshot

    return planning_generation_queue.enqueue_planning_generation(
        planning_input=planning_input,
        work_item_id=work_item_id,
        request=effective_request,
        snapshot_loader=current_snapshot,
        store=store,
        generation_guard=guard,
        refresh_preparation_binding=initial_resolution.binding,
    )


def _is_stale_mapping_response(response: ContentPlanningProposalResponse) -> bool:
    return bool(
        response.status == "stale"
        and any(
            blocker.label == "Mapa istniejącej strony wymaga odświeżenia"
            for blocker in response.blockers
        )
    )


def _authorized_stale_mapping_reconciliation_block(
    *,
    work_item_id: str,
    content_kind: PlanningContentKind,
    service_card_id: str | None,
) -> ContentPlanningProposalResponse:
    blocker = ContentPlanningProposalBlocker(
        code="refresh_preparation_proposal_binding_mismatch",
        label="Autoryzacja refresh nie pozwala zastąpić starej mapy",
        reason=(
            "Mapa istniejącej strony jest nieaktualna, ale receipt refresh autoryzuje "
            "jedną dokładną turę i nie może automatycznie ustawić replacementu."
        ),
        next_step=(
            "Nie ponawiaj automatycznie. Wykonaj osobną re-adjudykację/reconciliation "
            "mapy albo przygotuj nowy input refresh."
        ),
    )
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=work_item_id,
        content_kind=content_kind,
        service_card_id=service_card_id,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _canonical_refresh_preparation_authority() -> ContentRefreshPreparationAuthority:
    return content_refresh_preparation_authority()


def _unknown_service_card_response(
    *, work_item_id: str, request: ContentPlanningProposalRequest
) -> JSONResponse | None:
    if request.content_kind == "editorial":
        return None
    if any(
        card.id == request.service_card_id and card.card_type == "service"
        for card in ekologus_content_knowledge_cards()
    ):
        return None
    unknown = ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        blockers=[
            ContentPlanningProposalBlocker(
                code="unknown_service_card",
                label="Nieznana karta usługi",
                reason="Wybrana karta nie istnieje w aktualnym katalogu usług WILQ.",
                next_step="Wybierz kartę usługi zwróconą dla tego work itemu.",
            )
        ],
        safe_next_step="Wybierz kartę usługi zwróconą dla tego work itemu.",
    )
    return JSONResponse(status_code=422, content=unknown.model_dump(mode="json"))


def _zero_digest_response(
    *, work_item_id: str, request: ContentPlanningProposalRequest
) -> JSONResponse | None:
    if request.expected_planning_input_digest != "0" * 64:
        return None
    stale = ContentPlanningProposalResponse(
        status="stale",
        work_item_id=work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        blockers=[
            ContentPlanningProposalBlocker(
                code="stale_input",
                label="Wejście planu jest nieaktualne",
                reason="Pusty digest nie może reprezentować bieżącego wejścia planowania.",
                next_step="Odśwież stan planu i użyj aktualnego digestu.",
            )
        ],
        safe_next_step="Odśwież stan planu i użyj aktualnego digestu.",
    )
    return JSONResponse(status_code=409, content=stale.model_dump(mode="json"))


__all__ = ["register_content_planning_proposal_routes"]
