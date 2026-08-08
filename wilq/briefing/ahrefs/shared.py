"""Shared Ahrefs facts, refresh lineage, and collection helpers."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ConnectorRefreshRun,
    MetricFact,
    connector_refresh_has_live_data,
)
from wilq.storage.metric_store import metric_store

AhrefsGapType = Literal[
    "competitor_page",
    "content_gap",
    "backlink_gap",
    "organic_keyword_gap",
    "top_page_gap",
]

AhrefsBudgetStageStatus = Literal["completed", "failed", "skipped", "not_run"]

AHREFS_CONNECTOR_ID = "ahrefs"

AHREFS_CONTENT_REFRESH_ACTION_ID = "act_prepare_content_refresh_queue"

AHREFS_CROSS_CHECK_CONNECTOR_IDS = (
    "google_search_console",
    "wordpress_ekologus",
    "wordpress_sklep",
)

AHREFS_METRIC_FACT_LIMIT = 1000

AHREFS_CROSS_CHECK_METRIC_FACT_LIMIT = 1200

AHREFS_AUTHORITY_FACT_NAMES = {"domain_rating", "ahrefs_rank"}

AHREFS_COMPETITOR_READ_FACT_NAMES = {
    "organic_competitor_read_status",
    "organic_competitor_rows",
    "organic_competitor_country",
    "organic_competitor_mode",
}

AHREFS_GAP_FACT_NAMES = {
    "ahrefs_competitor_page_count",
    "ahrefs_content_gap_count",
    "ahrefs_backlink_gap_count",
    "ahrefs_referring_domain_gap_count",
    "ahrefs_organic_keyword_gap_count",
    "ahrefs_top_page_gap_count",
}

AHREFS_KNOWLEDGE_CARD_IDS = ["card_ahrefs_content_gap_playbook"]

AHREFS_EXPERT_RULE_IDS = ["content_brief_rules_v1"]

def _facts_for_known_refresh_runs(
    metric_facts: list[MetricFact],
    refresh_runs: list[ConnectorRefreshRun],
    *,
    latest_refresh: ConnectorRefreshRun | None = None,
) -> list[MetricFact]:
    selected_runs = [latest_refresh] if latest_refresh is not None else refresh_runs
    # Authority-only refreshes are useful for the current domain context, but
    # must not erase the latest persisted gap read.  A gap claim remains tied
    # to the exact evidence from the refresh that produced it.
    latest_gap_refresh = _latest_gap_refresh(refresh_runs)
    if latest_gap_refresh is not None and latest_gap_refresh not in selected_runs:
        selected_runs.append(latest_gap_refresh)
    known_evidence_ids = {
        evidence_id
        for run in selected_runs
        if run is not None
        for evidence_id in run.evidence_ids
        if evidence_id.startswith("ev_refresh_")
    }
    if not known_evidence_ids:
        return metric_facts
    return [fact for fact in metric_facts if fact.evidence_id in known_evidence_ids]

def _latest_gap_refresh(
    refresh_runs: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    def recency_key(run: ConnectorRefreshRun) -> datetime:
        return run.completed_at or run.started_at

    gap_runs = [
        run
        for run in refresh_runs
        if any(metric_name in AHREFS_GAP_FACT_NAMES for metric_name in run.metric_summary)
    ]
    return max(gap_runs, key=recency_key) if gap_runs else None

def _cross_check_metric_facts() -> list[MetricFact]:
    facts: list[MetricFact] = []
    for connector_id in AHREFS_CROSS_CHECK_CONNECTOR_IDS:
        facts.extend(
            metric_store().list_metric_facts(
                connector_id=connector_id,
                limit=AHREFS_CROSS_CHECK_METRIC_FACT_LIMIT,
            )
        )
    return facts

def _latest_relevant_ahrefs_refresh(
    refresh_runs: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    def recency_key(run: ConnectorRefreshRun) -> datetime:
        return run.completed_at or run.started_at

    live_vendor_reads = [
        run
        for run in refresh_runs
        if run.mode.value == "vendor_read" and connector_refresh_has_live_data(run)
    ]
    if live_vendor_reads:
        return max(live_vendor_reads, key=recency_key)
    return max(refresh_runs, key=recency_key) if refresh_runs else None

def _latest_facts_by_name(
    facts: list[MetricFact],
    names: set[str],
) -> list[MetricFact]:
    facts_by_name: dict[str, MetricFact] = {}
    for fact in facts:
        if fact.name not in names:
            continue
        facts_by_name.setdefault(fact.name, fact)
    return list(facts_by_name.values())

def _gap_facts(facts: list[MetricFact]) -> list[MetricFact]:
    return [fact for fact in facts if fact.name in AHREFS_GAP_FACT_NAMES]

def _ahrefs_snapshot_date(refresh: ConnectorRefreshRun | None) -> str | None:
    if refresh is None:
        return None
    value = refresh.metric_summary.get("date")
    return str(value) if value else None

def _fact_value(facts: list[MetricFact], name: str) -> int | float | str | None:
    for fact in facts:
        if fact.name == name:
            return fact.value
    return None

def _clean_metric_tiles(
    tiles: dict[str, int | float | str | None],
) -> dict[str, int | float | str]:
    return {key: value for key, value in tiles.items() if value is not None}

def _evidence_ids_for_facts_or_refresh(
    facts: list[MetricFact],
    run: ConnectorRefreshRun | None,
) -> list[str]:
    fact_evidence_ids = _unique(fact.evidence_id for fact in facts if fact.evidence_id)
    if fact_evidence_ids:
        return fact_evidence_ids
    return _refresh_or_connector_evidence_ids(run)

def _refresh_or_connector_evidence_ids(run: ConnectorRefreshRun | None) -> list[str]:
    if run and run.evidence_ids:
        return run.evidence_ids
    return [connector_evidence_id(AHREFS_CONNECTOR_ID)]

def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values

