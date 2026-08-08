"""Decomposed service_profile claims implementation."""

from __future__ import annotations

from collections import Counter
from typing import cast

from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    ContentKnowledgeProductionDepthReadiness,
)
from wilq.content.knowledge.private_source_proposals import PrivateSourceProposal
from wilq.content.knowledge.service_profile.contracts import (
    ContentServiceProfileCoverageGap,
    ContentServiceProfileCoverageSummary,
    ContentServiceProfilePolicySection,
    ContentServiceProfilePrivateSourceProposalSection,
    ContentServiceProfilePrivateSourceProposalSummary,
    ContentServiceProfileReviewAction,
    ContentServiceProfileReviewActionSummary,
    ContentServiceProfileServiceSection,
    ContentServiceProfileSourceFactCoverageAudit,
)
from wilq.content.knowledge.service_profile.review import (
    _private_review_queue,
    _private_review_value_summary,
    _review_action_queue,
)
from wilq.content.knowledge.service_profile.shared import (
    _confidence_label,
    _lifecycle,
    _percent,
    _redacted_lineage,
    _safe_next_step,
    _status_label,
    _unique,
)
from wilq.content.knowledge.source_facts import ContentKnowledgeLifecycleStatus, ContentSourceFact


def _source_fact_coverage_knowledge_status(status: str) -> ContentKnowledgeLifecycleStatus:
    if status == "production_depth":
        return "approved_current"
    return cast(ContentKnowledgeLifecycleStatus, status)


def _source_fact_coverage_audit(
    *,
    source_facts: list[ContentSourceFact],
    service_sections: list[ContentServiceProfileServiceSection],
    private_proposals: list[PrivateSourceProposal],
    coverage_summary: ContentServiceProfileCoverageSummary,
    production_depth_readiness: ContentKnowledgeProductionDepthReadiness,
    coverage_gaps: list[ContentServiceProfileCoverageGap],
    review_action_summary: ContentServiceProfileReviewActionSummary,
    review_actions: list[ContentServiceProfileReviewAction],
) -> ContentServiceProfileSourceFactCoverageAudit:
    fact_review_counts = Counter(fact.review_status for fact in source_facts)
    fact_scope_counts = Counter(fact.scope for fact in source_facts)
    fact_connector_counts = Counter(
        connector for fact in source_facts for connector in fact.source_connectors
    )
    approved_service_count = sum(
        1 for section in service_sections if section.status == "approved_current"
    )
    private_review_queue = _private_review_queue(private_proposals)
    private_review_value = _private_review_value_summary(
        facts=source_facts,
        private_review_queue=private_review_queue,
    )
    review_action_queue = _review_action_queue(
        review_actions=review_actions,
        service_sections=service_sections,
        private_proposals=private_proposals,
        first_review_action_id=review_action_summary.first_review_action_id,
    )
    blockers = [
        *production_depth_readiness.blocker_labels,
        *(gap.reason for gap in coverage_gaps),
    ]
    pass_state = (
        bool(source_facts)
        and bool(review_actions)
        and not any(proposal.promotion_allowed for proposal in private_review_queue)
    )
    return ContentServiceProfileSourceFactCoverageAudit(
        pass_state=pass_state,
        knowledge_status=_source_fact_coverage_knowledge_status(production_depth_readiness.status),
        ready_for_daily_content=production_depth_readiness.ready_for_daily_content,
        production_depth_percent=_percent(
            production_depth_readiness.production_depth_card_count,
            max(coverage_summary.service_card_count, 1),
        ),
        approved_service_percent=_percent(
            approved_service_count,
            max(len(service_sections), 1),
        ),
        reviewed_fact_percent=_percent(
            fact_review_counts["approved"],
            max(len(source_facts), 1),
        ),
        fact_count=len(source_facts),
        fact_review_counts=dict(sorted(fact_review_counts.items())),
        fact_scope_counts=dict(sorted(fact_scope_counts.items())),
        fact_connector_counts=dict(sorted(fact_connector_counts.items())),
        service_card_count=coverage_summary.service_card_count,
        coverage_gap_count=len(coverage_gaps),
        review_action_count=review_action_summary.total_count,
        first_review_action_id=review_action_summary.first_review_action_id,
        first_review_action_label=review_action_summary.first_review_action_label,
        private_proposal_count=len(private_proposals),
        private_review_required_count=(
            sum(1 for proposal in private_proposals if proposal.review_status == "review_required")
        ),
        private_review_value=private_review_value,
        private_review_queue=private_review_queue,
        review_action_queue=review_action_queue,
        blockers=blockers,
        safe_next_step=coverage_summary.safe_next_step,
    )


def _private_source_proposal_sections(
    proposals: list[PrivateSourceProposal],
) -> list[ContentServiceProfilePrivateSourceProposalSection]:
    return [
        ContentServiceProfilePrivateSourceProposalSection(
            proposal_id=proposal.proposal_id,
            source_id=proposal.source_id,
            source_type=proposal.source_type,
            privacy_class=proposal.privacy_class,
            scope=proposal.scope,
            target_card_id=proposal.target_card_id,
            target_card_title=proposal.target_card_title,
            source_class_label=proposal.source_class_label,
            source_locator_label=proposal.source_locator_label,
            freshness_status=proposal.freshness_status,
            review_status=proposal.review_status,
            support_level=proposal.support_level,
            risk_tier=proposal.risk_tier,
            data_classes=proposal.data_classes,
            source_block_refs=proposal.source_block_refs,
            retention_decision=proposal.retention_decision,
            deletion_path=proposal.deletion_path,
            eval_case_ids=proposal.eval_case_ids,
            confidence_label=_confidence_label(proposal.confidence),
            owner_role=proposal.owner_role,
            audience=proposal.audience,
            redacted=True,
            blocked_claims=proposal.blocked_claims,
            safe_next_step=proposal.safe_next_step,
            promotion_allowed=False,
            blocked_write_claim=(
                "To jest redacted proposal do review; nie promuje source fact ani knowledge card."
            ),
        )
        for proposal in proposals
    ]


def _private_source_proposal_summary(
    proposals: list[PrivateSourceProposal],
) -> ContentServiceProfilePrivateSourceProposalSummary:
    review_required = [
        proposal for proposal in proposals if proposal.review_status == "review_required"
    ]
    approved = [proposal for proposal in proposals if proposal.review_status == "approved"]
    scope_counts = Counter(proposal.scope for proposal in proposals)
    if review_required:
        safe_next_step = (
            "Pokaż redacted propozycje Wilkowi i zdecyduj, czy któraś ma stać się "
            "reviewed internal source fact; żadna nie odblokowuje production-depth."
        )
    else:
        safe_next_step = (
            "Użyj protokołu private source proposals dopiero po metadata-only "
            "intake i decyzji ownera."
        )
    return ContentServiceProfilePrivateSourceProposalSummary(
        proposal_protocol_available=True,
        proposal_count=len(proposals),
        service_proposal_count=scope_counts["service"],
        claim_policy_proposal_count=scope_counts["claim_policy"],
        evidence_requirement_proposal_count=scope_counts["evidence_requirement"],
        review_required_count=len(review_required),
        approved_count=len(approved),
        promotion_ready=False,
        promotion_checklist=[
            "Wilku albo owner potwierdza, że propozycja opisuje realną ofertę Ekologus.",
            "Źródło zostaje streszczone jako redacted/source-safe fact bez raw private text.",
            "Owner wskazuje dozwolone claimy, claimy wymagające review i claimy zakazane.",
            "WILQ zapisuje reviewer, freshness date, confidence i evidence/source lineage.",
            "Focused eval potwierdza, że karta nie odblokowuje legal/product/performance claimów.",
        ],
        promotion_blocked_reason=(
            "Brak zatwierdzenia człowieka i reviewed source fact; Service Profile pokazuje "
            "tylko propozycje review, bez promocji do wiedzy produkcyjnej."
        ),
        proposal_source_labels=_unique(proposal.source_locator_label for proposal in proposals),
        review_required_proposal_ids=[proposal.proposal_id for proposal in review_required],
        redacted=True,
        safe_next_step=safe_next_step,
    )


def _coverage_summary(
    *,
    cards: list[ContentKnowledgeCard],
    private_candidate_count: int,
    missing_required_area_count: int,
    status_label: str,
    ready_for_daily_content: bool,
) -> ContentServiceProfileCoverageSummary:
    lifecycle_counts = Counter(_lifecycle(card) for card in cards)
    return ContentServiceProfileCoverageSummary(
        card_count=len(cards),
        service_card_count=sum(1 for card in cards if card.card_type == "service"),
        seeded_contract_proof_count=lifecycle_counts["seeded_contract_proof"],
        source_backed_review_required_count=lifecycle_counts["source_backed_review_required"],
        approved_current_count=lifecycle_counts["approved_current"],
        stale_count=lifecycle_counts["stale"],
        rejected_count=lifecycle_counts["rejected"],
        private_candidate_count=private_candidate_count,
        missing_required_area_count=missing_required_area_count,
        ready_for_daily_content=ready_for_daily_content,
        status_label=status_label,
        safe_next_step=(
            "Przejrzyj karty review-required i luki usługowe z Wilkiem przed "
            "użyciem ich jako production-depth."
        ),
    )


def _service_section(card: ContentKnowledgeCard) -> ContentServiceProfileServiceSection:
    status = _lifecycle(card)
    return ContentServiceProfileServiceSection(
        card_id=card.id,
        title=card.title,
        status=status,
        status_label=_status_label(status),
        summary=card.summary,
        source_fact_ids=card.source_fact_ids,
        evidence_ids=card.evidence_ids,
        source_connector_labels=card.source_connectors,
        source_lineage_labels=_redacted_lineage(card.source_lineage),
        freshness_label=card.freshness,
        confidence_label=_confidence_label(card.confidence),
        service_fit_terms=card.service_fit_terms,
        buyer_problem_terms=card.buyer_problem_terms,
        buyer_triggers=card.buyer_triggers,
        cta_patterns=card.cta_patterns,
        allowed_claims=card.allowed_claims,
        claims_needing_review=card.claims_needing_review,
        forbidden_claims=card.forbidden_claims,
        evidence_requirements=card.evidence_requirements,
        usage_notes=card.usage_notes,
        safe_next_step=_safe_next_step(status),
        review_request_hint=(
            "Poproś Wilka/ownera o decyzję: approve, stale, reject albo potrzebne źródło."
        ),
    )


def _policy_section(card: ContentKnowledgeCard) -> ContentServiceProfilePolicySection:
    status = _lifecycle(card)
    return ContentServiceProfilePolicySection(
        card_id=card.id,
        title=card.title,
        status=status,
        claims_needing_review=card.claims_needing_review,
        forbidden_claims=card.forbidden_claims,
        measurement_sensitive_claims=card.measurement_sensitive_claims,
        evidence_requirements=card.evidence_requirements,
        safe_next_step=_safe_next_step(status),
    )


def _coverage_gaps(cards: list[ContentKnowledgeCard]) -> list[ContentServiceProfileCoverageGap]:
    service_terms = {term.lower() for card in cards for term in card.service_fit_terms}
    gaps: list[ContentServiceProfileCoverageGap] = []
    if "operat wodnoprawny" not in service_terms:
        gaps.append(
            ContentServiceProfileCoverageGap(
                gap_id="gap_service_operat_wodnoprawny",
                area="operat wodnoprawny",
                severity="blocker",
                label="Brak bezpośredniej karty usługi dla operatu wodnoprawnego",
                reason=(
                    "WILQ nie powinien dopasowywać szerokiej karty środowiskowej "
                    "do konkretnej usługi bez źródła."
                ),
                needed_source_type="public_site_or_reviewed_internal_service_fact",
                safe_next_step=(
                    "Dodaj publiczny albo reviewed internal source fact i zostaw go "
                    "review-required do decyzji Wilka."
                ),
                example_work_item_ids=["content_work_item_operat_wodnoprawny"],
            )
        )
    if not any(_lifecycle(card) == "approved_current" for card in cards):
        gaps.append(
            ContentServiceProfileCoverageGap(
                gap_id="gap_no_approved_current_cards",
                area="production-depth",
                severity="review_required",
                label="Brak zatwierdzonych production-depth kart usług",
                reason="Obecne karty są seedami albo source-backed review-required.",
                needed_source_type="owner_reviewed_source_fact",
                safe_next_step="Przeprowadź review kart usługowych i zapisz reviewer/freshness.",
            )
        )
    return gaps
