from __future__ import annotations

from wilq.content.preflight.vendor_read import (
    content_blocker_reason,
    content_vendor_read_blocker_decision,
    refresh_or_connector_evidence_ids,
)
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus


def _refresh(
    connector_id: str,
    *,
    summary: str = "Odczyt wykonany.",
    errors: list[str] | None = None,
    evidence_ids: list[str] | None = None,
) -> ConnectorRefreshRun:
    return ConnectorRefreshRun(
        id=f"refresh_{connector_id}",
        connector_id=connector_id,
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.blocked if errors else ConnectorRefreshStatus.completed,
        summary=summary,
        errors=errors or [],
        evidence_ids=evidence_ids or [],
    )


def test_content_blocker_reason_prefers_refresh_error_then_summary() -> None:
    refreshes = [
        _refresh(
            "google_search_console",
            summary="Odczyt GSC niepełny.",
            errors=["GSC token wygasł."],
        ),
        _refresh("wordpress_ekologus", summary="WordPress bez wpisów."),
    ]

    assert content_blocker_reason(refreshes, "google_search_console") == "GSC token wygasł."
    assert content_blocker_reason(refreshes, "wordpress_ekologus") == "WordPress bez wpisów."


def test_refresh_or_connector_evidence_ids_falls_back_to_connector_evidence() -> None:
    assert refresh_or_connector_evidence_ids([], "google_search_console") == [
        "ev_connector_google_search_console_status"
    ]
    assert refresh_or_connector_evidence_ids(
        [_refresh("wordpress_ekologus", evidence_ids=["ev_wp_latest"])],
        "wordpress_ekologus",
    ) == ["ev_wp_latest"]


def test_content_vendor_read_blocker_decision_requires_gsc_and_wordpress_before_content() -> None:
    decision = content_vendor_read_blocker_decision(
        [
            _refresh("google_search_console", evidence_ids=["ev_gsc_refresh"]),
            _refresh("wordpress_ekologus", summary="WordPress bez odczytu."),
        ],
        ["act_prepare_content_refresh_queue"],
        knowledge_card_ids=("card_gsc_seo_content_playbook",),
        expert_rule_ids=("seo_query_page_matrix_v1",),
    )

    assert decision.id == "content_block_vendor_read"
    assert decision.decision_type == "block_until_vendor_read"
    assert decision.status == "blocked"
    assert decision.metric_tiles == {"blokady": 2}
    assert decision.source_connectors == ["google_search_console", "wordpress_ekologus"]
    assert decision.evidence_ids == ["ev_gsc_refresh"]
    assert decision.action_ids == ["act_prepare_content_refresh_queue"]
    assert decision.knowledge_card_ids == ["card_gsc_seo_content_playbook"]
    assert "rekomendacja bez danych źródłowych" in decision.blocked_claims
    assert "WordPress bez odczytu." in decision.rationale
