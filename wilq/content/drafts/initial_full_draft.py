from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast
from uuid import uuid4

from wilq.codex.app_server import CodexAppServerClientProtocol, CodexAppServerTurnResult
from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.content.drafts.codex_section_proposal_contracts import ContentCodexRuntimeTrace
from wilq.content.drafts.generated_claim_safety import generated_claim_safety_issues
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftBlockerCode,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.drafts.initial_full_draft_document import (
    build_initial_draft_revision_command,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
    StructuredDraftOutputSection,
    contract_for_planning_proposal,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    build_content_planning_input,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.store import ContentWorkflowStore
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


@dataclass(frozen=True, slots=True)
class _InitialDraftInputs:
    planning_input: ContentPlanningInput
    proposal: ContentPlanningProposal
    generation_contract: StructuredDraftGenerationContract
    base_revision_id: str | None = None


def generate_initial_full_draft(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    client: CodexAppServerClientProtocol,
    workflow_store: ContentWorkflowStore,
    run_store: LocalStateStore,
    run_id: str | None = None,
) -> ContentInitialDraftResponse:
    prepared = _prepare_inputs(snapshot, request)
    if isinstance(prepared, ContentInitialDraftResponse):
        return prepared
    run = _start_run(prepared, run_store, run_id=run_id)
    runtime_result = _execute_runtime(prepared, client, run, run_store)
    if isinstance(runtime_result, ContentInitialDraftResponse):
        return runtime_result
    output, trace = runtime_result
    blocker = _output_blocker(prepared, output)
    if blocker is not None:
        _finish_run(run_store, run, status="blocked", error=blocker.code)
        return _blocked_response(
            snapshot,
            proposal=prepared.proposal,
            status="blocked",
            run=run,
            runtime=trace,
            blockers=[blocker],
        )
    return _persist_document(
        snapshot=snapshot,
        request=request,
        inputs=prepared,
        output=output,
        run=run,
        trace=trace,
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
                _blocker(
                    "revision_already_exists",
                    "Aktualna wersja już istnieje",
                    "Nowy pełny draft może powstać tylko jako kolejna rewizja aktualnego planu.",
                    "Otwórz aktualny plan albo pracuj na zapisanej wersji.",
                )
            ],
        )
    if planning is None or not planning.scope_current or not planning.section_map_current:
        return _blocked_response(
            snapshot,
            proposal=None if planning is None else planning.proposal,
            status="blocked",
            blockers=[
                _blocker(
                    "planning_not_approved",
                    "Plan nie ma dwóch aktualnych decyzji",
                    "Zakres i mapa sekcji muszą być zatwierdzone dla dokładnej wersji planu.",
                    "Sprawdź plan, zatwierdź zakres oraz mapę sekcji i spróbuj ponownie.",
                )
            ],
        )
    proposal = planning.proposal
    if not draftable_planning_sections(proposal.sections):
        return _blocked_response(
            snapshot,
            proposal=proposal,
            status="blocked",
            blockers=[
                _blocker(
                    "document_scope_mismatch",
                    "Plan nie ma sekcji do napisania",
                    "Wszystkie rozpoznane elementy zostały oznaczone do usunięcia "
                    "lub osobnego review.",
                    "Zostaw co najmniej jedną sekcję do tekstu albo zakończ review "
                    "bez generowania draftu.",
                )
            ],
        )
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
    planning_result = build_content_planning_input(snapshot, service_card_id=service_card_id)
    # Planning may use a public rendered ``the_content`` read to produce a
    # reviewable strategy, but a full durable document is a stronger boundary.
    # Keep every readiness blocker here: review-required WordPress material,
    # unapproved service cards and stale/blocked sources must not become a
    # real draft merely because the planner was allowed to inspect them.
    draft_blockers = [
        blocker
        for blocker in planning_result.blockers
        if not (
            blocker.code == "wordpress_material_review_required"
            and _usable_rendered_content_baseline(planning_result.planning_input)
        )
    ]
    if planning_result.planning_input is None or draft_blockers:
        return _blocked_response(
            snapshot,
            proposal=proposal,
            status="blocked",
            blockers=[
                _blocker(
                    "stale_planning_input",
                    "Wejście tekstu nie jest aktualne",
                    "Usługa, wiedza, inventory albo metryki nie przechodzą bieżących bramek.",
                    "Odśwież źródła lub zatwierdzenia i wygeneruj aktualny plan.",
                    source_codes=[item.code for item in draft_blockers],
                )
            ],
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
                _blocker(
                    "missing_generation_contract",
                    "Pełny tekst pozostaje zablokowany",
                    "Kontrakt szkicu odrzucił wiedzę, claims albo foundation.",
                    "Usuń wskazany blocker bez obchodzenia owner review.",
                    source_codes=[item.code for item in generation.blockers],
                )
            ],
        )
    generation_contract = contract_for_planning_proposal(
        generation.contract,
        proposal,
    )
    return _InitialDraftInputs(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=generation_contract,
        base_revision_id=None if latest_revision is None else latest_revision.revision_id,
    )


def _usable_rendered_content_baseline(
    planning_input: ContentPlanningInput | None,
) -> bool:
    """Allow an existing public page body to ground a refresh draft.

    A rendered ``the_content`` read is not an approved knowledge source, but it
    is a valid baseline for an unreviewed refresh when the API has preserved
    exact evidence and extraction lineage.  Claims and human scope/map gates
    remain enforced elsewhere in this preparation path.
    """
    if planning_input is None:
        return False
    inventory = planning_input.inventory
    return bool(
        inventory.content_status == "available"
        and inventory.content_text
        and inventory.material_confidence == "review_required"
        and inventory.extraction_region == "main_or_article_visible_text"
        and inventory.evidence_ids
        and inventory.source_field_lineage
    )


def _proposal_request_mismatch(
    proposal: ContentPlanningProposal,
    request: ContentInitialDraftRequest,
) -> ContentInitialDraftBlocker | None:
    if proposal.generation_status != "codex_generated" or proposal.proposal_id is None:
        return _blocker(
            "planning_not_generated",
            "Brakuje wygenerowanego planu",
            "Initial draft nie może powstać z preserve-first baseline bez planu modelowego.",
            "Wygeneruj plan, sprawdź go i zapisz obie decyzje człowieka.",
        )
    if (
        proposal.proposal_id != request.expected_proposal_id
        or proposal.planning_digest != request.expected_planning_digest
        or proposal.planning_input_digest != request.expected_planning_input_digest
    ):
        return _blocker(
            "proposal_mismatch",
            "Plan zmienił się przed generowaniem",
            "Żądanie nie wskazuje dokładnej bieżącej wersji planu i jego wejścia.",
            "Odśwież workspace i uruchom generowanie dla widocznego planu.",
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
            _blocker(
                "planning_not_generated",
                "Plan nie wskazuje zatwierdzonej usługi",
                "Pełny tekst wymaga exact service bindingu z wygenerowanego planu.",
                "Wygeneruj i zatwierdź aktualny plan dla wybranej usługi.",
            )
        ],
    )


def _execute_runtime(
    inputs: _InitialDraftInputs,
    client: CodexAppServerClientProtocol,
    run: CodexRun,
    run_store: LocalStateStore,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | ContentInitialDraftResponse:
    try:
        result = client.run_structured_turn(
            initial_full_draft_turn_request(
                planning_input=inputs.planning_input,
                proposal=inputs.proposal,
                generation_contract=inputs.generation_contract,
            )
        )
    except Exception:
        result = CodexAppServerTurnResult(status="failed")
    trace = _runtime_trace(result)
    if result.status != "completed" or result.output_text is None:
        code: ContentInitialDraftBlockerCode = (
            "runtime_blocked" if result.status == "blocked" else "runtime_failed"
        )
        blocker = _blocker(
            code,
            "Codex nie zwrócił pełnego tekstu",
            "App-server nie zakończył turnu poprawnym ustrukturyzowanym dokumentem.",
            "Sprawdź runtime i rozpocznij nową próbę; WILQ nic nie zapisał.",
            source_codes=[item.code for item in result.blockers],
        )
        status: Literal["blocked", "failed"] = (
            "blocked" if result.status == "blocked" else "failed"
        )
        _finish_run(run_store, run, status=status, error=code)
        return ContentInitialDraftResponse(
            status=status,
            work_item_id=inputs.planning_input.work_item_id,
            proposal_id=inputs.proposal.proposal_id,
            run_id=run.id,
            runtime=trace,
            blockers=[blocker],
            safe_next_step=blocker.next_step,
        )
    try:
        return ContentInitialDraftModelOutput.model_validate_json(result.output_text), trace
    except ValueError:
        blocker = _blocker(
            "invalid_structured_output",
            "Codex zwrócił niepoprawny dokument",
            "Wynik nie przeszedł ścisłego schematu pełnej treści WILQ.",
            "Odrzuć wynik i uruchom nową próbę po sprawdzeniu kontraktu.",
        )
        _finish_run(run_store, run, status="blocked", error=blocker.code)
        return ContentInitialDraftResponse(
            status="blocked",
            work_item_id=inputs.planning_input.work_item_id,
            proposal_id=inputs.proposal.proposal_id,
            run_id=run.id,
            runtime=trace,
            blockers=[blocker],
            safe_next_step=blocker.next_step,
        )


def _output_blocker(
    inputs: _InitialDraftInputs,
    output: ContentInitialDraftModelOutput,
) -> ContentInitialDraftBlocker | None:
    errors = _document_scope_errors(inputs.proposal, output)
    if errors:
        return _blocker(
            "document_scope_mismatch",
            "Dokument nie odpowiada zatwierdzonemu planowi",
            "Model zmienił strukturę albo plan nie ma kompletnego lineage.",
            "Odrzuć wynik; nie naprawiaj struktury ręcznie po generowaniu.",
            source_codes=errors,
        )
    issues = generated_claim_safety_issues(
        _claim_safety_output(inputs, output),
        inputs.generation_contract,
    )
    if issues:
        return _blocker(
            "generated_claim_blocked",
            "Tekst zawiera niedozwoloną obietnicę",
            "Deterministyczna bramka wykryła blocked claim albo ryzykowny język.",
            "Odrzuć wynik i wygeneruj bez niedozwolonych twierdzeń.",
            source_codes=list(dict.fromkeys(item.code for item in issues)),
        )
    return None


def _document_scope_errors(
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
) -> list[str]:
    errors: list[str] = []
    draftable_sections = draftable_planning_sections(proposal.sections)
    expected_sections = [(item.section_id, item.heading) for item in draftable_sections]
    actual_sections = [(item.section_id, item.heading) for item in output.sections]
    if actual_sections != expected_sections:
        errors.append("sections")
    if [item.question for item in output.faq] != [item.question for item in proposal.faq]:
        errors.append("faq")
    if len(output.cta_blocks) != len(proposal.cta_blocks):
        errors.append("cta_blocks")
    if [item.target_url for item in output.internal_links] != [
        item.target_url for item in proposal.internal_links
    ]:
        errors.append("internal_links")
    lineage_groups = [
        *(item.evidence_ids for item in draftable_sections),
        *(item.evidence_ids for item in proposal.faq),
        *(item.evidence_ids for item in proposal.cta_blocks),
        *(item.evidence_ids for item in proposal.internal_links),
    ]
    if any(not values for values in lineage_groups):
        errors.append("missing_evidence_lineage")
    lineage_atoms = [
        *(
            value
            for item in draftable_sections
            for value in (*item.query_terms, *item.claim_ids)
        ),
        *(value for item in proposal.faq for value in (*item.query_terms, *item.claim_ids)),
        *(value for item in proposal.cta_blocks for value in item.claim_ids),
        *(value for item in proposal.internal_links for value in item.claim_ids),
    ]
    if any(not value.strip() for value in lineage_atoms):
        errors.append("blank_lineage_atom")
    if any(not content_is_safe_public_url(item.target_url) for item in proposal.internal_links):
        errors.append("invalid_internal_link_target")
    return errors


def _claim_safety_output(
    inputs: _InitialDraftInputs,
    output: ContentInitialDraftModelOutput,
) -> StructuredDraftOutput:
    claim_text_by_id = {item.id: item.claim_text for item in inputs.planning_input.claim_ledger}
    sections: list[StructuredDraftOutputSection] = []
    draftable_sections = draftable_planning_sections(inputs.proposal.sections)
    global_claim_ids = [claim_id for item in draftable_sections for claim_id in item.claim_ids]
    sections.append(
        StructuredDraftOutputSection(
            heading="Page assets",
            body_markdown="\n".join(output.page_assets.model_dump(mode="json").values()),
            evidence_ids=inputs.proposal.evidence_ids,
            claims_used=_claim_texts(global_claim_ids, claim_text_by_id),
        )
    )
    for plan, generated in zip(draftable_sections, output.sections, strict=True):
        sections.append(
            StructuredDraftOutputSection(
                heading=generated.heading,
                body_markdown=generated.body_markdown,
                evidence_ids=plan.evidence_ids,
                claims_used=_claim_texts(plan.claim_ids, claim_text_by_id),
            )
        )
    sections.extend(_asset_safety_sections(inputs, output, claim_text_by_id))
    return StructuredDraftOutput(
        draft_kind="full_draft",
        language="pl-PL",
        title=output.page_assets.wordpress_title,
        meta_title=output.page_assets.meta_title,
        meta_description=output.page_assets.meta_description,
        h1=output.page_assets.h1,
        sections=sections,
        faq=[item.answer_markdown for item in output.faq],
        cta="\n".join(item.body_markdown for item in output.cta_blocks),
        internal_links=[item.anchor_text for item in output.internal_links],
        source_facts_used=inputs.planning_input.evidence_ids,
        claims_needing_review=[],
        forbidden_claims_avoided=inputs.generation_contract.model_input.claims_removed_or_blocked,
        human_review_checklist=inputs.generation_contract.model_input.human_review_questions,
        publish_ready=False,
    )


def _asset_safety_sections(
    inputs: _InitialDraftInputs,
    output: ContentInitialDraftModelOutput,
    claim_text_by_id: dict[str, str],
) -> list[StructuredDraftOutputSection]:
    sections: list[StructuredDraftOutputSection] = []
    for index, (faq_plan, faq_output) in enumerate(
        zip(inputs.proposal.faq, output.faq, strict=True)
    ):
        sections.append(
            StructuredDraftOutputSection(
                heading=f"FAQ {index + 1}: {faq_output.question}",
                body_markdown=faq_output.answer_markdown,
                evidence_ids=faq_plan.evidence_ids,
                claims_used=_claim_texts(faq_plan.claim_ids, claim_text_by_id),
            )
        )
    for index, (cta_plan, cta_output) in enumerate(
        zip(inputs.proposal.cta_blocks, output.cta_blocks, strict=True)
    ):
        sections.append(
            StructuredDraftOutputSection(
                heading=f"CTA {index + 1}",
                body_markdown=cta_output.body_markdown,
                evidence_ids=cta_plan.evidence_ids,
                claims_used=_claim_texts(cta_plan.claim_ids, claim_text_by_id),
            )
        )
    for index, (link_plan, link_output) in enumerate(
        zip(inputs.proposal.internal_links, output.internal_links, strict=True)
    ):
        sections.append(
            StructuredDraftOutputSection(
                heading=f"Link {index + 1}",
                body_markdown=link_output.anchor_text,
                evidence_ids=link_plan.evidence_ids,
                claims_used=_claim_texts(link_plan.claim_ids, claim_text_by_id),
            )
        )
    return sections


def _persist_document(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    inputs: _InitialDraftInputs,
    output: ContentInitialDraftModelOutput,
    run: CodexRun,
    trace: ContentCodexRuntimeTrace,
    workflow_store: ContentWorkflowStore,
    run_store: LocalStateStore,
) -> ContentInitialDraftResponse:
    try:
        command = build_initial_draft_revision_command(
            snapshot=snapshot,
            request=request,
            planning_input=inputs.planning_input,
            proposal=inputs.proposal,
            output=output,
            run=run,
            base_revision_id=inputs.base_revision_id,
        )
    except (ValueError, StopIteration):
        blocker = _blocker(
            "document_scope_mismatch",
            "Nie udało się złożyć bezpiecznego dokumentu",
            "Plan i pełny output nie tworzą poprawnej rewizji v2.",
            "Odrzuć wynik i popraw kontrakt wejścia przed ponowną próbą.",
        )
        _finish_run(run_store, run, status="blocked", error=blocker.code)
        return _blocked_response(
            snapshot,
            proposal=inputs.proposal,
            status="blocked",
            run=run,
            runtime=trace,
            blockers=[blocker],
        )
    completed_run = run.model_copy(
        update={"status": "completed", "completed_at": utc_now(), "error": None}
    )
    try:
        result = workflow_store.append_draft_revision(
            command,
            completed_codex_run=completed_run,
        )
    except Exception:
        blocker = _blocker(
            "persistence_failed",
            "Nie zapisano pełnego tekstu",
            "Atomowy zapis dokumentu i zakończonego CodexRun nie powiódł się.",
            "Sprawdź prywatny store i uruchom nową próbę; częściowy tekst nie istnieje.",
        )
        _finish_run(run_store, run, status="failed", error=blocker.code)
        return _blocked_response(
            snapshot,
            proposal=inputs.proposal,
            status="failed",
            run=run,
            runtime=trace,
            blockers=[blocker],
        )
    if result.status == "conflict" or result.revision is None:
        blocker = _blocker(
            "revision_conflict",
            "Pierwsza wersja powstała równolegle",
            "WILQ nie nadpisze istniejącej rewizji wynikiem drugiego turnu.",
            "Odśwież workspace i otwórz już zapisaną wersję.",
        )
        _finish_run(run_store, run, status="blocked", error=blocker.code)
        return _blocked_response(
            snapshot,
            proposal=inputs.proposal,
            status="conflict",
            run=run,
            runtime=trace,
            blockers=[blocker],
        )
    return ContentInitialDraftResponse(
        status="created",
        work_item_id=inputs.planning_input.work_item_id,
        proposal_id=inputs.proposal.proposal_id,
        run_id=run.id,
        revision=result.revision,
        runtime=trace,
        safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
    )


def _claim_texts(claim_ids: list[str], claim_text_by_id: dict[str, str]) -> list[str]:
    return [claim_text_by_id[item] for item in claim_ids if item in claim_text_by_id]


def _start_run(
    inputs: _InitialDraftInputs,
    run_store: LocalStateStore,
    *,
    run_id: str | None = None,
) -> CodexRun:
    work_item_id = inputs.planning_input.work_item_id
    return run_store.save_codex_run(
        CodexRun(
            id=run_id or f"codex_content_initial_draft_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_initial_full_draft",
            source="wilq_api",
        status="started",
        used_endpoints=[f"/api/content/work-items/{work_item_id}/initial-draft"],
        evidence_ids=inputs.planning_input.evidence_ids,
        proposal_id=inputs.proposal.proposal_id,
        planning_input_digest=inputs.planning_input.planning_input_digest,
    )
    )


def _finish_run(
    run_store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> CodexRun:
    return run_store.save_codex_run(
        run.model_copy(update={"status": status, "completed_at": utc_now(), "error": error})
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
    return _blocker(
        "stale_planning_input",
        "Metryki albo kontekst planu zmieniły się",
        "Bieżący planning_input_digest nie odpowiada zatwierdzonej wersji.",
        "Wygeneruj i zatwierdź nowy plan przed tworzeniem tekstu.",
    )


def _blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
    *,
    source_codes: list[str] | None = None,
) -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code=cast(ContentInitialDraftBlockerCode, code),
        label=label,
        reason=reason,
        next_step=next_step,
        source_codes=source_codes or [],
    )


__all__ = ["generate_initial_full_draft"]
