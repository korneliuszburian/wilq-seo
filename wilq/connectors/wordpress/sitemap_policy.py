"""Classification policy for WordPress sitemap child maps."""

from __future__ import annotations

from urllib.parse import urlparse

EDITORIAL_SITEMAP_GROUPS = frozenset(
    {"posts", "pages", "training", "training_close", "career", "other"}
)
COMMERCE_SITEMAP_GROUPS = frozenset({"products", "product_cat"})


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
    ):
        if filename.startswith(prefix):
            return group
    return "other"


def sitemap_entry_policy(group: str) -> tuple[str, str]:
    if group in COMMERCE_SITEMAP_GROUPS:
        return "false", "commerce_catalog"
    if group in EDITORIAL_SITEMAP_GROUPS:
        return "true", "editorial"
    return "false", "other"


def sitemap_url_object(entry: dict[str, str], *, metadata_group: str = "other") -> dict[str, str]:
    editorial_eligible, inventory_scope = sitemap_entry_policy(metadata_group)
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
]
