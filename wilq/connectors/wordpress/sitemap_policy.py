"""Classification policy for WordPress sitemap child maps."""

from __future__ import annotations

from urllib.parse import urlparse

EDITORIAL_SITEMAP_GROUPS = frozenset(
    {
        "posts",
        "pages",
        "training",
        "training_close",
        "career",
        "uslugi",
        "partnerzy",
        "szkolenia_otwarte",
        "specjalisci",
        "ofertypracy",
    }
)
COMMERCE_SITEMAP_GROUPS = frozenset({"products", "product_cat"})
TAXONOMY_SITEMAP_GROUPS = frozenset(
    {
        "category",
        "post_tag",
        "obszary_dzialania",
        "typ_wiedzy",
        "typ_szkolenia_otwarte",
        "kategorie_ofert",
        "author",
    }
)
LEGACY_COMMERCE_PATH_MARKERS = ("sorbent", "/sklep", "/shop")


def is_commerce_only_url(url: str) -> bool:
    """Return whether a public URL belongs to the non-editorial catalog."""

    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    path = parsed.path.casefold()
    return host == "sklep.ekologus.pl" or any(
        marker in path for marker in LEGACY_COMMERCE_PATH_MARKERS
    )


def sitemap_group_for_url(sitemap_url: str) -> str:
    filename = urlparse(sitemap_url).path.rsplit("/", 1)[-1].lower()
    for prefix, group in (
        ("post-sitemap", "posts"),
        ("page-sitemap", "pages"),
        ("product-sitemap", "products"),
        ("product_cat-sitemap", "product_cat"),
        ("training-close-sitemap", "training_close"),
        ("training-sitemap", "training"),
        ("career-sitemap", "career"),
        ("uslugi-sitemap", "uslugi"),
        ("partnerzy-sitemap", "partnerzy"),
        ("szkolenia_otwarte-sitemap", "szkolenia_otwarte"),
        ("specjalisci-sitemap", "specjalisci"),
        ("ofertypracy-sitemap", "ofertypracy"),
        ("category-sitemap", "category"),
        ("post_tag-sitemap", "post_tag"),
        ("obszary_dzialania-sitemap", "obszary_dzialania"),
        ("typ_wiedzy-sitemap", "typ_wiedzy"),
        ("typ_szkolenia_otwarte-sitemap", "typ_szkolenia_otwarte"),
        ("kategorie_ofert-sitemap", "kategorie_ofert"),
        ("author-sitemap", "author"),
    ):
        if filename.startswith(prefix):
            return group
    return "other"


def sitemap_entry_policy(group: str) -> tuple[str, str]:
    if group in COMMERCE_SITEMAP_GROUPS:
        return "false", "commerce_catalog"
    if group in EDITORIAL_SITEMAP_GROUPS:
        return "true", "editorial"
    if group in TAXONOMY_SITEMAP_GROUPS:
        return "false", "taxonomy"
    return "false", "other"


def sitemap_url_object(entry: dict[str, str], *, metadata_group: str = "other") -> dict[str, str]:
    editorial_eligible, inventory_scope = sitemap_entry_policy(metadata_group)
    if is_commerce_only_url(entry["loc"]):
        editorial_eligible, inventory_scope = "false", "commerce_catalog"
    return {
        "content_type": "sitemap",
        "content_url": entry["loc"],
        "modified_gmt": entry.get("lastmod", ""),
        "_metadata_group": metadata_group,
        "sitemap_group": metadata_group,
        "editorial_eligible": editorial_eligible,
        "inventory_scope": inventory_scope,
    }


__all__ = [
    "COMMERCE_SITEMAP_GROUPS",
    "EDITORIAL_SITEMAP_GROUPS",
    "sitemap_entry_policy",
    "sitemap_group_for_url",
    "sitemap_url_object",
    "is_commerce_only_url",
]
