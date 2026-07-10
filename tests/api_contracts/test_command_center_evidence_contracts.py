from __future__ import annotations

from wilq.briefing.command_center import _source_connectors_with_evidence


def test_command_center_source_connectors_follow_evidence_ids() -> None:
    source_connectors = _source_connectors_with_evidence(
        [
            "ahrefs",
            "google_search_console",
            "wordpress_ekologus",
            "wordpress_sklep",
        ],
        [
            "ev_refresh_refresh_google_analytics_4_action_test",
            "ev_connector_google_ads_status",
        ],
    )

    assert source_connectors == [
        "ahrefs",
        "google_search_console",
        "wordpress_ekologus",
        "wordpress_sklep",
        "google_analytics_4",
        "google_ads",
    ]
