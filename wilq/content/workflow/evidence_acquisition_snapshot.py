"""Exact, redacted current-page receipts for evidence acquisition."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Protocol

from wilq.content.canonical.urls import (
    content_is_safe_public_url,
    content_normalized_path,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.evidence_acquisition_contracts import (
    _MAX_EXCERPT_CHARS,
    _WORDPRESS_CONNECTOR_ID,
    EvidenceObservationReceipt,
    _sanitized_text,
    _snapshot_digest_payload,
)

CURRENT_PAGE_RECEIPT_MAX_AGE = timedelta(hours=24)


class _MaterialRead(Protocol):
    @property
    def url(self) -> str: ...

    @property
    def content_text(self) -> str: ...

    @property
    def extraction_region(self) -> str: ...


MaterialReader = Callable[[str], _MaterialRead]
Clock = Callable[[], datetime]


class CurrentPageSnapshotReadError(RuntimeError):
    """A current-page read could not produce an exact, sanitized receipt."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

class WordPressCurrentPageSnapshotAdapter:
    """Read one exact public page and retain only a redacted receipt."""

    def __init__(
        self,
        *,
        material_reader: MaterialReader | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._material_reader = material_reader or _read_wordpress_material
        self._clock = clock or (lambda: datetime.now(UTC))

    def read(
        self,
        *,
        source_url: str,
        canonical_path: str,
    ) -> EvidenceObservationReceipt:
        _validate_requested_identity(source_url, canonical_path)
        try:
            material = self._material_reader(source_url)
        except CurrentPageSnapshotReadError:
            raise
        except Exception as exc:
            raise CurrentPageSnapshotReadError(
                "current_page_snapshot_unavailable",
                "WordPress current-page read did not complete safely.",
            ) from exc
        _validate_material_identity(material, source_url, canonical_path)
        safe_body = _sanitized_text(material.content_text)
        if not safe_body:
            raise CurrentPageSnapshotReadError(
                "current_page_snapshot_unavailable",
                "WordPress current-page read returned no readable body.",
            )
        read_at = self._read_time()
        body_digest = sha256(safe_body.encode("utf-8")).hexdigest()
        excerpt = _bounded_excerpt(safe_body)
        excerpt_digest = sha256(excerpt.encode("utf-8")).hexdigest()
        observed_url = material.url
        snapshot_digest = canonical_json_digest(
            _snapshot_digest_payload(
                source_url=observed_url,
                canonical_path=canonical_path,
                body_digest=body_digest,
                excerpt_digest=excerpt_digest,
                extraction_region=material.extraction_region,
                read_at=read_at,
            )
        )
        evidence_id = f"ev_content_current_page_{snapshot_digest[:24]}"
        try:
            return EvidenceObservationReceipt(
                observation_id=f"content_current_page_observation_{snapshot_digest[:24]}",
                source_url=observed_url,
                canonical_path=canonical_path,
                source_snapshot_digest=snapshot_digest,
                body_digest=body_digest,
                excerpt_digest=excerpt_digest,
                collected_at=read_at,
                read_at=read_at,
                freshness_date=read_at.date().isoformat(),
                evidence_ids=(evidence_id,),
                source_connectors=(_WORDPRESS_CONNECTOR_ID,),
                extraction_region=material.extraction_region,
                sanitized_excerpt=excerpt,
            )
        except ValueError as exc:
            raise CurrentPageSnapshotReadError(
                "current_page_snapshot_unavailable",
                "WordPress current-page receipt failed its safety contract.",
            ) from exc

    def _read_time(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise CurrentPageSnapshotReadError(
                "current_page_snapshot_unavailable",
                "Current-page read did not provide an aware read timestamp.",
            )
        return value.astimezone(UTC)


def _read_wordpress_material(url: str) -> _MaterialRead:
    from wilq.connectors.wordpress.client import read_wordpress_content_material

    return read_wordpress_content_material(url, connector_id=_WORDPRESS_CONNECTOR_ID)


def _validate_requested_identity(source_url: str, canonical_path: str) -> None:
    if (
        not content_is_safe_public_url(source_url)
        or content_normalized_path(source_url) != canonical_path
    ):
        raise CurrentPageSnapshotReadError(
            "current_page_snapshot_lineage_mismatch",
            "Current-page read identity is not an exact safe URL/path pair.",
        )


def _validate_material_identity(
    material: _MaterialRead,
    source_url: str,
    canonical_path: str,
) -> None:
    if (
        not content_is_safe_public_url(material.url)
        or material.url != source_url
        or content_normalized_path(material.url) != canonical_path
    ):
        raise CurrentPageSnapshotReadError(
            "current_page_snapshot_lineage_mismatch",
            "Current-page material does not match the exact requested URL/path.",
        )
    if not isinstance(material.extraction_region, str) or not material.extraction_region.strip():
        raise CurrentPageSnapshotReadError(
            "current_page_snapshot_unavailable",
            "Current-page material has no extraction region.",
        )

def current_page_receipt_is_fresh(
    receipt: EvidenceObservationReceipt,
    *,
    now: datetime,
) -> bool:
    """Assess receipt freshness at consumption time, without mutating it."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Current-page freshness assessment requires an aware server time.")
    age = now.astimezone(UTC) - receipt.read_at
    return timedelta(0) <= age <= CURRENT_PAGE_RECEIPT_MAX_AGE


def _bounded_excerpt(value: str) -> str:
    if len(value) <= _MAX_EXCERPT_CHARS:
        return value
    shortened = value[: _MAX_EXCERPT_CHARS - 3].rsplit(" ", 1)[0].strip()
    return f"{shortened}..."


__all__ = [
    "CurrentPageSnapshotReadError",
    "CURRENT_PAGE_RECEIPT_MAX_AGE",
    "EvidenceObservationReceipt",
    "WordPressCurrentPageSnapshotAdapter",
    "current_page_receipt_is_fresh",
]
