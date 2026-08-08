"""Compatibility facade; decomposed — see wilq/briefing/merchant/."""

import sys
from types import ModuleType

from wilq.briefing.merchant import core as _core
from wilq.briefing.merchant import feed_quality as _feed_quality
from wilq.briefing.merchant import labels as _labels
from wilq.briefing.merchant import operator_summary as _operator_summary
from wilq.briefing.merchant import products as _products
from wilq.briefing.merchant import shared as _shared
from wilq.briefing.merchant.core import (  # noqa: F401
    MerchantDiagnosticsCacheEntry,
    build_merchant_diagnostics,
    build_merchant_diagnostics_cached,
    clear_merchant_diagnostics_cache,
)
from wilq.briefing.merchant.feed_quality import (  # noqa: F401
    _merchant_attribute_key,
    _merchant_freshness_assessment,
)
from wilq.briefing.merchant.labels import (  # noqa: F401
    _merchant_connector_status_label,
    _merchant_freshness_label,
    _merchant_product_performance_readiness_with_operator_labels,
    _merchant_refresh_status_label,
    _merchant_risk_label,
    _merchant_status_label,
)
from wilq.briefing.merchant.products import (  # noqa: F401
    _merchant_price_impact_readiness,
    _merchant_product_performance_readiness,
    _product_performance_metric_facts_by_connector,
)
from wilq.briefing.merchant.shared import _latest_connector_refresh  # noqa: F401

__all__ = _core.__all__

_FORWARD_TARGETS = (
    _core,
    _feed_quality,
    _labels,
    _operator_summary,
    _products,
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
