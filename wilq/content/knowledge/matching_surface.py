from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from wilq.content.knowledge.text_matching import normalize_search_text
from wilq.content.workflow.contracts.models import ContentWorkItem


class ServiceCardMatchingSource(Protocol):
    @property
    def card_type(self) -> str: ...

    @property
    def service_binding_urls(self) -> list[str]: ...

    @property
    def evidence_ids(self) -> list[str]: ...

    @property
    def source_connectors(self) -> list[str]: ...

    @property
    def freshness(self) -> str: ...


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
    exact_urls = _normalized_binding_urls((item.source_public_url, item.final_canonical_url))
    page_values: list[object] = [
        item.topic,
        item.wordpress_title_or_h1,
        item.source_public_url,
        item.final_canonical_url,
        item.intended_final_url,
        *_homepage_match_markers(item),
    ]
    metric_query_values = [str(fact.dimensions.get("query") or "") for fact in item.metric_facts]
    exact_service_urls = _normalized_binding_urls(
        binding_url
        for card in card_list
        if card.card_type == "service"
        for binding_url in card.service_binding_urls
    )
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
    return service_card_exact_binding_url(card, normalized_urls) is not None


def service_card_has_binding_provenance(card: ServiceCardMatchingSource) -> bool:
    """Only evidence-backed cards may become a service recommendation."""
    return bool(
        card.evidence_ids
        and all(value.strip() for value in card.evidence_ids)
        and card.source_connectors
        and all(value.strip() for value in card.source_connectors)
        and card.freshness.strip()
    )


def exactly_bound_service_cards[ServiceCardSourceT: ServiceCardMatchingSource](
    cards: Iterable[ServiceCardSourceT],
    normalized_urls: set[str],
) -> list[ServiceCardSourceT]:
    return [
        card
        for card in cards
        if (
            card.card_type == "service"
            and service_card_has_exact_url(card, normalized_urls)
            and service_card_has_binding_provenance(card)
        )
    ]


def service_card_exact_binding_url(
    card: ServiceCardMatchingSource,
    normalized_urls: set[str],
) -> str | None:
    return next(
        (
            binding_url
            for binding_url in card.service_binding_urls
            if _binding_url_key(binding_url) in normalized_urls
        ),
        None,
    )


def _normalized_binding_urls(values: Iterable[str | None]) -> set[str]:
    return {normalized for value in values if (normalized := _binding_url_key(value))}


def _binding_url_key(value: str | None) -> str:
    if not value:
        return ""
    if value != value.strip():
        return ""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""
    if (
        not parsed.scheme
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        return ""
    try:
        normalized_host = parsed.hostname.casefold() if parsed.hostname else ""
        normalized_port = parsed.port
    except ValueError:
        return ""
    if not normalized_host:
        return ""
    normalized_host = {
        "ekologus.pl": "www.ekologus.pl",
        "www.ekologus.pl": "www.ekologus.pl",
    }.get(normalized_host, normalized_host)
    normalized_netloc = normalized_host
    if normalized_port is not None:
        normalized_netloc = f"{normalized_netloc}:{normalized_port}"
    normalized_path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            normalized_netloc,
            normalized_path,
            parsed.query,
            parsed.fragment,
        )
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
