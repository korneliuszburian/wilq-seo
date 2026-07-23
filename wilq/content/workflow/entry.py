from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from wilq.briefing.content_diagnostics import build_content_diagnostics_cached
from wilq.content.workflow.catalog import build_content_inventory_catalog_cached
from wilq.content.workflow.queue import (
    ContentWorkItemQueueCandidate,
    build_content_work_item_queue_response,
)


class ContentWorkflowEntryMode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["refresh_existing", "new_page"]
    label: str
    description: str
    route: str


class ContentWorkflowEntryFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class ContentWorkflowEntryRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str
    title: str
    url: str
    reason: str
    facts: list[ContentWorkflowEntryFact] = Field(default_factory=list)


class ContentWorkflowEntrySearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str
    title: str
    url: str
    material_label: str


class ContentWorkflowEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_workflow_entry"] = "content_workflow_entry"
    refresh_existing: ContentWorkflowEntryMode
    new_page: ContentWorkflowEntryMode
    recommendations: list[ContentWorkflowEntryRecommendation] = Field(default_factory=list)
    search_query: str | None = None
    search_results: list[ContentWorkflowEntrySearchResult] = Field(default_factory=list)
    browse_inventory_label: str


def build_content_workflow_entry(*, search: str | None = None) -> ContentWorkflowEntryResponse:
    """Build the first marketer decision without presenting sitemap inventory as the product."""

    queue = build_content_work_item_queue_response(build_content_diagnostics_cached())
    query = (search or "").strip()
    return ContentWorkflowEntryResponse(
        refresh_existing=ContentWorkflowEntryMode(
            kind="refresh_existing",
            label="Odśwież istniejącą stronę",
            description="Sprawdź obecną treść i przygotuj jej nową wersję.",
            route="refresh_existing",
        ),
        new_page=ContentWorkflowEntryMode(
            kind="new_page",
            label="Utwórz nową stronę",
            description="Zacznij od briefu nowej strony, bez wymaganego starego adresu.",
            route="new_page",
        ),
        recommendations=[
            _recommendation(candidate)
            for candidate in queue.candidates
            if candidate.source_public_url and candidate.recommended_mode != "block"
        ][:3],
        search_query=query or None,
        search_results=_search_existing_pages(query),
        browse_inventory_label="Przeglądaj wszystkie strony",
    )


def _recommendation(candidate: ContentWorkItemQueueCandidate) -> ContentWorkflowEntryRecommendation:
    return ContentWorkflowEntryRecommendation(
        work_item_id=candidate.work_item_id,
        title=_recommendation_title(candidate),
        url=candidate.source_public_url or candidate.final_canonical_url or "",
        reason="Zobacz aktualną stronę i zdecyduj, czy potrzebuje nowej wersji.",
        facts=_facts(candidate),
    )


def _recommendation_title(candidate: ContentWorkItemQueueCandidate) -> str:
    """Give the marketer a readable topic without claiming an unavailable H1."""

    if candidate.search_metrics.primary_query:
        return candidate.search_metrics.primary_query.strip().capitalize()
    url = candidate.source_public_url or candidate.final_canonical_url or ""
    path = urlparse(url).path.strip("/")
    if path:
        return path.rsplit("/", maxsplit=1)[-1].replace("-", " ").capitalize()
    return "Istniejąca strona do sprawdzenia"


def _facts(candidate: ContentWorkItemQueueCandidate) -> list[ContentWorkflowEntryFact]:
    metrics = candidate.search_metrics
    facts: list[ContentWorkflowEntryFact] = []
    if metrics.impressions is not None:
        facts.append(
            ContentWorkflowEntryFact(
                label="Wyświetlenia GSC", value=str(metrics.impressions)
            )
        )
    if metrics.clicks is not None:
        facts.append(ContentWorkflowEntryFact(label="Kliknięcia GSC", value=str(metrics.clicks)))
    if metrics.primary_query:
        facts.append(
            ContentWorkflowEntryFact(
                label="Główne zapytanie", value=metrics.primary_query
            )
        )
    if not facts:
        facts.append(
            ContentWorkflowEntryFact(
                label="Dane strony",
                value="Dane zapytań nie zostały wczytane.",
            )
        )
    return facts[:3]


def _search_existing_pages(query: str) -> list[ContentWorkflowEntrySearchResult]:
    if not query:
        return []
    needle = query.casefold()
    catalog = build_content_inventory_catalog_cached()
    matches = [
        item
        for item in catalog.items
        if needle in " ".join(
            [item.title or "", item.path, item.url, item.content_summary or ""]
        ).casefold()
    ]
    return [
        ContentWorkflowEntrySearchResult(
            work_item_id=item.work_item_id,
            title=item.title or item.path,
            url=item.url,
            material_label=_material_label(item.material_status),
        )
        for item in matches[:10]
    ]


def _material_label(status: str) -> str:
    return {
        "content_and_structure": "Materiał strony dostępny",
        "content_summary": "Skrót materiału dostępny",
        "structure_only": "Dostępna jest struktura strony",
        "url_only": "Adres wymaga odczytu materiału",
    }.get(status, "Stan materiału wymaga sprawdzenia")
