"""Bounded deadline for regulatory source fact proposal turns.

A live regulatory fact turn exceeded the 120-second transport default. Like the
planning runtime contract, this bound keeps real margin for the full turn.
"""

from __future__ import annotations

import math
from os import environ

DEFAULT_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS = 900.0


def regulatory_fact_proposal_timeout_seconds() -> float:
    try:
        configured = float(
            environ.get(
                "WILQ_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS",
                str(DEFAULT_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        configured = DEFAULT_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS
    if not math.isfinite(configured):
        configured = DEFAULT_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS
    return max(5.0, configured)


__all__ = [
    "DEFAULT_REGULATORY_FACT_PROPOSAL_TIMEOUT_SECONDS",
    "regulatory_fact_proposal_timeout_seconds",
]
