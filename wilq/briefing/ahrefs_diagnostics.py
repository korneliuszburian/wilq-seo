"""Compatibility facade; decomposed — see wilq/briefing/ahrefs/."""

import sys
from types import ModuleType

from wilq.briefing.ahrefs import authority as _authority
from wilq.briefing.ahrefs import core as _core
from wilq.briefing.ahrefs import gap_records as _gap_records
from wilq.briefing.ahrefs import keywords as _keywords
from wilq.briefing.ahrefs import labels as _labels
from wilq.briefing.ahrefs import shared as _shared
from wilq.briefing.ahrefs.authority import _missing_authority_summary  # noqa: F401
from wilq.briefing.ahrefs.core import build_ahrefs_diagnostics  # noqa: F401
from wilq.briefing.ahrefs.gap_records import (  # noqa: F401
    AHREFS_GAP_BLOCKED_CLAIMS,
    AHREFS_GAP_IMPACT_BLOCKED_CLAIMS,
    AHREFS_GAP_READ_CONTRACTS,
    AHREFS_GAP_TYPES,
    AHREFS_REVIEWABLE_GAP_RECORD_LIMIT,
    AhrefsGapCrossCheck,
    _apply_exact_wordpress_cross_checks,
)
from wilq.briefing.ahrefs.keywords import (  # noqa: F401
    AHREFS_BROAD_BACKLINK_DOMAINS,
    AHREFS_EKOLOGUS_RELEVANCE_TERMS,
    AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS,
    AHREFS_OFF_TOPIC_TERMS,
    AHREFS_RELEVANCE_STOPWORDS,
    AHREFS_RELEVANT_COMPETITOR_DOMAINS,
    POLISH_ASCII_TRANSLATION,
)
from wilq.briefing.ahrefs.labels import (  # noqa: F401
    AHREFS_DECISION_TYPE_LABELS,
    AHREFS_GAP_TYPE_LABELS,
    AHREFS_METRIC_FACT_LABELS,
    AHREFS_READ_CONTRACT_LABELS,
    AHREFS_REVIEW_GATE_LABELS,
    _ahrefs_connector_status_label,
    _ahrefs_refresh_status_label,
    _ahrefs_status_label,
)
from wilq.briefing.ahrefs.shared import (  # noqa: F401
    AHREFS_AUTHORITY_FACT_NAMES,
    AHREFS_COMPETITOR_READ_FACT_NAMES,
    AHREFS_CONNECTOR_ID,
    AHREFS_CONTENT_REFRESH_ACTION_ID,
    AHREFS_CROSS_CHECK_CONNECTOR_IDS,
    AHREFS_CROSS_CHECK_METRIC_FACT_LIMIT,
    AHREFS_EXPERT_RULE_IDS,
    AHREFS_GAP_FACT_NAMES,
    AHREFS_KNOWLEDGE_CARD_IDS,
    AHREFS_METRIC_FACT_LIMIT,
    AhrefsBudgetStageStatus,
    AhrefsGapType,
    _latest_relevant_ahrefs_refresh,
)

__all__ = [
    "AhrefsBudgetStageStatus",
    "AhrefsGapCrossCheck",
    "AhrefsGapType",
    "AHREFS_AUTHORITY_FACT_NAMES",
    "AHREFS_BROAD_BACKLINK_DOMAINS",
    "AHREFS_COMPETITOR_READ_FACT_NAMES",
    "AHREFS_CONNECTOR_ID",
    "AHREFS_CONTENT_REFRESH_ACTION_ID",
    "AHREFS_CROSS_CHECK_CONNECTOR_IDS",
    "AHREFS_CROSS_CHECK_METRIC_FACT_LIMIT",
    "AHREFS_DECISION_TYPE_LABELS",
    "AHREFS_EKOLOGUS_RELEVANCE_TERMS",
    "AHREFS_EXPERT_RULE_IDS",
    "AHREFS_GAP_BLOCKED_CLAIMS",
    "AHREFS_GAP_FACT_NAMES",
    "AHREFS_GAP_IMPACT_BLOCKED_CLAIMS",
    "AHREFS_GAP_READ_CONTRACTS",
    "AHREFS_GAP_TYPE_LABELS",
    "AHREFS_GAP_TYPES",
    "AHREFS_KNOWLEDGE_CARD_IDS",
    "AHREFS_METRIC_FACT_LABELS",
    "AHREFS_METRIC_FACT_LIMIT",
    "AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS",
    "AHREFS_OFF_TOPIC_TERMS",
    "AHREFS_READ_CONTRACT_LABELS",
    "AHREFS_RELEVANCE_STOPWORDS",
    "AHREFS_RELEVANT_COMPETITOR_DOMAINS",
    "AHREFS_REVIEWABLE_GAP_RECORD_LIMIT",
    "AHREFS_REVIEW_GATE_LABELS",
    "POLISH_ASCII_TRANSLATION",
    "build_ahrefs_diagnostics",
]

_FORWARD_TARGETS = (
    _authority,
    _core,
    _gap_records,
    _keywords,
    _labels,
    _shared,
)


class _Facade(ModuleType):
    """Forward legacy monkeypatch targets to their decomposed owners."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for target in _FORWARD_TARGETS:
            if hasattr(target, name):
                setattr(target, name, value)


sys.modules[__name__].__class__ = _Facade
