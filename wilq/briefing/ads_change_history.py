from __future__ import annotations

from collections.abc import Iterable

from wilq.schemas import (
    AdsChangeHistoryReadContract,
    AdsChangeHistoryRow,
    MetricFact,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"


def build_change_history_read_contract(
    metric_facts: list[MetricFact],
    *,
    read_attempted: bool,
    fallback_evidence_ids: list[str],
) -> AdsChangeHistoryReadContract:
    rows = _change_history_rows(metric_facts)
    missing_read_contracts = [
        "pre_change_performance_window",
        "post_change_performance_window",
        "human_change_impact_review",
        "apply_preview",
    ]
    blocked_claims = [
        "change impact",
        "performance uplift",
        "budget scaling",
        "budget apply",
        "campaign mutation",
    ]
    if rows:
        resource_types = _unique(
            row.change_resource_type
            for row in rows
            if row.change_resource_type is not None
        )
        operations = _unique(
            row.resource_change_operation
            for row in rows
            if row.resource_change_operation is not None
        )
        summary = (
            f"WILQ ma {len(rows)} zdarzeń historii zmian Google Ads z ostatnich "
            f"14 dni. Typy zasobów: {', '.join(resource_types[:5])}; "
            f"operacje: {', '.join(operations[:5])}."
        )
        return AdsChangeHistoryReadContract(
            status="ready",
            title="Google Ads: historia zmian",
            summary=summary,
            allowed_metrics=[
                "change_event_available",
                "change_event_changed_field_count",
            ],
            missing_read_contracts=missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(
                [*(evidence_id for row in rows for evidence_id in row.evidence_ids)]
                or fallback_evidence_ids
            ),
            change_history_rows=rows,
            next_step=(
                "Użyj historii zmian jako kontekstu audytu: co zmieniono, kiedy i na "
                "jakim typie zasobu. Nie claimuj wpływu zmiany bez okna przed/po, "
                "celu biznesowego i ręcznego review."
            ),
        )
    if read_attempted:
        return AdsChangeHistoryReadContract(
            status="ready",
            title="Google Ads: brak zmian w historii zmian",
            summary=(
                "WILQ wykonał read-only change history read; Google Ads nie zwrócił "
                "zdarzeń zmian w ostatnich 14 dniach. Nie ma czego wiązać z "
                "wynikami kampanii."
            ),
            allowed_metrics=[
                "change_event_available",
                "change_event_changed_field_count",
            ],
            missing_read_contracts=missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=fallback_evidence_ids,
            change_history_rows=[],
            next_step=(
                "Nie przypisuj wyników kampanii do zmian, bo w bieżącym oknie "
                "Google Ads nie zwrócił zdarzeń change_event. Impact review "
                "pozostaje zablokowany do czasu pojawienia się zmian i okien "
                "wyników przed/po."
            ),
        )
    return AdsChangeHistoryReadContract(
        status="blocked",
        title="Google Ads: brak historii zmian",
        summary="WILQ nie ma jeszcze read-only metric facts z zasobu change_event.",
        allowed_metrics=[],
        missing_read_contracts=["change_history", *missing_read_contracts],
        blocked_claims=["change history", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=fallback_evidence_ids,
        change_history_rows=[],
        next_step=(
            "Uruchom Google Ads vendor_read z change_event read. Nie interpretuj "
            "wpływu zmian kampanii bez tych facts."
        ),
    )


def _change_history_rows(metric_facts: list[MetricFact]) -> list[AdsChangeHistoryRow]:
    grouped_facts: dict[str, list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str, str]] = set()
    for fact in metric_facts:
        if fact.name not in {"change_event_available", "change_event_changed_field_count"}:
            continue
        change_event_id = fact.dimensions.get("change_event_id")
        if not change_event_id:
            continue
        metric_key = (change_event_id, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(change_event_id, []).append(fact)

    rows = [
        _change_history_row(change_event_id, facts)
        for change_event_id, facts in grouped_facts.items()
    ]
    return sorted(rows, key=_change_history_row_sort_key)


def _change_history_row(
    change_event_id: str,
    facts: list[MetricFact],
) -> AdsChangeHistoryRow:
    facts_by_name = {fact.name: fact for fact in facts}
    first_dimensions = facts[0].dimensions if facts else {}
    changed_fields = [
        field.strip()
        for field in first_dimensions.get("changed_fields", "").split(",")
        if field.strip()
    ]
    expected_metrics = ["change_event_available", "change_event_changed_field_count"]
    return AdsChangeHistoryRow(
        change_event_id=change_event_id,
        change_date_time=first_dimensions.get("change_date_time"),
        change_resource_id=first_dimensions.get("change_resource_id"),
        change_resource_type=first_dimensions.get("change_resource_type"),
        resource_change_operation=first_dimensions.get("resource_change_operation"),
        client_type=first_dimensions.get("client_type"),
        campaign_id=first_dimensions.get("campaign_id"),
        changed_field_count=_int_metric_value(
            facts_by_name.get("change_event_changed_field_count")
        ),
        changed_fields=changed_fields,
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=[
            "change impact",
            "performance uplift",
            "budget apply",
            "campaign mutation",
        ],
    )


def _change_history_row_sort_key(row: AdsChangeHistoryRow) -> tuple[str, str]:
    return (row.change_date_time or "", row.change_event_id or "")


def _int_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None:
        return None
    try:
        return int(float(fact.value))
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
