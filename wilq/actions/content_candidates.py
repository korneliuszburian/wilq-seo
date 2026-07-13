from __future__ import annotations

from collections.abc import Callable

from wilq.actions.content_refresh import ContentRefreshMetricCandidate
from wilq.schemas import ActionObject, MetricFact

ContentCandidateBuilder = Callable[[list[MetricFact]], ContentRefreshMetricCandidate | None]
DraftHandoffBuilder = Callable[..., ActionObject | None]
DraftApplyBuilder = Callable[..., ActionObject]


def seed_metric_actions(
    *,
    content_facts: list[MetricFact],
    candidate_builder: ContentCandidateBuilder,
    draft_handoff_builder: DraftHandoffBuilder,
    draft_apply_builder: DraftApplyBuilder,
) -> dict[str, ActionObject]:
    candidate = candidate_builder(content_facts)
    if candidate is None:
        return {}
    actions = {candidate.action.id: candidate.action}
    handoff_action = draft_handoff_builder(
        content_payload=candidate.payload,
        content_action_metrics=candidate.action_metrics,
    )
    if handoff_action is None:
        return actions
    actions[handoff_action.id] = handoff_action
    apply_action = draft_apply_builder(handoff_action=handoff_action)
    actions[apply_action.id] = apply_action
    return actions
