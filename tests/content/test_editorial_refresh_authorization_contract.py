import sqlite3
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorizationRequest,
    ContentRefreshPreparationClassificationBinding,
    build_content_refresh_preparation_authorization,
    content_refresh_preparation_authorization_digest,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def _classification() -> ContentRefreshPreparationClassificationBinding:
    return ContentRefreshPreparationClassificationBinding(
        classification_run_id="classification_editorial",
        classification_run_digest="a" * 64,
        decision_set_digest="b" * 64,
        source_packet_row_digest="c" * 64,
        current_work_item_id="content_work_item_editorial",
        canonical_path="/artykul",
        public_url="https://www.ekologus.pl/artykul/",
    )


def test_editorial_refresh_authorization_has_no_service_identity() -> None:
    authorization = build_content_refresh_preparation_authorization(
        work_item_id="content_work_item_editorial",
        classification=_classification(),
        planning_input_digest="d" * 64,
        content_kind="editorial",
        service_card_id=None,
        acknowledged_classification_blocker_codes=[],
        authorized_by="wilku",
        authorized_at=datetime(2026, 8, 31, tzinfo=UTC),
    )

    assert authorization.schema_version == "wilq_content_refresh_preparation_authorization_v2"
    assert authorization.content_kind == "editorial"
    assert authorization.service_card_id is None
    assert authorization.binding.content_kind == "editorial"
    assert authorization.binding.service_card_id is None


def test_refresh_request_rejects_content_kind_service_mismatch() -> None:
    payload = {
        "expected_production_classification_run_digest": "a" * 64,
        "expected_production_classification_decision_set_digest": "b" * 64,
        "expected_production_classification_source_packet_row_digest": "c" * 64,
        "expected_planning_input_digest": "d" * 64,
        "content_kind": "editorial",
        "service_card_id": "fake_service",
        "authorized_by": "wilku",
        "acknowledged_classification_blocker_codes": [],
    }

    with pytest.raises(ValidationError, match="must match its content kind"):
        ContentRefreshPreparationAuthorizationRequest.model_validate(payload)


def test_service_authorization_digest_remains_v1_compatible() -> None:
    common = dict(
        work_item_id="content_work_item_service",
        classification_run_id="classification_service",
        classification_run_digest="a" * 64,
        decision_set_digest="b" * 64,
        source_packet_row_digest="c" * 64,
        canonical_path="/usluga",
        public_url="https://www.ekologus.pl/usluga/",
        planning_input_digest="d" * 64,
        service_card_id="service_card",
        acknowledged_classification_blocker_codes=[],
        authorized_by="wilku",
    )

    assert content_refresh_preparation_authorization_digest(**common) == (
        content_refresh_preparation_authorization_digest(content_kind="service", **common)
    )


def test_v1_store_migrates_without_changing_existing_authorization(tmp_path) -> None:
    path = tmp_path / "refresh-v1.sqlite3"
    authorization = build_content_refresh_preparation_authorization(
        work_item_id="content_work_item_service",
        classification=ContentRefreshPreparationClassificationBinding(
            classification_run_id="classification_service",
            classification_run_digest="a" * 64,
            decision_set_digest="b" * 64,
            source_packet_row_digest="c" * 64,
            current_work_item_id="content_work_item_service",
            canonical_path="/usluga",
            public_url="https://www.ekologus.pl/usluga/",
        ),
        planning_input_digest="d" * 64,
        service_card_id="service_card",
        acknowledged_classification_blocker_codes=[],
        authorized_by="wilku",
        authorized_at=datetime(2026, 8, 31, tzinfo=UTC),
    )
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE content_refresh_preparation_authorizations (
              authorization_id TEXT PRIMARY KEY,
              authorization_digest TEXT NOT NULL UNIQUE,
              work_item_id TEXT NOT NULL,
              classification_run_id TEXT NOT NULL,
              classification_run_digest TEXT NOT NULL,
              decision_set_digest TEXT NOT NULL,
              source_packet_row_digest TEXT NOT NULL,
              canonical_path TEXT NOT NULL,
              public_url TEXT NOT NULL,
              planning_input_digest TEXT NOT NULL,
              service_card_id TEXT NOT NULL,
              authorized_by TEXT NOT NULL,
              authorized_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              UNIQUE (
                work_item_id, classification_run_digest, decision_set_digest,
                source_packet_row_digest, planning_input_digest, service_card_id
              )
            );
            """
        )
        connection.execute(
            """
            INSERT INTO content_refresh_preparation_authorizations VALUES (
              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                authorization.authorization_id,
                authorization.authorization_digest,
                authorization.work_item_id,
                authorization.classification_run_id,
                authorization.classification_run_digest,
                authorization.decision_set_digest,
                authorization.source_packet_row_digest,
                authorization.canonical_path,
                authorization.public_url,
                authorization.planning_input_digest,
                authorization.service_card_id,
                authorization.authorized_by,
                authorization.authorized_at.isoformat(),
                authorization.model_dump_json(),
            ),
        )

    migrated = ContentWorkflowStore(path).load_refresh_preparation_authorization(
        authorization.authorization_id
    )
    with sqlite3.connect(path) as connection:
        columns = {
            row[1]: row[3]
            for row in connection.execute(
                "PRAGMA table_info(content_refresh_preparation_authorizations)"
            )
        }
        indexes = {
            row[1]
            for row in connection.execute(
                "PRAGMA index_list(content_refresh_preparation_authorizations)"
            )
        }

    assert migrated == authorization
    assert columns["content_kind"] == 1
    assert columns["service_card_id"] == 0
    assert "uq_refresh_preparation_authorization_context" in indexes


def test_store_rejects_editorial_authorization_without_content_kind_receipt(tmp_path) -> None:
    authorization = build_content_refresh_preparation_authorization(
        work_item_id="content_work_item_editorial",
        classification=_classification(),
        planning_input_digest="d" * 64,
        content_kind="editorial",
        service_card_id=None,
        acknowledged_classification_blocker_codes=[],
        authorized_by="wilku",
        authorized_at=datetime(2026, 8, 31, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="persisted content-kind receipt"):
        ContentWorkflowStore(
            tmp_path / "editorial.sqlite3"
        ).record_refresh_preparation_authorization(authorization)
