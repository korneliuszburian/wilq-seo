"""Bounded deadline for single-section repair turns.

An Operat repair turn hit the 120-second transport default and ended with
``runtime_failed``; this contract keeps real margin for a full single-section
repair turn.
"""

from __future__ import annotations

import math
from os import environ

DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS = 900.0


def section_repair_timeout_seconds() -> float:
    try:
        configured = float(
            environ.get(
                "WILQ_SECTION_REPAIR_TIMEOUT_SECONDS",
                str(DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        configured = DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS
    if not math.isfinite(configured):
        configured = DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS
    return max(5.0, configured)


__all__ = [
    "DEFAULT_SECTION_REPAIR_TIMEOUT_SECONDS",
    "section_repair_timeout_seconds",
]
