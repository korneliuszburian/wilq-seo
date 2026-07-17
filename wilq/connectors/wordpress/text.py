from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from typing import Any

WORDPRESS_HTML_TEXT_MAX_BYTES = 200_000


def clean_metadata_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(unescape(value).split())


def wordpress_title(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    rendered = value.get("rendered")
    if not isinstance(rendered, str):
        return ""
    return clean_metadata_text(rendered)


def html_text(value: str) -> str:
    parser = _HtmlTextParser()
    parser.feed(value[:WORDPRESS_HTML_TEXT_MAX_BYTES])
    return clean_metadata_text(" ".join(parser.chunks))


def summary_text_limited(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    shortened = value[:max_chars].rsplit(" ", 1)[0].strip()
    return shortened + "..."


class _HtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self.chunks.append(data)
