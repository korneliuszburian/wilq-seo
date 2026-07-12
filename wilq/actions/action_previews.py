from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any

from wilq.actions.content_preview import content_refresh_preview_cards
from wilq.actions.ga4.tracking_preview import (
    ga4_tracking_quality_preview_cards,
    metric_snapshot_preview_rows,
)
from wilq.actions.google_ads.business_context import (
    ADS_STRATEGY_REVIEW_ACTION_TYPE,
    ADS_TARGET_CONFIRMATION_ACTION_TYPE,
    ads_business_context_preview_rows,
    ads_strategy_review_preview_cards,
    ads_target_guardrail_preview_cards,
    micros_money_label,
)
from wilq.actions.google_ads.change_history import (
    CHANGE_HISTORY_IMPACT_PREVIEW_CONTRACT,
    change_history_preview_cards,
)
from wilq.actions.google_ads.custom_segments import custom_segment_preview_cards
from wilq.actions.google_ads.demand_gen import (
    DEMAND_GEN_READINESS_REVIEW_PREVIEW_CONTRACT,
    demand_gen_channel_label,
)
from wilq.actions.google_ads.demand_gen_preview import demand_gen_readiness_preview_cards
from wilq.actions.google_ads.keyword_planner import (
    KEYWORD_PLANNER_ACCESS_ACTION_TYPE,
    keyword_planner_access_preview_cards,
)
from wilq.actions.google_ads.negative_keywords import negative_keyword_preview_cards
from wilq.actions.google_ads.previews import budget_preview_cards
from wilq.actions.google_ads.recommendations import recommendation_preview_cards
from wilq.actions.google_ads.search_term_ngram_preview import search_term_ngram_preview_cards
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_PREVIEW_CONTRACT
from wilq.actions.localo.visibility_preview import (
    local_visibility_preview_cards,
    metric_snapshot_preview_rows_for_keys,
)
from wilq.actions.merchant import MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT
from wilq.actions.merchant_preview import merchant_preview_cards
from wilq.actions.service_profile import (
    knowledge_promotion_preview_cards,
    private_proposal_promotion_preview_cards,
)
from wilq.actions.social import social_draft_input_preview_cards
from wilq.actions.wordpress_preview import wordpress_draft_handoff_preview_cards
from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.schemas import ActionObject, ActionPreviewCardViewModel, ActionPreviewRowViewModel

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
StateLabel = Callable[[Any], str]
PlainMetricLabel = Callable[..., str]
SourceLabels = Callable[[list[str]], list[str]]
MetricLabel = Callable[[str], str]
BusinessContextRows = Callable[[dict[str, Any]], list[ActionPreviewRowViewModel]]
PreviewCards = Callable[[dict[str, Any]], list[ActionPreviewCardViewModel]]


@dataclass(frozen=True)
class ActionPreviewDependencies:
    preview_row: PreviewRow
    string_list: StringList
    apply_state_label: StateLabel
    system_readiness_label: StateLabel
    wordpress_draft_preview_card: Callable[..., ActionPreviewCardViewModel]
    source_connector_labels: SourceLabels
    metric_fact_label: MetricLabel
    plain_metric_value_label: PlainMetricLabel
    action_gate_labels: SourceLabels
    business_context_summary: Callable[[str], str]


def action_preview_cards(
    action: ActionObject,
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
    wordpress_draft_preview_card: Callable[..., ActionPreviewCardViewModel],
    source_connector_labels: SourceLabels,
    metric_fact_label: MetricLabel,
    plain_metric_value_label: PlainMetricLabel,
    action_gate_labels: SourceLabels,
    business_context_summary: Callable[[str], str],
) -> list[ActionPreviewCardViewModel]:
    """Own preview-contract routing while domain modules own card rendering."""
    dependencies = ActionPreviewDependencies(
        preview_row=preview_row,
        string_list=string_list,
        apply_state_label=apply_state_label,
        system_readiness_label=system_readiness_label,
        wordpress_draft_preview_card=wordpress_draft_preview_card,
        source_connector_labels=source_connector_labels,
        metric_fact_label=metric_fact_label,
        plain_metric_value_label=plain_metric_value_label,
        action_gate_labels=action_gate_labels,
        business_context_summary=business_context_summary,
    )
    handlers = _contract_preview_handlers(dependencies)
    contract = action.payload.get("preview_contract")
    handler = handlers.get(contract) if isinstance(contract, str) else None
    if handler is not None:
        return handler(action.payload)
    action_type = action.payload.get("action_type")
    action_handler = (
        _action_type_preview_handlers(dependencies).get(action_type)
        if isinstance(action_type, str)
        else None
    )
    return action_handler(action.payload) if action_handler is not None else action.preview_cards


def _contract_preview_handlers(
    dependencies: ActionPreviewDependencies,
) -> dict[str, PreviewCards]:
    """Map stable preview contracts to their domain-owned renderers."""
    return _contract_preview_handlers_core(dependencies) | _contract_preview_handlers_content(
        dependencies
    )


def _contract_preview_handlers_core(
    dependencies: ActionPreviewDependencies,
) -> dict[str, PreviewCards]:
    """Map vendor and Ads preview contracts to domain renderers."""
    deps = dependencies
    return {
        MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT: partial(
            merchant_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "budget_apply_preview_v1": partial(
            budget_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            micros_money_label=micros_money_label,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "recommendation_apply_preview_v1": partial(
            recommendation_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "custom_segment_change_preview_v1": partial(
            custom_segment_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "negative_keyword_change_preview_v1": partial(
            negative_keyword_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        CHANGE_HISTORY_IMPACT_PREVIEW_CONTRACT: partial(
            change_history_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            action_gate_labels=deps.action_gate_labels,
            blocked_claims=operator_blocked_claims,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        DEMAND_GEN_READINESS_REVIEW_PREVIEW_CONTRACT: partial(
            demand_gen_readiness_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            channel_label=demand_gen_channel_label,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        SEARCH_TERM_NGRAM_PREVIEW_CONTRACT: partial(
            search_term_ngram_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            plain_metric_value_label=deps.plain_metric_value_label,
            micros_money_label=micros_money_label,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
    }


def _contract_preview_handlers_content(
    dependencies: ActionPreviewDependencies,
) -> dict[str, PreviewCards]:
    """Map content, WordPress and knowledge preview contracts."""
    deps = dependencies
    return {
        "ga4_tracking_quality_review_v1": partial(
            ga4_tracking_quality_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            metric_snapshot_rows=metric_snapshot_preview_rows,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "local_visibility_review_preview_v1": partial(
            local_visibility_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            metric_snapshot_rows=metric_snapshot_preview_rows_for_keys,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "content_brief_preview_v1": partial(
            content_refresh_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
            wordpress_draft_preview_card=deps.wordpress_draft_preview_card,
        ),
        "wordpress_draft_handoff_preview_v1": partial(
            wordpress_draft_handoff_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "wordpress_draft_apply_preview_v1": partial(
            wordpress_draft_handoff_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "service_profile_knowledge_promotion_preview_v1": partial(
            knowledge_promotion_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "private_source_proposal_promotion_preview_v1": partial(
            private_proposal_promotion_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
    }


def _action_type_preview_handlers(
    dependencies: ActionPreviewDependencies,
) -> dict[str, PreviewCards]:
    """Map action-only preview routes to their domain-owned renderers."""
    deps = dependencies
    business_context_rows: BusinessContextRows = partial(
        ads_business_context_preview_rows,
        preview_row=deps.preview_row,
        plain_metric_value_label=deps.plain_metric_value_label,
        micros_money_label=micros_money_label,
    )
    return {
        KEYWORD_PLANNER_ACCESS_ACTION_TYPE: partial(
            keyword_planner_access_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
        ),
        ADS_TARGET_CONFIRMATION_ACTION_TYPE: partial(
            ads_target_guardrail_preview_cards,
            business_context_rows=business_context_rows,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        ADS_STRATEGY_REVIEW_ACTION_TYPE: partial(
            ads_strategy_review_preview_cards,
            business_context_rows=business_context_rows,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            strategy_summary=deps.business_context_summary,
            apply_state_label=deps.apply_state_label,
            system_readiness_label=deps.system_readiness_label,
        ),
        "linkedin_post_candidate": partial(
            social_draft_input_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            source_connector_labels=deps.source_connector_labels,
            metric_fact_label=deps.metric_fact_label,
            plain_metric_value_label=deps.plain_metric_value_label,
            apply_state_label=deps.apply_state_label,
        ),
        "facebook_post_candidate": partial(
            social_draft_input_preview_cards,
            preview_row=deps.preview_row,
            string_list=deps.string_list,
            source_connector_labels=deps.source_connector_labels,
            metric_fact_label=deps.metric_fact_label,
            plain_metric_value_label=deps.plain_metric_value_label,
            apply_state_label=deps.apply_state_label,
        ),
    }
