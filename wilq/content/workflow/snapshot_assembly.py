from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from wilq.content.briefs.sales import ContentSalesBriefSeed
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.enrichment.opportunity import ContentOpportunityEnrichment
from wilq.content.handoff.revision_wordpress import (
    build_revision_bound_wordpress_draft_handoff,
)
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.inventory.records import ContentInventoryRecord
from wilq.content.knowledge.cards import ContentKnowledgeCardMatch
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.contracts import (
    ContentDraftRevisionWorkspace,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightResponse,
    ContentWorkItemSalesBriefResponse,
    ContentWorkItemStructuredDraftGenerationResponse,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.demand_evidence import build_content_search_demand_evidence
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.operator_steps import (
    ContentWorkflowOperatorBlocker,
    ContentWorkflowOperatorFacts,
    build_content_workflow_operator_journey,
)
from wilq.content.workflow.planning import (
    ContentPlanningDecision,
    build_content_planning_proposal,
    build_content_planning_workspace,
)
from wilq.content.workflow.queue import ContentWorkItemQueueCandidate
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionSection,
    ContentDraftRevisionState,
    content_draft_package_digest,
)
from wilq.schemas import ContentFreshnessAssessment, MetricFact


@dataclass(frozen=True)
class SnapshotAssemblyCallbacks:
    """Typed seams for each stage of the content workflow snapshot."""

    preflight: Callable[..., ContentWorkItemPreflightResponse]
    sales_brief: Callable[..., ContentWorkItemSalesBriefResponse]
    draft_package: Callable[..., ContentWorkItemDraftPackageResponse]
    structured_generation: Callable[..., ContentWorkItemStructuredDraftGenerationResponse]
    human_review: Callable[..., ContentWorkItemHumanReviewResponse]
    wordpress_handoff: Callable[..., ContentWorkItemWordPressDraftHandoffResponse]
    measurement_window: Callable[..., ContentWorkItemMeasurementWindowResponse]


def assemble_content_work_item_snapshot(
    *,
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    freshness_assessment: ContentFreshnessAssessment,
    candidate: ContentWorkItemQueueCandidate,
    knowledge_match: ContentKnowledgeCardMatch,
    service_profile_context: ContentWorkItemServiceProfileContext,
    measurement_window_id: str,
    callbacks: SnapshotAssemblyCallbacks,
    human_review_record: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
    revision_state: ContentDraftRevisionState | None = None,
    planning_decisions: list[ContentPlanningDecision] | None = None,
    demand_metric_facts: list[MetricFact] | None = None,
    demand_source_page: str | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Assemble the API-owned snapshot while keeping stage policy in callbacks."""
    preflight = callbacks.preflight(item, inventory_records)
    sales_brief = callbacks.sales_brief(
        item,
        inventory_records,
        claim_ledger,
        seed,
        enrichment,
        knowledge_match,
        measurement_window_id,
    )
    brief = sales_brief.sales_brief_result.brief
    draft_package = callbacks.draft_package(
        item,
        inventory_records,
        claim_ledger,
        seed,
        enrichment,
        knowledge_match,
        measurement_window_id,
        None if brief is None else brief.id,
        brief,
    )
    draft = draft_package.draft_package_result.draft_package
    planning_workspace = (
        None
        if brief is None or draft is None
        else build_content_planning_workspace(
            build_content_planning_proposal(
                brief=brief,
                draft=draft,
                service_profile=service_profile_context,
                search_demand=build_content_search_demand_evidence(
                    metric_facts=demand_metric_facts or [],
                    source_page=demand_source_page,
                    final_canonical_url=brief.final_canonical_url,
                    service_card_id=service_profile_context.service_card_id,
                    draft=draft,
                    freshness=freshness_assessment,
                ),
            ),
            planning_decisions or [],
        )
    )
    approved_planning_digest = (
        planning_workspace.proposal.planning_digest
        if planning_workspace is not None
        and planning_workspace.scope_current
        and planning_workspace.section_map_current
        else None
    )
    structured_generation = callbacks.structured_generation(
        item,
        claim_ledger,
        measurement_window_id,
        None if brief is None else brief.id,
        brief,
        draft,
    )
    revision_workspace = build_content_draft_revision_workspace(
        item=item,
        draft_package=draft,
        state=revision_state,
        structured_contract_present=(
            structured_generation.structured_generation_result.contract is not None
        ),
        planning_digest=approved_planning_digest,
    )
    human_review = callbacks.human_review(
        item,
        claim_ledger,
        measurement_window_id,
        None if brief is None else brief.id,
        draft,
        human_review_record,
    )
    if revision_state is not None and revision_state.revision_count > 0:
        wordpress_handoff = ContentWorkItemWordPressDraftHandoffResponse(
            item=item,
            handoff_result=build_revision_bound_wordpress_draft_handoff(
                item=item,
                draft_package=draft,
                revision_state=revision_state,
                planning_digest=approved_planning_digest,
            ),
        )
    else:
        wordpress_handoff = callbacks.wordpress_handoff(
            human_review.reviewed_item,
            draft,
            human_review.review,
            audit,
        )
    measurement_window = callbacks.measurement_window(
        item,
        claim_ledger,
        wordpress_handoff,
        measurement_window_id,
        None if brief is None else brief.id,
        draft,
        human_review,
    )
    sales_brief_blocker = sales_brief.sales_brief_result.blockers[0:1]
    section_map_blocker = draft_package.draft_package_result.blockers[0:1]
    structured_contract_blocker = structured_generation.structured_generation_result.blockers[0:1]
    signal_quality = None if brief is None else brief.signal_quality
    if (
        revision_workspace.latest_revision is None
        and planning_workspace is not None
        and not (
            planning_workspace.scope_current
            and planning_workspace.section_map_current
        )
    ):
        revision_workspace = revision_workspace.model_copy(
            update={
                "can_save": False,
                "safe_next_step": (
                    "Najpierw zatwierdź aktualny zakres i plan sekcji."
                ),
            }
        )
    journey = build_content_workflow_operator_journey(
        ContentWorkflowOperatorFacts(
            sales_brief_present=brief is not None,
            sales_brief_signal_status=(None if signal_quality is None else signal_quality.status),
            sales_brief_signal_reason=(None if signal_quality is None else signal_quality.reason),
            sales_brief_safe_next_step=(
                signal_quality.safe_next_step
                if signal_quality is not None
                else (
                    sales_brief_blocker[0].next_step
                    if sales_brief_blocker
                    else "Uzupełnij zakres, źródła i bezpieczny brief treści."
                )
            ),
            sales_brief_blocker=(
                None
                if not sales_brief_blocker
                else ContentWorkflowOperatorBlocker(
                    code=sales_brief_blocker[0].code,
                    label=sales_brief_blocker[0].label,
                    reason=sales_brief_blocker[0].reason,
                )
            ),
            section_map_present=draft is not None,
            section_map_blocker=(
                None
                if not section_map_blocker
                else ContentWorkflowOperatorBlocker(
                    code=section_map_blocker[0].code,
                    label=section_map_blocker[0].label,
                    reason=section_map_blocker[0].reason,
                )
            ),
            section_map_safe_next_step=(
                "Sprawdź kolejność sekcji, ich cele i przypisane dowody."
                if draft is not None
                else (
                    section_map_blocker[0].next_step
                    if section_map_blocker
                    else "Najpierw przygotuj bezpieczny plan sekcji."
                )
            ),
            structured_contract_present=(
                structured_generation.structured_generation_result.contract is not None
            ),
            structured_contract_blocker=(
                None
                if not structured_contract_blocker
                else ContentWorkflowOperatorBlocker(
                    code=structured_contract_blocker[0].code,
                    label=structured_contract_blocker[0].label,
                    reason=structured_contract_blocker[0].reason,
                )
            ),
            structured_contract_safe_next_step=(
                structured_contract_blocker[0].next_step
                if structured_contract_blocker
                else "Najpierw przygotuj kontrakt roboczego szkicu."
            ),
            revision_workspace_status=revision_workspace.status,
            revision_context_current=_revision_context_is_current(
                item=item,
                draft_package=draft,
                state=revision_state,
                planning_digest=approved_planning_digest,
            ),
            revision_bound_wordpress_handoff_ready=(
                wordpress_handoff.handoff_result.handoff is not None
                and wordpress_handoff.handoff_result.handoff.revision_binding is not None
            ),
            scope_review_current=bool(
                planning_workspace and planning_workspace.scope_current
            ),
            section_map_review_current=bool(
                planning_workspace and planning_workspace.section_map_current
            ),
        )
    )
    return ContentWorkItemWorkflowSnapshotResponse(
        freshness_assessment=freshness_assessment,
        candidate=candidate,
        service_profile_context=service_profile_context,
        claim_ledger=claim_ledger,
        preflight=preflight,
        sales_brief=sales_brief,
        draft_package=draft_package,
        structured_generation=structured_generation,
        human_review=human_review,
        wordpress_handoff=wordpress_handoff,
        measurement_window=measurement_window,
        revision_workspace=revision_workspace,
        planning_workspace=planning_workspace,
        current_step_id=journey.current_step_id,
        operator_steps=journey.steps,
    )


def build_content_draft_revision_workspace(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    state: ContentDraftRevisionState | None,
    structured_contract_present: bool,
    planning_digest: str | None,
) -> ContentDraftRevisionWorkspace:
    current_state = state or ContentDraftRevisionState(
        status="empty",
        revision_count=0,
    )
    latest_revision = current_state.latest_revision
    context_current = _revision_context_is_current(
        item=item,
        draft_package=draft_package,
        state=current_state,
        planning_digest=planning_digest,
    )
    if latest_revision is not None and (context_current or draft_package is None):
        editor_title = latest_revision.title
        editor_sections = latest_revision.sections
    elif draft_package is not None:
        editor_title = (
            draft_package.title if latest_revision is None else latest_revision.title
        )
        editor_sections = _revision_editor_sections(
            draft_package,
            latest_revision=latest_revision,
        )
    else:
        editor_title = item.wordpress_title_or_h1 or item.topic
        editor_sections = []

    status = current_state.status
    canonical_url = item.final_canonical_url or item.intended_final_url
    current_context_ready = bool(
        draft_package is not None and canonical_url and structured_contract_present
    )
    return ContentDraftRevisionWorkspace(
        status=status,
        latest_revision=latest_revision,
        latest_review=current_state.latest_review,
        revision_count=current_state.revision_count,
        context_current=context_current,
        editor_title=editor_title,
        editor_sections=editor_sections,
        can_save=bool(
            current_context_ready
            and (
                status in {"empty", "needs_changes", "rejected"}
                or not context_current
            )
        ),
        can_review=bool(
            latest_revision is not None
            and status in {"unreviewed", "deferred"}
            and current_context_ready
            and context_current
        ),
        safe_next_step=_revision_workspace_safe_next_step(
            status,
            structured_contract_present=structured_contract_present,
            context_current=context_current,
        ),
    )


def _revision_editor_sections(
    draft_package: ContentDraftPackage,
    *,
    latest_revision: ContentDraftRevision | None,
) -> list[ContentDraftRevisionSection]:
    prior_text_by_heading = (
        {}
        if latest_revision is None
        else {
            section.heading: section.body_markdown
            for section in latest_revision.sections
        }
    )
    return [
        ContentDraftRevisionSection(
            heading=section.heading,
            body_markdown=prior_text_by_heading.get(section.heading)
            or "\n\n".join(
                value
                for value in (
                    section.purpose,
                    *(f"- {note}" for note in section.draft_notes),
                )
                if value
            ),
            evidence_ids=section.evidence_ids,
        )
        for section in draft_package.sections
    ]


def _revision_context_is_current(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    state: ContentDraftRevisionState | None,
    planning_digest: str | None,
) -> bool:
    if state is None or state.latest_revision is None:
        return True
    canonical_url = item.final_canonical_url or item.intended_final_url
    revision = state.latest_revision
    return bool(
        draft_package is not None
        and canonical_url
        and revision.draft_package_id == draft_package.id
        and revision.draft_package_digest == content_draft_package_digest(draft_package)
        and revision.planning_digest is not None
        and revision.planning_digest == planning_digest
        and revision.final_canonical_url == canonical_url
    )


def _revision_workspace_safe_next_step(
    status: str,
    *,
    structured_contract_present: bool,
    context_current: bool,
) -> str:
    if not structured_contract_present:
        return "Najpierw odtwórz bezpieczny plan i kontrakt przygotowania szkicu."
    if not context_current:
        return (
            "Plan sekcji albo adres strony zmienił się. Zapisz nową wersję "
            "powiązaną z aktualnym planem przed sprawdzeniem."
        )
    next_steps = {
        "empty": "Uzupełnij tekst i zapisz pierwszą wersję do sprawdzenia.",
        "unreviewed": "Sprawdź dokładną zapisaną wersję i zapisz decyzję człowieka.",
        "needs_changes": "Wprowadź wskazane poprawki i zapisz kolejną wersję.",
        "approved": (
            "Nie zapisuj jeszcze do WordPress; brakuje powiązania tej wersji "
            "z bezpiecznym podglądem draft-only."
        ),
        "rejected": "Nie przekazuj tej wersji dalej; przygotuj i zapisz nową wersję.",
        "deferred": (
            "Wróć do tej samej wersji i zapisz decyzję, gdy sprawdzenie będzie możliwe."
        ),
    }
    return next_steps[status]
