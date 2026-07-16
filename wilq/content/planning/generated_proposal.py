from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal, cast
from uuid import uuid4

from wilq.codex.app_server import CodexAppServerClientProtocol, CodexAppServerTurnResult
from wilq.content.drafts.codex_section_proposal_contracts import ContentCodexRuntimeTrace
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBlocker,
    build_content_planning_input,
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
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


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
    result = build_content_planning_input(snapshot, service_card_id=service_card_id)
    if result.planning_input is None:
        return _blocked_from_input(
            snapshot.preflight.item.id,
            service_card_id,
            result.blockers,
        )
    planning_input = result.planning_input
    if result.blockers:
        return _blocked_from_input(
            planning_input.work_item_id,
            service_card_id,
            result.blockers,
            planning_input_digest=planning_input.planning_input_digest,
        )
    latest = store.latest(planning_input.work_item_id)
    if latest is None:
        return ContentPlanningProposalResponse(
            status="not_generated",
            work_item_id=planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
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
            proposal=latest,
            blockers=[_stale_input_blocker()],
            safe_next_step="Wygeneruj nową wersję planu z aktualnego wejścia.",
        )
    return ContentPlanningProposalResponse(
        status="ready",
        work_item_id=planning_input.work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        proposal=latest,
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
        _finish_run(run_store, run, status=status, error=blocker.code)
        return _runtime_failure_response(
            planning_input,
            blocker,
            status=status,
            trace=trace,
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


def _prepare_generation(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentPlanningProposalRequest,
    store: ContentPlanningProposalStore,
) -> tuple[ContentPlanningInput | None, ContentPlanningProposalResponse | None]:
    result = build_content_planning_input(
        snapshot,
        service_card_id=request.service_card_id,
    )
    if result.planning_input is None:
        return None, _blocked_from_input(
            snapshot.preflight.item.id,
            request.service_card_id,
            result.blockers,
        )
    planning_input = result.planning_input
    if request.expected_planning_input_digest != planning_input.planning_input_digest:
        return None, ContentPlanningProposalResponse(
            status="stale",
            work_item_id=planning_input.work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            blockers=[_stale_input_blocker()],
            safe_next_step="Odśwież wejście i świadomie uruchom nową wersję planu.",
        )
    if result.blockers:
        return None, _blocked_from_input(
            planning_input.work_item_id,
            request.service_card_id,
            result.blockers,
            planning_input_digest=planning_input.planning_input_digest,
        )
    existing = store.for_input(
        planning_input.work_item_id,
        request.service_card_id,
        planning_input.planning_input_digest,
    )
    if existing is not None:
        return None, ContentPlanningProposalResponse(
            status="idempotent",
            work_item_id=planning_input.work_item_id,
            service_card_id=request.service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            proposal=existing,
            safe_next_step="Sprawdź zapisaną wersję planu; model nie został uruchomiony ponownie.",
        )
    return planning_input, None


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
        blocker = _blocker(
            "runtime_blocked" if status == "blocked" else "runtime_failed",
            "Codex nie zwrócił bezpiecznego planu",
            "App-server nie zakończył turnu poprawnym ustrukturyzowanym wynikiem.",
            "Sprawdź runtime i rozpocznij nową próbę; WILQ nic nie zapisał.",
            source_codes=[entry.code for entry in runtime_result.blockers],
        )
        return None, trace, blocker, status
    try:
        output = ContentPlanningModelOutput.model_validate_json(runtime_result.output_text)
    except ValueError:
        blocker = _blocker(
            "invalid_structured_output",
            "Codex zwrócił niepoprawny plan",
            "Wynik nie przeszedł ścisłego schematu planowania WILQ.",
            "Odrzuć wynik i uruchom nową próbę po sprawdzeniu kontraktu.",
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
        )
    return ContentPlanningProposalResponse(
        status="created" if store_status == "created" else "idempotent",
        work_item_id=planning_input.work_item_id,
        service_card_id=request.service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        proposal=stored,
        runtime=trace or ContentCodexRuntimeTrace(status="completed"),
        safe_next_step="Sprawdź strategię i każdą sekcję; plan pozostaje niezatwierdzony.",
    )


def _proposal_from_output(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
    run: CodexRun,
) -> ContentPlanningProposal:
    proposal_id = f"content_planning_proposal_{uuid4().hex}"
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
            else planning_input.baseline_proposal.cta_direction
        ),
        internal_link_directions=[
            f"{item.placement}: {item.target_url} ({item.anchor_direction})"
            for item in output.internal_links
        ],
        sections=[
            ContentPlanningSection(
                section_id=f"{proposal_id}_section_{index:02d}",
                **section.model_dump(),
            )
            for index, section in enumerate(output.sections, start=1)
        ],
        search_demand=planning_input.query_portfolio,
        page_assets=output.page_assets,
        faq=output.faq,
        cta_blocks=output.cta_blocks,
        internal_links=output.internal_links,
        conditional_hypotheses=output.conditional_hypotheses,
        measurement_plan=output.measurement_plan,
        evidence_ids=planning_input.evidence_ids,
        source_connectors=planning_input.source_connectors,
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
    inventory_headings = {item.heading for item in planning_input.inventory.sections}
    errors = _section_lineage_errors(
        output,
        allowed_queries=allowed_queries,
        allowed_evidence=allowed_evidence,
        allowed_claims=allowed_claims,
        inventory_headings=inventory_headings,
    )
    if output.service_card_id != planning_input.confirmed_service_card_id:
        errors.append("service_card_id")
    errors.extend(
        _asset_lineage_errors(
            output,
            allowed_queries=allowed_queries,
            allowed_evidence=allowed_evidence,
            allowed_claims=allowed_claims,
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
            if section.inventory_heading is not None:
                errors.append(f"created_section_inventory:{section.heading}")
        elif section.inventory_heading not in inventory_headings:
            errors.append(f"inventory_heading:{section.heading}")
    return errors


def _asset_lineage_errors(
    output: ContentPlanningModelOutput,
    *,
    allowed_queries: set[str],
    allowed_evidence: set[str],
    allowed_claims: set[str],
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
    if output.internal_links:
        errors.append("internal_links_without_exact_inventory_target")
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


def _runtime_failure_response(
    planning_input: ContentPlanningInput,
    blocker: ContentPlanningProposalBlocker,
    *,
    status: Literal["blocked", "failed"],
    trace: ContentCodexRuntimeTrace | None = None,
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status=status,
        work_item_id=planning_input.work_item_id,
        service_card_id=planning_input.confirmed_service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        runtime=trace or ContentCodexRuntimeTrace(status="failed"),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _blocked_from_input(
    work_item_id: str,
    service_card_id: str,
    blockers: list[ContentPlanningInputBlocker],
    *,
    planning_input_digest: str | None = None,
) -> ContentPlanningProposalResponse:
    return _blocked_response(
        work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=planning_input_digest,
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
) -> ContentPlanningProposalResponse:
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=planning_input_digest,
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


__all__ = [
    "generate_content_planning_proposal",
    "read_content_planning_proposal",
]
