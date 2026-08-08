from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_runtime import (
    content_codex_app_server_client,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputSummary,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal import (
    _prepare_generation,
    generate_content_planning_proposal,
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
    PlanningEnqueueOutcome,
    content_planning_proposal_store,
)
from wilq.content.planning.generation_claim_store import (
    ContentPlanningGenerationClaimStore,
    PlanningGenerationClaimFinalStatus,
    content_planning_generation_claim_store,
)
from wilq.content.planning.runtime_contract import planning_codex_timeout_seconds
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store.store import content_workflow_store
from wilq.storage.local_state import local_state_store

ContentPlanningSnapshotLoader = Callable[
    [str],
    ContentWorkItemWorkflowSnapshotResponse,
]

_PLANNING_GENERATION_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="wilq-content-plan",
)
# Planning is queued and polled by the API, so this deadline is not a browser
# request budget.  Keep the model turn bounded at three minutes; larger real
# pages can need more structured-output search, while a timeout remains a
# typed runtime blocker and can be retried from the same exact input digest.
# The first useful browser response remains the queued ``generating`` state.
def _planning_codex_client() -> StdioCodexAppServerClient:
    """Keep planning bounded without changing draft/review runtime budgets.

    Test and local harness clients are returned unchanged; only the real stdio
    adapter receives the planning-specific deadline.
    """

    client = content_codex_app_server_client()
    if not isinstance(client, StdioCodexAppServerClient):
        return client
    return StdioCodexAppServerClient(timeout_seconds=planning_codex_timeout_seconds())


def register_content_planning_proposal_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentPlanningSnapshotLoader,
) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/planning-proposals",
        response_model=ContentPlanningProposalResponse,
    )
    def content_work_item_planning_proposal_status(
        work_item_id: str,
    ) -> ContentPlanningProposalResponse:
        snapshot = snapshot_loader(work_item_id)
        response = read_content_planning_proposal(
            snapshot=snapshot,
            store=content_planning_proposal_store(),
        )
        return with_current_planning_workspace(
            response,
            content_workflow_store().load_planning_decisions(work_item_id),
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
        store = content_planning_proposal_store()
        if not any(
            card.id == request.service_card_id and card.card_type == "service"
            for card in ekologus_content_knowledge_cards()
        ):
            unknown = ContentPlanningProposalResponse(
                status="blocked",
                work_item_id=work_item_id,
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
        if request.expected_planning_input_digest == "0" * 64:
            stale = ContentPlanningProposalResponse(
                status="stale",
                work_item_id=work_item_id,
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
        snapshot: ContentWorkItemWorkflowSnapshotResponse | None = None
        existing = store.for_input(
            work_item_id,
            request.service_card_id,
            request.expected_planning_input_digest,
        )
        if existing is not None:
            snapshot = snapshot_loader(work_item_id)
            current = read_content_planning_proposal(
                snapshot=snapshot,
                store=store,
            )
            current_is_exact_input = (
                current.work_item_id == work_item_id
                and current.service_card_id == request.service_card_id
                and current.planning_input_digest == request.expected_planning_input_digest
            )
            current_has_existing_proposal = (
                current.proposal is not None
                and current.proposal.proposal_id == existing.proposal_id
                and current.proposal.planning_digest == existing.planning_digest
                and current.proposal.planning_input_digest == existing.planning_input_digest
            )
            current_is_exact_existing = current_is_exact_input and current_has_existing_proposal
            stale_mapping = current_is_exact_existing and current.status == "stale" and any(
                blocker.label == "Mapa istniejącej strony wymaga odświeżenia"
                for blocker in current.blockers
            )
            if stale_mapping or request.regenerate_after_review:
                # The server has already proved that this is the same exact
                # proposal and input. A stale inventory map or a review-bound
                # plan repair deliberately replaces only this exact lineage.
                request = request.model_copy(update={"regenerate_stale_mapping": True})
            elif current_is_exact_existing and current.status in {"created", "idempotent", "ready"}:
                return current.model_copy(
                    update={
                        "status": "idempotent",
                        "safe_next_step": (
                            "Plan już istnieje dla tego exact wejścia; odczytano wersję "
                            "bez ponownego uruchamiania Codexa."
                        ),
                    }
                )
            elif not current_is_exact_existing:
                # Never promote a historical proposal over the current typed
                # state: stale and quality-blocked reads are already the safe
                # response for this command.
                return current
            elif not request.regenerate_after_review:
                # A current quality blocker is actionable only after an
                # explicit new generation path, never through idempotency.
                return current
        if snapshot is None:
            try:
                snapshot = snapshot_loader(work_item_id)
            except Exception as error:
                return _planning_generation_failure_response(
                    work_item_id=work_item_id,
                    service_card_id=request.service_card_id,
                    planning_input_digest=request.expected_planning_input_digest,
                    input_summary=None,
                    error=error,
                )
        planning_input, early_response = _prepare_generation(
            snapshot=snapshot,
            request=request,
            store=store,
        )
        if early_response is not None:
            return early_response
        if planning_input is None:
            return _planning_generation_failure_response(
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
                planning_input_digest=request.expected_planning_input_digest,
                input_summary=None,
                error=RuntimeError("Planning preparation returned no input or blocker."),
            )
        # A changed digest is the normal re-plan path after fresh metrics,
        # inventory or knowledge arrive.  The command accepts only the exact
        # snapshot validated above; once queued, the worker must not rebuild a
        # potentially hanging prerequisite before it can begin or fail.
        result = ContentPlanningProposalResponse(
            status="generating",
            work_item_id=planning_input.work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=content_planning_input_summary(planning_input),
            runtime=ContentCodexRuntimeTrace(
                status="not_started",
                run_id=f"planning_generation_{uuid4().hex}",
            ),
            safe_next_step="Plan jest przygotowywany; ten widok odświeży się po zakończeniu.",
        )
        outcome = store.enqueue_pending(
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            response=result,
        )
        if outcome == "existing":
            queued = store.queued_response(
                work_item_id,
                request.service_card_id,
                request.expected_planning_input_digest,
            )
            if queued is not None:
                result = queued
        if outcome == "in_flight":
            active = store.active_generation_response(
                work_item_id,
                request.service_card_id,
                excluding_digest=request.expected_planning_input_digest,
            )
            result = ContentPlanningProposalResponse(
                status="blocked",
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
                runtime=active.runtime if active is not None else result.runtime,
                retry_after_seconds=5,
                blockers=[
                    ContentPlanningProposalBlocker(
                        code="runtime_blocked",
                        label="Plan jest już przygotowywany",
                        reason=(
                            "Dla tej strony i usługi działa już generowanie z innego "
                            "dokładnego wejścia. Nie uruchamiamy równoległego turnu Codexa."
                        ),
                        next_step="Poczekaj na zakończenie bieżącej próby i odśwież stan planu.",
                        source_codes=[
                            active.runtime.run_id
                            if active is not None and active.runtime.run_id
                            else "planning_generation_in_flight"
                        ],
                    )
                ],
                safe_next_step="Poczekaj kilka sekund i odśwież stan planu.",
            )
        return _schedule_queued_planning_generation(
            outcome=outcome,
            result=result,
            work_item_id=work_item_id,
            request=request,
            snapshot_loader=snapshot_loader,
            store=store,
        )


def _schedule_queued_planning_generation(
    *,
    outcome: PlanningEnqueueOutcome,
    result: ContentPlanningProposalResponse,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    snapshot_loader: ContentPlanningSnapshotLoader,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse:
    if outcome not in {"queued", "existing"}:
        return result
    claim_store = content_planning_generation_claim_store()
    claim_owner = (
        result.runtime.run_id
        if result.runtime is not None and result.runtime.run_id is not None
        else f"planning_generation_{uuid4().hex}"
    )
    claim = claim_store.claim(
        work_item_id=work_item_id,
        service_card_id=request.service_card_id,
        planning_input_digest=request.expected_planning_input_digest,
        claim_owner=claim_owner,
    )
    if claim.outcome != "acquired":
        return result
    try:
        _PLANNING_GENERATION_EXECUTOR.submit(
            _run_queued_planning_generation,
            work_item_id,
            request,
            snapshot_loader,
            claim_store,
            claim_owner,
            claim.claim_version,
        )
    except Exception as error:
        result = _planning_generation_failure_response(
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            input_summary=_queued_input_summary(
                store=store,
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
                planning_input_digest=request.expected_planning_input_digest,
            ),
            error=error,
        )
        result = _save_terminal_response_safely(
            store,
            result,
            job_planning_input_digest=request.expected_planning_input_digest,
            claim_version=claim.claim_version,
        )
        claim_store.finish(
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            claim_owner=claim_owner,
            claim_version=claim.claim_version,
            status="failed",
        )
    return result


def _run_queued_planning_generation(
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    snapshot_loader: ContentPlanningSnapshotLoader,
    claim_store: ContentPlanningGenerationClaimStore,
    claim_owner: str,
    claim_version: int,
) -> ContentPlanningProposalResponse:
    store = content_planning_proposal_store()
    claim_status: PlanningGenerationClaimFinalStatus = "failed"
    try:
        # The request digest is the immutable guard. Rebuild the snapshot in
        # the worker so a context change between enqueue and execution becomes
        # a typed stale response before Codex starts.
        snapshot = snapshot_loader(work_item_id)
        result = generate_content_planning_proposal(
            snapshot=snapshot,
            request=request,
            client=_planning_codex_client(),
            store=store,
            run_store=local_state_store(),
        )
    except Exception as error:
        result = _planning_generation_failure_response(
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            input_summary=_queued_input_summary(
                store=store,
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
                planning_input_digest=request.expected_planning_input_digest,
            ),
            error=error,
        )
    try:
        terminal_response = _save_terminal_response_safely(
            store,
            result,
            job_planning_input_digest=request.expected_planning_input_digest,
            claim_version=claim_version,
        )
        if terminal_response.status in {"created", "idempotent", "ready"}:
            claim_status = "finished"
    finally:
        claim_store.finish(
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            claim_owner=claim_owner,
            claim_version=claim_version,
            status=claim_status,
        )
    return terminal_response


def _save_terminal_response_safely(
    store: ContentPlanningProposalStore,
    response: ContentPlanningProposalResponse,
    *,
    job_planning_input_digest: str,
    claim_version: int,
) -> ContentPlanningProposalResponse:
    """Never turn a durable-job failure into an unhandled route/thread error."""
    try:
        outcome = store.save_terminal_response(
            response,
            job_planning_input_digest=job_planning_input_digest,
            claim_version=claim_version,
        )
    except Exception:
        # The queued row remains recoverable by stale-job retry. The typed
        # failure is still returned to the caller when this runs in the route.
        return response
    if outcome == "claim_stale":
        return _planning_generation_claim_stale_response(response)
    return response


def _planning_generation_claim_stale_response(
    response: ContentPlanningProposalResponse,
) -> ContentPlanningProposalResponse:
    blocker = ContentPlanningProposalBlocker(
        code="generation_claim_stale",
        label="Wynik pochodzi z nieaktualnej próby",
        reason=(
            "Nowszy worker przejął wygasły claim; spóźniony wynik tej próby "
            "został odrzucony."
        ),
        next_step="Poczekaj na wynik bieżącej próby i odśwież stan planu.",
    )
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=response.work_item_id,
        service_card_id=response.service_card_id,
        planning_input_digest=response.planning_input_digest,
        input_summary=response.input_summary,
        runtime=response.runtime,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _planning_generation_failure_response(
    *,
    work_item_id: str,
    service_card_id: str,
    planning_input_digest: str,
    input_summary: ContentPlanningInputSummary | None,
    error: Exception,
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status="failed",
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=(planning_input_digest if input_summary is not None else None),
        input_summary=input_summary,
        blockers=[
            ContentPlanningProposalBlocker(
                code="runtime_failed",
                label="Nie udało się przygotować planu",
                reason=(
                    "Przygotowanie aktualnego snapshotu albo uruchomienie "
                    "Codexa zakończyło się błędem."
                ),
                next_step="Odśwież gotowość i spróbuj ponownie; plan nie został zapisany.",
                source_codes=[type(error).__name__],
            )
        ],
        safe_next_step="Odśwież gotowość i spróbuj ponownie; plan nie został zapisany.",
    )


def _queued_input_summary(
    *,
    store: ContentPlanningProposalStore,
    work_item_id: str,
    service_card_id: str,
    planning_input_digest: str,
) -> ContentPlanningInputSummary | None:
    """Keep the queued exact input visible without retrying a failed read."""

    queued = store.queued_response(
        work_item_id,
        service_card_id,
        planning_input_digest,
    )
    return None if queued is None else queued.input_summary


__all__ = ["register_content_planning_proposal_routes"]
