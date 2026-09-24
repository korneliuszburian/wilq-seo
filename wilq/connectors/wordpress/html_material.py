"""Bounded visible-material extraction for public WordPress HTML."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from wilq.connectors.wordpress.errors import WordPressDraftReadError
from wilq.connectors.wordpress.text import clean_metadata_text

_MAX_COMPLETE_HTML_CHARS = 1_000_000


def require_complete_material_html(value: str) -> str:
    """Reject oversized HTML rather than silently hashing a truncated article."""

    if len(value) > _MAX_COMPLETE_HTML_CHARS:
        raise WordPressDraftReadError(
            "WordPress HTML przekroczył limit pełnego materiału; odczyt wymaga weryfikacji."
        )
    return value

_CONTENT_CLASSES = frozenset(
    {
        "article-body",
        "article-content",
        "article__content",
        "entry-content",
        "post-content",
        "post__content",
        "wp-block-post-content",
    }
)
_HIDDEN_CLASSES = frozenset({"hidden", "is-hidden", "d-none", "u-hidden"})
_IGNORED_TAGS = frozenset(
    {"script", "style", "nav", "header", "footer", "aside", "template"}
)
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "source",
        "track",
        "wbr",
    }
)


@dataclass
class _Candidate:
    kind: str
    tag: str
    same_tag_depth: int
    chunks: list[str]
    headings: list[str]
    article_depth: int
    specificity: int
    contains_h1: bool = False


class HtmlMaterialParser(HTMLParser):
    """Extract the narrowest visible primary article boundary from one page."""

    def __init__(self) -> None:
        super().__init__()
        self._candidates: dict[str, list[_Candidate]] = {
            "article_content": [],
            "article": [],
        }
        self._candidate_stack: list[_Candidate] = []
        self._main_chunks: list[str] = []
        self._body_chunks: list[str] = []
        self._main_depth = 0
        self._body_depth = 0
        self._ignored_root_tag: str | None = None
        self._ignored_root_same_tag_depth = 0
        self._heading_tag: str | None = None
        self._heading_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        attr_map = {key.casefold(): value or "" for key, value in attrs}
        for candidate in self._candidate_stack:
            if candidate.tag == normalized_tag:
                candidate.same_tag_depth += 1
        if normalized_tag == "body":
            self._body_depth += 1
        if normalized_tag in {"main", "article"}:
            self._main_depth += 1
        self._enter_ignored_region(normalized_tag, attr_map)
        if self._ignored_root_tag is not None:
            return
        candidate_kind = self._candidate_kind(normalized_tag, attr_map)
        if candidate_kind is not None:
            kind, specificity = candidate_kind
            self._candidate_stack.append(
                _Candidate(
                    kind=kind,
                    tag=normalized_tag,
                    same_tag_depth=0,
                    chunks=[],
                    headings=[],
                    article_depth=sum(
                        candidate.kind == "article" for candidate in self._candidate_stack
                    ),
                    specificity=specificity,
                )
            )
        if normalized_tag == "h1":
            for candidate in self._candidate_stack:
                if self._candidate_is_current(candidate):
                    candidate.contains_h1 = True
        elif normalized_tag in {"h2", "h3"} and self._heading_tag is None:
            self._heading_tag = normalized_tag
            self._heading_chunks = []

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if self._heading_tag == normalized_tag:
            heading = clean_metadata_text(" ".join(self._heading_chunks))
            if heading:
                for candidate in self._candidate_stack:
                    if self._candidate_is_current(candidate):
                        candidate.headings.append(heading)
            self._heading_tag = None
            self._heading_chunks = []
        self._finish_candidates(normalized_tag)
        self._leave_ignored_region(normalized_tag)
        if normalized_tag in {"main", "article"}:
            self._main_depth = max(0, self._main_depth - 1)
        if normalized_tag == "body":
            self._body_depth = max(0, self._body_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._ignored_root_tag is not None:
            return
        if self._heading_tag is not None:
            self._heading_chunks.append(data)
        for candidate in self._candidate_stack:
            if self._candidate_is_current(candidate):
                candidate.chunks.append(data)
        if self._main_depth:
            self._main_chunks.append(data)
        if self._body_depth:
            self._body_chunks.append(data)

    def close(self) -> None:
        super().close()
        while self._candidate_stack:
            candidate = self._candidate_stack.pop()
            self._candidates[candidate.kind].append(candidate)

    @property
    def material(self) -> tuple[str, str, list[str]]:
        nested_content = [
            candidate
            for candidate in self._candidates["article_content"]
            if candidate.article_depth == 1
        ]
        top_level_articles = [
            candidate
            for candidate in self._candidates["article"]
            if candidate.article_depth == 0
        ]
        standalone_content = sorted(
            (
                candidate
                for candidate in self._candidates["article_content"]
                if candidate.article_depth == 0
            ),
            key=lambda candidate: candidate.specificity,
        )
        groups = (
            (nested_content, "public_html.article_content"),
            (top_level_articles, "public_html.article"),
            (standalone_content, "public_html.article_content"),
        )
        for candidates, region in groups:
            preferred = [candidate for candidate in candidates if candidate.contains_h1]
            candidate: _Candidate | None = (preferred or candidates)[0] if candidates else None
            if candidate is not None:
                text = clean_metadata_text(" ".join(candidate.chunks))
                if text:
                    return text, region, candidate.headings
        for chunks, region in (
            (self._main_chunks, "public_html.main"),
            (self._body_chunks, "public_html.body"),
        ):
            if text := clean_metadata_text(" ".join(chunks)):
                return text, region, []
        return "", "", []

    @staticmethod
    def _candidate_kind(tag: str, attrs: dict[str, str]) -> tuple[str, int] | None:
        if tag == "article":
            return "article", 0
        if attrs.get("itemprop", "").casefold() == "articlebody":
            return "article_content", 0
        classes = {value.casefold() for value in attrs.get("class", "").split()}
        element_id = attrs.get("id", "").casefold()
        matched = classes.intersection(_CONTENT_CLASSES)
        if element_id in _CONTENT_CLASSES:
            matched.add(element_id)
        if matched:
            specificity = min(
                2 if value == "entry-content" else 0 if "post" in value else 1
                for value in matched
            )
            return "article_content", specificity
        return None

    def _finish_candidates(self, tag: str) -> None:
        for index in range(len(self._candidate_stack) - 1, -1, -1):
            candidate = self._candidate_stack[index]
            if candidate.tag != tag:
                continue
            if candidate.same_tag_depth:
                candidate.same_tag_depth -= 1
            else:
                del self._candidate_stack[index]
                self._candidates[candidate.kind].append(candidate)

    def _candidate_is_current(self, candidate: _Candidate) -> bool:
        open_article_count = sum(
            open_candidate.kind == "article"
            for open_candidate in self._candidate_stack
        )
        candidate_article_count = candidate.article_depth + (
            candidate.kind == "article"
        )
        return candidate_article_count == open_article_count

    def _enter_ignored_region(self, tag: str, attrs: dict[str, str]) -> None:
        if self._ignored_root_tag is not None:
            if tag == self._ignored_root_tag:
                self._ignored_root_same_tag_depth += 1
            return
        classes = {value.casefold() for value in attrs.get("class", "").split()}
        style = attrs.get("style", "").replace(" ", "").casefold()
        hidden = (
            "hidden" in attrs
            or "inert" in attrs
            or attrs.get("aria-hidden", "").casefold() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
            or bool(classes.intersection(_HIDDEN_CLASSES))
        )
        if tag not in _VOID_TAGS and (tag in _IGNORED_TAGS or hidden):
            self._ignored_root_tag = tag

    def _leave_ignored_region(self, tag: str) -> None:
        if tag != self._ignored_root_tag:
            return
        if self._ignored_root_same_tag_depth:
            self._ignored_root_same_tag_depth -= 1
        else:
            self._ignored_root_tag = None


__all__ = ["HtmlMaterialParser", "require_complete_material_html"]
