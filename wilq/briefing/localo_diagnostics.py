"""Compatibility facade; decomposed — see wilq/briefing/localo/."""

import sys
from types import ModuleType

from wilq.briefing.localo import competitors as _competitors
from wilq.briefing.localo import core as _core
from wilq.briefing.localo import labels as _labels
from wilq.briefing.localo import reviews as _reviews
from wilq.briefing.localo import shared as _shared
from wilq.briefing.localo import visibility as _visibility
from wilq.briefing.localo.core import build_localo_diagnostics  # noqa: F401
from wilq.briefing.localo.labels import (  # noqa: F401
    _localo_bool_label,
    _localo_connector_status_label,
    _localo_decision_status_label,
    _localo_decision_type_label,
    _localo_read_contract_status_label,
    _localo_refresh_status_label,
    _localo_section_status_label,
    _localo_token_presence_label,
)
from wilq.briefing.localo.shared import (  # noqa: F401
    LOCALO_BLOCKED_CLAIMS,
    LOCALO_CONNECTOR_ID,
    LOCALO_CONTRACT_FACT_NAMES,
    LOCALO_CONTRACT_ORDER,
    LOCALO_EXPERT_RULE_IDS,
    LOCALO_KNOWLEDGE_CARD_IDS,
    LOCALO_METRIC_FACT_LIMIT,
    LOCALO_PROBE_METRIC_NAMES,
    LOCALO_VISIBILITY_READ_CONTRACTS,
    _localo_contract_evidence_kind,
)

__all__ = [
    "LOCALO_BLOCKED_CLAIMS",
    "LOCALO_CONNECTOR_ID",
    "LOCALO_CONTRACT_FACT_NAMES",
    "LOCALO_CONTRACT_ORDER",
    "LOCALO_EXPERT_RULE_IDS",
    "LOCALO_KNOWLEDGE_CARD_IDS",
    "LOCALO_METRIC_FACT_LIMIT",
    "LOCALO_PROBE_METRIC_NAMES",
    "LOCALO_VISIBILITY_READ_CONTRACTS",
    "build_localo_diagnostics",
]

_FORWARD_TARGETS = (
    _competitors,
    _core,
    _labels,
    _reviews,
    _shared,
    _visibility,
)


class _Facade(ModuleType):
    """Forward legacy monkeypatch targets to their decomposed owners."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for target in _FORWARD_TARGETS:
            if hasattr(target, name):
                setattr(target, name, value)


sys.modules[__name__].__class__ = _Facade
