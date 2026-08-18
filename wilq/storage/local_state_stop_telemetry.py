from __future__ import annotations

import sqlite3

from wilq.codex.stop_telemetry import StopTelemetryEvent


class _StopTelemetryStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def append_stop_telemetry_event(
        self,
        event: StopTelemetryEvent,
    ) -> StopTelemetryEvent:
        with self._connect() as connection:
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
        return event
