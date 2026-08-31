"""Source rebuild and exact-binding checks used by classified-refresh operations."""

from __future__ import annotations

from urllib.parse import urlsplit

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftRequest
from wilq.content.knowledge.work_item_service_profile import ContentWorkItemServiceCandidate
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
    build_content_planning_input,
    content_planning_input_summary,
)
from wilq.content.planning.generation_readiness import planning_generation_blockers
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationAuthorizationRequest,
    ContentRefreshPreparationAuthorized,
    ContentRefreshPreparationBinding,
    ContentRefreshPreparationBlocked,
    ContentRefreshPreparationBlocker,
    ContentRefreshPreparationBlockerCode,
    ContentRefreshPreparationClassificationBinding,
    ContentRefreshPreparationReadyToAuthorize,
    ContentRefreshPreparationServiceCandidate,
    refresh_preparation_binding_matches_content_identity,
)
from wilq.content.workflow.refresh_preparation_models import (
    RefreshClassificationContext,
    RefreshPreparationSnapshotLoader,
    RefreshPreparationStore,
)


def classified_refresh_context(
    store: RefreshPreparationStore,
    work_item_id: str,
) -> RefreshClassificationContext | ContentRefreshPreparationBlocker | None:
    run = store.load_latest_production_classification()
    if run is None:
        return None
    row = run.for_work_item(work_item_id)
    if row is None:
        return None
    if row.current_work_item_id != work_item_id:
        return blocker(
            "refresh_preparation_alias_not_current",
            "Autoryzacja wymaga bieżącej tożsamości strony",
            "Klasyfikacja została znaleziona przez alias, retained ID albo historycznego "
            "ownera; refresh może użyć wyłącznie current work item ID.",
            "Otwórz bieżący work item wskazany przez klasyfikację przed przygotowaniem refresh.",
        )
    if row.decision != "refresh":
        return blocker(
            "refresh_preparation_decision_not_refresh",
            "Klasyfikacja nie pozwala na autoryzację refresh",
            "Ręczna autoryzacja jest jedynym wyjątkiem dla decyzji refresh; nie dotyczy "
            "reuse, write ani blocked.",
            row.next_step_pl,
            source_codes=[row.decision, *(item.code for item in row.blockers)],
        )
    return RefreshClassificationContext(
        run=run,
        row=row,
        binding=ContentRefreshPreparationClassificationBinding(
            classification_run_id=run.run_id,
            classification_run_digest=run.run_digest,
            decision_set_digest=run.input.decision_set_digest,
            source_packet_row_digest=row.source_packet_row_digest,
            current_work_item_id=work_item_id,
            canonical_path=row.canonical_path,
            public_url=row.public_url,
            classification_blocker_codes=[item.code for item in row.blockers],
        ),
    )


def approved_candidates(
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
) -> list[ContentRefreshPreparationServiceCandidate]:
    snapshot = snapshot_loader(work_item_id, None)
    candidate_ids = [
        candidate.service_card_id
        for candidate in snapshot.service_profile_context.service_candidates
        if candidate.lifecycle_status == "approved_current"
    ]
    candidates: list[ContentRefreshPreparationServiceCandidate] = []
    for candidate_id in candidate_ids:
        try:
            selected_snapshot = snapshot_loader(work_item_id, candidate_id)
            selected = selected_service_candidate(selected_snapshot, candidate_id)
            if selected is not None:
                candidates.append(refresh_candidate(selected_snapshot, selected))
        except (ValueError, RuntimeError):
            continue
    return candidates


def rebuild_preparation(
    *,
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
    classification: RefreshClassificationContext,
    service_card_id: str,
) -> (
    tuple[
        ContentWorkItemWorkflowSnapshotResponse,
        ContentPlanningInput,
        ContentRefreshPreparationServiceCandidate,
        list[ContentRefreshPreparationBlocker],
    ]
    | ContentRefreshPreparationBlocked
):
    snapshot = snapshot_loader(work_item_id, service_card_id)
    selected = selected_service_candidate(snapshot, service_card_id)
    if selected is None:
        return blocked_preparation(
            work_item_id,
            classification.binding,
            blocker(
                "refresh_preparation_service_unavailable",
                "Wybrana usługa nie jest już kandydatem",
                "Bieżący matcher nie potwierdza tej karty usługi dla strony i jej "
                "aktualnych źródeł.",
                "Odśwież przygotowanie i wybierz kartę z bieżącej listy kandydatów.",
            ),
        )
    try:
        service_candidate = refresh_candidate(snapshot, selected)
    except ValueError:
        return blocked_preparation(
            work_item_id,
            classification.binding,
            blocker(
                "refresh_preparation_service_sources_missing",
                "Karta usługi nie ma kompletnej linii źródłowej",
                "Wybrana karta musi być approved_current oraz mieć evidence, connector "
                "i co najmniej jeden reviewed source fact albo source material ID.",
                "Uzupełnij zatwierdzoną linię źródłową karty usługi przed przygotowaniem "
                "refresh.",
            ),
        )
    result = build_content_planning_input(snapshot, service_card_id=service_card_id)
    identity_blocker = preparation_identity_blocker(
        work_item_id=work_item_id,
        classification=classification.binding,
        candidate=service_candidate,
        planning_input=result.planning_input,
    )
    if identity_blocker is not None:
        return blocked_preparation(
            work_item_id,
            classification.binding,
            identity_blocker,
        )
    return _rebuild_result(
        result=result,
        snapshot=snapshot,
        classification=classification.binding,
        candidate=service_candidate,
        work_item_id=work_item_id,
    )


def _rebuild_result(
    *,
    result: ContentPlanningInputBuildResult,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    classification: ContentRefreshPreparationClassificationBinding,
    candidate: ContentRefreshPreparationServiceCandidate,
    work_item_id: str,
) -> (
    tuple[
        ContentWorkItemWorkflowSnapshotResponse,
        ContentPlanningInput,
        ContentRefreshPreparationServiceCandidate,
        list[ContentRefreshPreparationBlocker],
    ]
    | ContentRefreshPreparationBlocked
):
    planning_input = result.planning_input
    generation_blockers = planning_generation_blockers(result.blockers)
    informational = planning_input_blockers(result, include_generation=False)
    if planning_input is not None and not generation_blockers:
        return snapshot, planning_input, candidate, informational
    blockers = planning_input_blockers(result, include_generation=True)
    if not blockers:
        blockers = [
            blocker(
                "refresh_preparation_input_blocked",
                "Nie udało się zbudować wejścia refresh",
                "Pełny snapshot nie zwrócił wejścia planowania wymaganego do autoryzacji.",
                "Odśwież źródła i sprawdź wymagane elementy planning input.",
            )
        ]
    return ContentRefreshPreparationBlocked(
        status="blocked",
        work_item_id=work_item_id,
        classification=classification,
        service_candidate=candidate,
        input_summary=(
            None if planning_input is None else content_planning_input_summary(planning_input)
        ),
        blockers=blockers,
        safe_next_step=blockers[0].next_step,
    )


def blocked_preparation(
    work_item_id: str,
    classification: ContentRefreshPreparationClassificationBinding,
    item: ContentRefreshPreparationBlocker,
) -> ContentRefreshPreparationBlocked:
    return ContentRefreshPreparationBlocked(
        status="blocked",
        work_item_id=work_item_id,
        classification=classification,
        blockers=[item],
        safe_next_step=item.next_step,
    )


def preparation_identity_blocker(
    *,
    work_item_id: str,
    classification: ContentRefreshPreparationClassificationBinding,
    candidate: ContentRefreshPreparationServiceCandidate,
    planning_input: ContentPlanningInput | None,
) -> ContentRefreshPreparationBlocker | None:
    if planning_input is None:
        return None
    if (
        planning_input.work_item_id != work_item_id
        or planning_input.work_item_id != classification.current_work_item_id
    ):
        return blocker(
            "refresh_preparation_authorization_stale",
            "Odbudowany input dotyczy innej strony",
            "Pełny planning input nie zachował bieżącego work item ID klasyfikacji.",
            "Odśwież przygotowanie refresh dla bieżącej strony przed autoryzacją.",
        )
    if planning_input.confirmed_service_card_id != candidate.service_card_id:
        return blocker(
            "refresh_preparation_authorization_service_mismatch",
            "Odbudowany input ma inną usługę",
            "Potwierdzona karta w planning input różni się od jawnie wybranego kandydata.",
            "Odśwież przygotowanie i wybierz usługę widoczną w bieżącym snapshotcie.",
        )
    if planning_input.final_canonical_url != classification.public_url:
        return blocker(
            "refresh_preparation_authorization_stale",
            "Odbudowany input ma inny adres strony",
            "Finalny adres planning input nie odpowiada bieżącemu public URL klasyfikacji.",
            "Odśwież klasyfikację i przygotowanie dla jednego bieżącego adresu.",
        )
    canonical_path = urlsplit(planning_input.final_canonical_url).path.rstrip("/") or "/"
    if canonical_path != classification.canonical_path:
        return blocker(
            "refresh_preparation_authorization_stale",
            "Odbudowany input ma inną ścieżkę strony",
            "Ścieżka finalnego URL planning input nie odpowiada bieżącej klasyfikacji.",
            "Odśwież klasyfikację i przygotowanie dla jednej bieżącej ścieżki.",
        )
    return None


def selected_service_candidate(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    service_card_id: str,
) -> ContentWorkItemServiceCandidate | None:
    context = snapshot.service_profile_context
    if (
        context.service_card_id != service_card_id
        or not context.service_selection_confirmed
        or context.binding_status != "bound"
    ):
        return None
    return next(
        (
            candidate
            for candidate in context.service_candidates
            if candidate.service_card_id == service_card_id
        ),
        None,
    )


def refresh_candidate(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    candidate: ContentWorkItemServiceCandidate,
) -> ContentRefreshPreparationServiceCandidate:
    context = snapshot.service_profile_context
    return ContentRefreshPreparationServiceCandidate(
        service_card_id=candidate.service_card_id,
        service_label=candidate.service_label,
        lifecycle_status=candidate.lifecycle_status,
        matched_terms=candidate.matched_terms,
        match_reasons=candidate.match_reasons,
        source_fact_ids=context.source_fact_ids,
        source_material_ids=context.source_material_ids,
        evidence_ids=context.evidence_ids,
        source_connectors=context.source_connectors,
    )


def planning_input_blockers(
    result: ContentPlanningInputBuildResult,
    *,
    include_generation: bool,
) -> list[ContentRefreshPreparationBlocker]:
    generation = planning_generation_blockers(result.blockers)
    selected = (
        result.blockers
        if include_generation
        else [item for item in result.blockers if item not in generation]
    )
    return [
        blocker(
            "refresh_preparation_input_blocked",
            item.label,
            item.reason,
            item.next_step,
            source_codes=[item.code],
        )
        for item in selected
    ]


def authorization_request_mismatch(
    preview: ContentRefreshPreparationReadyToAuthorize | ContentRefreshPreparationAuthorized,
    request: ContentRefreshPreparationAuthorizationRequest,
) -> ContentRefreshPreparationBlocker | None:
    comparisons: tuple[
        tuple[str, str, ContentRefreshPreparationBlockerCode, str], ...
    ] = (
        (
            request.expected_production_classification_run_digest,
            preview.classification.classification_run_digest,
            "refresh_preparation_authorization_stale",
            "Klasyfikacja zmieniła się przed autoryzacją",
        ),
        (
            request.expected_production_classification_decision_set_digest,
            preview.classification.decision_set_digest,
            "refresh_preparation_authorization_stale",
            "Zestaw decyzji klasyfikacji zmienił się przed autoryzacją",
        ),
        (
            request.expected_production_classification_source_packet_row_digest,
            preview.classification.source_packet_row_digest,
            "refresh_preparation_authorization_stale",
            "Wiersz klasyfikacji zmienił się przed autoryzacją",
        ),
        (
            request.expected_planning_input_digest,
            preview.planning_input_digest,
            "refresh_preparation_authorization_input_mismatch",
            "Wejście refresh zmieniło się przed autoryzacją",
        ),
    )
    for actual, expected, code, label in comparisons:
        if actual != expected:
            return blocker(
                code,
                label,
                "Żądanie nie odpowiada bieżącemu exact receipt przygotowania refresh.",
                "Odśwież przygotowanie i użyj wszystkich aktualnych digestów.",
            )
    preview_service_card_id = (
        None if preview.service_candidate is None else preview.service_candidate.service_card_id
    )
    if request.service_card_id != preview_service_card_id:
        return blocker(
            "refresh_preparation_authorization_service_mismatch",
            "Usługa zmieniła się przed autoryzacją",
            "Żądanie wskazuje inną usługę niż dokładnie odbudowany snapshot refresh.",
            "Odśwież przygotowanie i wybierz aktualną kartę usługi.",
        )
    return None


def authorization_matches_context(
    authorization: ContentRefreshPreparationAuthorization,
    classification: ContentRefreshPreparationClassificationBinding,
    planning_input: ContentPlanningInput,
) -> bool:
    return (
        authorization.classification_run_id == classification.classification_run_id
        and authorization.classification_run_digest == classification.classification_run_digest
        and authorization.decision_set_digest == classification.decision_set_digest
        and authorization.source_packet_row_digest == classification.source_packet_row_digest
        and authorization.canonical_path == classification.canonical_path
        and authorization.public_url == classification.public_url
        and authorization.acknowledged_classification_blocker_codes
        == classification.classification_blocker_codes
        and refresh_preparation_binding_matches_content_identity(
            authorization.binding,
            work_item_id=planning_input.work_item_id,
            service_card_id=planning_input.confirmed_service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            final_canonical_url=planning_input.final_canonical_url,
        )
    )


def proposal_matches_initial_request(
    proposal: ContentPlanningProposal,
    request: ContentInitialDraftRequest,
) -> bool:
    binding: ContentRefreshPreparationBinding | None = proposal.refresh_preparation_binding
    return bool(
        proposal.generation_status == "codex_generated"
        and proposal.proposal_id == request.expected_proposal_id
        and proposal.planning_digest == request.expected_planning_digest
        and proposal.planning_input_digest == request.expected_planning_input_digest
        and binding is not None
        and binding.authorization_id == request.refresh_preparation_authorization_id
        and binding.authorization_digest
        == request.expected_refresh_preparation_authorization_digest
    )


def blocker(
    code: ContentRefreshPreparationBlockerCode,
    label: str,
    reason: str,
    next_step: str,
    *,
    source_codes: list[str] | None = None,
) -> ContentRefreshPreparationBlocker:
    return ContentRefreshPreparationBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
        source_codes=source_codes or [],
    )


__all__ = [
    "approved_candidates",
    "authorization_matches_context",
    "authorization_request_mismatch",
    "blocker",
    "classified_refresh_context",
    "proposal_matches_initial_request",
    "rebuild_preparation",
]
