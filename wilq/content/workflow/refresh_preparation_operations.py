"""Preview, authorization, and runtime operations for classified refresh work."""

from __future__ import annotations

from dataclasses import replace

from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    build_content_planning_workspace,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationAuthorizationConflictResponse,
    ContentRefreshPreparationAuthorizationCreatedResponse,
    ContentRefreshPreparationAuthorizationIdempotentResponse,
    ContentRefreshPreparationAuthorizationRequest,
    ContentRefreshPreparationAuthorizationResponse,
    ContentRefreshPreparationAuthorized,
    ContentRefreshPreparationBlocked,
    ContentRefreshPreparationBlocker,
    ContentRefreshPreparationPreview,
    ContentRefreshPreparationReadyToAuthorize,
    ContentRefreshPreparationSelectionRequired,
    ContentRefreshPreparationStale,
    build_content_refresh_preparation_authorization,
)
from wilq.content.workflow.refresh_preparation_models import (
    RefreshClassificationContext,
    RefreshPreparationRuntimeAuthorized,
    RefreshPreparationRuntimeBlocked,
    RefreshPreparationRuntimeResolution,
    RefreshPreparationSnapshotLoader,
    RefreshPreparationStore,
    RefreshPreparationUnclassified,
)
from wilq.content.workflow.refresh_preparation_resolution import (
    approved_candidates,
    authorization_matches_context,
    authorization_request_mismatch,
    blocker,
    classified_refresh_context,
    proposal_matches_initial_request,
    rebuild_preparation,
)
from wilq.schemas.core import utc_now


def preview(
    *,
    store: RefreshPreparationStore,
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
    service_card_id: str | None,
) -> ContentRefreshPreparationPreview:
    classified = classified_refresh_context(store, work_item_id)
    if isinstance(classified, ContentRefreshPreparationBlocker):
        return blocked_preview(work_item_id, classified)
    if classified is None:
        return blocked_preview(
            work_item_id,
            blocker(
                "production_classification_missing",
                "Brakuje klasyfikacji produkcyjnej",
                "Nie ma bieżącej klasyfikacji dla tej strony, więc ręczna autoryzacja "
                "refresh nie może powstać.",
                "Najpierw zapisz aktualną klasyfikację produkcyjną dla tej strony.",
            ),
        )
    stale = stale_preview(work_item_id, classified)
    if stale is not None:
        return stale
    if service_card_id is None:
        return selection_preview(snapshot_loader, work_item_id, classified)
    return selected_preview(store, snapshot_loader, work_item_id, classified, service_card_id)


def stale_preview(
    work_item_id: str,
    classified: RefreshClassificationContext,
) -> ContentRefreshPreparationStale | None:
    if not classified.run.freshness.requires_refresh:
        return None
    item = blocker(
        "stale_production_classification",
        "Klasyfikacja produkcyjna wymaga odświeżenia",
        "Najświeższa zaakceptowana klasyfikacja wskazuje konieczność odświeżenia źródeł.",
        "Odśwież klasyfikację z aktualnych źródeł, a następnie ponów przygotowanie.",
        source_codes=list(classified.run.freshness.connector_ids),
    )
    return ContentRefreshPreparationStale(
        status="stale",
        work_item_id=work_item_id,
        classification=classified.binding,
        blockers=[item],
        safe_next_step=item.next_step,
    )


def selection_preview(
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
    classified: RefreshClassificationContext,
) -> ContentRefreshPreparationPreview:
    candidates = approved_candidates(snapshot_loader, work_item_id)
    if not candidates:
        return blocked_preview(
            work_item_id,
            blocker(
                "refresh_preparation_service_unavailable",
                "Brakuje aktualnej karty usługi",
                "Żaden kandydat usługi dla bieżącego snapshotu nie ma pełnej "
                "zatwierdzonej linii źródłowej.",
                "Uzupełnij zatwierdzoną kartę usługi z evidence i source IDs przed "
                "przygotowaniem refresh.",
            ),
            classification=classified,
        )
    return ContentRefreshPreparationSelectionRequired(
        status="selection_required",
        work_item_id=work_item_id,
        classification=classified.binding,
        service_candidates=candidates,
        safe_next_step=(
            "Wybierz jedną aktualną kartę usługi; WILQ odbuduje pełne wejście "
            "refresh dla tego wyboru."
        ),
    )


def selected_preview(
    store: RefreshPreparationStore,
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
    classified: RefreshClassificationContext,
    service_card_id: str,
) -> ContentRefreshPreparationPreview:
    prepared = rebuild_preparation(
        snapshot_loader=snapshot_loader,
        work_item_id=work_item_id,
        classification=classified,
        service_card_id=service_card_id,
    )
    if isinstance(prepared, ContentRefreshPreparationBlocked):
        return prepared
    _snapshot, planning_input, candidate, informational = prepared
    try:
        authorization = store.find_refresh_preparation_authorization(
            work_item_id=work_item_id,
            classification_run_digest=classified.binding.classification_run_digest,
            decision_set_digest=classified.binding.decision_set_digest,
            source_packet_row_digest=classified.binding.source_packet_row_digest,
            canonical_path=classified.binding.canonical_path,
            public_url=classified.binding.public_url,
            planning_input_digest=planning_input.planning_input_digest,
            service_card_id=candidate.service_card_id,
        )
    except ValueError:
        return blocked_preview(
            work_item_id,
            corrupt_authorization_blocker(),
            classification=classified,
        )
    input_summary = content_planning_input_summary(planning_input)
    if authorization is None:
        return ContentRefreshPreparationReadyToAuthorize(
            status="ready_to_authorize",
            work_item_id=work_item_id,
            classification=classified.binding,
            service_candidate=candidate,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=input_summary,
            blockers=informational,
            safe_next_step=(
                "Potwierdź dokładne blockery klasyfikacji, aby zapisać jedną lokalną "
                "autoryzację tylko dla tego refresh i inputu."
            ),
        )
    return ContentRefreshPreparationAuthorized(
        status="authorized",
        work_item_id=work_item_id,
        classification=classified.binding,
        service_candidate=candidate,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=input_summary,
        blockers=informational,
        authorization=authorization,
        safe_next_step=(
            "Autoryzacja jest aktualna dla tego dokładnego inputu; można przygotować "
            "plan albo pełny tekst tylko z jej bindingiem."
        ),
    )


def authorize(
    *,
    store: RefreshPreparationStore,
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
    request: ContentRefreshPreparationAuthorizationRequest,
) -> ContentRefreshPreparationAuthorizationResponse:
    current = preview(
        store=store,
        snapshot_loader=snapshot_loader,
        work_item_id=work_item_id,
        service_card_id=request.service_card_id,
    )
    if not isinstance(
        current,
        (ContentRefreshPreparationReadyToAuthorize, ContentRefreshPreparationAuthorized),
    ):
        return conflict_from_preview(current)
    mismatch = authorization_request_mismatch(current, request)
    if mismatch is not None:
        return conflict_response(mismatch)
    if (
        request.acknowledged_classification_blocker_codes
        != current.classification.classification_blocker_codes
    ):
        return conflict_response(
            blocker(
                "refresh_preparation_acknowledgement_mismatch",
                "Potwierdzenie blockerów nie jest kompletne",
                "Autoryzacja refresh musi potwierdzać dokładnie bieżący zbiór kodów "
                "blockerów klasyfikacji.",
                "Odśwież przygotowanie i potwierdź wszystkie oraz tylko widoczne kody "
                "blockerów.",
                source_codes=current.classification.classification_blocker_codes,
            )
        )
    return record_authorization(store, work_item_id, current, request)


def record_authorization(
    store: RefreshPreparationStore,
    work_item_id: str,
    current: ContentRefreshPreparationReadyToAuthorize | ContentRefreshPreparationAuthorized,
    request: ContentRefreshPreparationAuthorizationRequest,
) -> ContentRefreshPreparationAuthorizationResponse:
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=work_item_id,
        classification=current.classification,
        planning_input_digest=current.planning_input_digest,
        content_kind=current.content_kind,
        service_card_id=(
            None
            if current.service_candidate is None
            else current.service_candidate.service_card_id
        ),
        acknowledged_classification_blocker_codes=request.acknowledged_classification_blocker_codes,
        authorized_by=request.authorized_by,
        authorized_at=utc_now(),
    )
    try:
        stored = store.record_refresh_preparation_authorization(authorization)
    except ValueError:
        return conflict_response(
            blocker(
                "refresh_preparation_authorization_stale",
                "Autoryzacja zmieniła się przed zapisem",
                "Atomowy zapis wykrył nowszą klasyfikację lub inny bieżący wiersz strony.",
                "Odśwież przygotowanie refresh i ponów autoryzację dla bieżącego receipt.",
            )
        )
    if stored.status == "conflict":
        return conflict_response(
            blocker(
                "refresh_preparation_authorization_conflict",
                "Autoryzacja dla tego kontekstu już istnieje",
                "Istniejąca autoryzacja ma innego operatora albo inny zestaw "
                "potwierdzonych blockerów; WILQ nie nadpisuje jej.",
                "Otwórz istniejącą autoryzację albo przygotuj nowy dokładny kontekst "
                "po zmianie źródeł.",
            )
        )
    if stored.status == "created":
        return ContentRefreshPreparationAuthorizationCreatedResponse(
            status="created",
            authorization=stored.authorization,
            safe_next_step=(
                "Autoryzacja jest zapisana lokalnie i dotyczy tylko bieżącej "
                "klasyfikacji, wybranej usługi oraz exact inputu refresh."
            ),
        )
    return ContentRefreshPreparationAuthorizationIdempotentResponse(
        status="idempotent",
        authorization=stored.authorization,
        safe_next_step=(
            "Autoryzacja jest zapisana lokalnie i dotyczy tylko bieżącej "
            "klasyfikacji, wybranej usługi oraz exact inputu refresh."
        ),
    )


def resolve_planning(
    *,
    store: RefreshPreparationStore,
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
    request: ContentPlanningProposalRequest,
) -> RefreshPreparationRuntimeResolution:
    if (
        request.refresh_preparation_authorization_id is not None
        and classified_refresh_context(store, work_item_id) is None
    ):
        return RefreshPreparationRuntimeBlocked(
            work_item_id,
            authorization_on_unclassified_blocker(),
        )
    if request.refresh_preparation_authorization_id is None:
        return unclassified_or_refresh_block(store, work_item_id)
    if request.service_card_id is None:
        return RefreshPreparationRuntimeBlocked(
            work_item_id,
            blocker(
                "refresh_preparation_authorization_foreign",
                "Autoryzacja editorial nie została jeszcze aktywowana",
                "Publiczny planning obsługuje editorial, ale sklasyfikowany refresh wymaga "
                "jeszcze persisted content-kind receipt.",
                "Użyj zwykłego workflow editorial albo dokończ migrację authority receipt.",
            ),
        )
    return resolve_authorized_context(
        store=store,
        snapshot_loader=snapshot_loader,
        work_item_id=work_item_id,
        service_card_id=request.service_card_id,
        planning_input_digest=request.expected_planning_input_digest,
        authorization_id=request.refresh_preparation_authorization_id,
        authorization_digest=request.expected_refresh_preparation_authorization_digest,
    )


def resolve_initial_draft(
    *,
    store: RefreshPreparationStore,
    snapshot_loader: RefreshPreparationSnapshotLoader,
    proposal_store: ContentPlanningProposalStore,
    work_item_id: str,
    request: ContentInitialDraftRequest,
) -> RefreshPreparationRuntimeResolution:
    classified = classified_refresh_context(store, work_item_id)
    if classified is None:
        if request.refresh_preparation_authorization_id is not None:
            return RefreshPreparationRuntimeBlocked(
                work_item_id,
                authorization_on_unclassified_blocker(),
            )
        return RefreshPreparationUnclassified(work_item_id)
    if isinstance(classified, ContentRefreshPreparationBlocker):
        return RefreshPreparationRuntimeBlocked(work_item_id, classified)
    if request.refresh_preparation_authorization_id is None:
        return RefreshPreparationRuntimeBlocked(work_item_id, missing_authorization_blocker())
    proposal = proposal_store.latest(work_item_id)
    if proposal is None or not proposal_matches_initial_request(proposal, request):
        return RefreshPreparationRuntimeBlocked(work_item_id, proposal_binding_blocker())
    if proposal.service_card_id is None or proposal.planning_input_digest is None:
        return RefreshPreparationRuntimeBlocked(work_item_id, proposal_binding_blocker())
    resolved = resolve_authorized_context(
        store=store,
        snapshot_loader=snapshot_loader,
        work_item_id=work_item_id,
        service_card_id=proposal.service_card_id,
        planning_input_digest=proposal.planning_input_digest,
        authorization_id=request.refresh_preparation_authorization_id,
        authorization_digest=request.expected_refresh_preparation_authorization_digest,
    )
    return bind_initial_proposal(resolved, proposal, request)


def bind_initial_proposal(
    resolved: RefreshPreparationRuntimeResolution,
    proposal: ContentPlanningProposal,
    request: ContentInitialDraftRequest,
) -> RefreshPreparationRuntimeResolution:
    if not isinstance(resolved, RefreshPreparationRuntimeAuthorized):
        return resolved
    if proposal.refresh_preparation_binding != resolved.binding:
        return RefreshPreparationRuntimeBlocked(
            resolved.work_item_id,
            proposal_binding_blocker(),
        )
    if resolved.planning_input.planning_input_digest != request.expected_planning_input_digest:
        return RefreshPreparationRuntimeBlocked(
            resolved.work_item_id,
            blocker(
                "refresh_preparation_authorization_input_mismatch",
                "Wejście planu zmieniło się po autoryzacji",
                "Żądanie pełnego tekstu wskazuje inny planning_input_digest niż bieżący "
                "autoryzowany snapshot.",
                "Odśwież plan i uruchom draft dla bieżącego exact inputu.",
            ),
        )
    return replace(
        resolved,
        snapshot=resolved.snapshot.model_copy(
            update={"planning_workspace": build_content_planning_workspace(proposal, [])}
        ),
    )


def resolve_authorized_context(
    *,
    store: RefreshPreparationStore,
    snapshot_loader: RefreshPreparationSnapshotLoader,
    work_item_id: str,
    service_card_id: str,
    planning_input_digest: str,
    authorization_id: str,
    authorization_digest: str | None,
) -> RefreshPreparationRuntimeResolution:
    classified = classified_refresh_context(store, work_item_id)
    if classified is None:
        return RefreshPreparationUnclassified(work_item_id)
    if isinstance(classified, ContentRefreshPreparationBlocker):
        return RefreshPreparationRuntimeBlocked(work_item_id, classified)
    stale = stale_preview(work_item_id, classified)
    if stale is not None:
        return RefreshPreparationRuntimeBlocked(work_item_id, stale.blockers[0])
    prepared = rebuild_preparation(
        snapshot_loader=snapshot_loader,
        work_item_id=work_item_id,
        classification=classified,
        service_card_id=service_card_id,
    )
    if isinstance(prepared, ContentRefreshPreparationBlocked):
        return RefreshPreparationRuntimeBlocked(work_item_id, prepared.blockers[0])
    snapshot, planning_input, candidate, _ = prepared
    if planning_input.planning_input_digest != planning_input_digest:
        return RefreshPreparationRuntimeBlocked(work_item_id, input_mismatch_blocker())
    try:
        authorization = store.load_refresh_preparation_authorization(authorization_id)
    except ValueError:
        return RefreshPreparationRuntimeBlocked(
            work_item_id,
            corrupt_authorization_blocker(),
        )
    invalid = authorization_validation_blocker(
        authorization=authorization,
        authorization_digest=authorization_digest,
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        classification=classified,
        planning_input=planning_input,
    )
    if invalid is not None:
        return RefreshPreparationRuntimeBlocked(work_item_id, invalid)
    # Keep the runtime boundary explicit even though validation above rejects it:
    # persisted state is untrusted and this path must never rely on assertions.
    if authorization is None:
        return RefreshPreparationRuntimeBlocked(
            work_item_id,
            missing_authorization_blocker(),
        )
    return RefreshPreparationRuntimeAuthorized(
        work_item_id=work_item_id,
        snapshot=snapshot,
        planning_input=planning_input,
        classification=classified.binding,
        service_candidate=candidate,
        authorization=authorization,
    )


def authorization_validation_blocker(
    *,
    authorization: ContentRefreshPreparationAuthorization | None,
    authorization_digest: str | None,
    work_item_id: str,
    service_card_id: str,
    classification: RefreshClassificationContext,
    planning_input: ContentPlanningInput,
) -> ContentRefreshPreparationBlocker | None:
    if authorization is None:
        return blocker(
            "refresh_preparation_authorization_foreign",
            "Nie znaleziono tej autoryzacji refresh",
            "Żądanie wskazuje identyfikator autoryzacji, którego nie ma w lokalnym workflow.",
            "Odśwież przygotowanie i użyj widocznej autoryzacji dla tej strony.",
        )
    if authorization_digest is None or authorization.authorization_digest != authorization_digest:
        return blocker(
            "refresh_preparation_authorization_digest_mismatch",
            "Digest autoryzacji nie pasuje",
            "Żądanie nie jest związane z dokładnym, zapisanym receipt autoryzacji.",
            "Odśwież przygotowanie i użyj aktualnego authorization digest.",
        )
    if authorization.work_item_id != work_item_id:
        return blocker(
            "refresh_preparation_authorization_foreign",
            "Autoryzacja należy do innej strony",
            "Autoryzacja refresh może dotyczyć wyłącznie jej bieżącego work itemu.",
            "Otwórz autoryzację przygotowaną dla tej dokładnej strony.",
        )
    if authorization.service_card_id != service_card_id:
        return blocker(
            "refresh_preparation_authorization_service_mismatch",
            "Usługa nie pasuje do autoryzacji",
            "Wybrana karta usługi różni się od karty związanej z zapisanym receipt "
            "autoryzacji.",
            "Odśwież przygotowanie i wybierz usługę zapisaną w aktualnej autoryzacji.",
        )
    if not authorization_matches_context(authorization, classification.binding, planning_input):
        return blocker(
            "refresh_preparation_authorization_stale",
            "Autoryzacja refresh nie pasuje już do kontekstu",
            "Klasyfikacja albo źródłowy input zmieniły się od czasu zapisania autoryzacji.",
            "Otwórz bieżące przygotowanie i zapisz nową autoryzację dla aktualnego kontekstu.",
        )
    return None


def corrupt_authorization_blocker() -> ContentRefreshPreparationBlocker:
    return blocker(
        "refresh_preparation_authorization_stale",
        "Autoryzacja refresh nie jest czytelna",
        "Zapisany receipt autoryzacji ma uszkodzony payload albo niezgodne identyfikatory "
        "trwałe, więc nie może zostać użyty.",
        "Odśwież przygotowanie refresh i zapisz nową autoryzację dla bieżącego receipt.",
    )


def unclassified_or_refresh_block(
    store: RefreshPreparationStore,
    work_item_id: str,
) -> RefreshPreparationRuntimeResolution:
    classified = classified_refresh_context(store, work_item_id)
    if classified is None:
        return RefreshPreparationUnclassified(work_item_id)
    if isinstance(classified, ContentRefreshPreparationBlocker):
        return RefreshPreparationRuntimeBlocked(work_item_id, classified)
    return RefreshPreparationRuntimeBlocked(work_item_id, missing_authorization_blocker())


def missing_authorization_blocker() -> ContentRefreshPreparationBlocker:
    return blocker(
        "refresh_preparation_authorization_missing",
        "Brakuje autoryzacji refresh",
        "Najnowsza klasyfikacja wymaga ręcznej, dokładnie związanej autoryzacji "
        "przed generowaniem.",
        "Otwórz przygotowanie refresh i zapisz autoryzację dla bieżącego inputu.",
    )


def authorization_on_unclassified_blocker() -> ContentRefreshPreparationBlocker:
    return blocker(
        "refresh_preparation_authorization_foreign",
        "Autoryzacja refresh nie ma bieżącej klasyfikacji",
        "Żądanie przekazuje receipt refresh, ale dla tej strony nie istnieje bieżący "
        "wiersz klasyfikacji refresh. WILQ nie obniży żądania do ścieżki legacy.",
        "Usuń receipt z żądania legacy albo odśwież klasyfikację i użyj bieżącej autoryzacji.",
    )


def proposal_binding_blocker() -> ContentRefreshPreparationBlocker:
    return blocker(
        "refresh_preparation_proposal_binding_mismatch",
        "Plan nie jest związany z autoryzacją refresh",
        "Pełny tekst wymaga dokładnego wygenerowanego planu z tym samym "
        "authorization ID i digestem.",
        "Odśwież plan i użyj wersji wygenerowanej dla aktualnej autoryzacji refresh.",
    )


def input_mismatch_blocker() -> ContentRefreshPreparationBlocker:
    return blocker(
        "refresh_preparation_authorization_input_mismatch",
        "Wejście refresh nie jest już aktualne",
        "Bieżący pełny snapshot wyliczył inny planning_input_digest niż żądanie.",
        "Odśwież przygotowanie, wygeneruj nowy plan i użyj bieżącego digestu.",
    )


def planning_block_response(
    resolution: RefreshPreparationRuntimeResolution,
    request: ContentPlanningProposalRequest,
) -> ContentPlanningProposalResponse | None:
    if isinstance(
        resolution,
        (RefreshPreparationUnclassified, RefreshPreparationRuntimeAuthorized),
    ):
        return None
    item = resolution.blocker
    return ContentPlanningProposalResponse(
        status="blocked",
        work_item_id=resolution.work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        blockers=[
            ContentPlanningProposalBlocker(
                code=item.code,
                label=item.label,
                reason=item.reason,
                next_step=item.next_step,
                source_codes=item.source_codes,
            )
        ],
        safe_next_step=item.next_step,
    )


def initial_draft_block_response(
    resolution: RefreshPreparationRuntimeResolution,
    request: ContentInitialDraftRequest,
) -> ContentInitialDraftResponse | None:
    if isinstance(
        resolution,
        (RefreshPreparationUnclassified, RefreshPreparationRuntimeAuthorized),
    ):
        return None
    item = resolution.blocker
    blocker_response = ContentInitialDraftBlocker(
        code=item.code,
        label=item.label,
        reason=item.reason,
        next_step=item.next_step,
        source_codes=item.source_codes,
    )
    return ContentInitialDraftResponse(
        status="conflict",
        work_item_id=resolution.work_item_id,
        proposal_id=request.expected_proposal_id,
        blockers=[blocker_response],
        safe_next_step=blocker_response.next_step,
    )


def blocked_preview(
    work_item_id: str,
    item: ContentRefreshPreparationBlocker,
    *,
    classification: RefreshClassificationContext | None = None,
) -> ContentRefreshPreparationBlocked:
    return ContentRefreshPreparationBlocked(
        status="blocked",
        work_item_id=work_item_id,
        classification=None if classification is None else classification.binding,
        blockers=[item],
        safe_next_step=item.next_step,
    )


def conflict_from_preview(
    preview_value: ContentRefreshPreparationPreview,
) -> ContentRefreshPreparationAuthorizationResponse:
    blockers = list(getattr(preview_value, "blockers", []))
    if not blockers:
        blockers = [
            blocker(
                "refresh_preparation_authorization_stale",
                "Kontekst autoryzacji nie jest już aktualny",
                "Bieżąca klasyfikacja albo wejście refresh nie pozwala zapisać tej autoryzacji.",
                "Odśwież przygotowanie i użyj aktualnego snapshotu.",
            )
        ]
    return ContentRefreshPreparationAuthorizationConflictResponse(
        status="conflict",
        blockers=blockers,
        safe_next_step=blockers[0].next_step,
    )


def conflict_response(
    item: ContentRefreshPreparationBlocker,
) -> ContentRefreshPreparationAuthorizationResponse:
    return ContentRefreshPreparationAuthorizationConflictResponse(
        status="conflict",
        blockers=[item],
        safe_next_step=item.next_step,
    )


__all__ = [
    "authorize",
    "initial_draft_block_response",
    "planning_block_response",
    "preview",
    "resolve_initial_draft",
    "resolve_planning",
]
