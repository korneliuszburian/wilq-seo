"""Shared orchestration spine for initial content drafts.

The callers own readiness, copy, and persistence policy.  This module owns the
ordered run -> turn -> alter -> persist lifecycle and its terminal branches.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
)
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_alteration import alter_draft_towards_persistence
from wilq.content.drafts.draft_assurance import ContentDraftAssuranceReceipt
from wilq.content.drafts.draft_assurance_runtime import ContentDraftAssuranceFailure
from wilq.content.drafts.initial_draft_run import (
    finish_initial_draft_run,
    safe_initial_draft_run_error,
    start_initial_draft_run,
)
from wilq.content.drafts.initial_draft_runtime import (
    InitialDraftTerminalHook,
    InitialDraftTurnFailure,
    InitialDraftTurnGoal,
    execute_initial_draft_turn,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
    ContentInitialDraftResponse,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


@dataclass(frozen=True, slots=True)
class InitialDraftRunMetadata:
    """Run identity supplied by a caller-specific adapter."""

    work_item_id: str
    evidence_ids: list[str]
    source_material_ids: list[str]
    proposal_id: str
    planning_digest: str | None
    planning_input_digest: str
    context_digest: str | None
    endpoint_path: str | None
    prompt: str | None
    run_id: str | None = None
    run_id_prefix: str | None = None
    hook: str | None = None


class InitialDraftTurnRequestBuilder(Protocol):
    def __call__(self) -> CodexAppServerStructuredTurnRequest: ...


class InitialDraftOutputBlocker(Protocol):
    def __call__(
        self, output: ContentInitialDraftModelOutput
    ) -> ContentInitialDraftBlocker | None: ...


class InitialDraftResponseBuilder(Protocol):
    def __call__(
        self,
        *,
        status: Literal["blocked", "failed", "conflict"],
        blocker: ContentInitialDraftBlocker,
        run: CodexRun,
        runtime: ContentCodexRuntimeTrace,
    ) -> ContentInitialDraftResponse: ...


class InitialDraftPersistenceAdapter(Protocol):
    def __call__(
        self,
        *,
        output: ContentInitialDraftModelOutput,
        runtime: ContentCodexRuntimeTrace,
        run: CodexRun,
        regulatory_assurance: ContentDraftAssuranceReceipt | None,
    ) -> ContentInitialDraftResponse: ...


@dataclass(frozen=True, slots=True)
class InitialDraftPipelineInputs:
    """Caller projection at the one initial-draft pipeline seam."""

    planning_input: ContentPlanningInput
    proposal: ContentPlanningProposal
    preflight_response: ContentInitialDraftResponse | None
    turn_request: InitialDraftTurnRequestBuilder
    turn_goal: InitialDraftTurnGoal
    run: InitialDraftRunMetadata
    output_blocker: InitialDraftOutputBlocker
    response: InitialDraftResponseBuilder
    persist: InitialDraftPersistenceAdapter
    base_revision_id: str | None = None
    output_transform: Callable[[ContentInitialDraftModelOutput], ContentInitialDraftModelOutput] = (
        lambda output: output
    )
    start_run: Callable[..., CodexRun] = start_initial_draft_run
    terminal_hook: InitialDraftTerminalHook = finish_initial_draft_run
    execute_turn: Callable[..., Any] = execute_initial_draft_turn
    alter: Callable[..., Any] = alter_draft_towards_persistence


def generate_initial_draft(
    *,
    inputs: InitialDraftPipelineInputs,
    client: CodexAppServerClientProtocol,
    workflow_store: object,
    run_store: LocalStateStore,
) -> ContentInitialDraftResponse:
    """Run the shared initial-draft lifecycle, including every terminal branch."""

    if inputs.preflight_response is not None:
        return inputs.preflight_response

    try:
        turn_request = inputs.turn_request()
    except Exception:
        run = _start_run(inputs, run_store, prompt=None)
        inputs.terminal_hook(run_store, run, status="failed", error="runtime_failed")
        return inputs.response(
            status="failed",
            blocker=_runtime_failure_blocker(inputs.turn_goal),
            run=run,
            runtime=ContentCodexRuntimeTrace(status="failed"),
        )

    run = _start_run(inputs, run_store, prompt=turn_request.instruction)
    execution = inputs.execute_turn(
        turn_request=turn_request,
        client=client,
        run=run,
        run_store=run_store,
        goal=inputs.turn_goal,
        on_terminal=inputs.terminal_hook,
    )
    if isinstance(execution, ContentInitialDraftResponse):
        return execution
    if isinstance(execution, InitialDraftTurnFailure):
        return inputs.response(
            status=execution.status,
            blocker=execution.blocker,
            run=run,
            runtime=execution.trace,
        )
    output, runtime = execution
    output = inputs.output_transform(output)
    altered = inputs.alter(
        planning_input=inputs.planning_input,
        proposal=inputs.proposal,
        output=output,
        trace=runtime,
        client=client,
        run_store=run_store,
        output_blocker=inputs.output_blocker,
    )
    if altered.status == "blocked":
        if altered.blocker is None:
            raise RuntimeError("Blocked initial draft alteration requires a blocker.")
        return _finish_alteration_block(
            inputs, run_store, run, altered.blocker, altered.trace or runtime
        )
    if altered.status == "assurance_failure":
        assurance = altered.assurance
        if not isinstance(assurance, ContentDraftAssuranceFailure):
            raise RuntimeError("Failed initial draft assurance requires its failure payload.")
        blocker = ContentInitialDraftBlocker(
            code=assurance.code,
            label=assurance.label,
            reason=assurance.reason,
            next_step=assurance.next_step,
            source_codes=assurance.source_codes,
        )
        return _finish_alteration_block(inputs, run_store, run, blocker, altered.trace or runtime)
    if altered.output is None or altered.trace is None:
        raise RuntimeError("Initial draft alteration returned no output or trace.")
    return inputs.persist(
        output=altered.output,
        runtime=altered.trace,
        run=run,
        regulatory_assurance=altered.assurance,
    )


def _start_run(
    inputs: InitialDraftPipelineInputs,
    run_store: LocalStateStore,
    *,
    prompt: str | None,
) -> CodexRun:
    metadata = inputs.run
    return inputs.start_run(
        run_store,
        work_item_id=metadata.work_item_id,
        evidence_ids=metadata.evidence_ids,
        source_material_ids=metadata.source_material_ids,
        proposal_id=metadata.proposal_id,
        planning_digest=metadata.planning_digest,
        planning_input_digest=metadata.planning_input_digest,
        context_digest=metadata.context_digest,
        run_id=metadata.run_id,
        run_id_prefix=metadata.run_id_prefix,
        hook=metadata.hook,
        endpoint_path=metadata.endpoint_path,
        prompt=prompt,
    )


def _finish_alteration_block(
    inputs: InitialDraftPipelineInputs,
    run_store: LocalStateStore,
    run: CodexRun,
    blocker: ContentInitialDraftBlocker,
    runtime: ContentCodexRuntimeTrace,
) -> ContentInitialDraftResponse:
    inputs.terminal_hook(
        run_store,
        run,
        status="blocked",
        error=safe_initial_draft_run_error(blocker),
    )
    return inputs.response(status="blocked", blocker=blocker, run=run, runtime=runtime)


def _runtime_failure_blocker(goal: InitialDraftTurnGoal) -> ContentInitialDraftBlocker:
    from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker
    from wilq.content.operator_copy import build_blocker

    copy = goal.runtime_failure
    return build_blocker(
        ContentInitialDraftBlocker,
        code="runtime_failed",
        label=copy.label,
        reason=copy.reason,
        next_step=copy.next_step,
    )


__all__ = [
    "InitialDraftPipelineInputs",
    "InitialDraftRunMetadata",
    "generate_initial_draft",
]
