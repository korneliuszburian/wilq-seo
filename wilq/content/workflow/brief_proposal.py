"""Reviewable brief proposal with per-field provenance and one routing branch."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.intake import ContentIntakeQueueItem
from wilq.content.workflow.request_workflow import ContentRequestWorkflowState
from wilq.content.workflow.research_read import ContentResearchReadResponse

BriefProvenance = Literal["user_input", "evidence", "inference", "unknown"]
BriefRoute = Literal["existing_page", "new_page", "ambiguous"]
WORKFLOW_OWNER = "WILQ content workflow"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentBriefField(_FrozenModel):
    field: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=2000)
    provenance: BriefProvenance
    detail: str = Field(min_length=1, max_length=600)
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_sorted_evidence(self) -> Self:
        if self.evidence_ids != tuple(sorted(set(self.evidence_ids))):
            raise ValueError("Brief field evidence IDs must be sorted and unique.")
        return self


class ContentBriefBlocker(_FrozenModel):
    code: str = Field(min_length=1, max_length=160)
    owner: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=600)


class ContentBriefProposal(_FrozenModel):
    schema_version: Literal["wilq_content_brief_proposal_v1"] = (
        "wilq_content_brief_proposal_v1"
    )
    queue_id: str = Field(min_length=1, max_length=240)
    status: Literal["ready", "blocked"]
    route: BriefRoute | None = None
    target_work_item_id: str | None = Field(default=None, max_length=240)
    target_path: str | None = Field(default=None, max_length=2048)
    target_public_url: str | None = Field(default=None, max_length=2048)
    fields: tuple[ContentBriefField, ...] = Field(min_length=1)
    blockers: tuple[ContentBriefBlocker, ...] = ()
    workflow_step: str = Field(min_length=1)
    research_status: str | None = None
    planning_proposal_created: Literal[False] = False
    action_created: Literal[False] = False
    generation_allowed: Literal[False] = False
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_exact_brief_shape(self) -> Self:
        if self.status == "ready" and (self.route is None or self.blockers):
            raise ValueError("A ready brief needs one route and no blockers.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("A blocked brief needs at least one typed blocker.")
        if len({field.field for field in self.fields}) != len(self.fields):
            raise ValueError("Brief fields must be unique.")
        if len({blocker.code for blocker in self.blockers}) != len(self.blockers):
            raise ValueError("Brief blockers must be unique.")
        if self.route == "existing_page" and (
            not self.target_work_item_id or not self.target_path
        ):
            raise ValueError("The existing-page route needs its exact target.")
        return self


def build_content_brief_proposal(
    *,
    queue_item: ContentIntakeQueueItem,
    workflow: ContentRequestWorkflowState,
    research_read: ContentResearchReadResponse | None,
) -> ContentBriefProposal:
    """Build one reviewable brief, marking missing data unknown instead of inventing it."""

    candidates = queue_item.candidate_work_item_ids
    if len(candidates) > 1:
        return _blocked_brief(
            queue_item,
            workflow,
            research_read,
            route="ambiguous",
            code="brief_route_ambiguous",
            owner=WORKFLOW_OWNER,
            detail="Prośba pasuje do wielu stron; brief nie wybiera gałęzi sam.",
            safe_next_step="Wskaż dokładnie jedną istniejącą stronę albo zgłoś nową.",
        )
    if not candidates:
        return _blocked_brief(
            queue_item,
            workflow,
            research_read,
            route="new_page",
            code="new_topic_discovery_source_unavailable",
            owner="Wilku",
            detail=(
                "Brak istniejącej strony i brak zatwierdzonego źródła discovery dla nowego "
                "tematu; nie tworzę popytu ani konkurencji z domysłów."
            ),
            safe_next_step=(
                "Zdecyduj źródło discovery dla nowego tematu albo wskaż istniejącą stronę."
            ),
        )
    work_item_id = candidates[0]
    if workflow.current_step not in {"brief_ready"}:
        blocker = workflow.blocker_code or "brief_workflow_not_ready"
        owner = workflow.blocker_owner or _pending_gate_owner(workflow) or WORKFLOW_OWNER
        return _blocked_brief(
            queue_item,
            workflow,
            research_read,
            route="existing_page",
            code=blocker,
            owner=owner,
            detail="Request-owned workflow nie jest gotowy na brief.",
            safe_next_step=workflow.safe_next_step,
        )
    if research_read is None or research_read.status != "ready":
        if research_read is None:
            code = "brief_research_not_ready"
        elif research_read.blockers:
            code = research_read.blockers[0].code
        else:
            code = "brief_research_not_ready"
        owner = (
            WORKFLOW_OWNER
            if research_read is None or not research_read.blockers
            else research_read.blockers[0].owner
        )
        return _blocked_brief(
            queue_item,
            workflow,
            research_read,
            route="existing_page",
            code=code,
            owner=owner,
            detail="Brak zatwierdzonych, bieżących źródeł dla tej strony.",
            safe_next_step=(
                research_read.safe_next_step
                if research_read is not None
                else "Odczytaj ponownie exact źródła tej strony."
            ),
        )
    target_path = research_read.canonical_path or queue_item.candidate_paths[0]
    target_url = research_read.page_url or queue_item.candidate_public_urls[0]
    return ContentBriefProposal(
        queue_id=queue_item.queue_id,
        status="ready",
        route="existing_page",
        target_work_item_id=work_item_id,
        target_path=target_path,
        target_public_url=target_url,
        fields=_brief_fields(
            queue_item,
            research_read,
            route="existing_page",
            target_value=target_path,
            target_lineage=_target_lineage(queue_item),
        ),
        workflow_step=workflow.current_step,
        research_status=research_read.status,
        safe_next_step=(
            "Otwórz existing-page workflow z tym briefem; bez planu i generacji w tym kroku."
        ),
    )


def _blocked_brief(
    queue_item: ContentIntakeQueueItem,
    workflow: ContentRequestWorkflowState,
    research_read: ContentResearchReadResponse | None,
    *,
    route: BriefRoute,
    code: str,
    owner: str,
    detail: str,
    safe_next_step: str,
) -> ContentBriefProposal:
    return ContentBriefProposal(
        queue_id=queue_item.queue_id,
        status="blocked",
        route=route,
        target_work_item_id=(
            queue_item.candidate_work_item_ids[0]
            if route == "existing_page" and queue_item.candidate_work_item_ids
            else None
        ),
        target_path=(
            queue_item.candidate_paths[0]
            if route == "existing_page" and queue_item.candidate_paths
            else None
        ),
        target_public_url=(
            queue_item.candidate_public_urls[0]
            if route == "existing_page" and queue_item.candidate_public_urls
            else None
        ),
        fields=_brief_fields(
            queue_item,
            research_read,
            route=route,
            target_value=(
                queue_item.candidate_paths[0]
                if route == "existing_page" and queue_item.candidate_paths
                else None
            ),
            target_lineage=_target_lineage(queue_item),
        ),
        blockers=(ContentBriefBlocker(code=code, owner=owner, detail=detail),),
        workflow_step=workflow.current_step,
        research_status=None if research_read is None else research_read.status,
        safe_next_step=safe_next_step,
    )


def _target_lineage(queue_item: ContentIntakeQueueItem) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                value
                for entry in queue_item.provenance
                if entry.field == "target_path"
                for value in entry.evidence_ids
            }
        )
    )


def _brief_fields(
    queue_item: ContentIntakeQueueItem,
    research_read: ContentResearchReadResponse | None,
    *,
    route: BriefRoute,
    target_value: str | None,
    target_lineage: tuple[str, ...],
) -> tuple[ContentBriefField, ...]:
    target_evidence = (
        target_lineage if route == "existing_page" else ()
    )
    resolved_target = (
        target_value
        if target_value
        else ("unknown" if not target_evidence else target_value)
    )
    resolved_target = resolved_target or "unknown"
    facts = () if research_read is None else research_read.facts
    fact_evidence = tuple(
        sorted({value for fact in facts for value in fact.evidence_ids})
    )
    return (
        ContentBriefField(
            field="topic",
            value=queue_item.ask,
            provenance="user_input",
            detail="Dosłowna prośba operatora; bez dopisywania wymagań.",
        ),
        ContentBriefField(
            field="target",
            value=resolved_target,
            provenance="evidence" if target_evidence else "unknown",
            detail=(
                "Dopasowanie z bieżącego katalogu WILQ."
                if target_evidence
                else "Brak zatwierdzonego adresu docelowego; nie tworzę go z domysłu."
            ),
            evidence_ids=target_evidence,
        ),
        ContentBriefField(
            field="content_kind",
            value="unknown",
            provenance="unknown",
            detail="Typ treści nie jest jeszcze zatwierdzony dla tego briefu.",
        ),
        ContentBriefField(
            field="audience",
            value="unknown",
            provenance="unknown",
            detail="Brak zweryfikowanego odbiorcy; brief nie zgaduje grupy docelowej.",
        ),
        ContentBriefField(
            field="cta",
            value="unknown",
            provenance="unknown",
            detail="Brak zweryfikowanego CTA; brief nie zgaduje wezwania do działania.",
        ),
        ContentBriefField(
            field="demand",
            value="unknown",
            provenance="unknown",
            detail=_claim_detail(
                research_read,
                "demand",
                "Brak świeżych danych popytu; brief nie tworzy claimu popytowego.",
                "Brak zatwierdzonej wartości popytu w tym briefie.",
            ),
        ),
        ContentBriefField(
            field="competition",
            value="unknown",
            provenance="unknown",
            detail=_claim_detail(
                research_read,
                "competitor",
                "Brak świeżych danych konkurencji; brief nie tworzy claimu konkurencyjnego.",
                "Brak zatwierdzonej wartości konkurencji w tym briefie.",
            ),
        ),
        ContentBriefField(
            field="source_facts",
            value=str(len(facts)),
            provenance="evidence" if facts else "unknown",
            detail=(
                "Zatwierdzone fakty źródłowe z Q2 research read."
                if facts
                else "Brak zatwierdzonych faktów źródłowych dla tego briefu."
            ),
            evidence_ids=fact_evidence,
        ),
    )


def _claim_detail(
    research_read: ContentResearchReadResponse | None,
    claim: Literal["demand", "competitor"],
    stale_detail: str,
    unresolved_detail: str,
) -> str:
    if research_read is not None and any(
        gate.claim == claim for gate in research_read.claim_gates
    ):
        return stale_detail
    return unresolved_detail


def _pending_gate_owner(workflow: ContentRequestWorkflowState) -> str | None:
    for gate in workflow.gates:
        if gate.status in {"pending", "stale"}:
            return gate.owner
    return None


__all__ = [
    "BriefProvenance",
    "BriefRoute",
    "ContentBriefBlocker",
    "ContentBriefField",
    "ContentBriefProposal",
    "build_content_brief_proposal",
]
