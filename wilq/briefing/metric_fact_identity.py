from __future__ import annotations

from collections.abc import Iterable

from wilq.schemas import MetricFact


def latest_metric_facts_by_identity(facts: Iterable[MetricFact]) -> list[MetricFact]:
    latest: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in facts:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted(fact.dimensions.items())),
        )
        current = latest.get(key)
        if current is None or _metric_fact_is_newer(fact, current):
            latest[key] = fact
    return list(latest.values())


def _metric_fact_is_newer(candidate: MetricFact, current: MetricFact) -> bool:
    if candidate.collected_at is not None and current.collected_at is not None:
        if candidate.collected_at != current.collected_at:
            return candidate.collected_at > current.collected_at
        return candidate.evidence_id > current.evidence_id
    if candidate.collected_at is not None:
        return True
    if current.collected_at is not None:
        return False
    return candidate.evidence_id > current.evidence_id
