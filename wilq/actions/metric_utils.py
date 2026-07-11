from collections.abc import Iterable

from wilq.schemas import MetricFact


def prioritize_action_metrics(
    facts: list[MetricFact], *, required_names: set[str]
) -> list[MetricFact]:
    required: list[MetricFact] = []
    remaining: list[MetricFact] = []
    seen_required: set[str] = set()
    for fact in facts:
        if fact.name in required_names and fact.name not in seen_required:
            required.append(fact)
            seen_required.add(fact.name)
        else:
            remaining.append(fact)
    return [*required, *remaining]


def unique_values(items: Iterable[str]) -> list[str]:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    return unique_items
