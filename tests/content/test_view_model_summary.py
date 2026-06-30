from __future__ import annotations

from typing import Literal

from wilq.content.view_models.summary import (
    ahrefs_wordpress_overlap_count_from_decisions,
    build_content_operator_summary,
    content_matched_inventory_count,
    content_query_page_count,
)
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticSection,
    OpportunityDomain,
    TacticalQueueItem,
)

type ContentDecisionKind = Literal[
    "block_until_vendor_read",
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "block_as_tracking_not_content",
    "review_ahrefs_gap_records",
]


def _decision(
    decision_id: str,
    decision_type: ContentDecisionKind,
    *,
    wordpress_match: str = "found",
    metric_tiles: dict[str, int | float | str] | None = None,
) -> ContentDecisionItem:
    return ContentDecisionItem(
        id=decision_id,
        decision_type=decision_type,
        status="ready",
        title="Treść do sprawdzenia",
        priority=20,
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=[f"ev_{decision_id}"],
        action_ids=["act_prepare_content_refresh_queue"],
        wordpress_match=wordpress_match,
        final_canonical_url="https://www.ekologus.pl/bdo/",
        metric_tiles=metric_tiles or {},
        rationale="WILQ ma dowody.",
        next_step="Sprawdź plan.",
    )


def test_content_operator_summary_defends_preserve_first_workflow() -> None:
    decisions = [
        _decision("content_decision_bdo", "refresh_or_merge"),
        _decision(
            "content_decision_ahrefs",
            "review_ahrefs_gap_records",
            metric_tiles={"Powiązanie z WordPress": 3},
        ),
    ]
    sections = [
        ContentDiagnosticSection(
            id="content_action_safety",
            title="Bezpieczeństwo akcji contentowych",
            status="ready",
            summary="Akcje contentowe są przygotowaniem.",
            diagnosis="Nie publikuj bez sprawdzenia.",
            next_step="Sprawdź akcję.",
            blocked_claims=["ranking_guarantee"],
        )
    ]

    summary = build_content_operator_summary(
        decisions,
        sections,
        ["act_prepare_content_refresh_queue"],
        query_page_count=4,
        matched_inventory_count=1,
    )

    assert summary.title == "Co marketer ma zrobić teraz z treściami"
    assert summary.top_decision_ids == ["content_decision_bdo", "content_decision_ahrefs"]
    assert summary.confirmed_wordpress_count == 2
    assert summary.current_site_match_count == 2
    assert summary.metric_tiles == {
        "Zapytania i adresy z GSC": 4,
        "Treści znalezione w WordPress": 1,
        "Luki Ahrefs powiązane z WordPress": 3,
        "Decyzje treści": 2,
    }
    assert "odświeżenie albo scalenie" in summary.decision_type_labels
    assert summary.blocked_claim_labels == ["gwarancja wzrostu pozycji"]


def test_content_summary_counts_query_pages_and_inventory_matches() -> None:
    gsc_item = TacticalQueueItem(
        id="queue_gsc",
        title="GSC item",
        domain=OpportunityDomain.gsc_seo,
        intent="content_refresh",
        priority=20,
        source_connectors=["google_search_console"],
        evidence_ids=["ev_gsc"],
        diagnosis="GSC pokazuje popyt.",
        next_step="Sprawdź plan.",
        dimensions={"wordpress_match": "found"},
    )
    content_item = TacticalQueueItem(
        id="queue_content",
        title="Content item",
        domain=OpportunityDomain.content,
        intent="content_refresh",
        priority=20,
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp"],
        diagnosis="WordPress potwierdza treść.",
        next_step="Sprawdź plan.",
        dimensions={"wordpress_match": "missing"},
    )

    assert content_query_page_count([gsc_item, content_item]) == 1
    assert content_matched_inventory_count([gsc_item, content_item]) == 1


def test_ahrefs_wordpress_overlap_defaults_to_zero_without_review_decision() -> None:
    assert ahrefs_wordpress_overlap_count_from_decisions([]) == 0
    assert (
        ahrefs_wordpress_overlap_count_from_decisions(
            [_decision("content_decision_bdo", "refresh_or_merge")]
        )
        == 0
    )
