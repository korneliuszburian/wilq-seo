"""Decomposed ga4_diagnostics conversions implementation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from wilq.briefing.ga4.labels import GA4_READ_CONTRACT_LABELS
from wilq.briefing.ga4.shared import (
    GA4_CONNECTOR_ID,
    GA4_CONVERSION_BLOCKED_CLAIMS,
    GA4_CONVERSION_METRIC_NAMES,
    _dimensioned_ga4_facts,
    _landing_group_count,
    _refresh_or_connector_evidence_ids,
    _tactical_landing_group_count,
    _unique,
)
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshRun,
    Ga4ConversionReadinessContract,
    MetricFact,
    TacticalQueueItem,
)


def _conversion_readiness_contract(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4ConversionReadinessContract:
    conversion_like_facts = [fact for fact in facts if fact.name in GA4_CONVERSION_METRIC_NAMES]
    observed_conversion_facts = [
        fact
        for fact in conversion_like_facts
        if isinstance(fact.value, (int, float))
        and not isinstance(fact.value, bool)
        and fact.value > 0
    ]
    dimensioned_facts = _dimensioned_ga4_facts(facts)
    landing_group_count = max(
        _landing_group_count(dimensioned_facts),
        _tactical_landing_group_count(tactical_items),
    )
    status: Literal["review_required", "blocked"] = (
        "review_required" if conversion_like_facts else "blocked"
    )
    available_read_contracts = (
        ["conversion_or_key_event_metric_facts"] if conversion_like_facts else []
    )
    missing_read_contracts = ["conversion_or_key_event_mapping"]
    if not conversion_like_facts:
        missing_read_contracts.append("conversion_or_key_event_metric_facts")
    evidence_ids = _unique(
        [
            *(fact.evidence_id for fact in conversion_like_facts),
            *(fact.evidence_id for fact in dimensioned_facts[:12]),
            *(evidence_id for item in tactical_items for evidence_id in item.evidence_ids),
            *_refresh_or_connector_evidence_ids(latest_refresh),
        ]
    )
    return Ga4ConversionReadinessContract(
        status=status,
        title="GA4: gotowość konwersji i zdarzeń kluczowych",
        summary=(
            "WILQ może oceniać jakość ruchu z GA4. Obecność kolumn konwersji i zdarzeń "
            "kluczowych nie potwierdza jednak ich konfiguracji; zwrot z reklam, przychód "
            "i opłacalność pozostają zablokowane do osobnego sprawdzenia."
            if conversion_like_facts
            else "GA4 nie dostarczył metryk konwersji ani zdarzeń kluczowych. WILQ może "
            "ocenić wyłącznie jakość ruchu; wnioski o konwersjach, przychodzie i "
            "opłacalności pozostają zablokowane."
        ),
        conversion_metric_availability_status=("available" if conversion_like_facts else "missing"),
        conversion_observation_status=(
            "observed_non_zero" if observed_conversion_facts else "zero_or_missing"
        ),
        key_event_configuration_status=("unverified" if conversion_like_facts else "missing"),
        allowed_metrics=sorted(GA4_CONVERSION_METRIC_NAMES),
        available_read_contracts=available_read_contracts,
        available_read_contract_labels=_ga4_read_contract_labels(available_read_contracts),
        missing_read_contracts=missing_read_contracts,
        missing_read_contract_labels=_ga4_read_contract_labels(missing_read_contracts),
        conversion_like_metric_count=len(conversion_like_facts),
        observed_conversion_fact_count=len(observed_conversion_facts),
        dimensioned_behavior_metric_count=len(dimensioned_facts),
        landing_group_count=landing_group_count,
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=GA4_CONVERSION_BLOCKED_CLAIMS,
        next_step=(
            "Sprawdź jakość pomiaru w WILQ i potwierdź powiązanie "
            "konwersji i zdarzeń kluczowych przed wnioskami o opłacalności."
        ),
        risk=ActionRisk.medium,
    )


def _ga4_read_contract_labels(values: Iterable[str]) -> list[str]:
    return [
        GA4_READ_CONTRACT_LABELS.get(value, "zakres danych GA4 do sprawdzenia") for value in values
    ]
