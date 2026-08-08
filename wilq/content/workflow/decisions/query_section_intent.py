from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Literal

QuerySectionIntent = Literal[
    "definition",
    "applicability",
    "obligations",
    "process",
    "service",
]

_TOKEN_RE = re.compile(r"[0-9a-z]+")
_EXPLICIT_INTENT_MARKERS: dict[QuerySectionIntent, tuple[str, ...]] = {
    "definition": ("co to", "czym jest", "co znaczy", "definic"),
    "applicability": ("dla kogo", "kto musi", "kogo dotyc", "mikroprzedsiebior"),
    "obligations": ("obowiazk", "wymagan", "prawo", "przepis", "musi"),
    "process": ("jak ", "prowadz", "rejestr", "ewidenc", "sprawozd", "wpis"),
    "service": (),
}
_STOPWORDS = {
    "a",
    "albo",
    "co",
    "czy",
    "dla",
    "do",
    "i",
    "jak",
    "jest",
    "lub",
    "na",
    "oraz",
    "sa",
    "sie",
    "to",
    "w",
    "we",
    "z",
    "ze",
}


def assign_query_to_sections(
    query: str,
    sections: Iterable[tuple[str, str]],
) -> list[str]:
    query_intents = _intents(query)
    query_topics = _topic_tokens(query, query_intents)
    if not query_topics:
        return []
    required_intents = query_intents - {"service"} or {"service"}
    candidates: list[str] = []
    for heading, purpose in sections:
        section_text = f"{heading} {purpose}"
        section_intents = _intents(section_text)
        if not required_intents.intersection(section_intents):
            continue
        section_topics = _topic_tokens(section_text, section_intents)
        if all(
            any(_tokens_match(query_topic, section_topic) for section_topic in section_topics)
            for query_topic in query_topics
        ):
            candidates.append(heading)
    return candidates if len(candidates) == 1 else []


def _intents(value: str) -> set[QuerySectionIntent]:
    normalized = _normalized_text(value)
    intents = {
        intent
        for intent, markers in _EXPLICIT_INTENT_MARKERS.items()
        if markers and any(marker in normalized for marker in markers)
    }
    return {"service", *intents}


def _topic_tokens(value: str, intents: set[QuerySectionIntent]) -> set[str]:
    intent_tokens = {
        token
        for intent in intents
        for marker in _EXPLICIT_INTENT_MARKERS[intent]
        for token in _TOKEN_RE.findall(marker)
    }
    return {
        token
        for token in _TOKEN_RE.findall(_normalized_text(value))
        if len(token) >= 2
        and token not in _STOPWORDS
        and not any(_tokens_match(token, marker) for marker in intent_tokens)
    }


def _tokens_match(left: str, right: str) -> bool:
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    if len(shorter) >= 5 and longer.startswith(shorter):
        return True
    prefix_length = 0
    for left_character, right_character in zip(left, right, strict=False):
        if left_character != right_character:
            break
        prefix_length += 1
    return prefix_length >= 6


def _normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        "".join(character for character in token if not unicodedata.combining(character))
        for token in decomposed.split()
    )
