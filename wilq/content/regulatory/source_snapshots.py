from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.regulatory.policy import (
    ContentRegulatorySourceCandidate,
    regulatory_content_profile,
    regulatory_source_candidates,
)
from wilq.storage.local_state import state_db_path
from wilq.storage.private_paths import prepare_private_store_path

# Official regulatory instructions are commonly PDFs. We persist only their
# digest and metadata, never the body, but must still read a bounded complete
# response to bind a review to its exact source snapshot.
_MAX_SNAPSHOT_BYTES = 12 * 1024 * 1024
_SOURCE_READ_TIMEOUT_SECONDS = 15
SourceReader = Callable[[str], tuple[bytes, str]]


class ContentRegulatorySourceSnapshot(BaseModel):
    """Metadata for one fetched official source, without persisting its body."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: str = Field(min_length=1)
    byte_length: int = Field(ge=1, le=_MAX_SNAPSHOT_BYTES)
    observed_at: datetime

    @model_validator(mode="after")
    def require_https_source(self) -> ContentRegulatorySourceSnapshot:
        if urlsplit(self.source_url).scheme != "https":
            raise ValueError("Regulatory source snapshots require an HTTPS URL.")
        return self

    @property
    def observed_on(self) -> str:
        return self.observed_at.date().isoformat()


class ContentRegulatorySourceSnapshotReadResponse(BaseModel):
    """Typed outcome of the allowlisted official-source read."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["captured", "blocked"]
    snapshot: ContentRegulatorySourceSnapshot | None = None
    reason: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_snapshot_only_when_captured(self) -> ContentRegulatorySourceSnapshotReadResponse:
        if self.status == "captured" and self.snapshot is None:
            raise ValueError("Captured regulatory source read requires a snapshot.")
        if self.status == "blocked" and self.snapshot is not None:
            raise ValueError("Blocked regulatory source read cannot expose a snapshot.")
        return self


class RegulatorySourceSnapshotStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def capture(
        self,
        candidate_id: str,
        *,
        reader: SourceReader | None = None,
        candidates: tuple[ContentRegulatorySourceCandidate, ...] | None = None,
        now: datetime | None = None,
    ) -> ContentRegulatorySourceSnapshot:
        candidate = _reviewable_candidate(
            candidate_id,
            candidates if candidates is not None else regulatory_source_candidates(),
        )
        body, content_type = (reader or _read_official_source)(candidate.source_url)
        if not body:
            raise ValueError("Official regulatory source returned an empty response.")
        if len(body) > _MAX_SNAPSHOT_BYTES:
            raise ValueError("Official regulatory source exceeds the safe snapshot size.")
        observed_at = now or datetime.now(UTC)
        snapshot = ContentRegulatorySourceSnapshot(
            snapshot_id=_snapshot_id(candidate, observed_at),
            candidate_id=candidate.candidate_id,
            profile_id=candidate.profile_id,
            profile_version=candidate.profile_version,
            source_url=candidate.source_url,
            content_digest=sha256(body).hexdigest(),
            content_type=content_type,
            byte_length=len(body),
            observed_at=observed_at,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_regulatory_source_snapshots (
                  snapshot_id, candidate_id, content_digest, observed_at, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_id) DO NOTHING
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.candidate_id,
                    snapshot.content_digest,
                    snapshot.observed_at.isoformat(),
                    json.dumps(
                        snapshot.model_dump(mode="json"),
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ),
            )
        return snapshot

    def get(
        self,
        snapshot_id: str,
    ) -> ContentRegulatorySourceSnapshot | None:
        if not self.path.exists():
            return None
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            with connection:
                if not _table_exists(connection, "content_regulatory_source_snapshots"):
                    return None
                row = connection.execute(
                    "SELECT payload_json FROM content_regulatory_source_snapshots "
                    "WHERE snapshot_id = ?",
                    (snapshot_id,),
                ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return ContentRegulatorySourceSnapshot.model_validate(json.loads(row["payload_json"]))

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(self.path, normalize_existing_parent=False)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_regulatory_source_snapshots (
              snapshot_id TEXT PRIMARY KEY,
              candidate_id TEXT NOT NULL,
              content_digest TEXT NOT NULL,
              observed_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        return connection

    def _read_connection(self) -> sqlite3.Connection | None:
        if not self.path.exists():
            return None
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection


def regulatory_source_snapshot_store() -> RegulatorySourceSnapshotStore:
    return RegulatorySourceSnapshotStore(state_db_path())


def _reviewable_candidate(
    candidate_id: str,
    candidates: tuple[ContentRegulatorySourceCandidate, ...],
) -> ContentRegulatorySourceCandidate:
    candidate = next((item for item in candidates if item.candidate_id == candidate_id), None)
    if candidate is None:
        raise ValueError("Regulatory source candidate is no longer available.")
    profile = regulatory_content_profile(service_card_id=candidate.service_card_ids[0])
    if profile is None or profile.id != candidate.profile_id:
        raise ValueError("Regulatory source candidate has no matching profile.")
    hostname = urlsplit(candidate.source_url).hostname
    if (
        urlsplit(candidate.source_url).scheme != "https"
        or hostname not in profile.official_source_hosts
    ):
        raise ValueError("Regulatory source candidate is not an allowlisted official HTTPS source.")
    return candidate


def _read_official_source(source_url: str) -> tuple[bytes, str]:
    request = Request(
        source_url,
        headers={"User-Agent": "WILQ-regulatory-source-review/1.0"},
    )
    with urlopen(request, timeout=_SOURCE_READ_TIMEOUT_SECONDS) as response:  # noqa: S310
        body = response.read(_MAX_SNAPSHOT_BYTES + 1)
        content_type = response.headers.get_content_type() or "application/octet-stream"
    return body, content_type


def _snapshot_id(
    candidate: ContentRegulatorySourceCandidate,
    observed_at: datetime,
) -> str:
    payload = f"{candidate.candidate_id}:{observed_at.isoformat()}"
    return f"regulatory_snapshot_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )
