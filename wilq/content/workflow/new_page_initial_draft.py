from __future__ import annotations

import json
from typing import Literal
from uuid import uuid4

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlockerCode,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_output_schema
from wilq.content.workflow.new_page import ContentNewPageBrief, ContentNewPagePlanningFoundation
from wilq.content.workflow.new_page_document import (
    ContentNewPageCanonicalDocumentWorkspace,
)
from wilq.content.workflow.new_page_revision import append_new_page_initial_revision
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.store import ContentWorkflowStore
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


def generate_new_page_initial_draft(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    proposal: ContentPlanningProposal,
    workspace: ContentNewPageCanonicalDocumentWorkspace,
    request: ContentInitialDraftRequest,
    client: CodexAppServerClientProtocol,
    workflow_store: ContentWorkflowStore,
    run_store: LocalStateStore,
    endpoint_path: str,
) -> ContentInitialDraftResponse:
    if workspace.status != "ready_for_document":
        return _blocked(workspace, proposal, "planning_not_ready", workspace.safe_next_step)
    if _request_mismatch(proposal, request):
        return _blocked(
            workspace, proposal, "proposal_mismatch", "Odśwież dokładny plan przed generowaniem."
        )
    if (
        workflow_store.load_draft_revision_state(foundation.work_item_id).latest_revision
        is not None
    ):
        return _blocked(
            workspace,
            proposal,
            "revision_already_exists",
            "Otwórz zapisaną rewizję zamiast tworzyć drugi pierwszy dokument.",
        )
    run = _start_run(proposal, endpoint_path, run_store)
    execution = _execute_turn(brief, proposal, client, run, run_store, workspace)
    if isinstance(execution, ContentInitialDraftResponse):
        return execution
    output, runtime = execution
    completed = run.model_copy(update={"status": "completed", "completed_at": utc_now()})
    try:
        result = append_new_page_initial_revision(
            brief=brief,
            foundation=foundation,
            proposal=proposal,
            expected_proposal_id=request.expected_proposal_id,
            expected_planning_digest=request.expected_planning_digest,
            expected_planning_input_digest=request.expected_planning_input_digest,
            output=output,
            completed_run=completed,
            requested_by=request.requested_by,
            store=workflow_store,
        )
    except ValueError:
        _finish_run(run_store, run, status="blocked", error="document_scope_mismatch")
        return _blocked(
            workspace,
            proposal,
            "document_scope_mismatch",
            "Wynik nie odpowiada dokładnemu zatwierdzonemu planowi; nic nie zapisano.",
            run.id,
            runtime,
        )
    if result.revision is None:
        _finish_run(run_store, run, status="blocked", error="revision_conflict")
        return _blocked(
            workspace,
            proposal,
            "revision_conflict",
            "Rewizja powstała równolegle; odśwież workspace.",
            run.id,
            runtime,
            status="conflict",
        )
    return ContentInitialDraftResponse(
        status="created",
        work_item_id=foundation.work_item_id,
        proposal_id=proposal.proposal_id,
        run_id=run.id,
        revision=result.revision,
        runtime=runtime,
        safe_next_step="Przeczytaj dokładną rewizję i zapisz decyzję człowieka.",
    )


def _start_run(
    proposal: ContentPlanningProposal, endpoint_path: str, run_store: LocalStateStore
) -> CodexRun:
    return run_store.save_codex_run(
        CodexRun(
            id=f"codex_content_new_page_draft_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_new_page_initial_draft",
            source="wilq_api",
            status="started",
            used_endpoints=[endpoint_path],
            evidence_ids=proposal.evidence_ids,
            proposal_id=proposal.proposal_id,
            planning_input_digest=proposal.planning_input_digest,
        )
    )


def _execute_turn(
    brief: ContentNewPageBrief,
    proposal: ContentPlanningProposal,
    client: CodexAppServerClientProtocol,
    run: CodexRun,
    run_store: LocalStateStore,
    workspace: ContentNewPageCanonicalDocumentWorkspace,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | ContentInitialDraftResponse:
    turn: CodexAppServerTurnResult | None
    try:
        turn = client.run_structured_turn(_turn_request(brief, proposal))
    except Exception:
        turn = None
    if turn is None or turn.status != "completed" or turn.output_text is None:
        code: Literal["runtime_blocked", "runtime_failed"] = (
            "runtime_blocked"
            if turn is not None and turn.status == "blocked"
            else "runtime_failed"
        )
        _finish_run(
            run_store,
            run,
            status="blocked" if code == "runtime_blocked" else "failed",
            error=code,
        )
        return _blocked(
            workspace,
            proposal,
            code,
            "Codex nie zwrócił poprawnego dokumentu; nic nie zapisano.",
            run.id,
            _runtime_trace(turn),
            status="blocked" if code == "runtime_blocked" else "failed",
        )
    trace = _runtime_trace(turn)
    try:
        return ContentInitialDraftModelOutput.model_validate_json(turn.output_text), trace
    except ValueError:
        _finish_run(run_store, run, status="blocked", error="invalid_structured_output")
        return _blocked(
            workspace,
            proposal,
            "invalid_structured_output",
            "Codex zwrócił dokument poza ścisłym kontraktem; nic nie zapisano.",
            run.id,
            trace,
        )


def _finish_run(
    run_store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> None:
    run_store.save_codex_run(
        run.model_copy(update={"status": status, "completed_at": utc_now(), "error": error})
    )


def _runtime_trace(turn: CodexAppServerTurnResult | None) -> ContentCodexRuntimeTrace:
    if turn is None:
        return ContentCodexRuntimeTrace(status="failed")
    return ContentCodexRuntimeTrace(
        status=turn.status,
        thread_id=turn.thread_id,
        turn_id=turn.turn_id,
        event_methods=list(turn.event_methods),
        item_types=list(turn.item_types),
        external_call_attempted=turn.external_call_attempted,
    )


def _turn_request(
    brief: ContentNewPageBrief, proposal: ContentPlanningProposal
) -> CodexAppServerStructuredTurnRequest:
    return CodexAppServerStructuredTurnRequest(
        instruction=(
            "Napisz po polsku roboczy dokument nowej strony wyłącznie z zatwierdzonego "
            "planu. Nie zakładaj istniejącego URL-a, nie publikuj, nie wykonuj write i "
            "zwróć publish_ready=false. Zachowaj dokładne sekcje, FAQ, CTA i targety "
            "linków z planu. Zwróć tylko JSON zgodny ze schema."
        ),
        application_context=json.dumps(
            {
                "operation": "generate_new_page_initial_draft",
                "brief_id": brief.brief_id,
                "proposal_id": proposal.proposal_id,
                "do_not_write_vendor": True,
                "publish_ready": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        untrusted_context=json.dumps(
            {
                "brief": brief.model_dump(mode="json"),
                "generated_plan": proposal.model_dump(mode="json"),
                "document_scope": [
                    item.section_id for item in draftable_planning_sections(proposal.sections)
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        output_schema=initial_full_draft_output_schema(proposal),
    )


def _request_mismatch(
    proposal: ContentPlanningProposal, request: ContentInitialDraftRequest
) -> bool:
    return bool(
        proposal.proposal_id != request.expected_proposal_id
        or proposal.planning_digest != request.expected_planning_digest
        or proposal.planning_input_digest != request.expected_planning_input_digest
    )


def _blocked(
    workspace: ContentNewPageCanonicalDocumentWorkspace,
    proposal: ContentPlanningProposal,
    code: ContentInitialDraftBlockerCode,
    next_step: str,
    run_id: str | None = None,
    runtime: ContentCodexRuntimeTrace | None = None,
    status: Literal["blocked", "failed", "conflict"] = "blocked",
) -> ContentInitialDraftResponse:
    from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftBlocker

    return ContentInitialDraftResponse(
        status=status,
        work_item_id=workspace.work_item_id,
        proposal_id=proposal.proposal_id,
        run_id=run_id,
        runtime=runtime or ContentCodexRuntimeTrace(status="not_started"),
        blockers=[
            ContentInitialDraftBlocker(
                code=code,
                label="Nie utworzono dokumentu nowej strony",
                reason=next_step,
                next_step=next_step,
            )
        ],
        safe_next_step=next_step,
    )


__all__ = ["generate_new_page_initial_draft"]
