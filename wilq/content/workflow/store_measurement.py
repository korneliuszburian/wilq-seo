from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from typing import cast

from wilq.content.measurement.learning import ContentLearningProposal
from wilq.content.measurement.outcome import ContentMeasurementOutcomeInterpretation
from wilq.content.measurement.window import ContentMeasurementWindow
from wilq.content.workflow.store_queries import model_json
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping


class MeasurementStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def save_measurement_window(self, window: ContentMeasurementWindow) -> ContentMeasurementWindow:
        redacted = ContentMeasurementWindow.model_validate(
            redact_mapping(window.model_dump(mode="json"))
        )
        payload = model_json(redacted)
        digest = sha256(payload.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_measurement_window_history
                  (work_item_id, window_id, window_digest, stored_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(work_item_id, window_id, window_digest) DO NOTHING
                """,
                (
                    redacted.work_item_id,
                    redacted.id,
                    digest,
                    utc_now().isoformat(),
                    payload,
                ),
            )
            connection.execute(
                """
                INSERT INTO content_measurement_windows (work_item_id, window_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(work_item_id) DO UPDATE SET
                  window_id = excluded.window_id, payload_json = excluded.payload_json
                """,
                (redacted.work_item_id, redacted.id, payload),
            )
        return redacted

    def latest_measurement_window(self, work_item_id: str) -> ContentMeasurementWindow | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_measurement_window_history
                WHERE work_item_id = ? ORDER BY stored_at DESC, rowid DESC LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_measurement_windows
                    WHERE work_item_id = ? LIMIT 1
                    """,
                    (work_item_id,),
                ).fetchone()
        if row is None:
            return None
        return ContentMeasurementWindow.model_validate(json.loads(cast(str, row["payload_json"])))

    def measurement_window(
        self, work_item_id: str, window_id: str
    ) -> ContentMeasurementWindow | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_measurement_window_history
                WHERE work_item_id = ? AND window_id = ?
                ORDER BY stored_at DESC, rowid DESC LIMIT 1
                """,
                (work_item_id, window_id),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_measurement_windows
                    WHERE work_item_id = ? AND window_id = ? LIMIT 1
                    """,
                    (work_item_id, window_id),
                ).fetchone()
        if row is None:
            return None
        return ContentMeasurementWindow.model_validate(json.loads(cast(str, row["payload_json"])))

    def save_measurement_completion(
        self,
        window: ContentMeasurementWindow,
        outcome: ContentMeasurementOutcomeInterpretation,
    ) -> tuple[ContentMeasurementWindow, ContentMeasurementOutcomeInterpretation]:
        if (
            outcome.work_item_id != window.work_item_id
            or outcome.measurement_window_id != window.id
        ):
            raise ValueError("Measurement outcome does not match the persisted window")
        redacted_window = ContentMeasurementWindow.model_validate(
            redact_mapping(window.model_dump(mode="json"))
        )
        redacted_outcome = ContentMeasurementOutcomeInterpretation.model_validate(
            redact_mapping(outcome.model_dump(mode="json"))
        )
        window_payload = model_json(redacted_window)
        outcome_payload = model_json(redacted_outcome)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            window_digest = sha256(window_payload.encode("utf-8")).hexdigest()
            connection.execute(
                """
                INSERT INTO content_measurement_window_history
                  (work_item_id, window_id, window_digest, stored_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(work_item_id, window_id, window_digest) DO NOTHING
                """,
                (
                    redacted_window.work_item_id,
                    redacted_window.id,
                    window_digest,
                    utc_now().isoformat(),
                    window_payload,
                ),
            )
            connection.execute(
                """
                INSERT INTO content_measurement_windows (work_item_id, window_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(work_item_id) DO UPDATE SET
                  window_id = excluded.window_id, payload_json = excluded.payload_json
                """,
                (redacted_window.work_item_id, redacted_window.id, window_payload),
            )
            connection.execute(
                """
                INSERT INTO content_measurement_outcome_history
                  (
                    work_item_id, measurement_window_id, outcome_id,
                    outcome_digest, stored_at, payload_json
                  )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(
                  work_item_id, measurement_window_id, outcome_id, outcome_digest
                ) DO NOTHING
                """,
                (
                    redacted_outcome.work_item_id,
                    redacted_outcome.measurement_window_id,
                    redacted_outcome.id,
                    sha256(outcome_payload.encode("utf-8")).hexdigest(),
                    utc_now().isoformat(),
                    outcome_payload,
                ),
            )
            connection.execute(
                """
                INSERT INTO content_measurement_outcomes
                  (work_item_id, measurement_window_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(work_item_id) DO UPDATE SET
                  measurement_window_id = excluded.measurement_window_id,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted_outcome.work_item_id,
                    redacted_outcome.measurement_window_id,
                    outcome_payload,
                ),
            )
        return redacted_window, redacted_outcome

    def latest_measurement_outcome(
        self,
        work_item_id: str,
    ) -> ContentMeasurementOutcomeInterpretation | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_measurement_outcome_history
                WHERE work_item_id = ? ORDER BY stored_at DESC, rowid DESC LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_measurement_outcomes
                    WHERE work_item_id = ? LIMIT 1
                    """,
                    (work_item_id,),
                ).fetchone()
        if row is None:
            return None
        return ContentMeasurementOutcomeInterpretation.model_validate(
            json.loads(cast(str, row["payload_json"]))
        )

    def measurement_outcome(
        self, work_item_id: str, measurement_window_id: str
    ) -> ContentMeasurementOutcomeInterpretation | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_measurement_outcome_history
                WHERE work_item_id = ? AND measurement_window_id = ?
                ORDER BY stored_at DESC, rowid DESC LIMIT 1
                """,
                (work_item_id, measurement_window_id),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_measurement_outcomes
                    WHERE work_item_id = ? AND measurement_window_id = ? LIMIT 1
                    """,
                    (work_item_id, measurement_window_id),
                ).fetchone()
        if row is None:
            return None
        return ContentMeasurementOutcomeInterpretation.model_validate(
            json.loads(cast(str, row["payload_json"]))
        )

    def save_learning_proposal(self, proposal: ContentLearningProposal) -> ContentLearningProposal:
        redacted = ContentLearningProposal.model_validate(
            redact_mapping(proposal.model_dump(mode="json"))
        )
        payload = model_json(redacted)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_learning_proposal_history
                  (work_item_id, measurement_window_id, proposal_id, stored_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(work_item_id, measurement_window_id, proposal_id) DO NOTHING
                """,
                (
                    redacted.work_item_id,
                    redacted.measurement_window_id,
                    redacted.id,
                    utc_now().isoformat(),
                    payload,
                ),
            )
            connection.execute(
                """
                INSERT INTO content_learning_proposals (work_item_id, proposal_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(work_item_id) DO UPDATE SET
                  proposal_id = excluded.proposal_id, payload_json = excluded.payload_json
                """,
                (redacted.work_item_id, redacted.id, payload),
            )
        return redacted

    def latest_learning_proposal(self, work_item_id: str) -> ContentLearningProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_learning_proposal_history
                WHERE work_item_id = ? ORDER BY stored_at DESC, rowid DESC LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_learning_proposals
                    WHERE work_item_id = ? LIMIT 1
                    """,
                    (work_item_id,),
                ).fetchone()
        if row is None:
            return None
        return ContentLearningProposal.model_validate(json.loads(cast(str, row["payload_json"])))

    def learning_proposal(
        self, work_item_id: str, measurement_window_id: str
    ) -> ContentLearningProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_learning_proposal_history
                WHERE work_item_id = ? AND measurement_window_id = ?
                ORDER BY stored_at DESC, rowid DESC LIMIT 1
                """,
                (work_item_id, measurement_window_id),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_learning_proposals
                    WHERE work_item_id = ? AND measurement_window_id = ? LIMIT 1
                    """,
                    (work_item_id, measurement_window_id),
                ).fetchone()
        if row is None:
            return None
        return ContentLearningProposal.model_validate(json.loads(cast(str, row["payload_json"])))
