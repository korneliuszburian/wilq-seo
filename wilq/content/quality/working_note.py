"""Shared working-note detection for reader-visible content."""

from __future__ import annotations

import re

WORKING_NOTE_MARKERS: frozenset[str] = frozenset(
    {
        r"weryfikacj[ieą]? przez człowieka",
        "przed wykorzystaniem",
        "wymagają weryfikacj",
        "do weryfikacji",
        r"notatk[ae] robocze?",
        "weryfikacja przez człowieka",
        "zweryfikować przez człowieka",
        "źródło wskazuje",
        "informacja wymaga weryfikacji",
        r"\[do uzupełnienia\]",
    }
)

_WORKING_NOTE_PATTERN = re.compile(
    rf"(?:{'|'.join(sorted(WORKING_NOTE_MARKERS))})",
    re.IGNORECASE,
)


def working_note_pattern() -> re.Pattern[str]:
    """Return the canonical case-insensitive working-note pattern."""

    return _WORKING_NOTE_PATTERN


def contains_working_note(text: str) -> bool:
    """Return whether reader-visible text contains a working-note marker."""

    return _WORKING_NOTE_PATTERN.search(text) is not None


__all__ = [
    "WORKING_NOTE_MARKERS",
    "contains_working_note",
    "working_note_pattern",
]
