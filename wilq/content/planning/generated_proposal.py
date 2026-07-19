from __future__ import annotations

import json
import re
from collections.abc import Iterable
from hashlib import sha256
from typing import Literal, cast
from uuid import uuid4

from pydantic import ValidationError

from wilq.codex.app_server import CodexAppServerClientProtocol, CodexAppServerTurnResult
from wilq.content.drafts.codex_section_proposal_contracts import ContentCodexRuntimeTrace
from wilq.content.knowledge.cards import (
    match_content_knowledge_cards,
    select_content_knowledge_service_card,
)
from wilq.content.knowledge.work_item_service_profile import (
    build_content_work_item_service_profile_context,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBlocker,
    ContentPlanningInputSummary,
    build_content_planning_input,
    content_planning_input_summary,
    planning_generation_blockers,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningModelOutput,
    ContentPlanningProposalBlocker,
    ContentPlanningProposalBlockerCode,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generated_proposal_turn import content_planning_turn_request
from wilq.content.planning.section_mapping import (
    build_inventory_mapping,
    canonicalize_model_inventory_headings,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.planning import (
    ContentPlanningInventoryMapping,
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore, local_state_store


def read_content_planning_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse:
    service_card_id = snapshot.service_profile_context.service_card_id
    if service_card_id is None:
        return _blocked_response(
            snapshot.preflight.item.id,
            service_card_id=None,
            planning_input_digest=None,
            blockers=[
                _blocker(
                    "unknown_service_card",
                    "Brakuje usługi do planowania",
                    "Bieżący snapshot nie ma dozwolonej karty usługi.",
                    "Wybierz work item z dokładnym dopasowaniem Service Profile.",
                )
            ],
        )
    planning_snapshot = _snapshot_with_explicit_service_selection(snapshot, service_card_id)
    result = build_content_planning_input(
        planning_snapshot,
        service_card_id=service_card_id,
    )
    if result.planning_input is None:
        return _blocked_from_input(
            snapshot.preflight.item.id,
            service_card_id,
            result.blockers,
        )
    planning_input = result.planning_input
    input_summary = content_planning_input_summary(planning_input)
    generation_blockers = planning_generation_blockers(result.blockers)
    if generation_blockers:
        return _blocked_from_input(
            planning_input.work_item_id,
            service_card_id,
            generation_blockers,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
        )
    queued = store.queued_response(
        planning_input.work_item_id,
        service_card_id,
        planning_input.planning_input_digest,
    )
    if queued is not None:
        return queued.model_copy(
            update={
                "planning_input_digest": planning_input.planning_input_digest,
                "input_summary": input_summary,
            }
        )
    # A newer proposal for another input digest must not shadow an exact
    # proposal that is valid for the current fixed point. History remains
    # immutable, but reads are keyed by the requested input first.
    latest = store.for_input(
        planning_input.work_item_id,
        service_card_id,
        planning_input.planning_input_digest,
    ) or store.latest(planning_input.work_item_id)
    if latest is None:
        return ContentPlanningProposalResponse(
            status="not_generated",
            work_item_id=planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            safe_next_step="Wygeneruj pierwszy plan i sprawdź go przed decyzją człowieka.",
        )
    if (
        latest.service_card_id != service_card_id
        or latest.planning_input_digest != planning_input.planning_input_digest
    ):
        return ContentPlanningProposalResponse(
            status="stale",
            work_item_id=planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            proposal=latest,
            blockers=[_stale_input_blocker()],
            safe_next_step="Wygeneruj nową wersję planu z aktualnego wejścia.",
        )
    persisted_quality_errors = _proposal_quality_errors(latest)
    if persisted_quality_errors:
        return ContentPlanningProposalResponse(
            status="blocked",
            work_item_id=planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            proposal=latest,
            blockers=[
                _blocker(
                    "quality_gate_failed",
                    "Zapisany plan wymaga ponownego wygenerowania",
                    "Ostatnia wersja zawiera nagłówki, które nie są użyteczną strukturą "
                    "odpowiedzi dla czytelnika.",
                    "Uruchom plan ponownie; poprzednia wersja nie jest gotowa do review.",
                    source_codes=persisted_quality_errors,
                )
            ],
            safe_next_step="Uruchom nową próbę planowania z aktualnego wejścia.",
        )
    if (
        not _persisted_inventory_mapping_is_current(planning_input, latest)
        or _inventory_mapping_has_unresolved_rows(latest)
    ):
        remapped = _remapped_proposal_projection(planning_input, latest)
        return ContentPlanningProposalResponse(
            status="stale",
            work_item_id=planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            proposal=remapped,
            blockers=[
                _blocker(
                    "stale_input",
                    "Mapa istniejącej strony wymaga odświeżenia",
                    "Zapisany plan nie zawiera aktualnej, deterministycznej mapy sekcji inventory.",
                    "Uruchom nową wersję planu; WILQ ponownie przypisze sekcje "
                    "bez ręcznego mapowania.",
                )
            ],
            safe_next_step="Uruchom nową wersję planu, aby odświeżyć automatyczną mapę sekcji.",
        )
    return ContentPlanningProposalResponse(
        status="ready",
        work_item_id=planning_input.work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=input_summary,
        proposal=latest,
        runtime=_persisted_runtime_trace(latest),
        safe_next_step="Sprawdź strategię i mapę sekcji; tylko człowiek może je zatwierdzić.",
    )


def generate_content_planning_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
    client: CodexAppServerClientProtocol,
    store: ContentPlanningProposalStore,
    run_store: LocalStateStore,
) -> ContentPlanningProposalResponse:
    planning_input, early_response = _prepare_generation(
        snapshot=snapshot,
        request=request,
        store=store,
    )
    if early_response is not None:
        return early_response
    assert planning_input is not None
    run = _start_run(planning_input, run_store)
    output, trace, blocker, status = _run_planning_turn(
        planning_input=planning_input,
        operator_hint=request.operator_hint,
        client=client,
    )
    if blocker is not None:
        assert status is not None
        _finish_run(
            run_store,
            run,
            status=status,
            error=_run_error_code(blocker),
        )
        return _runtime_failure_response(
            planning_input,
            blocker,
            status=status,
            trace=trace,
            run_id=run.id,
        )
    assert output is not None
    completed_run = run.model_copy(
        update={"status": "completed", "completed_at": utc_now(), "error": None}
    )
    proposal = _proposal_from_output(planning_input, output, completed_run)
    return _persist_generated_proposal(
        planning_input=planning_input,
        request=request,
        proposal=proposal,
        completed_run=completed_run,
        started_run=run,
        trace=trace,
        store=store,
        run_store=run_store,
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
    assert planning_input is not None
    response = ContentPlanningProposalResponse(
        status="generating",
        work_item_id=planning_input.work_item_id,
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


def _prepare_generation(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
    store: ContentPlanningProposalStore,
) -> tuple[ContentPlanningInput | None, ContentPlanningProposalResponse | None]:
    if request.service_card_id not in {
        candidate.service_card_id
        for candidate in snapshot.service_profile_context.service_candidates
    }:
        return None, _blocked_response(
            snapshot.preflight.item.id,
            service_card_id=request.service_card_id,
            planning_input_digest=None,
            blockers=[
                _blocker(
                    "unknown_service_card",
                    "Usługa nie należy do tego zadania",
                    "Wybrana karta nie wynika z dokładnego dopasowania strony i wiedzy WILQ.",
                    "Wybierz jedną z usług pokazanych dla tej strony.",
                )
            ],
        )
    planning_snapshot = _snapshot_with_explicit_service_selection(
        snapshot,
        request.service_card_id,
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
        )
    if request.expected_planning_input_digest != planning_input.planning_input_digest:
        return None, ContentPlanningProposalResponse(
            status="stale",
            work_item_id=planning_input.work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            blockers=[_stale_input_blocker()],
            safe_next_step="Odśwież wejście i świadomie uruchom nową wersję planu.",
        )
    existing = store.for_input(
        planning_input.work_item_id,
        request.service_card_id,
        planning_input.planning_input_digest,
    )
    if existing is not None and not request.regenerate_stale_mapping:
        if (
            _proposal_quality_errors(existing)
            or any(
                mapping.status in {"unmapped", "ambiguous"}
                for mapping in existing.inventory_mapping
            )
            or not _persisted_inventory_mapping_is_current(planning_input, existing)
        ):
            return planning_input, None
        return None, ContentPlanningProposalResponse(
            status="idempotent",
            work_item_id=planning_input.work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            proposal=existing,
            safe_next_step="Sprawdź zapisaną wersję planu; model nie został uruchomiony ponownie.",
        )
    return planning_input, None


def _snapshot_with_explicit_service_selection(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    service_card_id: str,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Treat the POST/preview card choice as a human service-selection action.

    It deliberately does not save planning scope approval. The generated plan
    remains unreviewed and later stages still require the persisted scope and
    section-map decisions.
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
    except Exception:
        blocker = _blocker(
            "runtime_failed",
            "Codex nie zakończył planowania",
            "Lokalny app-server zakończył się błędem bez wyniku.",
            "Sprawdź status Codexa i uruchom nową próbę; plan nie został zapisany.",
        )
        return None, None, blocker, "failed"
    trace = _runtime_trace(runtime_result)
    if runtime_result.status != "completed" or runtime_result.output_text is None:
        status: Literal["blocked", "failed"] = (
            "blocked" if runtime_result.status == "blocked" else "failed"
        )
        runtime_blocker = _planning_runtime_blocker(
            [entry.code for entry in runtime_result.blockers]
        )
        blocker = _blocker(
            "runtime_blocked" if status == "blocked" else "runtime_failed",
            runtime_blocker[0],
            runtime_blocker[1],
            runtime_blocker[2],
            source_codes=[entry.code for entry in runtime_result.blockers],
        )
        return None, trace, blocker, status
    try:
        output = ContentPlanningModelOutput.model_validate_json(runtime_result.output_text)
    except ValidationError as error:
        blocker = _blocker(
            "invalid_structured_output",
            "Codex zwrócił niepoprawny plan",
            "Wynik nie przeszedł ścisłego schematu planowania WILQ.",
            "Odrzuć wynik i uruchom nową próbę po sprawdzeniu kontraktu.",
            source_codes=_validation_source_codes(error),
        )
        return None, trace, blocker, "blocked"
    except ValueError:
        blocker = _blocker(
            "invalid_structured_output",
            "Codex zwrócił niepoprawny plan",
            "Wynik nie przeszedł ścisłego schematu planowania WILQ.",
            "Odrzuć wynik i uruchom nową próbę po sprawdzeniu kontraktu.",
        )
        return None, trace, blocker, "blocked"
    output = canonicalize_model_inventory_headings(planning_input, output)
    quality_errors = _planning_output_quality_errors(output)
    if quality_errors:
        quality_reason = (
            "Plan nie zawiera żadnego bloku CTA wymaganego dla bezpiecznego następnego kroku."
            if "missing_cta" in quality_errors
            else "Plan zawiera nagłówki nawigacyjne, promocyjne albo datowane, "
            "które nie są użyteczną strukturą odpowiedzi dla czytelnika."
        )
        blocker = _blocker(
            "quality_gate_failed",
            "Plan nie przeszedł bramki jakości",
            quality_reason,
            "Uruchom nową próbę po oczyszczeniu materiału wejściowego; WILQ nic nie zapisał.",
            source_codes=quality_errors,
        )
        return None, trace, blocker, "blocked"
    lineage_errors = _lineage_errors(planning_input, output)
    if lineage_errors:
        blocker = _blocker(
            "lineage_mismatch",
            "Plan używa danych spoza wejścia",
            "Codex zwrócił zapytanie, dowód, claim albo inventory spoza exact inputu.",
            "Odrzuć wynik; nie poprawiaj obcego lineage ręcznie.",
            source_codes=lineage_errors,
        )
        return None, trace, blocker, "blocked"
    return output, trace, None, None


def _validation_source_codes(error: ValidationError) -> list[str]:
    """Expose safe schema locations without persisting model output."""

    codes: list[str] = []
    for detail in error.errors():
        location = ".".join(str(part) for part in detail.get("loc", ())) or "$"
        error_type = str(detail.get("type", "validation_error"))
        code = f"schema:{location}:{error_type}"[:160]
        if code not in codes:
            codes.append(code)
    return codes[:12]


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
) -> list[str]:
    errors = _planning_heading_quality_errors(section.heading for section in output.sections)
    if not output.cta_blocks:
        errors.append("missing_cta")
    errors.extend(
        _orphaned_placement_quality_errors(
            sections=output.sections,
            placements=[
                *(item.placement for item in output.cta_blocks),
                *(item.placement for item in output.internal_links),
            ],
        )
    )
    return list(dict.fromkeys(errors))


def _proposal_quality_errors(proposal: ContentPlanningProposal) -> list[str]:
    errors = _planning_heading_quality_errors(section.heading for section in proposal.sections)
    if not proposal.cta_blocks:
        errors.append("missing_cta")
    errors.extend(
        _orphaned_placement_quality_errors(
            sections=proposal.sections,
            placements=[
                *(item.placement for item in proposal.cta_blocks),
                *(item.placement for item in proposal.internal_links),
            ],
        )
    )
    return list(dict.fromkeys(errors))


def _orphaned_placement_quality_errors(
    *,
    sections: Iterable[object],
    placements: Iterable[str],
) -> list[str]:
    removed_headings = {
        section.heading
        for section in sections
        if getattr(section, "inventory_disposition", None) == "remove_review_required"
    }
    return ["orphaned_placement"] if removed_headings.intersection(placements) else []


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
        mapping.status in {"unmapped", "ambiguous"}
        for mapping in proposal.inventory_mapping
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


def _persist_generated_proposal(
    *,
    planning_input: ContentPlanningInput,
    request: ContentPlanningProposalRequest,
    proposal: ContentPlanningProposal,
    completed_run: CodexRun,
    started_run: CodexRun,
    trace: ContentCodexRuntimeTrace | None,
    store: ContentPlanningProposalStore,
    run_store: LocalStateStore,
) -> ContentPlanningProposalResponse:
    try:
        store_status, stored = store.save_generated(proposal, completed_run)
    except Exception:
        blocker = _blocker(
            "persistence_failed",
            "Nie zapisano planu",
            "Atomowy zapis planu i zakończonego CodexRun nie powiódł się.",
            "Sprawdź prywatny store i uruchom nową próbę; częściowy plan nie jest dostępny.",
        )
        _finish_run(run_store, started_run, status="failed", error=blocker.code)
        return _runtime_failure_response(
            planning_input,
            blocker,
            status="failed",
            trace=trace,
            run_id=started_run.id,
        )
    return ContentPlanningProposalResponse(
        status="created" if store_status == "created" else "idempotent",
        work_item_id=planning_input.work_item_id,
        service_card_id=request.service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        proposal=stored,
        runtime=_runtime_trace_with_run_id(trace, started_run.id),
        safe_next_step="Sprawdź strategię i każdą sekcję; plan pozostaje niezatwierdzony.",
    )


def _proposal_from_output(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
    run: CodexRun,
) -> ContentPlanningProposal:
    proposal_id = f"content_planning_proposal_{uuid4().hex}"
    sections = [
        ContentPlanningSection(
            section_id=f"{proposal_id}_section_{index:02d}",
            source_material_ids=_lineage_ids_for_evidence(
                planning_input.source_facts,
                section.evidence_ids,
                field="source_material_ids",
            ),
            knowledge_card_ids=_lineage_ids_for_evidence(
                planning_input.source_facts,
                section.evidence_ids,
                field="knowledge_card_ids",
            ),
            **section.model_dump(),
        )
        for index, section in enumerate(output.sections, start=1)
    ]
    proposal = ContentPlanningProposal(
        work_item_id=planning_input.work_item_id,
        planning_digest="0" * 64,
        proposal_id=proposal_id,
        codex_run_id=run.id,
        generation_status="codex_generated",
        input_schema_version=planning_input.schema_name,
        criteria_version=planning_input.criteria_version,
        planning_input_digest=planning_input.planning_input_digest,
        final_canonical_url=planning_input.final_canonical_url,
        service_card_id=planning_input.confirmed_service_card_id,
        service_label=planning_input.service_label,
        service_selection_confirmed=True,
        target_reader=output.target_reader,
        buyer_problem=output.buyer_problem,
        buyer_trigger=output.buyer_trigger,
        search_intent=output.search_intent,
        angle=output.angle,
        value_proposition=output.value_proposition,
        cta_direction=(
            output.cta_blocks[0].copy_direction
            if output.cta_blocks
            else planning_input.baseline_cta_direction
        ),
        internal_link_directions=[
            f"{item.placement}: {item.target_url} ({item.anchor_direction})"
            for item in output.internal_links
        ],
        sections=sections,
        inventory_mapping=build_inventory_mapping(
            planning_input,
            output,
            [section.section_id for section in sections],
        ),
        search_demand=planning_input.query_portfolio,
        page_assets=output.page_assets,
        faq=output.faq,
        cta_blocks=output.cta_blocks,
        internal_links=output.internal_links,
        conditional_hypotheses=output.conditional_hypotheses,
        measurement_plan=output.measurement_plan,
        evidence_ids=planning_input.evidence_ids,
        source_connectors=planning_input.source_connectors,
        source_material_ids=sorted(
            {
                source_material_id
                for fact in planning_input.source_facts
                for source_material_id in fact.source_material_ids
            }
        ),
        knowledge_card_ids=planning_input.knowledge_card_ids,
        created_at=run.completed_at,
    )
    digest_payload = proposal.model_dump(
        mode="json",
        exclude={"planning_digest", "proposal_version", "created_at"},
    )
    digest = sha256(
        json.dumps(
            digest_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return proposal.model_copy(update={"planning_digest": digest})


def _lineage_ids_for_evidence(
    source_facts: Iterable[object],
    evidence_ids: Iterable[str],
    *,
    field: Literal["source_material_ids", "knowledge_card_ids"],
) -> list[str]:
    allowed_evidence = set(evidence_ids)
    values: set[str] = set()
    for fact in source_facts:
        fact_evidence_ids = getattr(fact, "evidence_ids", [])
        if allowed_evidence.intersection(fact_evidence_ids):
            values.update(getattr(fact, field, []))
    return sorted(values)


def _lineage_errors(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> list[str]:
    allowed_queries = {
        row.term
        for row in (
            *planning_input.query_portfolio.gsc_query_rows,
            *planning_input.query_portfolio.ads_term_rows,
            *planning_input.query_portfolio.keyword_planner_rows,
        )
    }
    allowed_evidence = set(planning_input.evidence_ids)
    allowed_claims = {
        entry.id
        for entry in planning_input.claim_ledger
        if entry.status in {"allowed_with_evidence", "allowed_general"}
    }
    allowed_internal_links = {
        candidate.target_url: set(candidate.evidence_ids)
        for candidate in planning_input.internal_link_candidates
    }
    inventory_headings = {item.heading for item in planning_input.inventory.sections}
    inventory_section_ids = {item.section_id for item in planning_input.inventory.sections}
    errors = _section_lineage_errors(
        output,
        allowed_queries=allowed_queries,
        allowed_evidence=allowed_evidence,
        allowed_claims=allowed_claims,
        inventory_headings=inventory_headings,
        inventory_section_ids=inventory_section_ids,
    )
    if output.service_card_id != planning_input.confirmed_service_card_id:
        errors.append("service_card_id")
    errors.extend(
        _asset_lineage_errors(
            output,
            allowed_queries=allowed_queries,
            allowed_evidence=allowed_evidence,
            allowed_claims=allowed_claims,
            allowed_internal_links=allowed_internal_links,
        )
    )
    errors.extend(_hypothesis_lineage_errors(planning_input, output))
    errors.extend(_measurement_lineage_errors(planning_input, output))
    return list(dict.fromkeys(errors))


def _section_lineage_errors(
    output: ContentPlanningModelOutput,
    *,
    allowed_queries: set[str],
    allowed_evidence: set[str],
    allowed_claims: set[str],
    inventory_headings: set[str],
    inventory_section_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    for section in output.sections:
        if not set(section.query_terms).issubset(allowed_queries):
            errors.append(f"section_query:{section.heading}")
        if not set(section.evidence_ids).issubset(allowed_evidence):
            errors.append(f"section_evidence:{section.heading}")
        if not set(section.claim_ids).issubset(allowed_claims):
            errors.append(f"section_claim:{section.heading}")
        if section.inventory_disposition == "create":
            if section.inventory_heading is not None or section.inventory_section_id is not None:
                errors.append(f"created_section_inventory:{section.heading}")
        else:
            if (
                section.inventory_section_id is not None
                and section.inventory_section_id not in inventory_section_ids
            ):
                errors.append(f"inventory_section_id:{section.heading}")
            if section.inventory_heading not in inventory_headings:
                errors.append(f"inventory_heading:{section.heading}")
    return errors


def _asset_lineage_errors(
    output: ContentPlanningModelOutput,
    *,
    allowed_queries: set[str],
    allowed_evidence: set[str],
    allowed_claims: set[str],
    allowed_internal_links: dict[str, set[str]],
) -> list[str]:
    errors: list[str] = []
    for faq in output.faq:
        if not set(faq.query_terms).issubset(allowed_queries):
            errors.append(f"faq_query:{faq.question}")
        if not set(faq.evidence_ids).issubset(allowed_evidence):
            errors.append(f"faq_evidence:{faq.question}")
        if not set(faq.claim_ids).issubset(allowed_claims):
            errors.append(f"faq_claim:{faq.question}")
    for cta in output.cta_blocks:
        if not set(cta.evidence_ids).issubset(allowed_evidence):
            errors.append(f"cta_evidence:{cta.placement}")
        if not set(cta.claim_ids).issubset(allowed_claims):
            errors.append(f"cta_claim:{cta.placement}")
    for link in output.internal_links:
        link_evidence = set(link.evidence_ids)
        candidate_evidence = allowed_internal_links.get(link.target_url)
        if candidate_evidence is None:
            errors.append(f"link_target:{link.target_url}")
        elif not link_evidence or not link_evidence.issubset(candidate_evidence):
            errors.append(f"link_inventory_evidence:{link.target_url}")
        if not link_evidence.issubset(allowed_evidence):
            errors.append(f"link_evidence:{link.target_url}")
        if not set(link.claim_ids).issubset(allowed_claims):
            errors.append(f"link_claim:{link.target_url}")
    return errors


def _hypothesis_lineage_errors(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> list[str]:
    errors: list[str] = []
    allowed_evidence = set(planning_input.evidence_ids)
    used_channels = {
        assessment.source
        for assessment in planning_input.source_assessments
        if assessment.status == "used"
    }
    for hypothesis in output.conditional_hypotheses:
        source = "google_ads" if hypothesis.channel == "google_ads" else "social"
        if source not in used_channels:
            errors.append(f"hypothesis_source:{hypothesis.channel}")
        if not set(hypothesis.evidence_ids).issubset(allowed_evidence):
            errors.append(f"hypothesis_evidence:{hypothesis.channel}")
    return errors


def _measurement_lineage_errors(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> list[str]:
    errors: list[str] = []
    if not set(output.measurement_plan.metrics_to_watch).issubset(
        planning_input.measurement_metrics
    ):
        errors.append("measurement_metrics")
    if not set(output.measurement_plan.baseline_evidence_ids).issubset(
        planning_input.measurement_baseline_evidence_ids
    ):
        errors.append("measurement_evidence")
    if output.measurement_plan.observation_rule != planning_input.measurement_observation_rule:
        errors.append("measurement_observation_rule")
    if output.measurement_plan.success_claim_rule != planning_input.measurement_success_claim_rule:
        errors.append("measurement_success_claim_rule")
    return errors


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


def _runtime_trace_with_run_id(
    trace: ContentCodexRuntimeTrace | None,
    run_id: str,
) -> ContentCodexRuntimeTrace:
    if trace is None:
        return ContentCodexRuntimeTrace(status="completed", run_id=run_id)
    return trace.model_copy(update={"run_id": run_id})


def _persisted_runtime_trace(proposal: ContentPlanningProposal) -> ContentCodexRuntimeTrace:
    """Keep a completed plan from looking like it never reached Codex after reload."""

    if not proposal.codex_run_id:
        return ContentCodexRuntimeTrace(status="not_started")
    run = next(
        (
            item
            for item in local_state_store().list_codex_runs()
            if item.id == proposal.codex_run_id
        ),
        None,
    )
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


def _runtime_failure_response(
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


def _blocked_from_input(
    work_item_id: str,
    service_card_id: str,
    blockers: list[ContentPlanningInputBlocker],
    *,
    planning_input_digest: str | None = None,
    input_summary: ContentPlanningInputSummary | None = None,
) -> ContentPlanningProposalResponse:
    return _blocked_response(
        work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=planning_input_digest,
        input_summary=input_summary,
        blockers=[
            _blocker(item.code, item.label, item.reason, item.next_step) for item in blockers
        ],
    )


def _blocked_response(
    work_item_id: str,
    *,
    service_card_id: str | None,
    planning_input_digest: str | None,
    blockers: list[ContentPlanningProposalBlocker],
    input_summary: ContentPlanningInputSummary | None = None,
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=planning_input_digest,
        input_summary=input_summary,
        blockers=blockers,
        safe_next_step=blockers[0].next_step,
    )


def _stale_input_blocker() -> ContentPlanningProposalBlocker:
    return _blocker(
        "stale_input",
        "Wejście planu zmieniło się",
        "Inventory, usługa, wiedza albo metryki mają inny exact digest.",
        "Odśwież dane i uruchom świadomie nową wersję planu.",
    )


def _blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
    *,
    source_codes: list[str] | None = None,
) -> ContentPlanningProposalBlocker:
    return ContentPlanningProposalBlocker(
        code=cast(ContentPlanningProposalBlockerCode, code),
        label=label,
        reason=reason,
        next_step=next_step,
        source_codes=source_codes or [],
    )


def _planning_runtime_blocker(source_codes: list[str]) -> tuple[str, str, str]:
    """Turn safe runtime codes into an operator-useful blocker."""

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
        "Codex nie zwrócił bezpiecznego planu",
        "App-server nie zakończył turnu poprawnym ustrukturyzowanym wynikiem.",
        "Sprawdź runtime i rozpocznij nową próbę; WILQ nic nie zapisał.",
    )


__all__ = [
    "generate_content_planning_proposal",
    "queue_content_planning_proposal",
    "read_content_planning_proposal",
]
