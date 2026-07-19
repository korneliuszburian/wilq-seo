from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.wilq_api.routers.content_codex_proposal import (
    content_codex_app_server_client,
)
from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.codex_section_proposal_contracts import ContentCodexRuntimeTrace
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputSummary,
    build_content_planning_input,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal import (
    _snapshot_with_explicit_service_selection,
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
from wilq.content.planning.runtime_contract import planning_codex_timeout_seconds
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
            current = read_content_planning_proposal(
                snapshot=snapshot_loader(work_item_id),
                store=store,
            )
            stale_mapping = (
                request.regenerate_stale_mapping
                or (
                    current.status == "stale"
                    and any(
                        blocker.label == "Mapa istniejącej strony wymaga odświeżenia"
                        for blocker in current.blockers
                    )
                )
            )
            if not stale_mapping:
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
            request = request.model_copy(update={"regenerate_stale_mapping": True})
        # A changed digest is the normal re-plan path after fresh metrics,
        # inventory or knowledge arrive.  The background generator validates
        # the request against the rebuilt snapshot and returns typed stale_input
        # when the operator supplied a digest that is not current.  The
        # generator owns the idempotency decision after it has checked the
        # current mapping contract; a router-level store shortcut would make
        # stale proposals impossible to regenerate.
        result = ContentPlanningProposalResponse(
            status="generating",
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
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
                    planning_input_digest=request.expected_planning_input_digest,
                    input_summary=_planning_input_summary_for_failure(
                        snapshot_loader=snapshot_loader,
                        work_item_id=work_item_id,
                        service_card_id=request.service_card_id,
                    ),
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
            planning_input_digest=request.expected_planning_input_digest,
            input_summary=_planning_input_summary_for_failure(
                snapshot_loader=snapshot_loader,
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
            ),
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


def _planning_input_summary_for_failure(
    *,
    snapshot_loader: ContentPlanningSnapshotLoader,
    work_item_id: str,
    service_card_id: str,
) -> ContentPlanningInputSummary | None:
    """Preserve the exact input context when a queued run fails before Codex."""

    try:
        snapshot = _snapshot_with_explicit_service_selection(
            snapshot_loader(work_item_id),
            service_card_id,
        )
        result = build_content_planning_input(
            snapshot,
            service_card_id=service_card_id,
        )
        if result.planning_input is None:
            return None
        return content_planning_input_summary(result.planning_input)
    except Exception:
        return None


__all__ = ["register_content_planning_proposal_routes"]
