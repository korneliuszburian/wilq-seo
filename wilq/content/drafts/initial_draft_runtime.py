"""Shared runtime policy for initial content-draft turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.codex_turn import runtime_trace
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.initial_draft_run import safe_initial_draft_run_error
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftBlockerCode,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
)
from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore

InitialDraftMismatchMode = Literal["refresh", "new_page"]
InitialDraftRequestMismatch = Literal["planning_not_generated", "proposal_mismatch"]


@dataclass(frozen=True, slots=True)
class InitialDraftFailureCopy:
    label: str
    reason: str
    next_step: str


@dataclass(frozen=True, slots=True)
class InitialDraftTurnGoal:
    runtime_failure: InitialDraftFailureCopy
    invalid_structured_output: InitialDraftFailureCopy
    include_runtime_source_codes: bool


@dataclass(frozen=True, slots=True)
class InitialDraftTurnFailure:
    status: Literal["blocked", "failed"]
    trace: ContentCodexRuntimeTrace
    blocker: ContentInitialDraftBlocker
    error: str


class InitialDraftTerminalHook(Protocol):
    def __call__(
        self,
        run_store: LocalStateStore,
        run: CodexRun,
        *,
        status: Literal["blocked", "failed"],
        error: str,
    ) -> CodexRun | None: ...


def build_initial_draft_blocker(
    code: ContentInitialDraftBlockerCode,
    label: str,
    reason: str,
    next_step: str,
    *,
    source_codes: list[str] | None = None,
) -> ContentInitialDraftBlocker:
    """Build the public blocker without changing caller-specific copy."""

    return build_blocker(
        ContentInitialDraftBlocker,
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
        source_codes=source_codes,
    )


def initial_draft_request_mismatch(
    *,
    proposal: ContentPlanningProposal,
    request: ContentInitialDraftRequest,
    planning_input: ContentPlanningInput | None,
    mode: InitialDraftMismatchMode,
) -> InitialDraftRequestMismatch | None:
    """Compare a draft request using the historical checks for its caller."""

    if mode == "refresh" and (
        proposal.generation_status != "codex_generated" or proposal.proposal_id is None
    ):
        return "planning_not_generated"
    if (
        proposal.proposal_id != request.expected_proposal_id
        or proposal.planning_digest != request.expected_planning_digest
        or proposal.planning_input_digest != request.expected_planning_input_digest
    ):
        return "proposal_mismatch"
    if mode == "refresh":
        return None
    if planning_input is None:
        raise ValueError("New-page initial draft mismatch check requires planning input.")
    if (
        planning_input.goal != "new_page"
        or planning_input.work_item_id != proposal.work_item_id
        or planning_input.planning_input_digest != request.expected_planning_input_digest
        or planning_input.confirmed_service_card_id != proposal.service_card_id
    ):
        return "proposal_mismatch"
    return None


def execute_initial_draft_turn(
    *,
    turn_request: CodexAppServerStructuredTurnRequest,
    client: CodexAppServerClientProtocol,
    run: CodexRun,
    run_store: LocalStateStore,
    goal: InitialDraftTurnGoal,
    on_terminal: InitialDraftTerminalHook,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | InitialDraftTurnFailure:
    """Execute one initial-draft turn and own its complete failure ladder."""

    try:
        turn = client.run_structured_turn(turn_request)
    except Exception:
        turn = CodexAppServerTurnResult(status="failed")
    trace = runtime_trace(turn)
    if turn.status != "completed" or turn.output_text is None:
        code: ContentInitialDraftBlockerCode = (
            "runtime_blocked" if turn.status == "blocked" else "runtime_failed"
        )
        status: Literal["blocked", "failed"] = "blocked" if code == "runtime_blocked" else "failed"
        copy = goal.runtime_failure
        blocker = build_blocker(
            ContentInitialDraftBlocker,
            code=code,
            label=copy.label,
            reason=copy.reason,
            next_step=copy.next_step,
            source_codes=(
                [item.code for item in turn.blockers] if goal.include_runtime_source_codes else None
            ),
        )
        error = safe_initial_draft_run_error(blocker)
        on_terminal(run_store, run, status=status, error=error)
        return InitialDraftTurnFailure(
            status=status,
            trace=trace,
            blocker=blocker,
            error=error,
        )
    try:
        return ContentInitialDraftModelOutput.model_validate_json(turn.output_text), trace
    except ValueError:
        copy = goal.invalid_structured_output
        blocker = build_blocker(
            ContentInitialDraftBlocker,
            code="invalid_structured_output",
            label=copy.label,
            reason=copy.reason,
            next_step=copy.next_step,
        )
        error = safe_initial_draft_run_error(blocker)
        on_terminal(run_store, run, status="blocked", error=error)
        return InitialDraftTurnFailure(
            status="blocked",
            trace=trace,
            blocker=blocker,
            error=error,
        )


__all__ = [
    "InitialDraftFailureCopy",
    "InitialDraftMismatchMode",
    "InitialDraftRequestMismatch",
    "InitialDraftTerminalHook",
    "InitialDraftTurnFailure",
    "InitialDraftTurnGoal",
    "build_initial_draft_blocker",
    "execute_initial_draft_turn",
    "initial_draft_request_mismatch",
]
