from __future__ import annotations

import re

_LEADING_DOCUMENT_H1 = re.compile(
    r"\A\s*<h1(?:\s[^>]*)?>.*?</h1>\s*",
    re.IGNORECASE | re.DOTALL,
)


def project_target_field_value(
    value: str,
    *,
    authoring_surface_kind: str | None,
    component_id: str,
    source_field: str,
    target_field: str,
    value_kind: str,
) -> str:
    """Project one canonical value into the exact observed target surface."""

    if (
        authoring_surface_kind == "wordpress_post_content"
        and component_id == "document-content"
        and source_field == "document_html"
        and target_field == "content_html"
        and value_kind == "html"
    ):
        return wordpress_post_content_html(value)
    return value


def wordpress_post_content_html(document_html: str) -> str:
    """Project a canonical document into native WordPress post content.

    WordPress themes render the post title as the page H1. The immutable
    document keeps its H1, while the target delivery projection omits precisely
    that leading heading so preview, payload digest and written content agree.
    """

    if _LEADING_DOCUMENT_H1.match(document_html) is None:
        raise ValueError(
            "Dokument kierowany do WordPress the_content musi zaczynać się od elementu h1."
        )
    return _LEADING_DOCUMENT_H1.sub("", document_html, count=1).strip()
