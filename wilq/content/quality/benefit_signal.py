"""Shared benefit-signal detection for WILQ drafts.

Both the readability gate (quality) and the pre-persist enrichment
(drafts) decide "is this a benefit heading that needs a concrete
buyer benefit in the body" from the same two phrase signals. They used
to own byte-identical copies, kept in sync by hand. This module owns
the single source; callers import the signals instead of copying them.
"""

from __future__ import annotations

import re

BENEFIT_HEADING_SIGNAL = re.compile(
    r"(?<!\w)(?:korzyśc|wartoś|efekt|rezultat|opłacal)\w*(?!\w)|"
    r"(?<!\w)co\s+(?:zysk|daj)\w*(?!\w)",
    re.IGNORECASE,
)
BENEFIT_BODY_MARKER = re.compile(
    r"(?<!\w)(?:koszt|zatrudnian|terminow|pewnoś|gwaranc|oszczędn|czas|"
    r"efektywn|ryzyk)\w*(?!\w)",
    re.IGNORECASE,
)

__all__ = ["BENEFIT_BODY_MARKER", "BENEFIT_HEADING_SIGNAL"]
