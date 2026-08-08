"""Compatibility facade; decomposed — see wilq/briefing/tactical_queue/."""

import sys
from pathlib import Path
from types import ModuleType

__path__ = [str(Path(__file__).with_suffix(""))]

from wilq.briefing.tactical_queue import core as _core
from wilq.briefing.tactical_queue import items as _items
from wilq.briefing.tactical_queue import labels as _labels
from wilq.briefing.tactical_queue import metrics as _metrics
from wilq.briefing.tactical_queue import shared as _shared
from wilq.briefing.tactical_queue.core import (  # noqa: F401
    _build_tactical_queue,
    build_tactical_queue,
    clear_tactical_queue_cache,
)
from wilq.briefing.tactical_queue.items import (  # noqa: F401
    _balanced_tactical_items,
    build_gsc_content_tactical_items,
    is_ahrefs_gap_fact,
    is_reviewable_ahrefs_gap_fact,
)
from wilq.briefing.tactical_queue.labels import (  # noqa: F401
    _merchant_dimension_label,
)
from wilq.briefing.tactical_queue.metrics import (  # noqa: F401
    _tactical_metric_facts,
)
from wilq.briefing.tactical_queue.metrics import (
    metric_store as metric_store,
)
from wilq.briefing.tactical_queue.shared import (  # noqa: F401
    AHREFS_GAP_FACT_NAMES,
    AHREFS_GAP_TYPE_LABELS,
    AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS,
    AHREFS_OFF_TOPIC_TERMS,
    AHREFS_RELEVANT_COMPETITOR_DOMAINS,
    AHREFS_RELEVANT_TERMS,
    DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS,
    GA4_LANDING_FACT_LIMIT,
    GSC_QUERY_PAGE_FACT_LIMIT,
    TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT,
    TACTICAL_QUEUE_DOMAIN_FLOOR,
    TACTICAL_QUEUE_LIMIT,
    TACTICAL_QUEUE_SOURCE_CONNECTORS,
    WORDPRESS_CANONICAL_HOST_ALIASES,
    WORDPRESS_INVENTORY_FACT_LIMIT,
    WORDPRESS_PUBLIC_CONTENT_HOSTS,
    TacticalIntent,
    TacticalQueueCacheEntry,
    WordPressContentIndex,
    WordPressMatch,
    WordPressMatchConfidence,
)

__all__ = [
    "AHREFS_GAP_FACT_NAMES",
    "AHREFS_GAP_TYPE_LABELS",
    "AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS",
    "AHREFS_OFF_TOPIC_TERMS",
    "AHREFS_RELEVANT_COMPETITOR_DOMAINS",
    "AHREFS_RELEVANT_TERMS",
    "DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS",
    "GA4_LANDING_FACT_LIMIT",
    "GSC_QUERY_PAGE_FACT_LIMIT",
    "TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT",
    "TACTICAL_QUEUE_DOMAIN_FLOOR",
    "TACTICAL_QUEUE_LIMIT",
    "TACTICAL_QUEUE_SOURCE_CONNECTORS",
    "TacticalIntent",
    "TacticalQueueCacheEntry",
    "WORDPRESS_CANONICAL_HOST_ALIASES",
    "WORDPRESS_INVENTORY_FACT_LIMIT",
    "WORDPRESS_PUBLIC_CONTENT_HOSTS",
    "WordPressContentIndex",
    "WordPressMatch",
    "WordPressMatchConfidence",
    "build_gsc_content_tactical_items",
    "build_tactical_queue",
    "clear_tactical_queue_cache",
    "is_ahrefs_gap_fact",
    "is_reviewable_ahrefs_gap_fact",
]

_FORWARD_TARGETS = (
    _core,
    _items,
    _labels,
    _metrics,
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
