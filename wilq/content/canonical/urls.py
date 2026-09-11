from __future__ import annotations

import re
from urllib.parse import urlparse

from wilq.schemas import ContentDecisionItem

CONTENT_SOURCE_SITE_HOSTS = {
    "www.ekologus.pl",
    "ekologus.pl",
    "sklep.ekologus.pl",
}
CONTENT_AUTHORING_SITE_HOSTS = {"ekologus.dev.proudsite.pl"}
_UNSAFE_PUBLIC_URL_CHARACTERS = re.compile(r'''[\x00-\x20\x7f<>"'`()\[\]{}|\\^]''')


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


def content_is_safe_public_url(value: str | None) -> bool:
    return _content_is_safe_url(value, CONTENT_SOURCE_SITE_HOSTS)


def content_is_safe_authoring_url(value: str | None) -> bool:
    """Accept only the one HTTPS dev authoring origin used for typed REST facts."""

    return _content_is_safe_url(value, CONTENT_AUTHORING_SITE_HOSTS)


def content_authoring_path_matches_public_url(
    public_url: str | None,
    authoring_url: str | None,
) -> bool:
    """Match one safe public URL to one safe dev REST URL by normalized path.

    This is deliberately the one predicate used both to classify an otherwise
    ambiguous public inventory row and to attach the REST evidence that made
    that classification possible.  It never treats a host, query, fragment,
    credential-bearing URL, or URL keyword as an identity signal.
    """

    return (
        content_is_safe_public_url(public_url)
        and content_is_safe_authoring_url(authoring_url)
        and content_normalized_path(public_url).casefold()
        == content_normalized_path(authoring_url).casefold()
    )


def _content_is_safe_url(value: str | None, allowed_hosts: set[str]) -> bool:
    if not value or value != value.strip() or _UNSAFE_PUBLIC_URL_CHARACTERS.search(value):
        return False
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError:
        return False
    hostname = parsed.hostname.casefold() if parsed.hostname else None
    return (
        parsed.scheme.casefold() == "https"
        and hostname in allowed_hosts
        and parsed.username is None
        and parsed.password is None
        and port is None
        and parsed.netloc.casefold() == hostname
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
        and parsed.path.startswith("/")
    )


def content_normalized_path(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    path = parsed.path.rstrip("/")
    return path or "/"
