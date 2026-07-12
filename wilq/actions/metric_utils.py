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


def metric_fact_sort_time(fact: MetricFact) -> str:
    if fact.collected_at is None:
        return ""
    return fact.collected_at.isoformat()


def latest_metric_facts_by_identity(metric_facts: list[MetricFact]) -> list[MetricFact]:
    latest_by_key: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in metric_facts:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted(fact.dimensions.items())),
        )
        current = latest_by_key.get(key)
        if current is None or metric_fact_sort_time(fact) > metric_fact_sort_time(current):
            latest_by_key[key] = fact
    return sorted(
        latest_by_key.values(),
        key=metric_fact_sort_time,
        reverse=True,
    )


def facts_by_connector(facts: list[MetricFact]) -> dict[str, list[MetricFact]]:
    grouped: dict[str, list[MetricFact]] = {}
    for fact in facts:
        grouped.setdefault(fact.source_connector, []).append(fact)
    return grouped


def metric_sentence(facts: list[MetricFact]) -> str:
    if not facts:
        return "Najważniejsze fakty: nie ma potwierdzonych metryk do pokazania"
    samples = ", ".join(f"{metric_fact_label(fact.name)}: {fact.value}" for fact in facts[:4])
    if len(facts) > 4:
        return f"Najważniejsze fakty: {samples} i kolejne sygnały w dowodach"
    return f"Najważniejsze fakty: {samples}"


def metric_fact_label(name: str) -> str:
    labels = {
        "issue_product_count": "zgłoszenia problemów",
        "sample_product_id": "przykładowe produkty",
        "active_users": "aktywni użytkownicy",
        "engagement_rate": "zaangażowanie",
        "ecommerce_purchases": "zakupy e-commerce",
        "key_events": "zdarzenia kluczowe",
        "clicks": "kliknięcia",
        "impressions": "wyświetlenia",
        "ctr": "CTR",
        "position": "średnia pozycja",
        "content_gap_count": "luki treści",
        "keyword_count": "liczba fraz",
        "visibility_score": "widoczność",
    }
    return labels.get(name, "metryka źródłowa")
