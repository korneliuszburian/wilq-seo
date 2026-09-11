"""Typed public responses for planning preparation, runtime, and stale input states."""

from __future__ import annotations

from typing import Literal

from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBlocker,
    ContentPlanningInputSummary,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse


def unexpected_planning_input_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
) -> ContentPlanningProposalResponse:
    return blocked_response(
        snapshot.preflight.item.id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        planning_input_digest=None,
        blockers=[unexpected_runtime_blocker()],
    )


def unexpected_runtime_blocker() -> ContentPlanningProposalBlocker:
    return build_blocker(
        ContentPlanningProposalBlocker,
        code="runtime_failed",
        label="Planowanie nie zwróciło kompletnego wejścia",
        reason="WILQ nie otrzymał kompletnego stanu potrzebnego do bezpiecznego planowania.",
        next_step="Odśwież workspace i uruchom nową próbę dopiero po sprawdzeniu blockerów.",
    )


def runtime_failure_response(
    planning_input: ContentPlanningInput,
    blocker: ContentPlanningProposalBlocker,
    *,
    status: Literal["blocked", "failed"],
    trace: ContentCodexRuntimeTrace | None = None,
    run_id: str | None = None,
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status=status,
        work_item_id=planning_input.work_item_id,
        content_kind=planning_input.content_kind,
        service_card_id=planning_input.confirmed_service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        runtime=(
            trace.model_copy(update={"run_id": run_id})
            if trace is not None and run_id is not None
            else trace or ContentCodexRuntimeTrace(status="failed", run_id=run_id)
        ),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def blocked_from_input(
    work_item_id: str,
    service_card_id: str | None,
    blockers: list[ContentPlanningInputBlocker],
    *,
    planning_input_digest: str | None = None,
    input_summary: ContentPlanningInputSummary | None = None,
    content_kind: Literal["service", "editorial"] = "service",
) -> ContentPlanningProposalResponse:
    return blocked_response(
        work_item_id,
        content_kind=content_kind,
        service_card_id=service_card_id,
        planning_input_digest=planning_input_digest,
        input_summary=input_summary,
        blockers=[
            build_blocker(
                ContentPlanningProposalBlocker,
                code=item.code,
                label=item.label,
                reason=item.reason,
                next_step=item.next_step,
            )
            for item in blockers
        ],
    )


def blocked_response(
    work_item_id: str,
    *,
    service_card_id: str | None,
    planning_input_digest: str | None,
    blockers: list[ContentPlanningProposalBlocker],
    input_summary: ContentPlanningInputSummary | None = None,
    content_kind: Literal["service", "editorial"] = "service",
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=work_item_id,
        content_kind=content_kind,
        service_card_id=service_card_id,
        planning_input_digest=planning_input_digest,
        input_summary=input_summary,
        blockers=blockers,
        safe_next_step=blockers[0].next_step,
    )


def stale_input_blocker() -> ContentPlanningProposalBlocker:
    return build_blocker(
        ContentPlanningProposalBlocker,
        code="stale_input",
        label="Wejście planu zmieniło się",
        reason="Inventory, usługa, wiedza albo metryki mają inny exact digest.",
        next_step="Odśwież dane i uruchom świadomie nową wersję planu.",
    )


def planning_runtime_blocker(source_codes: list[str]) -> tuple[str, str, str]:
    codes = set(source_codes)
    if "codex_response_stream_disconnected" in codes:
        return (
            "Połączenie z Codexem zostało przerwane",
            "Provider Codexa przerwał strumień odpowiedzi przed końcem tury; "
            "WILQ nie otrzymał bezpiecznego planu.",
            "Sprawdź status app-servera i połączenie, a potem uruchom nową próbę; "
            "WILQ nic nie zapisał.",
        )
    if "codex_timeout" in codes:
        return (
            "Codex nie zakończył planowania w limicie czasu",
            "App-server nie zwrócił bezpiecznego planu przed końcem ograniczonego okna.",
            "Sprawdź status Codexa i uruchom nową próbę; WILQ nic nie zapisał.",
        )
    return (
        "Codex nie zakończył planowania",
        "Lokalny app-server zakończył turę bez kompletnego, bezpiecznego planu.",
        "Sprawdź status Codexa i uruchom nową próbę; WILQ nic nie zapisał.",
    )


__all__ = [
    "blocked_from_input",
    "blocked_response",
    "planning_runtime_blocker",
    "runtime_failure_response",
    "stale_input_blocker",
    "unexpected_planning_input_response",
    "unexpected_runtime_blocker",
]
