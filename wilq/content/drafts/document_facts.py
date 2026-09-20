"""Project approved source facts into safe, reader-facing document text."""

from __future__ import annotations

import re

from wilq.content.quality.reading_quality import WORKING_NOTE
from wilq.content.workflow.documents.revisions import validate_no_inline_link

_SOURCE_ATTRIBUTION_PREFIX = re.compile(
    r"^\s*(?:źródło\s+podaje,\s+że\s+|zgodnie\s+z\s+treścią\s+źródła\s+|"
    r"według\s+dostarczonej\s+instrukcji\s+\w+\s*,?\s+|"
    r"zgodnie\s+z\s+oficjalnym\s+źródłem\s+\w+\s*,?\s+|"
    r"oficjalne\s+źródło\s+\w+\s+(?:wskazuje|wyjaśnia),\s+że\s+|"
    r"źródło\s+wskazuje,\s+że\s+|źródło\s+\w+\s+rozróżnia\s+)",
    re.IGNORECASE,
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ])")
_TRAILING_VERIFICATION_CLAUSE = re.compile(
    r"\s*(?:,?\s*i\s+)?wymagają?\s+weryfikacj[^.]*\.?\s*$",
    re.IGNORECASE,
)


def document_ready_fact_text(
    fact_text: str,
    *,
    protected_terms: list[str] | None,
) -> str:
    """Project one approved review fact into reader-facing document text."""

    stripped = _SOURCE_ATTRIBUTION_PREFIX.sub("", fact_text).strip()
    sentences = [
        sentence.strip() for sentence in _SENTENCE_BOUNDARY.split(stripped) if sentence.strip()
    ]
    normalized_terms = [term.casefold().strip() for term in (protected_terms or []) if term.strip()]
    kept: list[str] = []
    for sentence in sentences:
        if WORKING_NOTE.search(sentence) is None:
            kept.append(sentence)
            continue
        if not any(term in sentence.casefold() for term in normalized_terms):
            continue
        # The sentence carries a protected concept, but a reader must never see
        # the editorial working note itself. Strip only the note span.
        cleaned = _without_working_note(sentence)
        if cleaned:
            kept.append(cleaned)
    result = " ".join(kept) if kept else stripped
    qualifier = _TRAILING_VERIFICATION_CLAUSE.search(result)
    if qualifier and not any(term in qualifier.group(0).casefold() for term in normalized_terms):
        result = result[: qualifier.start()].rstrip(" ,;")
    if not result:
        return result
    return result[0].upper() + result[1:]


def _without_working_note(sentence: str) -> str:
    """Remove every editorial working-note span while keeping the rest."""

    cleaned = sentence
    while (match := WORKING_NOTE.search(cleaned)) is not None:
        cleaned = cleaned[: match.start()] + cleaned[match.end() :]
    cleaned = re.sub(r"\s*[,;]\s*(?=[.,;]|$)", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;")
    return cleaned


def safe_document_ready_fact_text(
    summary: str,
    *,
    protected_terms: list[str] | None,
) -> str | None:
    """Return reader-ready text unless the fact violates document safety."""

    try:
        sanitized = document_ready_fact_text(summary, protected_terms=protected_terms).strip()
        return validate_no_inline_link(sanitized).strip() if sanitized else None
    except ValueError:
        return None


__all__ = ["document_ready_fact_text", "safe_document_ready_fact_text"]
