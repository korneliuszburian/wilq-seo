from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from os import environ

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import (
    content_codex_app_server_client,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.planning.generated_proposal import (
    generate_content_planning_proposal,
    read_content_planning_proposal,
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
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
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
# request budget.  Keep the model turn bounded at two minutes; a timeout is a
# typed runtime blocker and can be retried from the same exact input digest.
# The first useful browser response remains the queued ``generating`` state.
_DEFAULT_PLANNING_TIMEOUT_SECONDS = 120.0


def _planning_codex_client():
    """Keep planning bounded without changing draft/review runtime budgets.

    Test and local harness clients are returned unchanged; only the real stdio
    adapter receives the planning-specific deadline.
    """

    client = content_codex_app_server_client()
    if not isinstance(client, StdioCodexAppServerClient):
        return client
    try:
        timeout_seconds = float(
            environ.get(
                "WILQ_PLANNING_CODEX_TIMEOUT_SECONDS",
                str(_DEFAULT_PLANNING_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        timeout_seconds = _DEFAULT_PLANNING_TIMEOUT_SECONDS
    return StdioCodexAppServerClient(timeout_seconds=max(5.0, timeout_seconds))


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
        pending = content_planning_proposal_store().latest_generation_response(work_item_id)
        if pending is not None:
            return pending
        return read_content_planning_proposal(
            snapshot=snapshot_loader(work_item_id),
            store=content_planning_proposal_store(),
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
        existing = store.for_input(
            work_item_id,
            request.service_card_id,
            request.expected_planning_input_digest,
        )
        if existing is not None:
            return ContentPlanningProposalResponse(
                status="idempotent",
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
                proposal=existing,
                safe_next_step=(
                    "Plan już istnieje dla tego exact wejścia; odczytano wersję "
                    "bez ponownego uruchamiania Codexa."
                ),
            )
        # A changed digest is the normal re-plan path after fresh metrics,
        # inventory or knowledge arrive.  The background generator validates
        # the request against the rebuilt snapshot and returns typed stale_input
        # when the operator supplied a digest that is not current.  Blocking
        # here merely because an older proposal exists makes legitimate
        # refreshes impossible and leaves the marketer stuck on stale copy.
        result = ContentPlanningProposalResponse(
            status="generating",
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
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
        if outcome == "queued":
            try:
                _PLANNING_GENERATION_EXECUTOR.submit(
                    _run_queued_planning_generation,
                    work_item_id,
                    request,
                    snapshot_loader,
                )
            except Exception as error:
                result = _planning_generation_failure_response(
                    work_item_id=work_item_id,
                    service_card_id=request.service_card_id,
                    error=error,
                )
                _save_terminal_response_safely(store, result)
        return result


def _run_queued_planning_generation(
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    snapshot_loader: ContentPlanningSnapshotLoader,
) -> None:
    store = content_planning_proposal_store()
    try:
        result = generate_content_planning_proposal(
            snapshot=snapshot_loader(work_item_id),
            request=request,
            client=_planning_codex_client(),
            store=store,
            run_store=local_state_store(),
        )
    except Exception as error:
        result = _planning_generation_failure_response(
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            error=error,
        )
    _save_terminal_response_safely(store, result)


def _save_terminal_response_safely(
    store: ContentPlanningProposalStore,
    response: ContentPlanningProposalResponse,
) -> None:
    """Never turn a durable-job failure into an unhandled route/thread error."""
    try:
        store.save_terminal_response(response)
    except Exception:
        # The queued row remains recoverable by stale-job retry. The typed
        # failure is still returned to the caller when this runs in the route.
        return


def _planning_generation_failure_response(
    *,
    work_item_id: str,
    service_card_id: str,
    error: Exception,
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status="failed",
        work_item_id=work_item_id,
        service_card_id=service_card_id,
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


__all__ = ["register_content_planning_proposal_routes"]
