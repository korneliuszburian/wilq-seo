"""Shared policy decisions for content workflow integrations."""

from __future__ import annotations

from urllib.parse import urlparse

from wilq.credentials.runtime import variable_value

WORDPRESS_DEV_HOSTS = {"ekologus.dev.proudsite.pl"}
_WORDPRESS_DRAFT_WRITE_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def wordpress_draft_writes_enabled() -> bool:
    return (
        (variable_value("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES") or "")
        .strip()
        .lower()
        in _WORDPRESS_DRAFT_WRITE_TRUTHY_VALUES
    )


def wordpress_dev_host_allowed(base_url: str | None) -> bool:
    if not base_url:
        return False
    return (urlparse(base_url).hostname or "").lower() in WORDPRESS_DEV_HOSTS


__all__ = [
    "WORDPRESS_DEV_HOSTS",
    "wordpress_draft_writes_enabled",
    "wordpress_dev_host_allowed",
]
