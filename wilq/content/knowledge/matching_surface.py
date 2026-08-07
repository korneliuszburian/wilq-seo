from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from wilq.content.knowledge.text_matching import normalize_search_text
from wilq.content.workflow.models import ContentWorkItem


class ServiceCardMatchingSource(Protocol):
    @property
    def card_type(self) -> str: ...

    @property
    def source_lineage(self) -> list[str]: ...


@dataclass(frozen=True)
class ContentKnowledgeMatchingSurface:
    exact_urls: set[str]
    page_text: str
    service_candidate_text: str
    priority_text: str


def build_content_knowledge_matching_surface(
    item: ContentWorkItem,
    cards: Iterable[ServiceCardMatchingSource],
) -> ContentKnowledgeMatchingSurface:
    card_list = list(cards)
    exact_urls = {
        normalize_search_text(url)
        for url in (item.source_public_url, item.final_canonical_url)
        if url
    }
    page_values: list[object] = [
        item.topic,
        item.wordpress_title_or_h1,
        item.source_public_url,
        item.final_canonical_url,
        item.intended_final_url,
        *_homepage_match_markers(item),
    ]
    metric_query_values = [
        str(fact.dimensions.get("query") or "") for fact in item.metric_facts
    ]
    exact_service_urls = {
        normalize_search_text(lineage)
        for card in card_list
        if card.card_type == "service"
        for lineage in card.source_lineage
        if lineage.startswith("http")
    }
    if exact_urls & exact_service_urls:
        page_values.append(item.wordpress_content_text)
    return ContentKnowledgeMatchingSurface(
        exact_urls=exact_urls,
        page_text=_search_text(page_values),
        service_candidate_text=_search_text([*page_values, *metric_query_values]),
        priority_text=_search_text(
            [
                item.topic,
                item.wordpress_title_or_h1,
                item.source_public_url,
                item.final_canonical_url,
                item.intended_final_url,
                *metric_query_values,
            ]
        ),
    )


def service_card_has_exact_url(
    card: ServiceCardMatchingSource,
    normalized_urls: set[str],
) -> bool:
    return any(
        normalize_search_text(lineage) in normalized_urls
        for lineage in card.source_lineage
        if lineage.startswith("http")
    )


def _search_text(values: Iterable[object]) -> str:
    return normalize_search_text(" ".join(str(value) for value in values if value))


def _homepage_match_markers(item: ContentWorkItem) -> list[str]:
    root_urls = {
        "https://ekologus.pl",
        "https://ekologus.pl/",
        "https://www.ekologus.pl",
        "https://www.ekologus.pl/",
    }
    item_urls = {
        str(url).strip().lower().rstrip("/")
        for url in (
            item.source_public_url,
            item.final_canonical_url,
            item.intended_final_url,
        )
        if url
    }
    if item_urls & {url.rstrip("/") for url in root_urls}:
        return ["homepage_overview"]
    return []
