"""Ahrefs keyword relevance and normalization helpers."""
from __future__ import annotations

import re
import unicodedata

from wilq.schemas import (
    AhrefsGapRecord,
)

AHREFS_EKOLOGUS_RELEVANCE_TERMS = (
    "bdo",
    "odpady",
    "odpad",
    "srodowisko",
    "srodowiskowy",
    "remediacja",
    "operat",
    "wodnoprawny",
    "pozwolenie",
    "zintegrowane",
    "zielony lad",
    "ppwr",
    "recykling",
    "emisja",
    "esg",
    "beczka",
    "sorbent",
    "wanna wychwytowa",
    "magazynowanie",
    "substancje",
    "chemiczne",
    "denios",
)

AHREFS_RELEVANT_COMPETITOR_DOMAINS = {
    "denios.pl",
    "dla-przemyslu.pl",
    "manutan.pl",
}

AHREFS_OFF_TOPIC_TERMS = (
    "prawo jazdy",
    "kalkulator oc",
    "ubezpieczenie samochodu",
    "samochod",
    "samochodu",
    "ubezpieczenie",
    "oc",
    "ac",
)

AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS = {
    "cuk.pl",
    "ltesty.pl",
}

AHREFS_BROAD_BACKLINK_DOMAINS = {
    "apple.com",
    "google.com",
    "waze.com",
    "wikipedia.org",
    "youtube.com",
    "businessinsider.com.pl",
    "storeleads.app",
    "trustedshops.pl",
    "wykop.pl",
}

AHREFS_RELEVANCE_STOPWORDS = {
    "https",
    "http",
    "www",
    "com",
    "pl",
    "dla",
    "oraz",
    "jest",
    "jak",
    "czy",
    "the",
}

POLISH_ASCII_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "a",
        "Ć": "c",
        "Ę": "e",
        "Ł": "l",
        "Ń": "n",
        "Ó": "o",
        "Ś": "s",
        "Ź": "z",
        "Ż": "z",
    }
)

def _gap_record_relevance_score(record: AhrefsGapRecord) -> int:
    text = " ".join(
        value
        for value in (
            record.keyword,
            record.source_url,
            record.referenced_public_url,
            record.competitor_domain,
        )
        if value
    )
    normalized_text = _normalize_text(text)
    tokens = _tokens_from_text(text)
    competitor_domain = _normalized_domain(record.competitor_domain)
    source_domain = _normalized_domain(record.source_url)
    if record.gap_type == "backlink_gap" and source_domain in AHREFS_BROAD_BACKLINK_DOMAINS:
        return -100
    score = 1

    if any(
        _matches_normalized_term(normalized_text, tokens, term)
        for term in AHREFS_EKOLOGUS_RELEVANCE_TERMS
    ):
        score += 4
    if competitor_domain in AHREFS_RELEVANT_COMPETITOR_DOMAINS:
        score += 3
    if record.gap_type in {"content_gap", "organic_keyword_gap", "top_page_gap"}:
        score += 1
    elif record.gap_type == "backlink_gap":
        score -= 1

    if any(
        _matches_normalized_term(normalized_text, tokens, term) for term in AHREFS_OFF_TOPIC_TERMS
    ):
        score -= 6
    if competitor_domain in AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS:
        score -= 4
    if source_domain in AHREFS_BROAD_BACKLINK_DOMAINS:
        score -= 5
    return score

def _tokens_from_text(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", _normalize_text(text))
        if len(token) > 2 and token not in AHREFS_RELEVANCE_STOPWORDS
    }

def _matches_normalized_term(normalized_text: str, tokens: set[str], term: str) -> bool:
    normalized_term = _normalize_text(term)
    if " " in normalized_term:
        return normalized_term in normalized_text
    return normalized_term in tokens

def _normalize_text(text: str) -> str:
    translated = text.translate(POLISH_ASCII_TRANSLATION)
    ascii_text = unicodedata.normalize("NFKD", translated).encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()

def _normalized_domain(value: str | None) -> str | None:
    if not value:
        return None
    normalized = _normalize_text(value).replace("https://", "").replace("http://", "")
    return normalized.split("/")[0].removeprefix("www.") or None

def _slug(value: str) -> str:
    normalized = []
    previous_separator = False
    for character in value.lower():
        if character.isalnum():
            normalized.append(character)
            previous_separator = False
        elif not previous_separator:
            normalized.append("_")
            previous_separator = True
    return "".join(normalized).strip("_")[:96] or "record"

