from __future__ import annotations

from typing import Any, cast

from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputSummary,
    bind_research_packet_to_planning_input,
    build_content_planning_input,
    content_planning_input_summary,
    planning_generation_blockers,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalBlockerCode,
    ContentPlanningProposalResponse,
    regulatory_response_lineage_errors,
)
from wilq.content.planning.generated_proposal_responses import (
    blocked_from_input as _blocked_from_input,
)
from wilq.content.planning.generated_proposal_responses import (
    blocked_response as _blocked_response,
)
from wilq.content.planning.generated_proposal_responses import (
    stale_input_blocker as _stale_input_blocker,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.proposal_quality import (
    inventory_mapping_has_unresolved_rows,
    persisted_inventory_mapping_is_current,
    proposal_quality_errors,
    remapped_proposal_projection,
)
from wilq.content.planning.subject import ContentPlanningSubject, PlanningContentKind
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBinding,
    refresh_preparation_bindings_match_authority,
)


def read_content_planning_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse:
    """Project only the proposal that is exact for the current planning input."""

    from wilq.content.planning.generated_proposal import with_explicit_content_service_selection

    content_kind: PlanningContentKind = (
        "editorial" if snapshot.preflight.item.content_kind == "editorial" else "service"
    )
    service_card_id = snapshot.service_profile_context.service_card_id
    if content_kind == "service" and service_card_id is None:
        return _blocked_response(
            snapshot.preflight.item.id,
            content_kind=content_kind,
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
    planning_snapshot = (
        with_explicit_content_service_selection(snapshot, service_card_id)
        if content_kind == "service" and service_card_id is not None
        else snapshot
    )
    result = build_content_planning_input(planning_snapshot, service_card_id=service_card_id)
    if result.planning_input is None:
        return _blocked_from_input(
            snapshot.preflight.item.id,
            service_card_id,
            result.blockers,
            content_kind=content_kind,
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
            content_kind=content_kind,
        )
    return _read_current_proposal(
        snapshot=planning_snapshot,
        planning_input=planning_input,
        content_kind=content_kind,
        service_card_id=service_card_id,
        input_summary=input_summary,
        store=store,
    )


def read_content_planning_proposal_for_refresh_binding(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    binding: ContentRefreshPreparationBinding,
    authority_binding: ContentRefreshPreparationBinding,
    store: ContentPlanningProposalStore,
    workflow_store: object | None = None,
) -> ContentPlanningProposalResponse:
    """Read the proposal/job bound to the exact packet-bound refresh receipt."""

    if (
        binding.current_work_item_id != planning_input.work_item_id
        or not refresh_preparation_bindings_match_authority(binding, authority_binding)
    ):
        return _refresh_binding_status_block(binding)
    subject = ContentPlanningSubject(
        content_kind=binding.content_kind,
        service_card_id=binding.service_card_id,
    )
    queued = store.queued_subject_response(
        binding.current_work_item_id,
        subject,
        binding.planning_input_digest,
    )
    response = queued
    if response is None:
        proposal = store.for_subject_input(
            binding.current_work_item_id,
            subject,
            binding.planning_input_digest,
        )
    else:
        proposal = None
    if response is None and proposal is not None:
        packet_bound_input = _packet_bound_refresh_input(
            planning_input=planning_input,
            proposal=proposal,
            binding=binding,
            workflow_store=workflow_store,
        )
        if packet_bound_input is None:
            return _packet_conflict_response(
                _packet_conflict_base_response(
                    planning_input=planning_input,
                    binding=binding,
                    research_packet_id=proposal.research_packet_id,
                    research_packet_digest=proposal.research_packet_digest,
                )
            )
        response = _response_for_current_proposal(
            planning_input=packet_bound_input,
            content_kind=binding.content_kind,
            service_card_id=binding.service_card_id,
            input_summary=content_planning_input_summary(packet_bound_input),
            latest=proposal,
            latest_is_current=True,
        )
    if response is None:
        return _refresh_binding_status_block(binding)
    response_binding = response.refresh_preparation_binding
    if (
        response_binding != binding
        or response.planning_input_digest != binding.planning_input_digest
    ):
        return _refresh_binding_status_block(binding)
    packet_bound_input = _packet_bound_refresh_input(
        planning_input=planning_input,
        proposal=response.proposal,
        response=response,
        binding=binding,
        workflow_store=workflow_store,
    )
    if packet_bound_input is None:
        return _packet_conflict_response(
            response,
            input_summary=content_planning_input_summary(planning_input),
        )
    return _revalidate_research_packet_response(
        response=response,
        snapshot=snapshot,
        planning_input=packet_bound_input,
        workflow_store=workflow_store,
    )


def _packet_bound_refresh_input(
    *,
    planning_input: ContentPlanningInput,
    binding: ContentRefreshPreparationBinding,
    proposal: ContentPlanningProposal | None = None,
    response: ContentPlanningProposalResponse | None = None,
    workflow_store: object | None = None,
) -> ContentPlanningInput | None:
    packet_id = (
        response.research_packet_id
        if response is not None
        else None if proposal is None else proposal.research_packet_id
    )
    packet_digest = (
        response.research_packet_digest
        if response is not None
        else None if proposal is None else proposal.research_packet_digest
    )
    if packet_id is None or packet_digest is None:
        return None
    packet_store = workflow_store
    if packet_store is None:
        from wilq.content.workflow.store.store import content_workflow_store

        packet_store = content_workflow_store()
    packet = cast(Any, packet_store).load_content_research_packet(packet_id)
    if packet is None or packet.packet_digest != packet_digest:
        return None
    try:
        bound = bind_research_packet_to_planning_input(planning_input, packet)
    except ValueError:
        return None
    return bound if bound.planning_input_digest == binding.planning_input_digest else None


def _refresh_binding_status_block(
    binding: ContentRefreshPreparationBinding,
) -> ContentPlanningProposalResponse:
    next_step = "Odśwież przygotowanie refresh i wygeneruj plan dla bieżącego receipt."
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=binding.current_work_item_id,
        content_kind=binding.content_kind,
        service_card_id=binding.service_card_id,
        blockers=[
            ContentPlanningProposalBlocker(
                code="refresh_preparation_authorization_foreign",
                label="Plan refresh nie ma już bieżącej autoryzacji",
                reason="Trwały plan nie pasuje do bieżącego receipt refresh.",
                next_step=next_step,
            )
        ],
        safe_next_step=next_step,
    )


def _packet_conflict_response(
    response: ContentPlanningProposalResponse,
    *,
    input_summary: ContentPlanningInputSummary | None = None,
) -> ContentPlanningProposalResponse:
    next_step = "Odśwież exact packet i wygeneruj plan dla bieżącego kontekstu."
    payload = response.model_dump(mode="python")
    payload.update(
        {
            "status": "blocked",
            "proposal": None,
            "planning_workspace": None,
            "input_summary": response.input_summary or input_summary,
            "blockers": [
                ContentPlanningProposalBlocker(
                    code="research_packet_conflict",
                    label="Research packet nie jest aktualny",
                    reason="Nie można potwierdzić exact packetu zachowanego planu.",
                    next_step=next_step,
                )
            ],
            "safe_next_step": next_step,
        }
    )
    return ContentPlanningProposalResponse.model_validate(payload)


def _packet_conflict_base_response(
    *,
    planning_input: ContentPlanningInput,
    binding: ContentRefreshPreparationBinding,
    research_packet_id: str | None,
    research_packet_digest: str | None,
) -> ContentPlanningProposalResponse:
    next_step = "Odśwież exact packet i wygeneruj plan dla bieżącego kontekstu."
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=binding.current_work_item_id,
        content_kind=binding.content_kind,
        service_card_id=binding.service_card_id,
        planning_input_digest=binding.planning_input_digest,
        research_packet_id=research_packet_id,
        research_packet_digest=research_packet_digest,
        input_summary=content_planning_input_summary(planning_input),
        refresh_preparation_binding=binding,
        blockers=[
            ContentPlanningProposalBlocker(
                code="research_packet_conflict",
                label="Research packet nie jest aktualny",
                reason="Nie można potwierdzić exact packetu zachowanego planu.",
                next_step=next_step,
            )
        ],
        safe_next_step=next_step,
    )


def _read_current_proposal(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    content_kind: PlanningContentKind,
    service_card_id: str | None,
    input_summary: ContentPlanningInputSummary,
    store: ContentPlanningProposalStore,
) -> ContentPlanningProposalResponse:
    subject = ContentPlanningSubject(
        content_kind=content_kind,
        service_card_id=service_card_id,
    )
    queued = store.queued_subject_response(
        planning_input.work_item_id,
        subject,
        planning_input.planning_input_digest,
    )
    if queued is not None:
        response = queued.model_copy(
            update={
                "planning_input_digest": planning_input.planning_input_digest,
                "input_summary": input_summary,
            }
        )
        return _revalidate_research_packet_response(
            response=response,
            snapshot=snapshot,
            planning_input=planning_input,
        )
    current = store.for_subject_input(
        planning_input.work_item_id,
        subject,
        planning_input.planning_input_digest,
    )
    latest = current or store.latest(planning_input.work_item_id)
    latest_is_current = current is not None
    if latest is not None and latest.research_packet_id is not None:
        from wilq.content.workflow.store.store import content_workflow_store

        packet = content_workflow_store().load_content_research_packet(
            latest.research_packet_id
        )
        if packet is not None:
            planning_input = bind_research_packet_to_planning_input(planning_input, packet)
            input_summary = content_planning_input_summary(planning_input)
            latest_is_current = latest.planning_input_digest == planning_input.planning_input_digest
    response = _response_for_current_proposal(
        planning_input=planning_input,
        content_kind=content_kind,
        service_card_id=service_card_id,
        input_summary=input_summary,
        latest=latest,
        latest_is_current=latest_is_current,
    )
    return _revalidate_research_packet_response(
        response=response,
        snapshot=snapshot,
        planning_input=planning_input,
    )


def _revalidate_research_packet_response(
    *,
    response: ContentPlanningProposalResponse,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    planning_input: ContentPlanningInput,
    workflow_store: object | None = None,
) -> ContentPlanningProposalResponse:
    packet_id = response.research_packet_id
    packet_digest = response.research_packet_digest
    if packet_id is None or packet_digest is None:
        return response
    from wilq.content.workflow.research_packet_preparation import (
        current_research_packet_blocker,
    )
    packet_store = workflow_store
    if packet_store is None:
        from wilq.content.workflow.store.store import content_workflow_store

        packet_store = content_workflow_store()
    packet = cast(Any, packet_store).load_content_research_packet(packet_id)
    if packet is None or packet.packet_digest != packet_digest:
        reason = "packet_conflict"
        next_step = "Odśwież exact packet i wygeneruj plan dla bieżącego kontekstu."
        evidence_ids: tuple[str, ...] = () if packet is None else packet.evidence_ids
    else:
        blocker = current_research_packet_blocker(
            store=cast(Any, packet_store),
            packet=packet,
            snapshot=snapshot,
            planning_input=planning_input,
        )
        if blocker is None:
            return response
        reason = blocker.reason
        next_step = blocker.next_step_pl
        evidence_ids = blocker.evidence_ids
    code = (
        "research_packet_conflict"
        if reason == "packet_conflict"
        else "research_packet_blocked"
    )
    packet_code = cast(ContentPlanningProposalBlockerCode, code)
    blocked = ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=response.work_item_id,
        content_kind=response.content_kind,
        service_card_id=response.service_card_id,
        planning_input_digest=response.planning_input_digest,
        research_packet_id=response.research_packet_id,
        research_packet_digest=response.research_packet_digest,
        input_summary=response.input_summary or content_planning_input_summary(planning_input),
        refresh_preparation_binding=response.refresh_preparation_binding,
        runtime=response.runtime,
        blockers=[
            ContentPlanningProposalBlocker(
                code=packet_code,
                label="Research packet nie jest aktualny",
                reason=next_step,
                next_step=next_step,
                source_codes=[reason, *evidence_ids],
            )
        ],
        safe_next_step=next_step,
    )
    return blocked


def _quality_blocked_response(
    planning_input: ContentPlanningInput,
    content_kind: PlanningContentKind,
    service_card_id: str | None,
    input_summary: ContentPlanningInputSummary,
    proposal: ContentPlanningProposal,
) -> ContentPlanningProposalResponse | None:
    errors = proposal_quality_errors(proposal)
    if not errors:
        return None
    return _blocked_response(
        planning_input.work_item_id,
        content_kind=content_kind,
        service_card_id=service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=input_summary,
        blockers=[
            build_blocker(
                ContentPlanningProposalBlocker,
                code="quality_gate_failed",
                label="Zapisany plan wymaga ponownego wygenerowania",
                reason="Ostatnia wersja nie jest użyteczną strukturą odpowiedzi dla czytelnika.",
                next_step="Uruchom plan ponownie; poprzednia wersja nie jest gotowa do review.",
                source_codes=errors,
            )
        ],
    )


def _response_for_current_proposal(
    *,
    planning_input: ContentPlanningInput,
    content_kind: PlanningContentKind,
    service_card_id: str | None,
    input_summary: ContentPlanningInputSummary,
    latest: ContentPlanningProposal | None,
    latest_is_current: bool,
) -> ContentPlanningProposalResponse:
    from wilq.content.planning.generated_proposal import persisted_runtime_trace

    if latest is None:
        return ContentPlanningProposalResponse(
            status="not_generated",
            work_item_id=planning_input.work_item_id,
            content_kind=content_kind,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            research_packet_id=latest_packet_id(latest),
            research_packet_digest=latest_packet_digest(latest),
            input_summary=input_summary,
            safe_next_step="Wygeneruj pierwszy plan z aktualnych źródeł.",
        )
    if not latest_is_current:
        return ContentPlanningProposalResponse(
            status="stale",
            work_item_id=planning_input.work_item_id,
            content_kind=content_kind,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            research_packet_id=latest_packet_id(latest),
            research_packet_digest=latest_packet_digest(latest),
            input_summary=input_summary,
            blockers=[_stale_input_blocker()],
            safe_next_step="Wygeneruj nową wersję planu z aktualnego wejścia.",
        )
    if quality_blocked := _quality_blocked_response(
        planning_input, content_kind, service_card_id, input_summary, latest
    ):
        return quality_blocked
    regulatory_blocked = _regulatory_lineage_blocked_response(
        planning_input,
        content_kind=content_kind,
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
            content_kind=content_kind,
            service_card_id=service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            proposal=remapped_proposal_projection(planning_input, latest),
            refresh_preparation_binding=latest.refresh_preparation_binding,
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
        content_kind=content_kind,
        service_card_id=service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=latest_packet_id(latest),
        research_packet_digest=latest_packet_digest(latest),
        input_summary=input_summary,
        proposal=latest,
        refresh_preparation_binding=latest.refresh_preparation_binding,
        runtime=persisted_runtime_trace(latest),
        safe_next_step="Sprawdź strukturę i przygotuj pełny tekst z tej dokładnej wersji planu.",
    )


def latest_packet_id(proposal: ContentPlanningProposal | None) -> str | None:
    return None if proposal is None else proposal.research_packet_id


def latest_packet_digest(proposal: ContentPlanningProposal | None) -> str | None:
    return None if proposal is None else proposal.research_packet_digest


def _regulatory_lineage_blocked_response(
    planning_input: ContentPlanningInput,
    *,
    content_kind: PlanningContentKind,
    service_card_id: str | None,
    input_summary: ContentPlanningInputSummary,
    proposal: ContentPlanningProposal,
) -> ContentPlanningProposalResponse | None:
    regulatory_errors = regulatory_response_lineage_errors(input_summary, proposal)
    if not regulatory_errors:
        return None
    return _blocked_response(
        planning_input.work_item_id,
        content_kind=content_kind,
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


__all__ = [
    "read_content_planning_proposal",
    "read_content_planning_proposal_for_refresh_binding",
]
