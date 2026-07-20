from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests._contract_support.api_client import client
from tests._contract_support.env import clear_ahrefs_env
from wilq.briefing.ahrefs_diagnostics import _latest_relevant_ahrefs_refresh
from wilq.connectors.vendor import VendorMetricFact
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store


def _run(
    *,
    run_id: str,
    connector_id: str,
    evidence_id: str,
    summary: str,
) -> ConnectorRefreshRun:
    return ConnectorRefreshRun(
        id=run_id,
        connector_id=connector_id,
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=[evidence_id],
        external_call_attempted=True,
        vendor_data_collected=True,
        summary=summary,
    )


def _seed_weak_ahrefs_gap_contract() -> None:
    run = _run(
        run_id="refresh_ahrefs_weak_overlap_test",
        connector_id="ahrefs",
        evidence_id="ev_refresh_ahrefs_weak_overlap_test",
        summary="Ahrefs weak-overlap fixture.",
    )
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                name,
                1,
                {
                    "gap_type": gap_type,
                    "keyword": "mieszalnik IBC",
                    "competitor_domain": "denios.pl",
                    "source_url": "https://denios.pl/mieszalnik-ibc/",
                },
                period="ahrefs_gap",
            )
            for name, gap_type in (
                ("ahrefs_competitor_page_count", "competitor_page"),
                ("ahrefs_content_gap_count", "content_gap"),
                ("ahrefs_backlink_gap_count", "backlink_gap"),
                ("ahrefs_organic_keyword_gap_count", "organic_keyword_gap"),
                ("ahrefs_top_page_gap_count", "top_page_gap"),
            )
        ],
    )


def _seed_weak_cross_check_sources() -> None:
    gsc_run = _run(
        run_id="refresh_gsc_weak_overlap_test",
        connector_id="google_search_console",
        evidence_id="ev_refresh_gsc_weak_overlap_test",
        summary="GSC weak-overlap fixture.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                "impressions",
                80,
                {
                    "query": "kontener IBC odpady",
                    "page": "https://www.ekologus.pl/kontener-ibc/",
                },
                period="last_28_days",
            )
        ],
    )
    wordpress_run = _run(
        run_id="refresh_wordpress_weak_overlap_test",
        connector_id="wordpress_ekologus",
        evidence_id="ev_refresh_wordpress_weak_overlap_test",
        summary="WordPress weak-overlap fixture.",
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                "content_object_seen",
                1,
                {
                    "title": "Lejek do kontenerów IBC",
                    "content_url": "https://www.ekologus.pl/lejek-do-kontenerow-ibc/",
                },
                period="wordpress_inventory",
            )
        ],
    )


def test_weak_ahrefs_cross_check_is_manual_and_has_no_queue_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_weak_overlap_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_weak_overlap.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    _seed_weak_ahrefs_gap_contract()
    _seed_weak_cross_check_sources()

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    contract = payload["gap_read_contract"]
    assert contract["status"] == "ready"
    assert contract["missing_read_contracts"] == []
    record = contract["gap_records"][0]
    assert record["mapping_status"] == "unbound"
    assert record["derived_method"]
    assert "zakres próby" in record["coverage_summary"]
    assert contract["coverage_summary"] == record["coverage_summary"]
    assert contract["cross_check_status"] == "manual_required"
    assert contract["cross_check_gsc_match_count"] == 0
    assert contract["cross_check_wordpress_match_count"] == 0
    assert contract["action_ids"] == []
    assert payload["action_ids"] == []
    candidate = next(
        item for item in contract["cross_check_candidates"] if item["topic"] == "mieszalnik IBC"
    )
    assert candidate["gsc_demand"] == "missing"
    assert candidate["wordpress_inventory_match"] == "missing"
    assert candidate["gsc_cross_check"]["strength"] == "weak"
    assert candidate["wordpress_cross_check"]["strength"] == "weak"
    assert candidate["gsc_overlap_terms"] == []
    assert candidate["wordpress_overlap_urls"] == []
    assert set(candidate["source_connectors"]) == {
        "ahrefs",
        "google_search_console",
        "wordpress_ekologus",
    }
    assert "Słabe podobieństwo" in contract["next_step"]
    assert payload["operator_summary"]["review_action_ids"] == []
    assert "Słabe podobieństwo" in payload["operator_summary"]["review_next_safe_click"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )

    assert context_response.status_code == 200
    context_contract = context_response.json()["ahrefs_diagnostics"]["gap_read_contract"]
    context_candidate = next(
        item
        for item in context_contract["cross_check_candidates"]
        if item["topic"] == "mieszalnik IBC"
    )
    assert context_candidate["gsc_cross_check"]["strength"] == "weak"
    assert context_candidate["wordpress_cross_check"]["strength"] == "weak"
    assert context_candidate["source_connectors"] == [
        "ahrefs",
        "google_search_console",
        "wordpress_ekologus",
    ]


def test_gap_contract_blocks_mixed_record_coverage_before_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_coverage_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_coverage.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    run = _run(
        run_id="refresh_ahrefs_mixed_coverage_test",
        connector_id="ahrefs",
        evidence_id="ev_refresh_ahrefs_mixed_coverage_test",
        summary="Ahrefs mixed coverage fixture.",
    )
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                "ahrefs_content_gap_count",
                1,
                {
                    "gap_type": "content_gap",
                    "keyword": "bdo odpady",
                    "competitor_domain": "denios.pl",
                    "target_domain": "ekologus.pl",
                    "target_keyword_sample_size": "100",
                    "target_keyword_limit": "1000",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_content_gap_count",
                1,
                {
                    "gap_type": "content_gap",
                    "keyword": "bdo raport",
                    "competitor_domain": "denios.pl",
                    "target_domain": "ekologus.pl",
                },
                period="ahrefs_gap",
            ),
        ],
    )

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    contract = response.json()["gap_read_contract"]
    assert contract["status"] == "blocked"
    assert "ahrefs_gap_coverage" in contract["missing_read_contracts"]
    assert any("zakres próby" in label for label in contract["missing_read_contract_labels"])
    assert contract["action_ids"] == []
    assert "kompletność zakresu porównania" in contract["blocked_claims"]


def test_latest_ahrefs_refresh_uses_newest_live_run_even_when_storage_order_is_old_first() -> None:
    old = _run(
        run_id="refresh_ahrefs_old",
        connector_id="ahrefs",
        evidence_id="ev_refresh_ahrefs_old",
        summary="old",
    ).model_copy(
        update={
            "started_at": datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
            "completed_at": datetime(2026, 7, 20, 8, 1, tzinfo=UTC),
            "metrics_persisted": True,
            "vendor_data_collected": True,
        }
    )
    newest = _run(
        run_id="refresh_ahrefs_newest",
        connector_id="ahrefs",
        evidence_id="ev_refresh_ahrefs_newest",
        summary="newest",
    ).model_copy(
        update={
            "started_at": datetime(2026, 7, 20, 9, 0, tzinfo=UTC),
            "completed_at": datetime(2026, 7, 20, 9, 1, tzinfo=UTC),
            "metrics_persisted": True,
            "vendor_data_collected": True,
        }
    )

    assert _latest_relevant_ahrefs_refresh([old, newest]) == newest


def test_ahrefs_request_budget_exposes_each_stage_and_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_budget_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_budget.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    run = _run(
        run_id="refresh_ahrefs_budget_test",
        connector_id="ahrefs",
        evidence_id="ev_refresh_ahrefs_budget_test",
        summary="Ahrefs budget fixture.",
    ).model_copy(
        update={
            "metrics_persisted": True,
            "metric_summary": {
                "domain_rating": 40,
                "organic_competitor_read_status": "completed",
                "organic_competitor_rows": 2,
                "top_pages_by_competitor_read_status": "completed",
                "top_pages_by_competitor_competitors": 2,
                "top_pages_by_competitor_rows": 4,
                "organic_keywords_by_url_read_status": "http_429",
                "organic_keywords_by_url_urls": 4,
                "organic_keywords_by_url_rows": 0,
                "content_gap_read_status": "skipped_no_competitor_keywords",
                "content_gap_competitor_keywords": 0,
                "backlink_gap_read_status": "completed",
                "backlink_gap_competitors": 2,
                "backlink_gap_rows": 3,
            },
        }
    )
    local_state_store().save_connector_refresh_run(run)

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    budget = response.json()["request_budget"]
    assert budget["estimated_calls"] == 11
    assert budget["failed_stages"] == 1
    assert budget["partial"] is True
    stages = {stage["id"]: stage for stage in budget["stages"]}
    assert stages["organic_keywords_by_url"]["status"] == "failed"
    assert stages["organic_keywords_by_url"]["requested_calls"] == 4
    assert stages["content_gap"]["status"] == "skipped"
    assert stages["backlink_gap"]["requested_calls"] == 3
