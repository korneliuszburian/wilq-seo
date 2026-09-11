from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urlparse

import httpx

from wilq.content.workflow.policies import wordpress_dev_host_allowed

_PANEL_TARGET_PREFIX = "sub-mega-menu-panel-"
_MAX_HTML_BYTES = 1_000_000
_VOID_ELEMENTS = {
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
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass(frozen=True)
class WordPressAcfRelationshipObservation:
    """A bounded, public rendering observation for one ACF ID relationship.

    The observation only identifies values already present in an exact ACF
    source row. It is not a write profile and never grants permission to alter
    a relationship field.
    """

    status: Literal["available", "unavailable"]
    source_url: str
    labels_by_id: dict[int, str]
    reason: str


def observe_wordpress_acf_panel_labels(
    source_url: str,
    relationship_ids: list[int],
    *,
    http_client: httpx.Client | None = None,
) -> WordPressAcfRelationshipObservation:
    """Resolve exact ACF IDs only when public markup exposes matching panels.

    The theme must render every requested relationship ID as the suffix of a
    `data-panel-target="sub-mega-menu-panel-{id}"` attribute. Any missing,
    ambiguous or malformed label fails closed; no partial relationship map is
    returned to an operator.
    """

    unique_ids = list(dict.fromkeys(relationship_ids))
    if not source_url or not unique_ids or any(value <= 0 for value in unique_ids):
        return WordPressAcfRelationshipObservation(
            status="unavailable",
            source_url=source_url,
            labels_by_id={},
            reason="Brakuje dokładnej listy identyfikatorów relacji ACF.",
        )

    parser, failure = _read_public_panel_markup(source_url, http_client=http_client)
    if failure is not None:
        return failure
    if parser is None:
        return _unavailable(source_url, "Nie udało się odczytać publicznego układu relacji na dev.")

    labels_by_id: dict[int, str] = {}
    for relationship_id in unique_ids:
        labels = parser.labels_by_id.get(relationship_id, set())
        if len(labels) != 1:
            return _unavailable(
                source_url,
                "Publiczny układ dev nie potwierdza jednoznacznie wszystkich relacji ACF.",
            )
        labels_by_id[relationship_id] = next(iter(labels))
    return WordPressAcfRelationshipObservation(
        status="available",
        source_url=source_url,
        labels_by_id=labels_by_id,
        reason="Publiczny układ dev potwierdza dokładne ID i etykiety relacji ACF.",
    )


def _read_public_panel_markup(
    source_url: str,
    *,
    http_client: httpx.Client | None,
) -> tuple[_PanelLabelParser | None, WordPressAcfRelationshipObservation | None]:
    try:
        parsed_source = urlparse(source_url)
    except ValueError:
        return None, _unavailable(
            source_url,
            "Adres źródłowy relacji ACF ma nieprawidłową składnię URL.",
        )
    if (
        parsed_source.scheme != "https"
        or parsed_source.username is not None
        or parsed_source.password is not None
        or not parsed_source.hostname
        or not wordpress_dev_host_allowed(source_url)
    ):
        return None, _unavailable(
            source_url,
            "Adres źródłowy relacji ACF nie spełnia wymagań bezpiecznego odczytu.",
        )
    try:
        source_port = parsed_source.port
    except ValueError:
        return None, _unavailable(source_url, "Adres źródłowy relacji ACF ma nieprawidłowy port.")
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=10, follow_redirects=False)
    parser = _PanelLabelParser()
    try:
        with client.stream("GET", source_url, follow_redirects=False) as response:
            try:
                parsed_response = urlparse(str(response.url))
                response_port = parsed_response.port
            except ValueError:
                return None, _unavailable(
                    source_url, "Odczyt relacji ACF zwrócił nieprawidłowy adres lub port."
                )
            if (
                parsed_response.scheme != parsed_source.scheme
                or parsed_response.hostname != parsed_source.hostname
                or (response_port if response_port is not None else 443)
                != (source_port if source_port is not None else 443)
                or parsed_response.username is not None
                or parsed_response.password is not None
            ):
                return None, _unavailable(
                    source_url,
                    "Odczyt relacji ACF zwrócił adres spoza zatwierdzonego źródła.",
                )
            response.raise_for_status()
            observed_bytes = 0
            for chunk in response.iter_text():
                observed_bytes += len(chunk.encode("utf-8", errors="ignore"))
                if observed_bytes > _MAX_HTML_BYTES:
                    return None, _unavailable(
                        source_url, "Strona dev przekroczyła bezpieczny limit odczytu."
                    )
                parser.feed(chunk)
        parser.close()
    except (httpx.InvalidURL, httpx.HTTPError, UnicodeError, ValueError):
        return None, _unavailable(
            source_url, "Nie udało się odczytać publicznego układu relacji na dev."
        )
    finally:
        if owns_client:
            client.close()
    return parser, None


def _unavailable(source_url: str, reason: str) -> WordPressAcfRelationshipObservation:
    return WordPressAcfRelationshipObservation(
        status="unavailable", source_url=source_url, labels_by_id={}, reason=reason
    )


class _PanelLabelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.labels_by_id: dict[int, set[str]] = {}
        self._active: tuple[int, str, list[str]] | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._active is not None:
            relationship_id, opening_tag, stack = self._active
            if tag not in _VOID_ELEMENTS:
                stack.append(tag)
            return
        target = dict(attrs).get("data-panel-target")
        parsed_relationship_id = _panel_id(target)
        if parsed_relationship_id is not None:
            self._active = (parsed_relationship_id, tag, [tag])
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_ELEMENTS:
            return
        if self._active is None:
            return
        relationship_id, opening_tag, stack = self._active
        if not stack or tag != stack[-1]:
            self._active = None
            self._parts = []
            return
        stack.pop()
        if stack:
            self._active = (relationship_id, opening_tag, stack)
            return
        label = " ".join("".join(self._parts).split())
        if label:
            self.labels_by_id.setdefault(relationship_id, set()).add(label)
        self._active = None
        self._parts = []


def _panel_id(value: str | None) -> int | None:
    if not isinstance(value, str) or not value.startswith(_PANEL_TARGET_PREFIX):
        return None
    suffix = value.removeprefix(_PANEL_TARGET_PREFIX)
    if not suffix.isascii() or not suffix.isdecimal():
        return None
    try:
        relationship_id = int(suffix)
    except ValueError:
        return None
    return relationship_id if relationship_id > 0 else None


__all__ = ["WordPressAcfRelationshipObservation", "observe_wordpress_acf_panel_labels"]
