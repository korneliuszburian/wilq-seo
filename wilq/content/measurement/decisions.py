from __future__ import annotations

from collections.abc import Iterable

from wilq.schemas import (
    ActionRisk,
    ContentDecisionItem,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
)


def ga4_tracking_gap_decisions(
    items: list[TacticalQueueItem],
    *,
    knowledge_card_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
) -> list[ContentDecisionItem]:
    tracking_gaps = [
        item
        for item in _unique_tactical_items(items)
        if item.domain == OpportunityDomain.ga4 and item.intent == "tracking_gap"
    ]
    if not tracking_gaps:
        return []
    evidence_ids = _unique(
        evidence_id for item in tracking_gaps for evidence_id in item.evidence_ids
    )
    metric_facts = _unique_metric_facts(
        fact for item in tracking_gaps for fact in item.metric_facts
    )
    return [
        ContentDecisionItem(
            id="content_decision_ga4_tracking_gap_block",
            decision_type="block_as_tracking_not_content",
            status="blocked",
            title="Zablokuj braki w pomiarze GA4 jako zadania contentowe",
            priority=12,
            metric_tiles={
                "blokady": len(tracking_gaps),
                "dowody": len(evidence_ids),
                "braki pomiaru": len(tracking_gaps),
            },
            source_connectors=["google_analytics_4"],
            evidence_ids=evidence_ids,
            metric_facts=metric_facts[:8],
            action_ids=_unique(
                action_id for item in tracking_gaps for action_id in item.action_ids
            ),
            knowledge_card_ids=list(knowledge_card_ids),
            expert_rule_ids=list(expert_rule_ids),
            blocked_claims=_unique(
                [
                    *(claim for item in tracking_gaps for claim in item.blocked_claims),
                    "przepisanie treści",
                    "wzrost konwersji",
                    "zwrot z reklam",
                ]
            ),
            rationale=(
                "GA4 `(not set)` i tracking_gap wskazują problem pomiaru, "
                "nie gotową rekomendację treści."
            ),
            next_step="Przekaż do sprawdzenia trackingu GA4 zamiast tworzyć rewrite treści.",
            risk=ActionRisk.medium,
        )
    ]


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _unique_tactical_items(items: Iterable[TacticalQueueItem]) -> list[TacticalQueueItem]:
    unique_items: dict[str, TacticalQueueItem] = {}
    for item in items:
        unique_items.setdefault(item.id, item)
    return list(unique_items.values())


def _unique_metric_facts(values: Iterable[MetricFact]) -> list[MetricFact]:
    unique_facts: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in values:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted((str(key), str(value)) for key, value in fact.dimensions.items())),
        )
        unique_facts.setdefault(key, fact)
    return list(unique_facts.values())
