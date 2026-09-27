"""Persistence for one idempotent current-acceptance attempt and sealed wave."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Literal, cast

from wilq.content.workflow.current_acceptance_contracts import (
    CurrentAcceptanceAttempt,
    CurrentAcceptanceBlocked,
    CurrentAcceptanceRow,
    CurrentAcceptanceWave,
    current_acceptance_scope_coverage_digest,
)
from wilq.content.workflow.per_url_decision_authority import (
    ContentPerUrlDecisionObservation,
)
from wilq.storage.model_json import model_json


def ensure_current_acceptance_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS content_current_acceptance_attempts (
            request_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL UNIQUE,
            input_digest TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'complete', 'failed')),
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS content_current_acceptance_waves (
            wave_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL UNIQUE,
            wave_digest TEXT NOT NULL UNIQUE,
            source_snapshot_digest TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS content_current_acceptance_wave_rows (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            wave_id TEXT NOT NULL,
            canonical_path TEXT NOT NULL,
            current_work_item_id TEXT,
            decision TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS content_current_acceptance_rows_by_scope
        ON content_current_acceptance_wave_rows(canonical_path, current_work_item_id, sequence);

        CREATE TRIGGER IF NOT EXISTS content_current_acceptance_waves_no_update
        BEFORE UPDATE ON content_current_acceptance_waves
        BEGIN SELECT RAISE(ABORT, 'current acceptance waves are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_current_acceptance_waves_no_delete
        BEFORE DELETE ON content_current_acceptance_waves
        BEGIN SELECT RAISE(ABORT, 'current acceptance waves are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_current_acceptance_wave_rows_no_update
        BEFORE UPDATE ON content_current_acceptance_wave_rows
        BEGIN SELECT RAISE(ABORT, 'current acceptance wave rows are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_current_acceptance_wave_rows_no_delete
        BEFORE DELETE ON content_current_acceptance_wave_rows
        BEGIN SELECT RAISE(ABORT, 'current acceptance wave rows are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_current_acceptance_attempts_no_delete
        BEFORE DELETE ON content_current_acceptance_attempts
        BEGIN SELECT RAISE(ABORT, 'current acceptance attempts are retained'); END;

        CREATE TRIGGER IF NOT EXISTS content_current_acceptance_attempts_transition
        BEFORE UPDATE ON content_current_acceptance_attempts
        WHEN OLD.request_id != NEW.request_id
          OR OLD.run_id != NEW.run_id
          OR OLD.input_digest != NEW.input_digest
          OR NOT (
            (OLD.status = 'queued' AND NEW.status IN ('running', 'failed'))
            OR (OLD.status = 'running' AND NEW.status IN ('complete', 'failed'))
          )
        BEGIN SELECT RAISE(ABORT, 'invalid current acceptance attempt transition'); END;
        """
    )


def _live_wordpress_generation() -> tuple[str, ...]:
    """Return the currently persisted latest completed WordPress vendor-read evidence."""

    from wilq.content.workflow.workspace.catalog import latest_wordpress_vendor_read_evidence_ids

    return tuple(sorted(set(latest_wordpress_vendor_read_evidence_ids())))


class CurrentAcceptanceStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def create_current_acceptance_attempt(
        self,
        attempt: CurrentAcceptanceAttempt,
    ) -> tuple[Literal["created", "idempotent", "conflict"], CurrentAcceptanceAttempt]:
        accepted = CurrentAcceptanceAttempt.model_validate_json(
            attempt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM content_current_acceptance_attempts "
                "WHERE request_id = ? OR run_id = ? LIMIT 1",
                (accepted.request_id, accepted.run_id),
            ).fetchone()
            if row is not None:
                stored = _attempt_from_row(row)
                if stored.input_digest != accepted.input_digest:
                    return "conflict", stored
                return "idempotent", stored
            connection.execute(
                "INSERT INTO content_current_acceptance_attempts "
                "(request_id, run_id, input_digest, status, updated_at, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    accepted.request_id,
                    accepted.run_id,
                    accepted.input_digest,
                    accepted.status,
                    accepted.updated_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def load_current_acceptance_attempt(
        self,
        run_id: str,
    ) -> CurrentAcceptanceAttempt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_current_acceptance_attempts WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return None if row is None else _attempt_from_row(row)

    def load_current_acceptance_attempt_by_request_id(
        self,
        request_id: str,
    ) -> CurrentAcceptanceAttempt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_current_acceptance_attempts WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return None if row is None else _attempt_from_row(row)

    def load_current_acceptance_wave(self, wave_id: str) -> CurrentAcceptanceWave | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_acceptance_waves WHERE wave_id = ?",
                (wave_id,),
            ).fetchone()
        return (
            None
            if row is None
            else CurrentAcceptanceWave.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def load_latest_current_acceptance_row_for_path(
        self,
        *,
        canonical_path: str,
    ) -> CurrentAcceptanceRow | None:
        """Return the newest sealed wave row for one canonical path.

        Supersession is intentionally path-scoped: an excluded or rebound row for
        the same path must override a stale work-item identity observation.
        """
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_acceptance_wave_rows "
                "WHERE canonical_path = ? "
                "ORDER BY sequence DESC LIMIT 1",
                (canonical_path,),
            ).fetchone()
        return (
            None
            if row is None
            else CurrentAcceptanceRow.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def load_latest_current_acceptance_row_for_work_item(
        self,
        current_work_item_id: str,
    ) -> CurrentAcceptanceRow | None:
        """Return the newest sealed wave row bound to one work item."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_acceptance_wave_rows "
                "WHERE current_work_item_id = ? "
                "ORDER BY sequence DESC LIMIT 1",
                (current_work_item_id,),
            ).fetchone()
        return (
            None
            if row is None
            else CurrentAcceptanceRow.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def mark_current_acceptance_running(
        self,
        run_id: str,
    ) -> CurrentAcceptanceAttempt | None:
        """Claim the queued-to-running transition exclusively.

        Returns the running attempt only to the caller that performed the
        transition. A missing, already running, completed or failed attempt
        returns None so a duplicate worker cannot read pages.
        """
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM content_current_acceptance_attempts WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            current = _attempt_from_row(row)
            if current.status != "queued":
                return None
            updated = current.model_copy(
                update={"status": "running", "updated_at": datetime.now(UTC)}
            )
            connection.execute(
                "UPDATE content_current_acceptance_attempts "
                "SET status = ?, updated_at = ?, payload_json = ? WHERE run_id = ?",
                (updated.status, updated.updated_at.isoformat(), model_json(updated), run_id),
            )
        return updated

    def fail_current_acceptance_attempt(
        self,
        run_id: str,
        code: str,
        owner: str,
        safe_next_step: str,
    ) -> CurrentAcceptanceAttempt | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM content_current_acceptance_attempts WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            current = _attempt_from_row(row)
            if current.status not in {"queued", "running"}:
                return current
            updated = current.model_copy(
                update={
                    "status": "failed",
                    "updated_at": datetime.now(UTC),
                    "blocker_code": code,
                    "blocker_owner": owner,
                    "safe_next_step": safe_next_step,
                }
            )
            connection.execute(
                "UPDATE content_current_acceptance_attempts "
                "SET status = ?, updated_at = ?, payload_json = ? WHERE run_id = ?",
                (updated.status, updated.updated_at.isoformat(), model_json(updated), run_id),
            )
        return updated

    def record_current_acceptance_wave(
        self,
        wave: CurrentAcceptanceWave,
        observations: tuple[ContentPerUrlDecisionObservation, ...],
    ) -> Literal["created", "idempotent"]:
        accepted_wave = CurrentAcceptanceWave.model_validate_json(
            wave.model_dump_json(), strict=True
        )
        accepted_observations = tuple(
            ContentPerUrlDecisionObservation.model_validate_json(
                item.model_dump_json(), strict=True
            )
            for item in observations
        )
        if len({item.observation_id for item in accepted_observations}) != len(
            accepted_observations
        ):
            raise ValueError("Current acceptance observations must have unique IDs.")
        referenced = {row.observation_id for row in accepted_wave.rows if row.observation_id}
        if not referenced.issubset({item.observation_id for item in accepted_observations}):
            raise ValueError("Current acceptance wave references an unpersisted observation.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM content_current_acceptance_attempts WHERE run_id = ?",
                (accepted_wave.run_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Current acceptance attempt is missing.")
            attempt = _attempt_from_row(row)
            if attempt.status == "complete":
                return _completed_wave_matches(connection, attempt, accepted_wave)
            if (
                attempt.status != "running"
                or attempt.source_snapshot_digest != accepted_wave.source_snapshot_digest
            ):
                raise ValueError("Current acceptance wave is outside its running source snapshot.")
            if _live_wordpress_generation() != attempt.wordpress_evidence_ids:
                raise CurrentAcceptanceBlocked(
                    "current_acceptance_source_superseded",
                    "WILQ WordPress connector",
                    "Odśwież bieżący odczyt WordPress i uruchom nową kwalifikację.",
                )
            if (
                len(accepted_wave.rows) != attempt.scope_row_count
                or current_acceptance_scope_coverage_digest(
                    (row.canonical_path, row.scope_disposition) for row in accepted_wave.rows
                )
                != attempt.scope_row_digest
            ):
                raise CurrentAcceptanceBlocked(
                    "current_acceptance_scope_coverage_mismatch",
                    "WILQ content workflow",
                    "Odbuduj wave na dokładnie jednym przypiętym zakresie inventory.",
                )
            _record_observations(connection, accepted_observations)
            _insert_wave(connection, accepted_wave)
            _insert_wave_rows(connection, accepted_wave.wave_id, accepted_wave.rows)
            _complete_attempt(connection, attempt, accepted_wave)
        return "created"


def _attempt_from_row(row: sqlite3.Row) -> CurrentAcceptanceAttempt:
    attempt = CurrentAcceptanceAttempt.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )
    if (
        attempt.request_id != row["request_id"]
        or attempt.run_id != row["run_id"]
        or attempt.input_digest != row["input_digest"]
        or attempt.status != row["status"]
        or attempt.updated_at.isoformat() != row["updated_at"]
    ):
        raise ValueError("Current acceptance attempt storage columns do not match payload.")
    return attempt


def _completed_wave_matches(
    connection: sqlite3.Connection,
    attempt: CurrentAcceptanceAttempt,
    wave: CurrentAcceptanceWave,
) -> Literal["idempotent"]:
    row = connection.execute(
        "SELECT payload_json FROM content_current_acceptance_waves WHERE wave_id = ?",
        (attempt.wave_id or "",),
    ).fetchone()
    stored = (
        None
        if row is None
        else CurrentAcceptanceWave.model_validate_json(cast(str, row["payload_json"]), strict=True)
    )
    if stored is None or stored.wave_digest != wave.wave_digest:
        raise ValueError("Completed current acceptance attempt has a wave conflict.")
    return "idempotent"


def _record_observations(
    connection: sqlite3.Connection,
    observations: tuple[ContentPerUrlDecisionObservation, ...],
) -> None:
    for observation in observations:
        row = connection.execute(
            "SELECT payload_json FROM content_per_url_decision_observations "
            "WHERE observation_id = ?",
            (observation.observation_id,),
        ).fetchone()
        if row is not None:
            stored = ContentPerUrlDecisionObservation.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
            if stored != observation:
                raise ValueError("Current acceptance observation ID conflicts with storage.")
            continue
        connection.execute(
            "INSERT INTO content_per_url_decision_observations "
            "(observation_id, canonical_path, current_work_item_id, semantic_row_digest, "
            "evidence_digest, observed_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                observation.observation_id,
                observation.policy_facts.canonical_path,
                observation.policy_facts.current_work_item_id,
                observation.semantic_row_digest,
                observation.evidence_digest,
                observation.observed_at.isoformat(),
                model_json(observation),
            ),
        )


def _insert_wave(connection: sqlite3.Connection, wave: CurrentAcceptanceWave) -> None:
    connection.execute(
        "INSERT INTO content_current_acceptance_waves "
        "(wave_id, run_id, wave_digest, source_snapshot_digest, payload_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            wave.wave_id,
            wave.run_id,
            wave.wave_digest,
            wave.source_snapshot_digest,
            model_json(wave),
        ),
    )


def _insert_wave_rows(
    connection: sqlite3.Connection,
    wave_id: str,
    rows: tuple[CurrentAcceptanceRow, ...],
) -> None:
    connection.executemany(
        "INSERT INTO content_current_acceptance_wave_rows "
        "(wave_id, canonical_path, current_work_item_id, decision, payload_json) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (
                wave_id,
                row.canonical_path,
                row.current_work_item_id,
                row.decision,
                model_json(row),
            )
            for row in rows
        ],
    )


def _complete_attempt(
    connection: sqlite3.Connection,
    attempt: CurrentAcceptanceAttempt,
    wave: CurrentAcceptanceWave,
) -> None:
    updated = attempt.model_copy(
        update={
            "status": "complete",
            "updated_at": datetime.now(UTC),
            "wave_id": wave.wave_id,
            "wave_digest": wave.wave_digest,
        }
    )
    connection.execute(
        "UPDATE content_current_acceptance_attempts "
        "SET status = ?, updated_at = ?, payload_json = ? WHERE run_id = ?",
        (updated.status, updated.updated_at.isoformat(), model_json(updated), attempt.run_id),
    )


__all__ = ["CurrentAcceptanceStoreMixin", "ensure_current_acceptance_schema"]
