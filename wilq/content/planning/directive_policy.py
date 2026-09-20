"""Claim-free policy for generated planning directives."""

from __future__ import annotations

import re
from collections.abc import Iterable

_AUTHORITATIVE_VALUE = re.compile(r"\d")


def regulatory_directive_value_errors(
    *,
    sections: Iterable[object],
    faq_items: Iterable[object],
    regulatory_evidence: set[str],
) -> list[str]:
    """Keep amounts and deadlines in exact facts, never in planning directives."""

    errors = [
        f"regulatory_directive_value:{getattr(section, 'heading', '')}"
        for section in sections
        if getattr(section, "regulatory_requirement_ids", ())
        and _AUTHORITATIVE_VALUE.search(
            f"{getattr(section, 'purpose', '')}\n{getattr(section, 'reader_question', '')}"
        )
    ]
    errors.extend(
        f"faq_directive_value:{getattr(faq, 'question', '')}"
        for faq in faq_items
        if regulatory_evidence.intersection(getattr(faq, "evidence_ids", ()))
        and _AUTHORITATIVE_VALUE.search(str(getattr(faq, "purpose", "")))
    )
    return errors


__all__ = ["regulatory_directive_value_errors"]
