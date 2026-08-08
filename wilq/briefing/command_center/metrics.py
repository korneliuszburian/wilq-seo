from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.briefing.merchant_labels import (
    merchant_dimension_label,
    merchant_dimension_value_label,
    merchant_metric_fact_label,
)
from wilq.briefing.tactical_queue import (
    GSC_QUERY_PAGE_FACT_LIMIT,
    WORDPRESS_INVENTORY_FACT_LIMIT,
    is_ahrefs_gap_fact,
    is_reviewable_ahrefs_gap_fact,
)
from wilq.schemas import (
    CommandCenterActionPlanItem,
    CommandCenterBriefItem,
    ConnectorRefreshRun,
    MetricFact,
    TacticalQueueItem,
)
from wilq.storage.metric_store import metric_store

from .shared import (
    AHREFS_COMMAND_CENTER_METRIC_FACT_LIMIT,
    AHREFS_CONNECTOR_ID,
    DAILY_DECISION_METRIC_FACT_LIMIT,
    GA4_COMMAND_CENTER_METRIC_FACT_LIMIT,
    GA4_CONNECTOR_ID,
    GOOGLE_ADS_COMMAND_CENTER_METRIC_FACT_LIMIT,
    GOOGLE_ADS_CONNECTOR_ID,
    GOOGLE_MERCHANT_CONNECTOR_ID,
    LOCALO_COMMAND_CENTER_CLAIM_BY_MISSING_CONTRACT,
    LOCALO_COMMAND_CENTER_CONTRACT_FACT_NAMES,
    LOCALO_COMMAND_CENTER_CONTRACT_ORDER,
    LOCALO_PROBE_METRIC_NAMES,
    MERCHANT_COMMAND_CENTER_METRIC_FACT_LIMIT,
    _unique,
)


def command_center_metric_fact_limits() -> dict[str, int]:
    return {
        GOOGLE_ADS_CONNECTOR_ID: GOOGLE_ADS_COMMAND_CENTER_METRIC_FACT_LIMIT,
        GOOGLE_MERCHANT_CONNECTOR_ID: MERCHANT_COMMAND_CENTER_METRIC_FACT_LIMIT,
        GA4_CONNECTOR_ID: GA4_COMMAND_CENTER_METRIC_FACT_LIMIT,
        AHREFS_CONNECTOR_ID: AHREFS_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "localo": 120,
        "google_search_console": GSC_QUERY_PAGE_FACT_LIMIT,
        "wordpress_ekologus": WORDPRESS_INVENTORY_FACT_LIMIT,
        "wordpress_sklep": WORDPRESS_INVENTORY_FACT_LIMIT,
    }


def _decision_metric_facts(
    plan_item: CommandCenterActionPlanItem,
    facts_by_connector: dict[str, list[MetricFact]],
) -> list[MetricFact]:
    evidence_ids = set(plan_item.evidence_ids)
    source_connectors = list(dict.fromkeys(plan_item.source_connectors))
    buckets: list[list[MetricFact]] = []
    seen: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()
    for connector_id in source_connectors:
        matched: list[MetricFact] = []
        fallback: list[MetricFact] = []
        candidate_facts = _decision_candidate_facts(
            plan_item,
            connector_id,
            facts_by_connector.get(connector_id, []),
        )
        for fact in candidate_facts:
            key = (
                fact.source_connector,
                fact.name,
                tuple(sorted(fact.dimensions.items())),
            )
            if key in seen:
                continue
            seen.add(key)
            fact = _decision_metric_fact_with_operator_labels(connector_id, fact)
            if fact.evidence_id in evidence_ids:
                matched.append(fact)
            else:
                fallback.append(fact)
        bucket = [*matched, *fallback]
        if bucket:
            buckets.append(bucket)
    selected: list[MetricFact] = []
    while buckets and len(selected) < DAILY_DECISION_METRIC_FACT_LIMIT:
        next_buckets: list[list[MetricFact]] = []
        for bucket in buckets:
            selected.append(bucket[0])
            if len(selected) >= DAILY_DECISION_METRIC_FACT_LIMIT:
                break
            if len(bucket) > 1:
                next_buckets.append(bucket[1:])
        else:
            buckets = next_buckets
            continue
        break
    return selected


def _decision_metric_fact_with_operator_labels(
    connector_id: str,
    fact: MetricFact,
) -> MetricFact:
    if connector_id != GOOGLE_MERCHANT_CONNECTOR_ID:
        return fact
    return fact.model_copy(
        update={
            "metric_label": merchant_metric_fact_label(fact.name),
            "dimension_labels": {key: merchant_dimension_label(key) for key in fact.dimensions},
            "dimension_value_labels": {
                key: merchant_dimension_value_label(key, value)
                for key, value in fact.dimensions.items()
            },
        }
    )


def _decision_candidate_facts(
    plan_item: CommandCenterActionPlanItem,
    connector_id: str,
    facts: list[MetricFact],
) -> list[MetricFact]:
    if plan_item.id != "plan_prepare_content_refresh_queue" or connector_id != AHREFS_CONNECTOR_ID:
        return facts
    reviewable_gap_facts = [fact for fact in facts if is_reviewable_ahrefs_gap_fact(fact)]
    if reviewable_gap_facts:
        return reviewable_gap_facts
    gap_facts = [fact for fact in facts if is_ahrefs_gap_fact(fact)]
    return gap_facts or facts


def _decision_metric_tiles(
    plan_item: CommandCenterActionPlanItem,
    brief_by_plan_id: dict[str, CommandCenterBriefItem],
) -> dict[str, float | int | str]:
    brief_item = brief_by_plan_id.get(plan_item.id)
    if brief_item is None:
        return {}
    return brief_item.metric_tiles


def _ads_campaign_count(facts: list[MetricFact]) -> int:
    return len(
        {
            fact.dimensions.get("campaign_id")
            for fact in facts
            if fact.dimensions.get("campaign_id")
            and fact.name
            in {
                "clicks",
                "impressions",
                "cost_micros",
                "conversions",
                "conversion_value",
                "budget_amount_micros",
            }
        }
    )


def _ads_search_term_count(facts: list[MetricFact]) -> int:
    return len(
        {
            fact.dimensions.get("search_term")
            for fact in facts
            if fact.dimensions.get("search_term") and fact.name.startswith("search_term_")
        }
    )


def _ads_distinct_dimension_count(facts: list[MetricFact], dimension: str) -> int:
    return len({fact.dimensions.get(dimension) for fact in facts if fact.dimensions.get(dimension)})


def _ads_recommendation_count(facts: list[MetricFact]) -> int:
    return _ads_distinct_dimension_count(facts, "recommendation_type")


def _ads_review_search_term_count(facts: list[MetricFact]) -> int:
    return len(
        {
            fact.dimensions.get("search_term")
            for fact in facts
            if fact.name in {"search_term_cost_micros", "search_term_90d_cost_micros"}
            and fact.dimensions.get("search_term")
            and isinstance(fact.value, int | float)
            and fact.value > 0
        }
    )


def _ads_derived_kpi_metric_tiles(facts: list[MetricFact]) -> dict[str, int]:
    campaign_rows = _ads_campaign_metric_rows(facts)
    if not campaign_rows:
        return {}
    cpa_rows = sum(
        1
        for row in campaign_rows.values()
        if _ratio_or_none(row.get("cost_micros"), row.get("conversions")) is not None
    )
    roas_rows = sum(
        1
        for row in campaign_rows.values()
        if _ratio_or_none(row.get("conversion_value"), _micros_to_units(row.get("cost_micros")))
        is not None
    )
    tiles = {"wskaźniki do sprawdzenia": len(campaign_rows)}
    if cpa_rows:
        tiles["wiersze kosztu pozyskania celu"] = cpa_rows
    if roas_rows:
        tiles["wiersze zwrotu z reklam"] = roas_rows
    return tiles


def _ads_campaign_metric_rows(
    facts: list[MetricFact],
) -> dict[tuple[str | None, str], dict[str, float]]:
    rows: dict[tuple[str | None, str], dict[str, float]] = {}
    seen_metric_keys: set[tuple[str | None, str, str]] = set()
    for fact in facts:
        if fact.name not in {
            "clicks",
            "impressions",
            "cost_micros",
            "conversions",
            "conversion_value",
        }:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        campaign_name = fact.dimensions.get("campaign_name") or (
            f"campaign {campaign_id}" if campaign_id else None
        )
        if campaign_name is None:
            continue
        metric_key = (campaign_id, campaign_name, fact.name)
        if metric_key in seen_metric_keys or not isinstance(fact.value, int | float):
            continue
        seen_metric_keys.add(metric_key)
        rows.setdefault((campaign_id, campaign_name), {})[fact.name] = float(fact.value)
    return rows


def _ratio_or_none(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _micros_to_units(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 1_000_000


def _ads_currency_tile(
    facts: list[MetricFact],
    metric_name: str,
    *,
    divide_by_million: bool = False,
) -> str:
    value = _sum_numeric_facts(facts, metric_name)
    amount = value / 1_000_000 if divide_by_million else value
    currency = _ads_currency_code(facts)
    amount_label = str(int(amount)) if amount.is_integer() else f"{amount:.2f}"
    return f"{amount_label} {currency}" if currency else amount_label


def _ads_currency_tile_from_summary(
    summary: dict[str, Any],
    facts: list[MetricFact],
    metric_name: str,
    *,
    divide_by_million: bool = False,
) -> str:
    value = _summary_numeric(summary, metric_name)
    if value is None:
        return _ads_currency_tile(facts, metric_name, divide_by_million=divide_by_million)
    amount = value / 1_000_000 if divide_by_million else value
    currency = _ads_summary_currency_code(summary) or _ads_currency_code(facts)
    amount_label = str(int(amount)) if amount.is_integer() else f"{amount:.2f}"
    return f"{amount_label} {currency}" if currency else amount_label


def _summary_int_tile(
    summary: dict[str, Any],
    keys: tuple[str, ...],
    fallback: int,
) -> int:
    for key in keys:
        value = _summary_numeric(summary, key)
        if value is not None:
            return int(value)
    return fallback


def _summary_number_tile(
    summary: dict[str, Any],
    key: str,
    fallback: float,
) -> int | float:
    value = _summary_numeric(summary, key)
    if value is None:
        value = fallback
    return int(value) if value.is_integer() else value


def _summary_numeric(summary: dict[str, Any], key: str) -> float | None:
    value = summary.get(key)
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return None


def _ads_summary_currency_code(summary: dict[str, Any]) -> str | None:
    value = summary.get("customer_currency_code") or summary.get("account_currency_code")
    return value if isinstance(value, str) and value else None


def _ads_currency_code(facts: list[MetricFact]) -> str | None:
    for fact in facts:
        if fact.name in {"customer_currency_code", "account_currency_code"} and isinstance(
            fact.value, str
        ):
            return fact.value
    return None


def _first_numeric_fact(facts: list[MetricFact], name: str) -> float:
    for fact in facts:
        if fact.name == name and isinstance(fact.value, int | float):
            return float(fact.value)
    return 0.0


def _sum_numeric_facts(facts: list[MetricFact], name: str) -> float:
    return sum(
        float(fact.value)
        for fact in facts
        if fact.name == name and isinstance(fact.value, int | float)
    )


def _merchant_issue_type_count(facts: list[MetricFact]) -> int:
    issue_keys = {
        (
            fact.dimensions.get("issue_type", ""),
            fact.dimensions.get("affected_attribute", ""),
            fact.dimensions.get("country", ""),
        )
        for fact in facts
        if fact.name == "issue_product_count" and fact.dimensions
    }
    return len(issue_keys)


def _merchant_issue_cluster_count(facts: list[MetricFact]) -> int:
    issue_keys = {
        (
            fact.dimensions.get("issue_type", ""),
            fact.dimensions.get("affected_attribute", ""),
            fact.dimensions.get("country", ""),
            fact.dimensions.get("severity", "UNKNOWN"),
            fact.dimensions.get("resolution", ""),
        )
        for fact in facts
        if fact.name == "issue_product_count" and fact.dimensions.get("issue_type")
    }
    return len(issue_keys)


def _merchant_item_product_count(item: TacticalQueueItem) -> float:
    for fact in item.metric_facts:
        if fact.name == "issue_product_count" and isinstance(fact.value, int | float):
            return float(fact.value)
    return 0.0


def _ahrefs_gap_facts(facts: list[MetricFact]) -> list[MetricFact]:
    record_facts = [fact for fact in facts if is_reviewable_ahrefs_gap_fact(fact)]
    if record_facts:
        return record_facts
    return [fact for fact in facts if is_ahrefs_gap_fact(fact)]


def _ahrefs_content_metric_tiles(facts: list[MetricFact]) -> dict[str, int]:
    if not facts:
        return {}
    content_gap_count = sum(
        1
        for fact in facts
        if fact.name == "ahrefs_content_gap_count"
        or fact.dimensions.get("gap_type") == "content_gap"
    )
    backlink_gap_count = sum(
        1
        for fact in facts
        if fact.name in {"ahrefs_backlink_gap_count", "ahrefs_referring_domain_gap_count"}
        or fact.dimensions.get("gap_type") == "backlink_gap"
    )
    tiles = {
        "ocena Ahrefs": 1,
        "rekordy Ahrefs": len(facts),
    }
    if content_gap_count:
        tiles["luki Ahrefs"] = content_gap_count
    if backlink_gap_count:
        tiles["luki linków"] = backlink_gap_count
    return tiles


def _sum_tactical_metric(items: list[TacticalQueueItem], name: str) -> int | float:
    total = sum(
        float(fact.value)
        for item in items
        for fact in item.metric_facts
        if fact.name == name and isinstance(fact.value, int | float)
    )
    return int(total) if total.is_integer() else total


def _numeric_tile(metric_tiles: dict[str, float | int | str], name: str) -> float:
    value = metric_tiles.get(name, 0)
    return float(value) if isinstance(value, int | float) else 0.0


def _dimensioned_ga4_facts(facts: Iterable[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.source_connector == GA4_CONNECTOR_ID
        and {"landing_page", "source_medium", "campaign_name"}.issubset(fact.dimensions)
    ]


def _ga4_landing_group_count(facts: Iterable[MetricFact]) -> int:
    return len(_ga4_landing_group_keys(facts))


def _ga4_measurement_issue_count(facts: Iterable[MetricFact]) -> int:
    return sum(
        1
        for landing_page, source_medium, campaign_name in _ga4_landing_group_keys(facts)
        if "(not set)" in {landing_page, source_medium, campaign_name}
    )


def _ga4_traffic_quality_count(facts: Iterable[MetricFact]) -> int:
    return sum(
        1
        for landing_page, source_medium, campaign_name in _ga4_landing_group_keys(facts)
        if "(not set)" not in {landing_page, source_medium, campaign_name}
    )


def _ga4_landing_group_keys(facts: Iterable[MetricFact]) -> set[tuple[str, str, str]]:
    return {
        (
            fact.dimensions.get("landing_page", ""),
            fact.dimensions.get("source_medium", ""),
            fact.dimensions.get("campaign_name", ""),
        )
        for fact in facts
    }


def _localo_value_facts(metric_facts: list[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in metric_facts
        if not (fact.source_connector == "localo" and fact.name in LOCALO_PROBE_METRIC_NAMES)
        and not (
            fact.source_connector == "localo"
            and fact.name == "api"
            and fact.value == "localo_mcp_oauth_probe"
        )
    ]


def _localo_missing_value_contracts(value_facts: list[MetricFact]) -> list[str]:
    if not value_facts:
        return [
            "local_rankings",
            "gbp_visibility",
            "competitor_visibility",
            "reviews",
            "local_tasks",
        ]
    fact_names = {fact.name for fact in value_facts}
    present = {
        contract
        for contract, names in LOCALO_COMMAND_CENTER_CONTRACT_FACT_NAMES.items()
        if fact_names.intersection(names)
    }
    return [
        contract for contract in LOCALO_COMMAND_CENTER_CONTRACT_ORDER if contract not in present
    ]


def _localo_blocked_claims_for_missing_contracts(
    missing_contracts: list[str],
) -> list[str]:
    claims = [
        claim
        for contract, claim in LOCALO_COMMAND_CENTER_CLAIM_BY_MISSING_CONTRACT.items()
        if contract in missing_contracts
    ]
    claims.extend(["zapis zmian w profilu firmy", "poprawa widoczności lokalnej"])
    return _unique(claims)


def _localo_metric_facts_for_run(
    run: ConnectorRefreshRun | None,
    fallback_facts: list[MetricFact],
) -> list[MetricFact]:
    if run and run.evidence_ids:
        evidence_ids = set(run.evidence_ids)
        batched_facts = [fact for fact in fallback_facts if fact.evidence_id in evidence_ids]
        if batched_facts:
            return batched_facts
        facts = metric_store().list_metric_facts_by_evidence_ids(run.evidence_ids)
        if facts:
            return facts
    return fallback_facts


def _localo_metric_tiles(
    value_facts: list[MetricFact],
    oauth_access_ready: bool,
) -> dict[str, int | float | str]:
    if not value_facts:
        return {
            "dostęp Localo": 1 if oauth_access_ready else 0,
            "dane rankingów": 0,
            "dane profilu firmy": 0,
        }
    return {
        "miejsca": _numeric_fact(value_facts, "localo_active_place_count"),
        "frazy": _numeric_fact(value_facts, "localo_tracked_keyword_count"),
        "widoczność": _numeric_fact(value_facts, "localo_avg_visibility_current"),
        "recenzje": _numeric_fact(value_facts, "localo_reviews_count"),
    }


def _numeric_fact(value_facts: list[MetricFact], name: str) -> int | float:
    for fact in value_facts:
        if fact.name != name or not isinstance(fact.value, int | float):
            continue
        if isinstance(fact.value, float) and fact.value.is_integer():
            return int(fact.value)
        return round(float(fact.value), 4) if isinstance(fact.value, float) else fact.value
    return 0


def _source_connectors_with_evidence(
    source_connectors: Iterable[object],
    evidence_ids: Iterable[object],
) -> list[str]:
    return _unique(
        [
            *source_connectors,
            *(
                connector_id
                for evidence_id in evidence_ids
                for connector_id in [_connector_from_evidence_id(str(evidence_id))]
                if connector_id
            ),
        ]
    )


def _connector_from_evidence_id(evidence_id: str) -> str | None:
    known_connectors = sorted(command_center_metric_fact_limits(), key=len, reverse=True)
    for connector_id in known_connectors:
        if evidence_id.startswith(f"ev_connector_{connector_id}_") or evidence_id.startswith(
            f"ev_refresh_refresh_{connector_id}_"
        ):
            return connector_id
    return None
