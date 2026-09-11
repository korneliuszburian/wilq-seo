from __future__ import annotations

from typing import Literal

from wilq.content.canonical.urls import content_authoring_path_matches_public_url

ContentKind = Literal[
    "service",
    "editorial",
    "landing_or_hub",
    "taxonomy_or_system",
    "ambiguous",
]


def classify_content_kind(wordpress_content_type: str | None) -> ContentKind:
    """Classify from typed WordPress inventory, never from URL keywords."""

    normalized = (wordpress_content_type or "").strip().casefold()
    if normalized in {"post", "posts"}:
        return "editorial"
    if normalized == "uslugi":
        return "service"
    if normalized in {"page", "pages"}:
        return "landing_or_hub"
    if normalized in {
        "author",
        "category",
        "kategorie_ofert",
        "obszary_dzialania",
        "post_tag",
        "typ_szkolenia_otwarte",
        "typ_wiedzy",
    }:
        return "taxonomy_or_system"
    return "ambiguous"


def content_kind_requires_service(kind: ContentKind) -> bool | None:
    if kind == "service":
        return True
    if kind in {"editorial", "taxonomy_or_system"}:
        return False
    return None


def classify_content_kind_from_inventory(
    wordpress_content_type: str | None,
    *,
    public_url: str,
    dev_objects: list[tuple[str, str]],
) -> tuple[str | None, ContentKind]:
    """Prefer source inventory, then one exact dev object type for the same path."""

    direct = classify_content_kind(wordpress_content_type)
    if direct != "ambiguous":
        return wordpress_content_type, direct
    observed_types = {
        content_type
        for url, content_type in dev_objects
        if content_authoring_path_matches_public_url(public_url, url) and content_type.strip()
    }
    if len(observed_types) != 1:
        return wordpress_content_type, "ambiguous"
    observed_type = observed_types.pop()
    return observed_type, classify_content_kind(observed_type)
__all__ = [
    "ContentKind",
    "classify_content_kind",
    "classify_content_kind_from_inventory",
    "content_kind_requires_service",
]
