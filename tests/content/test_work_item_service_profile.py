from __future__ import annotations

from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
    build_content_work_item_service_profile_context,
)
from wilq.content.workflow.models import ContentWorkItem


def test_homepage_projects_typed_service_profile_binding_with_review_blocker() -> None:
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
    assert context.decision_status == "blocked"
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


def test_not_evaluated_context_does_not_assign_a_service_before_workflow_snapshot() -> None:
    context = ContentWorkItemServiceProfileContext.not_evaluated(
        safe_next_step="Najpierw usuń blocker kolejki."
    )

    assert context.binding_status == "not_evaluated"
    assert context.decision_status == "not_evaluated"
    assert context.service_card_id is None
    assert context.evidence_ids == []
    assert context.safe_next_step == "Najpierw usuń blocker kolejki."
