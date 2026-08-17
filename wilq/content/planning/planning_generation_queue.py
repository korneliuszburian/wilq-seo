"""Queue, claim, execution, and terminal policy for planning generation."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputSummary,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal import (
    _prepare_generation,
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
from wilq.storage.local_state import local_state_store

ContentPlanningSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
PlanningClientFactory = Callable[[], StdioCodexAppServerClient]

_PLANNING_GENERATION_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="wilq-content-plan",
)


def planning_codex_client(client_factory: PlanningClientFactory) -> StdioCodexAppServerClient:
    client = client_factory()
    if not isinstance(client, StdioCodexAppServerClient):
        return client
    return StdioCodexAppServerClient(timeout_seconds=planning_codex_timeout_seconds())


def prepare_planning_generation(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    snapshot_loader: ContentPlanningSnapshotLoader,
    store: ContentPlanningProposalStore,
) -> tuple[
    ContentPlanningInput | None,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse | None,
]:
    snapshot, request, existing_response = existing_planning_generation_state(
        work_item_id=work_item_id,
        request=request,
        snapshot_loader=snapshot_loader,
        store=store,
    )
    if existing_response is not None:
        return None, request, existing_response
    if snapshot is None:
        try:
            snapshot = snapshot_loader(work_item_id)
        except Exception as error:
            return (
                None,
                request,
                planning_generation_failure_response(
                    work_item_id=work_item_id,
                    service_card_id=request.service_card_id,
                    planning_input_digest=request.expected_planning_input_digest,
                    input_summary=None,
                    error=error,
                ),
            )
    planning_input, early_response = _prepare_generation(
        snapshot=snapshot,
        request=request,
        store=store,
    )
    if early_response is not None:
        return None, request, early_response
    if planning_input is None:
        return (
            None,
            request,
            planning_generation_failure_response(
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
                planning_input_digest=request.expected_planning_input_digest,
                input_summary=None,
                error=RuntimeError("Planning preparation returned no input or blocker."),
            ),
        )
    return planning_input, request, None


def existing_planning_generation_state(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    snapshot_loader: ContentPlanningSnapshotLoader,
    store: ContentPlanningProposalStore,
) -> tuple[
    ContentWorkItemWorkflowSnapshotResponse | None,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse | None,
]:
    existing = store.for_input(
        work_item_id, request.service_card_id, request.expected_planning_input_digest
    )
    if existing is None:
        return None, request, None
    snapshot = snapshot_loader(work_item_id)
    current = read_content_planning_proposal(snapshot=snapshot, store=store)
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
    stale_mapping = (
        current_is_exact_existing
        and current.status == "stale"
        and any(
            blocker.label == "Mapa istniejącej strony wymaga odświeżenia"
            for blocker in current.blockers
        )
    )
    if stale_mapping or request.regenerate_after_review:
        request = request.model_copy(update={"regenerate_stale_mapping": True})
    elif current_is_exact_existing and current.status in {"created", "idempotent", "ready"}:
        return (
            snapshot,
            request,
            current.model_copy(
                update={
                    "status": "idempotent",
                    "safe_next_step": (
                        "Plan już istnieje dla tego exact wejścia; odczytano wersję "
                        "bez ponownego uruchamiania Codexa."
                    ),
                }
            ),
        )
    elif not current_is_exact_existing or not request.regenerate_after_review:
        return snapshot, request, current
    return snapshot, request, None


def enqueue_planning_generation(
    *,
    planning_input: ContentPlanningInput,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    snapshot_loader: ContentPlanningSnapshotLoader,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse:
    result = planning_generation_generating_response(planning_input=planning_input, request=request)
    outcome = store.enqueue_pending(
        work_item_id=work_item_id,
        service_card_id=request.service_card_id,
        planning_input_digest=request.expected_planning_input_digest,
        response=result,
        allow_finished_reset=request.regenerate_stale_mapping,
    )
    if outcome == "existing":
        queued = store.queued_response(
            work_item_id, request.service_card_id, request.expected_planning_input_digest
        )
        if queued is not None:
            result = queued
    if outcome == "in_flight":
        active = store.active_generation_response(
            work_item_id,
            request.service_card_id,
            excluding_digest=request.expected_planning_input_digest,
        )
        result = planning_generation_in_flight_response(
            work_item_id=work_item_id, request=request, result=result, active=active
        )
    return schedule_queued_planning_generation(
        outcome=outcome,
        result=result,
        work_item_id=work_item_id,
        request=request,
        snapshot_loader=snapshot_loader,
        store=store,
    )


def planning_generation_generating_response(
    *, planning_input: ContentPlanningInput, request: ContentPlanningProposalRequest
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status="generating",
        work_item_id=planning_input.work_item_id,
        service_card_id=request.service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        runtime=ContentCodexRuntimeTrace(
            status="not_started", run_id=f"planning_generation_{uuid4().hex}"
        ),
        safe_next_step="Plan jest przygotowywany; ten widok odświeży się po zakończeniu.",
    )


def planning_generation_in_flight_response(
    *,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
    result: ContentPlanningProposalResponse,
    active: ContentPlanningProposalResponse | None,
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
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
                    "Dla tej strony i usługi działa już generowanie z innego dokładnego "
                    "wejścia. Nie uruchamiamy równoległego turnu Codexa."
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


def schedule_queued_planning_generation(
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
        if result.runtime and result.runtime.run_id
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
            run_queued_planning_generation,
            work_item_id,
            request,
            snapshot_loader,
            claim_store,
            claim_owner,
            claim.claim_version,
        )
    except Exception as error:
        result = planning_generation_failure_response(
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            input_summary=queued_input_summary(
                store=store,
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
                planning_input_digest=request.expected_planning_input_digest,
            ),
            error=error,
        )
        result = save_terminal_response_safely(
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


def run_queued_planning_generation(
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
        result = generate_content_planning_proposal(
            snapshot=snapshot_loader(work_item_id),
            request=request,
            client=planning_codex_client(_default_client_factory),
            store=store,
            run_store=local_state_store(),
        )
    except Exception as error:
        result = planning_generation_failure_response(
            work_item_id=work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            input_summary=queued_input_summary(
                store=store,
                work_item_id=work_item_id,
                service_card_id=request.service_card_id,
                planning_input_digest=request.expected_planning_input_digest,
            ),
            error=error,
        )
    try:
        terminal_response = save_terminal_response_safely(
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


def _default_client_factory() -> StdioCodexAppServerClient:
    from apps.api.wilq_api.routers.content_codex_runtime import content_codex_app_server_client

    return content_codex_app_server_client()


def save_terminal_response_safely(
    store: ContentPlanningProposalStore,
    response: ContentPlanningProposalResponse,
    *,
    job_planning_input_digest: str,
    claim_version: int,
) -> ContentPlanningProposalResponse:
    try:
        outcome = store.save_terminal_response(
            response,
            job_planning_input_digest=job_planning_input_digest,
            claim_version=claim_version,
        )
    except Exception:
        return response
    if outcome == "claim_stale":
        return planning_generation_claim_stale_response(response)
    return response


def planning_generation_claim_stale_response(
    response: ContentPlanningProposalResponse,
) -> ContentPlanningProposalResponse:
    blocker = ContentPlanningProposalBlocker(
        code="generation_claim_stale",
        label="Wynik pochodzi z nieaktualnej próby",
        reason="Nowszy worker przejął wygasły claim; spóźniony wynik tej próby został odrzucony.",
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


def planning_generation_failure_response(
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
        planning_input_digest=planning_input_digest if input_summary is not None else None,
        input_summary=input_summary,
        blockers=[
            ContentPlanningProposalBlocker(
                code="runtime_failed",
                label="Nie udało się przygotować planu",
                reason=(
                    "Przygotowanie aktualnego snapshotu albo uruchomienie Codexa "
                    "zakończyło się błędem."
                ),
                next_step="Odśwież gotowość i spróbuj ponownie; plan nie został zapisany.",
                source_codes=[type(error).__name__],
            )
        ],
        safe_next_step="Odśwież gotowość i spróbuj ponownie; plan nie został zapisany.",
    )


def queued_input_summary(
    *,
    store: ContentPlanningProposalStore,
    work_item_id: str,
    service_card_id: str,
    planning_input_digest: str,
) -> ContentPlanningInputSummary | None:
    queued = store.queued_response(work_item_id, service_card_id, planning_input_digest)
    return None if queued is None else queued.input_summary
