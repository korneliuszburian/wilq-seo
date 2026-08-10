from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

from wilq.content.workflow.documents.revisions import ContentDraftRevisionSection

_WORD = re.compile(r"[\wąćęłńóśźż]+", re.IGNORECASE)
_MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MARKDOWN_EMPHASIS = re.compile(r"[*_]")
_VAGUE_CTA_OPENER = re.compile(
    r"^\s*(?:w razie|w przypadku|jakichkolwiek|wszelkich|ewentualnych)\b",
    re.IGNORECASE,
)
_WEAK_CTA_LITERALS = frozenset({"kliknij tutaj", "skontaktuj się", "czytaj dalej"})
_WORKING_NOTE = re.compile(
    r"(?:weryfikacj[ieą]? przez człowieka|przed wykorzystaniem|"
    r"wymagają weryfikacj|do weryfikacji|notatk[ae] robocze?|"
    r"weryfikacja przez człowieka|zweryfikować przez człowieka)",
    re.IGNORECASE,
)
_DUPLICATE_PARAGRAPH_RATIO = 0.8


@dataclass(frozen=True)
class RevisionReadabilityIssue:
    code: Literal[
        "thin_section",
        "wall_of_text",
        "working_note",
        "duplicate_paragraph",
    ]
    label: str
    reason: str
    next_step: str
    affected_section: str


def revision_readability_issues(
    sections: Iterable[ContentDraftRevisionSection],
) -> list[RevisionReadabilityIssue]:
    issues: list[RevisionReadabilityIssue] = []
    for section in sections:
        word_count = _markdown_word_count(section.body_markdown)
        if word_count < 12:
            issues.append(
                RevisionReadabilityIssue(
                    code="thin_section",
                    label="Sekcja jest zbyt krótka",
                    reason=(
                        f"Sekcja zawiera {word_count} słów; bramka czytelności wymaga "
                        "co najmniej 12."
                    ),
                    next_step="Rozwiń sekcję tak, aby odpowiadała na pytanie czytelnika.",
                    affected_section=section.heading,
                )
            )
        oversized_paragraph = _first_oversized_paragraph(section.body_markdown)
        if oversized_paragraph is not None:
            paragraph, paragraph_word_count = oversized_paragraph
            issues.append(
                RevisionReadabilityIssue(
                    code="wall_of_text",
                    label="Sekcja zawiera ścianę tekstu",
                    reason=(
                        f"Akapit zawiera {paragraph_word_count} słów (limit: 220). "
                        f"Przykład: „{_paragraph_example(paragraph)}”"
                    ),
                    next_step="Podziel długi akapit na krótsze części ułatwiające czytanie.",
                    affected_section=section.heading,
                )
            )
        working_note = _first_working_note(section.body_markdown)
        if working_note is not None:
            issues.append(
                RevisionReadabilityIssue(
                    code="working_note",
                    label="Treść zawiera notatkę roboczą",
                    reason=(
                        "W tekście został notatka robocza albo meta-komentarz "
                        "skierowany do redakcji, nie do czytelnika."
                    ),
                    next_step="Usuń notatkę roboczą i zostaw tekst przeznaczony dla czytelnika.",
                    affected_section=section.heading,
                )
            )
        duplicate_paragraph = _first_duplicate_paragraph(section.body_markdown)
        if duplicate_paragraph is not None:
            issues.append(
                RevisionReadabilityIssue(
                    code="duplicate_paragraph",
                    label="Sekcja powtarza akapit",
                    reason=(
                        "Dwa akapity w tej sekcji mówią prawie to samo; czytelnik "
                        "czyta powtórkę zamiast nowej informacji."
                    ),
                    next_step="Połącz albo usuń powtórzony akapit i zostaw jedną wersję.",
                    affected_section=section.heading,
                )
            )
    return issues


def weak_cta(cta: str) -> bool:
    normalized = cta.strip()
    return (
        not normalized
        or len(normalized) < 8
        or normalized.casefold() in _WEAK_CTA_LITERALS
        or _VAGUE_CTA_OPENER.match(normalized) is not None
    )


def _first_working_note(markdown: str) -> str | None:
    for paragraph in markdown.split("\n\n"):
        if _WORKING_NOTE.search(paragraph) is not None:
            return _paragraph_example(paragraph)
    return None


def _first_duplicate_paragraph(markdown: str) -> str | None:
    paragraphs = [paragraph for paragraph in markdown.split("\n\n") if paragraph.strip()]
    if len(paragraphs) < 2:
        return None
    normalized = [
        _MARKDOWN_EMPHASIS.sub("", _MARKDOWN_LINK.sub(r"\1", paragraph))
        for paragraph in paragraphs
    ]
    for index, candidate in enumerate(normalized):
        for other in normalized[index + 1 :]:
            if SequenceMatcher(None, candidate, other).ratio() >= _DUPLICATE_PARAGRAPH_RATIO:
                return _paragraph_example(paragraphs[index])
    return None


def _markdown_word_count(markdown: str) -> int:
    without_links = _MARKDOWN_LINK.sub(r"\1", markdown)
    without_markers = _MARKDOWN_EMPHASIS.sub("", without_links)
    return len(_WORD.findall(without_markers))


def _first_oversized_paragraph(markdown: str) -> tuple[str, int] | None:
    for paragraph in markdown.split("\n\n"):
        word_count = len(_WORD.findall(paragraph))
        if word_count > 220:
            return paragraph, word_count
    return None


def _paragraph_example(paragraph: str) -> str:
    normalized = " ".join(paragraph.split())
    if len(normalized) <= 160:
        return normalized
    return f"{normalized[:157].rstrip()}..."
