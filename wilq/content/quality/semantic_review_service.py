from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, cast
from uuid import uuid4

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerTurnBlocker,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning.dynamic_input import build_content_planning_input
from wilq.content.quality.semantic_inputs import SemanticInputs
from wilq.content.quality.semantic_review_contracts import (
    ContentSemanticBlockerCode,
    ContentSemanticFinding,
    ContentSemanticFindingOutput,
    ContentSemanticReview,
    ContentSemanticReviewBlocker,
    ContentSemanticReviewModelOutput,
    ContentSemanticReviewRequest,
    ContentSemanticReviewResponse,
)
from wilq.content.quality.semantic_review_guards import (
    regulatory_quality_issues,
    repetition_quality_issues,
)
from wilq.content.quality.semantic_review_store import (
    ContentSemanticReviewStore,
    SemanticReviewConflict,
    SemanticReviewDeadlineExpired,
    SemanticReviewStorageActivationRequired,
)
from wilq.content.quality.semantic_review_turn import semantic_review_turn_request
from wilq.content.quality.semantic_run_state import (
    runtime_error,
    transition_codex_run_if_status,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.revisions import ContentDraftRevision
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
                _blocker(
                    "missing_revision",
                    "Brakuje pełnej wersji do review",
                    "Review semantyczne wymaga zapisanej exact revision.",
                    "Najpierw wygeneruj pełny dokument.",
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
                _blocker(
                    "stale_revision",
                    "Wybrana rewizja nie jest bieżąca",
                    "WILQ nie ma exact review dla wskazanej historycznej rewizji.",
                    "Odśwież workspace i otwórz bieżącą rewizję.",
                )
            ],
        )
    exact = store.for_revision(
        revision.work_item_id,
        revision.revision_id,
        revision.content_digest,
    )
    if exact is not None:
        return _review_response("ready", revision, exact)
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
            safe_next_step="Uruchom advisory review dla dokładnej bieżącej wersji.",
        )
    return ContentSemanticReviewResponse(
        status="stale",
        work_item_id=revision.work_item_id,
        revision_id=latest.revision_id,
        revision_digest=latest.revision_digest,
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
) -> ContentSemanticReviewResponse:
    prepared = _prepare_inputs(snapshot, revision_id, request, store)
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
            snapshot, inputs.revision, run, trace,
            _blocker(
                "runtime_failed", "Przekroczono czas review semantycznego",
                "Exact deadline minął przed atomowym zapisem wyniku.",
                "Uruchom nową próbę review dla tej samej exact rewizji.",
                source_codes=["semantic_review_timeout"],
            ), run_store, response_status="failed", run_status="failed"
        )
    except SemanticReviewStorageActivationRequired:
        return _finish_with_blocker(
            snapshot, inputs.revision, run, trace, _storage_blocker(), run_store
        )
    except SemanticReviewConflict:
        return _finish_with_blocker(
            snapshot, inputs.revision, run, trace,
            _blocker(
                "review_conflict", "Review powstał równolegle",
                "WILQ nie nadpisze immutable review drugim wynikiem.",
                "Odśwież review widoczne dla bieżącej wersji.",
            ), run_store, response_status="conflict"
        )
    except Exception:
        return _finish_with_blocker(
            snapshot, inputs.revision, run, trace,
            _blocker(
                "persistence_failed", "Nie zapisano review semantycznego",
                "Atomowy zapis review i terminalnego CodexRun nie powiódł się.",
                "Sprawdź prywatny store; częściowe review nie jest dostępne.",
            ), run_store, response_status="failed", run_status="failed"
        )
    return ContentSemanticReviewResponse(
        status="created", work_item_id=stored.work_item_id,
        revision_id=stored.revision_id, revision_digest=stored.revision_digest,
        review=stored, run_id=stored.codex_run_id, runtime=trace,
        safe_next_step=stored.safe_next_step,
    )


def _prepare_inputs(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    revision_id: str,
    request: ContentSemanticReviewRequest,
    store: ContentSemanticReviewStore,
) -> _SemanticInputs | ContentSemanticReviewResponse:
    revision = snapshot.revision_workspace.latest_revision
    if revision is None:
        return _blocked(snapshot, blockers=[_missing_revision_blocker()])
    if (
        revision_id != revision.revision_id
        or request.expected_revision_digest != revision.content_digest
    ):
        return _blocked(
            snapshot,
            revision=revision,
            status="conflict",
            blockers=[
                _blocker(
                    "stale_revision",
                    "Wybrana wersja nie jest aktualna",
                    "Revision ID albo digest zmienił się przed review.",
                    "Odśwież workspace i uruchom review bieżącej wersji.",
                )
            ],
        )
    if revision.schema_version != "wilq_content_draft_revision_v2":
        return _blocked(
            snapshot,
            revision=revision,
            blockers=[
                _blocker(
                    "legacy_revision",
                    "Starsza wersja nie zawiera całej strony",
                    "Review semantyczne wymaga rewizji v2 z page assets, FAQ i CTA.",
                    "Utwórz pełny dokument v2 przed review.",
                )
            ],
        )
    if not snapshot.revision_workspace.context_current:
        return _blocked(
            snapshot,
            revision=revision,
            blockers=[
                _blocker(
                    "stale_content_context",
                    "Zmienił się kontekst treści",
                    "Plan, inventory, usługa, wiedza albo metryki nie odpowiadają rewizji.",
                    "Zrebasuj dokument na aktualny planning input.",
                )
            ],
        )
    planning = snapshot.planning_workspace
    if (
        planning is None
        or revision.planning_digest != planning.proposal.planning_digest
        or revision.planning_input_digest != planning.proposal.planning_input_digest
        or planning.proposal.service_card_id is None
    ):
        return _blocked(snapshot, revision=revision, blockers=[_planning_blocker()])
    planning_result = build_content_planning_input(
        snapshot,
        service_card_id=planning.proposal.service_card_id,
    )
    if (
        planning_result.planning_input is None
        or planning_result.blockers
        or planning_result.planning_input.planning_input_digest != revision.planning_input_digest
    ):
        blocker_codes = [item.code for item in planning_result.blockers]
        blocker = (
            _source_material_review_blocker(blocker_codes)
            if "wordpress_material_review_required" in blocker_codes
            else _planning_blocker(blocker_codes)
        )
        return _blocked(snapshot, revision=revision, blockers=[blocker])
    if not store.write_ready():
        return _blocked(snapshot, revision=revision, blockers=[_storage_blocker()])
    return _SemanticInputs(
        revision=revision,
        planning_input=planning_result.planning_input,
        proposal=planning.proposal,
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
        blocker = _blocker(
            "runtime_blocked",
            "Codex próbował wyjść poza review",
            "App-server zaobserwował próbę narzędzia albo zewnętrznego requestu.",
            "Odrzuć wynik i sprawdź izolację runtime; WILQ nic nie zapisał.",
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
        status: Literal["blocked", "failed"] = (
            "blocked" if result.status == "blocked" else "failed"
        )
        blocker = _blocker(
            code,
            "Codex nie zwrócił review semantycznego",
            "App-server nie zakończył advisory turnu poprawnym structured output.",
            "Sprawdź runtime i uruchom nową próbę; WILQ nic nie zapisał.",
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
        blocker = _blocker(
            "invalid_structured_output",
            "Codex zwrócił niepoprawne review",
            "Wynik nie ocenia dokładnie dziewięciu wymiarów kontraktu WILQ.",
            "Odrzuć wynik i rozpocznij nowy advisory turn.",
        )
        _finish_run(run_store, run, status="blocked", error=blocker.code)
        return _blocked(
            snapshot,
            revision=inputs.revision,
            blockers=[blocker],
            run=run,
            runtime=trace,
        )


def _apply_deterministic_quality_guards(
    inputs: _SemanticInputs,
    output: ContentSemanticReviewModelOutput,
) -> ContentSemanticReviewModelOutput:
    issues: list[tuple[str, str, str]] = []
    if inputs.proposal.cta_blocks and not inputs.revision.cta_blocks:
        issues.append(
            (
                "conversion_clarity",
                "cta_blocks",
                "Brakuje wymaganych bloków CTA z zatwierdzonego planu.",
            )
        )
    section_bodies = {
        str(section.section_id): section.body_markdown.strip().casefold()
        for section in inputs.revision.sections
    }
    issues.extend(
        regulatory_quality_issues(
            revision=inputs.revision,
            planning_input=inputs.planning_input,
            proposal=inputs.proposal,
        )
    )
    issues.extend(repetition_quality_issues(section_bodies))
    grouped: dict[str, tuple[list[str], str]] = {}
    for dimension, target, reason in issues:
        targets, previous_reason = grouped.get(dimension, ([], reason))
        if target not in targets:
            targets.append(target)
        grouped[dimension] = (targets, previous_reason)
    existing = {finding.dimension for finding in output.findings}
    dimensions = list(output.dimensions)
    findings = list(output.findings)
    for dimension, (targets, reason) in grouped.items():
        if dimension in existing:
            for index, finding in enumerate(findings):
                if finding.dimension == dimension:
                    findings[index] = finding.model_copy(
                        update={
                            "affected_targets": targets,
                            "reason": reason,
                            "instruction": "Popraw wskazany problem i uruchom review ponownie.",
                        }
                    )
                    break
            continue
        existing.add(dimension)
        for index, assessment in enumerate(dimensions):
            if assessment.dimension == dimension:
                dimensions[index] = assessment.model_copy(
                    update={
                        "status": "needs_changes",
                        "affected_targets": targets,
                        "reason": reason,
                    }
                )
                break
        findings.append(
            ContentSemanticFindingOutput(
                dimension=dimension,
                severity=(
                    "high"
                    if dimension in {"conversion_clarity", "search_intent_fit"}
                    else "medium"
                ),
                label="Automatyczna kontrola jakości",
                reason=reason,
                instruction="Popraw wskazany problem i uruchom review ponownie.",
                affected_targets=targets,
                evidence_ids=[],
            )
        )
    if not issues or len(findings) == len(output.findings):
        return output
    return output.model_copy(update={"dimensions": dimensions, "findings": findings})


def _scope_errors(
    revision: ContentDraftRevision,
    output: ContentSemanticReviewModelOutput,
) -> list[str]:
    allowed_targets = {
        "page_assets",
        "faq",
        "cta_blocks",
        "internal_links",
        "whole_document",
        *(str(item.section_id) for item in revision.sections),
    }
    allowed_evidence = set(_revision_evidence_ids(revision))
    errors: list[str] = []
    for dimension in output.dimensions:
        if not set(dimension.affected_targets).issubset(allowed_targets):
            errors.append(f"dimension_target:{dimension.dimension}")
    finding_dimensions = {item.dimension for item in output.findings}
    needs_change_dimensions = {
        item.dimension for item in output.dimensions if item.status == "needs_changes"
    }
    if finding_dimensions != needs_change_dimensions:
        errors.append("dimension_finding_consistency")
    for finding in output.findings:
        if not set(finding.affected_targets).issubset(allowed_targets):
            errors.append(f"finding_target:{finding.dimension}")
        if not set(finding.evidence_ids).issubset(allowed_evidence):
            errors.append(f"finding_evidence:{finding.dimension}")
    return list(dict.fromkeys(errors))


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
    status: Literal["reviewable", "needs_changes"] = (
        "needs_changes" if findings else "reviewable"
    )
    return ContentSemanticReview(
        review_id=review_id,
        work_item_id=inputs.revision.work_item_id,
        revision_id=inputs.revision.revision_id,
        revision_digest=inputs.revision.content_digest,
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
            or (
                queued.deadline_at is not None
                and utc_now() >= queued.deadline_at
            )
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
    blocker = _blocker(
        "runtime_failed",
        "Próba review wygasła przed uruchomieniem",
        "WILQ nie wskrzesił zakończonego albo przekroczonego deadline'u runu.",
        "Uruchom nową próbę review dla tej samej exact rewizji.",
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
    blocker = _blocker(
        "semantic_scope_mismatch",
        "Review wyszedł poza dokładną wersję",
        "Finding wskazuje obcy target, dowód albo niespójny wymiar.",
        "Odrzuć wynik i uruchom nowy advisory review dla bieżącej rewizji.",
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
    blocker = _blocker(
        "runtime_failed",
        "Przekroczono czas review semantycznego",
        "Exact deadline minął przed rozpoczęciem tury Codexa.",
        "Uruchom nową próbę review dla tej samej exact rewizji.",
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


def _finish_run(
    store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> CodexRun:
    terminal = run.model_copy(
        update={"status": status, "completed_at": utc_now(), "error": error}
    )
    if hasattr(store, "_connect"):
        return transition_codex_run_if_status(store, terminal) or run
    return store.save_codex_run(terminal)


def _trace(result: CodexAppServerTurnResult) -> ContentCodexRuntimeTrace:
    return ContentCodexRuntimeTrace(
        status=result.status,
        thread_id=result.thread_id,
        turn_id=result.turn_id,
        event_methods=list(result.event_methods),
        item_types=list(result.item_types),
        external_call_attempted=result.external_call_attempted,
    )


def _revision_evidence_ids(revision: ContentDraftRevision) -> list[str]:
    return list(
        dict.fromkeys(
            evidence_id
            for values in (
                *(item.evidence_ids for item in revision.sections),
                *(item.evidence_ids for item in revision.faq),
                *(item.evidence_ids for item in revision.cta_blocks),
                *(item.evidence_ids for item in revision.internal_links),
            )
            for evidence_id in values
        )
    )


def _review_response(
    status: Literal["ready", "idempotent"],
    revision: ContentDraftRevision,
    review: ContentSemanticReview,
) -> ContentSemanticReviewResponse:
    return ContentSemanticReviewResponse(
        status=status,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        review=review,
        run_id=review.codex_run_id,
        safe_next_step=review.safe_next_step,
    )


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
        run_id=None if run is None else run.id,
        runtime=runtime or ContentCodexRuntimeTrace(status="not_started"),
        blockers=blockers,
        safe_next_step=blockers[0].next_step,
    )


def _missing_revision_blocker() -> ContentSemanticReviewBlocker:
    return _blocker(
        "missing_revision",
        "Brakuje pełnej wersji do review",
        "Review semantyczne wymaga zapisanej exact revision.",
        "Najpierw wygeneruj pełny dokument.",
    )


def _planning_blocker(
    source_codes: Sequence[str] | None = None,
) -> ContentSemanticReviewBlocker:
    return _blocker(
        "missing_planning_input",
        "Brakuje aktualnego wejścia strategicznego",
        "Review musi porównać rewizję z tym samym planem, usługą, inventory i metrykami.",
        "Odśwież albo wygeneruj aktualny plan przed review semantycznym.",
        source_codes=source_codes,
    )


def _source_material_review_blocker(
    source_codes: Sequence[str],
) -> ContentSemanticReviewBlocker:
    return _blocker(
        "source_material_review_required",
        "Materiał źródłowy wymaga potwierdzenia",
        "Rewizja korzysta z publicznego materiału WordPress, którego pochodzenie "
        "nie zostało jeszcze zatwierdzone do pełnego dokumentu.",
        (
            "Zakończ kontrolowany import/redakcję i owner review materiału, "
            "potem uruchom review ponownie."
        ),
        source_codes=source_codes,
    )


def _storage_blocker() -> ContentSemanticReviewBlocker:
    return _blocker(
        "storage_activation_required",
        "Storage review czeka na maintenance window",
        "Realny local state nie ma jeszcze aktywowanej tabeli immutable semantic review.",
        "Użyj tymczasowego storage do proof albo zatwierdź backup i maintenance window.",
    )


def _blocker(
    code: str,
    label: str,
    reason: str,
    next_step: str,
    *,
    source_codes: Sequence[str] | None = None,
) -> ContentSemanticReviewBlocker:
    return ContentSemanticReviewBlocker(
        code=cast(ContentSemanticBlockerCode, code),
        label=label,
        reason=reason,
        next_step=next_step,
        source_codes=list(source_codes or []),
    )


__all__ = ["generate_content_semantic_review", "read_content_semantic_review"]
