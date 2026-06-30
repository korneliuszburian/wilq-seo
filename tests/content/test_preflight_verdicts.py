from __future__ import annotations

from wilq.content.preflight.verdicts import (
    content_preflight_mode,
    content_preflight_next_step,
    content_preflight_query_overlap,
    content_preflight_similar_urls,
    content_preflight_status,
)
from wilq.schemas import ContentAhrefsCandidateRow, ContentDecisionItem


def _decision(**overrides: object) -> ContentDecisionItem:
    payload: dict[str, object] = {
        "id": "content_decision_bdo",
        "title": "BDO",
        "decision_type": "refresh_or_merge",
        "status": "ready",
        "reason": "Istniejąca treść wymaga sprawdzenia.",
        "rationale": "GSC i WordPress potwierdzają istniejący publiczny adres.",
        "next_step": "Sprawdź plan treści.",
        "evidence_ids": ["ev_content_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
    }
    payload.update(overrides)
    return ContentDecisionItem(**payload)


def _ahrefs_row(**overrides: object) -> ContentAhrefsCandidateRow:
    payload: dict[str, object] = {
        "id": "ahrefs_gap_bdo",
        "topic": "BDO",
        "gap_type": "content_gap",
        "relevance_status": "review",
        "relevance_score": 70,
        "gsc_demand": "present",
        "wordpress_inventory_match": "present",
        "metric_name": "keyword_gap",
        "metric_value": 3,
        "next_step": "Sprawdź lukę w treści.",
    }
    payload.update(overrides)
    return ContentAhrefsCandidateRow(**payload)


def test_preflight_refresh_decision_requires_review_before_writing() -> None:
    decision = _decision()
    mode = content_preflight_mode(decision)

    assert mode == "refresh"
    assert content_preflight_status(decision, mode) == "review_required"
    assert content_preflight_next_step(decision, mode, "review_required") == (
        "Przygotuj plan odświeżenia dopiero po sprawdzeniu ryzykownych obietnic."
    )


def test_preflight_inventory_create_candidate_stays_blocked() -> None:
    decision = _decision(
        decision_type="inventory_check_before_create",
        next_step="Najpierw potwierdź spis istniejących treści.",
    )
    mode = content_preflight_mode(decision)

    assert mode == "block"
    assert content_preflight_status(decision, mode) == "blocked"
    assert content_preflight_next_step(decision, mode, "blocked") == (
        "Najpierw potwierdź spis istniejących treści."
    )


def test_preflight_merge_decision_has_merge_next_step() -> None:
    decision = _decision(decision_type="merge_create_after_inventory_check")
    mode = content_preflight_mode(decision)

    assert mode == "merge"
    assert content_preflight_status(decision, mode) == "review_required"
    assert content_preflight_next_step(decision, mode, "review_required") == (
        "Najpierw sprawdź duplikaty i zdecyduj, które sekcje scalić."
    )


def test_preflight_similar_urls_deduplicates_inventory_and_ahrefs_overlap() -> None:
    decision = _decision(
        wordpress_match="found",
        source_public_url="https://www.ekologus.pl/bdo/",
        final_canonical_url="https://ekologus.pl/bdo/",
        ahrefs_candidate_rows=[
            _ahrefs_row(
                wordpress_overlap_urls=[
                    "https://ekologus.pl/bdo/",
                    "https://ekologus.pl/zielony-lad/",
                ]
            )
        ],
    )

    assert content_preflight_similar_urls(decision) == [
        "https://ekologus.pl/bdo/",
        "https://ekologus.pl/zielony-lad/",
    ]


def test_preflight_query_overlap_uses_gsc_query_count_and_primary_query() -> None:
    decision = _decision(query_count=4, primary_query="bdo odpady")

    assert content_preflight_query_overlap(decision) == (
        "4 zapytań z GSC; główne zapytanie: bdo odpady."
    )


def test_preflight_query_overlap_explains_missing_overlap() -> None:
    decision = _decision(query_count=0, primary_query=None)

    assert content_preflight_query_overlap(decision) == (
        "Brak potwierdzonych wspólnych zapytań."
    )
