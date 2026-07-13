from __future__ import annotations

from collections.abc import Callable

from wilq.schemas import ActionObject, MetricFact

ActionFactory = Callable[..., ActionObject | None]


def seed_metric_actions(
    *,
    google_ads_facts: list[MetricFact],
    ga4_facts: list[MetricFact],
    latest_google_ads_evidence_ids: list[str],
    latest_ga4_evidence_ids: list[str],
    demand_gen_action: ActionFactory,
    campaign_review_action: ActionFactory,
    recommendation_action: ActionFactory,
    change_history_action: ActionFactory,
    search_term_ngram_action: ActionFactory,
    custom_segment_action: ActionFactory,
    negative_keyword_action: ActionFactory,
) -> dict[str, ActionObject]:
    actions: dict[str, ActionObject] = {}
    demand_gen = demand_gen_action(
        google_ads_facts,
        ga4_facts,
        latest_google_ads_evidence_ids=latest_google_ads_evidence_ids,
        latest_ga4_evidence_ids=latest_ga4_evidence_ids,
    )
    _add_action(actions, demand_gen)
    _add_action(actions, campaign_review_action(google_ads_facts))
    _add_action(actions, recommendation_action(google_ads_facts))
    _add_action(actions, change_history_action(google_ads_facts))
    _add_action(actions, search_term_ngram_action(google_ads_facts))
    _add_action(actions, custom_segment_action(google_ads_facts))
    _add_action(actions, negative_keyword_action(google_ads_facts))
    return actions


def _add_action(actions: dict[str, ActionObject], action: ActionObject | None) -> None:
    if action is not None:
        actions[action.id] = action
