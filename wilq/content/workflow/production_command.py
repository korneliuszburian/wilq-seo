"""One idempotent command over preparation, generation, and revision state."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexSectionProposalResponse,
    ContentRevisionRepairProposalRequest,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionState,
)


class ContentProductionInitialCommand(ContentInitialDraftRequest):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["initial"] = "initial"


class ContentProductionRepairCommand(ContentRevisionRepairProposalRequest):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["repair"] = "repair"


ContentProductionCommandRequest = Annotated[
    ContentProductionInitialCommand | ContentProductionRepairCommand,
    Field(discriminator="operation"),
]


class ContentProductionCommandBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=160)
    label: str = Field(min_length=1, max_length=240)
    reason: str = Field(min_length=1, max_length=600)
    next_step: str = Field(min_length=1, max_length=600)


class ContentProductionCommandResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["blocked", "generating", "created", "reused", "idempotent"]
    operation: Literal["initial", "repair"]
    work_item_id: str = Field(min_length=1, max_length=240)
    revision: ContentDraftRevision | None = None
    run_id: str | None = None
    blockers: list[ContentProductionCommandBlocker] = Field(default_factory=list)
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_status_shape(self) -> ContentProductionCommandResponse:
        if self.status == "reused":
            if self.revision is None or self.run_id is not None or self.blockers:
                raise ValueError("Reused production command requires only a revision.")
        elif self.status in {"created", "idempotent"}:
            if self.revision is None or self.blockers:
                raise ValueError("Successful production command requires a revision.")
        elif self.status == "generating":
            if self.revision is not None or not self.blockers:
                raise ValueError("Generating production command requires a blocker only.")
        elif self.revision is not None or not self.blockers:
            raise ValueError("Blocked production command requires blockers only.")
        return self


class ContentProductionCommandJournal(Protocol):
    def load_draft_revision_state(self, work_item_id: str) -> ContentDraftRevisionState: ...


InitialCommandExecutor = Callable[
    [str, ContentInitialDraftRequest], ContentInitialDraftResponse
]
RepairCommandExecutor = Callable[
    [str, ContentRevisionRepairProposalRequest], ContentCodexSectionProposalResponse
]


class ContentProductionCommand:
    """Guard one production attempt using the current revision journal first."""

    def __init__(
        self,
        *,
        journal: ContentProductionCommandJournal,
        initial_executor: InitialCommandExecutor,
        repair_executor: RepairCommandExecutor,
    ) -> None:
        self._journal = journal
        self._initial_executor = initial_executor
        self._repair_executor = repair_executor

    def run(
        self,
        work_item_id: str,
        request: ContentProductionInitialCommand | ContentProductionRepairCommand,
    ) -> ContentProductionCommandResponse:
        state = self._journal.load_draft_revision_state(work_item_id)
        if request.operation == "initial":
            return self._run_initial(work_item_id, request, state)
        return self._run_repair(work_item_id, request, state)

    def _run_initial(
        self,
        work_item_id: str,
        request: ContentProductionInitialCommand,
        state: ContentDraftRevisionState,
    ) -> ContentProductionCommandResponse:
        revision = state.latest_revision
        review = state.latest_review
        if revision is not None:
            if not _initial_request_matches_revision(request, revision):
                return _blocked(
                    work_item_id,
                    "initial",
                    "initial_context_mismatch",
                    "Żądanie nie wskazuje bieżącego kontekstu rewizji",
                    "Reuse wymaga zgodnych planning i refresh-preparation digestów exact rewizji.",
                    "Odśwież bieżący workspace i użyj aktualnych digestów.",
                )
            if review is not None and review.decision == "approved":
                return _reuse(work_item_id, revision)
            if review is not None and review.decision == "needs_changes":
                return _blocked(
                    work_item_id,
                    "initial",
                    "revision_needs_changes",
                    "Rewizja czeka na child repair",
                    "Bieżąca rewizja ma decyzję needs_changes; nie wolno tworzyć "
                    "drugiego root draftu.",
                    "Uruchom operation=repair z exact base_revision_id i jednym komponentem.",
                )
            return _blocked(
                work_item_id,
                "initial",
                "revision_already_exists",
                "Bieżąca rewizja już istnieje",
                "Najpierw wykonaj review albo pracuj na zapisanej rewizji zamiast "
                "generować drugi root.",
                "Odczytaj bieżącą rewizję i przejdź do właściwej decyzji review.",
            )
        return _from_initial(work_item_id, self._initial_executor(work_item_id, request))

    def _run_repair(
        self,
        work_item_id: str,
        request: ContentProductionRepairCommand,
        state: ContentDraftRevisionState,
    ) -> ContentProductionCommandResponse:
        revision = state.latest_revision
        review = state.latest_review
        if revision is None:
            return _blocked(
                work_item_id,
                "repair",
                "repair_requires_revision",
                "Brakuje rewizji bazowej",
                "Child repair wymaga dokładnej zapisanej rewizji i jej review.",
                "Najpierw przeprowadź operation=initial po przejściu prepare/authorize/plan.",
            )
        if review is None or review.decision != "needs_changes":
            return _blocked(
                work_item_id,
                "repair",
                "repair_requires_needs_changes",
                "Rewizja nie czeka na poprawkę",
                "Child może powstać tylko z bieżącej rewizji oznaczonej needs_changes.",
                "Zapisz exact human review needs_changes albo użyj operation=initial.",
            )
        if (
            request.expected_base_digest != revision.content_digest
            or request.expected_base_digest != review.revision_digest
        ):
            return _blocked(
                work_item_id,
                "repair",
                "repair_base_digest_mismatch",
                "Digest rewizji bazowej się nie zgadza",
                "Żądanie wskazuje inną rewizję niż bieżący needs_changes review.",
                "Odśwież journal i użyj exact revision digestu.",
            )
        return _from_repair(
            work_item_id,
            self._repair_executor(work_item_id, request),
        )


def _reuse(work_item_id: str, revision: ContentDraftRevision) -> ContentProductionCommandResponse:
    return ContentProductionCommandResponse(
        status="reused",
        operation="initial",
        work_item_id=work_item_id,
        revision=revision,
        safe_next_step="Otwórz dokładną zatwierdzoną rewizję; nie uruchamiaj nowej generacji.",
    )


def _initial_request_matches_revision(
    request: ContentProductionInitialCommand,
    revision: ContentDraftRevision,
) -> bool:
    if (
        revision.planning_digest is None
        or revision.planning_input_digest is None
        or request.expected_planning_digest != revision.planning_digest
        or request.expected_planning_input_digest != revision.planning_input_digest
    ):
        return False
    binding = revision.refresh_preparation_binding
    if binding is None:
        return (
            request.refresh_preparation_authorization_id is None
            and request.expected_refresh_preparation_authorization_digest is None
        )
    return (
        request.refresh_preparation_authorization_id == binding.authorization_id
        and request.expected_refresh_preparation_authorization_digest
        == binding.authorization_digest
    )


def _from_initial(
    work_item_id: str,
    response: ContentInitialDraftResponse,
) -> ContentProductionCommandResponse:
    if response.status == "reused":
        return _reuse(work_item_id, response.revision)  # type: ignore[arg-type]
    if response.status == "created":
        return ContentProductionCommandResponse(
            status="created",
            operation="initial",
            work_item_id=work_item_id,
            revision=response.revision,
            run_id=response.run_id,
            blockers=[
                _copy_blocker(item.code, item.label, item.reason, item.next_step)
                for item in response.blockers
            ],
            safe_next_step=response.safe_next_step,
        )
    if response.status == "generating":
        return ContentProductionCommandResponse(
            status="generating",
            operation="initial",
            work_item_id=work_item_id,
            run_id=response.run_id,
            blockers=[
                _copy_blocker(item.code, item.label, item.reason, item.next_step)
                for item in response.blockers
            ],
            safe_next_step=response.safe_next_step,
        )
    return _blocked_from_items(work_item_id, "initial", response.blockers, response.safe_next_step)


def _from_repair(
    work_item_id: str,
    response: ContentCodexSectionProposalResponse,
) -> ContentProductionCommandResponse:
    if response.status == "created":
        return ContentProductionCommandResponse(
            status="created",
            operation="repair",
            work_item_id=work_item_id,
            revision=response.revision,
            run_id=response.run_id,
            safe_next_step=response.safe_next_step,
        )
    if response.status == "idempotent":
        return ContentProductionCommandResponse(
            status="idempotent",
            operation="repair",
            work_item_id=work_item_id,
            revision=response.revision,
            run_id=response.run_id,
            safe_next_step=response.safe_next_step,
        )
    return _blocked_from_items(work_item_id, "repair", response.blockers, response.safe_next_step)


def _blocked_from_items(
    work_item_id: str,
    operation: Literal["initial", "repair"],
    items: Sequence[object],
    safe_next_step: str,
) -> ContentProductionCommandResponse:
    blockers = [
        _copy_blocker(
            getattr(item, "code", "production_command_blocked"),
            getattr(item, "label", "Komenda produkcyjna zablokowana"),
            getattr(item, "reason", "Istnieje blocker bieżącego workflow."),
            getattr(item, "next_step", safe_next_step),
        )
        for item in items
    ]
    if not blockers:
        blockers = [
            _copy_blocker(
                "production_command_blocked",
                "Komenda produkcyjna zablokowana",
                "Bieżący workflow nie zwrócił bezpiecznego wyniku.",
                safe_next_step,
            )
        ]
    return ContentProductionCommandResponse(
        status="blocked",
        operation=operation,
        work_item_id=work_item_id,
        blockers=blockers,
        safe_next_step=safe_next_step,
    )


def _copy_blocker(
    code: object,
    label: object,
    reason: object,
    next_step: object,
) -> ContentProductionCommandBlocker:
    return ContentProductionCommandBlocker(
        code=str(code),
        label=str(label),
        reason=str(reason),
        next_step=str(next_step),
    )


def _blocked(
    work_item_id: str,
    operation: Literal["initial", "repair"],
    code: str,
    label: str,
    reason: str,
    next_step: str,
) -> ContentProductionCommandResponse:
    return ContentProductionCommandResponse(
        status="blocked",
        operation=operation,
        work_item_id=work_item_id,
        blockers=[_copy_blocker(code, label, reason, next_step)],
        safe_next_step=next_step,
    )


__all__ = [
    "ContentProductionCommand",
    "ContentProductionCommandBlocker",
    "ContentProductionCommandRequest",
    "ContentProductionCommandResponse",
    "ContentProductionInitialCommand",
    "ContentProductionRepairCommand",
]
