from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog_cached,
)
from wilq.schemas.core import utc_now


class ContentNewPageBriefInput(BaseModel):
    """The smallest marketer-owned statement of a page that does not exist yet."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=160)
    purpose: str = Field(min_length=8, max_length=800)
    service: str = Field(min_length=2, max_length=160)
    audience: str = Field(min_length=3, max_length=300)
    search_intent: str = Field(min_length=3, max_length=300)
    proposed_ia_location: str = Field(min_length=3, max_length=300)


class ContentNewPageBrief(ContentNewPageBriefInput):
    model_config = ConfigDict(extra="forbid")

    brief_id: str = Field(min_length=1)
    brief_digest: str = Field(min_length=64, max_length=64)
    created_at: datetime
    work_kind: Literal["new_page"] = "new_page"


class ContentNewPageOverlapCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    match_kind: Literal["same_title", "shared_intent", "shared_service"]
    evidence_ids: list[str] = Field(default_factory=list)


class ContentNewPageOverlapGuard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: Literal[
        "no_conflict", "differentiate", "reuse", "merge", "human_decision_required"
    ]
    label: str
    reason: str
    caveat: str
    evidence_ids: list[str] = Field(default_factory=list)
    candidates: list[ContentNewPageOverlapCandidate] = Field(default_factory=list)


class ContentNewPageBriefWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_new_page_brief_workspace"] = "content_new_page_brief_workspace"
    contract_version: Literal["content_new_page_brief_workspace_v1"] = (
        "content_new_page_brief_workspace_v1"
    )
    brief: ContentNewPageBrief
    overlap_guard: ContentNewPageOverlapGuard
    review_status: Literal["blocked"] = "blocked"
    review_reason: str
    next_action_label: str


def build_new_page_brief(input: ContentNewPageBriefInput) -> ContentNewPageBrief:
    payload = input.model_dump(mode="json")
    digest = sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return ContentNewPageBrief(
        **payload,
        brief_id=f"content_new_page_brief_{uuid4().hex}",
        brief_digest=digest,
        created_at=utc_now(),
    )


def build_new_page_brief_workspace(
    brief: ContentNewPageBrief,
    *,
    catalog: ContentInventoryCatalogResponse | None = None,
) -> ContentNewPageBriefWorkspace:
    guard = build_new_page_overlap_guard(
        brief,
        catalog=catalog or build_content_inventory_catalog_cached(),
    )
    return ContentNewPageBriefWorkspace(
        brief=brief,
        overlap_guard=guard,
        review_reason=(
            "Brief opisuje nową stronę, ale nie jest jeszcze dokumentem do review. "
            "Kolejny etap przygotuje dokument bez zmiany istniejących stron."
        ),
        next_action_label="Przygotowanie dokumentu zostanie udostępnione w następnym etapie",
    )


def build_new_page_overlap_guard(
    brief: ContentNewPageBrief,
    *,
    catalog: ContentInventoryCatalogResponse,
) -> ContentNewPageOverlapGuard:
    """Return only observed inventory signals; never infer a match from a URL slug."""

    catalog_evidence_ids = _catalog_evidence_ids(catalog)
    if not catalog.items or not catalog_evidence_ids:
        return ContentNewPageOverlapGuard(
            disposition="human_decision_required",
            label="Nie można jeszcze ocenić pokrycia serwisu",
            reason=(
                "Aktualny katalog stron nie zawiera materiału z potwierdzonym źródłem, "
                "z którym można porównać brief."
            ),
            caveat="Brak katalogu lub dowodów nie jest zgodą na tworzenie duplikatu.",
            evidence_ids=catalog_evidence_ids,
        )

    exact_title = _normalized(brief.title)
    title_matches = [
        _candidate(item, "same_title")
        for item in catalog.items
        if item.title and _normalized(item.title) == exact_title
    ]
    if title_matches:
        return ContentNewPageOverlapGuard(
            disposition="reuse",
            label="Istnieje strona o tym samym tytule",
            reason=(
                "W aktualnym katalogu jest strona o dokładnie takim samym tytule. "
                "Zanim powstanie nowa, sprawdź wykorzystanie istniejącej."
            ),
            caveat=(
                "To porównanie dotyczy obserwowanego tytułu, nie układu WordPressa "
                "ani gotowości do dostawy."
            ),
            evidence_ids=_evidence_ids(title_matches),
            candidates=title_matches,
        )

    signals = [
        ("shared_intent", _normalized(brief.search_intent)),
        ("shared_service", _normalized(brief.service)),
    ]
    candidates = _shared_phrase_candidates(catalog.items, signals)
    if candidates:
        return ContentNewPageOverlapGuard(
            disposition="human_decision_required",
            label="Pokrycie wymaga decyzji człowieka",
            reason=(
                "W aktualnym katalogu znaleźliśmy strony z bezpośrednio wspólną intencją "
                "lub usługą. Wybierz później, czy nowa strona ma się wyraźnie odróżniać, "
                "zostać połączona czy wykorzystać istniejący materiał."
            ),
            caveat=(
                "Wspólne słowa są sygnałem do sprawdzenia, a nie automatycznym dowodem "
                "duplikacji."
            ),
            evidence_ids=_evidence_ids(candidates),
            candidates=candidates,
        )

    return ContentNewPageOverlapGuard(
        disposition="no_conflict",
        label="Nie znaleziono bezpośredniego pokrycia",
        reason=(
            "Aktualny katalog nie pokazuje strony z tym samym tytułem ani bezpośrednio "
            "wspólną intencją lub usługą."
        ),
        caveat=(
            "To wynik porównania z aktualnym katalogiem, nie dowód braku wszystkich "
            "możliwych duplikatów."
        ),
        evidence_ids=catalog_evidence_ids,
    )


def _shared_phrase_candidates(
    items: list[ContentInventoryCatalogItem],
    signals: list[tuple[Literal["shared_intent", "shared_service"], str]],
) -> list[ContentNewPageOverlapCandidate]:
    candidates: list[ContentNewPageOverlapCandidate] = []
    for item in items:
        if not item.title:
            continue
        observed_title = _normalized(item.title)
        for kind, phrase in signals:
            # Short terms create broad, weak matches. They must not drive a disposition.
            if len(phrase) >= 5 and phrase in observed_title:
                candidates.append(_candidate(item, kind))
                break
    return candidates


def _candidate(
    item: ContentInventoryCatalogItem,
    match_kind: Literal["same_title", "shared_intent", "shared_service"],
) -> ContentNewPageOverlapCandidate:
    return ContentNewPageOverlapCandidate(
        title=item.title or item.path,
        url=item.url,
        match_kind=match_kind,
        evidence_ids=[item.evidence_id],
    )


def _evidence_ids(candidates: list[ContentNewPageOverlapCandidate]) -> list[str]:
    return sorted(
        {
            evidence_id
            for candidate in candidates
            for evidence_id in candidate.evidence_ids
        }
    )


def _catalog_evidence_ids(catalog: ContentInventoryCatalogResponse) -> list[str]:
    """Keep the guard tied to every inventory record actually inspected."""

    return sorted(
        {
            *catalog.evidence_ids,
            *(item.evidence_id for item in catalog.items),
        }
    )


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", value.casefold()).strip()
