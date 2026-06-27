from __future__ import annotations

from collections.abc import Iterable

from wilq.schemas import (
    AdsImpressionShareReadContract,
    AdsImpressionShareRow,
    MetricFact,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"


def build_impression_share_read_contract(
    metric_facts: list[MetricFact],
    *,
    read_attempted: bool,
    fallback_evidence_ids: list[str],
) -> AdsImpressionShareReadContract:
    rows = _impression_share_rows(metric_facts)
    missing_read_contracts = [
        "change_history",
        "human_budget_goal",
        "budget_apply_preview",
    ]
    blocked_claims = [
        "skalowanie budżetu",
        "zmiana budżetu",
        "zmarnowany budżet",
        "obietnica poprawy wyniku",
        "zapis zmian kampanii",
    ]
    if rows or read_attempted:
        if rows:
            budget_limited = sum(
                1
                for row in rows
                if (row.search_budget_lost_impression_share or 0) > 0
            )
            rank_limited = sum(
                1
                for row in rows
                if (row.search_rank_lost_impression_share or 0) > 0
            )
            summary = (
                f"WILQ ma udział w wyświetleniach dla {len(rows)} kampanii; "
                f"utrata przez budżet występuje w {budget_limited}, a utrata przez ranking "
                f"w {rank_limited}."
            )
        else:
            summary = (
                "WILQ odczytał udział w wyświetleniach; Google Ads nie zwrócił "
                "kampanii z tymi metrykami w bieżącym oknie."
            )
        return AdsImpressionShareReadContract(
            status="ready",
            title="Google Ads: udział w wyświetleniach",
            summary=summary,
            empty_state_message=(
                "Brak wierszy udziału w wyświetleniach. WILQ nie może ocenić utraconej "
                "ekspozycji przez budżet albo ranking bez metryk udziału w wyświetleniach."
            ),
            allowed_metrics=[
                "search_impression_share",
                "search_budget_lost_impression_share",
                "search_rank_lost_impression_share",
            ],
            missing_read_contracts=missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(
                [*(evidence_id for row in rows for evidence_id in row.evidence_ids)]
                or fallback_evidence_ids
            ),
            impression_share_rows=rows,
            next_step=(
                "Użyj udziału w wyświetleniach jako kontekstu ograniczeń budżetu lub "
                "rankingu. Nie skaluj budżetu ani nie twierdź, że budżet jest "
                "marnowany bez historii zmian, celu biznesowego i podglądu "
                "zapisu zmian."
            ),
        )
    return AdsImpressionShareReadContract(
        status="blocked",
        title="Google Ads: brak udziału w wyświetleniach",
        summary="WILQ nie ma jeszcze metryk udziału w wyświetleniach z Google Ads.",
        empty_state_message=(
            "Brak wierszy udziału w wyświetleniach. Odśwież dane Google Ads z metrykami "
            "udziału w wyświetleniach, żeby ocenić utraconą ekspozycję."
        ),
        allowed_metrics=[],
        missing_read_contracts=["impression_share", *missing_read_contracts],
        blocked_claims=["udział w wyświetleniach", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=fallback_evidence_ids,
        impression_share_rows=[],
        next_step=(
            "Uruchom odczyt danych Google Ads z metrykami udziału w wyświetleniach. "
            "Nie oceniaj utraconego udziału w wyświetleniach bez tych danych."
        ),
    )


def _impression_share_rows(metric_facts: list[MetricFact]) -> list[AdsImpressionShareRow]:
    grouped_facts: dict[tuple[str | None, str], list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str | None, str, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "search_impression_share",
            "search_budget_lost_impression_share",
            "search_rank_lost_impression_share",
        }:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        campaign_name = fact.dimensions.get("campaign_name")
        if not campaign_id and not campaign_name:
            continue
        row_key = (campaign_id, campaign_name or f"campaign {campaign_id}")
        metric_key = (campaign_id, row_key[1], fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _impression_share_row(campaign_id, campaign_name, facts)
        for (campaign_id, campaign_name), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_impression_share_row_sort_key)


def _impression_share_row(
    campaign_id: str | None,
    campaign_name: str,
    facts: list[MetricFact],
) -> AdsImpressionShareRow:
    facts_by_name = {fact.name: fact for fact in facts}
    first_dimensions = facts[0].dimensions if facts else {}
    expected_metrics = [
        "search_impression_share",
        "search_budget_lost_impression_share",
        "search_rank_lost_impression_share",
    ]
    return AdsImpressionShareRow(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        campaign_status=first_dimensions.get("campaign_status"),
        advertising_channel_type=first_dimensions.get("advertising_channel_type"),
        search_impression_share=_float_metric_value(
            facts_by_name.get("search_impression_share")
        ),
        search_budget_lost_impression_share=_float_metric_value(
            facts_by_name.get("search_budget_lost_impression_share")
        ),
        search_rank_lost_impression_share=_float_metric_value(
            facts_by_name.get("search_rank_lost_impression_share")
        ),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=[
            "skalowanie budżetu",
            "zmiana budżetu",
            "zmarnowany budżet",
            "obietnica poprawy wyniku",
        ],
    )


def _impression_share_row_sort_key(
    row: AdsImpressionShareRow,
) -> tuple[float, float, str]:
    budget_lost = row.search_budget_lost_impression_share or 0
    rank_lost = row.search_rank_lost_impression_share or 0
    return (-budget_lost, -rank_lost, row.campaign_name)


def _float_metric_value(fact: MetricFact | None) -> float | None:
    if fact is None:
        return None
    try:
        return float(fact.value)
    except (TypeError, ValueError):
        return None


def _unique(values: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        unique_values.append(text)
    return unique_values
