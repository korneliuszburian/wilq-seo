"""Compatibility facade for decomposed Google Ads schemas."""

from __future__ import annotations

import sys as _sys
from datetime import datetime
from types import ModuleType as _ModuleType
from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
    model_serializer,
    model_validator,
)

from wilq.operator_labels import (
    action_count_label,
    ads_campaign_status_label,
    ads_channel_type_label,
    blocked_claim_count_label,
    blocked_claim_label,
    evidence_count_label,
    missing_contract_count_label,
    policy_count_label,
    required_validation_count_label,
    source_contract_count_label,
)

from ..actions import (
    ActionPreviewCardViewModel,
    ActionReviewOutcome,
)
from ..core import (
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorStatus,
    MetricFact,
    utc_now,
)
from . import business as _business
from . import contracts as _contracts
from . import custom_segments as _custom_segments
from . import demand_gen as _demand_gen
from . import diagnostics as _diagnostics
from . import labels as _labels
from . import negative_keywords as _negative_keywords
from . import optimizer as _optimizer
from .business import *  # noqa: F401,F403
from .business import (  # noqa: F401
    AdsBusinessContextReadContract,
    AdsBusinessTargetInterpretation,
    AdsDerivedKpiReadContract,
    AdsDerivedKpiRow,
    AdsStrategyReviewReadinessContract,
)
from .contracts import (  # noqa: F401
    AdsAggregationContract,
    AdsBlockedHandoff,
    AdsDecisionItem,
    AdsDiagnosticSection,
    AdsDiagnosticsResponse,
    AdsFreshnessAssessment,
    AdsOperatorSummary,
)
from .custom_segments import *  # noqa: F401,F403
from .custom_segments import (  # noqa: F401
    AdsCustomSegmentApplySafetyReview,
    AdsCustomSegmentAudienceForecastReadContract,
    AdsCustomSegmentAudienceForecastRow,
    AdsCustomSegmentCandidate,
    AdsCustomSegmentPayloadPreview,
    AdsCustomSegmentSourceQuality,
    AdsCustomSegmentsReadContract,
    AdsCustomSegmentTargetingPreview,
    default_ads_custom_segment_audience_forecast_contract,
)
from .demand_gen import *  # noqa: F401,F403
from .demand_gen import (  # noqa: F401
    DemandGenAdGroupAdRow,
    DemandGenCampaignModeReviewRow,
    DemandGenCreativeAssetRow,
    DemandGenLandingQualityRow,
)
from .diagnostics import *  # noqa: F401,F403
from .diagnostics import (  # noqa: F401
    AdsAccountCurrencyReadContract,
    AdsCampaignMetricRow,
    AdsCampaignReadContract,
    AdsCampaignTriageReadContract,
    AdsCampaignTriageRow,
    AdsChangeHistoryReadContract,
    AdsChangeHistoryRow,
    AdsChangeImpactReadinessContract,
    AdsChangeImpactReadinessRow,
    AdsImpressionShareReadContract,
    AdsImpressionShareRow,
    AdsLandingServiceBinding,
    AdsSearchTermCampaignReviewRow,
    AdsSearchTermCoverage,
    AdsSearchTermMetricRow,
    AdsSearchTermNgramReadContract,
    AdsSearchTermNgramRow,
    AdsSearchTermReviewRow,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermSafetyRow,
    AdsSearchTermsReadContract,
)
from .labels import *  # noqa: F401,F403
from .negative_keywords import *  # noqa: F401,F403
from .negative_keywords import (  # noqa: F401
    AdsKeywordMatchContextReadContract,
    AdsKeywordMatchContextRow,
    AdsKeywordPlannerIdeaRow,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordCandidate,
    AdsNegativeKeywordPayloadPreview,
    AdsNegativeKeywordsReadContract,
)
from .optimizer import *  # noqa: F401,F403
from .optimizer import (  # noqa: F401 *  # noqa: F401,F403
    AdsBudgetApplyPreview,
    AdsBudgetApplySafetyReview,
    AdsBudgetPacingReadContract,
    AdsBudgetPacingRow,
    AdsOptimizerReadinessContract,
    AdsOptimizerReadinessItem,
    AdsRecommendationApplyPreview,
    AdsRecommendationRow,
    AdsRecommendationsReadContract,
    AdsSharedBudgetCampaignShare,
    AdsSharedBudgetDistributionRow,
)

__all__ = [
    "annotations",
    "datetime",
    "Any",
    "Literal",
    "BaseModel",
    "Field",
    "model_serializer",
    "model_validator",
    "action_count_label",
    "ads_campaign_status_label",
    "ads_channel_type_label",
    "blocked_claim_count_label",
    "blocked_claim_label",
    "evidence_count_label",
    "missing_contract_count_label",
    "policy_count_label",
    "required_validation_count_label",
    "source_contract_count_label",
    "ActionPreviewCardViewModel",
    "ActionReviewOutcome",
    "ActionRisk",
    "ConnectorRefreshRun",
    "ConnectorStatus",
    "MetricFact",
    "utc_now",
    "AdsDiagnosticSection",
    "AdsBlockedHandoff",
    "AdsCampaignMetricRow",
    "AdsCampaignReadContract",
    "AdsAccountCurrencyReadContract",
    "AdsBusinessTargetInterpretation",
    "AdsStrategyReviewReadinessContract",
    "AdsBusinessContextReadContract",
    "AdsDerivedKpiRow",
    "AdsDerivedKpiReadContract",
    "AdsBudgetApplySafetyReview",
    "AdsBudgetApplyPreview",
    "AdsBudgetPacingRow",
    "AdsSharedBudgetCampaignShare",
    "AdsSharedBudgetDistributionRow",
    "AdsBudgetPacingReadContract",
    "AdsRecommendationApplyPreview",
    "AdsRecommendationRow",
    "AdsRecommendationsReadContract",
    "AdsImpressionShareRow",
    "AdsImpressionShareReadContract",
    "AdsCampaignTriageRow",
    "AdsCampaignTriageReadContract",
    "AdsOptimizerReadinessItem",
    "AdsOptimizerReadinessContract",
    "AdsChangeHistoryRow",
    "AdsChangeHistoryReadContract",
    "AdsChangeImpactReadinessRow",
    "AdsChangeImpactReadinessContract",
    "AdsLandingServiceBinding",
    "AdsSearchTermMetricRow",
    "AdsSearchTermCoverage",
    "AdsSearchTermsReadContract",
    "AdsSearchTermReviewRow",
    "AdsSearchTermCampaignReviewRow",
    "AdsSearchTermReviewSummaryContract",
    "AdsSearchTermNgramRow",
    "AdsSearchTermNgramReadContract",
    "AdsSearchTermSafetyRow",
    "AdsSearchTermSafetyReadContract",
    "AdsKeywordMatchContextRow",
    "AdsKeywordMatchContextReadContract",
    "AdsCustomSegmentTargetingPreview",
    "AdsCustomSegmentApplySafetyReview",
    "AdsCustomSegmentPayloadPreview",
    "AdsCustomSegmentAudienceForecastRow",
    "AdsCustomSegmentAudienceForecastReadContract",
    "default_ads_custom_segment_audience_forecast_contract",
    "AdsKeywordPlannerIdeaRow",
    "AdsKeywordPlannerReadContract",
    "AdsCustomSegmentSourceQuality",
    "AdsCustomSegmentCandidate",
    "AdsCustomSegmentsReadContract",
    "AdsNegativeKeywordPayloadPreview",
    "AdsNegativeKeywordCandidate",
    "AdsNegativeKeywordsReadContract",
    "AdsDecisionItem",
    "AdsOperatorSummary",
    "AdsFreshnessAssessment",
    "AdsAggregationContract",
    "AdsDiagnosticsResponse",
    "DemandGenAdGroupAdRow",
    "DemandGenCreativeAssetRow",
    "DemandGenLandingQualityRow",
    "DemandGenCampaignModeReviewRow",
]

_FORWARD_TARGETS = (
    _labels,
    _diagnostics,
    _optimizer,
    _business,
    _custom_segments,
    _negative_keywords,
    _demand_gen,
    _contracts,
)


class _AdsSchemaFacade(_ModuleType):
    """Forward legacy monkeypatch targets to decomposed schema modules."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for target in _FORWARD_TARGETS:
            if name in vars(target):
                setattr(target, name, value)


_sys.modules[__name__].__class__ = _AdsSchemaFacade
