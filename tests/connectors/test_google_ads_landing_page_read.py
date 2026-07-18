import json

import httpx
import pytest

from tests._contract_support.env import clear_google_ads_env
from wilq.connectors.google_ads.ad_landing_pages import (
    ADS_LANDING_ACTUAL_CLICKED,
    ADS_LANDING_IDENTITY,
    ADS_LANDING_MAPPING_STATUS,
    ADS_SEARCH_TERM_PAYLOAD_STATUS,
)
from wilq.connectors.google_ads.client import refresh_google_ads_campaign_summary
from wilq.connectors.vendor import VendorReadResult
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshStatus,
)


def test_google_ads_refresh_keeps_search_terms_live_when_landing_join_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
) -> None:
    result, queries = _run_refresh(monkeypatch, tmp_path, _search_term_row())

    assert result.status == ConnectorRefreshStatus.completed
    assert result.metric_summary[ADS_SEARCH_TERM_PAYLOAD_STATUS] == "ready"
    assert result.metric_summary["search_term_landing_mapped_row_count"] == 0
    assert result.metric_summary["search_term_landing_blocked_row_count"] == 1
    query = next(query for query in queries if "FROM search_term_view" in query)
    assert "metrics.clicks > 0" in query
    assert "expanded_landing_page_view.expanded_final_url" not in query
    click_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_term_clicks"
    )
    assert click_fact.period == "last_30_days"
    assert click_fact.dimensions[ADS_LANDING_MAPPING_STATUS] != "resolved"
    assert ADS_LANDING_ACTUAL_CLICKED not in click_fact.dimensions
    assert ADS_LANDING_IDENTITY not in click_fact.dimensions
    assert any(
        fact.name == ADS_SEARCH_TERM_PAYLOAD_STATUS and fact.value == "ready"
        for fact in result.metric_facts
    )


@pytest.mark.parametrize("malformed_case", ["missing_metrics", "infinite_metric"])
def test_google_ads_refresh_blocks_malformed_search_term_row_without_partial_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
    malformed_case: str,
) -> None:
    incomplete_row = _search_term_row()
    if malformed_case == "missing_metrics":
        incomplete_row.pop("metrics")
    else:
        metrics = incomplete_row["metrics"]
        assert isinstance(metrics, dict)
        metrics["conversionsValue"] = "Infinity"

    result, _ = _run_refresh(monkeypatch, tmp_path, incomplete_row)

    assert result.metric_summary[ADS_SEARCH_TERM_PAYLOAD_STATUS] == "blocked"
    assert result.metric_summary["search_term_row_count"] == 0
    assert not any(
        fact.name.startswith("search_term_")
        and fact.name != ADS_SEARCH_TERM_PAYLOAD_STATUS
        for fact in result.metric_facts
    )
    status_facts = [
        fact
        for fact in result.metric_facts
        if fact.name == ADS_SEARCH_TERM_PAYLOAD_STATUS
    ]
    assert [(fact.value, fact.period) for fact in status_facts] == [
        ("blocked", "last_30_days")
    ]


def _run_refresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
    search_term_row: dict[str, object],
) -> tuple[VendorReadResult, list[str]]:
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path))
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "developer-token-test")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id-test")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "client-secret-test")
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "refresh-token-test")
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "1234567890")
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "9998887777")
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "mock-access-token"})
        payload = json.loads(request.content.decode())
        if "query" not in payload:
            return httpx.Response(200, json={"results": []})
        query = payload["query"]
        queries.append(query)
        if "FROM search_term_view" in query and "LAST_30_DAYS" in query:
            return httpx.Response(200, json=[{"results": [search_term_row]}])
        return httpx.Response(200, json=[])

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    return result, queries


def _search_term_row() -> dict[str, object]:
    return {
        "campaign": {"id": "101", "name": "Doradztwo"},
        "adGroup": {"id": "201", "name": "Outsourcing"},
        "searchTermView": {
            "searchTerm": "outsourcing środowiskowy",
            "status": "ADDED",
        },
        "metrics": {
            "clicks": "9",
            "impressions": "100",
            "costMicros": "2400000",
            "conversions": 1.5,
            "conversionsValue": 900.0,
        },
    }
