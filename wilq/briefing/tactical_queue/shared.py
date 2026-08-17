"""Decomposed tactical_queue shared implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from wilq.schemas import MetricFact, TacticalQueueResponse

TACTICAL_QUEUE_LIMIT = 24


TACTICAL_QUEUE_DOMAIN_FLOOR = 4


TACTICAL_QUEUE_SOURCE_CONNECTORS = (
    "ahrefs",
    "google_search_console",
    "google_analytics_4",
    "google_merchant_center",
    "wordpress_ekologus",
    "wordpress_sklep",
)


TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT = 300


GSC_QUERY_PAGE_FACT_LIMIT = 1200


GA4_LANDING_FACT_LIMIT = 2000


WORDPRESS_INVENTORY_FACT_LIMIT = 5000


TacticalIntent = Literal[
    "content_refresh",
    "content_create",
    "content_merge",
    "content_block",
    "landing_page_quality",
    "tracking_gap",
    "merchant_feed_triage",
    "traffic_quality_review",
]


WordPressMatchConfidence = Literal[
    "exact_url",
    "host_alias_sitemap",
    "path_fallback",
    "missing",
]


WORDPRESS_CANONICAL_HOST_ALIASES = {
    "www.ekologus.pl": {"ekologus.pl"},
    "ekologus.pl": {"www.ekologus.pl"},
}


WORDPRESS_PUBLIC_CONTENT_HOSTS = {
    "ekologus.pl",
    "www.ekologus.pl",
    "sklep.ekologus.pl",
}


AHREFS_GAP_FACT_NAMES = {
    "ahrefs_competitor_page_count",
    "ahrefs_content_gap_count",
    "ahrefs_backlink_gap_count",
    "ahrefs_referring_domain_gap_count",
    "ahrefs_organic_keyword_gap_count",
    "ahrefs_top_page_gap_count",
}


AHREFS_GAP_TYPE_LABELS = {
    "competitor_page": "strona konkurencji",
    "content_gap": "luka treści",
    "backlink_gap": "luka linków",
    "organic_keyword_gap": "luka słów organicznych",
    "top_page_gap": "luka najlepszych stron konkurencji",
}


AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS = {
    "cuk.pl",
    "ltesty.pl",
}


AHREFS_OFF_TOPIC_TERMS = (
    "prawo jazdy",
    "kalkulator oc",
    "ubezpieczenie samochodu",
    "samochod",
    "samochodu",
    "ubezpieczenie",
)


AHREFS_RELEVANT_COMPETITOR_DOMAINS = {
    "denios.pl",
    "dla-przemyslu.pl",
    "manutan.pl",
}


AHREFS_RELEVANT_TERMS = (
    "bdo",
    "odpady",
    "odpad",
    "srodowisko",
    "srodowiskowy",
    "remediacja",
    "operat",
    "wodnoprawny",
    "zielony lad",
    "ppwr",
    "audyt",
    "beczka",
    "sorbent",
)


DEFAULT_TACTICAL_QUEUE_CACHE_SECONDS = 30.0


@dataclass(frozen=True)
class WordPressContentIndex:
    exact_urls: dict[str, MetricFact]
    paths: dict[str, list[MetricFact]]


@dataclass(frozen=True)
class WordPressMatch:
    fact: MetricFact | None
    confidence: WordPressMatchConfidence
    requested_url_key: str
    requested_path_key: str


@dataclass(frozen=True)
class TacticalQueueCacheEntry:
    created_at: float
    queue: TacticalQueueResponse


def _stable_slug(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.lower())
    compact = "_".join(part for part in normalized.split("_") if part)
    return (compact or "unknown")[:48]


def _normalize_url_key(value: str) -> str:
    parsed = urlparse(value)
    if parsed.netloc:
        path = parsed.path or "/"
        return f"{parsed.netloc.lower()}{_normalize_path_only(path)}"
    return _normalize_path_key(value)


def _normalize_path_key(value: str) -> str:
    parsed = urlparse(value)
    return _normalize_path_only(parsed.path or value)


def _normalize_path_only(value: str) -> str:
    path = value.strip() or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path.lower()


def _url_host(value: str) -> str:
    return urlparse(value).netloc.lower()
