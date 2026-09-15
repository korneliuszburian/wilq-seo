from __future__ import annotations

from typing import Literal
from uuid import uuid4

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerTurnBlocker,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.operator_copy import build_blocker
from wilq.content.planning.dynamic_input import build_content_planning_input
from wilq.content.quality.review_packet_binding import (
    ReviewSnapshotLoader,
    resolve_content_review_inputs,
)
from wilq.content.quality.review_packet_binding import (
    content_review_snapshot_is_packet_bound as _is_packet_bound_snapshot,
)
from wilq.content.quality.review_packet_binding import (
    content_review_snapshot_packet_pair as _snapshot_packet_pair,
)
from wilq.content.quality.review_packet_binding import (
    same_content_review_inputs as _same_review_inputs,
)
from wilq.content.quality.semantic_inputs import (
    SemanticInputs,
)
from wilq.content.quality.semantic_inputs import (
    revision_evidence_ids as _revision_evidence_ids,
)
from wilq.content.quality.semantic_review_blockers import (
    deterministic_quality_gate_for_snapshot as _deterministic_quality_gate_for_snapshot,
)
from wilq.content.quality.semantic_review_blockers import (
    semantic_blocker_code as _semantic_blocker_code,
)
from wilq.content.quality.semantic_review_blockers import (
    storage_blocker as _storage_blocker,
)
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticBlockerCode,
    ContentSemanticFinding,
    ContentSemanticReview,
    ContentSemanticReviewBlocker,
    ContentSemanticReviewModelOutput,
    ContentSemanticReviewRequest,
    ContentSemanticReviewResponse,
)
from wilq.content.quality.semantic_review_guards import (
    apply_deterministic_quality_guards as _apply_deterministic_quality_guards,
)
from wilq.content.quality.semantic_review_guards import (
    review_scope_errors as _scope_errors,
)
from wilq.content.quality.semantic_review_packet import (
    semantic_binding_blocker as _semantic_binding_blocker,
)
from wilq.content.quality.semantic_review_packet import (
    semantic_review_response as _review_response,
)
from wilq.content.quality.semantic_review_runtime import (
    finish_semantic_run as _finish_run,
)
from wilq.content.quality.semantic_review_runtime import (
    semantic_runtime_trace as _trace,
)
from wilq.content.quality.semantic_review_store import (
    ContentSemanticReviewStore,
    SemanticReviewConflict,
    SemanticReviewDeadlineExpired,
    SemanticReviewStorageActivationRequired,
)
from wilq.content.quality.semantic_review_turn import semantic_review_turn_request
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.runtime.codex_run_lifecycle import (
    runtime_error,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore

_SemanticInputs = SemanticInputs


def read_content_semantic_review(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    store: ContentSemanticReviewStore,
) -> ContentSemanticReviewResponse:
    revision = snapshot.revision_workspace.latest_revision
    if revision is None:
        return _blocked(
            snapshot,
            blockers=[
                build_blocker(
                    ContentSemanticReviewBlocker,
                    code=_semantic_blocker_code("missing_revision"),
                    label="Brakuje pełnej wersji do review",
                    reason="Review semantyczne wymaga zapisanej exact revision.",
                    next_step="Najpierw wygeneruj pełny dokument.",
                )
            ],
        )
    if revision_id != revision.revision_id:
        historical = store.for_revision_id(revision.work_item_id, revision_id)
        if historical is not None:
            return ContentSemanticReviewResponse(
                status="stale",
                work_item_id=revision.work_item_id,
                revision_id=revision_id,
                revision_digest=historical.revision_digest,
                research_packet_id=historical.research_packet_id,
                research_packet_digest=historical.research_packet_digest,
                review=historical,
                run_id=historical.codex_run_id,
                safe_next_step=(
                    "To review dotyczy starszej rewizji; uruchom nowe dla bieżącej wersji."
                ),
            )
        return _blocked(
            snapshot,
            revision=revision,
            blockers=[
                build_blocker(
                    ContentSemanticReviewBlocker,
                    code=_semantic_blocker_code("stale_revision"),
                    label="Wybrana rewizja nie jest bieżąca",
                    reason="WILQ nie ma exact review dla wskazanej historycznej rewizji.",
                    next_step="Odśwież workspace i otwórz bieżącą rewizję.",
                )
            ],
        )
    exact = store.for_revision(
        revision.work_item_id,
        revision.revision_id,
        revision.content_digest,
    )
    if exact is not None:
        return _read_exact_review(snapshot, revision_id, revision, exact, store)
    preflight = _prepare_inputs(
        snapshot,
        revision_id,
        ContentSemanticReviewRequest(
            expected_revision_digest=revision.content_digest,
            requested_by="WILQ read preflight",
        ),
        store,
    )
    if isinstance(preflight, ContentSemanticReviewResponse):
        return preflight
    latest = store.latest(revision.work_item_id)
    if latest is None:
        return ContentSemanticReviewResponse(
            status="not_generated",
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            research_packet_id=revision.research_packet_id,
            research_packet_digest=revision.research_packet_digest,
            safe_next_step="Uruchom advisory review dla dokładnej bieżącej wersji.",
        )
    return ContentSemanticReviewResponse(
        status="stale",
        work_item_id=revision.work_item_id,
        revision_id=latest.revision_id,
        revision_digest=latest.revision_digest,
        research_packet_id=latest.research_packet_id,
        research_packet_digest=latest.research_packet_digest,
        review=latest,
        run_id=latest.codex_run_id,
        safe_next_step="Wersja zmieniła się; uruchom nowe review dla bieżącego digestu.",
    )


def generate_content_semantic_review(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    request: ContentSemanticReviewRequest,
    client: CodexAppServerClientProtocol,
    store: ContentSemanticReviewStore,
    run_store: LocalStateStore,
    run_id: str | None = None,
    snapshot_loader: ReviewSnapshotLoader | None = None,
) -> ContentSemanticReviewResponse:
    prepared = _prepare_inputs(
        snapshot,
        revision_id,
        request,
        store,
        snapshot_loader=snapshot_loader,
    )
    if isinstance(prepared, ContentSemanticReviewResponse):
        return prepared
    existing = store.for_revision(
        prepared.revision.work_item_id,
        prepared.revision.revision_id,
        prepared.revision.content_digest,
    )
    if existing is not None:
        return _review_response("idempotent", prepared.revision, existing)
    try:
        run = _start_run(prepared, run_store, run_id=run_id)
    except ValueError:
        return _expired_run_response(snapshot, prepared, run_store, run_id)
    runtime = _execute(snapshot, prepared, run, client, run_store)
    if isinstance(runtime, ContentSemanticReviewResponse):
        return runtime
    output, trace = runtime
    revalidated = _prepare_inputs(
        snapshot,
        revision_id,
        request,
        store,
        snapshot_loader=snapshot_loader,
    )
    if isinstance(revalidated, ContentSemanticReviewResponse):
        blocker = revalidated.blockers[0]
        return _finish_with_blocker(
            snapshot,
            prepared.revision,
            run,
            trace,
            blocker,
            run_store,
            response_status="blocked",
        )
    if not _same_review_inputs(prepared, revalidated):
        blocker = build_blocker(
            ContentSemanticReviewBlocker,
            code=_semantic_blocker_code("stale_content_context"),
            label="Zmienił się kontekst treści",
            reason="Planning input albo persisted proposal zmieniły się przed zapisem review.",
            next_step="Odśwież workspace i uruchom review dla bieżącej wersji.",
        )
        return _finish_with_blocker(
            snapshot,
            prepared.revision,
            run,
            trace,
            blocker,
            run_store,
            response_status="conflict",
        )
    scope_errors = _scope_errors(prepared.revision, output)
    if scope_errors:
        return _scope_mismatch_response(
            snapshot, prepared.revision, run, trace, run_store, scope_errors
        )
    return _persist_review(
        snapshot=snapshot,
        inputs=prepared,
        request=request,
        output=output,
        run=run,
        trace=trace,
        store=store,
        run_store=run_store,
    )


def _persist_review(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    inputs: _SemanticInputs,
    request: ContentSemanticReviewRequest,
    output: ContentSemanticReviewModelOutput,
    run: CodexRun,
    trace: ContentCodexRuntimeTrace,
    store: ContentSemanticReviewStore,
    run_store: LocalStateStore,
) -> ContentSemanticReviewResponse:
    review = _build_review(inputs, request, output, run)
    completed = run.model_copy(
        update={"status": "completed", "completed_at": utc_now(), "error": None}
    )
    try:
        stored = store.save_generated(review, completed)
    except SemanticReviewDeadlineExpired:
        return _finish_with_blocker(
            snapshot,
            inputs.revision,
            run,
            trace,
            build_blocker(
                ContentSemanticReviewBlocker,
                code=_semantic_blocker_code("runtime_failed"),
                label="Przekroczono czas review semantycznego",
                reason="Exact deadline minął przed atomowym zapisem wyniku.",
                next_step="Uruchom nową próbę review dla tej samej exact rewizji.",
                source_codes=["semantic_review_timeout"],
            ),
            run_store,
            response_status="failed",
            run_status="failed",
        )
    except SemanticReviewStorageActivationRequired:
        return _finish_with_blocker(
            snapshot, inputs.revision, run, trace, _storage_blocker(), run_store
        )
    except SemanticReviewConflict:
        return _finish_with_blocker(
            snapshot,
            inputs.revision,
            run,
            trace,
            build_blocker(
                ContentSemanticReviewBlocker,
                code=_semantic_blocker_code("review_conflict"),
                label="Review powstał równolegle",
                reason="WILQ nie nadpisze immutable review drugim wynikiem.",
                next_step="Odśwież review widoczne dla bieżącej wersji.",
            ),
            run_store,
            response_status="conflict",
        )
    except Exception:
        return _finish_with_blocker(
            snapshot,
            inputs.revision,
            run,
            trace,
            build_blocker(
                ContentSemanticReviewBlocker,
                code=_semantic_blocker_code("persistence_failed"),
                label="Nie zapisano review semantycznego",
                reason="Atomowy zapis review i terminalnego CodexRun nie powiódł się.",
                next_step="Sprawdź prywatny store; częściowe review nie jest dostępne.",
            ),
            run_store,
            response_status="failed",
            run_status="failed",
        )
    return ContentSemanticReviewResponse(
        status="created",
        work_item_id=stored.work_item_id,
        revision_id=stored.revision_id,
        revision_digest=stored.revision_digest,
        research_packet_id=stored.research_packet_id,
        research_packet_digest=stored.research_packet_digest,
        review=stored,
        run_id=stored.codex_run_id,
        runtime=trace,
        safe_next_step=stored.safe_next_step,
    )


def _prepare_inputs(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    request: ContentSemanticReviewRequest,
    store: ContentSemanticReviewStore,
    *,
    snapshot_loader: ReviewSnapshotLoader | None = None,
) -> _SemanticInputs | ContentSemanticReviewResponse:
    resolution = resolve_content_review_inputs(
        snapshot=snapshot,
        revision_id=revision_id,
        expected_revision_digest=request.expected_revision_digest,
        workflow_store=content_workflow_store(),
        snapshot_loader=snapshot_loader,
        planning_input_builder=build_content_planning_input,
    )
    if resolution.blocker is not None:
        revision = snapshot.revision_workspace.latest_revision
        return _blocked(
            snapshot,
            revision=revision,
            status=("conflict" if resolution.blocker.code == "stale_revision" else "blocked"),
            blockers=[_semantic_binding_blocker(resolution)],
        )
    inputs = resolution.inputs
    if inputs is None:
        raise RuntimeError("Review input resolver returned no exact context.")
    revision = inputs.revision
    planning_input = inputs.planning_input
    planning_proposal = inputs.proposal
    deterministic_blocker = _deterministic_quality_gate_for_snapshot(
        snapshot=snapshot,
        revision=revision,
        planning_input=planning_input,
        planning_proposal=planning_proposal,
    )
    if deterministic_blocker is not None:
        return _blocked(
            snapshot,
            revision=revision,
            blockers=[deterministic_blocker],
        )
    if not store.write_ready():
        return _blocked(snapshot, revision=revision, blockers=[_storage_blocker()])
    return _SemanticInputs(
        revision=revision,
        planning_input=planning_input,
        proposal=planning_proposal,
        review_inputs=inputs,
    )


def preflight_content_semantic_review(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    request: ContentSemanticReviewRequest,
    store: ContentSemanticReviewStore,
    snapshot_loader: ReviewSnapshotLoader | None = None,
) -> _SemanticInputs | ContentSemanticReviewResponse:
    """Validate review context without claiming a run or calling Codex."""

    return _prepare_inputs(
        snapshot,
        revision_id,
        request,
        store,
        snapshot_loader=snapshot_loader,
    )


def _execute(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    inputs: _SemanticInputs,
    run: CodexRun,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
) -> (
    tuple[ContentSemanticReviewModelOutput, ContentCodexRuntimeTrace]
    | ContentSemanticReviewResponse
):
    if run.deadline_at is not None and utc_now() >= run.deadline_at:
        return _expired_turn_response(snapshot, inputs, run, run_store)
    try:
        result = client.run_structured_turn(
            semantic_review_turn_request(
                revision=inputs.revision,
                planning_input=inputs.planning_input,
                proposal=inputs.proposal,
            )
        )
    except Exception:
        result = CodexAppServerTurnResult(
            status="failed",
            blockers=(
                CodexAppServerTurnBlocker(
                    code="codex_runtime_exception",
                    message="Lokalny runtime Codexa zakończył się nieoczekiwanym błędem.",
                ),
            ),
        )
    trace = _trace(result)
    if result.external_call_attempted:
        blocker = build_blocker(
            ContentSemanticReviewBlocker,
            code=_semantic_blocker_code("runtime_blocked"),
            label="Codex próbował wyjść poza review",
            reason="App-server zaobserwował próbę narzędzia albo zewnętrznego requestu.",
            next_step="Odrzuć wynik i sprawdź izolację runtime; WILQ nic nie zapisał.",
        )
        _finish_run(run_store, run, status="blocked", error=blocker.code)
        return _blocked(
            snapshot,
            revision=inputs.revision,
            blockers=[blocker],
            run=run,
            runtime=trace,
        )
    if result.status != "completed" or result.output_text is None:
        code: ContentSemanticBlockerCode = (
            "runtime_blocked" if result.status == "blocked" else "runtime_failed"
        )
        status: Literal["blocked", "failed"] = "blocked" if result.status == "blocked" else "failed"
        blocker = build_blocker(
            ContentSemanticReviewBlocker,
            code=_semantic_blocker_code(code),
            label="Codex nie zwrócił review semantycznego",
            reason="App-server nie zakończył advisory turnu poprawnym structured output.",
            next_step="Sprawdź runtime i uruchom nową próbę; WILQ nic nie zapisał.",
            source_codes=[item.code for item in result.blockers],
        )
        _finish_run(
            run_store,
            run,
            status=status,
            error=runtime_error(code, [item.code for item in result.blockers]),
        )
        return _blocked(
            snapshot,
            revision=inputs.revision,
            status=status,
            blockers=[blocker],
            run=run,
            runtime=trace,
        )
    try:
        output = ContentSemanticReviewModelOutput.model_validate_json(result.output_text)
        return _apply_deterministic_quality_guards(inputs, output), trace
    except ValueError:
        blocker = build_blocker(
            ContentSemanticReviewBlocker,
            code=_semantic_blocker_code("invalid_structured_output"),
            label="Codex zwrócił niepoprawne review",
            reason="Wynik nie ocenia dokładnie dziewięciu wymiarów kontraktu WILQ.",
            next_step="Odrzuć wynik i rozpocznij nowy advisory turn.",
        )
        _finish_run(run_store, run, status="blocked", error=blocker.code)
        return _blocked(
            snapshot,
            revision=inputs.revision,
            blockers=[blocker],
            run=run,
            runtime=trace,
        )


def _build_review(
    inputs: _SemanticInputs,
    request: ContentSemanticReviewRequest,
    output: ContentSemanticReviewModelOutput,
    run: CodexRun,
) -> ContentSemanticReview:
    review_id = f"content_semantic_review_{uuid4().hex}"
    findings = [
        ContentSemanticFinding(
            finding_id=f"{review_id}_finding_{index:02d}",
            **finding.model_dump(),
        )
        for index, finding in enumerate(output.findings, start=1)
    ]
    status: Literal["reviewable", "needs_changes"] = "needs_changes" if findings else "reviewable"
    return ContentSemanticReview(
        review_id=review_id,
        work_item_id=inputs.revision.work_item_id,
        revision_id=inputs.revision.revision_id,
        revision_digest=inputs.revision.content_digest,
        research_packet_id=inputs.revision.research_packet_id,
        research_packet_digest=inputs.revision.research_packet_digest,
        codex_run_id=run.id,
        status=status,
        dimensions=output.dimensions,
        findings=findings,
        evidence_ids=_revision_evidence_ids(inputs.revision),
        source_connectors=inputs.planning_input.source_connectors,
        requested_by=request.requested_by,
        created_at=utc_now(),
        safe_next_step=(
            "Wybierz sekcje wynikające z findings i zdecyduj, które poprawić."
            if findings
            else "Przejdź do niezależnego review człowieka; model niczego nie zatwierdził."
        ),
    )


def _start_run(
    inputs: _SemanticInputs,
    store: LocalStateStore,
    *,
    run_id: str | None = None,
) -> CodexRun:
    if run_id is not None:
        queued = next(
            (run for run in store.list_codex_runs() if run.id == run_id),
            None,
        )
        endpoint = (
            f"/api/content/work-items/{inputs.revision.work_item_id}/draft-revisions/"
            f"{inputs.revision.revision_id}/semantic-review"
        )
        if (
            queued is None
            or queued.status != "started"
            or queued.hook != "content_semantic_review"
            or queued.planning_input_digest != inputs.revision.planning_input_digest
            or endpoint not in queued.used_endpoints
            or (queued.deadline_at is not None and utc_now() >= queued.deadline_at)
        ):
            raise ValueError("semantic review queued run is no longer executable")
        return queued
    revision = inputs.revision
    return store.save_codex_run(
        CodexRun(
            id=run_id or f"codex_content_semantic_review_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_semantic_review",
            source="wilq_api",
            status="started",
            planning_input_digest=revision.planning_input_digest,
            used_endpoints=[
                f"/api/content/work-items/{revision.work_item_id}/draft-revisions/"
                f"{revision.revision_id}/semantic-review"
            ],
            evidence_ids=_revision_evidence_ids(revision),
        )
    )


def _expired_run_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    inputs: _SemanticInputs,
    store: LocalStateStore,
    run_id: str | None,
) -> ContentSemanticReviewResponse:
    existing_run = next(
        (item for item in store.list_codex_runs() if item.id == run_id),
        None,
    )
    blocker = build_blocker(
        ContentSemanticReviewBlocker,
        code=_semantic_blocker_code("runtime_failed"),
        label="Próba review wygasła przed uruchomieniem",
        reason="WILQ nie wskrzesił zakończonego albo przekroczonego deadline'u runu.",
        next_step="Uruchom nową próbę review dla tej samej exact rewizji.",
    )
    return _blocked(
        snapshot,
        revision=inputs.revision,
        status="failed",
        blockers=[blocker],
        run=existing_run,
        runtime=ContentCodexRuntimeTrace(status="failed"),
    )


def _scope_mismatch_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision: ContentDraftRevision,
    run: CodexRun,
    trace: ContentCodexRuntimeTrace,
    store: LocalStateStore,
    scope_errors: list[str],
) -> ContentSemanticReviewResponse:
    blocker = build_blocker(
        ContentSemanticReviewBlocker,
        code=_semantic_blocker_code("semantic_scope_mismatch"),
        label="Review wyszedł poza dokładną wersję",
        reason="Finding wskazuje obcy target, dowód albo niespójny wymiar.",
        next_step="Odrzuć wynik i uruchom nowy advisory review dla bieżącej rewizji.",
        source_codes=scope_errors,
    )
    _finish_run(store, run, status="blocked", error=blocker.code)
    return _blocked(
        snapshot,
        revision=revision,
        blockers=[blocker],
        run=run,
        runtime=trace,
    )


def _expired_turn_response(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    inputs: _SemanticInputs,
    run: CodexRun,
    store: LocalStateStore,
) -> ContentSemanticReviewResponse:
    blocker = build_blocker(
        ContentSemanticReviewBlocker,
        code=_semantic_blocker_code("runtime_failed"),
        label="Przekroczono czas review semantycznego",
        reason="Exact deadline minął przed rozpoczęciem tury Codexa.",
        next_step="Uruchom nową próbę review dla tej samej exact rewizji.",
    )
    _finish_run(store, run, status="failed", error="semantic_review_timeout")
    return _blocked(
        snapshot,
        revision=inputs.revision,
        status="failed",
        blockers=[blocker],
        run=run,
        runtime=ContentCodexRuntimeTrace(status="failed"),
    )


def _finish_with_blocker(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision: ContentDraftRevision,
    run: CodexRun,
    trace: ContentCodexRuntimeTrace,
    blocker: ContentSemanticReviewBlocker,
    run_store: LocalStateStore,
    *,
    response_status: Literal["blocked", "failed", "conflict"] = "blocked",
    run_status: Literal["blocked", "failed"] = "blocked",
) -> ContentSemanticReviewResponse:
    _finish_run(
        run_store,
        run,
        status=run_status,
        error=runtime_error(blocker.code, blocker.source_codes),
    )
    return _blocked(
        snapshot,
        revision=revision,
        status=response_status,
        blockers=[blocker],
        run=run,
        runtime=trace,
    )


def _read_exact_review(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    revision: ContentDraftRevision,
    review: ContentSemanticReview,
    store: ContentSemanticReviewStore,
) -> ContentSemanticReviewResponse:
    if _is_packet_bound_snapshot(snapshot):
        preflight = _prepare_inputs(
            snapshot,
            revision_id,
            ContentSemanticReviewRequest(
                expected_revision_digest=revision.content_digest,
                requested_by="WILQ read preflight",
            ),
            store,
        )
        if isinstance(preflight, ContentSemanticReviewResponse):
            return preflight
        review_packet_pair = (
            review.research_packet_id,
            review.research_packet_digest,
        )
        if review_packet_pair != _snapshot_packet_pair(snapshot):
            return _blocked(
                snapshot,
                revision=revision,
                blockers=[
                    build_blocker(
                        ContentSemanticReviewBlocker,
                        code=_semantic_blocker_code("research_packet_conflict"),
                        label="Review nie jest związany z exact packetem",
                        reason=(
                            "Zapisany review nie ma tego samego packet ID i digestu co "
                            "bieżący packet. Historyczny wynik pozostaje niezmieniony."
                        ),
                        next_step="Utwórz nowe exact review dla bieżącego packetu.",
                    )
                ],
            )
    return _review_response("ready", revision, review)


def _blocked(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    blockers: list[ContentSemanticReviewBlocker],
    revision: ContentDraftRevision | None = None,
    status: Literal["blocked", "failed", "conflict"] = "blocked",
    run: CodexRun | None = None,
    runtime: ContentCodexRuntimeTrace | None = None,
) -> ContentSemanticReviewResponse:
    return ContentSemanticReviewResponse(
        status=status,
        work_item_id=snapshot.preflight.item.id,
        revision_id=None if revision is None else revision.revision_id,
        revision_digest=None if revision is None else revision.content_digest,
        research_packet_id=(None if revision is None else revision.research_packet_id),
        research_packet_digest=(
            None if revision is None else revision.research_packet_digest
        ),
        run_id=None if run is None else run.id,
        runtime=runtime or ContentCodexRuntimeTrace(status="not_started"),
        blockers=blockers,
        safe_next_step=blockers[0].next_step,
    )


__all__ = [
    "generate_content_semantic_review",
    "preflight_content_semantic_review",
    "read_content_semantic_review",
]
