"""Compatibility facade; decomposed — see wilq/briefing/command_center/."""

import sys
from pathlib import Path
from types import ModuleType

__path__ = [str(Path(__file__).with_suffix(""))]

from wilq.briefing.command_center import actions as _actions
from wilq.briefing.command_center import core as _core
from wilq.briefing.command_center import daily_check as _daily_check
from wilq.briefing.command_center import labels as _labels
from wilq.briefing.command_center import metrics as _metrics
from wilq.briefing.command_center import shared as _shared
from wilq.briefing.command_center import tactical_queue as _tactical_queue
from wilq.briefing.command_center.actions import (  # noqa: F401
    build_command_center_action_plan,
)
from wilq.briefing.command_center.core import (  # noqa: F401
    build_command_center_brief,
    build_command_center_response,
)
from wilq.briefing.command_center.daily_check import build_daily_decisions  # noqa: F401
from wilq.briefing.command_center.labels import _decision_state_label  # noqa: F401
from wilq.briefing.command_center.metrics import (  # noqa: F401
    _localo_metric_facts_for_run,
    _source_connectors_with_evidence,
    command_center_metric_fact_limits,
)
from wilq.briefing.command_center.shared import (  # noqa: F401
    AHREFS_COMMAND_CENTER_METRIC_FACT_LIMIT,
    GA4_COMMAND_CENTER_METRIC_FACT_LIMIT,
    GOOGLE_ADS_COMMAND_CENTER_METRIC_FACT_LIMIT,
    MERCHANT_COMMAND_CENTER_METRIC_FACT_LIMIT,
)
from wilq.briefing.command_center.tactical_queue import (  # noqa: F401
    _ads_business_context_item_from_facts,
    _ads_item_from_facts,
    _content_item_from_tactical,
    _ga4_item_from_tactical,
    _merchant_item_from_tactical,
    tactical_item_count,
)
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION  # noqa: F401
from wilq.connectors.registry import get_connector_status as get_connector_status
from wilq.storage.local_state import local_state_store as local_state_store
from wilq.storage.metric_store import metric_store as metric_store

__all__ = [
    "build_command_center_action_plan",
    "build_command_center_brief",
    "build_command_center_response",
    "build_daily_decisions",
    "command_center_metric_fact_limits",
    "tactical_item_count",
]

_FORWARD_TARGETS = (
    _actions,
    _core,
    _daily_check,
    _labels,
    _metrics,
    _shared,
    _tactical_queue,
)


class _Facade(ModuleType):
    """Forward legacy monkeypatch targets to their decomposed owners."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for target in _FORWARD_TARGETS:
            if hasattr(target, name):
                setattr(target, name, value)


sys.modules[__name__].__class__ = _Facade
