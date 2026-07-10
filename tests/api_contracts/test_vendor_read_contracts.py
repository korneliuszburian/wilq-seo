"""Non-Ads vendor-read API contract tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests._contract_support.api_client import client
from tests._contract_support.env import (
    clear_ahrefs_env,
    clear_google_service_env,
    clear_localo_env,
    clear_wordpress_env,
)
from wilq.connectors.ahrefs.client import refresh_ahrefs_domain_rating
from wilq.connectors.google_analytics_4.client import refresh_ga4_behavior_summary
from wilq.connectors.google_search_console.client import refresh_search_console_site_summary
from wilq.connectors.google_sheets.client import refresh_google_sheets_review_surface
from wilq.connectors.localo.client import (
    _competitor_visibility_summary,
    refresh_localo_visibility_summary,
)
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.connectors.wordpress.client import refresh_wordpress_content_inventory
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRequest, ConnectorRefreshStatus


def test_gsc_vendor_read_uses_search_analytics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setattr(
        "wilq.connectors.google_search_console.client.google_access_token",
        lambda scopes: "gsc-access-token",
    )
    monkeypatch.setattr(
        "wilq.connectors.google_search_console.client._default_availability_range",
        lambda: ("2026-06-19", "2026-06-28"),
    )

    seen_requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "searchconsole.googleapis.com"
        assert (
            request.url.path == "/webmasters/v3/sites/sc-domain:ekologus.pl/searchAnalytics/query"
        )
        assert request.headers["authorization"] == "Bearer gsc-access-token"
        body = json.loads(request.content.decode())
        assert "startDate" in body
        assert "endDate" in body
        assert body["type"] == "web"
        seen_requests.append(body)
        if body["dimensions"] == ["date"]:
            assert body["rowLimit"] == 10
            return httpx.Response(
                200,
                json={
                    "rows": [
                        {
                            "keys": ["2026-06-27"],
                            "clicks": 10,
                            "impressions": 100,
                            "ctr": 0.1,
                            "position": 5.0,
                        },
                        {
                            "keys": ["2026-06-28"],
                            "clicks": 12,
                            "impressions": 120,
                            "ctr": 0.1,
                            "position": 4.5,
                        },
                    ]
                },
            )
        if body["dimensions"] == ["country", "device"]:
            assert body["aggregationType"] == "byProperty"
            assert body["rowLimit"] == 25000
            assert body["startDate"] == "2026-06-28"
            assert body["endDate"] == "2026-06-28"
            return httpx.Response(
                200,
                json={
                    "rows": [
                        {
                            "keys": ["pol", "DESKTOP"],
                            "clicks": 200,
                            "impressions": 1000,
                            "ctr": 0.2,
                            "position": 3.0,
                        },
                        {
                            "keys": ["pol", "MOBILE"],
                            "clicks": 100,
                            "impressions": 1000,
                            "ctr": 0.1,
                            "position": 5.0,
                        },
                    ]
                },
            )
        assert body["dimensions"] == ["query", "page"]
        assert body["rowLimit"] == 1000
        assert body["startDate"] == "2026-06-28"
        assert body["endDate"] == "2026-06-28"
        assert body["startRow"] == 0
        return httpx.Response(
            200,
            json={
                "rows": [
                    {
                        "keys": [
                            f"odpady przemysłowe {index}",
                            f"https://ekologus.pl/oferta/{index}/",
                        ],
                        "clicks": 1,
                        "impressions": 10,
                        "ctr": 0.1,
                        "position": 4.5,
                    }
                    for index in range(250)
                ]
                + [
                    {
                        "keys": ["odpady przemysłowe", "https://ekologus.pl/oferta/"],
                        "clicks": 12,
                        "impressions": 120,
                        "ctr": 0.1,
                        "position": 4.5,
                    }
                ],
            },
        )

    result = refresh_search_console_site_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary["row_count"] == 251
    assert result.metric_summary["clicks"] == 262
    assert result.metric_summary["impressions"] == 2620
    assert result.metric_summary["ctr"] == 0.1
    assert result.metric_summary["average_position"] == 4.5
    assert result.metric_summary["date_start"] == "2026-06-28"
    assert result.metric_summary["date_end"] == "2026-06-28"
    assert result.metric_summary["data_availability_checked"] == "true"
    assert result.metric_summary["date_availability_status"] == "available"
    assert result.metric_summary["availability_date_start"] <= "2026-06-28"
    assert result.metric_summary["availability_date_end"] >= "2026-06-28"
    assert result.metric_summary["query_page_row_limit"] == 1000
    assert result.metric_summary["query_page_max_rows"] == 1000
    assert result.metric_summary["query_page_rows_truncated"] == "false"
    assert result.metric_summary["search_type"] == "web"
    assert result.metric_summary["detail_dimensions"] == "query,page"
    assert result.metric_summary["detail_data_completeness"] == "partial_possible"
    assert result.metric_summary["aggregate_date_start"] == "2026-06-28"
    assert result.metric_summary["aggregate_date_end"] == "2026-06-28"
    assert result.metric_summary["aggregate_dimensions"] == "country,device"
    assert result.metric_summary["aggregate_aggregation_type"] == "byProperty"
    assert (
        result.metric_summary["aggregate_data_completeness"]
        == "aggregate_without_query_page_dimensions"
    )
    assert result.metric_summary["aggregate_row_count"] == 2
    assert result.metric_summary["aggregate_clicks"] == 300
    assert result.metric_summary["aggregate_impressions"] == 2000
    assert result.metric_summary["aggregate_ctr"] == 0.15
    assert result.metric_summary["aggregate_average_position"] == 4.0
    assert [request["dimensions"] for request in seen_requests] == [
        ["date"],
        ["country", "device"],
        ["query", "page"],
    ]
    assert [request.get("startRow") for request in seen_requests[2:]] == [0]
    assert result.metric_facts[0].name == "clicks"
    assert result.metric_facts[0].value == 1
    assert result.metric_facts[0].dimensions == {
        "query": "odpady przemysłowe 0",
        "page": "https://ekologus.pl/oferta/0/",
    }


def test_ga4_vendor_read_uses_run_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GA4_PROPERTY_ID", "properties/411974093")
    monkeypatch.setattr(
        "wilq.connectors.google_analytics_4.client.google_access_token",
        lambda scopes: "ga4-access-token",
    )

    requests_seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "analyticsdata.googleapis.com"
        assert request.url.path == "/v1beta/properties/411974093:runReport"
        assert request.headers["authorization"] == "Bearer ga4-access-token"
        body = json.loads(request.content.decode())
        requests_seen.append(body)
        dimensions = [dimension["name"] for dimension in body["dimensions"]]
        if dimensions == [
            "landingPagePlusQueryString",
            "sessionSourceMedium",
            "sessionCampaignName",
        ]:
            assert [metric["name"] for metric in body["metrics"]] == [
                "activeUsers",
                "sessions",
                "screenPageViews",
                "eventCount",
                "engagementRate",
                "keyEvents",
                "ecommercePurchases",
                "purchaseRevenue",
                "totalRevenue",
                "transactions",
            ]
            assert body["limit"] == "10"
            return httpx.Response(
                200,
                json={
                    "dimensionHeaders": [
                        {"name": "landingPagePlusQueryString"},
                        {"name": "sessionSourceMedium"},
                        {"name": "sessionCampaignName"},
                    ],
                    "metricHeaders": [
                        {"name": "activeUsers"},
                        {"name": "sessions"},
                        {"name": "screenPageViews"},
                        {"name": "eventCount"},
                        {"name": "engagementRate"},
                        {"name": "keyEvents"},
                        {"name": "ecommercePurchases"},
                        {"name": "purchaseRevenue"},
                        {"name": "totalRevenue"},
                        {"name": "transactions"},
                    ],
                    "rows": [
                        {
                            "dimensionValues": [
                                {"value": "/oferta/"},
                                {"value": "google / cpc"},
                                {"value": "PMax odpady"},
                            ],
                            "metricValues": [
                                {"value": "20"},
                                {"value": "30"},
                                {"value": "50"},
                                {"value": "75"},
                                {"value": "0.62"},
                                {"value": "3"},
                                {"value": "1"},
                                {"value": "125.50"},
                                {"value": "150.75"},
                                {"value": "1"},
                            ],
                        }
                    ],
                },
            )
        assert dimensions == ["itemId", "itemName"]
        assert [metric["name"] for metric in body["metrics"]] == [
            "itemsViewed",
            "itemsAddedToCart",
            "itemsCheckedOut",
            "itemsPurchased",
            "itemRevenue",
        ]
        assert body["limit"] == "50"
        return httpx.Response(
            200,
            json={
                "dimensionHeaders": [{"name": "itemId"}, {"name": "itemName"}],
                "metricHeaders": [
                    {"name": "itemsViewed"},
                    {"name": "itemsAddedToCart"},
                    {"name": "itemsCheckedOut"},
                    {"name": "itemsPurchased"},
                    {"name": "itemRevenue"},
                ],
                "rows": [
                    {
                        "dimensionValues": [
                            {"value": "pl~PL~gla_107394"},
                            {"value": "Sorbent chemiczny 10 kg"},
                        ],
                        "metricValues": [
                            {"value": "9"},
                            {"value": "4"},
                            {"value": "3"},
                            {"value": "2"},
                            {"value": "410.25"},
                        ],
                    }
                ],
            },
        )

    result = refresh_ga4_behavior_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary["row_count"] == 1
    assert result.metric_summary["active_users"] == 20
    assert result.metric_summary["sessions"] == 30
    assert result.metric_summary["screen_page_views"] == 50
    assert result.metric_summary["event_count"] == 75
    assert result.metric_summary["engagement_rate"] == 0.62
    assert result.metric_summary["key_events"] == 3
    assert result.metric_summary["ecommerce_purchases"] == 1
    assert result.metric_summary["purchase_revenue"] == 125.50
    assert result.metric_summary["total_revenue"] == 150.75
    assert result.metric_summary["transactions"] == 1
    assert result.metric_summary["ga4_item_product_row_count"] == 1
    assert result.metric_summary["ga4_items_viewed"] == 9
    assert result.metric_summary["ga4_items_added_to_cart"] == 4
    assert result.metric_summary["ga4_items_checked_out"] == 3
    assert result.metric_summary["ga4_items_purchased"] == 2
    assert result.metric_summary["ga4_item_revenue"] == 410.25
    assert result.metric_facts[0].name == "active_users"
    assert result.metric_facts[0].value == 20
    assert result.metric_facts[0].dimensions == {
        "landing_page": "/oferta/",
        "source_medium": "google / cpc",
        "campaign_name": "PMax odpady",
    }
    facts_by_name = {fact.name: fact for fact in result.metric_facts}
    assert facts_by_name["key_events"].value == 3
    assert facts_by_name["ecommerce_purchases"].value == 1
    assert facts_by_name["purchase_revenue"].value == 125.50
    assert facts_by_name["total_revenue"].value == 150.75
    assert facts_by_name["transactions"].value == 1
    assert facts_by_name["item_purchases"].value == 2
    assert facts_by_name["item_purchases"].dimensions == {
        "item_id": "pl~PL~gla_107394",
        "item_name": "Sorbent chemiczny 10 kg",
    }
    assert facts_by_name["item_revenue"].value == 410.25
    assert len(requests_seen) == 2


def test_google_first_party_vendor_reads_route_through_refresh_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "google_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")
    service_account_json = tmp_path / "sa.json"
    service_account_json.write_text('{"type":"service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_search_console_site_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="GSC read completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"clicks": 12, "impressions": 120},
        ),
    )
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ga4_behavior_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="GA4 read completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"active_users": 20, "sessions": 30},
        ),
    )

    gsc_response = client.post(
        "/api/connectors/google_search_console/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )
    ga4_response = client.post(
        "/api/connectors/google_analytics_4/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert gsc_response.status_code == 200
    assert ga4_response.status_code == 200
    assert gsc_response.json()["metric_summary"] == {"clicks": 12, "impressions": 120}
    assert ga4_response.json()["metric_summary"] == {"active_users": 20, "sessions": 30}


def test_google_sheets_vendor_read_uses_spreadsheets_get(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID", "sheet-id")
    monkeypatch.setattr(
        "wilq.connectors.google_sheets.client.google_access_token",
        lambda scopes: "sheets-access-token",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "sheets.googleapis.com"
        assert request.url.path == "/v4/spreadsheets/sheet-id"
        assert request.headers["authorization"] == "Bearer sheets-access-token"
        assert "sheets(properties(" in request.url.params["fields"]
        assert request.url.params["includeGridData"] == "false"
        return httpx.Response(
            200,
            json={
                "sheets": [
                    {
                        "properties": {
                            "sheetId": 1,
                            "gridProperties": {"rowCount": 100, "columnCount": 8},
                        }
                    },
                    {
                        "properties": {
                            "sheetId": 2,
                            "gridProperties": {"rowCount": 20, "columnCount": 4},
                        }
                    },
                ]
            },
        )

    result = refresh_google_sheets_review_surface(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary == {
        "api": "google_sheets_spreadsheets_get",
        "spreadsheet_configured": 1,
        "sheet_count": 2,
        "total_grid_rows": 120,
        "total_grid_columns": 12,
        "max_grid_rows": 100,
        "max_grid_columns": 8,
    }


def test_google_sheets_vendor_read_is_blocked_when_disabled_by_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "sheets_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID", "sheet-id")
    response = client.post(
        "/api/connectors/google_sheets/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "blocked"
    assert run["external_call_attempted"] is False
    assert run["vendor_data_collected"] is False
    assert run["metric_summary"] == {}
    assert "disabled by current product scope" in run["summary"]


def test_ahrefs_vendor_read_uses_site_explorer_domain_rating(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    monkeypatch.setenv("AHREFS_TARGET", "https://www.ekologus.pl/oferta")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.host == "api.ahrefs.com"
        assert request.headers["authorization"] == "Bearer ahrefs-token-test"
        assert request.headers["accept"] == "application/json"
        assert request.url.params["output"] == "json"
        if request.url.path == "/v3/site-explorer/domain-rating":
            assert len(request.url.params["date"]) == 10
            assert request.url.params["target"] == "ekologus.pl"
            return httpx.Response(
                200,
                json={"domain_rating": {"ahrefs_rank": 1450, "domain_rating": 90.0}},
            )
        if request.url.path == "/v3/site-explorer/organic-competitors":
            assert len(request.url.params["date"]) == 10
            assert request.url.params["target"] == "ekologus.pl"
            assert request.url.params["mode"] == "subdomains"
            assert request.url.params["country"] == "pl"
            assert request.url.params["limit"] == "10"
            assert "competitor_domain" in request.url.params["select"]
            return httpx.Response(
                200,
                json={
                    "competitors": [
                        {
                            "competitor_domain": None,
                            "competitor_url": "https://konkurent.pl/bdo/",
                            "keywords_common": 8,
                            "keywords_competitor": 42,
                            "keywords_target": 12,
                            "pages": 7,
                            "share": 0.17,
                        }
                    ]
                },
            )
        if request.url.path == "/v3/site-explorer/top-pages":
            assert len(request.url.params["date"]) == 10
            assert request.url.params["target"] == "konkurent.pl"
            assert request.url.params["mode"] == "subdomains"
            assert request.url.params["country"] == "pl"
            assert request.url.params["limit"] == "3"
            assert request.url.params["order_by"] == "sum_traffic:desc"
            assert "top_keyword" in request.url.params["select"]
            return httpx.Response(
                200,
                json={
                    "pages": [
                        {
                            "raw_url": "https://konkurent.pl/top-bdo/",
                            "top_keyword": "bdo szkolenie",
                            "sum_traffic": 121,
                            "keywords": 31,
                            "referring_domains": 4,
                            "top_keyword_best_position": 2,
                            "top_keyword_country": "pl",
                        }
                    ]
                },
            )
        if request.url.path == "/v3/site-explorer/organic-keywords":
            assert len(request.url.params["date"]) == 10
            assert request.url.params["country"] == "pl"
            assert request.url.params["order_by"] == "sum_traffic:desc"
            assert "keyword" in request.url.params["select"]
            if request.url.params["target"] == "https://konkurent.pl/top-bdo/":
                assert request.url.params["mode"] == "exact"
                assert request.url.params["limit"] == "3"
                return httpx.Response(
                    200,
                    json={
                        "keywords": [
                            {
                                "keyword": "bdo szkolenie online",
                                "best_position": 3,
                                "best_position_url": "https://konkurent.pl/top-bdo/",
                                "volume": 150,
                                "sum_traffic": 24,
                                "keyword_difficulty": 8,
                                "cpc": 1.21,
                                "is_branded": False,
                                "is_commercial": True,
                                "is_informational": False,
                                "is_local": False,
                                "is_transactional": True,
                            }
                        ]
                    },
                )
            assert request.url.params["target"] == "ekologus.pl"
            assert request.url.params["mode"] == "subdomains"
            assert request.url.params["limit"] == "1000"
            return httpx.Response(
                200,
                json={
                    "keywords": [
                        {"keyword": "ekologus"},
                        {"keyword": "audyt środowiskowy"},
                    ]
                },
            )
        assert request.url.path == "/v3/site-explorer/refdomains"
        assert request.url.params["mode"] == "subdomains"
        assert request.url.params["history"] == "live"
        assert request.url.params["order_by"] == "domain_rating:desc"
        assert "domain" in request.url.params["select"]
        if request.url.params["target"] == "ekologus.pl":
            assert request.url.params["limit"] == "1000"
            return httpx.Response(
                200,
                json={"refdomains": [{"domain": "shared-source.pl", "domain_rating": 44}]},
            )
        assert request.url.params["target"] == "konkurent.pl"
        assert request.url.params["limit"] == "10"
        return httpx.Response(
            200,
            json={
                "refdomains": [
                    {"domain": "shared-source.pl", "domain_rating": 44},
                    {
                        "domain": "gap-source.pl",
                        "domain_rating": 66,
                        "links_to_target": 3,
                        "dofollow_links": 2,
                        "dofollow_refdomains": 1,
                        "traffic_domain": 1200,
                        "positions_source_domain": 82,
                        "first_seen": "2025-01-02",
                        "last_seen": "2026-06-19",
                        "is_spam": False,
                        "is_root_domain": True,
                    },
                ]
            },
        )

    result = refresh_ahrefs_domain_rating(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary == {
        "api": "ahrefs_site_explorer_domain_rating",
        "date": result.metric_summary["date"],
        "target_source": "process_env",
        "domain_rating": 90.0,
        "ahrefs_rank": 1450,
        "organic_competitor_read_status": "completed",
        "organic_competitor_rows": 1,
        "organic_competitor_country": "pl",
        "organic_competitor_mode": "subdomains",
        "top_pages_by_competitor_read_status": "completed",
        "top_pages_by_competitor_rows": 1,
        "top_pages_by_competitor_competitors": 1,
        "top_pages_by_competitor_country": "pl",
        "top_pages_by_competitor_mode": "subdomains",
        "organic_keywords_by_url_read_status": "completed",
        "organic_keywords_by_url_rows": 1,
        "organic_keywords_by_url_urls": 1,
        "organic_keywords_by_url_country": "pl",
        "organic_keywords_by_url_mode": "exact",
        "organic_keywords_by_url_keyword_limit": 3,
        "content_gap_read_status": "completed",
        "content_gap_rows": 1,
        "content_gap_target_keywords": 2,
        "content_gap_target_keyword_limit": 1000,
        "content_gap_competitor_keywords": 1,
        "content_gap_mode": "subdomains",
        "backlink_gap_read_status": "completed",
        "backlink_gap_rows": 1,
        "backlink_gap_competitors": 1,
        "backlink_gap_target_refdomains": 1,
        "backlink_gap_target_refdomain_limit": 1000,
        "backlink_gap_competitor_refdomain_limit": 10,
        "backlink_gap_mode": "subdomains",
        "backlink_gap_history": "live",
    }
    assert result.metric_facts == [
        VendorMetricFact(
            "ahrefs_competitor_page_count",
            7,
            {
                "gap_type": "competitor_page",
                "competitor_domain": "konkurent.pl",
                "source_url": "https://konkurent.pl/bdo/",
                "country": "pl",
                "target_mode": "subdomains",
                "keywords_common": "8",
                "keywords_competitor": "42",
                "keywords_target": "12",
                "share": "0.17",
            },
            period="ahrefs_organic_competitors",
        ),
        VendorMetricFact(
            "ahrefs_top_page_gap_count",
            1,
            {
                "gap_type": "top_page_gap",
                "competitor_domain": "konkurent.pl",
                "source_url": "https://konkurent.pl/top-bdo/",
                "keyword": "bdo szkolenie",
                "country": "pl",
                "target_mode": "subdomains",
                "sum_traffic": "121",
                "keywords": "31",
                "referring_domains": "4",
                "top_keyword_best_position": "2",
                "top_keyword_country": "pl",
            },
            period="ahrefs_top_pages",
        ),
        VendorMetricFact(
            "ahrefs_organic_keyword_gap_count",
            1,
            {
                "gap_type": "organic_keyword_gap",
                "competitor_domain": "konkurent.pl",
                "source_url": "https://konkurent.pl/top-bdo/",
                "keyword": "bdo szkolenie online",
                "country": "pl",
                "target_mode": "exact",
                "best_position": "3",
                "best_position_url": "https://konkurent.pl/top-bdo/",
                "volume": "150",
                "sum_traffic": "24",
                "keyword_difficulty": "8",
                "cpc": "1.21",
                "is_branded": "False",
                "is_commercial": "True",
                "is_informational": "False",
                "is_local": "False",
                "is_transactional": "True",
            },
            period="ahrefs_organic_keywords",
        ),
        VendorMetricFact(
            "ahrefs_content_gap_count",
            1,
            {
                "gap_type": "content_gap",
                "competitor_domain": "konkurent.pl",
                "source_url": "https://konkurent.pl/top-bdo/",
                "target_domain": "ekologus.pl",
                "keyword": "bdo szkolenie online",
                "country": "pl",
                "target_mode": "subdomains",
                "competitor_target_mode": "exact",
                "best_position": "3",
                "best_position_url": "https://konkurent.pl/top-bdo/",
                "volume": "150",
                "sum_traffic": "24",
                "keyword_difficulty": "8",
                "cpc": "1.21",
                "is_branded": "False",
                "is_commercial": "True",
                "is_informational": "False",
                "is_local": "False",
                "is_transactional": "True",
                "target_keyword_sample_size": "2",
                "target_keyword_limit": "1000",
            },
            period="ahrefs_content_gap",
        ),
        VendorMetricFact(
            "ahrefs_referring_domain_gap_count",
            1,
            {
                "gap_type": "backlink_gap",
                "competitor_domain": "konkurent.pl",
                "source_url": "gap-source.pl",
                "referring_domain": "gap-source.pl",
                "target_domain": "ekologus.pl",
                "target_mode": "subdomains",
                "history": "live",
                "domain_rating": "66",
                "links_to_target": "3",
                "dofollow_links": "2",
                "dofollow_refdomains": "1",
                "traffic_domain": "1200",
                "positions_source_domain": "82",
                "first_seen": "2025-01-02",
                "last_seen": "2026-06-19",
                "is_spam": "False",
                "is_root_domain": "True",
                "target_refdomain_sample_size": "1",
                "target_refdomain_limit": "1000",
            },
            period="ahrefs_refdomains_gap",
        ),
    ]
    assert [request.url.path for request in requests] == [
        "/v3/site-explorer/domain-rating",
        "/v3/site-explorer/organic-competitors",
        "/v3/site-explorer/top-pages",
        "/v3/site-explorer/organic-keywords",
        "/v3/site-explorer/organic-keywords",
        "/v3/site-explorer/refdomains",
        "/v3/site-explorer/refdomains",
    ]
    serialized = json.dumps(result.metric_summary)
    assert "ahrefs-token-test" not in serialized
    assert "ekologus.pl" not in serialized


def test_ahrefs_vendor_read_prefers_marketing_site_over_wordpress_runtime_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    monkeypatch.setenv("MIS_PRIMARY_SITE_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.dev.proudsite.pl")
    requested_targets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_targets.append(request.url.params["target"])
        if request.url.path == "/v3/site-explorer/domain-rating":
            return httpx.Response(
                200,
                json={"domain_rating": {"ahrefs_rank": 1450, "domain_rating": 90.0}},
            )
        return httpx.Response(200, json={"competitors": []})

    result = refresh_ahrefs_domain_rating(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert requested_targets == ["ekologus.pl", "ekologus.pl"]
    assert result.metric_summary["target_source"] == "process_env"


def test_ahrefs_vendor_read_routes_through_refresh_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ahrefs_domain_rating",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Ahrefs domain rating completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"domain_rating": 90.0, "ahrefs_rank": 1450},
        ),
    )

    response = client.post(
        "/api/connectors/ahrefs/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["metric_summary"] == {"domain_rating": 90.0, "ahrefs_rank": 1450}


def test_localo_vendor_read_routes_through_mcp_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_localo_visibility_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="Localo MCP endpoint reachable; OAuth authorization required.",
            external_call_attempted=True,
            vendor_data_collected=False,
            metric_summary={
                "api": "localo_mcp_oauth_probe",
                "mcp_initialize_status": 401,
                "authorization_code_supported": 1,
                "pkce_s256_supported": 1,
                "access_token_present": 1,
            },
            errors=["Localo OAuth authorization is incomplete."],
        ),
    )

    response = client.post(
        "/api/connectors/localo/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "blocked"
    assert run["external_call_attempted"] is True
    assert run["vendor_data_collected"] is False
    assert run["metric_summary"]["api"] == "localo_mcp_oauth_probe"
    assert run["metric_summary"]["access_token_present"] == 1


def test_localo_vendor_read_collects_read_only_aggregate_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://api.localo.com/.well-known/oauth-protected-resource":
            return httpx.Response(
                200,
                json={"authorization_servers": ["https://api.localo.com"]},
            )
        if str(request.url) == "https://api.localo.com/.well-known/oauth-authorization-server":
            return httpx.Response(
                200,
                json={
                    "grant_types_supported": ["authorization_code"],
                    "code_challenge_methods_supported": ["S256"],
                },
            )
        assert str(request.url) == "https://api.localo.com/api/mcp"
        assert request.headers["authorization"] == "Bearer localo-access-test"
        payload = json.loads(request.content.decode())
        method = payload["method"]
        if method == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": {}})
        if method == "notifications/initialized":
            return httpx.Response(204)
        assert method == "tools/call"
        arguments = payload["params"]["arguments"]
        query = arguments["query"]
        variables = arguments["variables"]
        if "placesList" in query:
            assert variables == {"input": {"active": True, "pageNo": 1, "pageSize": 20}}
            return _localo_mcp_text_response(
                {
                    "data": {
                        "placesList": {
                            "places": [{"id": "place-one"}, {"id": "place-two"}],
                            "placesTags": [],
                        }
                    }
                }
            )
        if "activePlaceKeywords" in query:
            if variables["placeId"] == "place-one":
                return _localo_mcp_text_response(
                    {
                        "data": {
                            "place": {
                                "latestPlaceSnapshot": {"rating": 4.5, "reviewsCount": 10},
                                "activePlaceKeywords": [
                                    {
                                        "visibility": {"current": 50, "change": 2},
                                        "ahrefsOverview": {"volume": 100},
                                        "latestGrids": [{"orderedPlacePosition": 3}],
                                    },
                                    {
                                        "visibility": {"current": 70, "change": -1},
                                        "ahrefsOverview": {"volume": 200},
                                        "latestGrids": [{"orderedPlacePosition": 5}],
                                    },
                                ],
                            }
                        }
                    }
                )
            return _localo_mcp_text_response(
                {
                    "data": {
                        "place": {
                            "latestPlaceSnapshot": {"rating": 4.0, "reviewsCount": 20},
                            "activePlaceKeywords": [
                                {
                                    "visibility": {"current": 30, "change": 0},
                                    "ahrefsOverview": {"volume": 50},
                                    "latestGrids": [],
                                }
                            ],
                        }
                    }
                }
            )
        if "reviewsStats" in query:
            if variables["placeId"] == "place-one":
                return _localo_mcp_text_response(
                    {
                        "data": {
                            "reviewsStats": {
                                "reviewsCount": 10,
                                "repliedCount": 8,
                                "removedCount": 1,
                            }
                        }
                    }
                )
            return _localo_mcp_text_response(
                {
                    "data": {
                        "reviewsStats": {
                            "reviewsCount": 20,
                            "repliedCount": 10,
                            "removedCount": 2,
                        }
                    }
                }
            )
        if "googleMetricSeries" in query:
            metric = variables["args"]["metrics"][0]
            assert variables["args"]["placeId"] in {"place-one", "place-two"}
            assert variables["args"]["dateStart"]
            assert variables["args"]["dateEnd"]
            if metric in {
                "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
                "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
                "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
                "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
            }:
                return _localo_mcp_text_response(
                    {"data": {"googleMetricSeries": [{"value": 10}, {"value": 5}]}}
                )
            return _localo_mcp_text_response(
                {"data": {"googleMetricSeries": [{"value": 2}, {"value": 1}]}}
            )
        if "listPlaceActionTrackerFavoriteCompetitors" in query:
            if variables["placeId"] == "place-one":
                return _localo_mcp_text_response(
                    {
                        "data": {
                            "competitors": [
                                {"favorite": True, "changesCount": 3},
                                {"favorite": False, "changesCount": 1},
                            ]
                        }
                    }
                )
            return _localo_mcp_text_response(
                {"data": {"competitors": [{"favorite": True, "changesCount": 2}]}}
            )
        return httpx.Response(500, json={"error": "Unexpected Localo query"})

    result = refresh_localo_visibility_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read, reason="contract test"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.vendor_data_collected is True
    assert result.metric_summary["api"] == "localo_mcp_oauth_probe"
    assert result.metric_summary["localo_active_place_count"] == 2
    assert result.metric_summary["localo_tracked_keyword_count"] == 3
    assert result.metric_summary["localo_avg_visibility_current"] == 50.0
    assert result.metric_summary["localo_avg_visibility_change"] == 0.3333
    assert result.metric_summary["localo_avg_latest_grid_position"] == 4.0
    assert result.metric_summary["localo_total_keyword_volume"] == 350
    assert result.metric_summary["localo_reviews_count"] == 30
    assert result.metric_summary["localo_review_reply_rate"] == 0.6
    assert result.metric_summary["localo_gbp_impressions_total"] == 120
    assert result.metric_summary["localo_gbp_actions_total"] == 18
    assert result.metric_summary["localo_competitor_count"] == 3
    assert result.metric_summary["localo_favorite_competitor_count"] == 2
    assert result.metric_summary["localo_competitor_change_count"] == 6
    fact_by_name = {fact.name: fact for fact in result.metric_facts}
    assert fact_by_name["localo_active_place_count"].dimensions == {
        "contract": "place_inventory",
        "scope": "active_places",
    }
    assert fact_by_name["localo_avg_visibility_current"].dimensions["contract"] == (
        "local_rankings"
    )
    assert fact_by_name["localo_reviews_count"].dimensions["contract"] == "reviews"
    assert fact_by_name["localo_gbp_impressions_total"].dimensions["contract"] == ("gbp_visibility")
    assert fact_by_name["localo_competitor_count"].dimensions["contract"] == (
        "competitor_visibility"
    )
    serialized = json.dumps(
        {
            "summary": result.metric_summary,
            "facts": [fact.__dict__ for fact in result.metric_facts],
        },
        ensure_ascii=False,
    )
    assert "place-one" not in serialized
    assert "place-two" not in serialized
    assert "localo-access-test" not in serialized
    assert "localo-token-test" not in serialized


def _localo_mcp_text_response(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload),
                    }
                ]
            },
        },
    )


def test_localo_competitor_summary_treats_graphql_errors_as_missing_optional_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["method"] == "tools/call"
        return _localo_mcp_text_response(
            {"errors": [{"message": "Competitor visibility is unavailable for this place."}]}
        )

    summary = _competitor_visibility_summary(
        httpx.Client(transport=httpx.MockTransport(handler)),
        "localo-access-test",
        "place-without-competitor-contract",
    )

    assert summary == {
        "competitor_count": 0,
        "favorite_competitor_count": 0,
        "competitor_change_count": 0,
    }


def test_wordpress_vendor_read_uses_rest_content_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_wordpress_env(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://ekologus.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "ekologus.test"
        if request.url.path == "/wp-json/wp/v2/posts":
            assert request.headers["authorization"].startswith("Basic ")
            assert request.url.params["per_page"] == "100"
            assert (
                request.url.params["_fields"]
                == "id,status,modified_gmt,date_gmt,link,slug,title,content,acf,template"
            )
            return httpx.Response(
                200,
                headers={"X-WP-Total": "12"},
                json=[
                    {
                        "id": 1,
                        "status": "publish",
                        "modified_gmt": "2026-06-15T10:00:00",
                        "link": "https://ekologus.test/blog/remediacja/",
                        "title": {"rendered": "Remediacja środowiska"},
                    }
                ],
            )
        if request.url.path == "/wp-json/wp/v2/pages":
            assert request.headers["authorization"].startswith("Basic ")
            assert request.url.params["per_page"] == "100"
            assert (
                request.url.params["_fields"]
                == "id,status,modified_gmt,date_gmt,link,slug,title,content,acf,template"
            )
            return httpx.Response(
                200,
                headers={"X-WP-Total": "4"},
                json=[
                    {
                        "id": 2,
                        "status": "publish",
                        "modified_gmt": "2026-06-16T10:00:00",
                        "link": "https://ekologus.test/oferta/",
                        "title": {"rendered": "Oferta Ekologus"},
                    }
                ],
            )
        if request.url.path == "/wp-sitemap.xml":
            return httpx.Response(
                200,
                text=(
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    "<sitemap><loc>https://ekologus.test/page-sitemap.xml</loc>"
                    "<lastmod>2026-06-16T12:00:00+00:00</lastmod></sitemap>"
                    "</sitemapindex>"
                ),
            )
        if request.url.path == "/page-sitemap.xml":
            return httpx.Response(
                200,
                text=(
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    "<url><loc>https://ekologus.test/europejski-zielony-lad-co-to-takiego/</loc>"
                    "<lastmod>2026-06-16T12:00:00+00:00</lastmod></url>"
                    "</urlset>"
                ),
            )
        return httpx.Response(404)

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary == {
        "api": "wordpress_rest_and_sitemap_content_inventory",
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_object_count": 16,
        "posts_total": 12,
        "pages_total": 4,
        "sitemap_url_count": 1,
        "public_sitemap_url_count": 0,
        "latest_modified_gmt": "2026-06-16T10:00:00",
        "latest_post_modified_gmt": "2026-06-15T10:00:00",
        "latest_page_modified_gmt": "2026-06-16T10:00:00",
    }
    assert result.metric_facts[0].name == "content_object_count"
    assert result.metric_facts[0].value == 12
    assert result.metric_facts[0].dimensions == {
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_type": "posts",
    }
    content_url_fact = next(
        fact for fact in result.metric_facts if fact.name == "content_object_seen"
    )
    assert content_url_fact.value == 1
    expected_content_url_dimensions = {
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_type": "posts",
        "object_id": "1",
        "content_url": "https://ekologus.test/blog/remediacja/",
        "status": "publish",
        "modified_gmt": "2026-06-15T10:00:00",
        "title_or_h1": "Remediacja środowiska",
        "canonical_url": "",
        "inventory_source": "wordpress_rest",
    }
    for key, value in expected_content_url_dimensions.items():
        assert content_url_fact.dimensions[key] == value
    sitemap_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "content_object_seen"
        and fact.dimensions.get("inventory_source") == "sitemap"
    )
    assert sitemap_fact.value == 1
    expected_sitemap_dimensions = {
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_type": "sitemap",
        "object_id": "",
        "content_url": "https://ekologus.test/europejski-zielony-lad-co-to-takiego/",
        "status": "indexed",
        "modified_gmt": "2026-06-16T12:00:00+00:00",
        "title_or_h1": "",
        "canonical_url": "",
        "inventory_source": "sitemap",
    }
    for key, value in expected_sitemap_dimensions.items():
        assert sitemap_fact.dimensions[key] == value
    assert any(fact.name == "sitemap_url_count" for fact in result.metric_facts)


def test_wordpress_vendor_read_adds_public_production_sitemap_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_wordpress_env(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.dev.proudsite.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "ekologus.dev.proudsite.pl":
            if request.url.path == "/wp-json/wp/v2/posts":
                return httpx.Response(200, headers={"X-WP-Total": "0"}, json=[])
            if request.url.path == "/wp-json/wp/v2/pages":
                return httpx.Response(200, headers={"X-WP-Total": "0"}, json=[])
            if request.url.path == "/wp-sitemap.xml":
                return httpx.Response(404)
        if request.url.host == "www.ekologus.pl":
            if request.url.path == "/wp-sitemap.xml":
                return httpx.Response(404)
            if request.url.path == "/sitemap_index.xml":
                return httpx.Response(
                    200,
                    text=(
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                        "<sitemap><loc>https://www.ekologus.pl/post-sitemap.xml</loc>"
                        "<lastmod>2026-06-17T12:00:00+00:00</lastmod></sitemap>"
                        "</sitemapindex>"
                    ),
                )
            if request.url.path == "/post-sitemap.xml":
                return httpx.Response(
                    200,
                    text=(
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                        "<url><loc>https://www.ekologus.pl/"
                        "bdo-co-musi-wiedziec-przedsiebiorca/</loc>"
                        "<lastmod>2026-06-17T12:00:00+00:00</lastmod></url>"
                        "</urlset>"
                    ),
                )
            if request.url.path == "/bdo-co-musi-wiedziec-przedsiebiorca/":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/html; charset=utf-8"},
                    text=(
                        "<html><head>"
                        "<title>BDO - co musi wiedzieć przedsiębiorca?</title>"
                        '<link rel="canonical" href="https://www.ekologus.pl/'
                        'bdo-co-musi-wiedziec-przedsiebiorca/" />'
                        "</head><body><h1>BDO dla przedsiębiorcy</h1>"
                        "<h2>Obowiązki przedsiębiorcy</h2><h3>Rejestr BDO</h3>"
                        "</body></html>"
                    ),
                )
        return httpx.Response(404)

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.metric_summary["public_sitemap_url_count"] == 1
    public_sitemap_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "content_object_seen"
        and fact.dimensions.get("inventory_source") == "public_sitemap"
    )
    assert public_sitemap_fact.dimensions["content_url"] == (
        "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    )
    assert public_sitemap_fact.dimensions["title_or_h1"] == (
        "BDO - co musi wiedzieć przedsiębiorca?"
    )
    assert public_sitemap_fact.dimensions["canonical_url"] == (
        "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    )
    assert public_sitemap_fact.dimensions["section_heading_count"] == "2"
    assert json.loads(public_sitemap_fact.dimensions["section_headings_json"]) == [
        "Obowiązki przedsiębiorcy",
        "Rejestr BDO",
    ]
    assert any(fact.name == "public_sitemap_url_count" for fact in result.metric_facts)


def test_wordpress_vendor_read_routes_through_refresh_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_wordpress_env(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_wordpress_content_inventory",
        lambda connector_id, request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="WordPress inventory completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"content_object_count": 16, "posts_total": 12, "pages_total": 4},
        ),
    )

    response = client.post(
        "/api/connectors/wordpress_ekologus/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["metric_summary"] == {
        "content_object_count": 16,
        "posts_total": 12,
        "pages_total": 4,
    }
