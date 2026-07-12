"""Content workflow, WordPress inventory and content context-pack tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests._contract_support.api_client import client
from tests._contract_support.assertions import assert_operator_context_strings_clean
from tests._contract_support.env import clear_google_service_env, clear_wordpress_env
from wilq.briefing.content_diagnostics import build_content_diagnostics, build_content_preflight
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    OpportunityDomain,
    TacticalQueueItem,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store


def test_marketing_tactical_queue_rejects_dev_preview_sitemap_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "dev_preview_queue.duckdb"))
    gsc_run = ConnectorRefreshRun(
        id="refresh_google_search_console_dev_preview_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_search_console_dev_preview_test"],
        metric_summary={"clicks": 8, "impressions": 220},
        summary="GSC dev preview rejection test seed.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_dev_preview_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_wordpress_ekologus_dev_preview_test"],
        metric_summary={"content_object_count": 1, "sitemap_url_count": 1},
        summary="WordPress dev preview sitemap seed.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=8,
                dimensions={
                    "query": "bdo przedsiębiorca",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            ),
            VendorMetricFact(
                name="impressions",
                value=220,
                dimensions={
                    "query": "bdo przedsiębiorca",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            ),
            VendorMetricFact(
                name="ctr",
                value=0.036,
                dimensions={
                    "query": "bdo przedsiębiorca",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            ),
            VendorMetricFact(
                name="average_position",
                value=6.2,
                dimensions={
                    "query": "bdo przedsiębiorca",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "site_kind": "primary",
                    "content_type": "sitemap",
                    "object_id": "",
                    "content_url": (
                        "https://ekologus.dev.proudsite.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
                    ),
                    "status": "indexed",
                    "modified_gmt": "2026-06-17T20:00:00+00:00",
                    "inventory_source": "sitemap",
                },
            )
        ],
    )

    response = client.get("/api/marketing/tactical-queue")

    assert response.status_code == 200
    item = next(
        item
        for item in response.json()["items"]
        if item["dimensions"].get("query") == "bdo przedsiębiorca"
    )
    assert item["dimensions"]["wordpress_match"] == "missing"
    assert item["dimensions"]["wordpress_match_confidence"] == "missing"
    assert "wordpress_content_host" not in item["dimensions"]
    assert item["dimensions"].get("wordpress_host_alias_applied") in {None, "false"}
    assert "wordpress_inventory_source" not in item["dimensions"]
    assert "wordpress_ekologus" not in item["source_connectors"]
    assert "ev_refresh_refresh_wordpress_ekologus_dev_preview_test" not in item["evidence_ids"]


def test_marketing_tactical_queue_uses_full_wordpress_inventory_for_url_matching(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "large_inventory.duckdb"))
    gsc_run = ConnectorRefreshRun(
        id="refresh_google_search_console_large_inventory_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_google_search_console_large_inventory_test"],
        metric_summary={"clicks": 29, "impressions": 651},
        summary="GSC large inventory test seed.",
    )
    target_wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_target_inventory_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ekologus_target_inventory_test"],
        metric_summary={"content_object_count": 1},
        summary="WordPress target URL seed.",
    )
    noisy_wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_noisy_inventory_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ekologus_noisy_inventory_test"],
        metric_summary={"content_object_count": 350},
        summary="Newer noisy WordPress inventory seed.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=29,
                dimensions={
                    "query": "co to jest zielony ład",
                    "page": ("https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"),
                },
            ),
            VendorMetricFact(
                name="impressions",
                value=651,
                dimensions={
                    "query": "co to jest zielony ład",
                    "page": ("https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"),
                },
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        target_wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": (
                        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
                    ),
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            )
        ],
    )
    metric_store().save_connector_refresh_metrics(
        noisy_wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": f"https://www.ekologus.pl/noisy-page-{index}/",
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            )
            for index in range(350)
        ],
    )

    response = client.get("/api/marketing/tactical-queue")

    assert response.status_code == 200
    item = next(
        item
        for item in response.json()["items"]
        if item["dimensions"].get("query") == "co to jest zielony ład"
    )
    assert item["dimensions"]["wordpress_match"] == "found"
    assert item["dimensions"]["wordpress_match_confidence"] == "exact_url"
    assert item["dimensions"]["wordpress_requested_path"] == (
        "/europejski-zielony-lad-co-to-takiego"
    )
    assert item["dimensions"]["wordpress_matched_path"] == ("/europejski-zielony-lad-co-to-takiego")
    assert item["intent"] in {"content_refresh", "content_merge"}
    assert "ev_refresh_wordpress_ekologus_target_inventory_test" in item["evidence_ids"]
    serialized_item = json.dumps(item, ensure_ascii=False)
    assert "stan wpisu:" in serialized_item
    assert "status:" not in serialized_item


def test_marketing_tactical_queue_does_not_slice_wordpress_inventory_url_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "wide_inventory.duckdb"))
    gsc_run = ConnectorRefreshRun(
        id="refresh_google_search_console_wide_inventory_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_google_search_console_wide_inventory_test"],
        metric_summary={"clicks": 4, "impressions": 4429},
        summary="GSC wide inventory test seed.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_wide_inventory_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ekologus_wide_inventory_test"],
        metric_summary={"content_object_count": 1301},
        summary="Wide WordPress inventory seed.",
    )
    wordpress_content_url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=4,
                dimensions={
                    "query": "bdo co to",
                    "page": wordpress_content_url,
                },
            ),
            VendorMetricFact(
                name="impressions",
                value=4429,
                dimensions={
                    "query": "bdo co to",
                    "page": wordpress_content_url,
                },
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            *[
                VendorMetricFact(
                    name="content_object_seen",
                    value=1,
                    dimensions={
                        "connector_id": "wordpress_ekologus",
                        "content_type": "sitemap",
                        "content_url": f"https://www.ekologus.pl/a-noise-{index:04d}/",
                        "status": "indexed",
                        "inventory_source": "public_sitemap",
                    },
                )
                for index in range(1250)
            ],
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": wordpress_content_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            ),
        ],
    )

    response = client.get("/api/marketing/tactical-queue")

    assert response.status_code == 200
    item = next(
        item for item in response.json()["items"] if item["dimensions"].get("query") == "bdo co to"
    )
    assert item["dimensions"]["wordpress_match"] == "found"
    assert item["dimensions"]["wordpress_match_confidence"] == "exact_url"
    assert item["dimensions"]["wordpress_content_url"] == wordpress_content_url


def test_content_diagnostics_blocks_until_vendor_read_when_no_content_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_block_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_block_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    clear_wordpress_env(monkeypatch)

    diagnostics = build_content_diagnostics(
        tactical_items=[],
        metric_facts=[],
        actions=[],
    )

    assert diagnostics.live_data_available is False
    assert all(connector.status_label for connector in diagnostics.connectors)
    assert all(refresh.connector_label for refresh in diagnostics.latest_refreshes)
    assert len(diagnostics.decision_queue) == 1
    decision = diagnostics.decision_queue[0]
    assert decision.id == "content_block_vendor_read"
    assert decision.decision_type == "block_until_vendor_read"
    assert decision.status == "blocked"
    assert decision.source_connectors == [
        "google_search_console",
        "wordpress_ekologus",
    ]
    assert decision.source_connector_labels == [
        "Google Search Console",
        "WordPress ekologus.pl",
    ]
    assert decision.evidence_ids == [
        "ev_connector_google_search_console_status",
        "ev_connector_wordpress_ekologus_status",
    ]
    assert decision.metric_tiles == {"blokady": 2}
    assert "query/page" not in decision.summary
    assert "danych GSC dla zapytań i stron" in decision.summary
    assert "rekomendacja bez danych źródłowych" in decision.blocked_claims
    assert "odczyt danych" in decision.next_step
    assert diagnostics.operator_summary.top_decision_ids == [decision.id]
    assert diagnostics.operator_summary.source_connector_labels == [
        "Google Search Console",
        "WordPress ekologus.pl",
    ]
    assert diagnostics.operator_summary.blocked_claim_labels
    assert "blokada do czasu odczytu danych" in (diagnostics.operator_summary.decision_type_labels)
    assert diagnostics.marketer_decision is not None
    assert diagnostics.marketer_decision.technical_decision_id == decision.id
    assert diagnostics.marketer_decision.status == "blocked"
    assert diagnostics.marketer_decision.source_connector_labels == [
        "Google Search Console",
        "WordPress ekologus.pl",
    ]
    assert "GSC" in diagnostics.marketer_decision.decision
    assert "automatyczna publikacja" in diagnostics.marketer_decision.blocked_claims
    assert all("_" not in value for value in diagnostics.marketer_decision.missing_inputs)
    assert diagnostics.marketer_decision.review_card_label == "Karta decyzji dla Wilka"
    assert "Nie zatwierdzaj" in diagnostics.marketer_decision.review_decision_after_review
    assert "GSC" in diagnostics.marketer_decision.review_question_for_wilku
    assert "nie publikuj" in diagnostics.marketer_decision.review_next_safe_click.lower()
    assert diagnostics.marketer_decision.review_action_ids == []

    preflight = build_content_preflight(diagnostics)
    assert preflight.primary_item is not None
    assert preflight.primary_item.recommended_mode == "block"
    assert preflight.primary_item.status == "blocked"
    assert preflight.primary_item.source_connector_labels == [
        "Google Search Console",
        "WordPress ekologus.pl",
    ]
    assert preflight.primary_item.create_allowed is False
    assert preflight.primary_item.draft_allowed is False
    assert preflight.primary_item.wordpress_draft_allowed is False
    assert preflight.primary_item.sales_brief_allowed is False
    assert preflight.blocker_count == 1


def test_content_diagnostics_exposes_query_page_inventory_queue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_diag_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_diag_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    clear_wordpress_env(monkeypatch)
    service_account_json = tmp_path / "google_adc.json"
    service_account_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_search_console_site_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt GSC zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "api": "search_console_search_analytics",
                "clicks": 12,
                "impressions": 120,
                "data_availability_checked": "true",
                "date_availability_status": "available",
                "availability_date_start": "2026-06-21",
                "availability_date_end": "2026-06-30",
                "date_start": "2026-06-29",
                "date_end": "2026-06-29",
                "search_type": "web",
                "detail_dimensions": "query,page",
                "detail_data_completeness": "partial_possible",
                "query_page_row_limit": 1000,
                "query_page_max_rows": 1000,
                "query_page_rows_truncated": "false",
                "aggregate_date_start": "2026-06-29",
                "aggregate_date_end": "2026-06-29",
                "aggregate_dimensions": "country,device",
                "aggregate_aggregation_type": "byProperty",
                "aggregate_data_completeness": "aggregate_without_query_page_dimensions",
                "aggregate_row_count": 2,
                "aggregate_clicks": 30,
                "aggregate_impressions": 300,
                "aggregate_ctr": 0.1,
                "aggregate_average_position": 4.0,
            },
            metric_facts=[
                VendorMetricFact(
                    "clicks",
                    12,
                    {
                        "query": "zielony ład",
                        "page": ("https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"),
                    },
                ),
                VendorMetricFact(
                    "impressions",
                    120,
                    {
                        "query": "zielony ład",
                        "page": ("https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"),
                    },
                ),
            ],
        ),
    )
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_wordpress_content_inventory",
        lambda connector_id, request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="WordPress inventory completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"content_object_count": 16, "pages_total": 4},
            metric_facts=[
                VendorMetricFact("content_object_count", 16, {}),
                VendorMetricFact(
                    "content_object_seen",
                    1,
                    {
                        "connector_id": "wordpress_ekologus",
                        "content_type": "sitemap",
                        "status": "indexed",
                        "content_url": (
                            "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
                        ),
                        "modified_gmt": "2024-07-11T07:04:02+00:00",
                        "title_or_h1": "Europejski Zielony Ład - co to takiego?",
                        "section_headings_json": json.dumps(
                            ["Co to jest Zielony Ład", "Kogo dotyczy"]
                        ),
                        "section_heading_count": "2",
                        "inventory_source": "public_sitemap",
                    },
                ),
            ],
        ),
    )

    gsc_response = client.post(
        "/api/connectors/google_search_console/refresh",
        json={"mode": "vendor_read", "reason": "content diagnostics test"},
    )
    wordpress_response = client.post(
        "/api/connectors/wordpress_ekologus/refresh",
        json={"mode": "vendor_read", "reason": "content diagnostics test"},
    )
    assert gsc_response.status_code == 200
    assert wordpress_response.status_code == 200
    ahrefs_collected_at = datetime(2026, 6, 18, 9, 0, tzinfo=UTC)
    ahrefs_run = ConnectorRefreshRun(
        id="refresh_ahrefs_gap_records",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=ahrefs_collected_at,
        completed_at=ahrefs_collected_at,
        evidence_ids=["ev_refresh_ahrefs_gap_records"],
        metric_summary={"ahrefs_content_gap_count": 2, "ahrefs_backlink_gap_count": 1},
        vendor_data_collected=True,
        summary="Dane luk Ahrefs odczytane przez test adapter.",
    )
    metric_store().save_connector_refresh_metrics(
        ahrefs_run,
        detailed_facts=[
            VendorMetricFact(
                "ahrefs_content_gap_count",
                1,
                {
                    "gap_type": "content_gap",
                    "keyword": "zielony ład",
                    "competitor_domain": "konkurent.example",
                },
            ),
            VendorMetricFact(
                "ahrefs_content_gap_count",
                1,
                {
                    "gap_type": "content_gap",
                    "keyword": "audyt środowiskowy",
                    "competitor_domain": "konkurent.example",
                },
            ),
            VendorMetricFact(
                "ahrefs_organic_keyword_gap_count",
                1,
                {
                    "gap_type": "organic_keyword_gap",
                    "keyword": "pozwolenie zintegrowane",
                    "competitor_domain": "konkurent.example",
                },
            ),
            VendorMetricFact(
                "ahrefs_backlink_gap_count",
                1,
                {
                    "gap_type": "backlink_gap",
                    "competitor_domain": "konkurent.example",
                    "source_url": "branża.example",
                },
            ),
        ],
    )

    response = client.get("/api/content/diagnostics")
    preflight_response = client.get("/api/content/preflight")

    assert response.status_code == 200
    assert preflight_response.status_code == 200
    payload = response.json()
    preflight_payload = preflight_response.json()
    assert payload["language"] == "pl-PL"
    assert all(connector["status_label"] for connector in payload["connectors"])
    assert all(refresh["status_label"] for refresh in payload["latest_refreshes"])
    assert all(refresh["connector_label"] for refresh in payload["latest_refreshes"])
    assert payload["live_data_available"] is True
    assert payload["live_data_status_label"] == "dane GSC i WordPress dostępne"
    freshness = payload["freshness_assessment"]
    assert freshness["state"] == "fresh"
    assert freshness["state_label"] == "dane treści świeże"
    assert freshness["requires_refresh"] is False
    assert freshness["stale_after_hours"] == 48
    assert "Podstawowe dane treści" in freshness["summary"]
    assert "bez dodatkowego odświeżenia" in freshness["next_step"]
    gsc_contract = payload["gsc_search_analytics_contract"]
    assert gsc_contract["source_connector"] == "google_search_console"
    assert "ev_refresh_" in " ".join(gsc_contract["evidence_ids"])
    assert gsc_contract["data_availability_checked"] is True
    assert gsc_contract["date_availability_status"] == "available"
    assert gsc_contract["expected_data_delay_days_min"] == 2
    assert gsc_contract["expected_data_delay_days_max"] == 3
    assert gsc_contract["availability_date_start"] == "2026-06-21"
    assert gsc_contract["availability_date_end"] == "2026-06-30"
    assert gsc_contract["latest_available_detail_date"] == "2026-06-29"
    assert gsc_contract["search_type"] == "web"
    assert gsc_contract["detail_dimensions"] == "query,page"
    assert gsc_contract["detail_data_completeness"] == "partial_possible"
    assert gsc_contract["read_granularity"] == "single_day_latest_available"
    assert gsc_contract["api_recommended_page_size"] == 25000
    assert gsc_contract["api_daily_row_cap_per_search_type"] == 50000
    assert gsc_contract["query_page_row_limit"] == 1000
    assert gsc_contract["query_page_max_rows"] == 1000
    assert gsc_contract["query_page_rows_truncated"] is False
    assert gsc_contract["aggregate_date_start"] == "2026-06-29"
    assert gsc_contract["aggregate_date_end"] == "2026-06-29"
    assert gsc_contract["aggregate_dimensions"] == "country,device"
    assert gsc_contract["aggregate_aggregation_type"] == "byProperty"
    assert gsc_contract["aggregate_data_completeness"] == "aggregate_without_query_page_dimensions"
    assert gsc_contract["aggregate_row_count"] == 2
    assert gsc_contract["aggregate_clicks"] == 30
    assert gsc_contract["aggregate_impressions"] == 300
    assert gsc_contract["aggregate_ctr"] == 0.1
    assert gsc_contract["aggregate_average_position"] == 4.0
    assert "Agregat GSC" in gsc_contract["aggregate_summary_label"]
    assert "najnowszy dostępny dzień" in gsc_contract["summary_label"]
    assert "nie pełną sumą całego ruchu" in gsc_contract["partial_detail_warning_label"]
    assert "rowLimit=1000" in gsc_contract["paging_label"]
    assert "2-3 dniach" in gsc_contract["official_limits_label"]
    assert "25 000 wierszy" in gsc_contract["official_limits_label"]
    assert "50 000 wierszy" in gsc_contract["official_limits_label"]
    assert "rowLimit=1000" in gsc_contract["wilq_internal_cap_label"]
    assert "max rows=1000" in gsc_contract["wilq_internal_cap_label"]
    assert payload["query_page_count"] >= 1
    assert payload["matched_inventory_count"] >= 1
    assert "act_prepare_content_refresh_queue" in payload["action_ids"]
    assert "akcj" in payload["action_summary_label"]
    query_section = next(
        section for section in payload["sections"] if section["id"] == "content_query_page_matrix"
    )
    assert query_section["status"] == "ready"
    assert query_section["evidence_summary_label"]
    assert "akcj" in query_section["action_summary_label"]
    assert isinstance(query_section["blocked_claim_labels"], list)
    assert all(fact["metric_label"] for fact in query_section["metric_facts"])
    assert query_section["tactical_items"]
    assert any(
        item["dimensions"].get("query") == "zielony ład" for item in query_section["tactical_items"]
    )
    inventory_section = next(
        section for section in payload["sections"] if section["id"] == "content_inventory_match"
    )
    assert inventory_section["status"] == "ready"
    assert inventory_section["evidence_summary_label"]
    assert "akcj" in inventory_section["action_summary_label"]
    assert isinstance(inventory_section["blocked_claim_labels"], list)
    assert all(fact["metric_label"] for fact in inventory_section["metric_facts"])
    assert any(
        item["dimensions"].get("wordpress_match") == "found"
        for item in inventory_section["tactical_items"]
    )
    assert payload["decision_queue"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "content_operator_summary"
    assert operator_summary["title"] == "Co marketer ma zrobić teraz z treściami"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["confirmed_wordpress_count"] == sum(
        1 for decision in payload["decision_queue"] if decision.get("wordpress_match") == "found"
    )
    assert operator_summary["missing_wordpress_count"] == sum(
        1 for decision in payload["decision_queue"] if decision.get("wordpress_match") == "missing"
    )
    assert operator_summary["current_site_match_count"] == sum(
        1
        for decision in payload["decision_queue"]
        if decision.get("final_canonical_url")
        and "ekologus.dev.proudsite.pl" not in str(decision.get("final_canonical_url"))
    )
    assert not any(key.startswith("target_site_") for key in operator_summary)
    assert not any(key.startswith("mapping_review_") for key in operator_summary)
    assert not any(key.startswith("transition_candidate") for key in operator_summary)
    assert "odświeżenie albo scalenie" in operator_summary["decision_type_labels"]
    assert operator_summary["source_connector_labels"]
    assert not any("_" in value for value in operator_summary["source_connector_labels"])
    assert "act_prepare_content_refresh_queue" in operator_summary["action_ids"]
    assert operator_summary["evidence_summary_label"]
    assert "akcj" in operator_summary["action_summary_label"]
    assert "wzrost liczby leadów" in operator_summary["blocked_claims"]
    assert "wzrost liczby leadów" in operator_summary["blocked_claim_labels"]
    assert (
        operator_summary["metric_tiles"]["Zapytania i adresy z GSC"] == payload["query_page_count"]
    )
    assert (
        operator_summary["metric_tiles"]["Treści znalezione w WordPress"]
        == payload["matched_inventory_count"]
    )
    assert operator_summary["metric_tiles"]["Luki Ahrefs powiązane z WordPress"] == 1
    assert operator_summary["metric_tiles"]["Decyzje treści"] == len(payload["decision_queue"])
    assert "Zapytania/URL" not in operator_summary["metric_tiles"]
    assert "GSC↔WP" not in operator_summary["metric_tiles"]
    assert "Ahrefs↔WP" not in operator_summary["metric_tiles"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    marketer_decision = payload["marketer_decision"]
    assert marketer_decision["technical_decision_id"] == payload["decision_queue"][0]["id"]
    assert marketer_decision["decision"]
    assert marketer_decision["why_it_matters"]
    assert marketer_decision["safe_next_action"]
    assert marketer_decision["review_card_label"] == "Karta decyzji dla Wilka"
    assert marketer_decision["review_decision_after_review"]
    assert marketer_decision["review_question_for_wilku"]
    assert marketer_decision["review_next_safe_click"]
    assert marketer_decision["review_action_ids"] == ["act_prepare_content_refresh_queue"]
    assert "bez zapisu" in marketer_decision["review_next_safe_click"]
    assert "publikacji" in marketer_decision["review_next_safe_click"]
    assert marketer_decision["metric_tiles"]
    assert marketer_decision["content_angle"]
    assert marketer_decision["h1_direction"]
    assert marketer_decision["h2_direction"]
    assert marketer_decision["faq_direction"]
    assert marketer_decision["cta_direction"]
    assert marketer_decision["source_facts"]
    assert marketer_decision["evidence_summary"]
    assert marketer_decision["source_connectors"]
    assert marketer_decision["source_connector_labels"]
    assert not any("_" in value for value in marketer_decision["source_connector_labels"])
    assert marketer_decision["evidence_ids"]
    assert marketer_decision["measurement_plan"]
    if marketer_decision["source_public_url"]:
        assert marketer_decision["source_public_url"].startswith("https://www.ekologus.pl/")
    if marketer_decision["final_canonical_url"]:
        assert "ekologus.dev.proudsite.pl" not in marketer_decision["final_canonical_url"]
        assert marketer_decision["final_canonical_url"].startswith("https://www.ekologus.pl/")
    assert not any("podgląd" in value.lower() for value in marketer_decision["missing_inputs"])
    assert not any("_" in value for value in marketer_decision["missing_inputs"])
    assert not any(
        "ActionObject" in value for value in marketer_decision.values() if isinstance(value, str)
    )
    assert not any(
        "publish" in value.lower() for value in marketer_decision.values() if isinstance(value, str)
    )
    first_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["decision_type"] == "refresh_or_merge"
    )
    assert first_decision["decision_type"] == "refresh_or_merge"
    assert first_decision["source_connector_labels"]
    assert not any("_" in value for value in first_decision["source_connector_labels"])
    assert all(fact["metric_label"] for fact in first_decision["metric_facts"])
    assert first_decision["status"] == "ready"
    assert first_decision["priority"] == 23
    assert first_decision["metric_tiles"] == {
        "zapytania": 1,
        "WP": "znaleziono",
        "sekcje WP": 2,
        "wyświetlenia": 120,
        "kliknięcia": 12,
        "CTR": "10.00%",
    }
    assert first_decision["title"] == (
        "Istniejący URL /europejski-zielony-lad-co-to-takiego: "
        "sprawdź istniejącą treść (1 zapytanie)"
    )
    assert first_decision["summary"] == (
        "GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "
        '"zielony ład". WordPress potwierdza istniejącą stronę, więc najpierw '
        "sprawdź aktualny URL, obecne sekcje i CTA. Aktualny tytuł/H1 w "
        'WordPress: "Europejski Zielony Ład - co to takiego?". Widoczne sekcje: '
        "Co to jest Zielony Ład, Kogo dotyczy. To nie jest nowy artykuł ani "
        "zadanie budowane z samego zapytania."
    )
    assert first_decision["wordpress_title_or_h1"] == ("Europejski Zielony Ład - co to takiego?")
    assert first_decision["wordpress_inventory_source"] == "public_sitemap"
    assert first_decision["wordpress_modified_gmt"] == "2024-07-11T07:04:02+00:00"
    assert first_decision["wordpress_section_headings"] == [
        "Co to jest Zielony Ład",
        "Kogo dotyczy",
    ]
    assert first_decision["wordpress_section_count"] == 2
    assert first_decision["wordpress_section_inventory_status"] == "available"
    assert first_decision["wordpress_content_inventory_status"] == "missing"
    assert "WordPress REST" in first_decision["wordpress_content_inventory_note"]
    assert first_decision["wordpress_acf_section_inventory_status"] == "missing"
    assert "ACF/flexible content" in first_decision["wordpress_acf_section_inventory_note"]
    assert first_decision["primary_query"] == "zielony ład"
    assert first_decision["total_clicks"] == 12
    assert first_decision["total_impressions"] == 120
    assert first_decision["aggregate_ctr"] == 0.1
    assert first_decision["wordpress_match"] == "found"
    assert first_decision["wordpress_match_confidence"] == "exact_url"
    assert first_decision["source_public_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert first_decision["final_canonical_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert first_decision["intended_final_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert first_decision["preview_url"] is None
    assert not any(key.startswith("target_site_") for key in first_decision)
    assert not any(key.startswith("mapping_review_") for key in first_decision)
    assert not any(key.startswith("transition_candidate") for key in first_decision)
    assert first_decision["inventory_gate_status"] == "confirmed_current_inventory"
    assert first_decision["canonical_gate_status"] == "public_canonical_confirmed"
    assert (
        first_decision["duplicate_gate_status"]
        == "existing_public_content_requires_refresh_or_merge"
    )
    assert "odświeżenie albo scalenie" in first_decision["content_gate_summary"]
    assert "nowy artykuł" in first_decision["content_gate_summary"]
    active_content_copy = json.dumps(
        {
            "operator_summary": operator_summary,
            "marketer_decision": marketer_decision,
            "decision_queue": payload["decision_queue"],
            "preflight": preflight_payload,
        },
        ensure_ascii=False,
    )
    assert "mapowanie" not in active_content_copy
    assert "mapping" not in active_content_copy
    assert first_decision["normalized_page_path"] == ("/europejski-zielony-lad-co-to-takiego")
    assert first_decision["evidence_ids"]
    assert first_decision["evidence_summary_label"]
    assert "act_prepare_content_refresh_queue" in first_decision["action_ids"]
    assert first_decision["action_summary_label"] == "1 akcja do sprawdzenia"
    assert first_decision["knowledge_card_ids"] == [
        "card_gsc_seo_content_playbook",
        "card_wordpress_content_refresh_playbook",
    ]
    assert first_decision["expert_rule_ids"] == [
        "seo_gsc_opportunities_v1",
        "seo_query_page_matrix_v1",
        "seo_content_decay_v1",
        "seo_cannibalization_v1",
        "content_duplication_rules_v1",
        "content_brief_rules_v1",
    ]
    preflight_item = next(
        item
        for item in preflight_payload["items"]
        if item["technical_decision_id"] == first_decision["id"]
    )
    assert preflight_payload["primary_item"] == preflight_item
    assert preflight_payload["source_connector_labels"]
    assert not any("_" in value for value in preflight_payload["source_connector_labels"])
    assert preflight_item["recommended_mode"] == "refresh"
    assert preflight_item["recommended_mode_label"] == "odświeżyć"
    assert preflight_item["status"] == "review_required"
    assert preflight_item["status_label"] == "wymaga sprawdzenia"
    assert preflight_item["create_allowed"] is False
    assert preflight_item["draft_allowed"] is False
    assert preflight_item["wordpress_draft_allowed"] is False
    assert preflight_item["sales_brief_allowed"] is True
    assert preflight_item["evidence_summary_label"]
    assert preflight_item["source_connector_labels"] == first_decision["source_connector_labels"]
    assert preflight_item["source_public_url"] == first_decision["source_public_url"]
    assert preflight_item["final_canonical_url"] == first_decision["final_canonical_url"]
    assert preflight_item["preview_url"] is None
    assert preflight_item["inventory_gate_status"] == "confirmed_current_inventory"
    assert preflight_item["inventory_gate_status_label"] == ("spis potwierdzony na obecnej stronie")
    assert preflight_item["canonical_gate_status"] == "public_canonical_confirmed"
    assert preflight_item["canonical_gate_status_label"] == "publiczny URL kanoniczny potwierdzony"
    assert (
        preflight_item["duplicate_gate_status"]
        == "existing_public_content_requires_refresh_or_merge"
    )
    assert preflight_item["duplicate_gate_status_label"] == (
        "istniejąca publiczna treść wymaga odświeżenia albo scalenia"
    )
    assert preflight_item["claim_gate_status_label"]
    assert preflight_item["service_fit_status_label"]
    assert preflight_item["similar_existing_urls"] == [
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    ]
    assert "1 zapytań z GSC" in preflight_item["query_overlap_summary"]
    assert "sprawdzeniu ryzykownych obietnic" in preflight_item["next_step"]
    ahrefs_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["decision_type"] == "review_ahrefs_gap_records"
    )
    assert ahrefs_decision["status"] == "ready"
    assert ahrefs_decision["title"] == ("Ahrefs: zweryfikuj luki SEO przed planem treści")
    assert ahrefs_decision["metric_tiles"] == {
        "rekordy Ahrefs": 4,
        "pasujące": 3,
        "do sprawdzenia": 0,
        "poza zakresem": 1,
        "Powiązanie z GSC": 1,
        "Powiązanie z WordPress": 1,
        "luki treści": 2,
        "luki linków zwrotnych": 1,
    }
    assert "GSC overlap" not in ahrefs_decision["metric_tiles"]
    assert "WP overlap" not in ahrefs_decision["metric_tiles"]
    assert {"zielony ład", "audyt środowiskowy", "pozwolenie zintegrowane"}.issubset(
        set(ahrefs_decision["queries"])
    )
    assert "branża.example" not in json.dumps(ahrefs_decision["queries"])
    assert len(ahrefs_decision["ahrefs_candidate_rows"]) == 3
    zielony_lad_candidate = next(
        candidate
        for candidate in ahrefs_decision["ahrefs_candidate_rows"]
        if candidate["topic"] == "zielony ład"
    )
    assert zielony_lad_candidate["relevance_status"] == "relevant"
    assert zielony_lad_candidate["gsc_demand"] == "present"
    assert zielony_lad_candidate["gsc_demand_label"] == "jest w GSC"
    assert zielony_lad_candidate["gsc_cross_check"]["strength"] == "exact"
    assert zielony_lad_candidate["gsc_cross_check"]["source_connectors"] == [
        "google_search_console"
    ]
    assert zielony_lad_candidate["wordpress_inventory_match"] == "present"
    assert zielony_lad_candidate["wordpress_inventory_match_label"] == "jest w WordPress"
    assert zielony_lad_candidate["wordpress_cross_check"]["strength"] == "exact"
    assert zielony_lad_candidate["wordpress_cross_check"]["source_connectors"] == [
        "wordpress_ekologus"
    ]
    assert zielony_lad_candidate["gsc_overlap_terms"] == ["zielony ład"]
    assert zielony_lad_candidate["wordpress_overlap_urls"] == [
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    ]
    assert "ekologus_domain_term" in zielony_lad_candidate["business_relevance_reasons"]
    assert "gsc_overlap" in zielony_lad_candidate["business_relevance_reasons"]
    assert "wordpress_inventory_overlap" in zielony_lad_candidate["business_relevance_reasons"]
    assert "content_candidate" in zielony_lad_candidate["business_relevance_reasons"]
    assert set(zielony_lad_candidate["source_connectors"]) == {
        "ahrefs",
        "google_search_console",
        "wordpress_ekologus",
    }
    assert "ev_refresh_ahrefs_gap_records" in zielony_lad_candidate["evidence_ids"]
    assert set(zielony_lad_candidate["evidence_ids"]) == {
        "ev_refresh_ahrefs_gap_records",
        *zielony_lad_candidate["gsc_cross_check"]["evidence_ids"],
        *zielony_lad_candidate["wordpress_cross_check"]["evidence_ids"],
    }
    assert "Wspólne sygnały: GSC: zielony ład" in zielony_lad_candidate["next_step"]
    assert "branża.example" not in json.dumps(ahrefs_decision["ahrefs_candidate_rows"])
    assert ahrefs_decision["source_connectors"] == ["ahrefs"]
    assert ahrefs_decision["source_connector_labels"] == ["Ahrefs"]
    assert ahrefs_decision["evidence_ids"] == ["ev_refresh_ahrefs_gap_records"]
    assert "act_prepare_content_refresh_queue" in ahrefs_decision["action_ids"]
    assert ahrefs_decision["knowledge_card_ids"] == [
        "card_ahrefs_content_gap_playbook",
        "card_gsc_seo_content_playbook",
        "card_wordpress_content_refresh_playbook",
    ]
    assert ahrefs_decision["expert_rule_ids"] == [
        "content_brief_rules_v1",
        "content_duplication_rules_v1",
    ]
    assert "rekomendacja treści poza zakresem" in ahrefs_decision["blocked_claims"]
    assert "wzrost ruchu" in ahrefs_decision["blocked_claims"]
    assert "ev_refresh_ahrefs_gap_records" in payload["evidence_ids"]
    assert all(
        candidate["gsc_demand_label"] != "brak"
        and candidate["wordpress_inventory_match_label"] != "brak"
        for candidate in ahrefs_decision["ahrefs_candidate_rows"]
    )

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-content-strategist"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["content_diagnostics"]["evidence_ids"] == payload["evidence_ids"]
    assert (
        context_payload["content_preflight"]["primary_item"]["technical_decision_id"]
        == (first_decision["id"])
    )
    assert context_payload["content_preflight"]["primary_item"]["recommended_mode"] == "refresh"
    assert context_payload["content_preflight"]["primary_item"]["draft_allowed"] is False
    assert context_payload["content_diagnostics"]["action_ids"] == payload["action_ids"]
    context_decision = next(
        decision
        for decision in context_payload["content_diagnostics"]["decision_queue"]
        if decision["id"] == first_decision["id"]
    )
    assert context_decision["decision_type"] == first_decision["decision_type"]
    assert context_decision["status"] == first_decision["status"]
    assert context_decision["priority"] == first_decision["priority"]
    assert context_decision["metric_tiles"] == first_decision["metric_tiles"]
    assert context_decision["summary"] == first_decision["summary"]
    assert context_decision["primary_query"] == first_decision["primary_query"]
    assert context_decision["total_impressions"] == first_decision["total_impressions"]
    assert (
        context_decision["wordpress_match_confidence"]
        == first_decision["wordpress_match_confidence"]
    )
    assert context_decision["normalized_page_path"] == first_decision["normalized_page_path"]
    assert context_decision["inventory_gate_status"] == first_decision["inventory_gate_status"]
    assert context_decision["canonical_gate_status"] == first_decision["canonical_gate_status"]
    assert context_decision["duplicate_gate_status"] == first_decision["duplicate_gate_status"]
    assert context_decision["content_gate_summary"] == first_decision["content_gate_summary"]
    assert context_decision["source_connectors"] == first_decision["source_connectors"]
    assert context_decision["evidence_ids"] == first_decision["evidence_ids"]
    assert context_decision["action_ids"] == first_decision["action_ids"]
    assert context_decision["knowledge_card_ids"] == first_decision["knowledge_card_ids"]
    assert context_decision["expert_rule_ids"] == first_decision["expert_rule_ids"]
    context_knowledge_card_ids = {
        card["id"] for card in context_payload["knowledge_card_summaries"]
    }
    context_expert_rule_ids = {rule["id"] for rule in context_payload["expert_rule_summaries"]}
    assert set(context_decision["knowledge_card_ids"]).issubset(context_knowledge_card_ids)
    assert set(context_decision["expert_rule_ids"]).issubset(context_expert_rule_ids)
    assert any(
        decision["decision_type"] == "review_ahrefs_gap_records"
        for decision in context_payload["content_diagnostics"]["decision_queue"]
    )
    context_ahrefs_decision = next(
        decision
        for decision in context_payload["content_diagnostics"]["decision_queue"]
        if decision["decision_type"] == "review_ahrefs_gap_records"
    )
    assert context_ahrefs_decision["ahrefs_candidate_rows_total"] == len(
        ahrefs_decision["ahrefs_candidate_rows"]
    )
    assert context_ahrefs_decision["ahrefs_candidate_rows"]
    context_candidate = context_ahrefs_decision["ahrefs_candidate_rows"][0]
    assert "gap_type" not in context_candidate
    assert "metric_name" not in context_candidate
    assert "id" not in context_candidate
    assert context_candidate["gap_type_label"]
    assert context_candidate["gsc_cross_check"]["strength"] == "exact"
    assert context_candidate["wordpress_cross_check"]["strength"] == "exact"
    assert set(context_candidate["source_connectors"]) == {
        "ahrefs",
        "google_search_console",
        "wordpress_ekologus",
    }
    assert "competitor_page" not in json.dumps(
        context_ahrefs_decision["ahrefs_candidate_rows"], ensure_ascii=False
    )

    gsc_context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-gsc-content-doctor"},
    )
    assert gsc_context_response.status_code == 200
    gsc_context_payload = gsc_context_response.json()
    assert all(
        decision["decision_type"] != "review_ahrefs_gap_records"
        for decision in gsc_context_payload["content_diagnostics"]["decision_queue"]
    )
    assert all(
        "_ahrefs" not in str(evidence_id)
        for evidence_id in gsc_context_payload["content_diagnostics"]["evidence_ids"]
    )
    serialized = json.dumps(payload)
    assert "google_adc.json" not in serialized
    assert "app-password" not in serialized


def test_content_diagnostics_preserves_gsc_query_page_after_newer_aggregate_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_window_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_window_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    clear_wordpress_env(monkeypatch)
    service_account_json = tmp_path / "google_adc.json"
    service_account_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    dimensioned_at = datetime(2026, 6, 18, 8, 0, tzinfo=UTC)
    query_page_run = ConnectorRefreshRun(
        id="refresh_gsc_query_page",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=dimensioned_at,
        completed_at=dimensioned_at,
        evidence_ids=["ev_refresh_gsc_query_page"],
        metric_summary={"clicks": 4, "impressions": 4429},
        vendor_data_collected=True,
        summary="Older GSC query/page vendor read.",
    )
    metric_store().save_connector_refresh_metrics(
        query_page_run,
        detailed_facts=[
            VendorMetricFact(
                "clicks",
                4,
                {
                    "query": "bdo co to",
                    "page": ("https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"),
                },
            ),
            VendorMetricFact(
                "impressions",
                4429,
                {
                    "query": "bdo co to",
                    "page": ("https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"),
                },
            ),
            VendorMetricFact(
                "ctr",
                0.0009031384059607134,
                {
                    "query": "bdo co to",
                    "page": ("https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"),
                },
            ),
            VendorMetricFact(
                "average_position",
                9.441183111311808,
                {
                    "query": "bdo co to",
                    "page": ("https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"),
                },
            ),
        ],
    )

    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_inventory",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=dimensioned_at,
        completed_at=dimensioned_at,
        evidence_ids=["ev_refresh_wordpress_inventory"],
        metric_summary={"content_object_count": 16, "pages_total": 4},
        vendor_data_collected=True,
        summary="WordPress inventory vendor read.",
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                "content_object_seen",
                1,
                {
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "status": "indexed",
                    "content_url": ("https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"),
                    "inventory_source": "public_sitemap",
                },
            )
        ],
    )
    local_state_store().save_connector_refresh_run(wordpress_run)

    latest_aggregate_run: ConnectorRefreshRun | None = None
    for index in range(151):
        collected_at = datetime(2026, 6, 19, 8, index % 60, tzinfo=UTC)
        aggregate_run = ConnectorRefreshRun(
            id=f"refresh_gsc_aggregate_{index}",
            connector_id="google_search_console",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=collected_at,
            completed_at=collected_at,
            evidence_ids=[f"ev_refresh_gsc_aggregate_{index}"],
            metric_summary={"clicks": 12, "impressions": 120},
            vendor_data_collected=True,
            summary="Newer aggregate GSC vendor read.",
        )
        metric_store().save_connector_refresh_metrics(aggregate_run)
        latest_aggregate_run = aggregate_run
    assert latest_aggregate_run is not None
    local_state_store().save_connector_refresh_run(latest_aggregate_run)

    response = client.get("/api/content/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_data_available"] is True
    assert payload["query_page_count"] >= 1
    assert payload["decision_queue"]
    assert any(
        decision["page"] == "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
        for decision in payload["decision_queue"]
    )
    query_section = next(
        section for section in payload["sections"] if section["id"] == "content_query_page_matrix"
    )
    assert query_section["status"] == "ready"
    assert any(
        item["dimensions"].get("query") == "bdo co to" for item in query_section["tactical_items"]
    )


def test_tactical_queue_wordpress_dimensions_use_operator_labels() -> None:
    item = TacticalQueueItem(
        id="tq_wordpress_dimension_labels",
        title="Treść do sprawdzenia",
        domain=OpportunityDomain.content,
        intent="content_refresh",
        priority=20,
        risk=ActionRisk.low,
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wordpress_dimension_labels"],
        dimensions={
            "wordpress_connector": "wordpress_ekologus",
            "wordpress_content_type": "sitemap",
            "wordpress_status": "indexed",
            "wordpress_content_url": "https://www.ekologus.pl/",
            "wordpress_host_alias_applied": "false",
            "target_mode": "subdomains",
        },
        diagnosis="WILQ ma spis treści WordPress.",
        next_step="Sprawdź istniejącą treść przed pisaniem.",
    )

    assert item.dimension_labels["wordpress_connector"] == "źródło WordPress"
    assert item.dimension_value_labels["wordpress_connector"] == "WordPress ekologus.pl"
    assert item.dimension_labels["wordpress_content_type"] == "typ treści WordPress"
    assert item.dimension_value_labels["wordpress_content_type"] == "mapa strony"
    assert item.dimension_value_labels["wordpress_status"] == "w indeksie"
    assert item.dimension_value_labels["wordpress_content_url"] == "https://www.ekologus.pl/"
    assert item.dimension_value_labels["wordpress_host_alias_applied"] == "nie"
    assert item.dimension_value_labels["target_mode"] == "subdomeny"
    serialized = json.dumps(item.model_dump(mode="json"), ensure_ascii=False)
    assert "wymiar do sprawdzenia" not in serialized
    assert "wartość do sprawdzenia" not in serialized


def test_codex_context_pack_scopes_content_strategist_payload() -> None:
    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-content-strategist"},
    )

    assert response.status_code == 200
    data = response.json()
    assert_operator_context_strings_clean(data)
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-content-strategist"
    assert "content_diagnostics" in data
    assert "ads_diagnostics" not in data
    assert "merchant_diagnostics" not in data
    assert "command_center" not in data
    assert len(data["evidence_summaries"]) <= 80
    connector_ids = {connector["id"] for connector in data["connector_status"]}
    assert connector_ids.issubset(
        {
            "google_search_console",
            "google_analytics_4",
            "ahrefs",
            "wordpress_ekologus",
            "wordpress_sklep",
        }
    )
    assert data["content_diagnostics"]["language"] == "pl-PL"
    assert data["content_diagnostics"]["evidence_ids"]
    assert "sections" not in data["content_diagnostics"]
    assert '"metric_facts":' not in json.dumps(data["content_diagnostics"])
    action_ids = {action["id"] for action in data["active_action_objects"]}
    assert action_ids == {"act_prepare_content_refresh_queue"}
    assert data["context_pack_compaction"]["connector_refresh_runs_compacted"] is True
    assert data["context_pack_compaction"]["evidence_summaries_compacted"] is True
    assert data["context_pack_compaction"]["knowledge_card_summaries_compacted"] is True
    assert data["context_pack_compaction"]["raw_history_omitted"] is True
    content_compaction = data["content_diagnostics"]["context_pack_compaction"]
    assert content_compaction["metric_facts_removed"] is True
    assert content_compaction["sections_omitted"] is True
    assert content_compaction["sections_total"] == 3
    assert content_compaction["connectors_compacted"] is True
    assert content_compaction["latest_refreshes_compacted"] is True
    assert content_compaction["full_endpoint"] == "/api/content/diagnostics"
    serialized_operator_context = json.dumps(
        {
            "connector_status": data["connector_status"],
            "connector_refresh_runs": data["connector_refresh_runs"],
            "evidence_summaries": data["evidence_summaries"],
            "knowledge_card_summaries": data["knowledge_card_summaries"],
            "expert_rule_summaries": data["expert_rule_summaries"],
            "active_action_objects": data["active_action_objects"],
            "content_diagnostics_connectors": data["content_diagnostics"].get("connectors"),
            "content_diagnostics_latest_refreshes": data["content_diagnostics"].get(
                "latest_refreshes"
            ),
        },
        ensure_ascii=False,
    )
    for forbidden_term in (
        "target_site",
        "mapping_review",
        "vendor_read",
        "Read-only",
        "read-only",
        "review-only",
        "ActionObject",
        "ga4_tracking_quality_review_v1",
        "tracking_quality_review",
    ):
        assert forbidden_term not in serialized_operator_context


def test_codex_context_pack_scopes_gsc_content_doctor_without_ahrefs_decisions() -> None:
    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-gsc-content-doctor"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-gsc-content-doctor"
    assert "content_diagnostics" in data
    assert "ahrefs_diagnostics" not in data
    content = data["content_diagnostics"]
    assert content["language"] == "pl-PL"
    assert "sections" not in content
    assert content["decision_queue"]
    assert all(
        decision["decision_type"] != "review_ahrefs_gap_records"
        for decision in content["decision_queue"]
    )
    assert all(
        "ahrefs" not in decision.get("source_connectors", [])
        for decision in content["decision_queue"]
    )
    assert "ahrefs" not in {
        connector
        for decision in content["decision_queue"]
        for connector in decision.get("source_connectors", [])
    }
    assert all("_ahrefs" not in str(evidence_id) for evidence_id in content["evidence_ids"])
    assert content["context_pack_compaction"]["purpose"] == "gsc_content_doctor_context"
    assert content["context_pack_compaction"]["ahrefs_decisions_removed"] is True


def test_content_operator_context_pack_exposes_service_profile_review_actions() -> None:
    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-content-operator"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-content-operator"

    actions_by_id = {action["id"]: action for action in data["active_action_objects"]}
    public_action = actions_by_id["act_prepare_service_profile_knowledge_promotion"]
    private_action = actions_by_id["act_prepare_service_profile_private_proposal_promotion"]

    assert "payload" not in public_action
    assert "payload" not in private_action
    assert public_action["api_endpoint_template"] == "/api/actions/{action_id}"
    assert private_action["api_endpoint_template"] == "/api/actions/{action_id}"
    assert public_action["preview_cards"]
    assert private_action["preview_cards"]
    assert public_action["preview_cards"][0]["kind"] == "service_profile_knowledge_promotion_review"
    assert (
        private_action["preview_cards"][0]["kind"]
        == "service_profile_private_proposal_promotion_review"
    )
    assert public_action["evidence_ids"] == ["ev_content_service_profile_source_facts"]
    assert private_action["evidence_ids"] == ["ev_content_service_profile_source_facts"]
