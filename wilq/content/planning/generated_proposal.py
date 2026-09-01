from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Literal
from uuid import uuid4

from pydantic import ValidationError

from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.codex_turn import runtime_trace
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.knowledge.cards import (
    match_content_knowledge_cards,
    select_content_knowledge_service_card,
)
from wilq.content.knowledge.work_item_service_profile import (
    build_content_work_item_service_profile_context,
)
from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    build_content_planning_input,
    content_planning_input_summary,
    planning_generation_blockers,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningModelOutput,
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_persistence import (
    persist_generated_proposal,
    proposal_from_output,
)
from wilq.content.planning.generated_proposal_responses import (
    blocked_from_input as _blocked_from_input,
)
from wilq.content.planning.generated_proposal_responses import (
    blocked_response as _blocked_response,
)
from wilq.content.planning.generated_proposal_responses import (
    planning_runtime_blocker as _planning_runtime_blocker,
)
from wilq.content.planning.generated_proposal_responses import (
    runtime_failure_response as _runtime_failure_response,
)
from wilq.content.planning.generated_proposal_responses import (
    stale_input_blocker as _stale_input_blocker,
)
from wilq.content.planning.generated_proposal_responses import (
    unexpected_planning_input_response as _unexpected_planning_input_response,
)
from wilq.content.planning.generated_proposal_responses import (
    unexpected_runtime_blocker as _unexpected_runtime_blocker,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generated_proposal_turn import content_planning_turn_request
from wilq.content.planning.proposal_lineage import (
    canonicalize_regulatory_section_assertions,
    canonicalize_regulatory_section_evidence,
    planning_output_lineage_errors,
)
from wilq.content.planning.proposal_quality import (
    persisted_inventory_mapping_is_current,
    planning_output_quality_errors,
    proposal_quality_errors,
)
from wilq.content.planning.section_mapping import (
    build_inventory_mapping,
    canonicalize_model_inventory_headings,
)
from wilq.content.planning.subject import ContentPlanningSubject
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import (
    ContentPlanningDecision,
    ContentPlanningInventoryMapping,
    ContentPlanningProposal,
    build_content_planning_workspace,
)
from wilq.content.workflow.refresh_preparation_contracts import ContentRefreshPreparationBinding
from wilq.content.workflow.runtime.codex_run_lifecycle import save_terminal_codex_run
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore, local_state_store


def read_content_planning_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse:
    from wilq.content.planning.proposal_read import read_content_planning_proposal as read

    return read(snapshot=snapshot, store=store)


def with_current_planning_workspace(
    response: ContentPlanningProposalResponse,
    decisions: list[ContentPlanningDecision],
) -> ContentPlanningProposalResponse:
    """Project review only when it binds to the response's exact ready plan."""

    if response.status != "ready" or response.proposal is None:
        return response.model_copy(update={"planning_workspace": None})
    proposal = response.proposal
    exact_decisions = [
        decision
        for decision in decisions
        if decision.work_item_id == proposal.work_item_id
        and decision.planning_digest == proposal.planning_digest
        and (
            decision.service_card_id is None or decision.service_card_id == proposal.service_card_id
        )
    ]
    return response.model_copy(
        update={
            "planning_workspace": build_content_planning_workspace(
                proposal,
                exact_decisions,
            )
        }
    )


def generate_content_planning_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
    client: CodexAppServerClientProtocol,
    store: ContentPlanningProposalStore,
    run_store: LocalStateStore,
    refresh_preparation_binding: ContentRefreshPreparationBinding | None = None,
    pre_persistence_guard: Callable[[], ContentPlanningProposalResponse | None] | None = None,
) -> ContentPlanningProposalResponse:
    planning_input, early_response = _prepare_generation(
        snapshot=snapshot,
        request=request,
        store=store,
    )
    if early_response is not None:
        return early_response
    if planning_input is None:
        return _unexpected_planning_input_response(snapshot, request)
    run = _start_run(planning_input, run_store)
    output, trace, blocker, status = _run_planning_turn(
        planning_input=planning_input,
        operator_hint=request.operator_hint,
        client=client,
    )
    if blocker is not None or output is None:
        failure_status: Literal["blocked", "failed"] = status or "failed"
        failure_blocker = blocker or _unexpected_runtime_blocker()
        _finish_run(
            run_store,
            run,
            status=failure_status,
            error=_run_error_code(failure_blocker),
        )
        return _runtime_failure_response(
            planning_input,
            failure_blocker,
            status=failure_status,
            trace=trace,
            run_id=run.id,
        )
    completed_run = run.model_copy(
        update={"status": "completed", "completed_at": utc_now(), "error": None}
    )
    proposal = proposal_from_output(
        planning_input,
        output,
        completed_run,
        refresh_preparation_binding=refresh_preparation_binding,
    )
    return persist_generated_proposal(
        planning_input=planning_input,
        request=request,
        proposal=proposal,
        completed_run=completed_run,
        started_run=run,
        trace=trace,
        store=store,
        run_store=run_store,
        pre_persistence_guard=pre_persistence_guard,
        finish_run=_finish_persisted_run,
        runtime_failure_response=_persistence_failure_response,
        runtime_trace_with_run_id=_runtime_trace_with_run_id,
    )


def queue_content_planning_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse:
    """Create a durable in-flight marker without invoking Codex on the request path."""
    planning_input, early_response = _prepare_generation(
        snapshot=snapshot,
        request=request,
        store=store,
    )
    if early_response is not None:
        return early_response
    if planning_input is None:
        return _unexpected_planning_input_response(snapshot, request)
    response = ContentPlanningProposalResponse(
        status="generating",
        work_item_id=planning_input.work_item_id,
        content_kind=planning_input.content_kind,
        service_card_id=request.service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        safe_next_step=(
            "Plan jest przygotowywany; ten widok odświeży się po zakończeniu "
            "bez ponownego wysyłania danych."
        ),
    )
    store.enqueue(response)
    return response


def _content_kind_mismatch_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
) -> ContentPlanningProposalResponse | None:
    if (
        snapshot.preflight.item.content_kind not in {"service", "editorial"}
        or snapshot.preflight.item.content_kind == request.content_kind
    ):
        return None
    return _blocked_response(
        snapshot.preflight.item.id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        planning_input_digest=None,
        blockers=[
            build_blocker(
                ContentPlanningProposalBlocker,
                code="content_kind_mismatch",
                label="Typ treści zmienił się przed planowaniem",
                reason="Żądanie nie odpowiada bieżącej klasyfikacji strony.",
                next_step="Odśwież workspace i użyj aktualnego typu treści.",
            )
        ],
    )


def _prepare_generation(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
    store: ContentPlanningProposalStore,
) -> tuple[ContentPlanningInput | None, ContentPlanningProposalResponse | None]:
    if mismatch := _content_kind_mismatch_response(snapshot, request):
        return None, mismatch
    if request.content_kind == "service" and request.service_card_id not in {
        candidate.service_card_id
        for candidate in snapshot.service_profile_context.service_candidates
    }:
        return None, _blocked_response(
            snapshot.preflight.item.id,
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
            planning_input_digest=None,
            blockers=[
                build_blocker(
                    ContentPlanningProposalBlocker,
                    code="unknown_service_card",
                    label="Usługa nie należy do tego zadania",
                    reason="Wybrana karta nie wynika z dokładnego dopasowania strony i wiedzy WILQ.",  # noqa: E501
                    next_step="Wybierz jedną z usług pokazanych dla tej strony.",
                )
            ],
        )
    planning_snapshot = (
        with_explicit_content_service_selection(snapshot, request.service_card_id)
        if request.content_kind == "service" and request.service_card_id is not None
        else snapshot
    )
    result = build_content_planning_input(
        planning_snapshot,
        service_card_id=request.service_card_id,
    )
    if result.planning_input is None:
        return None, _blocked_from_input(
            snapshot.preflight.item.id,
            request.service_card_id,
            result.blockers,
            content_kind=request.content_kind,
        )
    planning_input = result.planning_input
    input_summary = content_planning_input_summary(planning_input)
    generation_blockers = planning_generation_blockers(result.blockers)
    if generation_blockers:
        return None, _blocked_from_input(
            planning_input.work_item_id,
            request.service_card_id,
            generation_blockers,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            content_kind=request.content_kind,
        )
    if request.expected_planning_input_digest != planning_input.planning_input_digest:
        return None, ContentPlanningProposalResponse(
            status="stale",
            work_item_id=planning_input.work_item_id,
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            blockers=[_stale_input_blocker()],
            safe_next_step="Odśwież wejście i świadomie uruchom nową wersję planu.",
        )
    existing = store.for_subject_input(
        planning_input.work_item_id,
        ContentPlanningSubject(
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
        ),
        planning_input.planning_input_digest,
    )
    if existing is not None and not (
        request.regenerate_stale_mapping or request.regenerate_after_review
    ):
        if (
            proposal_quality_errors(existing)
            or any(
                mapping.status in {"unmapped", "ambiguous"}
                for mapping in existing.inventory_mapping
            )
            or not persisted_inventory_mapping_is_current(planning_input, existing)
        ):
            return planning_input, None
        return None, ContentPlanningProposalResponse(
            status="idempotent",
            work_item_id=planning_input.work_item_id,
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            proposal=existing,
            refresh_preparation_binding=existing.refresh_preparation_binding,
            safe_next_step="Sprawdź zapisaną wersję planu; model nie został uruchomiony ponownie.",
        )
    return planning_input, None


def with_explicit_content_service_selection(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    service_card_id: str,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Bind an exact service choice to one planning-derived command.

    This deliberately does not write a legacy planning decision. The only
    human approval in the active content journey belongs to the immutable
    document revision, after the full document is visible.
    """

    item = snapshot.preflight.item
    match = select_content_knowledge_service_card(
        match_content_knowledge_cards(item),
        service_card_id,
    )
    context = build_content_work_item_service_profile_context(
        item,
        knowledge_match=match,
        service_selection_confirmed=True,
    )
    return snapshot.model_copy(update={"service_profile_context": context})


def _run_planning_turn(
    *,
    planning_input: ContentPlanningInput,
    operator_hint: str,
    client: CodexAppServerClientProtocol,
) -> tuple[
    ContentPlanningModelOutput | None,
    ContentCodexRuntimeTrace | None,
    ContentPlanningProposalBlocker | None,
    Literal["blocked", "failed"] | None,
]:
    try:
        runtime_result = client.run_structured_turn(
            content_planning_turn_request(
                planning_input,
                operator_hint=operator_hint,
            )
        )
    except Exception as error:
        blocker = build_blocker(
            ContentPlanningProposalBlocker,
            code="runtime_failed",
            label="Codex nie zakończył planowania",
            reason="Lokalny app-server zakończył się błędem bez wyniku.",
            next_step="Sprawdź status Codexa i uruchom nową próbę; plan nie został zapisany.",
            source_codes=[type(error).__name__],
        )
        return None, None, blocker, "failed"
    trace = runtime_trace(runtime_result)
    if runtime_result.status != "completed" or runtime_result.output_text is None:
        status: Literal["blocked", "failed"] = (
            "blocked" if runtime_result.status == "blocked" else "failed"
        )
        runtime_blocker = _planning_runtime_blocker(
            [entry.code for entry in runtime_result.blockers]
        )
        blocker = build_blocker(
            ContentPlanningProposalBlocker,
            code="runtime_blocked" if status == "blocked" else "runtime_failed",
            label=runtime_blocker[0],
            reason=runtime_blocker[1],
            next_step=runtime_blocker[2],
            source_codes=[entry.code for entry in runtime_result.blockers],
        )
        return None, trace, blocker, status
    try:
        output = ContentPlanningModelOutput.model_validate_json(runtime_result.output_text)
    except ValidationError as error:
        blocker = build_blocker(
            ContentPlanningProposalBlocker,
            code="invalid_structured_output",
            label="Codex zwrócił niepoprawny plan",
            reason="Wynik nie przeszedł ścisłego schematu planowania WILQ.",
            next_step="Odrzuć wynik i uruchom nową próbę po sprawdzeniu kontraktu.",
            source_codes=_validation_source_codes(error),
        )
        return None, trace, blocker, "blocked"
    except ValueError:
        blocker = build_blocker(
            ContentPlanningProposalBlocker,
            code="invalid_structured_output",
            label="Codex zwrócił niepoprawny plan",
            reason="Wynik nie przeszedł ścisłego schematu planowania WILQ.",
            next_step="Odrzuć wynik i uruchom nową próbę po sprawdzeniu kontraktu.",
        )
        return None, trace, blocker, "blocked"
    output, output_blocker = _validated_planning_output(planning_input, output)
    if output_blocker is not None:
        return None, trace, output_blocker, "blocked"
    return output, trace, None, None


def _validated_planning_output(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> tuple[ContentPlanningModelOutput, ContentPlanningProposalBlocker | None]:
    if (
        output.content_kind != planning_input.content_kind
        or output.service_card_id != planning_input.confirmed_service_card_id
    ):
        return output, build_blocker(
            ContentPlanningProposalBlocker,
            code="lineage_mismatch",
            label="Plan ma inną tożsamość treści",
            reason="Wynik nie odpowiada typowi i subjectowi exact planning input.",
            next_step="Odrzuć wynik i uruchom ponownie planowanie z bieżącego wejścia.",
            source_codes=["planning_subject_mismatch"],
        )
    output = canonicalize_model_inventory_headings(planning_input, output)
    output = canonicalize_regulatory_section_evidence(planning_input, output)
    output = canonicalize_regulatory_section_assertions(planning_input, output)
    quality_errors = planning_output_quality_errors(output, planning_input=planning_input)
    if quality_errors:
        return output, _quality_gate_blocker(quality_errors)
    lineage_errors = planning_output_lineage_errors(planning_input, output)
    if lineage_errors:
        return output, build_blocker(
            ContentPlanningProposalBlocker,
            code="lineage_mismatch",
            label="Plan używa danych spoza wejścia",
            reason="Codex zwrócił zapytanie, dowód, claim albo inventory spoza exact inputu.",
            next_step="Odrzuć wynik; nie poprawiaj obcego lineage ręcznie.",
            source_codes=lineage_errors,
        )
    return output, None


def _quality_gate_blocker(quality_errors: list[str]) -> ContentPlanningProposalBlocker:
    return build_blocker(
        ContentPlanningProposalBlocker,
        code="quality_gate_failed",
        label="Plan nie przeszedł bramki jakości",
        reason=_quality_gate_reason(quality_errors),
        next_step=(
            "Uruchom nową próbę po oczyszczeniu materiału wejściowego; WILQ nic nie "
            "zapisał."
        ),
        source_codes=quality_errors,
    )


def _quality_gate_reason(quality_errors: list[str]) -> str:
    if "missing_cta" in quality_errors:
        return "Plan nie zawiera żadnego bloku CTA wymaganego dla bezpiecznego następnego kroku."
    if "cta_pattern_coverage" in quality_errors:
        return "Plan nie obejmuje wszystkich zatwierdzonych wzorców CTA dokładnie po jednym razie."
    if "missing_query_assignments" in quality_errors:
        return "Plan zawiera exact zapytania, ale nie przypisuje żadnego z nich do sekcji."
    if {"missing_measurement_metrics", "missing_measurement_evidence"}.intersection(
        quality_errors
    ):
        return "Plan ma dostępne sygnały pomiarowe, ale nie zawiera ich w planie obserwacji."
    return (
        "Plan zawiera nagłówki nawigacyjne, promocyjne albo datowane, które nie są "
        "użyteczną strukturą odpowiedzi dla czytelnika."
    )


def _validation_source_codes(error: ValidationError) -> list[str]:
    """Expose safe schema locations without persisting model output."""

    codes: list[str] = []
    for detail in error.errors():
        location = ".".join(str(part) for part in detail.get("loc", ())) or "$"
        error_type = str(detail.get("type", "validation_error"))
        suffix = ""
        if location == "$" and error_type == "value_error":
            suffix = f":{_root_validation_reason_code(str(detail.get('msg', '')))}"
        code = f"schema:{location}:{error_type}{suffix}"[:160]
        if code not in codes:
            codes.append(code)
    return codes[:12]


def _root_validation_reason_code(message: str) -> str:
    """Classify root-model failures without exposing model output text."""

    patterns = (
        ("section headings must be unique", "duplicate_section_headings"),
        ("placement must name", "invalid_placement"),
        ("remove_review_required", "removed_section_placement"),
        ("every page asset", "missing_page_asset"),
        ("every faq item", "missing_faq_evidence"),
        ("every cta block", "missing_cta_evidence"),
        ("every internal link", "missing_internal_link_evidence"),
        ("internal-link targets must be unique", "duplicate_internal_link"),
        ("observation rule", "missing_measurement_observation_rule"),
        ("success-claim rule", "missing_measurement_success_claim_rule"),
    )
    lowered = re.sub(r"\s+", " ", message).strip().lower()
    for phrase, code in patterns:
        if phrase in lowered:
            return code
    return "root_contract"


_HEADING_NOISE_PATTERNS = (
    (
        "heading_navigation_noise",
        re.compile(r"^(?:zaufali nam|copyright|menu|więcej)\b", re.I),
    ),
    (
        "heading_presentation_noise",
        re.compile(r"^poniżej przedstawiamy\b", re.I),
    ),
    (
        "heading_promotional_noise",
        re.compile(r"^dowiedz się więcej .* podczas", re.I),
    ),
    (
        "heading_related_content_noise",
        re.compile(r"^(?:powiązane materiały|zobacz także|materiały powiązane)\b", re.I),
    ),
    (
        "heading_dated_event_noise",
        re.compile(
            r"\b\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|"
            r"sierpnia|września|października|listopada|grudnia)\s+\d{4}\b",
            re.I,
        ),
    ),
)


def _planning_output_quality_errors(
    output: ContentPlanningModelOutput,
    *,
    planning_input: ContentPlanningInput | None = None,
) -> list[str]:
    errors = _planning_heading_quality_errors(section.heading for section in output.sections)
    required_cta_blocks = (
        1 if planning_input is None else getattr(planning_input, "minimum_cta_blocks", 1)
    )
    if len(output.cta_blocks) < required_cta_blocks:
        errors.append("missing_cta")
    required_patterns = list(getattr(planning_input, "required_cta_patterns", []))
    if required_patterns:
        observed_patterns = [item.copy_direction.strip() for item in output.cta_blocks]
        if len(observed_patterns) != len(required_patterns) or set(observed_patterns) != set(
            required_patterns
        ):
            errors.append("cta_pattern_coverage")
    errors.extend(
        _orphaned_placement_quality_errors(
            sections=output.sections,
            placements=_placement_values(output.cta_blocks)
            + _placement_values(output.internal_links),
        )
    )
    if (
        planning_input is not None
        and _has_exact_query_rows(planning_input)
        and not any(section.query_terms for section in output.sections)
    ):
        errors.append("missing_query_assignments")
    if (
        planning_input is not None
        and getattr(planning_input, "measurement_metrics", [])
        and not output.measurement_plan.metrics_to_watch
    ):
        errors.append("missing_measurement_metrics")
    if (
        planning_input is not None
        and getattr(planning_input, "measurement_baseline_evidence_ids", [])
        and not output.measurement_plan.baseline_evidence_ids
    ):
        errors.append("missing_measurement_evidence")
    return list(dict.fromkeys(errors))


def _proposal_quality_errors(proposal: ContentPlanningProposal) -> list[str]:
    errors = _planning_heading_quality_errors(section.heading for section in proposal.sections)
    if len(proposal.cta_blocks) < proposal.minimum_cta_blocks:
        errors.append("missing_cta")
    if proposal.required_cta_patterns:
        observed_patterns = [item.copy_direction.strip() for item in proposal.cta_blocks]
        if len(observed_patterns) != len(proposal.required_cta_patterns) or set(
            observed_patterns
        ) != set(proposal.required_cta_patterns):
            errors.append("cta_pattern_coverage")
    errors.extend(
        _orphaned_placement_quality_errors(
            sections=proposal.sections,
            placements=_placement_values(proposal.cta_blocks)
            + _placement_values(proposal.internal_links),
        )
    )
    if _has_exact_query_rows(proposal.search_demand) and not any(
        section.query_terms for section in proposal.sections
    ):
        errors.append("missing_query_assignments")
    if proposal.measurement_metrics and not proposal.measurement_plan.metrics_to_watch:
        errors.append("missing_measurement_metrics")
    if (
        proposal.measurement_baseline_evidence_ids
        and not proposal.measurement_plan.baseline_evidence_ids
    ):
        errors.append("missing_measurement_evidence")
    return list(dict.fromkeys(errors))


def _has_exact_query_rows(value: object) -> bool:
    """Return whether a portfolio contains any exact query/term rows."""

    if hasattr(value, "query_portfolio"):
        value = value.query_portfolio
    return any(
        bool(getattr(value, field, []))
        for field in ("gsc_query_rows", "ads_term_rows", "keyword_planner_rows")
    )


def _orphaned_placement_quality_errors(
    *,
    sections: Iterable[object],
    placements: Iterable[str],
) -> list[str]:
    removed_targets = {
        target
        for section in sections
        if getattr(section, "inventory_disposition", None) == "remove_review_required"
        for target in (
            getattr(section, "heading", None),
            getattr(section, "section_id", None),
            getattr(section, "inventory_section_id", None),
        )
        if target
    }
    return ["orphaned_placement"] if removed_targets.intersection(placements) else []


def _placement_values(items: Iterable[object]) -> list[str]:
    return [
        placement
        for item in items
        if isinstance(placement := getattr(item, "placement", None), str)
    ]


def _expected_inventory_mapping(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> list[ContentPlanningInventoryMapping]:
    return build_inventory_mapping(
        planning_input,
        proposal,
        [section.section_id for section in proposal.sections],
    )


def _persisted_inventory_mapping_is_current(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> bool:
    return _expected_inventory_mapping(planning_input, proposal) == proposal.inventory_mapping


def _inventory_mapping_has_unresolved_rows(
    proposal: ContentPlanningProposal,
) -> bool:
    return any(
        mapping.status in {"unmapped", "ambiguous"} for mapping in proposal.inventory_mapping
    )


def _remapped_proposal_projection(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> ContentPlanningProposal:
    return proposal.model_copy(
        update={"inventory_mapping": _expected_inventory_mapping(planning_input, proposal)}
    )


def _planning_heading_quality_errors(headings: Iterable[str]) -> list[str]:
    errors: list[str] = []
    for raw_heading in headings:
        heading = str(raw_heading).strip()
        for code, pattern in _HEADING_NOISE_PATTERNS:
            if pattern.search(heading):
                errors.append(code)
    return list(dict.fromkeys(errors))


def _start_run(
    planning_input: ContentPlanningInput,
    run_store: LocalStateStore,
) -> CodexRun:
    return run_store.save_codex_run(
        CodexRun(
            id=f"codex_content_planning_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_planning_proposal",
            source="wilq_api",
            status="started",
            used_endpoints=[
                f"/api/content/work-items/{planning_input.work_item_id}/planning-proposals"
            ],
            evidence_ids=planning_input.evidence_ids,
            planning_input_digest=planning_input.planning_input_digest,
        )
    )


def _run_error_code(
    blocker: ContentPlanningProposalBlocker,
) -> str:
    """Persist only typed runtime codes, never model or transport payloads."""

    if blocker.source_codes:
        return ":".join((blocker.code, *blocker.source_codes))
    return blocker.code


def _finish_run(
    run_store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> CodexRun:
    return save_terminal_codex_run(run_store, run, status=status, error=error)


def _finish_persisted_run(
    run_store: LocalStateStore,
    run: CodexRun,
    status: Literal["blocked", "failed"],
    error: str,
) -> None:
    _finish_run(run_store, run, status=status, error=error)


def _persistence_failure_response(
    planning_input: ContentPlanningInput,
    blocker: ContentPlanningProposalBlocker,
    status: Literal["blocked", "failed"],
    trace: ContentCodexRuntimeTrace | None,
    run_id: str,
) -> ContentPlanningProposalResponse:
    return _runtime_failure_response(
        planning_input,
        blocker,
        status=status,
        trace=trace,
        run_id=run_id,
    )


def _runtime_trace_with_run_id(
    trace: ContentCodexRuntimeTrace | None,
    run_id: str,
) -> ContentCodexRuntimeTrace:
    if trace is None:
        return ContentCodexRuntimeTrace(status="completed", run_id=run_id)
    return trace.model_copy(update={"run_id": run_id})


def persisted_runtime_trace(proposal: ContentPlanningProposal) -> ContentCodexRuntimeTrace:
    """Keep a completed plan from looking like it never reached Codex after reload."""

    if not proposal.codex_run_id:
        return ContentCodexRuntimeTrace(status="not_started")
    run = local_state_store().get_codex_run(proposal.codex_run_id)
    if run is None:
        return ContentCodexRuntimeTrace(status="not_started")
    runtime_status: Literal["not_started", "completed", "blocked", "failed"] = (
        "completed"
        if run.status == "completed"
        else "failed"
        if run.status == "failed"
        else "blocked"
        if run.status == "blocked"
        else "not_started"
    )
    return ContentCodexRuntimeTrace(
        status=runtime_status,
        run_id=run.id,
        external_call_attempted=run.status in {"completed", "failed", "blocked"},
    )


_persisted_runtime_trace = persisted_runtime_trace


__all__ = [
    "generate_content_planning_proposal",
    "persisted_runtime_trace",
    "queue_content_planning_proposal",
    "read_content_planning_proposal",
    "with_explicit_content_service_selection",
]
