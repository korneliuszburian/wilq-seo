"""Compatibility facade for decomposed content refresh actions."""

from __future__ import annotations

import sys as _sys
from collections.abc import (
    Iterable,
    Mapping,
)
from dataclasses import dataclass
from types import ModuleType as _ModuleType
from typing import Any
from urllib.parse import urlparse

from wilq.actions.metric_utils import (
    metric_sentence,
    prioritize_action_metrics,
    unique_values,
)
from wilq.actions.wordpress_payload_preview import build_wordpress_draft_payload_preview
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    MetricFact,
    OpportunityDomain,
)

from . import core as _core
from . import delivery as _delivery
from . import queue as _queue
from . import review as _review
from . import shared as _shared
from . import store as _store
from .core import *  # noqa: F401,F403
from .core import content_refresh_payload_from_metric_facts  # noqa: F401
from .delivery import *  # noqa: F401,F403
from .delivery import (  # noqa: F401
    content_payload_with_reviewed_wordpress_draft_previews,
    post_publication_measurement_plan,
    post_publication_measurement_summary,
)
from .queue import *  # noqa: F401,F403
from .queue import (  # noqa: F401
    ContentRefreshMetricCandidate,
    content_refresh_metric_candidate,
    content_refresh_queue_action,
    seed_content_refresh_action,
)
from .review import *  # noqa: F401,F403
from .review import (  # noqa: F401
    content_contract_label,
    content_contract_labels,
    content_url_review_contract,
)
from .shared import *  # noqa: F401,F403
from .shared import (  # noqa: F401
    AHREFS_GAP_FACT_NAMES,
    AHREFS_OFF_TOPIC_TERMS,
    AHREFS_RELEVANCE_TERMS,
    AHREFS_RELEVANT_COMPETITOR_DOMAINS,
    CONTENT_BLOCKED_CLAIMS,
    CONTENT_BRIEF_PREVIEW_CONTRACT,
    CONTENT_CONTRACT_LABELS,
    CONTENT_REFRESH_ACTION_TYPE,
    CONTENT_SOURCE_CONNECTORS,
    CONTENT_SOURCE_SITE_HOSTS,
    CONTENT_URL_REVIEW_CONTRACT,
    GSC_METRIC_NAMES,
    POST_PUBLICATION_MEASUREMENT_PLAN_CONTRACT,
    WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT,
)
from .store import *  # noqa: F401,F403

__all__ = [
    "annotations",
    "Iterable",
    "Mapping",
    "dataclass",
    "Any",
    "urlparse",
    "metric_sentence",
    "prioritize_action_metrics",
    "unique_values",
    "build_wordpress_draft_payload_preview",
    "connector_evidence_id",
    "ActionMode",
    "ActionObject",
    "ActionRisk",
    "ActionStatus",
    "MetricFact",
    "OpportunityDomain",
    "CONTENT_REFRESH_ACTION_TYPE",
    "CONTENT_BRIEF_PREVIEW_CONTRACT",
    "CONTENT_URL_REVIEW_CONTRACT",
    "WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT",
    "POST_PUBLICATION_MEASUREMENT_PLAN_CONTRACT",
    "CONTENT_SOURCE_SITE_HOSTS",
    "CONTENT_SOURCE_CONNECTORS",
    "seed_content_refresh_action",
    "content_refresh_queue_action",
    "ContentRefreshMetricCandidate",
    "content_refresh_metric_candidate",
    "GSC_METRIC_NAMES",
    "AHREFS_GAP_FACT_NAMES",
    "AHREFS_RELEVANCE_TERMS",
    "AHREFS_RELEVANT_COMPETITOR_DOMAINS",
    "AHREFS_OFF_TOPIC_TERMS",
    "CONTENT_BLOCKED_CLAIMS",
    "CONTENT_CONTRACT_LABELS",
    "content_refresh_payload_from_metric_facts",
    "content_url_review_contract",
    "content_contract_label",
    "content_contract_labels",
    "content_payload_with_reviewed_wordpress_draft_previews",
    "post_publication_measurement_plan",
    "post_publication_measurement_summary",
]

_FORWARD_TARGETS = (_shared, _store, _review, _delivery, _core, _queue)


class _ContentRefreshFacade(_ModuleType):
    """Forward legacy monkeypatch targets to every decomposed binding."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for target in _FORWARD_TARGETS:
            if name in vars(target):
                setattr(target, name, value)


_sys.modules[__name__].__class__ = _ContentRefreshFacade
