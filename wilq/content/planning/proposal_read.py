from __future__ import annotations

from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputSummary,
    build_content_planning_input,
    content_planning_input_summary,
    planning_generation_blockers,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalResponse,
    regulatory_response_lineage_errors,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.proposal_quality import (
    inventory_mapping_has_unresolved_rows,
    persisted_inventory_mapping_is_current,
    proposal_quality_errors,
    remapped_proposal_projection,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal


def read_content_planning_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse:
    """Project only the proposal that is exact for the current planning input."""

    from wilq.content.planning.generated_proposal import (
        _blocked_from_input,
        _blocked_response,
        with_explicit_content_service_selection,
    )

    service_card_id = snapshot.service_profile_context.service_card_id
    if service_card_id is None:
        return _blocked_response(
            snapshot.preflight.item.id,
            service_card_id=None,
            planning_input_digest=None,
            blockers=[
                build_blocker(
                    ContentPlanningProposalBlocker,
                    code="unknown_service_card",
                    label="Brakuje usługi do planowania",
                    reason="Bieżący snapshot nie ma dozwolonej karty usługi.",
                    next_step="Wybierz work item z dokładnym dopasowaniem Service Profile.",
                )
            ],
        )
    planning_snapshot = with_explicit_content_service_selection(snapshot, service_card_id)
    result = build_content_planning_input(planning_snapshot, service_card_id=service_card_id)
    if result.planning_input is None:
        return _blocked_from_input(snapshot.preflight.item.id, service_card_id, result.blockers)
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
    current = store.read_latest_or_none_for_input(
        planning_input.work_item_id,
        service_card_id,
        planning_input.planning_input_digest,
    )
    latest = current or store.latest(planning_input.work_item_id)
    return _response_for_current_proposal(
        planning_input=planning_input,
        service_card_id=service_card_id,
        input_summary=input_summary,
        latest=latest,
        latest_is_current=current is not None,
    )


def _response_for_current_proposal(
    *,
    planning_input: ContentPlanningInput,
    service_card_id: str,
    input_summary: ContentPlanningInputSummary,
    latest: ContentPlanningProposal | None,
    latest_is_current: bool,
) -> ContentPlanningProposalResponse:
    from wilq.content.planning.generated_proposal import (
        _blocked_response,
        _persisted_runtime_trace,
        _stale_input_blocker,
    )

    if latest is None:
        return ContentPlanningProposalResponse(
            status="not_generated",
            work_item_id=planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            safe_next_step="Wygeneruj pierwszy plan z aktualnych źródeł.",
        )
    if not latest_is_current:
        return ContentPlanningProposalResponse(
            status="stale",
            work_item_id=planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            blockers=[_stale_input_blocker()],
            safe_next_step="Wygeneruj nową wersję planu z aktualnego wejścia.",
        )
    quality_errors = proposal_quality_errors(latest)
    if quality_errors:
        return _blocked_response(
            planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            blockers=[
                build_blocker(
                    ContentPlanningProposalBlocker,
                    code="quality_gate_failed",
                    label="Zapisany plan wymaga ponownego wygenerowania",
                    reason=(
                        "Ostatnia wersja nie jest użyteczną strukturą odpowiedzi "
                        "dla czytelnika."
                    ),
                    next_step="Uruchom plan ponownie; poprzednia wersja nie jest gotowa do review.",
                    source_codes=quality_errors,
                )
            ],
        )
    regulatory_blocked = _regulatory_lineage_blocked_response(
        planning_input,
        service_card_id=service_card_id,
        input_summary=input_summary,
        proposal=latest,
    )
    if regulatory_blocked is not None:
        return regulatory_blocked
    if not persisted_inventory_mapping_is_current(
        planning_input, latest
    ) or inventory_mapping_has_unresolved_rows(latest):
        return ContentPlanningProposalResponse(
            status="stale",
            work_item_id=planning_input.work_item_id,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            proposal=remapped_proposal_projection(planning_input, latest),
            blockers=[
                build_blocker(
                    ContentPlanningProposalBlocker,
                    code="stale_input",
                    label="Mapa istniejącej strony wymaga odświeżenia",
                    reason=(
                        "Zapisany plan nie zawiera aktualnej, deterministycznej "
                        "mapy sekcji inventory."
                    ),
                    next_step=(
                        "Uruchom nową wersję planu; WILQ ponownie przypisze sekcje "
                        "bez ręcznego mapowania."
                    ),
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
        safe_next_step="Sprawdź strukturę i przygotuj pełny tekst z tej dokładnej wersji planu.",
    )


def _regulatory_lineage_blocked_response(
    planning_input: ContentPlanningInput,
    *,
    service_card_id: str,
    input_summary: ContentPlanningInputSummary,
    proposal: ContentPlanningProposal,
) -> ContentPlanningProposalResponse | None:
    regulatory_errors = regulatory_response_lineage_errors(input_summary, proposal)
    if not regulatory_errors:
        return None
    from wilq.content.planning.generated_proposal import _blocked_response

    return _blocked_response(
        planning_input.work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=input_summary,
        blockers=[
            build_blocker(
                ContentPlanningProposalBlocker,
                code="lineage_mismatch",
                label="Zapisany plan nie ma pełnej lineage źródeł urzędowych",
                reason=(
                    "Wymagania regulacyjne lub ich dokładne dowody nie są zgodne "
                    "z bieżącym profilem planowania."
                ),
                next_step="Wygeneruj plan ponownie z aktualnych, zatwierdzonych źródeł urzędowych.",
                source_codes=regulatory_errors,
            )
        ],
    )
