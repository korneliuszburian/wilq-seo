from __future__ import annotations

import json
from html.parser import HTMLParser

import httpx

from wilq.connectors.wordpress.text import clean_metadata_text

WORDPRESS_METADATA_FETCH_LIMIT = 50
WORDPRESS_METADATA_MAX_BYTES = 200_000
WORDPRESS_METADATA_TIMEOUT_SECONDS = 3.0
WORDPRESS_SECTION_HEADING_LIMIT = 12
WORDPRESS_CONTENT_SUMMARY_MAX_CHARS = 240


def _enrich_sitemap_objects_with_page_metadata(
    client: httpx.Client,
    objects: list[dict[str, str]],
    *,
    distribute_content_groups: bool = False,
) -> list[dict[str, str]]:
    enriched: list[dict[str, str]] = []
    group_counts: dict[str, int] = {}
    for index, item in enumerate(objects):
        group = _metadata_budget_group(item) if distribute_content_groups else "all"
        group_count = group_counts.get(group, 0)
        limit_reached = (
            index >= WORDPRESS_METADATA_FETCH_LIMIT
            if not distribute_content_groups
            else group_count >= WORDPRESS_METADATA_FETCH_LIMIT
        )
        if limit_reached:
            enriched.append(item)
            continue
        group_counts[group] = group_count + 1
        metadata = _fetch_public_page_metadata(client, item.get("content_url", ""))
        enriched.append({**item, **metadata} if metadata else item)
    return enriched


def _metadata_budget_group(item: dict[str, str]) -> str:
    group = item.get("_metadata_group", "")
    return group if group in {"posts", "pages"} else "other"


def _fetch_public_page_metadata(client: httpx.Client, url: str) -> dict[str, str]:
    if not url:
        return {}
    try:
        response = client.get(url, timeout=WORDPRESS_METADATA_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError:
        return {}
    content_type = response.headers.get("content-type", "")
    if content_type and "html" not in content_type.lower():
        return {}
    parser = _HtmlMetadataParser()
    parser.feed(response.text[:WORDPRESS_METADATA_MAX_BYTES])
    title_or_h1 = clean_metadata_text(parser.title or parser.h1)
    canonical_url = clean_metadata_text(parser.canonical_url)
    section_headings = [
        heading
        for heading in (clean_metadata_text(value) for value in parser.section_headings)
        if heading
    ][:WORDPRESS_SECTION_HEADING_LIMIT]
    content_text = clean_metadata_text(" ".join(parser.main_text_chunks))
    content_summary = _summary_text(content_text)
    return {
        key: value
        for key, value in {
            "title_or_h1": title_or_h1,
            "canonical_url": canonical_url,
            "section_headings_json": json.dumps(section_headings, ensure_ascii=False),
            "section_heading_count": str(len(section_headings)),
            "content_summary": content_summary,
            "content_word_count": str(len(content_text.split())) if content_text else "",
        }.items()
        if value
    }


def _summary_text(value: str) -> str:
    if len(value) <= WORDPRESS_CONTENT_SUMMARY_MAX_CHARS:
        return value
    shortened = value[:WORDPRESS_CONTENT_SUMMARY_MAX_CHARS].rsplit(" ", 1)[0].strip()
    return shortened + "..."


class _HtmlMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.h1 = ""
        self.canonical_url = ""
        self.section_headings: list[str] = []
        self._capture: str | None = None
        self._capture_tag: str | None = None
        self._chunks: list[str] = []
        self.main_text_chunks: list[str] = []
        self._body_depth = 0
        self._main_depth = 0
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        normalized_tag = tag.lower()
        if normalized_tag == "body":
            self._body_depth += 1
        if normalized_tag in {"main", "article"}:
            self._main_depth += 1
        if normalized_tag in {"script", "style", "nav", "header", "footer", "aside"}:
            self._ignored_depth += 1
        if (
            normalized_tag == "link"
            and not self.canonical_url
            and "canonical" in attr_map.get("rel", "").lower().split()
        ):
            self.canonical_url = attr_map.get("href", "")
        if normalized_tag == "title" and not self.title:
            self._start_capture("title", normalized_tag)
        elif normalized_tag == "h1" and not self.h1:
            self._start_capture("h1", normalized_tag)
        elif normalized_tag in {"h2", "h3"} and len(
            self.section_headings
        ) < WORDPRESS_SECTION_HEADING_LIMIT:
            self._start_capture("section_heading", normalized_tag)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if self._capture_tag != tag.lower():
            pass
        else:
            text = clean_metadata_text(" ".join(self._chunks))
            if self._capture == "title" and text:
                self.title = text
            elif self._capture == "h1" and text:
                self.h1 = text
            elif self._capture == "section_heading" and text:
                self.section_headings.append(text)
            self._capture = None
            self._capture_tag = None
            self._chunks = []
        if normalized_tag in {"script", "style", "nav", "header", "footer", "aside"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        if normalized_tag in {"main", "article"}:
            self._main_depth = max(0, self._main_depth - 1)
        if normalized_tag == "body":
            self._body_depth = max(0, self._body_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._chunks.append(data)
        if self._ignored_depth == 0 and (self._main_depth > 0 or self._body_depth > 0):
            self.main_text_chunks.append(data)

    def _start_capture(self, capture: str, tag: str) -> None:
        self._capture = capture
        self._capture_tag = tag
        self._chunks = []
