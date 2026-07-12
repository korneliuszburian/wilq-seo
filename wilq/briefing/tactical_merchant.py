from __future__ import annotations

from collections.abc import Iterable

from wilq.briefing.merchant_labels import (
    MERCHANT_ISSUE_LABELS,
    MERCHANT_RESOLUTION_LABELS,
    MERCHANT_SEVERITY_LABELS,
)
from wilq.schemas import ActionRisk, MetricFact, OpportunityDomain, TacticalQueueItem


def build_merchant_feed_items(
    *, facts: list[MetricFact], action_ids: dict[str, list[str]]
) -> list[TacticalQueueItem]:
    merchant_facts = [fact for fact in facts if fact.source_connector == "google_merchant_center"]
    issue_facts = [
        fact
        for fact in merchant_facts
        if fact.name == "issue_product_count"
        and {"severity", "issue_type", "country"}.issubset(fact.dimensions)
    ]
    if any(fact.dimensions.get("issue_type") for fact in issue_facts):
        issue_facts = [fact for fact in issue_facts if fact.dimensions.get("issue_type")]
    issue_groups = _group(issue_facts, issue=True)
    product_groups = _group(
        (
            fact
            for fact in merchant_facts
            if fact.name
            in {"active_products", "pending_products", "disapproved_products", "expiring_products"}
            and "country" in fact.dimensions
        ),
        issue=False,
    )
    items = _issue_items(issue_groups, action_ids)
    items.extend(_status_items(product_groups, action_ids))
    return items


def _issue_items(
    groups: dict[tuple[str, ...], list[MetricFact]], action_ids: dict[str, list[str]]
) -> list[TacticalQueueItem]:
    items: list[TacticalQueueItem] = []
    for index, ((severity, resolution, issue_type, country), group_facts) in enumerate(
        groups.items(), start=1
    ):
        product_count = _numeric(group_facts, "issue_product_count")
        issue_title = _dimension(group_facts, "issue_title")
        affected_attribute = _dimension(group_facts, "affected_attribute")
        issue_label = MERCHANT_ISSUE_LABELS.get(
            issue_type, issue_title or "problem Merchant do sprawdzenia"
        )
        severity_label = MERCHANT_SEVERITY_LABELS.get(severity, "ważność Merchant do sprawdzenia")
        resolution_label = MERCHANT_RESOLUTION_LABELS.get(
            resolution, "rozwiązanie Merchant do sprawdzenia"
        )
        items.append(
            TacticalQueueItem(
                id=f"tq_merchant_issue_{_slug(country)}_{_slug(severity)}_{_slug(issue_type)}",
                title=f"Merchant: {severity_label}; {issue_label}; kraj {country}",
                domain=OpportunityDomain.merchant,
                intent="merchant_feed_triage",
                priority=_priority(severity, product_count, index),
                risk=ActionRisk.medium if resolution == "MERCHANT_ACTION" else ActionRisk.low,
                source_connectors=["google_merchant_center"],
                evidence_ids=_unique(f.evidence_id for f in group_facts),
                metric_facts=group_facts[:6],
                dimensions={
                    "country": country,
                    "severity": severity,
                    "resolution": resolution,
                    "issue_type": issue_type,
                    **({"issue_title": issue_title} if issue_title else {}),
                    **({"affected_attribute": affected_attribute} if affected_attribute else {}),
                },
                diagnosis=(
                    f"Merchant Center pokazuje {product_count or 0} produktów w problemie "
                    f"{severity_label}: {issue_label}; {resolution_label}; kraj {country}."
                ),
                next_step=(
                    "Przygotuj kolejkę przeglądu problemów pliku produktowego i podgląd zmian. "
                    "Nie zmieniaj danych produktu bez sprawdzenia propozycji w WILQ "
                    "i zgody operatora."
                ),
                blocked_claims=[
                    "wdrożona poprawka produktu",
                    "ponowne zatwierdzenie produktu",
                    "odzyskany przychód",
                ],
                action_ids=action_ids.get("google_merchant_center", []),
            )
        )
    return items


def _status_items(
    groups: dict[tuple[str, ...], list[MetricFact]], action_ids: dict[str, list[str]]
) -> list[TacticalQueueItem]:
    items: list[TacticalQueueItem] = []
    for index, ((country, reporting_context), group_facts) in enumerate(groups.items(), start=1):
        expiring = _numeric(group_facts, "expiring_products")
        disapproved = _numeric(group_facts, "disapproved_products")
        if not expiring and not disapproved:
            continue
        items.append(
            TacticalQueueItem(
                id=f"tq_merchant_status_{_slug(country)}_{_slug(reporting_context)}",
                title=(
                    f"Merchant: status produktów w kraju {country}; kontekst: {reporting_context}"
                ),
                domain=OpportunityDomain.merchant,
                intent="merchant_feed_triage",
                priority=45 + index,
                risk=ActionRisk.medium if disapproved else ActionRisk.low,
                source_connectors=["google_merchant_center"],
                evidence_ids=_unique(f.evidence_id for f in group_facts),
                metric_facts=group_facts[:6],
                dimensions={"country": country, "reporting_context": reporting_context},
                diagnosis=(
                    f"Status pliku produktowego: disapproved_products={disapproved or 0}, "
                    f"expiring_products={expiring or 0} dla {country}/{reporting_context}."
                ),
                next_step="Sprawdź statusy produktów i przygotuj kolejkę ręcznego sprawdzenia.",
                blocked_claims=[
                    "ponowne zatwierdzenie produktu",
                    "rozwiązany problem pliku produktowego",
                ],
                action_ids=action_ids.get("google_merchant_center", []),
            )
        )
    return items


def _group(facts: Iterable[MetricFact], *, issue: bool) -> dict[tuple[str, ...], list[MetricFact]]:
    grouped: dict[tuple[str, ...], list[MetricFact]] = {}
    for fact in facts:
        dimensions = fact.dimensions
        key = (
            (
                dimensions.get("severity", ""),
                dimensions.get("resolution", "unknown_resolution"),
                dimensions.get("issue_type", "unknown_issue"),
                dimensions.get("country", ""),
            )
            if issue
            else (dimensions.get("country", ""), dimensions.get("reporting_context", ""))
        )
        if all(key):
            grouped.setdefault(key, []).append(fact)
    return grouped


def _numeric(facts: list[MetricFact], name: str) -> float | int | None:
    fact = next((item for item in facts if item.name == name), None)
    return fact.value if fact is not None and isinstance(fact.value, int | float) else None


def _dimension(facts: list[MetricFact], name: str) -> str | None:
    return next((value for fact in facts if (value := fact.dimensions.get(name))), None)


def _priority(severity: str, product_count: float | int | None, index: int) -> int:
    base = 18 if severity == "DISAPPROVED" else 34
    if product_count and product_count >= 10:
        base -= 4
    return max(1, min(base + index, 59))


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_")[:80]


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
