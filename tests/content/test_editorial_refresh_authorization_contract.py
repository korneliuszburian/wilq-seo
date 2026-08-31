import json
import sqlite3
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

import wilq.content.workflow.decisions.production as production_module
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.workflow.content_kind_receipt import build_editorial_content_kind_receipt
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    classification_counts,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorizationRequest,
    ContentRefreshPreparationClassificationBinding,
    build_content_refresh_preparation_authorization,
    content_refresh_preparation_authorization_digest,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import inventory_work_item_id

PUBLIC_URL = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/"
WORK_ITEM_ID = inventory_work_item_id(PUBLIC_URL)


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
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert migrated == authorization
    assert columns["content_kind"] == 1
    assert columns["service_card_id"] == 0
    assert "uq_refresh_preparation_authorization_context" in indexes
    assert "content_kind_receipts" in tables


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


def test_editorial_receipt_persists_idempotently_and_gates_exact_authorization(tmp_path) -> None:
    path = tmp_path / "editorial.sqlite3"
    store = ContentWorkflowStore(path)
    run = _stored_editorial_refresh_run()
    store.record_production_classification(run)
    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=run.rows[0].source_packet_row_digest,
        current_work_item_id=WORK_ITEM_ID,
        canonical_path="/analiza-pozwolen-zintegrowanych",
        public_url=PUBLIC_URL,
        classification_blocker_codes=[item.code for item in run.rows[0].blockers],
    )
    receipt = build_editorial_content_kind_receipt(
        work_item_id=WORK_ITEM_ID,
        classification_run_id=classification.classification_run_id,
        classification_run_digest=classification.classification_run_digest,
        decision_set_digest=classification.decision_set_digest,
        source_packet_row_digest=classification.source_packet_row_digest,
        canonical_path=classification.canonical_path,
        public_url=classification.public_url,
        planning_input_digest="d" * 64,
        inventory_binding=ContentKindInventoryBinding(
            work_item_id=WORK_ITEM_ID,
            canonical_path=classification.canonical_path,
            public_url=PUBLIC_URL,
            wordpress_content_type="posts",
            content_kind="editorial",
            inventory_evidence_ids=("ev_current_public", "ev_current_rest"),
            trusted=True,
        ),
    )
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=WORK_ITEM_ID,
        classification=classification,
        planning_input_digest="d" * 64,
        content_kind="editorial",
        service_card_id=None,
        acknowledged_classification_blocker_codes=classification.classification_blocker_codes,
        authorized_by="wilku",
        authorized_at=datetime(2026, 9, 1, tzinfo=UTC),
    )

    created_receipt = store.record_content_kind_receipt(receipt)
    repeated_receipt = store.record_content_kind_receipt(receipt)
    created_authorization = store.record_refresh_preparation_authorization(authorization)
    stale_authorization = build_content_refresh_preparation_authorization(
        work_item_id=WORK_ITEM_ID,
        classification=classification,
        planning_input_digest="e" * 64,
        content_kind="editorial",
        service_card_id=None,
        acknowledged_classification_blocker_codes=classification.classification_blocker_codes,
        authorized_by="wilku",
        authorized_at=datetime(2026, 9, 1, tzinfo=UTC),
    )

    assert created_receipt.status == "created"
    assert repeated_receipt.status == "idempotent"
    assert created_authorization.status == "created"
    with pytest.raises(ValueError, match="persisted content-kind receipt"):
        store.record_refresh_preparation_authorization(stale_authorization)

    with sqlite3.connect(path) as connection:
        payload = receipt.model_dump(mode="json")
        payload["schema_version"] = "wilq_content_kind_receipt_future"
        connection.execute(
            "UPDATE content_kind_receipts SET payload_json = ? WHERE receipt_id = ?",
            (json.dumps(payload), receipt.receipt_id),
        )
    with pytest.raises(ValidationError, match="schema_version"):
        store.load_content_kind_receipt(receipt.receipt_id)


def _stored_editorial_refresh_run():
    run = exact_public_bdo_run()
    payload = run.rows[0].model_dump(mode="python")
    payload.update(
        {
            "canonical_path": "/analiza-pozwolen-zintegrowanych",
            "public_url": PUBLIC_URL,
            "decision": "refresh",
            "current_work_item_id": WORK_ITEM_ID,
            "retained_work_item_id": None,
            "revision_id": None,
            "revision_digest": None,
            "revision_approved": False,
            "revision_complete": False,
            "retained_binding": None,
            "verified_actions": (),
            "verified_drafts": (),
        }
    )
    row = ContentProductionClassificationRow.model_validate(payload)
    return production_module._build_run(
        input_receipt=run.input,
        counts=classification_counts((row, run.rows[1])),
        freshness=run.freshness,
        source_receipts=run.source_receipts,
        judge_receipt=run.judge_receipt,
        rows=(row, run.rows[1]),
        audit=run.audit,
    )
