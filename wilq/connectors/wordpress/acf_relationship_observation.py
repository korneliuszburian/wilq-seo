from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Literal

import httpx

_PANEL_TARGET_PREFIX = "sub-mega-menu-panel-"
_MAX_HTML_BYTES = 1_000_000


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

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=10, follow_redirects=True)
    parser = _PanelLabelParser()
    try:
        with client.stream("GET", source_url) as response:
            response.raise_for_status()
            observed_bytes = 0
            for chunk in response.iter_text():
                observed_bytes += len(chunk.encode("utf-8", errors="ignore"))
                if observed_bytes > _MAX_HTML_BYTES:
                    return _unavailable(
                        source_url, "Strona dev przekroczyła bezpieczny limit odczytu."
                    )
                parser.feed(chunk)
        parser.close()
    except httpx.HTTPError:
        return _unavailable(source_url, "Nie udało się odczytać publicznego układu relacji na dev.")
    finally:
        if owns_client:
            client.close()

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


def _unavailable(source_url: str, reason: str) -> WordPressAcfRelationshipObservation:
    return WordPressAcfRelationshipObservation(
        status="unavailable", source_url=source_url, labels_by_id={}, reason=reason
    )


class _PanelLabelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.labels_by_id: dict[int, set[str]] = {}
        self._active: tuple[int, str, int] | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._active is not None:
            relationship_id, opening_tag, depth = self._active
            self._active = (relationship_id, opening_tag, depth + 1)
            return
        target = dict(attrs).get("data-panel-target")
        relationship_id = _panel_id(target)
        if relationship_id is not None:
            self._active = (relationship_id, tag, 1)
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._active is None:
            return
        relationship_id, opening_tag, depth = self._active
        remaining_depth = depth - 1
        if remaining_depth > 0:
            self._active = (relationship_id, opening_tag, remaining_depth)
            return
        if tag != opening_tag:
            self._active = None
            self._parts = []
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
    if not suffix.isdigit() or int(suffix) <= 0:
        return None
    return int(suffix)


__all__ = ["WordPressAcfRelationshipObservation", "observe_wordpress_acf_panel_labels"]
