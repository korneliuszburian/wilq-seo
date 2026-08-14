from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

from wilq.content.quality.benefit_signal import (
    BENEFIT_BODY_MARKER,
    BENEFIT_HEADING_SIGNAL,
)
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
_QUESTION_HEADING_WORD = re.compile(
    r"^\s*(?:jak|czy|co|kiedy|który|która|które|ile|gdzie|czemu|dlaczego)(?!\w)",
    re.IGNORECASE,
)
_VAGUE_ANSWER_HEDGE = re.compile(
    r"(?<!\w)(?:może\s+obejmować|w\s+ramach|można\s+przejść|związane\s+z|"
    r"mogą\s+pozwolić|w\s+zależności|na\s+podstawie\s+można|zakres\s+może)(?!\w)",
    re.IGNORECASE,
)
_VAGUE_ANSWER_PHRASE = re.compile(
    r"(?<!\w)(?:ustalić\s+zakres|zebrać\s+informacje|zebranie\s+informacji|"
    r"omówienia\s+zakresu|omówić\s+zakres|zależnie\s+od\s+potrzeb|"
    r"zależnie\s+od\s+sytuacji|osobnego\s+omówienia|początek\s+rozmowy|"
    r"wstępnie\s+ustalić)(?!\w)",
    re.IGNORECASE,
)
_VAGUE_ANSWER_ADAPTATION_HEDGE = re.compile(
    r"(?<!\w)(?:można|da\s+się)\s+dopasować\s+do\s+potrzeb(?!\w)",
    re.IGNORECASE,
)
_VAGUE_ANSWER_CONCRETE_SIGNAL = re.compile(
    r"(?<!\w)(?:wniosek|karta|raport|kobize|bdo|termin|dni|norma|wymaga|numer|"
    r"rejestr)(?!\w)|(?<!\w)(?:sprawozdan|op(?:l|ł)at|pozwoleni|decyzj|"
    r"zgłoszen|próbk|pomiar|analiz)\w*(?!\w)|\d",
    re.IGNORECASE,
)
_CONCRETE_ANSWER_SIGNAL = re.compile(
    r"(?<!\w)(?:pobiera\s+się\s+przez|najpierw|następnie|krok|polega\s+na|wymaga|"
    r"składa\s+się\s+z|próbka|analiza\s+laboratoryjna|przepis|norma|decyzja|"
    r"pozwolenie|sprawozdanie|ewidencja|kpo|rejestr)(?!\w)",
    re.IGNORECASE,
)
_CONCRETE_NUMBER_OR_MEASURE = re.compile(
    r"(?<!\w)\d+(?:[.,]\d+)?(?:\s*(?:%|mm|cm|m|km|ml|l|g|kg|mg|ha|°c))?(?!\w)",
    re.IGNORECASE,
)
_DUPLICATE_PARAGRAPH_RATIO = 0.8
_LONG_SENTENCE_WORD_LIMIT = 20
_POLISH_ABBREVIATIONS = frozenset(
    {
        "art.",
        "itd.",
        "itp.",
        "m.in.",
        "np.",
        "tj.",
        "tzn.",
        "ust.",
        "ww.",
    }
)
_SENTENCE_TOKEN_WRAPPERS = "\"'()*[]_{}«»‘’‚“”„"  # nosec B105


@dataclass(frozen=True)
class RevisionReadabilityIssue:
    code: Literal[
        "thin_section",
        "wall_of_text",
        "long_sentence",
        "heading_answer_mismatch",
        "vague_answer_phrase",
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
        long_sentence_word_count = _first_long_sentence_word_count(section.body_markdown)
        if long_sentence_word_count is not None:
            issues.append(
                RevisionReadabilityIssue(
                    code="long_sentence",
                    label="Sekcja zawiera zbyt długie zdanie",
                    reason=(
                        f"Zdanie liczy {long_sentence_word_count} słów "
                        f"(limit: {_LONG_SENTENCE_WORD_LIMIT})."
                    ),
                    next_step="Podziel długie zdanie na krótsze.",
                    affected_section=section.heading,
                )
            )
        if _heading_answer_mismatch(section.heading, section.body_markdown):
            issues.append(
                RevisionReadabilityIssue(
                    code="heading_answer_mismatch",
                    label="Nagłówek-pyranie nie doczekał się odpowiedzi",
                    reason="Nagłówek pyta o... ale treść omija odpowiedź ogólnikami.",
                    next_step=("Rozwiń treść o konkretną odpowiedź na pytanie z nagłówka."),
                    affected_section=section.heading,
                )
            )
        if _benefit_heading_without_buyer_benefit(
            section.heading, section.body_markdown
        ) or _contains_vague_answer_phrase(section.body_markdown):
            issues.append(_vague_answer_phrase_issue(section.heading))
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


def _heading_answer_mismatch(heading: str, markdown: str) -> bool:
    if _QUESTION_HEADING_WORD.search(heading) is None:
        return False
    if _VAGUE_ANSWER_HEDGE.search(markdown) is None:
        return False
    if (
        BENEFIT_HEADING_SIGNAL.search(heading) is not None
        and BENEFIT_BODY_MARKER.search(markdown) is not None
    ):
        return False
    return (
        _CONCRETE_ANSWER_SIGNAL.search(markdown) is None
        and _CONCRETE_NUMBER_OR_MEASURE.search(markdown) is None
    )


def _contains_vague_answer_phrase(markdown: str) -> bool:
    has_vague_marker = (
        _VAGUE_ANSWER_PHRASE.search(markdown) is not None
        or _VAGUE_ANSWER_ADAPTATION_HEDGE.search(markdown) is not None
    )
    if not has_vague_marker:
        return False
    return _VAGUE_ANSWER_CONCRETE_SIGNAL.search(markdown) is None


def _benefit_heading_without_buyer_benefit(heading: str, markdown: str) -> bool:
    if BENEFIT_HEADING_SIGNAL.search(heading) is None:
        return False
    return not _has_benefit_or_concrete_signal(markdown)


def _has_benefit_or_concrete_signal(markdown: str) -> bool:
    if BENEFIT_BODY_MARKER.search(markdown) is not None:
        return True
    return any(
        signal.group(0).casefold() != "wymaga"
        for signal in _VAGUE_ANSWER_CONCRETE_SIGNAL.finditer(markdown)
    )


def _vague_answer_phrase_issue(heading: str) -> RevisionReadabilityIssue:
    return RevisionReadabilityIssue(
        code="vague_answer_phrase",
        label="Sekcja zawiera ogólnik zamiast odpowiedzi",
        reason=(
            "Treść odsyła do ustalenia zakresu albo zebrania informacji zamiast podać konkret."
        ),
        next_step=("Podaj konkretne obowiązki, dokumenty, terminy albo czynności z source facts."),
        affected_section=heading,
    )


def _first_duplicate_paragraph(markdown: str) -> str | None:
    paragraphs = [paragraph for paragraph in markdown.split("\n\n") if paragraph.strip()]
    if len(paragraphs) < 2:
        return None
    normalized = [
        _MARKDOWN_EMPHASIS.sub("", _MARKDOWN_LINK.sub(r"\1", paragraph)) for paragraph in paragraphs
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


def _first_long_sentence_word_count(markdown: str) -> int | None:
    tokens = markdown.split()
    sentence_word_count = 0
    for index in range(len(tokens)):
        sentence_word_count += 1
        if not _token_ends_sentence(tokens, index):
            continue
        if sentence_word_count > _LONG_SENTENCE_WORD_LIMIT:
            return sentence_word_count
        sentence_word_count = 0
    if sentence_word_count > _LONG_SENTENCE_WORD_LIMIT:
        return sentence_word_count
    return None


def _token_ends_sentence(tokens: list[str], index: int) -> bool:
    token = tokens[index].strip(_SENTENCE_TOKEN_WRAPPERS)
    if token.endswith(("?", "!")):
        return True
    if not token.endswith(".") or token.casefold() in _POLISH_ABBREVIATIONS:
        return False
    return index == len(tokens) - 1 or _next_token_starts_with_uppercase(tokens, index)


def _next_token_starts_with_uppercase(tokens: list[str], index: int) -> bool:
    for token in tokens[index + 1 :]:
        first_letter = next((character for character in token if character.isalpha()), None)
        if first_letter is not None:
            return first_letter.isupper()
    return False


def _paragraph_example(paragraph: str) -> str:
    normalized = " ".join(paragraph.split())
    if len(normalized) <= 160:
        return normalized
    return f"{normalized[:157].rstrip()}..."
