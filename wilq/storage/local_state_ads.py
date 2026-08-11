from __future__ import annotations

import sqlite3
from typing import cast

from wilq.schemas import (
    AdsStrategyReviewRecord,
    AdsTargetGuardrailConfirmation,
)
from wilq.storage.local_state_runs import _model_from_json, _model_json


class _AdsReviewStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def save_ads_target_guardrail_confirmation(
        self,
        confirmation: AdsTargetGuardrailConfirmation,
    ) -> AdsTargetGuardrailConfirmation:
        payload_json = _model_json(confirmation)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ads_target_guardrail_confirmations (
                  id, connector_id, created_at, payload_json
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  connector_id = excluded.connector_id,
                  created_at = excluded.created_at,
                  payload_json = excluded.payload_json
                """,
                (
                    confirmation.id,
                    confirmation.connector_id,
                    confirmation.created_at.isoformat(),
                    payload_json,
                ),
            )
        return confirmation

    def latest_ads_target_guardrail_confirmation(
        self,
    ) -> AdsTargetGuardrailConfirmation | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM ads_target_guardrail_confirmations
                WHERE connector_id = 'google_ads'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(
            AdsTargetGuardrailConfirmation,
            cast(str, row["payload_json"]),
        )

    def save_ads_strategy_review(
        self,
        review: AdsStrategyReviewRecord,
    ) -> AdsStrategyReviewRecord:
        payload_json = _model_json(review)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ads_strategy_reviews (
                  id, connector_id, created_at, payload_json
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  connector_id = excluded.connector_id,
                  created_at = excluded.created_at,
                  payload_json = excluded.payload_json
                """,
                (
                    review.id,
                    review.connector_id,
                    review.created_at.isoformat(),
                    payload_json,
                ),
            )
        return review

    def latest_ads_strategy_review(self) -> AdsStrategyReviewRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM ads_strategy_reviews
                WHERE connector_id = 'google_ads'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return _model_from_json(AdsStrategyReviewRecord, cast(str, row["payload_json"]))
