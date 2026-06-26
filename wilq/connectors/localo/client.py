from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from wilq.connectors.vendor import MetricSummaryValue, VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

LOCALO_MCP_ENDPOINT = "https://api.localo.com/api/mcp"
LOCALO_RESOURCE_METADATA_ENDPOINT = "https://api.localo.com/.well-known/oauth-protected-resource"
LOCALO_AUTHORIZATION_SERVER_METADATA_ENDPOINT = (
    "https://api.localo.com/.well-known/oauth-authorization-server"
)
LOCALO_PLACE_PAGE_SIZE = 20
LOCALO_PLACE_DETAIL_LIMIT = 10
LOCALO_GBP_IMPRESSION_METRICS = [
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
]
LOCALO_GBP_ACTION_METRICS = [
    "CALL_CLICKS",
    "WEBSITE_CLICKS",
    "BUSINESS_DIRECTION_REQUESTS",
]

LOCALO_PLACES_QUERY = """
query PlaceList($input: PlaceListFiltersInput!) {
  placesList(input: $input) {
    places {
      id
    }
    placesTags {
      id
    }
  }
}
"""

LOCALO_PLACE_DETAIL_QUERY = """
query PlaceLocalVisibility($placeId: GUID!) {
  place(id: $placeId) {
    latestPlaceSnapshot {
      rating
      reviewsCount
    }
    activePlaceKeywords {
      visibility {
        current
        previous
        change
      }
      ahrefsOverview {
        volume
      }
      latestGrids(limit: 1) {
        orderedPlacePosition
        insertedAt
      }
    }
  }
}
"""

LOCALO_REVIEWS_STATS_QUERY = """
query PlaceReviewsStats($placeId: GUID!) {
  reviewsStats(placeId: $placeId) {
    reviewsCount
    repliedCount
    removedCount
  }
}
"""

LOCALO_GOOGLE_METRIC_SERIES_QUERY = """
query GoogleMetricSeries($args: GoogleMetricSeriesArgs!) {
  googleMetricSeries(args: $args) {
    value
    date
  }
}
"""

LOCALO_FAVORITE_COMPETITORS_QUERY = """
query LocaloFavoriteCompetitors($placeId: GUID!) {
  competitors: listPlaceActionTrackerFavoriteCompetitors(placeId: $placeId) {
    favorite
    changesCount
  }
}
"""


class LocaloMcpReadError(RuntimeError):
    pass


def refresh_localo_visibility_summary(
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    organization_id = variable_value("LOCALO_ORGANIZATION_ID")
    api_token = variable_value("LOCALO_API_TOKEN")
    access_token = variable_value("LOCALO_ACCESS_TOKEN")
    missing = [
        name
        for name, value in (
            ("LOCALO_ORGANIZATION_ID", organization_id),
            ("LOCALO_API_TOKEN", api_token),
        )
        if not value
    ]
    if missing:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "Odczyt danych Localo zablokowany przez brakujące credential names: "
                f"{', '.join(missing)}."
            ),
            errors=[f"Localo missing credential names: {', '.join(missing)}."],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30, follow_redirects=False)
    try:
        try:
            oauth_metadata = _fetch_oauth_metadata(client)
            initialize_status = _mcp_initialize_status(client, access_token)
        except httpx.HTTPStatusError as exc:
            return _http_failure_result(exc)
        except httpx.HTTPError as exc:
            return _transport_failure_result(exc)

        metric_summary: dict[str, MetricSummaryValue] = {
            "api": "localo_mcp_oauth_probe",
            "mcp_initialize_status": initialize_status,
            "authorization_code_supported": int(
                "authorization_code" in oauth_metadata.get("grant_types_supported", [])
            ),
            "pkce_s256_supported": int(
                "S256" in oauth_metadata.get("code_challenge_methods_supported", [])
            ),
            "access_token_present": int(bool(access_token)),
        }
        if initialize_status == 200:
            try:
                value_summary, metric_facts = _fetch_localo_value_facts(client, access_token)
            except LocaloMcpReadError as exc:
                return VendorReadResult(
                    status=ConnectorRefreshStatus.failed,
                    summary="Dostęp Localo działa, ale odczyt danych widoczności nie przeszedł.",
                    external_call_attempted=True,
                    vendor_data_collected=False,
                    metric_summary=metric_summary,
                    errors=[str(exc)],
                )
            metric_summary.update(value_summary)
            return VendorReadResult(
                status=ConnectorRefreshStatus.completed,
                summary=(
                    "Odczyt danych Localo zebrał agregaty miejsc, widoczności fraz "
                    "i opinii. Aktywne miejsca: "
                    f"{value_summary['localo_active_place_count']}; monitorowane frazy: "
                    f"{value_summary['localo_tracked_keyword_count']}."
                ),
                external_call_attempted=True,
                vendor_data_collected=True,
                metric_summary=metric_summary,
                metric_facts=metric_facts,
            )

        if not access_token:
            return VendorReadResult(
                status=ConnectorRefreshStatus.blocked,
                summary=(
                    "Endpoint Localo jest osiągalny, ale WILQ nie ma LOCALO_ACCESS_TOKEN. "
                    "Localo wymaga OAuth authorization_code z PKCE przed odczytem metryk "
                    "lokalnej widoczności."
                ),
                external_call_attempted=True,
                vendor_data_collected=False,
                metric_summary=metric_summary,
                errors=[
                    "Localo OAuth authorization is incomplete: missing LOCALO_ACCESS_TOKEN."
                ],
            )

        return VendorReadResult(
            status=ConnectorRefreshStatus.failed,
            summary=f"Test dostępu Localo zakończył się HTTP {initialize_status}.",
            external_call_attempted=True,
            vendor_data_collected=False,
            metric_summary=metric_summary,
            errors=[f"Localo access test HTTP {initialize_status}."],
        )
    finally:
        if owns_client:
            client.close()


def _fetch_oauth_metadata(client: httpx.Client) -> dict[str, Any]:
    resource_response = client.get(LOCALO_RESOURCE_METADATA_ENDPOINT)
    resource_response.raise_for_status()
    resource_payload = resource_response.json()
    authorization_servers = resource_payload.get("authorization_servers", [])
    if LOCALO_AUTHORIZATION_SERVER_METADATA_ENDPOINT and authorization_servers:
        metadata_url = f"{authorization_servers[0]}/.well-known/oauth-authorization-server"
    else:
        metadata_url = LOCALO_AUTHORIZATION_SERVER_METADATA_ENDPOINT
    response = client.get(metadata_url)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def _mcp_initialize_status(client: httpx.Client, access_token: str | None) -> int:
    response = client.post(
        LOCALO_MCP_ENDPOINT,
        headers=_mcp_headers(access_token),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "wilq", "version": "0.1.0"},
            },
        },
    )
    return response.status_code


def _fetch_localo_value_facts(
    client: httpx.Client,
    access_token: str | None,
) -> tuple[dict[str, MetricSummaryValue], list[VendorMetricFact]]:
    _mcp_initialized_notification(client, access_token)
    places = _active_places(client, access_token)
    place_ids = [place_id for place_id in places[:LOCALO_PLACE_DETAIL_LIMIT] if place_id]

    visibility_current_values: list[float] = []
    visibility_change_values: list[float] = []
    latest_grid_positions: list[float] = []
    keyword_volumes: list[float] = []
    review_ratings: list[float] = []
    snapshot_review_counts: list[float] = []
    reviews_count = 0
    reviews_replied_count = 0
    reviews_removed_count = 0
    gbp_impressions_total = 0
    gbp_actions_total = 0
    gbp_metric_point_count = 0
    competitor_count = 0
    favorite_competitor_count = 0
    competitor_change_count = 0
    tracked_keyword_count = 0

    for place_id in place_ids:
        place = _place_detail(client, access_token, place_id)
        snapshot = _mapping(place.get("latestPlaceSnapshot"))
        _append_float(review_ratings, snapshot.get("rating"))
        _append_float(snapshot_review_counts, snapshot.get("reviewsCount"))

        keywords = place.get("activePlaceKeywords", [])
        if isinstance(keywords, list):
            tracked_keyword_count += len([item for item in keywords if isinstance(item, dict)])
            for keyword in keywords:
                if not isinstance(keyword, dict):
                    continue
                visibility = _mapping(keyword.get("visibility"))
                _append_float(visibility_current_values, visibility.get("current"))
                _append_float(visibility_change_values, visibility.get("change"))
                ahrefs = _mapping(keyword.get("ahrefsOverview"))
                _append_float(keyword_volumes, ahrefs.get("volume"))
                latest_grids = keyword.get("latestGrids", [])
                if isinstance(latest_grids, list) and latest_grids:
                    grid = _mapping(latest_grids[0])
                    _append_float(latest_grid_positions, grid.get("orderedPlacePosition"))

        review_stats = _reviews_stats(client, access_token, place_id)
        reviews_count += _int_metric(review_stats.get("reviewsCount"))
        reviews_replied_count += _int_metric(review_stats.get("repliedCount"))
        reviews_removed_count += _int_metric(review_stats.get("removedCount"))

        gbp_summary = _gbp_visibility_summary(client, access_token, place_id)
        gbp_impressions_total += gbp_summary["impressions_total"]
        gbp_actions_total += gbp_summary["actions_total"]
        gbp_metric_point_count += gbp_summary["metric_point_count"]

        competitor_summary = _competitor_visibility_summary(client, access_token, place_id)
        competitor_count += competitor_summary["competitor_count"]
        favorite_competitor_count += competitor_summary["favorite_competitor_count"]
        competitor_change_count += competitor_summary["competitor_change_count"]

    summary: dict[str, MetricSummaryValue] = {
        "localo_read_contract_count": 5,
        "localo_active_place_count": len(places),
        "localo_place_detail_count": len(place_ids),
        "localo_tracked_keyword_count": tracked_keyword_count,
        "localo_visibility_score_count": len(visibility_current_values),
        "localo_latest_grid_position_count": len(latest_grid_positions),
        "localo_keyword_volume_count": len(keyword_volumes),
        "localo_total_keyword_volume": int(sum(keyword_volumes)),
        "localo_reviews_count": reviews_count,
        "localo_reviews_replied_count": reviews_replied_count,
        "localo_reviews_removed_count": reviews_removed_count,
        "localo_gbp_impressions_total": gbp_impressions_total,
        "localo_gbp_actions_total": gbp_actions_total,
        "localo_gbp_metric_point_count": gbp_metric_point_count,
        "localo_competitor_count": competitor_count,
        "localo_favorite_competitor_count": favorite_competitor_count,
        "localo_competitor_change_count": competitor_change_count,
        "localo_review_reply_rate": round(reviews_replied_count / reviews_count, 6)
        if reviews_count
        else 0.0,
    }
    if visibility_current_values:
        summary["localo_avg_visibility_current"] = _average(visibility_current_values)
    if visibility_change_values:
        summary["localo_avg_visibility_change"] = _average(visibility_change_values)
    if latest_grid_positions:
        summary["localo_avg_latest_grid_position"] = _average(latest_grid_positions)
    if review_ratings:
        summary["localo_avg_rating"] = _average(review_ratings)
    if snapshot_review_counts:
        summary["localo_snapshot_reviews_count"] = int(sum(snapshot_review_counts))

    metric_facts = _localo_metric_facts(summary)
    return summary, metric_facts


def _mcp_initialized_notification(client: httpx.Client, access_token: str | None) -> None:
    response = client.post(
        LOCALO_MCP_ENDPOINT,
        headers=_mcp_headers(access_token),
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    if response.status_code not in {200, 202, 204}:
        raise LocaloMcpReadError(
            f"Localo initialized notification HTTP {response.status_code}."
        )


def _active_places(client: httpx.Client, access_token: str | None) -> list[str]:
    data = _mcp_graphql_query(
        client,
        access_token,
        LOCALO_PLACES_QUERY,
        {"input": {"active": True, "pageNo": 1, "pageSize": LOCALO_PLACE_PAGE_SIZE}},
    )
    places_list = _mapping(data.get("placesList"))
    places = places_list.get("places", [])
    if not isinstance(places, list):
        return []
    return [
        str(place["id"])
        for place in places
        if isinstance(place, dict) and isinstance(place.get("id"), str)
    ]


def _place_detail(client: httpx.Client, access_token: str | None, place_id: str) -> dict[str, Any]:
    data = _mcp_graphql_query(
        client,
        access_token,
        LOCALO_PLACE_DETAIL_QUERY,
        {"placeId": place_id},
    )
    return _mapping(data.get("place"))


def _reviews_stats(client: httpx.Client, access_token: str | None, place_id: str) -> dict[str, Any]:
    data = _mcp_graphql_query(
        client,
        access_token,
        LOCALO_REVIEWS_STATS_QUERY,
        {"placeId": place_id},
    )
    return _mapping(data.get("reviewsStats"))


def _gbp_visibility_summary(
    client: httpx.Client,
    access_token: str | None,
    place_id: str,
) -> dict[str, int]:
    impressions_total = 0
    actions_total = 0
    metric_point_count = 0
    for metric in LOCALO_GBP_IMPRESSION_METRICS:
        values = _google_metric_series_values(client, access_token, place_id, metric)
        impressions_total += sum(values)
        metric_point_count += len(values)
    for metric in LOCALO_GBP_ACTION_METRICS:
        values = _google_metric_series_values(client, access_token, place_id, metric)
        actions_total += sum(values)
        metric_point_count += len(values)
    return {
        "impressions_total": impressions_total,
        "actions_total": actions_total,
        "metric_point_count": metric_point_count,
    }


def _google_metric_series_values(
    client: httpx.Client,
    access_token: str | None,
    place_id: str,
    metric: str,
) -> list[int]:
    date_range = _google_metric_series_date_range()
    data = _mcp_graphql_query(
        client,
        access_token,
        LOCALO_GOOGLE_METRIC_SERIES_QUERY,
        {"args": {"placeId": place_id, "metrics": [metric], **date_range}},
    )
    series = data.get("googleMetricSeries", [])
    if not isinstance(series, list):
        return []
    return [_int_metric(_mapping(item).get("value")) for item in series]


def _google_metric_series_date_range() -> dict[str, str]:
    date_end = datetime.now(UTC).date()
    date_start = date_end - timedelta(days=30)
    return {"dateStart": date_start.isoformat(), "dateEnd": date_end.isoformat()}


def _competitor_visibility_summary(
    client: httpx.Client,
    access_token: str | None,
    place_id: str,
) -> dict[str, int]:
    try:
        data = _mcp_graphql_query(
            client,
            access_token,
            LOCALO_FAVORITE_COMPETITORS_QUERY,
            {"placeId": place_id},
        )
    except LocaloMcpReadError:
        return {
            "competitor_count": 0,
            "favorite_competitor_count": 0,
            "competitor_change_count": 0,
        }
    competitors = data.get("competitors", [])
    if not isinstance(competitors, list):
        return {
            "competitor_count": 0,
            "favorite_competitor_count": 0,
            "competitor_change_count": 0,
        }
    competitor_rows = [item for item in competitors if isinstance(item, dict)]
    return {
        "competitor_count": len(competitor_rows),
        "favorite_competitor_count": sum(
            1 for item in competitor_rows if item.get("favorite") is True
        ),
        "competitor_change_count": sum(
            _int_metric(item.get("changesCount")) for item in competitor_rows
        ),
    }


def _mcp_graphql_query(
    client: httpx.Client,
    access_token: str | None,
    query: str,
    variables: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        LOCALO_MCP_ENDPOINT,
        headers=_mcp_headers(access_token),
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "query",
                "arguments": {"query": query, "variables": variables},
            },
        },
    )
    if response.status_code != 200:
        raise LocaloMcpReadError(f"Localo data query HTTP {response.status_code}.")
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise LocaloMcpReadError("Localo data query returned JSON-RPC error.")
    graphql_payload = _graphql_payload_from_mcp_response(payload)
    if graphql_payload.get("errors"):
        raise LocaloMcpReadError("Localo GraphQL query returned errors.")
    data = graphql_payload.get("data")
    return data if isinstance(data, dict) else {}


def _graphql_payload_from_mcp_response(payload: Any) -> dict[str, Any]:
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return {}
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "text":
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
    data = result.get("data")
    if isinstance(data, dict):
        return data
    return result


def _mcp_headers(access_token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def _localo_metric_facts(summary: dict[str, MetricSummaryValue]) -> list[VendorMetricFact]:
    contracts = {
        "localo_active_place_count": "place_inventory",
        "localo_place_detail_count": "place_inventory",
        "localo_tracked_keyword_count": "local_rankings",
        "localo_visibility_score_count": "local_rankings",
        "localo_avg_visibility_current": "local_rankings",
        "localo_avg_visibility_change": "local_rankings",
        "localo_latest_grid_position_count": "local_rankings",
        "localo_avg_latest_grid_position": "local_rankings",
        "localo_keyword_volume_count": "local_rankings",
        "localo_total_keyword_volume": "local_rankings",
        "localo_avg_rating": "reviews",
        "localo_snapshot_reviews_count": "reviews",
        "localo_reviews_count": "reviews",
        "localo_reviews_replied_count": "reviews",
        "localo_reviews_removed_count": "reviews",
        "localo_review_reply_rate": "reviews",
        "localo_gbp_impressions_total": "gbp_visibility",
        "localo_gbp_actions_total": "gbp_visibility",
        "localo_gbp_metric_point_count": "gbp_visibility",
        "localo_competitor_count": "competitor_visibility",
        "localo_favorite_competitor_count": "competitor_visibility",
        "localo_competitor_change_count": "competitor_visibility",
    }
    facts: list[VendorMetricFact] = []
    for name, contract in contracts.items():
        value = summary.get(name)
        if value is None:
            continue
        facts.append(
            VendorMetricFact(
                name=name,
                value=value,
                dimensions={"contract": contract, "scope": "active_places"},
                period="localo_mcp_read",
            )
        )
    return facts


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _append_float(target: list[float], value: Any) -> None:
    parsed = _float_or_none(value)
    if parsed is not None:
        target.append(parsed)


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _int_metric(value: Any) -> int:
    parsed = _float_or_none(value)
    if parsed is None:
        return 0
    return int(parsed)


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _http_failure_result(exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Localo OAuth discovery failed with HTTP {status_code}.",
        external_call_attempted=True,
        errors=[f"Localo OAuth discovery HTTP {status_code}."],
    )


def _transport_failure_result(exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Localo OAuth discovery failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"Localo OAuth discovery {type(exc).__name__}."],
    )
