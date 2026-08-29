from __future__ import annotations

from ._contract import AdjudicationError
from ._models import (
    NoindexAdjudicationSources,
    ReconciliationResult,
    RetainedAuthorities,
    SourceArtifact,
)
from ._policy import PRODUCTION_EXPECTATIONS
from ._service import _validate_retained_authorities
from ._service import reconcile_noindex_adjudication as _reconcile

__all__ = [
    "AdjudicationError",
    "NoindexAdjudicationSources",
    "ReconciliationResult",
    "RetainedAuthorities",
    "SourceArtifact",
    "reconcile_noindex_adjudication",
    "validate_retained_noindex_authorities",
]


def reconcile_noindex_adjudication(
    sources: NoindexAdjudicationSources,
) -> ReconciliationResult:
    return _reconcile(sources, expectations=PRODUCTION_EXPECTATIONS)


def validate_retained_noindex_authorities(
    ledger_bytes: bytes,
    journal_bytes: bytes,
) -> RetainedAuthorities:
    return _validate_retained_authorities(
        ledger_bytes,
        journal_bytes,
        expectations=PRODUCTION_EXPECTATIONS,
    )
