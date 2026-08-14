from __future__ import annotations

import json
from typing import Literal

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.codex_turn import runtime_trace
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_alteration import alter_draft_towards_persistence
from wilq.content.drafts.draft_assurance_runtime import ContentDraftAssuranceFailure
from wilq.content.drafts.fact_selection import approved_source_facts_by_section
from wilq.content.drafts.generated_claim_safety import (
    claim_safety_output,
    generated_claim_blocker,
    generated_claim_safety_issues,
)
from wilq.content.drafts.initial_draft_run import (
    safe_initial_draft_run_error,
    start_initial_draft_run,
    transition_initial_draft_run_if_status,
)
from wilq.content.drafts.initial_draft_validation import (
    document_scope_errors_for_planning_input,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftBlockerCode,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_output_schema
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
    StructuredDraftSignalQuality,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.target.new_page import (
    ContentNewPageBrief,
    ContentNewPagePlanningFoundation,
)
from wilq.content.workflow.target.new_page_document import (
    ContentNewPageCanonicalDocumentWorkspace,
)
from wilq.content.workflow.target.new_page_revision import append_new_page_initial_revision
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore

_NewPagePrePersistResult = (
    tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace]
    | ContentInitialDraftResponse
)


def generate_new_page_initial_draft(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    planning_input: ContentPlanningInput,
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
    if _request_mismatch(planning_input, proposal, request):
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
    try:
        turn_request = _turn_request(brief, planning_input, proposal)
    except Exception:
        run = start_initial_draft_run(
            run_store,
            work_item_id=proposal.work_item_id,
            evidence_ids=proposal.evidence_ids,
            source_material_ids=proposal.source_material_ids,
            proposal_id=request.expected_proposal_id,
            planning_digest=proposal.planning_digest,
            planning_input_digest=request.expected_planning_input_digest,
            context_digest=None,
            run_id_prefix="codex_content_new_page_draft_",
            hook="content_new_page_initial_draft",
            endpoint_path=endpoint_path,
            prompt=None,
        )
        transition_initial_draft_run_if_status(
            run_store,
            run,
            status="failed",
            error="runtime_failed",
        )
        return _blocked(
            workspace,
            proposal,
            "runtime_failed",
            "Codex nie zwrócił poprawnego dokumentu; nic nie zapisano.",
            run_id=run.id,
            runtime=ContentCodexRuntimeTrace(status="failed"),
            status="failed",
        )
    run = start_initial_draft_run(
        run_store,
        work_item_id=proposal.work_item_id,
        evidence_ids=proposal.evidence_ids,
        source_material_ids=proposal.source_material_ids,
        proposal_id=request.expected_proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=request.expected_planning_input_digest,
        context_digest=None,
        run_id_prefix="codex_content_new_page_draft_",
        hook="content_new_page_initial_draft",
        endpoint_path=endpoint_path,
        prompt=turn_request.instruction,
    )
    execution = _execute_turn(
        proposal,
        client,
        run,
        run_store,
        workspace,
        turn_request,
    )
    if isinstance(execution, ContentInitialDraftResponse):
        return execution
    output, runtime = execution
    prepared = _prepare_output_for_persistence(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        runtime=runtime,
        client=client,
        run=run,
        run_store=run_store,
        workspace=workspace,
    )
    if isinstance(prepared, ContentInitialDraftResponse):
        return prepared
    output, runtime = prepared
    return _persist_new_page_initial_draft(
        brief=brief,
        foundation=foundation,
        proposal=proposal,
        request=request,
        output=output,
        runtime=runtime,
        run=run,
        workflow_store=workflow_store,
        run_store=run_store,
        workspace=workspace,
    )


def _persist_new_page_initial_draft(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    proposal: ContentPlanningProposal,
    request: ContentInitialDraftRequest,
    output: ContentInitialDraftModelOutput,
    runtime: ContentCodexRuntimeTrace,
    run: CodexRun,
    workflow_store: ContentWorkflowStore,
    run_store: LocalStateStore,
    workspace: ContentNewPageCanonicalDocumentWorkspace,
) -> ContentInitialDraftResponse:
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
        transition_initial_draft_run_if_status(
            run_store,
            run,
            status="blocked",
            error="document_scope_mismatch",
        )
        return _blocked(
            workspace,
            proposal,
            "document_scope_mismatch",
            "Wynik nie odpowiada dokładnemu zatwierdzonemu planowi; nic nie zapisano.",
            run.id,
            runtime,
        )
    if result.revision is None:
        transition_initial_draft_run_if_status(
            run_store,
            run,
            status="blocked",
            error="revision_conflict",
        )
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


def _prepare_output_for_persistence(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    runtime: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    run: CodexRun,
    run_store: LocalStateStore,
    workspace: ContentNewPageCanonicalDocumentWorkspace,
) -> _NewPagePrePersistResult:
    altered = alter_draft_towards_persistence(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        trace=runtime,
        client=client,
        run_store=run_store,
        output_blocker=lambda candidate: _output_blocker(
            planning_input,
            proposal,
            candidate,
        ),
    )
    if altered.status == "blocked":
        if altered.blocker is None:
            raise RuntimeError("Blocked new-page draft alteration requires a blocker.")
        return _finish_quality_blocked(
            workspace=workspace,
            proposal=proposal,
            run=run,
            runtime=altered.trace or runtime,
            blocker=altered.blocker,
            run_store=run_store,
        )
    if altered.status == "assurance_failure":
        assurance = altered.assurance
        if not isinstance(assurance, ContentDraftAssuranceFailure):
            raise RuntimeError("Failed new-page draft assurance requires its failure payload.")
        return _finish_quality_blocked(
            workspace=workspace,
            proposal=proposal,
            run=run,
            runtime=altered.trace or runtime,
            blocker=ContentInitialDraftBlocker(
                code=assurance.code,
                label=assurance.label,
                reason=assurance.reason,
                next_step=assurance.next_step,
                source_codes=assurance.source_codes,
            ),
            run_store=run_store,
        )
    if altered.output is None:
        raise RuntimeError("Ready new-page draft alteration requires an output.")
    return altered.output, altered.trace or runtime


def _output_blocker(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
) -> ContentInitialDraftBlocker | None:
    errors = document_scope_errors_for_planning_input(
        planning_input,
        proposal,
        output,
        include_regulatory=False,
    )
    if errors:
        return ContentInitialDraftBlocker(
            code="document_scope_mismatch",
            label="Dokument nie odpowiada zatwierdzonemu planowi",
            reason="Model zmienił strukturę albo plan nie ma kompletnego lineage.",
            next_step="Odrzuć wynik; nie naprawiaj struktury ręcznie po generowaniu.",
            source_codes=errors,
        )
    generation_contract = _claim_safety_contract(planning_input, proposal, output)
    issues = generated_claim_safety_issues(
        claim_safety_output(planning_input, proposal, output, generation_contract),
        generation_contract,
    )
    return generated_claim_blocker(issues) if issues else None


def _claim_safety_contract(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
) -> StructuredDraftGenerationContract:
    return StructuredDraftGenerationContract(
        model_input=StructuredDraftGenerationInput(
            work_item_id=planning_input.work_item_id,
            planning_input_digest=planning_input.planning_input_digest,
            planning_criteria_version=planning_input.criteria_version,
            draft_kind="full_draft",
            title=output.page_assets.wordpress_title,
            final_canonical_url="",
            target_reader=proposal.target_reader,
            buyer_problem=proposal.buyer_problem,
            buyer_trigger=proposal.buyer_trigger,
            search_intent=proposal.search_intent,
            service_fit=proposal.service_label or "",
            cta_direction=proposal.cta_direction,
            sales_brief_signal_quality=StructuredDraftSignalQuality(
                status="review_required",
                status_label="Nowa strona wymaga review człowieka",
                reason="Bramka claimów nie nadaje gotowości do publikacji.",
                evidence_id_count=len(planning_input.evidence_ids),
                source_connector_count=len(proposal.source_connectors),
                source_fact_count=len(planning_input.source_facts),
                missing_evidence_count=0,
                knowledge_constraint_count=0,
                review_required_knowledge_card_count=0,
                measurement_baseline_ready=False,
                safe_next_step="Przekaż zapisaną rewizję do dokładnego review człowieka.",
            ),
            claims_removed_or_blocked=[],
            removed_or_blocked_claim_markers=[],
            human_review_questions=[],
        ),
        output_schema=initial_full_draft_output_schema(proposal),
        system_instruction="Sprawdź bezpieczeństwo claimów bez publikacji i bez zapisu.",
        user_instruction="Oceń wyłącznie przekazany dokument nowej strony.",
    )


def _finish_quality_blocked(
    *,
    workspace: ContentNewPageCanonicalDocumentWorkspace,
    proposal: ContentPlanningProposal,
    run: CodexRun,
    runtime: ContentCodexRuntimeTrace,
    blocker: ContentInitialDraftBlocker,
    run_store: LocalStateStore,
) -> ContentInitialDraftResponse:
    transition_initial_draft_run_if_status(
        run_store,
        run,
        status="blocked",
        error=safe_initial_draft_run_error(blocker),
    )
    return ContentInitialDraftResponse(
        status="blocked",
        work_item_id=workspace.work_item_id,
        proposal_id=proposal.proposal_id,
        run_id=run.id,
        runtime=runtime,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _execute_turn(
    proposal: ContentPlanningProposal,
    client: CodexAppServerClientProtocol,
    run: CodexRun,
    run_store: LocalStateStore,
    workspace: ContentNewPageCanonicalDocumentWorkspace,
    turn_request: CodexAppServerStructuredTurnRequest,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | ContentInitialDraftResponse:
    turn: CodexAppServerTurnResult | None
    try:
        turn = client.run_structured_turn(turn_request)
    except Exception:
        turn = None
    if turn is None or turn.status != "completed" or turn.output_text is None:
        code: Literal["runtime_blocked", "runtime_failed"] = (
            "runtime_blocked"
            if turn is not None and turn.status == "blocked"
            else "runtime_failed"
        )
        transition_initial_draft_run_if_status(
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
            (
                ContentCodexRuntimeTrace(status="failed")
                if turn is None
                else runtime_trace(turn)
            ),
            status="blocked" if code == "runtime_blocked" else "failed",
        )
    trace = runtime_trace(turn)
    try:
        return ContentInitialDraftModelOutput.model_validate_json(turn.output_text), trace
    except ValueError:
        transition_initial_draft_run_if_status(
            run_store,
            run,
            status="blocked",
            error="invalid_structured_output",
        )
        return _blocked(
            workspace,
            proposal,
            "invalid_structured_output",
            "Codex zwrócił dokument poza ścisłym kontraktem; nic nie zapisano.",
            run.id,
            trace,
        )


def _turn_request(
    brief: ContentNewPageBrief,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> CodexAppServerStructuredTurnRequest:
    return CodexAppServerStructuredTurnRequest(
        instruction=(
            "Napisz po polsku roboczy dokument nowej strony wyłącznie z zatwierdzonego "
            "planu. Nie zakładaj istniejącego URL-a, nie publikuj, nie wykonuj write i "
            "zwróć publish_ready=false. Zachowaj dokładne sekcje, FAQ, CTA i targety "
            "linków z planu. W każdej sekcji użyj konkretnego zatwierdzonego faktu "
            "przypisanego w approved_source_facts_by_section, jeśli ta lista nie jest pusta. "
            "Nie dodawaj faktów spoza przekazanego kontekstu. Zwróć tylko JSON zgodny ze schema."
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
                "approved_source_facts_by_section": approved_source_facts_by_section(
                    planning_input,
                    proposal,
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        output_schema=initial_full_draft_output_schema(proposal),
    )


def _request_mismatch(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    request: ContentInitialDraftRequest,
) -> bool:
    return bool(
        proposal.proposal_id != request.expected_proposal_id
        or proposal.planning_digest != request.expected_planning_digest
        or proposal.planning_input_digest != request.expected_planning_input_digest
        or planning_input.goal != "new_page"
        or planning_input.work_item_id != proposal.work_item_id
        or planning_input.planning_input_digest != request.expected_planning_input_digest
        or planning_input.confirmed_service_card_id != proposal.service_card_id
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
