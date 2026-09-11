from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal
from urllib.parse import ParseResult, urlparse

import httpx

from wilq.connectors.wordpress.authoring import WordPressAuthoringDevContentObject
from wilq.content.workflow.policies import wordpress_dev_host_allowed

_MAX_RESPONSE_BYTES = 1_000_000


@dataclass(frozen=True)
class NativePostContentObservation:
    status: Literal["available", "unavailable"]
    source_ref: str
    blocker_code: str | None
    reason: str


def observe_native_post_content(
    item: WordPressAuthoringDevContentObject,
) -> NativePostContentObservation:
    """Observe native post content and preserve typed read failures."""

    try:
        parsed = urlparse(item.link)
    except ValueError:
        return _unavailable(
            item.link,
            "wordpress_native_content_target_invalid",
            "Adres obiektu dev ma nieprawidłową składnię URL.",
        )
    if (
        parsed.scheme != "https"
        or not wordpress_dev_host_allowed(item.link)
        or parsed.username is not None
        or parsed.password is not None
        or not positive_ascii_decimal(item.post_id)
    ):
        return _unavailable(
            item.link,
            "wordpress_native_content_target_invalid",
            "Adres lub identyfikator obiektu nie spełnia wymagań bezpiecznego odczytu.",
        )
    if not _valid_url_port(parsed):
        return _unavailable(
            item.link,
            "wordpress_native_content_target_invalid",
            "Adres obiektu ma nieprawidłowy port.",
        )
    endpoint = item.rest_endpoint.strip().strip("/")
    if endpoint not in {"pages", "posts"}:
        return _unavailable(
            item.link,
            "wordpress_native_content_endpoint_invalid",
            "Odczyt natywnej treści nie ma potwierdzonego endpointu pages/posts.",
        )
    request_url = f"{parsed.scheme}://{parsed.netloc}/wp-json/wp/v2/{endpoint}/{item.post_id}"
    payload, failure = _fetch_native_content_payload(request_url)
    if failure is not None:
        return failure
    if not isinstance(payload, dict) or "id" not in payload:
        return _unavailable(
            request_url,
            "wordpress_native_content_invalid_payload",
            "WordPress nie zwrócił identyfikatora obserwowanego obiektu.",
        )
    if str(payload.get("id")) != item.post_id:
        return _unavailable(
            request_url,
            "wordpress_native_content_identity_mismatch",
            "WordPress zwrócił treść innego obiektu niż wskazany post ID.",
        )
    content = payload.get("content")
    rendered = content.get("rendered") if isinstance(content, dict) else None
    if not isinstance(rendered, str) or not rendered.strip():
        return _unavailable(
            request_url,
            "wordpress_native_content_empty",
            "Obiekt dev nie ma odczytanej treści HTML w polu content.rendered.",
        )
    return NativePostContentObservation(
        status="available",
        source_ref=request_url,
        blocker_code=None,
        reason="WordPress potwierdził natywną treść HTML obiektu dev.",
    )


def _fetch_native_content_payload(
    request_url: str,
) -> tuple[object | None, NativePostContentObservation | None]:
    try:
        with httpx.Client(timeout=3, follow_redirects=False) as client, client.stream(
            "GET",
            request_url,
            params={"_fields": "id,content"},
            follow_redirects=False,
        ) as response:
                observed_url = getattr(response, "url", request_url)
                if not _same_origin_https(request_url, str(observed_url)):
                    return None, _unavailable(
                        request_url,
                        "wordpress_native_content_redirect",
                        "Odczyt natywnej treści zwrócił adres spoza zatwierdzonego hosta dev.",
                    )
                if getattr(response, "is_redirect", False):
                    return None, _unavailable(
                        request_url,
                        "wordpress_native_content_redirect",
                        "Odczyt natywnej treści został przekierowany i nie jest używany.",
                    )
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > _MAX_RESPONSE_BYTES:
                        return None, _unavailable(
                            request_url,
                            "wordpress_native_content_response_too_large",
                            "Odpowiedź natywnej treści przekroczyła bezpieczny limit odczytu.",
                        )
                return json.loads(bytes(body)), None
    except httpx.HTTPStatusError:
        return None, _unavailable(
            request_url,
            "wordpress_native_content_http_error",
            "WordPress nie udostępnił natywnej treści dla tego obiektu dev.",
        )
    except httpx.RequestError:
        return None, _unavailable(
            request_url,
            "wordpress_native_content_request_failed",
            "Nie udało się odczytać natywnej treści obiektu dev.",
        )
    except httpx.HTTPError:
        return None, _unavailable(
            request_url,
            "wordpress_native_content_request_failed",
            "Nie udało się odczytać natywnej treści obiektu dev.",
        )
    except ValueError:
        return None, _unavailable(
            request_url,
            "wordpress_native_content_invalid_payload",
            "WordPress zwrócił nieprawidłowy payload natywnej treści.",
        )


def _unavailable(
    source_ref: str, blocker_code: str, reason: str
) -> NativePostContentObservation:
    return NativePostContentObservation(
        status="unavailable", source_ref=source_ref, blocker_code=blocker_code, reason=reason
    )


def positive_ascii_decimal(value: str) -> bool:
    return value.isascii() and value.isdecimal() and bool(value.strip("0"))


def _same_origin_https(source: str, observed: str) -> bool:
    try:
        source_parts = urlparse(source)
        observed_parts = urlparse(observed)
        source_port = _effective_port(source_parts)
        observed_port = _effective_port(observed_parts)
    except ValueError:
        return False
    return (
        source_parts.scheme == observed_parts.scheme == "https"
        and source_parts.hostname == observed_parts.hostname
        and source_port == observed_port
        and observed_parts.username is None
        and observed_parts.password is None
    )


def _valid_url_port(parsed: ParseResult) -> bool:
    try:
        port = parsed.port
    except ValueError:
        return False
    return port is None or isinstance(port, int)


def _effective_port(parsed: ParseResult) -> int | None:
    return parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else None)


__all__ = [
    "NativePostContentObservation",
    "observe_native_post_content",
    "positive_ascii_decimal",
    "valid_url_port",
]


valid_url_port = _valid_url_port
