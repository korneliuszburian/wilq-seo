from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
    ContentPlanningInputReadinessResponse,
    build_new_page_planning_input,
    content_planning_input_readiness,
    content_planning_input_summary,
)
from wilq.content.planning.generated_proposal import _run_planning_turn
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningModelOutput,
    ContentPlanningProposalBlocker,
    ContentPlanningProposalBlockerCode,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.workflow.target.new_page import (
    ContentNewPageBrief,
    ContentNewPageOverlapGuard,
    ContentNewPagePlanningFoundation,
    build_new_page_document_identity,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


class ContentNewPagePlanningProposalRequest(BaseModel):
    """A command tied to the ready input; it cannot select another service."""

    model_config = ConfigDict(extra="forbid")

    expected_planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_by: str = Field(min_length=1, max_length=160)
    operator_hint: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def require_visible_requester(self) -> ContentNewPagePlanningProposalRequest:
        self.requested_by = self.requested_by.strip()
        self.operator_hint = self.operator_hint.strip()
        if not self.requested_by:
            raise ValueError("Planning generation requires requester attribution.")
        return self


class ContentNewPagePlanningProposalWorkspace(BaseModel):
    """Read model for one brief's plan, never a refresh-workflow snapshot."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_new_page_planning_proposal_workspace"] = (
        "content_new_page_planning_proposal_workspace"
    )
    contract_version: Literal["content_new_page_planning_proposal_workspace_v1"] = (
        "content_new_page_planning_proposal_workspace_v1"
    )
    brief_id: str = Field(min_length=1)
    readiness: ContentPlanningInputReadinessResponse
    proposal_status: ContentPlanningProposalResponse | None = None

    @model_validator(mode="after")
    def require_one_exact_new_page_input(self) -> ContentNewPagePlanningProposalWorkspace:
        response = self.proposal_status
        if response is None:
            return self
        identity = self.readiness.new_page_document_identity
        if (
            self.readiness.status != "ready"
            or self.readiness.work_item_id is None
            or self.readiness.planning_input_digest is None
            or identity is None
            or self.brief_id != identity.brief_id
            or response.work_item_id != self.readiness.work_item_id
            or response.service_card_id != identity.service_card_id
            or response.planning_input_digest != self.readiness.planning_input_digest
        ):
            raise ValueError("New-page proposal workspace must keep one exact ready input.")
        proposal = response.proposal
        if proposal is not None:
            proposal_identity = proposal.new_page_document_identity
            if (
                proposal.goal != "new_page"
                or proposal.planning_input_digest != self.readiness.planning_input_digest
                or proposal_identity is None
                or proposal_identity != identity
            ):
                raise ValueError("New-page proposal must match the workspace document identity.")
        return self


def build_new_page_planning_proposal_workspace(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation | None,
    overlap_guard: ContentNewPageOverlapGuard,
    service_card: ContentKnowledgeCard | None,
    store: ContentPlanningProposalStore,
) -> ContentNewPagePlanningProposalWorkspace:
    result = build_new_page_planning_input(
        brief=brief,
        foundation=foundation,
        overlap_guard=overlap_guard,
        service_card=service_card,
    )
    readiness = content_planning_input_readiness(
        result,
        work_item_id=foundation.work_item_id if foundation is not None else None,
    )
    return ContentNewPagePlanningProposalWorkspace(
        brief_id=brief.brief_id,
        readiness=readiness,
        proposal_status=(
            _read_proposal(
                planning_input=result.planning_input,
                store=store,
            )
            if result.planning_input is not None
            else None
        ),
    )


def generate_new_page_planning_proposal(
    *,
    workspace: ContentNewPagePlanningProposalWorkspace,
    build_result: ContentPlanningInputBuildResult,
    request: ContentNewPagePlanningProposalRequest,
    client: CodexAppServerClientProtocol,
    store: ContentPlanningProposalStore,
    run_store: LocalStateStore,
    endpoint_path: str,
) -> ContentNewPagePlanningProposalWorkspace:
    """Run only after the workspace has rebuilt the exact current input."""

    if build_result.planning_input is None:
        return workspace
    planning_input = build_result.planning_input
    _require_workspace_matches_planning_input(workspace, planning_input)
    response = _generate_proposal(
        planning_input,
        request,
        client=client,
        store=store,
        run_store=run_store,
        endpoint_path=endpoint_path,
    )
    return _workspace_with_proposal_status(workspace, response)


def queue_new_page_planning_proposal(
    *,
    workspace: ContentNewPagePlanningProposalWorkspace,
    build_result: ContentPlanningInputBuildResult,
    request: ContentNewPagePlanningProposalRequest,
    store: ContentPlanningProposalStore,
) -> tuple[ContentNewPagePlanningProposalWorkspace, bool]:
    """Atomically queue at most one model turn for one exact new-page input."""

    if build_result.planning_input is None:
        return workspace, False
    planning_input = build_result.planning_input
    _require_workspace_matches_planning_input(workspace, planning_input)
    response, outcome = _queue_proposal(planning_input, request, store)
    return _workspace_with_proposal_status(workspace, response), outcome == "queued"


def _require_workspace_matches_planning_input(
    workspace: ContentNewPagePlanningProposalWorkspace,
    planning_input: ContentPlanningInput,
) -> None:
    """Reject a rebuilt input before it can claim a different brief workspace."""

    identity = workspace.readiness.new_page_document_identity
    if (
        planning_input.new_page_foundation is None
        or planning_input.proposed_ia_location is None
    ):
        raise ValueError("New-page planning input requires exact document identity.")
    expected_identity = build_new_page_document_identity(
        foundation=planning_input.new_page_foundation,
        proposed_ia_location=planning_input.proposed_ia_location,
    )
    if (
        workspace.readiness.status != "ready"
        or workspace.readiness.work_item_id != planning_input.work_item_id
        or workspace.readiness.planning_input_digest != planning_input.planning_input_digest
        or identity != expected_identity
        or workspace.brief_id != expected_identity.brief_id
    ):
        raise ValueError("New-page planning input must match the exact workspace readiness.")


def _workspace_with_proposal_status(
    workspace: ContentNewPagePlanningProposalWorkspace,
    response: ContentPlanningProposalResponse,
) -> ContentNewPagePlanningProposalWorkspace:
    """Revalidate derived workspaces; model_copy(update=...) skips validators."""

    return ContentNewPagePlanningProposalWorkspace.model_validate(
        workspace.model_dump(mode="python")
        | {"proposal_status": response.model_dump(mode="python")}
    )


def terminalize_new_page_planning_claim(
    response: ContentPlanningProposalResponse,
    store: ContentPlanningProposalStore,
    *,
    code: ContentPlanningProposalBlockerCode,
) -> None:
    """Release the exact queued claim when its worker cannot safely start Codex."""

    blocker = ContentPlanningProposalBlocker(
        code=code,
        label="Plan nowej strony nie został uruchomiony",
        reason="Bieżące wejście zmieniło się albo przestało być gotowe przed uruchomieniem.",
        next_step="Odśwież wejście i świadomie uruchom nowy plan.",
    )
    store.save_terminal_response(
        response.model_copy(
            update={
                "status": "stale" if code == "stale_input" else "blocked",
                "blockers": [blocker],
                "safe_next_step": blocker.next_step,
            }
        )
    )


def _read_proposal(
    *, planning_input: ContentPlanningInput, store: ContentPlanningProposalStore
) -> ContentPlanningProposalResponse:
    queued = store.queued_response(
        planning_input.work_item_id,
        planning_input.confirmed_service_card_id,
        planning_input.planning_input_digest,
    )
    if queued is not None:
        return queued
    proposal = store.for_input(
        planning_input.work_item_id,
        planning_input.confirmed_service_card_id,
        planning_input.planning_input_digest,
    )
    if proposal is None:
        return ContentPlanningProposalResponse(
            status="not_generated",
            work_item_id=planning_input.work_item_id,
            service_card_id=planning_input.confirmed_service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=content_planning_input_summary(planning_input),
            safe_next_step="Przygotuj pierwszy plan z dokładnego briefu i foundation.",
        )
    return ContentPlanningProposalResponse(
        status="ready",
        work_item_id=planning_input.work_item_id,
        service_card_id=planning_input.confirmed_service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        proposal=proposal,
        safe_next_step="Sprawdź strukturę i przygotuj pełny tekst z tej dokładnej wersji planu.",
    )


def _queue_proposal(
    planning_input: ContentPlanningInput,
    request: ContentNewPagePlanningProposalRequest,
    store: ContentPlanningProposalStore,
) -> tuple[ContentPlanningProposalResponse, str]:
    summary = content_planning_input_summary(planning_input)
    if request.expected_planning_input_digest != planning_input.planning_input_digest:
        return _stale_response(planning_input), "stale"
    existing = store.for_input(
        planning_input.work_item_id,
        planning_input.confirmed_service_card_id,
        planning_input.planning_input_digest,
    )
    if existing is not None:
        return ContentPlanningProposalResponse(
            status="idempotent",
            work_item_id=planning_input.work_item_id,
            service_card_id=planning_input.confirmed_service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=summary,
            proposal=existing,
            safe_next_step=(
                "Plan już istnieje dla tego exact wejścia; "
                "model nie został uruchomiony ponownie."
            ),
        ), "idempotent"
    queued = ContentPlanningProposalResponse(
        status="generating",
        work_item_id=planning_input.work_item_id,
        service_card_id=planning_input.confirmed_service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=summary,
        safe_next_step="Plan jest przygotowywany; odśwież ten widok po zakończeniu.",
    )
    return queued, store.enqueue(queued)


def _generate_proposal(
    planning_input: ContentPlanningInput,
    request: ContentNewPagePlanningProposalRequest,
    *,
    client: CodexAppServerClientProtocol,
    store: ContentPlanningProposalStore,
    run_store: LocalStateStore,
    endpoint_path: str,
) -> ContentPlanningProposalResponse:
    if request.expected_planning_input_digest != planning_input.planning_input_digest:
        return _stale_response(planning_input)
    existing = store.for_input(
        planning_input.work_item_id,
        planning_input.confirmed_service_card_id,
        planning_input.planning_input_digest,
    )
    if existing is not None:
        return _queue_proposal(planning_input, request, store)[0]
    run = run_store.save_codex_run(
        CodexRun(
            id=f"codex_content_planning_{uuid4().hex}",
            skill="wilq-content-operator",
            hook="content_planning_proposal",
            source="wilq_api",
            status="started",
            used_endpoints=[endpoint_path],
            evidence_ids=planning_input.evidence_ids,
            planning_input_digest=planning_input.planning_input_digest,
        )
    )
    output, trace, blocker, status = _run_planning_turn(
        planning_input=planning_input, operator_hint=request.operator_hint, client=client
    )
    if blocker is not None:
        if status is None:
            raise RuntimeError("Blocked planning turn returned no terminal status.")
        run_store.save_codex_run(
            run.model_copy(
                update={"status": status, "completed_at": utc_now(), "error": blocker.code}
            )
        )
        return ContentPlanningProposalResponse(
            status=status,
            work_item_id=planning_input.work_item_id,
            service_card_id=planning_input.confirmed_service_card_id,
            planning_input_digest=planning_input.planning_input_digest,
            input_summary=content_planning_input_summary(planning_input),
            runtime=(trace or ContentCodexRuntimeTrace(status=status)).model_copy(
                update={"run_id": run.id}
            ),
            blockers=[blocker],
            safe_next_step=blocker.next_step,
        )
    if output is None:
        raise RuntimeError("Completed planning turn returned no model output.")
    completed = run.model_copy(
        update={"status": "completed", "completed_at": utc_now(), "error": None}
    )
    proposal = _proposal_from_output(planning_input, output, completed)
    saved_status, saved = store.save_generated(proposal, completed)
    return ContentPlanningProposalResponse(
        status="created" if saved_status == "created" else "idempotent",
        work_item_id=planning_input.work_item_id,
        service_card_id=planning_input.confirmed_service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        proposal=saved,
        runtime=(trace or ContentCodexRuntimeTrace(status="completed")).model_copy(
            update={"run_id": run.id}
        ),
        safe_next_step="Sprawdź strukturę i przygotuj pełny tekst z tej dokładnej wersji planu.",
    )


def _stale_response(planning_input: ContentPlanningInput) -> ContentPlanningProposalResponse:
    blocker = ContentPlanningProposalBlocker(
        code="stale_input",
        label="Wejście planu zmieniło się",
        reason="Polecenie nie wskazuje bieżącego exact digestu wejścia.",
        next_step="Odśwież wejście i uruchom świadomie nową wersję planu.",
    )
    return ContentPlanningProposalResponse(
        status="stale",
        work_item_id=planning_input.work_item_id,
        service_card_id=planning_input.confirmed_service_card_id,
        planning_input_digest=planning_input.planning_input_digest,
        input_summary=content_planning_input_summary(planning_input),
        blockers=[blocker],
        safe_next_step=blocker.next_step,
    )


def _proposal_from_output(
    planning_input: ContentPlanningInput, output: ContentPlanningModelOutput, run: CodexRun
) -> ContentPlanningProposal:
    foundation = planning_input.new_page_foundation
    if foundation is None or planning_input.proposed_ia_location is None:
        raise ValueError("New-page proposal requires exact foundation and IA location.")
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
        goal="new_page",
        final_canonical_url=None,
        proposed_ia_location=planning_input.proposed_ia_location,
        new_page_document_identity=build_new_page_document_identity(
            foundation=foundation,
            proposed_ia_location=planning_input.proposed_ia_location,
        ),
        service_card_id=planning_input.confirmed_service_card_id,
        service_label=planning_input.service_label,
        service_selection_confirmed=True,
        target_reader=output.target_reader,
        buyer_problem=output.buyer_problem,
        buyer_trigger=output.buyer_trigger,
        search_intent=output.search_intent,
        angle=output.angle,
        value_proposition=output.value_proposition,
        cta_direction=output.cta_blocks[0].copy_direction,
        sections=[
            ContentPlanningSection(
                section_id=f"{proposal_id}_section_{index:02d}", **section.model_dump()
            )
            for index, section in enumerate(output.sections, start=1)
        ],
        inventory_mapping=[],
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
            {item for fact in planning_input.source_facts for item in fact.source_material_ids}
        ),
        knowledge_card_ids=planning_input.knowledge_card_ids,
        created_at=run.completed_at,
    )
    payload = proposal.model_dump(
        mode="json", exclude={"planning_digest", "proposal_version", "created_at"}
    )
    digest = sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return proposal.model_copy(update={"planning_digest": digest})


__all__ = [
    "ContentNewPagePlanningProposalRequest",
    "ContentNewPagePlanningProposalWorkspace",
    "build_new_page_planning_proposal_workspace",
    "generate_new_page_planning_proposal",
    "queue_new_page_planning_proposal",
    "terminalize_new_page_planning_claim",
]
