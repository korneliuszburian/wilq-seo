from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlparse

from markdown_it import MarkdownIt

_MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": False})
_VOID_ELEMENTS = frozenset({"br", "hr"})
_ALLOWED_ELEMENTS = frozenset(
    {
        "a",
        "blockquote",
        "br",
        "code",
        "del",
        "div",
        "em",
        "figcaption",
        "figure",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
_BLOCK_ELEMENTS = frozenset(
    {
        "blockquote",
        "div",
        "figcaption",
        "figure",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "ol",
        "p",
        "pre",
        "table",
        "tr",
        "ul",
    }
)
_GLOBAL_ATTRIBUTES = frozenset({"class", "id", "title"})


def content_html_from_markdown(markdown: str) -> str:
    """Create the non-persisted starting HTML buffer for a legacy revision."""

    return validate_content_html(str(_MARKDOWN.render(markdown)))


def validate_content_html(value: str) -> str:
    """Accept only bounded editorial HTML while preserving its authored structure."""

    content_html = value.strip()
    if not content_html:
        raise ValueError("Draft revision content HTML cannot be blank.")
    validator = _EditorialHtmlValidator()
    try:
        validator.feed(content_html)
        validator.close()
    except ValueError:
        raise
    if validator.open_elements:
        raise ValueError("Draft revision content HTML must close every element.")
    if not validator.has_visible_text:
        raise ValueError("Draft revision content HTML must contain visible text.")
    return content_html


class _EditorialHtmlValidator(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.open_elements: list[str] = []
        self.has_visible_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._validate_start(tag, attrs)
        if tag not in _VOID_ELEMENTS:
            self.open_elements.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._validate_start(tag, attrs)
        if tag not in _VOID_ELEMENTS:
            raise ValueError(f"Draft revision content HTML cannot self-close <{tag}>.")

    def handle_endtag(self, tag: str) -> None:
        if tag not in _ALLOWED_ELEMENTS or tag in _VOID_ELEMENTS:
            raise ValueError(f"Draft revision content HTML has an unsafe closing tag: {tag}.")
        if not self.open_elements or self.open_elements[-1] != tag:
            raise ValueError(f"Draft revision content HTML has an unmatched closing tag: {tag}.")
        self.open_elements.pop()

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.has_visible_text = True

    def handle_comment(self, data: str) -> None:
        raise ValueError("Draft revision content HTML cannot contain comments.")

    def handle_decl(self, decl: str) -> None:
        raise ValueError("Draft revision content HTML cannot contain declarations.")

    def unknown_decl(self, data: str) -> None:
        raise ValueError("Draft revision content HTML cannot contain declarations.")

    def _validate_start(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _ALLOWED_ELEMENTS:
            raise ValueError(f"Draft revision content HTML has an unsafe element: {tag}.")
        for name, value in attrs:
            attribute = name.casefold()
            if attribute.startswith("on") or attribute == "style":
                raise ValueError(f"Draft revision content HTML has an unsafe attribute: {name}.")
            if attribute in _GLOBAL_ATTRIBUTES or attribute.startswith(("aria-", "data-")):
                continue
            if tag == "a" and attribute in {"href", "rel", "target"}:
                self._validate_link_attribute(attribute, value)
                continue
            if tag in {"td", "th"} and attribute in {"colspan", "rowspan"}:
                if value is None or not value.isdigit() or int(value) < 1:
                    raise ValueError(f"Draft revision content HTML has an invalid {name} attribute.")
                continue
            raise ValueError(f"Draft revision content HTML has an unsupported attribute: {name}.")

    @staticmethod
    def _validate_link_attribute(name: str, value: str | None) -> None:
        if value is None:
            raise ValueError(f"Draft revision content HTML link {name} cannot be blank.")
        if name == "href":
            parsed = urlparse(value.strip())
            if parsed.scheme not in {"http", "https"}:
                raise ValueError("Draft revision content HTML links require an http(s) URL.")
        elif name == "target" and value not in {"_blank", "_self"}:
            raise ValueError("Draft revision content HTML has an unsupported link target.")
