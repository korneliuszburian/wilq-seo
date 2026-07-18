from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from wilq.content.briefs.sales import ContentSalesBrief, ContentSalesBriefSeed
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
from wilq.content.planning.dynamic_input import (
    build_content_planning_input_from_components,
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
    ContentWorkflowOperatorJourney,
    build_content_workflow_operator_journey,
)
from wilq.content.workflow.planning import (
    ContentPlanningDecision,
    ContentPlanningProposal,
    ContentPlanningWorkspace,
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


@dataclass(frozen=True)
class _SnapshotFoundation:
    preflight: ContentWorkItemPreflightResponse
    sales_brief: ContentWorkItemSalesBriefResponse
    draft_package: ContentWorkItemDraftPackageResponse
    planning_workspace: ContentPlanningWorkspace | None
    approved_planning_digest: str | None


@dataclass(frozen=True)
class _SnapshotDelivery:
    structured_generation: ContentWorkItemStructuredDraftGenerationResponse
    revision_workspace: ContentDraftRevisionWorkspace
    human_review: ContentWorkItemHumanReviewResponse
    wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponse
    measurement_window: ContentWorkItemMeasurementWindowResponse


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
    generated_planning_proposal: ContentPlanningProposal | None = None,
    demand_metric_facts: list[MetricFact] | None = None,
    demand_source_page: str | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Assemble the API-owned snapshot while keeping stage policy in callbacks."""
    foundation = _assemble_foundation(
        item=item,
        inventory_records=inventory_records,
        claim_ledger=claim_ledger,
        seed=seed,
        enrichment=enrichment,
        freshness_assessment=freshness_assessment,
        knowledge_match=knowledge_match,
        service_profile_context=service_profile_context,
        measurement_window_id=measurement_window_id,
        callbacks=callbacks,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
        demand_metric_facts=demand_metric_facts,
        demand_source_page=demand_source_page,
    )
    delivery = _assemble_delivery(
        item=item,
        claim_ledger=claim_ledger,
        measurement_window_id=measurement_window_id,
        callbacks=callbacks,
        foundation=foundation,
        human_review_record=human_review_record,
        audit=audit,
        revision_state=revision_state,
    )
    journey = _operator_journey(
        item=item,
        foundation=foundation,
        delivery=delivery,
        revision_state=revision_state,
    )
    return ContentWorkItemWorkflowSnapshotResponse(
        freshness_assessment=freshness_assessment,
        candidate=candidate,
        service_profile_context=service_profile_context,
        claim_ledger=claim_ledger,
        preflight=foundation.preflight,
        sales_brief=foundation.sales_brief,
        draft_package=foundation.draft_package,
        structured_generation=delivery.structured_generation,
        human_review=delivery.human_review,
        wordpress_handoff=delivery.wordpress_handoff,
        measurement_window=delivery.measurement_window,
        revision_workspace=delivery.revision_workspace,
        planning_workspace=foundation.planning_workspace,
        current_step_id=journey.current_step_id,
        operator_steps=journey.steps,
    )


def _assemble_foundation(
    *,
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    freshness_assessment: ContentFreshnessAssessment,
    knowledge_match: ContentKnowledgeCardMatch,
    service_profile_context: ContentWorkItemServiceProfileContext,
    measurement_window_id: str,
    callbacks: SnapshotAssemblyCallbacks,
    planning_decisions: list[ContentPlanningDecision] | None,
    generated_planning_proposal: ContentPlanningProposal | None,
    demand_metric_facts: list[MetricFact] | None,
    demand_source_page: str | None,
) -> _SnapshotFoundation:
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
    baseline = _baseline_planning_proposal(
        brief=brief,
        draft=draft,
        service_profile_context=service_profile_context,
        freshness_assessment=freshness_assessment,
        demand_metric_facts=demand_metric_facts,
        demand_source_page=demand_source_page,
    )
    current = _current_planning_proposal(
        item=item,
        service_profile_context=service_profile_context,
        preflight=preflight,
        brief=brief,
        draft=draft,
        baseline=baseline,
        freshness=freshness_assessment,
        claim_ledger=claim_ledger,
        generated=generated_planning_proposal,
    )
    planning_workspace = (
        None
        if current is None
        else build_content_planning_workspace(current, planning_decisions or [])
    )
    approved_digest = (
        planning_workspace.proposal.planning_digest
        if planning_workspace is not None
        and planning_workspace.scope_current
        and planning_workspace.section_map_current
        else None
    )
    return _SnapshotFoundation(
        preflight=preflight,
        sales_brief=sales_brief,
        draft_package=draft_package,
        planning_workspace=planning_workspace,
        approved_planning_digest=approved_digest,
    )


def _baseline_planning_proposal(
    *,
    brief: ContentSalesBrief | None,
    draft: ContentDraftPackage | None,
    service_profile_context: ContentWorkItemServiceProfileContext,
    freshness_assessment: ContentFreshnessAssessment,
    demand_metric_facts: list[MetricFact] | None,
    demand_source_page: str | None,
) -> ContentPlanningProposal | None:
    if brief is None or draft is None:
        return None
    demand = build_content_search_demand_evidence(
        metric_facts=demand_metric_facts or [],
        source_page=demand_source_page,
        final_canonical_url=brief.final_canonical_url,
        service_card_id=service_profile_context.service_card_id,
        draft=draft,
        freshness=freshness_assessment,
    )
    return build_content_planning_proposal(
        brief=brief,
        draft=draft,
        service_profile=service_profile_context,
        search_demand=demand,
    )


def _assemble_delivery(
    *,
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    callbacks: SnapshotAssemblyCallbacks,
    foundation: _SnapshotFoundation,
    human_review_record: ContentHumanReview | None,
    audit: ContentWordPressDraftAuditEnvelope | None,
    revision_state: ContentDraftRevisionState | None,
) -> _SnapshotDelivery:
    brief = foundation.sales_brief.sales_brief_result.brief
    draft = foundation.draft_package.draft_package_result.draft_package
    structured = callbacks.structured_generation(
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
        structured_contract_present=(structured.structured_generation_result.contract is not None),
        planning_digest=foundation.approved_planning_digest,
        planning_input_digest=(
            None
            if foundation.planning_workspace is None
            else foundation.planning_workspace.proposal.planning_input_digest
        ),
        service_card_id=(
            None
            if foundation.planning_workspace is None
            else foundation.planning_workspace.proposal.service_card_id
        ),
    )
    revision_workspace = _gate_revision_workspace(
        revision_workspace,
        foundation.planning_workspace,
    )
    human_review = callbacks.human_review(
        item,
        claim_ledger,
        measurement_window_id,
        None if brief is None else brief.id,
        draft,
        human_review_record,
    )
    wordpress_handoff = _wordpress_handoff(
        item=item,
        draft=draft,
        planning_digest=foundation.approved_planning_digest,
        planning_input_digest=(
            None
            if foundation.planning_workspace is None
            else foundation.planning_workspace.proposal.planning_input_digest
        ),
        service_card_id=(
            None
            if foundation.planning_workspace is None
            else foundation.planning_workspace.proposal.service_card_id
        ),
        human_review=human_review,
        audit=audit,
        revision_state=revision_state,
        callbacks=callbacks,
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
    return _SnapshotDelivery(
        structured_generation=structured,
        revision_workspace=revision_workspace,
        human_review=human_review,
        wordpress_handoff=wordpress_handoff,
        measurement_window=measurement_window,
    )


def _gate_revision_workspace(
    workspace: ContentDraftRevisionWorkspace,
    planning_workspace: ContentPlanningWorkspace | None,
) -> ContentDraftRevisionWorkspace:
    if workspace.latest_revision is not None or planning_workspace is None:
        return workspace
    if planning_workspace.scope_current and planning_workspace.section_map_current:
        return workspace
    return workspace.model_copy(
        update={
            "can_save": False,
            "safe_next_step": "Najpierw zatwierdź aktualny zakres i plan sekcji.",
        }
    )


def _wordpress_handoff(
    *,
    item: ContentWorkItem,
    draft: ContentDraftPackage | None,
    planning_digest: str | None,
    planning_input_digest: str | None,
    service_card_id: str | None,
    human_review: ContentWorkItemHumanReviewResponse,
    audit: ContentWordPressDraftAuditEnvelope | None,
    revision_state: ContentDraftRevisionState | None,
    callbacks: SnapshotAssemblyCallbacks,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    if revision_state is None or revision_state.revision_count == 0:
        return callbacks.wordpress_handoff(
            human_review.reviewed_item,
            draft,
            human_review.review,
            audit,
        )
    return ContentWorkItemWordPressDraftHandoffResponse(
        item=item,
        handoff_result=build_revision_bound_wordpress_draft_handoff(
            item=item,
            draft_package=draft,
            revision_state=revision_state,
            planning_digest=planning_digest,
            planning_input_digest=planning_input_digest,
            service_card_id=service_card_id,
        ),
    )


def _operator_journey(
    *,
    item: ContentWorkItem,
    foundation: _SnapshotFoundation,
    delivery: _SnapshotDelivery,
    revision_state: ContentDraftRevisionState | None,
) -> ContentWorkflowOperatorJourney:
    brief = foundation.sales_brief.sales_brief_result.brief
    draft = foundation.draft_package.draft_package_result.draft_package
    sales_blocker = foundation.sales_brief.sales_brief_result.blockers[0:1]
    section_blocker = foundation.draft_package.draft_package_result.blockers[0:1]
    structured_blocker = delivery.structured_generation.structured_generation_result.blockers[0:1]
    signal = None if brief is None else brief.signal_quality
    return build_content_workflow_operator_journey(
        ContentWorkflowOperatorFacts(
            sales_brief_present=brief is not None,
            sales_brief_signal_status=None if signal is None else signal.status,
            sales_brief_signal_reason=None if signal is None else signal.reason,
            sales_brief_safe_next_step=_sales_brief_next_step(signal, sales_blocker),
            sales_brief_blocker=_operator_blocker(sales_blocker),
            section_map_present=draft is not None,
            section_map_blocker=_operator_blocker(section_blocker),
            section_map_safe_next_step=_section_map_next_step(draft, section_blocker),
            structured_contract_present=(
                delivery.structured_generation.structured_generation_result.contract is not None
            ),
            structured_contract_blocker=_operator_blocker(structured_blocker),
            structured_contract_safe_next_step=(
                structured_blocker[0].next_step
                if structured_blocker
                else "Najpierw przygotuj kontrakt roboczego szkicu."
            ),
            revision_workspace_status=delivery.revision_workspace.status,
            revision_context_current=_revision_context_is_current(
                item=item,
                draft_package=draft,
                state=revision_state,
                planning_digest=foundation.approved_planning_digest,
                planning_input_digest=(
                    None
                    if foundation.planning_workspace is None
                    else foundation.planning_workspace.proposal.planning_input_digest
                ),
                service_card_id=(
                    None
                    if foundation.planning_workspace is None
                    else foundation.planning_workspace.proposal.service_card_id
                ),
            ),
            revision_bound_wordpress_handoff_ready=(
                delivery.wordpress_handoff.handoff_result.handoff is not None
                and delivery.wordpress_handoff.handoff_result.handoff.revision_binding is not None
            ),
            scope_review_current=bool(
                foundation.planning_workspace and foundation.planning_workspace.scope_current
            ),
            section_map_review_current=bool(
                foundation.planning_workspace and foundation.planning_workspace.section_map_current
            ),
        )
    )


def _operator_blocker(blockers: list[Any]) -> ContentWorkflowOperatorBlocker | None:
    if not blockers:
        return None
    blocker = blockers[0]
    return ContentWorkflowOperatorBlocker(
        code=blocker.code,
        label=blocker.label,
        reason=blocker.reason,
    )


def _sales_brief_next_step(signal: Any, blockers: list[Any]) -> str:
    if signal is not None:
        return str(signal.safe_next_step)
    if blockers:
        return str(blockers[0].next_step)
    return "Uzupełnij zakres, źródła i bezpieczny brief treści."


def _section_map_next_step(
    draft: ContentDraftPackage | None,
    blockers: list[Any],
) -> str:
    if draft is not None:
        return "Sprawdź kolejność sekcji, ich cele i przypisane dowody."
    if blockers:
        return str(blockers[0].next_step)
    return "Najpierw przygotuj bezpieczny plan sekcji."


def _current_planning_proposal(
    *,
    item: ContentWorkItem,
    service_profile_context: ContentWorkItemServiceProfileContext,
    preflight: ContentWorkItemPreflightResponse,
    brief: ContentSalesBrief | None,
    draft: ContentDraftPackage | None,
    baseline: ContentPlanningProposal | None,
    freshness: ContentFreshnessAssessment,
    claim_ledger: ContentClaimLedger,
    generated: ContentPlanningProposal | None,
) -> ContentPlanningProposal | None:
    service_card_id = service_profile_context.service_card_id
    if baseline is None or generated is None or service_card_id is None:
        return baseline
    planning_input = build_content_planning_input_from_components(
        item=item,
        service_profile=service_profile_context,
        inventory_resolution=preflight.inventory_resolution,
        brief=brief,
        draft=draft,
        baseline_proposal=baseline,
        freshness=freshness,
        claim_ledger=claim_ledger,
        service_card_id=service_card_id,
    )
    current_input = planning_input.planning_input
    if planning_input.blockers or current_input is None:
        return baseline
    if (
        generated.service_card_id != service_card_id
        or generated.planning_input_digest != current_input.planning_input_digest
    ):
        return baseline
    return generated


def build_content_draft_revision_workspace(
    *,
    item: ContentWorkItem,
    draft_package: ContentDraftPackage | None,
    state: ContentDraftRevisionState | None,
    structured_contract_present: bool,
    planning_digest: str | None,
    planning_input_digest: str | None,
    service_card_id: str | None,
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
        planning_input_digest=planning_input_digest,
        service_card_id=service_card_id,
    )
    if latest_revision is not None and (context_current or draft_package is None):
        editor_title = latest_revision.title
        editor_sections = latest_revision.sections
    elif draft_package is not None:
        editor_title = draft_package.title if latest_revision is None else latest_revision.title
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
            and (status in {"empty", "needs_changes", "rejected"} or not context_current)
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
        else {section.heading: section.body_markdown for section in latest_revision.sections}
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
    planning_input_digest: str | None,
    service_card_id: str | None,
) -> bool:
    if state is None or state.latest_revision is None:
        return True
    canonical_url = item.final_canonical_url or item.intended_final_url
    revision = state.latest_revision
    baseline_current = bool(
        draft_package is not None
        and canonical_url
        and revision.draft_package_id == draft_package.id
        and revision.draft_package_digest == content_draft_package_digest(draft_package)
        and revision.planning_digest is not None
        and revision.planning_digest == planning_digest
        and revision.final_canonical_url == canonical_url
    )
    if not baseline_current or revision.schema_version == "wilq_content_draft_revision_v1":
        return baseline_current
    return bool(
        revision.planning_input_digest is not None
        and revision.planning_input_digest == planning_input_digest
        and revision.service_card_id is not None
        and revision.service_card_id == service_card_id
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
        "deferred": ("Wróć do tej samej wersji i zapisz decyzję, gdy sprawdzenie będzie możliwe."),
    }
    return next_steps[status]
