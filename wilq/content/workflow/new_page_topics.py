from __future__ import annotations

import json
import re
import unicodedata
from hashlib import sha256
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.schemas.ahrefs import AhrefsDiagnosticsResponse

if TYPE_CHECKING:
    from wilq.schemas.content import ContentAhrefsCandidateRow


class ContentNewPageTopicCandidate(BaseModel):
    """A read-only topic seed that is safe to carry into a new-page brief.

    This is deliberately narrower than a brief: it proves only the observed
    topic and its evidence, not the marketer's audience, purpose or IA choice.
    """

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    title: str = Field(min_length=3, max_length=160)
    topic: str = Field(min_length=3, max_length=160)
    rationale: str = Field(min_length=1)
    source_connectors: list[str] = Field(min_length=2)
    evidence_ids: list[str] = Field(min_length=2)


class ContentNewPageTopicRecommendations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_new_page_topic_recommendations"] = (
        "content_new_page_topic_recommendations"
    )
    contract_version: Literal["content_new_page_topic_recommendations_v1"] = (
        "content_new_page_topic_recommendations_v1"
    )
    status: Literal["ready", "no_qualified_topics", "blocked"]
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)
    candidates: list[ContentNewPageTopicCandidate] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


def build_new_page_topic_recommendations(
    diagnostics: AhrefsDiagnosticsResponse | None = None,
) -> ContentNewPageTopicRecommendations:
    """Return only topics that can start a brief without pretending certainty.

    A candidate needs an exact GSC demand match, no exact WordPress inventory
    match, explicit Ahrefs relevance and evidence from both reads.  The normal
    new-page overlap guard still runs when a brief is saved.
    """

    if diagnostics is None:
        # Diagnostics reaches the broader actions graph, so it belongs behind
        # the read operation rather than becoming an import-time dependency of
        # every revision/workflow model.
        from wilq.briefing.ahrefs_diagnostics import build_ahrefs_diagnostics

        diagnostics = build_ahrefs_diagnostics()
    response = diagnostics
    contract = response.gap_read_contract
    connectors = _unique(contract.source_connectors)
    evidence_ids = _unique(contract.evidence_ids)
    if contract.status != "ready":
        return ContentNewPageTopicRecommendations(
            status="blocked",
            title="Tematy z danych są jeszcze niedostępne",
            reason=(
                "WILQ nie ma kompletnego odczytu Ahrefs potrzebnego do bezpiecznej "
                "rekomendacji nowej strony."
            ),
            safe_next_step=(
                "Odśwież odczyt Ahrefs, GSC i katalog aktualnych stron przed wyborem "
                "tematu."
            ),
            source_connectors=connectors,
            evidence_ids=evidence_ids,
        )

    candidates = _qualified_candidates(response)
    if not candidates:
        return ContentNewPageTopicRecommendations(
            status="no_qualified_topics",
            title="Brak bezpiecznej rekomendacji tematu",
            reason=(
                "Aktualne sygnały Ahrefs nie mają jednocześnie potwierdzonego popytu w GSC, "
                "dopasowania do zakresu Ekologus i braku istniejącej strony."
            ),
            safe_next_step=(
                "Opisz własny temat albo odśwież dane; przed zapisem WILQ i tak sprawdzi "
                "pokrycie całego serwisu."
            ),
            source_connectors=connectors,
            evidence_ids=evidence_ids,
        )
    return ContentNewPageTopicRecommendations(
        status="ready",
        title="Tematy potwierdzone przez dane",
        reason=(
            "Każdy temat ma zgodny sygnał Ahrefs i GSC oraz nie ma potwierdzonego "
            "odpowiednika w obserwowanym katalogu WordPress."
        ),
        safe_next_step=(
            "Wybierz temat, uzupełnij cel, odbiorcę i miejsce w serwisie, a WILQ ponownie "
            "sprawdzi pokrycie przed zapisaniem briefu."
        ),
        candidates=candidates,
        source_connectors=_unique(
            connector for candidate in candidates for connector in candidate.source_connectors
        ),
        evidence_ids=_unique(
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        ),
    )


def resolve_new_page_topic_candidate(
    *,
    candidate_id: str,
    candidate_digest: str,
    recommendations: ContentNewPageTopicRecommendations | None = None,
) -> ContentNewPageTopicCandidate | None:
    current = recommendations or build_new_page_topic_recommendations()
    return next(
        (
            candidate
            for candidate in current.candidates
            if candidate.candidate_id == candidate_id
            and candidate.candidate_digest == candidate_digest
        ),
        None,
    )


def _qualified_candidates(
    response: AhrefsDiagnosticsResponse,
) -> list[ContentNewPageTopicCandidate]:
    selected: dict[str, ContentNewPageTopicCandidate] = {}
    rows = sorted(
        response.gap_read_contract.cross_check_candidates,
        key=lambda row: (
            _normalized_topic((row.keyword or row.topic).strip()),
            -row.relevance_score,
            row.mapping_key,
        ),
    )
    for row in rows:
        topic = (row.keyword or row.topic).strip()
        if not _is_qualified_row(row, topic):
            continue
        key = _normalized_topic(topic)
        candidate = _candidate_from_row(row, topic)
        selected.setdefault(key, candidate)
    return sorted(selected.values(), key=lambda candidate: candidate.title.casefold())[:3]


def _is_qualified_row(row: ContentAhrefsCandidateRow, topic: str) -> bool:
    # Keep the predicate local to this policy owner; no dashboard-side ranking.
    return bool(
        topic
        and len(topic) >= 3
        and row.gap_type in {"content_gap", "organic_keyword_gap"}
        and row.relevance_status == "relevant"
        and row.gsc_cross_check.strength == "exact"
        and row.wordpress_cross_check.strength == "missing"
        and {"ahrefs", "google_search_console"}.issubset(set(row.source_connectors))
        and len(row.evidence_ids) >= 2
    )


def _candidate_from_row(
    row: ContentAhrefsCandidateRow, topic: str
) -> ContentNewPageTopicCandidate:
    mapping_hash = sha256(row.mapping_key.encode()).hexdigest()[:12]
    candidate_id = f"content_new_page_topic_{_slug(topic)}_{mapping_hash}"
    payload = {
        "candidate_id": candidate_id,
        "topic": topic,
        "mapping_key": row.mapping_key,
        "evidence_ids": sorted(set(row.evidence_ids)),
        "source_connectors": sorted(set(row.source_connectors)),
    }
    digest = sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ContentNewPageTopicCandidate(
        candidate_id=candidate_id,
        candidate_digest=digest,
        title=topic,
        topic=topic,
        rationale=(
            "Ahrefs wskazuje temat, GSC potwierdza dokładne zapytanie, a katalog WordPress "
            "nie wskazuje istniejącej strony o tym samym temacie."
        ),
        source_connectors=payload["source_connectors"],
        evidence_ids=payload["evidence_ids"],
    )


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-") or "topic"


def _normalized_topic(value: str) -> str:
    return _slug(value)


def _unique(values: object) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))
