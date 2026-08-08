"""Compatibility facade; decomposed — see wilq/briefing/ads/."""

import sys
from types import ModuleType

from wilq.briefing.ads import core as _core
from wilq.briefing.ads import search_terms as _search_terms
from wilq.briefing.ads.core import *  # noqa: F403
from wilq.briefing.ads.core import (  # noqa: F401
    build_ads_diagnostics,
    build_ads_diagnostics_summary_cached,
    clear_ads_summary_cache,
)

metric_store = _search_terms.metric_store
_latest_google_ads_refresh = _core._latest_google_ads_refresh
__all__ = _core.__all__


class _AdsDiagnosticsFacade(ModuleType):
    """Forward legacy monkeypatch targets to their decomposed owners."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        target = {
            "build_ads_diagnostics": _core,
            "metric_store": _search_terms,
            "_latest_google_ads_refresh": _core,
        }.get(name)
        if target is not None:
            setattr(target, name, value)


sys.modules[__name__].__class__ = _AdsDiagnosticsFacade
