from __future__ import annotations

from typing import Literal

ContentTargetSourceKind = Literal[
    "document_title",
    "document_content",
    "page_assets",
    "rich_text",
    "faq",
    "cta",
    "internal_link",
]


def source_field_specs(kind: ContentTargetSourceKind) -> list[tuple[str, str]]:
    return {
        "document_title": [("wordpress_title", "Tytuł strony")],
        "document_content": [("document_html", "Pełna treść dokumentu")],
        "page_assets": [
            ("meta_title", "Tytuł meta"),
            ("meta_description", "Opis meta"),
            ("h1", "Nagłówek H1"),
            ("lead", "Lead strony"),
        ],
        "rich_text": [("heading", "Nagłówek sekcji"), ("content_html", "Treść sekcji")],
        "faq": [("question", "Pytanie"), ("answer_markdown", "Odpowiedź")],
        "cta": [("body_markdown", "Treść CTA")],
        "internal_link": [("anchor_text", "Tekst linku"), ("target_url", "Adres linku")],
    }[kind]
