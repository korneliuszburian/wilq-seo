from __future__ import annotations

from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
    build_content_work_item_service_profile_context,
)
from wilq.content.workflow.models import ContentWorkItem


def test_homepage_projects_typed_service_profile_binding_with_review_requirement() -> None:
    context = build_content_work_item_service_profile_context(
        ContentWorkItem(
            id="content_work_item_homepage",
            topic="Strona główna ekologus.pl: sprawdź istniejącą treść",
            source_public_url="https://www.ekologus.pl/",
            final_canonical_url="https://www.ekologus.pl/",
            intended_final_url="https://www.ekologus.pl/",
            evidence_ids=["ev_gsc_homepage"],
            source_connectors=["google_search_console", "wordpress_ekologus"],
        )
    )

    assert context.binding_status == "bound"
    assert context.decision_status == "review_required"
    assert context.service_card_id == "ekologus_service_homepage_overview"
    assert context.service_label == "Strona główna i przegląd oferty Ekologus"
    assert context.service_status == "source_backed_review_required"
    assert context.evidence_ids == ["ev_content_service_profile_source_facts"]
    assert context.source_connectors == ["public_site"]
    assert context.freshness_label == "publiczna strona wymaga review (ostatni sygnał: 2026-07-02)"
    assert context.freshness_as_of == "2026-07-02"
    assert context.claims_needing_review
    assert context.blocked_claims
    assert context.claim_policy_scope_label.startswith("Ten skrót dotyczy tylko")
    assert context.missing_contracts
    assert context.review_action_id == (
        "service_profile_review_card_ekologus_service_homepage_overview"
    )
    assert context.safe_next_step.startswith("Sprawdź kartę usługi")


def test_unbound_work_item_is_a_blocker_not_a_free_text_service_guess() -> None:
    context = build_content_work_item_service_profile_context(
        ContentWorkItem(
            id="content_work_item_unrelated_topic",
            topic="Rozliczenie podatku dochodowego dla firmy IT",
            evidence_ids=["ev_gsc_unrelated_topic"],
            source_connectors=["google_search_console"],
        )
    )

    assert context.binding_status == "unbound"
    assert context.decision_status == "blocked"
    assert context.service_card_id is None
    assert context.service_label is None
    assert context.allowed_claims == []
    assert context.evidence_ids == []
    assert context.source_connectors == []
    assert context.missing_contracts
    assert "typed karty usługi" in context.reason


def test_two_exact_pages_use_one_normalized_service_candidate_contract() -> None:
    bdo = build_content_work_item_service_profile_context(
        ContentWorkItem(
            id=(
                "content_work_item_content_decision_https___www_ekologus_pl_"
                "bdo_co_musi_wiedziec_przedsiebiorca"
            ),
            topic="BDO — co musi wiedzieć przedsiębiorca?",
            source_public_url=(
                "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
            ),
            final_canonical_url=(
                "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
            ),
            evidence_ids=["ev_gsc_bdo", "ev_wp_bdo"],
            source_connectors=["google_search_console", "wordpress_ekologus"],
        )
    )
    outsourcing = build_content_work_item_service_profile_context(
        ContentWorkItem(
            id=(
                "content_work_item_content_decision_https___www_ekologus_pl_"
                "oferta_doradztwo_i_outsourcing_ekologiczny"
            ),
            topic="Doradztwo i outsourcing ekologiczny",
            source_public_url=(
                "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/"
            ),
            final_canonical_url=(
                "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/"
            ),
            evidence_ids=["ev_gsc_outsourcing", "ev_wp_outsourcing"],
            source_connectors=["google_search_console", "wordpress_ekologus"],
        )
    )

    assert bdo.service_card_id == "ekologus_service_bdo_reporting"
    assert outsourcing.service_card_id == (
        "ekologus_service_environmental_consulting_outsourcing"
    )
    assert all(candidate.lifecycle_status for candidate in bdo.service_candidates)
    assert all(candidate.match_reasons for candidate in bdo.service_candidates)
    assert [
        candidate.service_card_id
        for candidate in outsourcing.service_candidates
        if candidate.recommended
    ] == ["ekologus_service_environmental_consulting_outsourcing"]
    assert outsourcing.service_candidates[0].matched_terms == [
        "outsourcing ekologiczny"
    ]
    assert bdo.decision_status == "ready"
    assert outsourcing.decision_status == "ready"
    assert not bdo.missing_contracts
    assert not outsourcing.missing_contracts


def test_exact_landing_url_wins_when_page_copy_mentions_bdo_too() -> None:
    context = build_content_work_item_service_profile_context(
        ContentWorkItem(
            id="content_work_item_outsourcing_with_bdo_copy",
            topic="Doradztwo i outsourcing ekologiczny",
            source_public_url=(
                "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/"
            ),
            final_canonical_url=(
                "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/"
            ),
            wordpress_content_text=(
                "Doradztwo i outsourcing ekologiczny. W ramach oferty wspieramy "
                "firmy także przy BDO i sprawozdawczości."
            ),
            evidence_ids=["ev_wp_outsourcing"],
            source_connectors=["wordpress_ekologus"],
        )
    )

    assert context.service_card_id == (
        "ekologus_service_environmental_consulting_outsourcing"
    )

    for foreign_topic in ("subdomena firmowa", "rozliczenie podatku dochodowego"):
        unrelated = build_content_work_item_service_profile_context(
            ContentWorkItem(
                id=f"content_work_item_{foreign_topic.replace(' ', '_')}",
                topic=foreign_topic,
                evidence_ids=["ev_gsc_unrelated"],
                source_connectors=["google_search_console"],
            )
        )
        assert unrelated.service_card_id is None
        assert all(
            candidate.service_card_id != "ekologus_service_bdo_reporting"
            for candidate in unrelated.service_candidates
        )


def test_not_evaluated_context_does_not_assign_a_service_before_workflow_snapshot() -> None:
    context = ContentWorkItemServiceProfileContext.not_evaluated(
        safe_next_step="Najpierw usuń blocker kolejki."
    )

    assert context.binding_status == "not_evaluated"
    assert context.decision_status == "not_evaluated"
    assert context.service_card_id is None
    assert context.evidence_ids == []
    assert context.safe_next_step == "Najpierw usuń blocker kolejki."
