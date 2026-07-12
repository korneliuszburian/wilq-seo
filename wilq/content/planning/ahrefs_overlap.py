from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from wilq.content.canonical.urls import (
    CONTENT_SOURCE_SITE_HOSTS,
    content_normalized_path,
    content_url_host,
)
from wilq.schemas import MetricFact

AhrefsCrossSourceMatchStrength = Literal["exact", "weak", "missing"]

_STOPWORDS = {
    "dla",
    "http",
    "https",
    "jak",
    "jest",
    "oraz",
    "pl",
    "the",
    "www",
}
_POLISH_ASCII_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ż": "z",
        "ź": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ż": "Z",
        "Ź": "Z",
    }
)


@dataclass(frozen=True)
class AhrefsCrossSourceMatch:
    """One source-specific result with only lineage-backed proof material."""

    strength: AhrefsCrossSourceMatchStrength
    matching_labels: tuple[str, ...] = ()
    source_connectors: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AhrefsCrossSourceOverlap:
    """Shared pure assessment for Ahrefs planning and tactical queue projections."""

    gsc: AhrefsCrossSourceMatch
    wordpress: AhrefsCrossSourceMatch

    @property
    def has_exact_match(self) -> bool:
        return self.gsc.strength == "exact" or self.wordpress.strength == "exact"


@dataclass(frozen=True)
class _SourceRecord:
    label: str
    topic_words: tuple[str, ...]
    public_url_key: str | None
    source_connector: str
    evidence_id: str


def assess_ahrefs_cross_source_overlap(
    *,
    keyword: str,
    referenced_public_url: str | None,
    gsc_facts: Iterable[MetricFact],
    wordpress_facts: Iterable[MetricFact],
) -> AhrefsCrossSourceOverlap:
    """Classify direct phrase/URL lineage separately from weak token similarity.

    The Ahrefs source URL, competitor domain and other vendor metadata are not
    topic evidence. GSC demand needs an exact query phrase; WordPress inventory
    needs an exact public URL or an exact phrase in typed inventory metadata.
    """
    topic_words = _words(keyword)
    referenced_url_key = _public_url_key(referenced_public_url)
    return AhrefsCrossSourceOverlap(
        gsc=_assess_source(
            topic_words,
            referenced_url_key,
            _gsc_records(gsc_facts),
            reference_is_exact=False,
        ),
        wordpress=_assess_source(
            topic_words,
            referenced_url_key,
            _wordpress_records(wordpress_facts),
            reference_is_exact=True,
        ),
    )


def _assess_source(
    topic_words: tuple[str, ...],
    referenced_url_key: str | None,
    records: tuple[_SourceRecord, ...],
    *,
    reference_is_exact: bool,
) -> AhrefsCrossSourceMatch:
    exact_records = [
        record
        for record in records
        if _phrase_matches(topic_words, record.topic_words)
        or (
            reference_is_exact
            and referenced_url_key is not None
            and referenced_url_key == record.public_url_key
        )
    ]
    if exact_records:
        return _match("exact", exact_records)

    weak_records = [
        record
        for record in records
        if bool(set(topic_words) & set(record.topic_words))
        or (
            referenced_url_key is not None
            and referenced_url_key == record.public_url_key
        )
    ]
    return _match("weak", weak_records) if weak_records else AhrefsCrossSourceMatch("missing")


def _gsc_records(facts: Iterable[MetricFact]) -> tuple[_SourceRecord, ...]:
    records: list[_SourceRecord] = []
    for fact in facts:
        if fact.source_connector != "google_search_console":
            continue
        query = fact.dimensions.get("query", "")
        page = fact.dimensions.get("page", "")
        label = query or page
        if not label:
            continue
        records.append(
            _SourceRecord(
                label=label,
                topic_words=_words(query),
                public_url_key=_public_url_key(page),
                source_connector=fact.source_connector,
                evidence_id=fact.evidence_id,
            )
        )
    return tuple(records)


def _wordpress_records(facts: Iterable[MetricFact]) -> tuple[_SourceRecord, ...]:
    records: list[_SourceRecord] = []
    for fact in facts:
        if not fact.source_connector.startswith("wordpress"):
            continue
        content_url = fact.dimensions.get("content_url", "")
        public_url_key = _public_url_key(content_url)
        # A dev draft is an authoring workspace, not public inventory or SEO
        # lineage. Without a public final URL, even an exact title cannot
        # confirm an existing public page or unlock a content action.
        if public_url_key is None:
            continue
        source_text = " ".join(
            value
            for value in (
                fact.dimensions.get("title", ""),
                fact.dimensions.get("title_or_h1", ""),
                fact.dimensions.get("slug", ""),
                fact.dimensions.get("path", ""),
            )
            if value
        )
        label = content_url or source_text
        if not label:
            continue
        records.append(
            _SourceRecord(
                label=label,
                topic_words=_words(source_text),
                public_url_key=public_url_key,
                source_connector=fact.source_connector,
                evidence_id=fact.evidence_id,
            )
        )
    return tuple(records)


def _match(
    strength: AhrefsCrossSourceMatchStrength,
    records: Iterable[_SourceRecord],
) -> AhrefsCrossSourceMatch:
    selected = tuple(records)
    return AhrefsCrossSourceMatch(
        strength=strength,
        matching_labels=tuple(_unique(record.label for record in selected)[:4]),
        source_connectors=tuple(_unique(record.source_connector for record in selected)),
        evidence_ids=tuple(
            _unique(record.evidence_id for record in selected if record.evidence_id)
        ),
    )


def _phrase_matches(topic_words: tuple[str, ...], source_words: tuple[str, ...]) -> bool:
    if not topic_words or not source_words:
        return False
    if len(topic_words) == 1:
        return source_words == topic_words
    width = len(topic_words)
    return any(
        source_words[index : index + width] == topic_words
        for index in range(len(source_words))
    )


def _words(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", value.translate(_POLISH_ASCII_TRANSLATION))
    return tuple(
        token
        for token in re.findall(r"[a-z0-9]+", normalized.lower())
        if len(token) > 2 and token not in _STOPWORDS
    )


def _public_url_key(value: str | None) -> str | None:
    host = content_url_host(value)
    if host not in CONTENT_SOURCE_SITE_HOSTS:
        return None
    canonical_host = "ekologus.pl" if host in {"ekologus.pl", "www.ekologus.pl"} else host
    path = content_normalized_path(value)
    return f"{canonical_host}{path}" if path else None


def _unique(values: Iterable[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)
    return unique_values
