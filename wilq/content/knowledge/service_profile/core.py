"""Decomposed service_profile core implementation."""

from __future__ import annotations

from wilq.content.knowledge.cards import content_knowledge_cards_response
from wilq.content.knowledge.private_source_proposals import (
    ekologus_private_source_proposal_registry,
)
from wilq.content.knowledge.service_profile.claims import (
    _coverage_gaps,
    _coverage_summary,
    _policy_section,
    _private_source_proposal_sections,
    _private_source_proposal_summary,
    _service_section,
    _source_fact_coverage_audit,
)
from wilq.content.knowledge.service_profile.contracts import (
    ContentServiceProfileResponse,
    ContentServiceProfileReviewPolicy,
    ContentServiceProfileTechnicalTrace,
)
from wilq.content.knowledge.service_profile.review import (
    _approval_readiness,
    _review_action_summary,
    _review_actions,
)
from wilq.content.knowledge.source_facts import ekologus_source_fact_registry


def content_service_profile_response() -> ContentServiceProfileResponse:
    knowledge = content_knowledge_cards_response()
    source_fact_registry = ekologus_source_fact_registry()
    private_proposal_registry = ekologus_private_source_proposal_registry()
    cards = knowledge.cards
    source_facts = list(source_fact_registry.facts)
    service_sections = [_service_section(card) for card in cards if card.card_type == "service"]
    coverage_gaps = _coverage_gaps(cards)
    private_proposals = private_proposal_registry.proposals
    review_actions = _review_actions(
        cards=cards,
        coverage_gaps=coverage_gaps,
        private_proposals=private_proposals,
    )
    review_action_summary = _review_action_summary(
        review_actions=review_actions,
    )
    coverage_summary = _coverage_summary(
        cards=cards,
        private_candidate_count=private_proposal_registry.proposal_count,
        missing_required_area_count=len(coverage_gaps),
        status_label=knowledge.production_depth_readiness.status_label,
        ready_for_daily_content=knowledge.production_depth_readiness.ready_for_daily_content,
    )
    source_fact_coverage = _source_fact_coverage_audit(
        source_facts=source_facts,
        service_sections=service_sections,
        private_proposals=private_proposals,
        coverage_summary=coverage_summary,
        production_depth_readiness=knowledge.production_depth_readiness,
        coverage_gaps=coverage_gaps,
        review_action_summary=review_action_summary,
        review_actions=review_actions,
    )
    return ContentServiceProfileResponse(
        workspace_id="ekologus",
        workspace_label="Ekologus",
        generated_at="2026-07-01T00:00:00Z",
        read_only=True,
        review_policy=ContentServiceProfileReviewPolicy(
            can_edit_cards=False,
            can_promote_facts=False,
            can_request_review=True,
            review_required_label=(
                "Wiedza review-required może wspierać analizę i UAT, "
                "ale nie odblokowuje production-depth treści."
            ),
            blocked_write_reason=(
                "Edycja kart i promocja faktów wymagają osobnej zatwierdzonej "
                "akcji, review człowieka i audytu."
            ),
        ),
        production_depth_readiness=knowledge.production_depth_readiness,
        coverage_summary=coverage_summary,
        service_sections=service_sections,
        claim_policy_sections=[
            _policy_section(card)
            for card in cards
            if card.claims_needing_review
            or card.forbidden_claims
            or card.measurement_sensitive_claims
        ],
        evidence_policy_sections=[
            _policy_section(card)
            for card in cards
            if card.card_type == "evidence_requirement" or card.evidence_requirements
        ],
        private_source_proposal_summary=_private_source_proposal_summary(private_proposals),
        private_review_value=source_fact_coverage.private_review_value,
        private_source_proposals=_private_source_proposal_sections(private_proposals),
        coverage_gaps=coverage_gaps,
        review_action_summary=review_action_summary,
        review_actions=review_actions,
        source_fact_coverage=source_fact_coverage,
        approval_readiness=_approval_readiness(
            coverage_summary=coverage_summary,
            review_action_summary=review_action_summary,
            private_proposals=private_proposals,
        ),
        technical_trace=ContentServiceProfileTechnicalTrace(
            knowledge_card_endpoint="/api/content/knowledge-cards",
            source_fact_count=source_fact_registry.fact_count,
            source_fact_ids=[fact.source_id for fact in source_fact_registry.facts],
            private_source_proposal_ids=[
                proposal.proposal_id for proposal in private_proposal_registry.proposals
            ],
            private_source_protocol_doc="docs/architecture/private-source-proposal-protocol.md",
        ),
    )
