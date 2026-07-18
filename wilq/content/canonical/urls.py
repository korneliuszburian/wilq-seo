from __future__ import annotations

from urllib.parse import urlparse

from wilq.schemas import ContentDecisionItem

CONTENT_SOURCE_SITE_HOSTS = {
    "www.ekologus.pl",
    "ekologus.pl",
    "sklep.ekologus.pl",
}


def content_decision_final_canonical_url(decision: ContentDecisionItem) -> str | None:
    if decision.final_canonical_url:
        return decision.final_canonical_url
    return decision.intended_final_url or decision.source_public_url or decision.page


def content_decision_has_public_final_canonical(decision: ContentDecisionItem) -> bool:
    return content_url_host(content_decision_final_canonical_url(decision)) in (
        CONTENT_SOURCE_SITE_HOSTS
    )


def content_decision_url_semantics(
    *,
    source_url: str,
    wordpress_content_url: str | None,
) -> dict[str, str | None]:
    source_public_url = source_url
    intended_final_url = (
        wordpress_content_url
        if content_url_host(wordpress_content_url) in CONTENT_SOURCE_SITE_HOSTS
        else source_public_url
    )
    return {
        "source_public_url": source_public_url,
        "preview_url": None,
        "intended_final_url": intended_final_url,
        "final_canonical_url": intended_final_url,
    }


def content_normalized_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path = content_normalized_path(value)
    if not host or not path:
        return ""
    return f"{parsed.scheme.lower() or 'https'}://{host}{path}"


def content_url_host(value: str | None) -> str | None:
    if not value:
        return None
    return urlparse(value).netloc.lower() or None


def content_normalized_path(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    path = parsed.path.rstrip("/")
    return path or "/"
