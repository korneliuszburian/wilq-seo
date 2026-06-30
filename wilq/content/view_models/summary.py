from __future__ import annotations

from collections.abc import Iterable

from wilq.content.canonical.urls import content_decision_has_public_final_canonical
from wilq.content.preflight.marketer_view import (
    content_blocked_claim_labels,
    content_decision_type_summary_label,
)
from wilq.operator_labels import action_count_label, evidence_count_label
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticSection,
    ContentOperatorSummary,
    OpportunityDomain,
    TacticalQueueItem,
)


def build_content_operator_summary(
    decisions: list[ContentDecisionItem],
    sections: list[ContentDiagnosticSection],
    action_ids: list[str],
    *,
    query_page_count: int,
    matched_inventory_count: int,
) -> ContentOperatorSummary:
    top_decisions = decisions[:4]
    current_site_match_count = sum(
        1 for decision in decisions if content_decision_has_public_final_canonical(decision)
    )
    ahrefs_wordpress_overlap_count = ahrefs_wordpress_overlap_count_from_decisions(decisions)
    return ContentOperatorSummary(
        title="Co marketer ma zrobić teraz z treściami",
        summary=(
            "WILQ łączy zapytania i adresy z GSC ze spisem treści WordPress. "
            "Najpierw obsłuż istniejące URL-e i klastry zapytań, potem dopiero "
            "twórz nowe treści. Bez dowodów nie wolno twierdzić, że wzrosną "
            "leady, pozycje albo konwersje."
        ),
        next_step=(
            "Przejdź przez top decyzje contentowe: odśwież, scal, utwórz albo "
            "zablokuj. Potem sprawdź w WILQ tylko właściwą akcję."
        ),
        top_decision_ids=[decision.id for decision in top_decisions],
        confirmed_wordpress_count=sum(
            1 for decision in decisions if decision.wordpress_match == "found"
        ),
        missing_wordpress_count=sum(
            1 for decision in decisions if decision.wordpress_match == "missing"
        ),
        current_site_match_count=current_site_match_count,
        decision_type_labels=_unique(
            content_decision_type_summary_label(decision.decision_type) for decision in decisions
        ),
        source_connectors=_unique(
            connector for decision in top_decisions for connector in decision.source_connectors
        ),
        evidence_ids=_unique(
            evidence_id for decision in top_decisions for evidence_id in decision.evidence_ids
        ),
        evidence_summary_label=evidence_count_label(
            _unique(
                evidence_id for decision in top_decisions for evidence_id in decision.evidence_ids
            )
        ),
        action_ids=action_ids,
        action_summary_label=action_count_label(action_ids),
        blocked_claims=_unique(claim for section in sections for claim in section.blocked_claims),
        blocked_claim_labels=content_blocked_claim_labels(
            claim for section in sections for claim in section.blocked_claims
        ),
        metric_tiles={
            "Zapytania i adresy z GSC": query_page_count,
            "Treści znalezione w WordPress": matched_inventory_count,
            "Luki Ahrefs powiązane z WordPress": ahrefs_wordpress_overlap_count,
            "Decyzje treści": len(decisions),
        },
    )


def ahrefs_wordpress_overlap_count_from_decisions(
    decisions: list[ContentDecisionItem],
) -> int:
    for decision in decisions:
        if decision.decision_type == "review_ahrefs_gap_records":
            value = decision.metric_tiles.get("Powiązanie z WordPress")
            if isinstance(value, (int, float)):
                return int(value)
    return 0


def content_query_page_count(items: list[TacticalQueueItem]) -> int:
    return sum(1 for item in items if item.domain == OpportunityDomain.gsc_seo)


def content_matched_inventory_count(items: list[TacticalQueueItem]) -> int:
    return sum(1 for item in items if item.dimensions.get("wordpress_match") == "found")


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
