from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
)
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.generated_claim_safety import (
    claim_safety_output,
    generated_claim_blocker,
    generated_claim_safety_issues,
)
from wilq.content.drafts.initial_draft_persistence import (
    InitialDraftRevisionStore,
    persist_initial_draft,
)
from wilq.content.drafts.initial_draft_pipeline import (
    InitialDraftPipelineInputs,
    InitialDraftRunMetadata,
    generate_initial_draft,
)
from wilq.content.drafts.initial_draft_run import (
    finish_initial_draft_run,
    initial_draft_context_digest,
    start_initial_draft_run,
)
from wilq.content.drafts.initial_draft_runtime import (
    InitialDraftFailureCopy,
    InitialDraftTurnFailure,
    InitialDraftTurnGoal,
    execute_initial_draft_turn,
    initial_draft_request_mismatch,
)
from wilq.content.drafts.initial_draft_validation import (
    document_scope_errors_for_planning_input,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.drafts.regulatory_repair import regulatory_draft_preflight_errors
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    contract_for_planning_proposal,
)
from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBlocker,
    ContentPlanningInputBuildResult,
    build_content_planning_input,
)
from wilq.content.planning.generated_proposal import (
    with_explicit_content_service_selection,
)
from wilq.content.quality.benefit_signal import (
    BENEFIT_BODY_MARKER,
    BENEFIT_HEADING_SIGNAL,
    BENEFIT_SOURCE_FACT_MARKER,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import (
    content_draft_package_digest,
    validate_no_inline_link,
)
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


@dataclass(frozen=True, slots=True)
class _InitialDraftInputs:
    planning_input: ContentPlanningInput
    proposal: ContentPlanningProposal
    generation_contract: StructuredDraftGenerationContract
    base_revision_id: str | None = None


BENEFIT_SOURCE_FACT_LIMIT = 2

_REFRESH_INITIAL_DRAFT_TURN_GOAL = InitialDraftTurnGoal(
    runtime_failure=InitialDraftFailureCopy(
        label="Codex nie zwrócił pełnego tekstu",
        reason="App-server nie zakończył turnu poprawnym ustrukturyzowanym dokumentem.",
        next_step="Sprawdź runtime i rozpocznij nową próbę; WILQ nic nie zapisał.",
    ),
    invalid_structured_output=InitialDraftFailureCopy(
        label="Codex zwrócił niepoprawny dokument",
        reason="Wynik nie przeszedł ścisłego schematu pełnej treści WILQ.",
        next_step="Odrzuć wynik i uruchom nową próbę po sprawdzeniu kontraktu.",
    ),
    include_runtime_source_codes=True,
)


def _benefit_source_fact_text(summary: str) -> str | None:
    text = summary.strip()
    if BENEFIT_SOURCE_FACT_MARKER.search(text) is None:
        return None
    try:
        return validate_no_inline_link(text)
    except ValueError:
        return None


def _enrich_benefit_sections(
    output: ContentInitialDraftModelOutput,
    planning_input: ContentPlanningInput,
) -> ContentInitialDraftModelOutput:
    benefit_facts = [
        text
        for fact in planning_input.source_facts
        if (text := _benefit_source_fact_text(fact.summary)) is not None
    ][:BENEFIT_SOURCE_FACT_LIMIT]
    if not benefit_facts:
        return output
    fact_sentences = [
        fact if fact.endswith((".", "!", "?")) else f"{fact}." for fact in benefit_facts
    ]
    fallback = f"Z korzyści współpracy: {' '.join(fact_sentences)}"
    sections = []
    for section in output.sections:
        if (
            BENEFIT_HEADING_SIGNAL.search(section.heading) is not None
            and BENEFIT_BODY_MARKER.search(section.body_markdown) is None
        ):
            section = section.model_copy(
                update={"body_markdown": f"{section.body_markdown.rstrip()}\n\n{fallback}"}
            )
        sections.append(section)
    if sections == output.sections:
        return output
    return ContentInitialDraftModelOutput.model_validate(
        {
            **output.model_dump(mode="python"),
            "sections": [section.model_dump(mode="python") for section in sections],
        }
    )


def _initial_draft_context_digest(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    prepared: _InitialDraftInputs,
) -> str:
    package = snapshot.draft_package.draft_package_result.draft_package
    if package is None:
        raise ValueError("Initial draft context requires a draft package.")
    item = snapshot.preflight.item
    return initial_draft_context_digest(
        base_revision_id=prepared.base_revision_id,
        draft_package_id=package.id,
        draft_package_digest=content_draft_package_digest(package),
        final_canonical_url=prepared.planning_input.final_canonical_url
        or item.final_canonical_url
        or item.intended_final_url,
        service_card_id=prepared.planning_input.confirmed_service_card_id,
        proposal_id=prepared.proposal.proposal_id or "",
        planning_digest=prepared.proposal.planning_digest,
        planning_input_digest=prepared.planning_input.planning_input_digest,
    )


def generate_initial_full_draft(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    client: CodexAppServerClientProtocol,
    workflow_store: InitialDraftRevisionStore,
    run_store: LocalStateStore,
    run_id: str | None = None,
    context_digest: str | None = None,
) -> ContentInitialDraftResponse:
    prepared = _prepare_inputs(snapshot, request)
    if isinstance(prepared, ContentInitialDraftResponse):
        return prepared
    if (proposal_id := prepared.proposal.proposal_id) is None:
        raise RuntimeError("Prepared initial draft is missing its generated proposal ID.")
    return generate_initial_draft(
        inputs=InitialDraftPipelineInputs(
            planning_input=prepared.planning_input,
            proposal=prepared.proposal,
            preflight_response=None,
            turn_request=lambda: initial_full_draft_turn_request(
                planning_input=prepared.planning_input,
                proposal=prepared.proposal,
                generation_contract=prepared.generation_contract,
            ),
            turn_goal=_REFRESH_INITIAL_DRAFT_TURN_GOAL,
            run=InitialDraftRunMetadata(
                work_item_id=prepared.planning_input.work_item_id,
                evidence_ids=prepared.planning_input.evidence_ids,
                source_material_ids=prepared.proposal.source_material_ids,
                proposal_id=proposal_id,
                planning_digest=prepared.proposal.planning_digest,
                planning_input_digest=prepared.planning_input.planning_input_digest,
                context_digest=context_digest or _initial_draft_context_digest(snapshot, prepared),
                endpoint_path=None,
                prompt=None,
                run_id=run_id,
            ),
            output_blocker=lambda candidate: _output_blocker(prepared, candidate),
            output_transform=lambda output: _enrich_benefit_sections(
                output, prepared.planning_input
            ),
            response=lambda *, status, blocker, run, runtime: _blocked_response(
                snapshot,
                proposal=prepared.proposal,
                status=status,
                run=run,
                runtime=runtime,
                blockers=[blocker],
            ),
            persist=lambda *, output, runtime, run, regulatory_assurance: persist_initial_draft(
                snapshot=snapshot,
                request=request,
                planning_input=prepared.planning_input,
                proposal=prepared.proposal,
                base_revision_id=prepared.base_revision_id,
                output=output,
                run=run,
                trace=runtime,
                workflow_store=workflow_store,
                run_store=run_store,
                regulatory_assurance=regulatory_assurance,
            ),
            start_run=start_initial_draft_run,
            terminal_hook=finish_initial_draft_run,
            execute_turn=lambda **kwargs: _execute_runtime(
                prepared,
                kwargs["client"],
                kwargs["run"],
                kwargs["run_store"],
                kwargs["turn_request"],
            ),
        ),
        client=client,
        workflow_store=workflow_store,
        run_store=run_store,
    )


def _prepare_inputs(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
) -> _InitialDraftInputs | ContentInitialDraftResponse:
    planning = snapshot.planning_workspace
    latest_revision = snapshot.revision_workspace.latest_revision
    if latest_revision is not None and snapshot.revision_workspace.context_current:
        return _blocked_response(
            snapshot,
            proposal=None if planning is None else planning.proposal,
            status="conflict",
            blockers=[
                build_blocker(
                    ContentInitialDraftBlocker,
                    code="revision_already_exists",
                    label="Aktualna wersja już istnieje",
                    reason=(
                        "Nowy pełny draft może powstać tylko jako kolejna rewizja aktualnego planu."
                    ),
                    next_step="Otwórz aktualny plan albo pracuj na zapisanej wersji.",
                )
            ],
        )
    if planning is None or not planning.section_map_current:
        return _blocked_response(
            snapshot,
            proposal=None if planning is None else planning.proposal,
            status="blocked",
            blockers=[
                build_blocker(
                    ContentInitialDraftBlocker,
                    code="planning_not_ready",
                    label="Brakuje aktualnego wygenerowanego planu",
                    reason=(
                        "Pełny tekst wymaga dokładnego wygenerowanego planu "
                        "związanego z bieżącym wejściem."
                    ),
                    next_step=(
                        "Odśwież źródła lub wygeneruj aktualny plan, a następnie "
                        "uruchom pełny tekst."
                    ),
                )
            ],
        )
    proposal = planning.proposal
    if not draftable_planning_sections(proposal.sections):
        return _no_draftable_sections(snapshot, proposal)
    mismatch = _proposal_request_mismatch(proposal, request)
    if mismatch is not None:
        return _blocked_response(
            snapshot,
            proposal=proposal,
            status="conflict",
            blockers=[mismatch],
        )
    service_card_id = proposal.service_card_id
    if service_card_id is None:
        return _planning_not_generated(snapshot, proposal)
    planning_result = _current_planning_input(snapshot, service_card_id)
    # A durable document requires stricter readiness than a reviewable plan.
    draft_blockers = planning_result.blockers
    if planning_result.planning_input is None or draft_blockers:
        return _blocked_response(
            snapshot,
            proposal=proposal,
            status="blocked",
            blockers=[_planning_input_blocker(draft_blockers)],
        )
    planning_input = planning_result.planning_input
    if planning_input.planning_input_digest != request.expected_planning_input_digest:
        return _blocked_response(
            snapshot,
            proposal=proposal,
            status="conflict",
            blockers=[_stale_input_blocker()],
        )
    generation = snapshot.structured_generation.structured_generation_result
    if generation.contract is None or generation.blockers:
        return _blocked_response(
            snapshot,
            proposal=proposal,
            status="blocked",
            blockers=[
                build_blocker(
                    ContentInitialDraftBlocker,
                    code="missing_generation_contract",
                    label="Pełny tekst pozostaje zablokowany",
                    reason="Kontrakt szkicu odrzucił wiedzę, claims albo foundation.",
                    next_step="Usuń wskazany blocker bez obchodzenia owner review.",
                    source_codes=[item.code for item in generation.blockers],
                )
            ],
        )
    if errors := regulatory_draft_preflight_errors(planning_input, proposal):
        return _regulatory_preflight_blocked(snapshot, proposal, errors)
    generation_contract = contract_for_planning_proposal(
        generation.contract,
        proposal,
        planning_input,
    )
    return _InitialDraftInputs(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=generation_contract,
        base_revision_id=None if latest_revision is None else latest_revision.revision_id,
    )


def _regulatory_preflight_blocked(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    proposal: ContentPlanningProposal,
    errors: list[str],
) -> ContentInitialDraftResponse:
    requirement_count = len({error.split(":", 3)[2] for error in errors})
    blocker = build_blocker(
        ContentInitialDraftBlocker,
        code="regulatory_preflight_failed",
        label="Plan regulacyjny nie spełnia warunków szkicu",
        reason=(
            "Zatwierdzony plan nie zapewnia kompletnego, weryfikowalnego pokrycia "
            "wymagań regulacyjnych (liczba brakujących wymogów: "
            f"{requirement_count}), więc pełny tekst nie został uruchomiony."
        ),
        next_step="Wygeneruj nowy plan z sekcją dla każdego wymogu regulacyjnego, a następnie "
        "ponów pełny tekst.",
        source_codes=errors,
    )
    return _blocked_response(snapshot, proposal=proposal, status="blocked", blockers=[blocker])


def _no_draftable_sections(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    proposal: ContentPlanningProposal,
) -> ContentInitialDraftResponse:
    return _blocked_response(
        snapshot,
        proposal=proposal,
        status="blocked",
        blockers=[
            build_blocker(
                ContentInitialDraftBlocker,
                code="document_scope_mismatch",
                label="Plan nie ma sekcji do napisania",
                reason=(
                    "Wszystkie rozpoznane elementy zostały oznaczone do usunięcia "
                    "lub osobnego review."
                ),
                next_step=(
                    "Zostaw co najmniej jedną sekcję do tekstu albo zakończ review "
                    "bez generowania draftu."
                ),
            )
        ],
    )


def _current_planning_input(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    service_card_id: str,
) -> ContentPlanningInputBuildResult:
    planning_snapshot = with_explicit_content_service_selection(snapshot, service_card_id)
    return build_content_planning_input(planning_snapshot, service_card_id=service_card_id)


def _proposal_request_mismatch(
    proposal: ContentPlanningProposal,
    request: ContentInitialDraftRequest,
) -> ContentInitialDraftBlocker | None:
    mismatch = initial_draft_request_mismatch(
        proposal=proposal,
        request=request,
        planning_input=None,
        mode="refresh",
    )
    if mismatch == "planning_not_generated":
        return build_blocker(
            ContentInitialDraftBlocker,
            code="planning_not_generated",
            label="Brakuje wygenerowanego planu",
            reason="Initial draft nie może powstać z preserve-first baseline bez planu modelowego.",
            next_step="Wygeneruj aktualny plan i uruchom pełny tekst z widocznego szkicu.",
        )
    if mismatch == "proposal_mismatch":
        return build_blocker(
            ContentInitialDraftBlocker,
            code="proposal_mismatch",
            label="Plan zmienił się przed generowaniem",
            reason="Żądanie nie wskazuje dokładnej bieżącej wersji planu i jego wejścia.",
            next_step="Odśwież workspace i uruchom generowanie dla widocznego planu.",
        )
    return None


def _planning_not_generated(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    proposal: ContentPlanningProposal,
) -> ContentInitialDraftResponse:
    return _blocked_response(
        snapshot,
        proposal=proposal,
        status="blocked",
        blockers=[
            build_blocker(
                ContentInitialDraftBlocker,
                code="planning_not_generated",
                label="Plan nie wskazuje zatwierdzonej usługi",
                reason="Pełny tekst wymaga exact service bindingu z wygenerowanego planu.",
                next_step="Wygeneruj aktualny plan dla wybranej usługi.",
            )
        ],
    )


def _execute_runtime(
    inputs: _InitialDraftInputs,
    client: CodexAppServerClientProtocol,
    run: CodexRun,
    run_store: LocalStateStore,
    turn_request: CodexAppServerStructuredTurnRequest,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | ContentInitialDraftResponse:
    execution = execute_initial_draft_turn(
        turn_request=turn_request,
        client=client,
        run=run,
        run_store=run_store,
        goal=_REFRESH_INITIAL_DRAFT_TURN_GOAL,
        on_terminal=finish_initial_draft_run,
    )
    if isinstance(execution, InitialDraftTurnFailure):
        return ContentInitialDraftResponse(
            status=execution.status,
            work_item_id=inputs.planning_input.work_item_id,
            proposal_id=inputs.proposal.proposal_id,
            run_id=run.id,
            runtime=execution.trace,
            blockers=[execution.blocker],
            safe_next_step=execution.blocker.next_step,
        )
    return execution


def _output_blocker(
    inputs: _InitialDraftInputs,
    output: ContentInitialDraftModelOutput,
) -> ContentInitialDraftBlocker | None:
    errors = document_scope_errors_for_planning_input(
        inputs.planning_input,
        inputs.proposal,
        output,
    )
    if errors:
        return build_blocker(
            ContentInitialDraftBlocker,
            code="document_scope_mismatch",
            label="Dokument nie odpowiada zatwierdzonemu planowi",
            reason="Model zmienił strukturę albo plan nie ma kompletnego lineage.",
            next_step="Odrzuć wynik; nie naprawiaj struktury ręcznie po generowaniu.",
            source_codes=errors,
        )
    issues = generated_claim_safety_issues(
        claim_safety_output(
            inputs.planning_input,
            inputs.proposal,
            output,
            inputs.generation_contract,
        ),
        inputs.generation_contract,
    )
    if issues:
        return generated_claim_blocker(issues)
    return None


def _blocked_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    proposal: ContentPlanningProposal | None,
    status: Literal["blocked", "failed", "conflict"],
    blockers: list[ContentInitialDraftBlocker],
    run: CodexRun | None = None,
    runtime: ContentCodexRuntimeTrace | None = None,
) -> ContentInitialDraftResponse:
    return ContentInitialDraftResponse(
        status=status,
        work_item_id=snapshot.preflight.item.id,
        proposal_id=None if proposal is None else proposal.proposal_id,
        run_id=None if run is None else run.id,
        runtime=runtime or ContentCodexRuntimeTrace(status="not_started"),
        blockers=blockers,
        safe_next_step=blockers[0].next_step,
    )


def _stale_input_blocker() -> ContentInitialDraftBlocker:
    return build_blocker(
        ContentInitialDraftBlocker,
        code="stale_planning_input",
        label="Metryki albo kontekst planu zmieniły się",
        reason="Bieżący planning_input_digest nie odpowiada zatwierdzonej wersji.",
        next_step="Wygeneruj nowy plan przed tworzeniem tekstu.",
    )


def _planning_input_blocker(
    blockers: list[ContentPlanningInputBlocker],
) -> ContentInitialDraftBlocker:
    """Keep the first actionable planning gate visible at the draft seam."""
    first = blockers[0] if blockers else None
    blocker_code = first.code if first is not None else "stale_planning_input"
    return build_blocker(
        ContentInitialDraftBlocker,
        code=blocker_code,
        label=first.label if first is not None else "Wejście tekstu nie jest aktualne",
        reason=first.reason
        if first is not None
        else "Usługa, wiedza, inventory albo metryki nie przechodzą bieżących bramek.",
        next_step=first.next_step
        if first is not None
        else "Odśwież źródła lub zatwierdzenia i wygeneruj aktualny plan.",
        source_codes=[item.code for item in blockers],
    )


__all__ = ["generate_initial_full_draft"]
