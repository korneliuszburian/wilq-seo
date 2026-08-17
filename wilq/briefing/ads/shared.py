from __future__ import annotations

import hashlib
from typing import Any, Literal

from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionPreviewRowViewModel,
    AdsKeywordMatchContextRow,
    AdsSearchTermCoverage,
    AdsSearchTermMetricRow,
    AdsSearchTermSafetyRow,
    ConnectorRefreshRun,
    MetricFact,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"


AdsTargetStatus = Literal[
    "within_target",
    "outside_target",
    "spend_without_conversions",
    "insufficient_data",
    "no_target",
]


ADS_METRIC_FACT_LIMIT = 2500


ADS_SUMMARY_METRIC_FACT_LIMIT = 500


ADS_SUMMARY_VIEW_ROW_LIMIT = 5


ADS_SEARCH_TERM_ROW_LIMIT_30D = 50


ADS_SEARCH_TERM_ROW_LIMIT_90D = 200


ADS_STALE_AFTER_HOURS = 48


def _search_term_coverage(
    *,
    window: Literal["last_30_days", "search_term_safety_90d"],
    returned_row_count: int,
    requested_row_limit: int,
    blocked: bool = False,
) -> AdsSearchTermCoverage:
    connector_cap = requested_row_limit
    return AdsSearchTermCoverage(
        window=window,
        window_label="ostatnie 30 dni" if window == "last_30_days" else "ostatnie 90 dni",
        requested_row_limit=requested_row_limit,
        returned_row_count=returned_row_count,
        connector_cap=connector_cap,
        cap_applied=returned_row_count >= connector_cap,
        coverage_status=(
            "blocked" if blocked else "empty" if returned_row_count == 0 else "bounded_sample"
        ),
        privacy_omission_caveat=(
            "Google Ads może pomijać niskowolumenowe zapytania; wynik nie jest pełnym uniwersum."
        ),
    )


def _copy_limited_model(model: Any, **field_limits: int) -> Any:
    updates = {}
    for field_name, limit in field_limits.items():
        if hasattr(model, field_name):
            updates[field_name] = getattr(model, field_name)[:limit]
    if not updates:
        return model
    return model.model_copy(update=updates)


def _latest_refresh_has_summary_metric(
    latest_refresh: ConnectorRefreshRun | None,
    metric_name: str,
) -> bool:
    if latest_refresh is None:
        return False
    return metric_name in latest_refresh.metric_summary


def _remove_missing_contract_names(
    missing_read_contracts: list[str],
    *contract_names: str,
) -> list[str]:
    removals = set(contract_names)
    return [contract for contract in missing_read_contracts if contract not in removals]


def _int_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        try:
            return int(float(fact.value))
        except ValueError:
            return None
    return int(fact.value)


def _float_metric_value(fact: MetricFact | None) -> float | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        try:
            return float(fact.value)
        except ValueError:
            return None
    return float(fact.value)


def _format_float(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _search_term_row_sort_key(row: AdsSearchTermMetricRow) -> tuple[int, int, str]:
    return (-(row.cost_micros or 0), -(row.clicks or 0), row.search_term)


def _search_term_safety_key(
    row: AdsSearchTermMetricRow | AdsSearchTermSafetyRow,
) -> tuple[str, str | None, str | None]:
    return (row.search_term, row.campaign_id, row.ad_group_id)


def _safety_row_has_conversion_signal(row: AdsSearchTermSafetyRow) -> bool:
    return bool((row.conversions_90d or 0) > 0 or (row.conversion_value_90d or 0) > 0)


def _keyword_match_context_key(row: AdsKeywordMatchContextRow) -> tuple[str | None, str | None]:
    return (row.campaign_id, row.ad_group_id)


def _slug(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "_" for character in value)
    return "_".join(part for part in normalized.split("_") if part)[:80] or "unknown"


def _refresh_or_connector_evidence_ids(latest_refresh: ConnectorRefreshRun | None) -> list[str]:
    if latest_refresh:
        return latest_refresh.evidence_ids
    return [connector_evidence_id(GOOGLE_ADS_CONNECTOR_ID)]


def _format_micros(value: float | None) -> str | None:
    if value is None:
        return None
    account_units = value / 1_000_000
    if account_units >= 100:
        return f"{account_units:.0f}"
    if account_units >= 10:
        return f"{account_units:.1f}"
    return f"{account_units:.2f}"


def _ads_preview_card_id(kind: str, source_id: str) -> str:
    digest = hashlib.sha256(source_id.encode("utf-8")).digest()
    suffix = "".join(chr(ord("a") + byte % 26) for byte in digest[:8])
    return f"{kind}_card_{suffix}"


def _ads_preview_row(label: str, value: str) -> ActionPreviewRowViewModel:
    return ActionPreviewRowViewModel(label=label, value=value)
