from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, cast
from uuid import uuid4

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerTurnResult,
)
from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexRuntimeTrace,
    ContentCodexSectionProposalBlocker,
    ContentCodexSectionProposalBlockerCode,
    ContentCodexSectionProposalRequest,
    ContentCodexSectionProposalResponse,
)
from wilq.content.drafts.codex_section_proposal_turn import codex_turn_request
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.drafts.preview import structured_draft_preview_blockers
from wilq.content.drafts.proposal_quality_input import (
    persisted_selected_sections_quality_input,
    proposal_duplicate_risk,
    proposal_quality_ledger,
    proposal_stage_quality_review,
)
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
)
from wilq.content.quality.review import ContentQualityReview, build_content_quality_review
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.revision_children import build_child_draft_revision_command
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store import ContentWorkflowStore
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


@dataclass(frozen=True, slots=True)
class _ProposalInputs:
    base_revision: ContentDraftRevision
    contract: StructuredDraftGenerationContract
    draft_package: ContentDraftPackage
    sales_brief: ContentSalesBrief
    claim_ledger: ContentClaimLedger
    selected_headings: list[str]


@dataclass(frozen=True, slots=True)
class _RuntimeCall:
    run: CodexRun
    result: CodexAppServerTurnResult
    trace: ContentCodexRuntimeTrace


@dataclass(frozen=True, slots=True)
class _RuntimeOutput(_RuntimeCall):
    output: StructuredDraftOutput


def propose_content_section_revision(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    base_revision_id: str,
    request: ContentCodexSectionProposalRequest,
    client: CodexAppServerClientProtocol,
    workflow_store: ContentWorkflowStore,
    run_store: LocalStateStore,
) -> ContentCodexSectionProposalResponse:
    selected_headings = _ordered_selected_headings(snapshot, request)
    blockers = _proposal_preflight_blockers(
        snapshot,
        base_revision_id=base_revision_id,
        request=request,
    )
    if blockers:
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=base_revision_id,
            selected_headings=selected_headings,
            run=None,
            runtime=_not_started_trace(),
            blockers=blockers,
        )
    inputs = _required_inputs(snapshot, selected_headings=selected_headings)
    runtime_call = _execute_runtime(
        snapshot=snapshot,
        inputs=inputs,
        base_revision_id=base_revision_id,
        client=client,
        run_store=run_store,
    )
    if isinstance(runtime_call, ContentCodexSectionProposalResponse):
        return runtime_call
    runtime = _validate_runtime_call(
        snapshot=snapshot,
        inputs=inputs,
        call=runtime_call,
        run_store=run_store,
    )
    if isinstance(runtime, ContentCodexSectionProposalResponse):
        return runtime
    quality_review = _review_runtime_output(
        snapshot=snapshot,
        inputs=inputs,
        runtime=runtime,
        run_store=run_store,
    )
    if isinstance(quality_review, ContentCodexSectionProposalResponse):
        return quality_review
    return _persist_proposal(
        snapshot=snapshot,
        request=request,
        inputs=inputs,
        runtime=runtime,
        quality_review=quality_review,
        workflow_store=workflow_store,
        run_store=run_store,
    )


def _required_inputs(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    selected_headings: list[str],
) -> _ProposalInputs:
    values = (
        snapshot.revision_workspace.latest_revision,
        snapshot.structured_generation.structured_generation_result.contract,
        snapshot.draft_package.draft_package_result.draft_package,
        snapshot.sales_brief.sales_brief_result.brief,
        snapshot.claim_ledger,
    )
    if any(value is None for value in values):
        raise RuntimeError("Content proposal preflight passed without required typed inputs.")
    base_revision, contract, draft_package, sales_brief, claim_ledger = values
    return _ProposalInputs(
        base_revision=cast(ContentDraftRevision, base_revision),
        contract=cast(StructuredDraftGenerationContract, contract),
        draft_package=cast(ContentDraftPackage, draft_package),
        sales_brief=cast(ContentSalesBrief, sales_brief),
        claim_ledger=claim_ledger,
        selected_headings=selected_headings,
    )


def _start_run(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    base_revision: ContentDraftRevision,
    run_store: LocalStateStore,
) -> CodexRun:
    run = CodexRun(
        id=f"codex_content_proposal_{uuid4().hex}",
        skill="wilq-content-operator",
        hook="content_revision_proposal",
        source="wilq_api",
        status="started",
        used_endpoints=[
            f"/api/content/work-items/{base_revision.work_item_id}/draft-revisions/"
            f"{base_revision.revision_id}/codex-proposal"
        ],
        evidence_ids=_proposal_evidence_ids(snapshot),
    )
    return run_store.save_codex_run(run)


def _execute_runtime(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    inputs: _ProposalInputs,
    base_revision_id: str,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
) -> _RuntimeCall | ContentCodexSectionProposalResponse:
    run = _start_run(snapshot, inputs.base_revision, run_store)
    try:
        result = client.run_structured_turn(
            codex_turn_request(
                snapshot=snapshot,
                selected_headings=inputs.selected_headings,
                base_revision=inputs.base_revision,
            )
        )
    except Exception:
        blocker = _blocker(
            "runtime_failed",
            "Codex nie zakończył propozycji",
            "Lokalny app-server zakończył się błędem technicznym bez bezpiecznego wyniku.",
            "Sprawdź lokalny status Codexa i uruchom nową propozycję; nic nie zapisano.",
        )
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=base_revision_id,
            selected_headings=inputs.selected_headings,
            run=_finish_run(run_store, run, status="failed", error=blocker.code),
            runtime=ContentCodexRuntimeTrace(status="failed"),
            blockers=[blocker],
            status="failed",
        )
    trace = _runtime_trace(result)
    if result.status != "completed" or result.output_text is None:
        code: ContentCodexSectionProposalBlockerCode = (
            "runtime_blocked" if result.status == "blocked" else "runtime_failed"
        )
        blocker = _blocker(
            code,
            "Codex nie zwrócił bezpiecznej propozycji",
            "App-server nie zakończył turnu poprawnym ustrukturyzowanym wynikiem.",
            "Sprawdź lokalny runtime i rozpocznij nową propozycję; WILQ nic nie zapisał.",
            source_codes=[entry.code for entry in result.blockers],
        )
        run_status: Literal["blocked", "failed"] = (
            "blocked" if code == "runtime_blocked" else "failed"
        )
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=base_revision_id,
            selected_headings=inputs.selected_headings,
            run=_finish_run(run_store, run, status=run_status, error=code),
            runtime=trace,
            blockers=[blocker],
            status=run_status,
        )
    return _RuntimeCall(run=run, result=result, trace=trace)


def _validate_runtime_call(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    inputs: _ProposalInputs,
    call: _RuntimeCall,
    run_store: LocalStateStore,
) -> _RuntimeOutput | ContentCodexSectionProposalResponse:
    output_text = call.result.output_text
    if output_text is None:
        raise RuntimeError("Completed Codex call is missing output text.")
    try:
        output = StructuredDraftOutput.model_validate_json(output_text)
    except ValueError:
        blocker = _blocker(
            "invalid_structured_output",
            "Codex zwrócił niepoprawny szkic",
            "Wynik nie przeszedł ścisłego schematu treści WILQ.",
            "Odrzuć wynik i uruchom nową propozycję po sprawdzeniu kontraktu.",
        )
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=inputs.base_revision.revision_id,
            selected_headings=inputs.selected_headings,
            run=_finish_run(run_store, call.run, status="blocked", error=blocker.code),
            runtime=call.trace,
            blockers=[blocker],
        )
    scope_blocker = _section_scope_blocker(
        output,
        base_revision=inputs.base_revision,
        selected_headings=inputs.selected_headings,
    )
    if scope_blocker is not None:
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=inputs.base_revision.revision_id,
            selected_headings=inputs.selected_headings,
            run=_finish_run(run_store, call.run, status="blocked", error=scope_blocker.code),
            runtime=call.trace,
            blockers=[scope_blocker],
        )
    preview_blockers = structured_draft_preview_blockers(
        output=output,
        contract=inputs.contract,
    )
    if preview_blockers:
        blocker = _blocker(
            "proposal_contract_blocked",
            "Propozycja narusza kontrakt treści",
            (
                "WILQ wykrył obcy identyfikator, znany blocked claim, "
                "niezadeklarowaną obietnicę albo brak wymaganego lineage."
            ),
            preview_blockers[0].next_step,
            source_codes=[entry.code for entry in preview_blockers],
        )
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=inputs.base_revision.revision_id,
            selected_headings=inputs.selected_headings,
            run=_finish_run(run_store, call.run, status="blocked", error=blocker.code),
            runtime=call.trace,
            blockers=[blocker],
        )
    return _RuntimeOutput(
        run=call.run,
        result=call.result,
        trace=call.trace,
        output=output,
    )


def _review_runtime_output(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    inputs: _ProposalInputs,
    runtime: _RuntimeOutput,
    run_store: LocalStateStore,
) -> ContentQualityReview | ContentCodexSectionProposalResponse:
    quality_review = proposal_stage_quality_review(
        build_content_quality_review(
            item=snapshot.preflight.item,
            draft_package=inputs.draft_package,
            structured_output=persisted_selected_sections_quality_input(
                output=runtime.output,
                base_revision=inputs.base_revision,
                selected_headings=inputs.selected_headings,
            ),
            claim_ledger=proposal_quality_ledger(inputs.claim_ledger, inputs.contract),
            sales_brief=inputs.sales_brief,
            duplicate_risk=proposal_duplicate_risk(snapshot),
        )
    ).model_copy(update={"review_id": f"proposal_quality_review_{runtime.run.id}"})
    if quality_review.verdict == "blocked":
        blocker = _blocker(
            "quality_blocked",
            "Propozycja nie przeszła kontroli jakości",
            "WILQ wykrył twardą blokadę w deklarowanej strukturze lub lineage szkicu.",
            quality_review.safe_next_step,
            source_codes=[entry.code for entry in quality_review.blockers],
        )
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=inputs.base_revision.revision_id,
            selected_headings=inputs.selected_headings,
            run=_finish_run(
                run_store,
                runtime.run,
                status="blocked",
                error=blocker.code,
            ),
            runtime=runtime.trace,
            blockers=[blocker],
            quality_review=quality_review,
        )
    return quality_review


def _persist_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentCodexSectionProposalRequest,
    inputs: _ProposalInputs,
    runtime: _RuntimeOutput,
    quality_review: ContentQualityReview,
    workflow_store: ContentWorkflowStore,
    run_store: LocalStateStore,
) -> ContentCodexSectionProposalResponse:
    base_revision = inputs.base_revision
    if base_revision.planning_digest is None:
        blocker = _blocker(
            "missing_planning_binding",
            "Wersja nie jest powiązana z zatwierdzonym planem",
            "Starsza wersja nie wskazuje dokładnego zakresu i mapy sekcji.",
            "Zapisz nową wersję po zatwierdzeniu aktualnego planu.",
        )
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=base_revision.revision_id,
            selected_headings=inputs.selected_headings,
            run=_finish_run(
                run_store,
                runtime.run,
                status="blocked",
                error=blocker.code,
            ),
            runtime=runtime.trace,
            blockers=[blocker],
            quality_review=quality_review,
        )
    revision_sections = _merge_selected_sections(
        base_revision,
        runtime.output,
        inputs.selected_headings,
    )
    completed_run = _terminal_run(runtime.run, status="completed")
    append_result = workflow_store.append_draft_revision(
        build_child_draft_revision_command(
            base_revision,
            sections=revision_sections,
            proposal_metadata=_proposal_metadata(
                run=runtime.run,
                output=runtime.output,
                contract=inputs.contract,
                quality_review=quality_review,
                selected_headings=inputs.selected_headings,
            ),
            created_by=request.requested_by,
        ),
        completed_codex_run=completed_run,
    )
    if append_result.status == "conflict" or append_result.revision is None:
        blocker = _blocker(
            "revision_conflict",
            "Wersja bazowa zmieniła się podczas generowania",
            "WILQ nie zapisze propozycji nad nowszą wersją treści.",
            "Odśwież workspace i uruchom propozycję dla aktualnej wersji.",
        )
        return _blocked_response(
            snapshot=snapshot,
            base_revision_id=base_revision.revision_id,
            selected_headings=inputs.selected_headings,
            run=_finish_run(run_store, runtime.run, status="blocked", error=blocker.code),
            runtime=runtime.trace,
            blockers=[blocker],
            quality_review=quality_review,
            status="conflict",
        )
    return ContentCodexSectionProposalResponse(
        status=append_result.status,
        run_id=completed_run.id,
        work_item_id=base_revision.work_item_id,
        base_revision_id=base_revision.revision_id,
        selected_section_headings=inputs.selected_headings,
        revision=append_result.revision,
        quality_review=quality_review,
        runtime=runtime.trace,
        evidence_ids=_proposal_evidence_ids(snapshot),
        source_connectors=_proposal_source_connectors(snapshot),
        safe_next_step=(
            "Porównaj zmienione sekcje z wersją bazową i wykonaj semantyczny human review."
        ),
    )


def _proposal_preflight_blockers(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    base_revision_id: str,
    request: ContentCodexSectionProposalRequest,
) -> list[ContentCodexSectionProposalBlocker]:
    workspace = snapshot.revision_workspace
    base_revision = workspace.latest_revision
    if base_revision is None:
        return [
            _blocker(
                "missing_base_revision",
                "Brakuje wersji bazowej",
                "Codex może przygotować tylko child revision dokładnej zapisanej wersji.",
                "Najpierw zapisz i sprawdź wersję bazową w workspace treści.",
            )
        ]
    if (
        base_revision_id != base_revision.revision_id
        or request.expected_base_digest != base_revision.content_digest
    ):
        return [
            _blocker(
                "stale_base_revision",
                "Wybrana wersja bazowa nie jest aktualna",
                "Identyfikator albo digest nie odpowiada najnowszej zapisanej wersji.",
                "Odśwież workspace i wybierz sekcje z aktualnej wersji.",
            )
        ]
    if not workspace.context_current:
        return [
            _blocker(
                "stale_content_context",
                "Zmienił się plan lub kontekst treści",
                "Zapisana wersja nie odpowiada już aktualnej paczce planu i dowodów.",
                "Najpierw zrebasuj wersję na aktualny plan i źródła.",
            )
        ]
    if workspace.status not in {"needs_changes", "rejected"} or not workspace.can_save:
        return [
            _blocker(
                "revision_not_ready_for_proposal",
                "Ta wersja nie czeka na poprawki",
                "Codex poprawia tylko aktualną wersję oznaczoną po review jako do zmiany.",
                "Najpierw zapisz decyzję review albo przejdź do bezpiecznego kolejnego kroku.",
            )
        ]
    contract = snapshot.structured_generation.structured_generation_result.contract
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    sales_brief = snapshot.sales_brief.sales_brief_result.brief
    if (
        contract is None
        or draft_package is None
        or sales_brief is None
        or snapshot.claim_ledger is None
    ):
        return [
            _blocker(
                "missing_generation_contract",
                "Brakuje kontraktu generowania",
                "WILQ nie ma pełnego model inputu, claim ledgeru albo planu sekcji.",
                "Uzupełnij blokady briefu i claimów przed użyciem Codexa.",
            )
        ]
    selection_blockers = _selected_section_blockers(base_revision, contract, request)
    if selection_blockers:
        return selection_blockers
    claim_texts = [
        marker.claim_text for marker in contract.model_input.claim_markers if marker.claim_text
    ]
    if len(claim_texts) != len(set(claim_texts)):
        return [
            _blocker(
                "ambiguous_claim_marker",
                "Claim Ledger ma niejednoznaczne twierdzenia",
                "Dwa claimy mają ten sam tekst, więc nie można bezpiecznie zapisać ich ID.",
                "Ujednoznacznij claimy w Claim Ledger przed generowaniem.",
            )
        ]
    return []


def _selected_section_blockers(
    base_revision: ContentDraftRevision,
    contract: StructuredDraftGenerationContract,
    request: ContentCodexSectionProposalRequest,
) -> list[ContentCodexSectionProposalBlocker]:
    base_headings = {section.heading for section in base_revision.sections}
    base_by_id = {
        str(section.section_id): section.heading
        for section in base_revision.sections
        if section.section_id is not None
    }
    contract_headings = {section.heading for section in contract.model_input.sections}
    unknown = (
        [
            section_id
            for section_id in request.selected_section_ids
            if section_id not in base_by_id
        ]
        if request.selected_section_ids
        else [
            heading
            for heading in request.selected_section_headings
            if heading not in base_headings or heading not in contract_headings
        ]
    )
    if not unknown:
        return []
    return [
        _blocker(
            "unknown_selected_section",
            "Wybrana sekcja nie należy do aktualnego planu",
            "Codex może zmienić tylko sekcje obecne w wersji bazowej i model input WILQ.",
            "Odśwież mapę sekcji i wybierz aktualne sekcje.",
        )
    ]


def _ordered_selected_headings(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentCodexSectionProposalRequest,
) -> list[str]:
    base_revision = snapshot.revision_workspace.latest_revision
    if base_revision is None:
        return request.selected_section_headings
    if request.selected_section_ids:
        selected_ids = set(request.selected_section_ids)
        return [
            section.heading
            for section in base_revision.sections
            if section.section_id in selected_ids
        ]
    selected_headings = set(request.selected_section_headings)
    return [
        section.heading
        for section in base_revision.sections
        if section.heading in selected_headings
    ]


def _section_scope_blocker(
    output: StructuredDraftOutput,
    *,
    base_revision: ContentDraftRevision,
    selected_headings: list[str],
) -> ContentCodexSectionProposalBlocker | None:
    output_headings = [section.heading for section in output.sections]
    base_by_heading = {section.heading: section for section in base_revision.sections}
    evidence_mapping_matches = all(
        section.evidence_ids == base_by_heading[section.heading].evidence_ids
        for section in output.sections
        if section.heading in base_by_heading
    )
    if (
        output.title == base_revision.title
        and output_headings == selected_headings
        and evidence_mapping_matches
    ):
        return None
    return _blocker(
        "section_scope_mismatch",
        "Codex wyszedł poza wybrane sekcje",
        "Wynik musi zachować tytuł, wybrane nagłówki, ich kolejność i mapę dowodów.",
        "Odrzuć wynik i uruchom nową propozycję dla aktualnego wyboru.",
    )


def _merge_selected_sections(
    base_revision: ContentDraftRevision,
    output: StructuredDraftOutput,
    selected_headings: list[str],
) -> list[ContentDraftRevisionSection]:
    selected = set(selected_headings)
    generated_by_heading = {section.heading: section for section in output.sections}
    return [
        base_section.model_copy(
            update={"body_markdown": generated_by_heading[base_section.heading].body_markdown}
        )
        if base_section.heading in selected
        else base_section
        for base_section in base_revision.sections
    ]


def _proposal_metadata(
    *,
    run: CodexRun,
    output: StructuredDraftOutput,
    contract: StructuredDraftGenerationContract,
    quality_review: ContentQualityReview,
    selected_headings: list[str],
) -> ContentDraftRevisionProposalMetadata:
    if quality_review.verdict == "blocked":
        raise RuntimeError("Blocked quality review cannot be persisted as a proposal.")
    marker_by_text = {
        marker.claim_text: marker.claim_id for marker in contract.model_input.claim_markers
    }
    output_by_heading = {section.heading: section for section in output.sections}
    return ContentDraftRevisionProposalMetadata(
        codex_run_id=run.id,
        selected_section_headings=selected_headings,
        section_lineage=[
            ContentDraftRevisionProposalSectionLineage(
                heading=heading,
                evidence_ids=output_by_heading[heading].evidence_ids,
                claim_ids=[
                    marker_by_text[claim] for claim in output_by_heading[heading].claims_used
                ],
            )
            for heading in selected_headings
        ],
        quality_verdict=quality_review.verdict,
        quality_finding_codes=_unique(finding.code for finding in quality_review.findings),
    )


def _runtime_trace(result: CodexAppServerTurnResult) -> ContentCodexRuntimeTrace:
    return ContentCodexRuntimeTrace(
        status=result.status,
        thread_id=result.thread_id,
        turn_id=result.turn_id,
        event_methods=list(result.event_methods),
        item_types=list(result.item_types),
        external_call_attempted=result.external_call_attempted,
    )


def _not_started_trace() -> ContentCodexRuntimeTrace:
    return ContentCodexRuntimeTrace(status="not_started")


def _blocked_response(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    base_revision_id: str,
    selected_headings: list[str],
    run: CodexRun | None,
    runtime: ContentCodexRuntimeTrace,
    blockers: list[ContentCodexSectionProposalBlocker],
    quality_review: ContentQualityReview | None = None,
    status: Literal["blocked", "failed", "conflict"] = "blocked",
) -> ContentCodexSectionProposalResponse:
    return ContentCodexSectionProposalResponse(
        status=status,
        run_id=None if run is None else run.id,
        work_item_id=snapshot.preflight.item.id,
        base_revision_id=base_revision_id,
        selected_section_headings=selected_headings,
        quality_review=quality_review,
        runtime=runtime,
        evidence_ids=_proposal_evidence_ids(snapshot),
        source_connectors=_proposal_source_connectors(snapshot),
        blockers=blockers,
        safe_next_step=blockers[0].next_step,
    )


def _finish_run(
    store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["completed", "failed", "blocked"],
    error: str | None = None,
) -> CodexRun:
    return store.save_codex_run(_terminal_run(run, status=status, error=error))


def _terminal_run(
    run: CodexRun,
    *,
    status: Literal["completed", "failed", "blocked"],
    error: str | None = None,
) -> CodexRun:
    return run.model_copy(update={"status": status, "completed_at": utc_now(), "error": error})


def _proposal_evidence_ids(snapshot: ContentWorkItemWorkflowSnapshotResponse) -> list[str]:
    contract = snapshot.structured_generation.structured_generation_result.contract
    if contract is None:
        return _unique(snapshot.preflight.item.evidence_ids)
    return _unique(
        [
            *snapshot.preflight.item.evidence_ids,
            *(fact.evidence_id for fact in contract.model_input.source_facts),
            *(
                evidence_id
                for section in contract.model_input.sections
                for evidence_id in section.evidence_ids
            ),
            *(
                evidence_id
                for marker in [
                    *contract.model_input.claim_markers,
                    *contract.model_input.removed_or_blocked_claim_markers,
                ]
                for evidence_id in marker.evidence_ids
            ),
        ]
    )


def _proposal_source_connectors(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> list[str]:
    contract = snapshot.structured_generation.structured_generation_result.contract
    if contract is None:
        return _unique(snapshot.preflight.item.source_connectors)
    return _unique(
        [
            *snapshot.preflight.item.source_connectors,
            *(fact.source_connector for fact in contract.model_input.source_facts),
            *(
                connector
                for marker in [
                    *contract.model_input.claim_markers,
                    *contract.model_input.removed_or_blocked_claim_markers,
                ]
                for connector in marker.source_connectors
            ),
        ]
    )


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _blocker(
    code: ContentCodexSectionProposalBlockerCode,
    label: str,
    reason: str,
    next_step: str,
    *,
    source_codes: list[str] | None = None,
) -> ContentCodexSectionProposalBlocker:
    return ContentCodexSectionProposalBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
        source_codes=source_codes or [],
    )


__all__ = [
    "ContentCodexSectionProposalRequest",
    "ContentCodexSectionProposalResponse",
    "propose_content_section_revision",
]
