"""Scenario seed for evidence-backed cross-source action candidates."""

from __future__ import annotations

from pathlib import Path

import pytest

from wilq.connectors.vendor import VendorMetricFact
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus
from wilq.storage.metric_store import metric_store


def seed_action_candidate_metric_facts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "action_candidates.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "action_candidates.duckdb"))
    detailed_facts_by_run = _detailed_facts_by_run()

    for run in _candidate_refresh_runs():
        metric_store().save_connector_refresh_metrics(
            run,
            detailed_facts=detailed_facts_by_run.get(run.id),
        )


def _candidate_refresh_runs() -> list[ConnectorRefreshRun]:
    return [
        ConnectorRefreshRun(
            id="refresh_google_merchant_center_action_test",
            connector_id="google_merchant_center",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_google_merchant_center_action_test"],
            metric_summary={
                "total_products": 10900,
                "active_products": 12,
                "disapproved_products": 3,
                "item_level_issue_count": 3,
            },
            summary="Merchant Center action candidate metric seed.",
        ),
        ConnectorRefreshRun(
            id="refresh_google_analytics_4_action_test",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_google_analytics_4_action_test"],
            metric_summary={"active_users": 20, "sessions": 30},
            summary="GA4 action candidate metric seed.",
        ),
        ConnectorRefreshRun(
            id="refresh_wordpress_ekologus_action_test",
            connector_id="wordpress_ekologus",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_wordpress_ekologus_action_test"],
            metric_summary={"content_object_count": 16, "pages_total": 4},
            summary="WordPress action candidate metric seed.",
        ),
        ConnectorRefreshRun(
            id="refresh_google_search_console_action_test",
            connector_id="google_search_console",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_google_search_console_action_test"],
            metric_summary={"clicks": 12, "impressions": 120},
            summary="GSC action candidate metric seed.",
        ),
        ConnectorRefreshRun(
            id="refresh_ahrefs_action_test",
            connector_id="ahrefs",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_ahrefs_action_test"],
            metric_summary={"domain_rating": 90, "ahrefs_rank": 1450},
            summary="Ahrefs action candidate metric seed.",
        ),
    ]


def _detailed_facts_by_run() -> dict[str, list[VendorMetricFact]]:
    return {
        "refresh_google_search_console_action_test": _gsc_candidate_facts(),
        "refresh_google_analytics_4_action_test": _ga4_candidate_facts(),
        "refresh_wordpress_ekologus_action_test": _wordpress_candidate_facts(),
        "refresh_ahrefs_action_test": _ahrefs_candidate_facts(),
        "refresh_google_merchant_center_action_test": _merchant_candidate_facts(),
    }


def _gsc_candidate_facts() -> list[VendorMetricFact]:
    zielony_lad_dimensions = {
        "query": "zielony ład",
        "page": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
    }
    audyt_dimensions = {
        "query": "audyt środowiskowy",
        "page": "https://www.ekologus.pl/audyt-srodowiskowy/",
    }
    return [
        VendorMetricFact(name="clicks", value=12, dimensions=zielony_lad_dimensions),
        VendorMetricFact(name="impressions", value=120, dimensions=zielony_lad_dimensions),
        VendorMetricFact(name="ctr", value=0.1, dimensions=zielony_lad_dimensions),
        VendorMetricFact(name="average_position", value=2.1, dimensions=zielony_lad_dimensions),
        VendorMetricFact(name="clicks", value=2, dimensions=audyt_dimensions),
        VendorMetricFact(name="impressions", value=88, dimensions=audyt_dimensions),
    ]


def _ga4_candidate_facts() -> list[VendorMetricFact]:
    dimensions = {
        "landing_page": "/europejski-zielony-lad-co-to-takiego/",
        "source_medium": "google / cpc",
        "campaign_name": "Ekologus Ogólna",
    }
    return [
        VendorMetricFact(name="active_users", value=41, dimensions=dimensions),
        VendorMetricFact(name="sessions", value=54, dimensions=dimensions),
        VendorMetricFact(name="engagement_rate", value=0.12, dimensions=dimensions),
    ]


def _wordpress_candidate_facts() -> list[VendorMetricFact]:
    return [
        VendorMetricFact(
            name="content_object_seen",
            value=1,
            dimensions={
                "connector_id": "wordpress_ekologus",
                "site_kind": "primary",
                "content_type": "pages",
                "object_id": "42",
                "content_url": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
                "status": "publish",
                "modified_gmt": "2026-06-15T10:00:00",
            },
        ),
        VendorMetricFact(
            name="content_object_seen",
            value=1,
            dimensions={
                "connector_id": "wordpress_ekologus",
                "site_kind": "primary",
                "content_type": "pages",
                "object_id": "84",
                "content_url": "https://www.ekologus.pl/audyt-srodowiskowy/",
                "title": "Audyt środowiskowy",
                "status": "publish",
                "modified_gmt": "2026-06-16T10:00:00",
            },
        ),
    ]


def _ahrefs_candidate_facts() -> list[VendorMetricFact]:
    return [
        VendorMetricFact(
            name="ahrefs_content_gap_count",
            value=1,
            dimensions={
                "gap_type": "content_gap",
                "keyword": "audyt środowiskowy",
                "competitor_domain": "denios.pl",
                "source_url": "https://www.denios.pl/audyt-srodowiskowy/",
            },
        ),
        VendorMetricFact(
            name="ahrefs_top_page_gap_count",
            value=1,
            dimensions={
                "gap_type": "top_page_gap",
                "keyword": "beczka",
                "competitor_domain": "denios.pl",
                "source_url": "https://www.denios.pl/beczki/",
            },
        ),
        VendorMetricFact(
            name="ahrefs_competitor_page_count",
            value=2207,
            dimensions={
                "gap_type": "competitor_page",
                "competitor_domain": "cuk.pl",
            },
        ),
    ]


def _merchant_candidate_facts() -> list[VendorMetricFact]:
    return [
        VendorMetricFact(
            name="issue_product_count",
            value=3,
            dimensions={
                "country": "PL",
                "severity": "DISAPPROVED",
                "resolution": "MERCHANT_ACTION",
                "issue_type": "missing_image",
                "issue_title": "Missing image",
                "affected_attribute": "image_link",
            },
        ),
        VendorMetricFact(
            name="expiring_products",
            value=2,
            dimensions={"country": "PL", "reporting_context": "SHOPPING_ADS"},
        ),
    ]
