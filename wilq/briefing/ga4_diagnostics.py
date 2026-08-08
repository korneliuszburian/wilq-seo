"""Compatibility facade; decomposed — see wilq/briefing/ga4/."""

import sys
from types import ModuleType

from wilq.briefing.ga4 import conversions as _conversions
from wilq.briefing.ga4 import core as _core
from wilq.briefing.ga4 import labels as _labels
from wilq.briefing.ga4 import measurement as _measurement
from wilq.briefing.ga4 import shared as _shared
from wilq.briefing.ga4 import traffic as _traffic
from wilq.briefing.ga4.conversions import _ga4_read_contract_labels  # noqa: F401
from wilq.briefing.ga4.core import (  # noqa: F401
    DEFAULT_GA4_DIAGNOSTICS_CACHE_SECONDS,
    Ga4DiagnosticsCacheEntry,
    _ga4_diagnostics_cache_seconds,
    build_ga4_diagnostics,
    build_ga4_diagnostics_cached,
    clear_ga4_diagnostics_cache,
    ga4_diagnostics_cache_ready,
    monotonic,
)
from wilq.briefing.ga4.labels import (  # noqa: F401
    GA4_DECISION_TYPE_LABELS,
    GA4_METRIC_DIMENSION_LABELS,
    GA4_METRIC_FACT_LABELS,
    GA4_READ_CONTRACT_LABELS,
    GA4_SECTION_LABELS,
    GA4_WORDPRESS_MATCH_CONFIDENCE_LABELS,
    GA4_WORDPRESS_MATCH_LABELS,
    _ga4_connector_status_label,
    _ga4_decision_with_marketer_labels,
    _ga4_freshness_label,
    _ga4_optional_label,
    _ga4_refresh_status_label,
    _ga4_risk_label,
    _ga4_section_status_label,
)
from wilq.briefing.ga4.measurement import (  # noqa: F401
    _ga4_freshness_assessment,
    _latest_ga4_refresh,
)
from wilq.briefing.ga4.shared import (  # noqa: F401
    GA4_CONNECTOR_ID,
    GA4_CONVERSION_BLOCKED_CLAIMS,
    GA4_CONVERSION_METRIC_NAMES,
    GA4_EXPERT_RULE_IDS,
    GA4_KNOWLEDGE_CARD_IDS,
    GA4_METRIC_FACT_LIMIT,
    GA4_STALE_AFTER_HOURS,
    Ga4DecisionType,
)

__all__ = [
    "DEFAULT_GA4_DIAGNOSTICS_CACHE_SECONDS",
    "GA4_CONNECTOR_ID",
    "GA4_CONVERSION_BLOCKED_CLAIMS",
    "GA4_CONVERSION_METRIC_NAMES",
    "GA4_DECISION_TYPE_LABELS",
    "GA4_EXPERT_RULE_IDS",
    "GA4_KNOWLEDGE_CARD_IDS",
    "GA4_METRIC_DIMENSION_LABELS",
    "GA4_METRIC_FACT_LABELS",
    "GA4_METRIC_FACT_LIMIT",
    "GA4_READ_CONTRACT_LABELS",
    "GA4_SECTION_LABELS",
    "GA4_STALE_AFTER_HOURS",
    "GA4_WORDPRESS_MATCH_CONFIDENCE_LABELS",
    "GA4_WORDPRESS_MATCH_LABELS",
    "Ga4DecisionType",
    "Ga4DiagnosticsCacheEntry",
    "build_ga4_diagnostics",
    "build_ga4_diagnostics_cached",
    "clear_ga4_diagnostics_cache",
    "ga4_diagnostics_cache_ready",
]

_FORWARD_TARGETS = (
    _conversions,
    _core,
    _labels,
    _measurement,
    _shared,
    _traffic,
)


class _Facade(ModuleType):
    """Forward legacy monkeypatch targets to their decomposed owners."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for target in _FORWARD_TARGETS:
            if hasattr(target, name):
                setattr(target, name, value)


sys.modules[__name__].__class__ = _Facade
