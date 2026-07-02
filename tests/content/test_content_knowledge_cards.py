from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_workflow import router
from wilq.actions.service import get_action, preview_action, validate_action
from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    compile_source_facts_to_knowledge_cards,
    content_knowledge_card_blockers,
    content_knowledge_cards_response,
    content_knowledge_production_depth_readiness,
    ekologus_content_knowledge_cards,
    ekologus_seed_content_knowledge_cards,
    match_content_knowledge_cards,
    required_content_knowledge_card_ids,
)
from wilq.content.knowledge.service_profile import content_service_profile_response
from wilq.content.knowledge.source_facts import (
    ContentSourceFact,
    ekologus_source_fact_registry,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.evidence.registry import (
    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    get_evidence,
)


def _item(**overrides: object) -> ContentWorkItem:
    payload: dict[str, Any] = {
        "id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "duplicate_status": "checked",
    }
    payload.update(overrides)
    return ContentWorkItem.model_validate(payload)


def test_ekologus_content_knowledge_cards_are_typed_and_seeded() -> None:
    cards = ekologus_content_knowledge_cards()

    assert {card.id for card in cards} >= {
        "ekologus_service_environmental_compliance",
        "ekologus_cta_consultation_without_guarantee",
        "ekologus_evidence_live_connector_requirement",
    }
    service_card = next(card for card in cards if card.card_type == "service")
    assert service_card.confidence >= 0.8
    assert service_card.source_lineage
    assert service_card.claims_needing_review
    assert service_card.forbidden_claims
    assert service_card.measurement_sensitive_claims
    assert "bdo" in service_card.service_fit_terms
    assert service_card.lifecycle_status == "seeded_contract_proof"


def test_source_fact_registry_loads_commit_safe_public_facts() -> None:
    registry = ekologus_source_fact_registry()

    assert registry.fact_count >= 5
    bdo_fact = next(
        fact for fact in registry.facts if fact.source_id == "ekologus_public_bdo_faq_2026_07_01"
    )
    assert bdo_fact.source_type == "public_site"
    assert bdo_fact.privacy_class == "commit_safe"
    assert bdo_fact.review_status == "review_required"
    assert bdo_fact.source_connectors == ["public_site"]
    assert bdo_fact.blocked_claims


def test_source_facts_compile_to_review_required_cards() -> None:
    cards = compile_source_facts_to_knowledge_cards(ekologus_source_fact_registry().facts)

    bdo_card = next(card for card in cards if card.id == "ekologus_service_bdo_reporting")
    assert bdo_card.lifecycle_status == "source_backed_review_required"
    assert bdo_card.freshness == "public_site_review_required_2026-07-01"
    assert bdo_card.source_fact_ids == ["ekologus_public_bdo_faq_2026_07_01"]
    assert bdo_card.source_connectors == ["public_site"]
    assert "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/" in (
        bdo_card.source_lineage
    )
    assert bdo_card.claims_needing_review
    assert any("unikniesz kary" in rule.reason for rule in bdo_card.forbidden_claims)
    assert "ekologus_service_eko_opieka_calendar" not in {card.id for card in cards}
    assert "ekologus_claim_policy_brand_voice" not in {card.id for card in cards}
    assert "ekologus_claim_policy_legal_safety" not in {card.id for card in cards}


def test_service_profile_exposes_private_policy_proposals_without_promotion() -> None:
    profile = content_service_profile_response()

    proposals = {proposal.target_card_id: proposal for proposal in profile.private_source_proposals}
    assert {
        "ekologus_service_eko_opieka_calendar",
        "ekologus_service_environmental_compliance_audit",
        "ekologus_claim_policy_brand_voice",
        "ekologus_claim_policy_legal_safety",
    } <= set(proposals)
    assert profile.private_source_proposal_summary.proposal_count >= 4
    assert profile.private_source_proposal_summary.service_proposal_count >= 2
    assert profile.private_source_proposal_summary.claim_policy_proposal_count >= 2
    assert profile.private_source_proposal_summary.evidence_requirement_proposal_count == 0
    assert profile.private_source_proposal_summary.review_required_count >= 4
    assert profile.private_source_proposal_summary.promotion_ready is False
    assert profile.review_policy.can_promote_facts is False
    assert profile.production_depth_readiness.ready_for_daily_content is False

    brand_voice = proposals["ekologus_claim_policy_brand_voice"]
    assert brand_voice.scope == "claim_policy"
    assert brand_voice.source_class_label == "review-required internal claim-policy source fact"
    assert brand_voice.support_level == "direct"
    assert brand_voice.risk_tier == "high"
    assert brand_voice.promotion_allowed is False
    assert "automatycznej bramki bez review" in brand_voice.safe_next_step

    legal_safety = proposals["ekologus_claim_policy_legal_safety"]
    assert legal_safety.scope == "claim_policy"
    assert legal_safety.redacted is True
    assert legal_safety.blocked_claims

    action_ids = {action.action_id for action in profile.review_actions}
    assert (
        "service_profile_review_private_proposal_"
        "ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01"
    ) in action_ids
    assert (
        "service_profile_review_private_proposal_"
        "ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01"
    ) in action_ids


def test_source_backed_waste_storage_card_matches_review_required_topic() -> None:
    match = match_content_knowledge_cards(
        _item(
            id="content_work_item_magazynowanie_odpadow",
            topic="Magazynowanie odpadów",
            source_public_url="https://ekologus.pl/magazynowanie-odpadow/",
            final_canonical_url="https://ekologus.pl/magazynowanie-odpadow/",
            intended_final_url="https://ekologus.pl/magazynowanie-odpadow/",
            evidence_ids=["ev_gsc_magazynowanie_odpadow", "ev_wp_magazynowanie_odpadow"],
        )
    )

    assert match.blockers == []
    assert match.service_card is not None
    assert match.service_card.id == "ekologus_service_waste_packaging_obligations"
    assert match.service_card.lifecycle_status == "source_backed_review_required"
    assert "ekologus_public_waste_packaging_obligations_2026_07_01" in (
        match.service_card.source_fact_ids
    )
    assert any(
        "techniczne zalecenie magazynowania odpadów" in rule.reason
        for rule in match.service_card.forbidden_claims
    )


def test_water_permit_topic_matches_review_required_public_source_card() -> None:
    match = match_content_knowledge_cards(
        _item(
            id="content_work_item_operat_wodnoprawny",
            topic="Operat wodnoprawny",
            source_public_url="https://ekologus.pl/operat-wodnoprawny/",
            final_canonical_url="https://ekologus.pl/operat-wodnoprawny/",
            intended_final_url="https://ekologus.pl/operat-wodnoprawny/",
            evidence_ids=["ev_gsc_operat_wodnoprawny", "ev_wp_operat_wodnoprawny"],
        )
    )

    blocker_codes = {blocker.code for blocker in content_knowledge_card_blockers(match)}
    assert match.service_card is not None
    assert match.service_card.id == "ekologus_service_operat_wodnoprawny"
    assert match.service_card.lifecycle_status == "source_backed_review_required"
    assert "missing_service_card" not in blocker_codes
    assert "ekologus_public_water_permit_documentation_2026_07_02" in (
        match.service_card.source_fact_ids
    )
    assert "public_site" in match.service_card.source_connectors
    assert any(
        "gwarancja uzyskania pozwolenia wodnoprawnego" in rule.reason
        for rule in match.service_card.forbidden_claims
    )
    assert any(
        "GSC/WordPress evidence" in requirement
        for requirement in match.service_card.evidence_requirements
    )


def test_knowledge_cards_response_exposes_lineage_without_replacing_evidence() -> None:
    response = content_knowledge_cards_response()

    assert response.card_count == len(response.cards)
    assert "docs/goals/archive/004-goal.md" in response.source_lineage
    assert "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/" in response.source_lineage
    assert response.production_depth_readiness.status == "source_backed_review_required"
    assert response.production_depth_readiness.ready_for_daily_content is False
    assert response.production_depth_readiness.seeded_card_count == len(
        ekologus_seed_content_knowledge_cards()
    )
    assert response.production_depth_readiness.source_backed_review_required_count >= 5
    assert response.production_depth_readiness.production_depth_card_count == 0
    evidence_card = next(
        card for card in response.cards if card.id == "ekologus_evidence_live_connector_requirement"
    )
    assert any(
        "Brak evidence ID" in requirement
        for requirement in evidence_card.evidence_requirements
    )
    assert any("nie zastępuje" in note for note in evidence_card.usage_notes)


def test_internal_seeded_cards_cannot_claim_production_depth_readiness() -> None:
    readiness = content_knowledge_production_depth_readiness(
        ekologus_seed_content_knowledge_cards()
    )

    assert readiness.status == "seeded_contract_proof"
    assert readiness.ready_for_daily_content is False
    assert readiness.production_depth_card_count == 0
    assert any("production-depth" in label for label in readiness.blocker_labels)


def test_source_backed_cards_still_require_review_before_daily_content() -> None:
    cards = [
        ContentKnowledgeCard(
            id="ekologus_service_bdo_reporting",
            card_type="service",
            title="BDO i sprawozdawczość",
            summary="Publiczna strona Ekologus potwierdza temat BDO.",
            service_fit_terms=["bdo"],
            source_lineage=[
                "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
            ],
            lifecycle_status="source_backed_review_required",
            confidence=0.74,
            freshness="public_site_review_required_2026-07-01",
        )
    ]

    readiness = content_knowledge_production_depth_readiness(cards)

    assert readiness.status == "source_backed_review_required"
    assert readiness.ready_for_daily_content is False
    assert readiness.source_backed_review_required_count == 1
    assert readiness.production_depth_card_count == 0


def test_work_item_matches_required_service_cta_claim_and_evidence_cards() -> None:
    match = match_content_knowledge_cards(_item())

    assert match.blockers == []
    assert match.service_card is not None
    assert match.service_card.id == "ekologus_service_bdo_reporting"
    assert match.service_card.lifecycle_status == "source_backed_review_required"
    assert match.cta_cards
    assert match.claim_policy_cards
    assert match.evidence_requirement_cards
    required_ids = required_content_knowledge_card_ids(match)
    assert required_ids[0] == "ekologus_service_bdo_reporting"
    assert "ekologus_cta_consultation_without_guarantee" in required_ids
    assert "ekologus_evidence_live_connector_requirement" in required_ids


def test_rejected_or_private_source_facts_do_not_compile_to_cards() -> None:
    facts = [
        ContentSourceFact(
            source_id="private_fact",
            source_type="private_candidate",
            privacy_class="private_local",
            source_url_or_path="/private/source.md",
            extracted_fact="Private candidate should not be committed as a card.",
            scope="service",
            freshness_date="2026-07-01",
            confidence=0.6,
            review_status="review_required",
            target_card_id="private_card",
            target_card_type="service",
            target_card_title="Private card",
        ),
        ContentSourceFact(
            source_id="rejected_fact",
            source_type="reviewed_internal",
            privacy_class="commit_safe",
            source_url_or_path="docs/review.md",
            extracted_fact="Rejected fact should not compile.",
            scope="service",
            freshness_date="2026-07-01",
            confidence=0.6,
            review_status="rejected",
            target_card_id="rejected_card",
            target_card_type="service",
            target_card_title="Rejected card",
        ),
    ]

    assert compile_source_facts_to_knowledge_cards(facts) == ()


def test_unknown_topic_blocks_required_service_and_cta_cards() -> None:
    match = match_content_knowledge_cards(
        _item(
            topic="Neutralny temat bez dopasowania",
            source_public_url="https://ekologus.pl/neutralny-temat/",
            final_canonical_url="https://ekologus.pl/neutralny-temat/",
            intended_final_url="https://ekologus.pl/neutralny-temat/",
            evidence_ids=["ev_neutral"],
        )
    )

    blocker_codes = {blocker.code for blocker in content_knowledge_card_blockers(match)}
    assert {"missing_service_card", "missing_cta_card"} <= blocker_codes
    assert "missing_claim_policy_card" not in blocker_codes
    assert "missing_evidence_requirement_card" not in blocker_codes


def test_broad_environmental_terms_do_not_overmatch_as_service_card() -> None:
    match = match_content_knowledge_cards(
        _item(
            id="content_work_item_generic_environmental_obligation",
            topic="Obowiązki środowiskowe firmy",
            source_public_url="https://ekologus.pl/obowiazki-srodowiskowe/",
            final_canonical_url="https://ekologus.pl/obowiazki-srodowiskowe/",
            intended_final_url="https://ekologus.pl/obowiazki-srodowiskowe/",
            evidence_ids=["ev_gsc_obowiazki_srodowiskowe"],
        )
    )

    blocker_codes = {blocker.code for blocker in content_knowledge_card_blockers(match)}
    assert match.service_card is None
    assert "missing_service_card" in blocker_codes


def test_content_knowledge_cards_endpoint_exposes_typed_cards() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/content/knowledge-cards")

    assert response.status_code == 200
    payload = response.json()
    assert payload["card_count"] >= 3
    assert {card["id"] for card in payload["cards"]} >= {
        "ekologus_service_environmental_compliance",
        "ekologus_cta_consultation_without_guarantee",
        "ekologus_evidence_live_connector_requirement",
    }
    assert "docs/goals/archive/004-goal.md" in payload["source_lineage"]
    assert payload["production_depth_readiness"]["status"] == "source_backed_review_required"
    assert payload["production_depth_readiness"]["ready_for_daily_content"] is False


def test_service_profile_response_is_read_only_and_review_gated() -> None:
    response = content_service_profile_response()

    assert response.workspace_id == "ekologus"
    assert response.read_only is True
    assert response.review_policy.can_edit_cards is False
    assert response.review_policy.can_promote_facts is False
    assert response.review_policy.can_request_review is True
    assert response.coverage_summary.ready_for_daily_content is False
    assert response.coverage_summary.source_backed_review_required_count >= 5
    assert response.coverage_summary.approved_current_count == 0
    assert response.service_sections
    assert any(
        section.card_id == "ekologus_service_bdo_reporting"
        and section.status == "source_backed_review_required"
        for section in response.service_sections
    )
    public_service_review_actions = [
        action
        for action in response.review_actions
        if action.action_id.startswith("service_profile_review_card_")
    ]
    public_review_targets = {action.target_card_id for action in public_service_review_actions}
    assert "ekologus_service_bdo_reporting" in public_review_targets
    assert "ekologus_service_operat_wodnoprawny" in public_review_targets
    assert all(action.mode == "review_request" for action in public_service_review_actions)
    assert all(
        action.review_scope == "public_service_card"
        for action in public_service_review_actions
    )
    assert all(action.priority == "medium" for action in public_service_review_actions)
    assert all(
        action.decision_options == ["approve", "needs_changes", "stale", "reject"]
        for action in public_service_review_actions
    )
    required_review_fields = {
        "action_id",
        "target_card_id",
        "decision",
        "source_trace_clear",
        "blocked_claims_reviewed",
        "notes",
    }
    assert all(
        required_review_fields
        <= {requirement.field for requirement in action.review_requirements if requirement.required}
        for action in public_service_review_actions
    )
    assert all(
        any(
            requirement.field == "follow_up_beads"
            and requirement.requirement_type == "follow_up"
            and requirement.blocking_rule
            and "decision != approve" in requirement.blocking_rule
            for requirement in action.review_requirements
        )
        for action in public_service_review_actions
    )
    assert all(
        "nie promuje" in action.blocked_write_claim
        for action in public_service_review_actions
    )
    assert response.private_source_proposal_summary.proposal_protocol_available is True
    assert response.private_source_proposal_summary.proposal_count >= 4
    assert response.private_source_proposal_summary.service_proposal_count >= 2
    assert response.private_source_proposal_summary.claim_policy_proposal_count >= 2
    assert response.private_source_proposal_summary.evidence_requirement_proposal_count == 0
    assert response.private_source_proposal_summary.review_required_count >= 4
    assert response.private_source_proposal_summary.approved_count == 0
    assert response.private_source_proposal_summary.promotion_ready is False
    assert len(response.private_source_proposal_summary.promotion_checklist) >= 5
    assert "Brak zatwierdzenia człowieka" in (
        response.private_source_proposal_summary.promotion_blocked_reason
    )
    assert response.private_source_proposal_summary.redacted is True
    assert len(response.private_source_proposals) >= 4
    assert {
        "ekologus_service_eko_opieka_calendar",
        "ekologus_service_environmental_compliance_audit",
        "ekologus_claim_policy_brand_voice",
        "ekologus_claim_policy_legal_safety",
    } <= {proposal.target_card_id for proposal in response.private_source_proposals}
    assert {
        "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
        "ekologus_ai_kb003_audyt_zgodnosci_review_candidate_2026_07_01",
        "ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01",
        "ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01",
    } <= {proposal.source_id for proposal in response.private_source_proposals}
    assert all(
        proposal.source_type == "reviewed_internal"
        for proposal in response.private_source_proposals
    )
    assert all(
        proposal.privacy_class == "redacted_only"
        for proposal in response.private_source_proposals
    )
    assert all(proposal.redacted for proposal in response.private_source_proposals)
    assert all(not proposal.promotion_allowed for proposal in response.private_source_proposals)
    assert all(proposal.blocked_claims for proposal in response.private_source_proposals)
    assert all(proposal.data_classes for proposal in response.private_source_proposals)
    assert all(proposal.source_block_refs for proposal in response.private_source_proposals)
    assert all(
        proposal.retention_decision == "pending_owner_decision"
        for proposal in response.private_source_proposals
    )
    assert all(proposal.deletion_path for proposal in response.private_source_proposals)
    assert all(proposal.eval_case_ids for proposal in response.private_source_proposals)
    proposals_by_target = {
        proposal.target_card_id: proposal for proposal in response.private_source_proposals
    }
    assert "service_strategy" in proposals_by_target[
        "ekologus_service_eko_opieka_calendar"
    ].data_classes
    assert "KB_001_EKO_OPIEKA" in proposals_by_target[
        "ekologus_service_eko_opieka_calendar"
    ].source_block_refs
    assert "legal_or_claim_policy" in proposals_by_target[
        "ekologus_claim_policy_brand_voice"
    ].data_classes
    assert "goal_005_private_claim_policy_review" in proposals_by_target[
        "ekologus_claim_policy_brand_voice"
    ].eval_case_ids
    assert all(
        "nie promuje" in proposal.blocked_write_claim
        for proposal in response.private_source_proposals
    )
    assert response.coverage_summary.private_candidate_count >= 4
    assert {
        "private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
        "private_proposal_ekologus_ai_kb003_audyt_zgodnosci_review_candidate_2026_07_01",
        "private_proposal_ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01",
        "private_proposal_ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01",
    } <= set(response.technical_trace.private_source_proposal_ids)
    assert response.review_actions
    assert response.review_action_summary.total_count == len(response.review_actions)
    assert response.review_action_summary.public_service_review_count >= 6
    assert response.review_action_summary.private_review_count >= 4
    assert response.review_action_summary.private_service_review_count >= 2
    assert response.review_action_summary.private_policy_review_count >= 2
    assert response.review_action_summary.review_request_count >= 10
    assert response.review_action_summary.prepare_count >= 1
    assert "nie promuje faktów" in response.review_action_summary.safe_next_step
    private_review_actions = [
        action
        for action in response.review_actions
        if action.action_id.startswith("service_profile_review_private_proposal_")
    ]
    assert {
        "ekologus_service_eko_opieka_calendar",
        "ekologus_service_environmental_compliance_audit",
        "ekologus_claim_policy_brand_voice",
        "ekologus_claim_policy_legal_safety",
    } <= {action.target_card_id for action in private_review_actions}
    assert all(action.mode == "review_request" for action in private_review_actions)
    assert all("nie promuje" in action.blocked_write_claim for action in private_review_actions)
    private_action_by_target = {action.target_card_id: action for action in private_review_actions}
    assert (
        private_action_by_target[
            "ekologus_service_eko_opieka_calendar"
        ].review_scope
        == "private_service_proposal"
    )
    assert (
        private_action_by_target[
            "ekologus_claim_policy_brand_voice"
        ].review_scope
        == "private_claim_policy_proposal"
    )
    assert private_action_by_target["ekologus_claim_policy_brand_voice"].priority == "high"
    assert private_action_by_target[
        "ekologus_claim_policy_brand_voice"
    ].decision_options == ["approve", "needs_changes", "stale", "reject"]
    assert {
        requirement.field
        for requirement in private_action_by_target[
            "ekologus_claim_policy_brand_voice"
        ].review_requirements
        if requirement.required
    } >= required_review_fields
    assert any(
        requirement.field == "follow_up_beads" and requirement.blocking_rule
        for requirement in private_action_by_target[
            "ekologus_claim_policy_brand_voice"
        ].review_requirements
    )


def test_service_profile_exposes_water_permit_as_review_required_card() -> None:
    response = content_service_profile_response()

    assert "gap_service_operat_wodnoprawny" not in {
        gap.gap_id for gap in response.coverage_gaps
    }
    section = next(
        section
        for section in response.service_sections
        if section.card_id == "ekologus_service_operat_wodnoprawny"
    )
    assert section.status == "source_backed_review_required"
    assert "public_site" in section.source_connector_labels
    assert any(
        "pozwolenia wodnoprawnego" in claim.reason
        for claim in section.forbidden_claims
    )


def test_content_service_profile_endpoint_exposes_read_only_view_model() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/content/service-profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    assert payload["review_policy"]["can_edit_cards"] is False
    assert payload["review_policy"]["can_promote_facts"] is False
    assert payload["coverage_summary"]["ready_for_daily_content"] is False
    assert payload["production_depth_readiness"]["status"] == "source_backed_review_required"
    assert payload["private_source_proposals"]
    assert payload["private_source_proposals"][0]["promotion_allowed"] is False
    gap_ids = {gap["gap_id"] for gap in payload["coverage_gaps"]}
    assert "gap_no_approved_current_cards" in gap_ids
    assert "gap_service_operat_wodnoprawny" not in gap_ids


def test_service_profile_promotion_action_is_prepare_only_and_review_gated() -> None:
    before_profile = content_service_profile_response()
    action = get_action("act_prepare_service_profile_knowledge_promotion")

    assert action is not None
    assert action.mode == "prepare"
    assert action.connector == "wordpress_ekologus"
    assert action.evidence_ids == [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID]
    assert action.payload["action_type"] == "service_profile_knowledge_promotion_review"
    assert action.payload["preview_contract"] == (
        "service_profile_knowledge_promotion_preview_v1"
    )
    assert action.payload["apply_allowed"] is False
    assert action.payload["api_mutation_ready"] is False
    assert action.payload["target_lifecycle"] == "approved_current"
    preview_rows = action.payload["payload_preview"]
    assert preview_rows
    assert any(
        row["target_card_id"] == "ekologus_service_bdo_reporting"
        and row["source_fact_ids"] == ["ekologus_public_bdo_faq_2026_07_01"]
        for row in preview_rows
    )
    assert all(row["apply_allowed"] is False for row in preview_rows)
    assert all(row["api_mutation_ready"] is False for row in preview_rows)
    assert all("promotion_blocked_reason" in row for row in preview_rows)

    validation = validate_action(action)
    assert validation.valid is True
    preview = preview_action(action)
    assert preview.status == "blocked"
    assert preview.mutation_allowed is False
    assert "action_mode_prepare_only" in preview.blockers
    assert "payload_apply_allowed_false" in preview.blockers
    assert preview.preview_cards
    assert preview.preview_cards[0].kind == "service_profile_knowledge_promotion_review"
    assert preview.preview_cards[0].apply_state_label == "zapis zmian zablokowany"

    after_profile = content_service_profile_response()
    assert after_profile.read_only is True
    assert after_profile.review_policy.can_promote_facts is False
    assert after_profile.coverage_summary.ready_for_daily_content is False
    assert after_profile.coverage_summary.approved_current_count == (
        before_profile.coverage_summary.approved_current_count
    )


def test_private_proposal_promotion_action_is_prepare_only_and_review_gated() -> None:
    before_profile = content_service_profile_response()
    action = get_action("act_prepare_service_profile_private_proposal_promotion")

    assert action is not None
    assert action.mode == "prepare"
    assert action.connector == "wordpress_ekologus"
    assert action.evidence_ids == [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID]
    assert action.payload["action_type"] == "service_profile_private_proposal_promotion_review"
    assert action.payload["preview_contract"] == "private_source_proposal_promotion_preview_v1"
    assert action.payload["apply_allowed"] is False
    assert action.payload["api_mutation_ready"] is False
    assert action.payload["proposal_count"] >= 4
    preview_rows = action.payload["payload_preview"]
    assert preview_rows
    assert {
        "ekologus_service_eko_opieka_calendar",
        "ekologus_service_environmental_compliance_audit",
        "ekologus_claim_policy_brand_voice",
        "ekologus_claim_policy_legal_safety",
    } <= {row["target_card_id"] for row in preview_rows}
    assert {"service", "claim_policy"} <= {row["scope"] for row in preview_rows}
    assert all(row["redacted"] is True for row in preview_rows)
    assert all(row["apply_allowed"] is False for row in preview_rows)
    assert all(row["api_mutation_ready"] is False for row in preview_rows)
    assert all("promotion_blocked_reason" in row for row in preview_rows)
    assert all(row["data_classes"] for row in preview_rows)
    assert all(row["source_block_refs"] for row in preview_rows)
    assert all(row["retention_decision"] == "pending_owner_decision" for row in preview_rows)
    assert all(row["deletion_path"] for row in preview_rows)
    assert all(row["eval_case_ids"] for row in preview_rows)

    validation = validate_action(action)
    assert validation.valid is True
    preview = preview_action(action)
    assert preview.status == "blocked"
    assert preview.mutation_allowed is False
    assert "action_mode_prepare_only" in preview.blockers
    assert "payload_apply_allowed_false" in preview.blockers
    assert preview.preview_cards
    assert preview.preview_cards[0].kind == "service_profile_private_proposal_promotion_review"
    assert preview.preview_cards[0].apply_state_label == "zapis zmian zablokowany"
    assert any(
        "Prywatna propozycja Service Profile" in card.title_label
        for card in preview.preview_cards
    )

    after_profile = content_service_profile_response()
    assert after_profile.read_only is True
    assert after_profile.review_policy.can_promote_facts is False
    assert after_profile.coverage_summary.ready_for_daily_content is False
    assert after_profile.private_source_proposal_summary.promotion_ready is False
    assert after_profile.coverage_summary.approved_current_count == (
        before_profile.coverage_summary.approved_current_count
    )


def test_service_profile_source_facts_evidence_is_known() -> None:
    evidence = get_evidence(SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID)

    assert evidence is not None
    assert evidence.id == SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID
    assert evidence.source_connector == "public_site"
    assert evidence.source_type == "compiled_service_profile_source_facts"
    assert "review-required" in evidence.summary
