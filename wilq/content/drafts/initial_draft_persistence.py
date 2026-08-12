"""Atomic persistence owner for an assured initial content draft."""

from __future__ import annotations

from typing import Literal, Protocol

from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_assurance import ContentDraftAssuranceReceipt
from wilq.content.drafts.initial_draft_run import (
    finish_initial_draft_run,
    safe_initial_draft_run_error,
)
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
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionWriteResult,
)
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


class InitialDraftRevisionStore(Protocol):
    def append_draft_revision(
        self,
        command: ContentDraftRevisionAppendCommand,
        *,
        completed_codex_run: CodexRun | None = None,
    ) -> ContentDraftRevisionWriteResult: ...


def persist_initial_draft(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    base_revision_id: str | None,
    output: ContentInitialDraftModelOutput,
    run: CodexRun,
    trace: ContentCodexRuntimeTrace,
    workflow_store: InitialDraftRevisionStore,
    run_store: LocalStateStore,
    regulatory_assurance: ContentDraftAssuranceReceipt | None,
) -> ContentInitialDraftResponse:
    """Persist revision and completed run atomically, or return a typed blocker."""

    try:
        command = build_initial_draft_revision_command(
            snapshot=snapshot,
            request=request,
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            run=run,
            base_revision_id=base_revision_id,
            regulatory_assurance=regulatory_assurance,
        )
    except (ValueError, StopIteration):
        return _finish_failure(
            snapshot=snapshot,
            proposal=proposal,
            run=run,
            trace=trace,
            run_store=run_store,
            status="blocked",
            blocker=_blocker(
                "document_scope_mismatch",
                "Nie udało się złożyć bezpiecznego dokumentu",
                "Plan i pełny output nie tworzą poprawnej rewizji v2.",
                "Odrzuć wynik i popraw kontrakt wejścia przed ponowną próbą.",
            ),
        )
    result = _append_revision(
        command=command,
        snapshot=snapshot,
        proposal=proposal,
        run=run,
        trace=trace,
        workflow_store=workflow_store,
        run_store=run_store,
    )
    if isinstance(result, ContentInitialDraftResponse):
        return result
    if result.status == "conflict" or result.revision is None:
        return _finish_failure(
            snapshot=snapshot,
            proposal=proposal,
            run=run,
            trace=trace,
            run_store=run_store,
            status="conflict",
            blocker=_blocker(
                "revision_conflict",
                "Pierwsza wersja powstała równolegle",
                "WILQ nie nadpisze istniejącej rewizji wynikiem drugiego turnu.",
                "Odśwież workspace i otwórz już zapisaną wersję.",
            ),
        )
    return ContentInitialDraftResponse(
        status="created",
        work_item_id=planning_input.work_item_id,
        proposal_id=proposal.proposal_id,
        run_id=run.id,
        revision=result.revision,
        runtime=trace,
        safe_next_step="Przeczytaj pełną stronę i zapisz decyzję człowieka dla tej rewizji.",
    )


def _append_revision(
    *,
    command: ContentDraftRevisionAppendCommand,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    proposal: ContentPlanningProposal,
    run: CodexRun,
    trace: ContentCodexRuntimeTrace,
    workflow_store: InitialDraftRevisionStore,
    run_store: LocalStateStore,
) -> ContentDraftRevisionWriteResult | ContentInitialDraftResponse:
    completed_run = run.model_copy(
        update={"status": "completed", "completed_at": utc_now(), "error": None}
    )
    try:
        result = workflow_store.append_draft_revision(
            command,
            completed_codex_run=completed_run,
        )
    except ValueError as error:
        if str(error) != "stale_initial_draft_context":
            raise
        return _finish_failure(
            snapshot=snapshot,
            proposal=proposal,
            run=run,
            trace=trace,
            run_store=run_store,
            status="blocked",
            blocker=_blocker(
                "stale_initial_draft_context",
                "Kontekst szkicu zmienił się",
                "Bieżący package, adres lub powiązanie usługi zmieniły się przed zapisem.",
                "Odśwież kontekst i uruchom nową próbę.",
            ),
        )
    except Exception:
        return _finish_failure(
            snapshot=snapshot,
            proposal=proposal,
            run=run,
            trace=trace,
            run_store=run_store,
            status="failed",
            blocker=_blocker(
                "persistence_failed",
                "Nie zapisano pełnego tekstu",
                "Atomowy zapis dokumentu i zakończonego CodexRun nie powiódł się.",
                "Sprawdź prywatny store i uruchom nową próbę; częściowy tekst nie istnieje.",
            ),
        )
    return result


def _finish_failure(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    proposal: ContentPlanningProposal,
    run: CodexRun,
    trace: ContentCodexRuntimeTrace,
    run_store: LocalStateStore,
    status: Literal["blocked", "failed", "conflict"],
    blocker: ContentInitialDraftBlocker,
) -> ContentInitialDraftResponse:
    run_status: Literal["blocked", "failed"] = "failed" if status == "failed" else "blocked"
    finish_initial_draft_run(
        run_store,
        run,
        status=run_status,
        error=safe_initial_draft_run_error(blocker),
    )
    return ContentInitialDraftResponse(
        status=status,
        work_item_id=snapshot.preflight.item.id,
        proposal_id=proposal.proposal_id,
        run_id=run.id,
        runtime=trace,
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _blocker(
    code: ContentInitialDraftBlockerCode,
    label: str,
    reason: str,
    next_step: str,
) -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code=code,
        label=label,
        reason=reason,
        next_step=next_step,
    )


__all__ = ["InitialDraftRevisionStore", "persist_initial_draft"]
