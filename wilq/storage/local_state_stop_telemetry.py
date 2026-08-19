from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from wilq.codex.stop_telemetry import (
    StopTelemetryEvent,
    StopTelemetryHighWatermarkError,
    StopTelemetryReceipt,
    StopTelemetryStorageUnavailable,
)
from wilq.storage.schema_versions import reject_newer_sqlite_schema


class _StopTelemetryStoreMixin:
    path: Path

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def intake_stop_telemetry_event(
        self,
        event: StopTelemetryEvent,
        *,
        cutoff: datetime,
        purge_batch_size: int,
        high_watermark: int,
    ) -> StopTelemetryReceipt:
        blocked_receipt: StopTelemetryReceipt | None = None
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                purged = connection.execute(
                    """
                    DELETE FROM codex_stop_events
                    WHERE id IN (
                      SELECT id FROM codex_stop_events
                      WHERE received_at < ?
                      ORDER BY received_at, id
                      LIMIT ?
                    )
                    """,
                    (cutoff.isoformat(), purge_batch_size),
                ).rowcount
                row = connection.execute(
                    "SELECT COUNT(*) AS count FROM codex_stop_events"
                ).fetchone()
                if row is None:
                    raise RuntimeError("Stop telemetry count is unavailable")
                count = int(row["count"])
                if count >= high_watermark:
                    blocked_receipt = StopTelemetryReceipt(
                        status="high_watermark",
                        cutoff=cutoff,
                        purged_count=purged,
                        count=count,
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO codex_stop_events (
                          id, received_at, event_type, contract_version
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            event.event_id,
                            event.received_at.isoformat(),
                            event.event_type,
                            event.contract_version,
                        ),
                    )
                    row = connection.execute(
                        "SELECT COUNT(*) AS count FROM codex_stop_events"
                    ).fetchone()
                    if row is None:
                        raise RuntimeError("Stop telemetry count is unavailable")
                    count = int(row["count"])
        except (OSError, sqlite3.Error) as exc:
            raise StopTelemetryStorageUnavailable(
                "Stop telemetry storage is unavailable"
            ) from exc
        if blocked_receipt is not None:
            raise StopTelemetryHighWatermarkError(blocked_receipt)
        return StopTelemetryReceipt(
            cutoff=cutoff,
            purged_count=purged,
            count=count,
        )

    def stop_telemetry_health(
        self,
        *,
        cutoff: datetime,
        high_watermark: int,
    ) -> StopTelemetryReceipt:
        count = 0
        try:
            if self.path.exists():
                sqlite_uri = f"{self.path.resolve().as_uri()}?mode=ro"
                connection = sqlite3.connect(sqlite_uri, uri=True)
                try:
                    connection.row_factory = sqlite3.Row
                    reject_newer_sqlite_schema(connection)
                    row = connection.execute(
                        "SELECT COUNT(*) AS count FROM codex_stop_events"
                    ).fetchone()
                finally:
                    connection.close()
                if row is None:
                    raise RuntimeError("Stop telemetry count is unavailable")
                count = int(row["count"])
        except (OSError, sqlite3.Error) as exc:
            raise StopTelemetryStorageUnavailable(
                "Stop telemetry storage is unavailable"
            ) from exc
        receipt = StopTelemetryReceipt(
            status="healthy" if count < high_watermark else "high_watermark",
            cutoff=cutoff,
            purged_count=0,
            count=count,
        )
        if count >= high_watermark:
            raise StopTelemetryHighWatermarkError(receipt)
        return receipt
