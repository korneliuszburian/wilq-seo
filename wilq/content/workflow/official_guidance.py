"""One bounded, review-only official-guidance source for the content workflow.

This is deliberately a candidate seam, not a generic URL catalogue.  The
candidate identifies one exact target page and one exact ISO page; callers can
select the candidate id, never an arbitrary URL.
"""

from __future__ import annotations

import ipaddress
import socket
import ssl
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from typing import Any
from urllib.parse import SplitResult, urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.evidence_acquisition_contracts import (
    _MAX_EXCERPT_CHARS,
    OfficialGuidanceObservationReceipt,
    _sanitized_text,
)

OFFICIAL_GUIDANCE_CANDIDATE_ID = "iso_37301_official_guidance"
OFFICIAL_GUIDANCE_CANONICAL_PATH = (
    "/dlaczego-mowimy-o-compliance-czyli-zarzadzaniu-zgodnoscia"
)
OFFICIAL_GUIDANCE_SOURCE_PATH = (
    "/sites/tc309/home/projects/published/iso-37301-compliance-management.html"
)
OFFICIAL_GUIDANCE_SOURCE_URL = (
    f"https://committee.iso.org{OFFICIAL_GUIDANCE_SOURCE_PATH}"
)
OFFICIAL_GUIDANCE_SOURCE_HOST = "committee.iso.org"
OFFICIAL_GUIDANCE_CONNECTOR_ID = "official_guidance"
OFFICIAL_GUIDANCE_RECEIPT_MAX_AGE = timedelta(hours=24)
_MAX_GUIDANCE_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_GUIDANCE_HEADER_BYTES = 64 * 1024
_GUIDANCE_TRANSPORT_TIMEOUT_SECONDS = 15.0
_GUIDANCE_USER_AGENT = "WILQ-official-guidance/1.0"
_UTF8_CHARSETS = frozenset({"utf-8", "utf8", "utf_8"})
_DNS_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="wilq-official-guidance-dns",
)


class OfficialGuidanceCandidateError(ValueError):
    """The server-side candidate registry cannot resolve an exact candidate."""


class OfficialGuidanceCandidate(BaseModel):
    """Typed, static guidance candidate bound to one content target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)
    canonical_path: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    allowed_claim_scope: tuple[str, ...] = Field(min_length=1)
    blocked_claims: tuple[str, ...] = ()

    @property
    def candidate_digest(self) -> str:
        return canonical_json_digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")

    @model_validator(mode="after")
    def _validate(self) -> OfficialGuidanceCandidate:
        if self.candidate_id != OFFICIAL_GUIDANCE_CANDIDATE_ID:
            raise OfficialGuidanceCandidateError("Unknown official-guidance candidate id.")
        if self.canonical_path != OFFICIAL_GUIDANCE_CANONICAL_PATH:
            raise OfficialGuidanceCandidateError(
                "Official-guidance candidate is not bound to the exact canonical path."
            )
        if self.source_url != OFFICIAL_GUIDANCE_SOURCE_URL or not _is_exact_https_url(
            self.source_url
        ):
            raise OfficialGuidanceCandidateError(
                "Official-guidance candidate requires the exact ISO HTTPS URL."
            )
        if not self.title.strip() or not self.allowed_claim_scope:
            raise OfficialGuidanceCandidateError(
                "Official-guidance candidate requires a title and allowed claim scope."
            )
        if any(not value.strip() for value in self.allowed_claim_scope):
            raise OfficialGuidanceCandidateError(
                "Official-guidance claim scope cannot contain blank claims."
            )
        return self


def _is_exact_https_url(value: object) -> bool:
    if not isinstance(value, str) or value != value.strip():
        return False
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == OFFICIAL_GUIDANCE_SOURCE_HOST
        and parsed.username is None
        and parsed.password is None
        and port is None
        and not parsed.query
        and not parsed.fragment
        and parsed.path == OFFICIAL_GUIDANCE_SOURCE_PATH
        and parsed.netloc == OFFICIAL_GUIDANCE_SOURCE_HOST
    )


_ISO_37301_CANDIDATE = OfficialGuidanceCandidate(
    candidate_id=OFFICIAL_GUIDANCE_CANDIDATE_ID,
    canonical_path=OFFICIAL_GUIDANCE_CANONICAL_PATH,
    source_url=OFFICIAL_GUIDANCE_SOURCE_URL,
    title="ISO 37301 — compliance management systems",
    allowed_claim_scope=(
        "ISO 37301 is a current international compliance management systems standard.",
        (
            "The guidance covers establishing, developing, implementing, evaluating, "
            "maintaining, and improving a compliance management system."
        ),
        "The standard is applicable to organizations of any size.",
    ),
    blocked_claims=(
        "certification",
        "legal compliance guarantee",
        "environmental compliance guarantee",
        "purchased standard contents",
    ),
)


def official_guidance_candidates() -> tuple[OfficialGuidanceCandidate, ...]:
    """Return the immutable P0 candidate set."""

    return (_ISO_37301_CANDIDATE,)


def resolve_official_guidance_candidate(
    candidate_id: str,
) -> OfficialGuidanceCandidate | None:
    return next(
        (
            candidate
            for candidate in official_guidance_candidates()
            if candidate.candidate_id == candidate_id
        ),
        None,
    )


class OfficialGuidanceReadError(RuntimeError):
    """An exact official-guidance read could not produce a safe receipt."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class OfficialGuidanceMaterial:
    """Transient extracted material; the response body is never persisted."""

    url: str
    content_text: str
    extraction_region: str


class OfficialGuidanceHTTPSReader:
    """Fetch one exact ISO URL over a pinned, direct HTTPS socket.

    DNS is resolved once. Every returned address must be globally routable,
    and each selected IP is connected directly before TLS is wrapped with the
    original hostname for certificate and SNI verification. No URL opener,
    proxy environment, cookie jar, redirect handler, or credential source is
    involved.
    """

    def __init__(
        self,
        *,
        resolver: Callable[..., list[tuple[Any, ...]]] | None = None,
        socket_factory: Callable[..., Any] | None = None,
        tls_context_factory: Callable[[], ssl.SSLContext] | None = None,
        clock: Callable[[], float] | None = None,
        timeout_seconds: float = _GUIDANCE_TRANSPORT_TIMEOUT_SECONDS,
        max_response_bytes: int = _MAX_GUIDANCE_RESPONSE_BYTES,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Official-guidance transport timeout must be positive.")
        if max_response_bytes <= 0:
            raise ValueError("Official-guidance response cap must be positive.")
        self._resolver = resolver or socket.getaddrinfo
        self._socket_factory = socket_factory or socket.socket
        self._tls_context_factory = tls_context_factory or ssl.create_default_context
        self._clock = clock or time.monotonic
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes

    def read(self, source_url: str) -> OfficialGuidanceMaterial:
        parsed = _parse_exact_source_url(source_url)
        deadline = self._clock() + self._timeout_seconds
        addresses = self._resolve(
            parsed.hostname or "",
            deadline=deadline,
        )
        last_transport_error: BaseException | None = None
        for family, socktype, proto, sockaddr in addresses:
            raw_socket: Any | None = None
            tls_socket: Any | None = None
            try:
                try:
                    raw_socket = self._socket_factory(family, socktype, proto)
                    raw_socket.settimeout(self._operation_timeout(deadline))
                    raw_socket.connect(sockaddr)
                    raw_socket.settimeout(self._operation_timeout(deadline))
                    context = self._tls_context_factory()
                    tls_socket = context.wrap_socket(
                        raw_socket,
                        server_hostname=parsed.hostname,
                    )
                    tls_socket.settimeout(self._operation_timeout(deadline))
                except OfficialGuidanceReadError:
                    raise
                except (OSError, ssl.SSLError, ValueError) as exc:
                    last_transport_error = exc
                    continue
                try:
                    tls_socket.sendall(_http_request(parsed.hostname or "", parsed.path))
                    body = _read_http_response(
                        tls_socket,
                        max_response_bytes=self._max_response_bytes,
                        deadline=deadline,
                        clock=self._clock,
                        operation_timeout=self._timeout_seconds,
                    )
                except OfficialGuidanceReadError:
                    raise
                except (OSError, ssl.SSLError, ValueError) as exc:
                    raise OfficialGuidanceReadError(
                        "official_guidance_transport_unavailable",
                        "Official-guidance HTTPS transport did not complete safely.",
                    ) from exc
                break
            finally:
                if tls_socket is not None:
                    _close_quietly(tls_socket)
                elif raw_socket is not None:
                    _close_quietly(raw_socket)
        else:
            raise OfficialGuidanceReadError(
                "official_guidance_transport_unavailable",
                "All validated official-guidance addresses failed before HTTP response bytes.",
            ) from last_transport_error
        try:
            text = _decode_and_extract_html(body)
        except OfficialGuidanceReadError:
            raise
        except (UnicodeError, ValueError) as exc:
            raise OfficialGuidanceReadError(
                "official_guidance_extraction_failed",
                "Official-guidance HTML did not contain safe UTF-8 visible text.",
            ) from exc
        return OfficialGuidanceMaterial(
            url=source_url,
            content_text=text,
            extraction_region="official_html.main_or_body_visible_text",
        )

    def _operation_timeout(self, deadline: float) -> float:
        remaining = deadline - self._clock()
        if remaining <= 0:
            raise OfficialGuidanceReadError(
                "official_guidance_deadline_exceeded",
                "Official-guidance read exceeded its single transport deadline.",
            )
        return min(remaining, self._timeout_seconds)

    def _resolve(
        self,
        hostname: str,
        *,
        deadline: float,
    ) -> tuple[tuple[int, int, int, tuple[Any, ...]], ...]:
        remaining = self._operation_timeout(deadline)
        resolution = _DNS_EXECUTOR.submit(
            self._resolver,
            hostname,
            443,
            type=socket.SOCK_STREAM,
        )
        try:
            addresses = resolution.result(timeout=remaining)
        except FutureTimeoutError as exc:
            resolution.cancel()
            raise OfficialGuidanceReadError(
                "official_guidance_deadline_exceeded",
                "Official-guidance DNS resolution exceeded its deadline.",
            ) from exc
        except (OSError, ValueError) as exc:
            raise OfficialGuidanceReadError(
                "official_guidance_transport_unavailable",
                "Official-guidance DNS resolution did not complete safely.",
            ) from exc
        except Exception as exc:
            raise OfficialGuidanceReadError(
                "official_guidance_transport_unavailable",
                "Official-guidance DNS resolver failed safely.",
            ) from exc
        validated: list[tuple[int, int, int, bytes, tuple[Any, ...]]] = []
        for info in addresses:
            if len(info) < 5:
                raise OfficialGuidanceReadError(
                    "official_guidance_transport_unavailable",
                    "Official-guidance DNS result had an invalid shape.",
                )
            family, socktype, proto, _canonname, sockaddr = info[:5]
            if family not in (socket.AF_INET, socket.AF_INET6):
                continue
            try:
                address = ipaddress.ip_address(str(sockaddr[0]))
            except (IndexError, ValueError) as exc:
                raise OfficialGuidanceReadError(
                    "official_guidance_transport_unsafe_address",
                    "Official-guidance DNS returned an invalid address.",
                ) from exc
            if (
                not address.is_global
                or address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
                or address.is_multicast
                or address.is_unspecified
            ):
                raise OfficialGuidanceReadError(
                    "official_guidance_transport_unsafe_address",
                    "Official-guidance DNS returned a non-global address.",
                )
            validated.append(
                (family, socktype, proto, address.packed, _pinned_sockaddr(address, sockaddr))
            )
        if not validated:
            raise OfficialGuidanceReadError(
                "official_guidance_transport_unavailable",
                "Official-guidance DNS returned no usable global address.",
            )
        ordered = sorted(
            validated,
            key=lambda item: (
                0 if item[0] == socket.AF_INET else 1,
                item[3],
                item[0],
                item[1],
                item[2],
            ),
        )
        return tuple(
            (family, socktype, proto, sockaddr)
            for family, socktype, proto, _packed, sockaddr in ordered
        )


class OfficialGuidanceObservationAdapter:
    """Extract a bounded receipt from an injected, controlled HTTPS reader.

    The default uses ``OfficialGuidanceHTTPSReader``. Tests may inject a
    bounded material reader without touching the network.
    """

    def __init__(
        self,
        *,
        material_reader: Callable[[str], object] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._material_reader = material_reader or OfficialGuidanceHTTPSReader().read
        self._clock = clock or (lambda: datetime.now(UTC))

    def read(
        self,
        *,
        candidate_id: str,
        source_url: str,
        canonical_path: str,
    ) -> OfficialGuidanceObservationReceipt:
        candidate = resolve_official_guidance_candidate(candidate_id)
        if (
            candidate is None
            or source_url != candidate.source_url
            or canonical_path != candidate.canonical_path
        ):
            raise OfficialGuidanceReadError(
                "official_guidance_lineage_mismatch",
                "Official-guidance read is not bound to the exact server candidate.",
            )
        try:
            material = self._material_reader(source_url)
        except OfficialGuidanceReadError:
            raise
        except Exception as exc:
            raise OfficialGuidanceReadError(
                "official_guidance_transport_unavailable",
                "Official-guidance transport did not complete safely.",
            ) from exc
        material_url = getattr(material, "url", None)
        content_text = getattr(material, "content_text", None)
        extraction_region = getattr(material, "extraction_region", None)
        if (
            material_url != source_url
            or not _is_exact_https_url(material_url)
            or not isinstance(extraction_region, str)
            or not extraction_region.strip()
        ):
            raise OfficialGuidanceReadError(
                "official_guidance_lineage_mismatch",
                "Official-guidance material did not preserve the exact source URL.",
            )
        safe_body = _sanitized_text(content_text)
        if not safe_body:
            raise OfficialGuidanceReadError(
                "official_guidance_unavailable",
                "Official-guidance material returned no readable body.",
            )
        read_at = self._read_time()
        excerpt = _bounded_excerpt(safe_body)
        body_digest = _sha256(safe_body)
        excerpt_digest = _sha256(excerpt)
        snapshot_digest = canonical_json_digest(
            {
                "body_digest": body_digest,
                "candidate_digest": candidate.candidate_digest,
                "candidate_id": candidate.candidate_id,
                "canonical_path": canonical_path,
                "connector": OFFICIAL_GUIDANCE_CONNECTOR_ID,
                "excerpt_digest": excerpt_digest,
                "extraction_region": extraction_region,
                "quality_tier": "exact_official_guidance_observation",
                "read_at": read_at.isoformat(),
                "redaction_status": "sanitized",
                "source_type": "official_guidance_observation",
                "source_url": source_url,
            }
        )
        try:
            return OfficialGuidanceObservationReceipt(
                observation_id=f"content_official_guidance_observation_{snapshot_digest[:24]}",
                candidate_id=candidate.candidate_id,
                candidate_digest=candidate.candidate_digest,
                source_url=source_url,
                canonical_path=canonical_path,
                source_snapshot_digest=snapshot_digest,
                body_digest=body_digest,
                excerpt_digest=excerpt_digest,
                collected_at=read_at,
                read_at=read_at,
                freshness_date=read_at.date().isoformat(),
                evidence_ids=(f"ev_content_official_guidance_{snapshot_digest[:24]}",),
                source_connectors=(OFFICIAL_GUIDANCE_CONNECTOR_ID,),
                extraction_region=extraction_region,
                sanitized_excerpt=excerpt,
            )
        except ValueError as exc:
            raise OfficialGuidanceReadError(
                "official_guidance_unavailable",
                "Official-guidance receipt failed its safety contract.",
            ) from exc

    def _read_time(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise OfficialGuidanceReadError(
                "official_guidance_unavailable",
                "Official-guidance read did not provide an aware timestamp.",
            )
        return value.astimezone(UTC)


def official_guidance_receipt_is_fresh(
    receipt: OfficialGuidanceObservationReceipt,
    *,
    now: datetime,
) -> bool:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Official-guidance freshness assessment requires aware server time.")
    age = now.astimezone(UTC) - receipt.read_at
    return timedelta(0) <= age <= OFFICIAL_GUIDANCE_RECEIPT_MAX_AGE


def _parse_exact_source_url(source_url: str) -> SplitResult:
    if not _is_exact_https_url(source_url):
        raise OfficialGuidanceReadError(
            "official_guidance_lineage_mismatch",
            "Official-guidance transport accepts only the exact ISO candidate URL.",
        )
    parsed = urlsplit(source_url)
    if parsed.hostname is None or parsed.path != OFFICIAL_GUIDANCE_SOURCE_PATH:
        raise OfficialGuidanceReadError(
            "official_guidance_lineage_mismatch",
            "Official-guidance transport path does not match the candidate.",
        )
    return parsed


def _pinned_sockaddr(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    sockaddr: Any,
) -> tuple[Any, ...]:
    if address.version == 4:
        return (str(address), 443)
    if not isinstance(sockaddr, tuple) or len(sockaddr) < 4:
        raise OfficialGuidanceReadError(
            "official_guidance_transport_unavailable",
            "Official-guidance IPv6 DNS result had an invalid socket address.",
        )
    return (str(address), 443, sockaddr[2], sockaddr[3])


def _http_request(hostname: str, path: str) -> bytes:
    return (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {hostname}\r\n"
        f"User-Agent: {_GUIDANCE_USER_AGENT}\r\n"
        "Accept-Encoding: identity\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")


class _ResponseReader:
    def __init__(
        self,
        connection: Any,
        *,
        max_wire_bytes: int,
        deadline: float,
        clock: Callable[[], float],
        operation_timeout: float,
        buffered: bytes = b"",
    ) -> None:
        self._connection = connection
        self._buffer = buffered
        self._max_wire_bytes = max_wire_bytes
        self._deadline = deadline
        self._clock = clock
        self._operation_timeout = operation_timeout
        self._wire_bytes = len(buffered)

    def read_until(self, marker: bytes, *, limit: int) -> bytes:
        while True:
            position = self._buffer.find(marker)
            if position >= 0:
                end = position + len(marker)
                value = self._buffer[:position]
                self._buffer = self._buffer[end:]
                return value
            if len(self._buffer) > limit:
                raise OfficialGuidanceReadError(
                    "official_guidance_response_invalid",
                    "Official-guidance response headers exceeded the safety cap.",
                )
            chunk = self._recv(min(4096, limit - len(self._buffer) + 1))
            if not chunk:
                raise OfficialGuidanceReadError(
                    "official_guidance_response_invalid",
                    "Official-guidance response ended before its headers completed.",
                )
            self._buffer += chunk

    def read_exact(self, size: int) -> bytes:
        if size < 0:
            raise OfficialGuidanceReadError(
                "official_guidance_response_invalid",
                "Official-guidance response declared a negative body length.",
            )
        parts: list[bytes] = []
        remaining = size
        while remaining:
            if self._buffer:
                part = self._buffer[:remaining]
                self._buffer = self._buffer[len(part) :]
            else:
                part = self._recv(min(65536, remaining))
            if not part:
                raise OfficialGuidanceReadError(
                    "official_guidance_response_invalid",
                    "Official-guidance response ended before Content-Length bytes arrived.",
                )
            parts.append(part)
            remaining -= len(part)
        return b"".join(parts)

    def read_to_eof(self, *, max_bytes: int) -> bytes:
        parts = [self._buffer]
        total = len(self._buffer)
        self._buffer = b""
        if total > max_bytes:
            raise OfficialGuidanceReadError(
                "official_guidance_response_too_large",
                "Official-guidance response exceeded the bounded byte cap.",
            )
        while True:
            chunk = self._recv(65536)
            if not chunk:
                return b"".join(parts)
            total += len(chunk)
            if total > max_bytes:
                raise OfficialGuidanceReadError(
                    "official_guidance_response_too_large",
                    "Official-guidance response exceeded the bounded byte cap.",
                )
            parts.append(chunk)

    def _recv(self, size: int) -> bytes:
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise OfficialGuidanceReadError(
                "official_guidance_deadline_exceeded",
                "Official-guidance response exceeded its single transport deadline.",
            )
        self._connection.settimeout(min(remaining, self._operation_timeout))
        try:
            chunk = self._connection.recv(size)
        except TimeoutError as exc:
            if self._clock() >= self._deadline:
                raise OfficialGuidanceReadError(
                    "official_guidance_deadline_exceeded",
                    "Official-guidance response exceeded its single transport deadline.",
                ) from exc
            raise OfficialGuidanceReadError(
                "official_guidance_transport_timeout",
                "Official-guidance response read timed out.",
            ) from exc
        except OSError as exc:
            raise OfficialGuidanceReadError(
                "official_guidance_transport_unavailable",
                "Official-guidance response read failed safely.",
            ) from exc
        if not isinstance(chunk, bytes):
            raise OfficialGuidanceReadError(
                "official_guidance_response_invalid",
                "Official-guidance response reader returned non-bytes.",
            )
        self._wire_bytes += len(chunk)
        if self._wire_bytes > self._max_wire_bytes:
            raise OfficialGuidanceReadError(
                "official_guidance_response_too_large",
                "Official-guidance wire response exceeded the bounded byte cap.",
            )
        return chunk


def _read_http_response(
    connection: Any,
    *,
    max_response_bytes: int,
    deadline: float,
    clock: Callable[[], float],
    operation_timeout: float,
) -> bytes:
    reader = _ResponseReader(
        connection,
        max_wire_bytes=max_response_bytes,
        deadline=deadline,
        clock=clock,
        operation_timeout=operation_timeout,
    )
    header_bytes = reader.read_until(b"\r\n\r\n", limit=_MAX_GUIDANCE_HEADER_BYTES)
    status, headers = _parse_response_headers(header_bytes)
    if 300 <= status < 400:
        raise OfficialGuidanceReadError(
            "official_guidance_redirect_rejected",
            "Official-guidance redirects are not allowed for exact lineage.",
        )
    if status != 200:
        raise OfficialGuidanceReadError(
            "official_guidance_http_status",
            "Official-guidance source did not return HTTP 200.",
        )
    _require_html_content_type(headers)
    content_encoding = headers.get("content-encoding", "").strip().casefold()
    if content_encoding not in {"", "identity"}:
        raise OfficialGuidanceReadError(
            "official_guidance_content_encoding_unsupported",
            "Official-guidance response compression is not allowed.",
        )
    transfer_encoding = headers.get("transfer-encoding", "").strip().casefold()
    content_length = _content_length(headers)
    if transfer_encoding and content_length is not None:
        raise OfficialGuidanceReadError(
            "official_guidance_response_invalid",
            "Official-guidance response has ambiguous transfer framing.",
        )
    if transfer_encoding in {"", "identity"}:
        if content_length is not None:
            if content_length > max_response_bytes:
                raise OfficialGuidanceReadError(
                    "official_guidance_response_too_large",
                    "Official-guidance Content-Length exceeds the bounded byte cap.",
                )
            return reader.read_exact(content_length)
        return reader.read_to_eof(max_bytes=max_response_bytes)
    if transfer_encoding == "chunked":
        return _read_chunked_body(reader, max_response_bytes=max_response_bytes)
    raise OfficialGuidanceReadError(
        "official_guidance_response_invalid",
        "Official-guidance transfer encoding is not allowed.",
    )


def _parse_response_headers(header_bytes: bytes) -> tuple[int, dict[str, str]]:
    try:
        lines = header_bytes.decode("iso-8859-1").split("\r\n")
        status_line = lines[0].split(" ", 2)
        status = int(status_line[1])
    except (IndexError, ValueError, UnicodeError) as exc:
        raise OfficialGuidanceReadError(
            "official_guidance_response_invalid",
            "Official-guidance response status line was invalid.",
        ) from exc
    if (
        len(status_line) < 2
        or not status_line[0].startswith("HTTP/")
        or len(status_line[1]) != 3
        or not status_line[1].isdigit()
    ):
        raise OfficialGuidanceReadError(
            "official_guidance_response_invalid",
            "Official-guidance response status line was invalid.",
        )
    headers: dict[str, str] = {}
    ambiguous_headers = frozenset(
        {"content-length", "transfer-encoding", "content-type", "content-encoding"}
    )
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        key = name.strip().casefold()
        value = value.strip()
        if key not in ambiguous_headers:
            continue
        if key in headers and headers[key] != value:
            raise OfficialGuidanceReadError(
                "official_guidance_response_invalid",
                "Official-guidance response repeated a header inconsistently.",
            )
        headers[key] = value
    return status, headers


def _require_html_content_type(headers: dict[str, str]) -> None:
    content_type = headers.get("content-type", "")
    pieces = [piece.strip() for piece in content_type.split(";")]
    if not pieces or pieces[0].casefold() != "text/html":
        raise OfficialGuidanceReadError(
            "official_guidance_content_type_unsupported",
            "Official-guidance response must be text/html.",
        )
    charset = "utf-8"
    for parameter in pieces[1:]:
        if "=" not in parameter:
            continue
        name, value = parameter.split("=", 1)
        if name.strip().casefold() == "charset":
            charset = value.strip().strip('"').casefold()
    if charset not in _UTF8_CHARSETS:
        raise OfficialGuidanceReadError(
            "official_guidance_content_type_unsupported",
            "Official-guidance HTML must use a UTF-8-compatible charset.",
        )


def _content_length(headers: dict[str, str]) -> int | None:
    value = headers.get("content-length")
    if value is None:
        return None
    try:
        length = int(value, 10)
    except ValueError as exc:
        raise OfficialGuidanceReadError(
            "official_guidance_response_invalid",
            "Official-guidance Content-Length was invalid.",
        ) from exc
    if length < 0:
        raise OfficialGuidanceReadError(
            "official_guidance_response_invalid",
            "Official-guidance Content-Length was negative.",
        )
    return length


def _read_chunked_body(reader: _ResponseReader, *, max_response_bytes: int) -> bytes:
    parts: list[bytes] = []
    total = 0
    while True:
        line = reader.read_until(b"\r\n", limit=_MAX_GUIDANCE_HEADER_BYTES)
        try:
            chunk_size = int(line.split(b";", 1)[0].strip(), 16)
        except ValueError as exc:
            raise OfficialGuidanceReadError(
                "official_guidance_response_invalid",
                "Official-guidance chunk framing was invalid.",
            ) from exc
        if chunk_size < 0 or total + chunk_size > max_response_bytes:
            raise OfficialGuidanceReadError(
                "official_guidance_response_too_large",
                "Official-guidance chunked response exceeded the bounded byte cap.",
            )
        if chunk_size == 0:
            while True:
                trailer = reader.read_until(b"\r\n", limit=_MAX_GUIDANCE_HEADER_BYTES)
                if not trailer:
                    return b"".join(parts)
        parts.append(reader.read_exact(chunk_size))
        total += chunk_size
        if reader.read_exact(2) != b"\r\n":
            raise OfficialGuidanceReadError(
                "official_guidance_response_invalid",
                "Official-guidance chunk did not end with CRLF.",
            )


def _decode_and_extract_html(body: bytes) -> str:
    try:
        html = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OfficialGuidanceReadError(
            "official_guidance_content_type_unsupported",
            "Official-guidance HTML is not valid UTF-8.",
        ) from exc
    try:
        from wilq.content.regulatory.source_fact_proposals import _extract_html_main_text

        extracted = _extract_html_main_text(html)
    except ImportError:
        extracted = _fallback_extract_html_main_text(html)
    if not extracted.strip():
        raise OfficialGuidanceReadError(
            "official_guidance_extraction_failed",
            "Official-guidance HTML had no visible main/body text.",
        )
    return extracted


class _FallbackVisibleHTMLParser(HTMLParser):
    _ignored_tags = frozenset(
        {
            "aside",
            "footer",
            "form",
            "header",
            "nav",
            "noscript",
            "script",
            "style",
            "svg",
            "template",
        }
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._body_depth = 0
        self._main_depth = 0
        self._ignored_depth = 0
        self._hidden_depth = 0
        self._saw_main = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag == "body":
            self._body_depth += 1
        elif tag == "main":
            self._main_depth += 1
            self._saw_main = True
        if tag in self._ignored_tags:
            self._ignored_depth += 1
        attributes = {name.casefold(): (value or "") for name, value in attrs}
        style = "".join(attributes.get("style", "").casefold().split())
        if (
            "hidden" in attributes
            or attributes.get("aria-hidden", "").casefold() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        ):
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in self._ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag == "main" and self._main_depth:
            self._main_depth -= 1
        elif tag == "body" and self._body_depth:
            self._body_depth -= 1
        if self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        in_content = self._main_depth > 0 if self._saw_main else self._body_depth > 0
        if in_content and not self._ignored_depth and not self._hidden_depth:
            self.parts.append(data)


def _fallback_extract_html_main_text(html: str) -> str:
    parser = _FallbackVisibleHTMLParser()
    parser.feed(html)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def _close_quietly(connection: Any) -> None:
    with suppress(Exception):
        connection.close()


def _sha256(value: str) -> str:
    from hashlib import sha256

    return sha256(value.encode("utf-8")).hexdigest()


def _bounded_excerpt(value: str) -> str:
    if len(value) <= _MAX_EXCERPT_CHARS:
        return value
    shortened = value[: _MAX_EXCERPT_CHARS - 3].rsplit(" ", 1)[0].strip()
    return f"{shortened}..."


__all__ = [
    "OFFICIAL_GUIDANCE_CANONICAL_PATH",
    "OFFICIAL_GUIDANCE_CANDIDATE_ID",
    "OFFICIAL_GUIDANCE_CONNECTOR_ID",
    "OFFICIAL_GUIDANCE_RECEIPT_MAX_AGE",
    "OFFICIAL_GUIDANCE_SOURCE_URL",
    "OFFICIAL_GUIDANCE_SOURCE_PATH",
    "OfficialGuidanceCandidate",
    "OfficialGuidanceCandidateError",
    "OfficialGuidanceHTTPSReader",
    "OfficialGuidanceMaterial",
    "OfficialGuidanceObservationAdapter",
    "OfficialGuidanceReadError",
    "official_guidance_candidates",
    "official_guidance_receipt_is_fresh",
    "resolve_official_guidance_candidate",
]
