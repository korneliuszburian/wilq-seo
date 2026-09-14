from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

import wilq.content.workflow.decisions.production as production_module
from apps.api.wilq_api.main import app
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    ContentDeliveryIdentityCommand,
    inventory_evidence_digest,
    reconcile_content_delivery_identity,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def _command(
    *,
    retained: bool,
    run: production_module.ContentProductionClassificationRun | None = None,
    **updates: object,
) -> ContentDeliveryIdentityCommand:
    run = exact_public_bdo_run() if run is None else run
    row = run.rows[0] if retained else run.rows[1]
    evidence = tuple(sorted(row.primary_evidence_ids[:1]))
    payload: dict[str, object] = {
        "canonical_path": row.canonical_path,
        "public_url": row.public_url,
        "current_work_item_id": row.current_work_item_id,
        "classification_run_id": run.run_id,
        "classification_run_digest": run.run_digest,
        "classification_decision_set_digest": run.input.decision_set_digest,
        "classification_source_row_digest": row.source_packet_row_digest,
        "inventory_evidence_ids": evidence,
        "inventory_evidence_digest": inventory_evidence_digest(evidence),
        "final_disposition": "keep",
        "retained_work_item_id": row.retained_work_item_id if retained else None,
        "retained_usage": "reuse" if retained else None,
        "recorded_by": "content_delivery_test",
        "recorded_at": datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
    }
    payload.update(updates)
    return ContentDeliveryIdentityCommand.model_validate(payload)


def test_delivery_identity_api_has_no_caller_owned_write_route() -> None:
    methods = app.openapi()["paths"].get("/api/content/delivery-identities", {})

    assert "post" not in methods


def test_store_records_exact_reconciled_and_typed_blocked_identity_states(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)

    exact = store.record_content_delivery_identity(_command(retained=False))
    retained = store.record_content_delivery_identity(_command(retained=True))
    blocked = store.record_content_delivery_identity(
        _command(retained=False, public_url="https://www.ekologus.pl/inny/")
    )

    assert exact.status == "created"
    assert exact.binding.status == "exact_current"
    assert retained.binding.status == "reconciled_retained"
    assert retained.binding.retained_usage == "reuse"
    assert blocked.binding.status == "blocked"
    assert blocked.binding.blocker is not None
    assert blocked.binding.blocker.reason == "canonical_path_mismatch"
    assert store.load_content_delivery_identity(exact.binding.binding_id) == exact.binding
    retry = store.record_content_delivery_identity(
        _command(
            retained=False,
            recorded_by="retry_actor",
            recorded_at=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        )
    )
    assert retry.status == "idempotent"
    assert retry.binding.binding_id == exact.binding.binding_id
    assert retry.binding.recorded_by == "content_delivery_test"
    assert exact.delivery_record.robot_ready is False
    assert exact.delivery_record.content_state == "identity_bound"

    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM content_delivery_identity_bindings"
        ).fetchone() == (3,)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE content_delivery_identity_bindings SET status = 'blocked'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM content_delivery_records")


def test_identity_current_projection_blocks_after_newer_classification_without_rebinding(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    recorded_run = exact_public_bdo_run()
    store.record_production_classification(recorded_run)
    created = store.record_content_delivery_identity(
        _command(retained=True, retained_work_item_id=None, retained_usage=None)
    )

    assert created.current.current_status == "exact_current"
    newer_packet_sha = "a" * 64
    newer_run = production_module._build_run(
        input_receipt=recorded_run.input.model_copy(
            update={"packet_sha256": newer_packet_sha}
        ),
        counts=recorded_run.counts,
        freshness=recorded_run.freshness,
        source_receipts=recorded_run.source_receipts,
        judge_receipt=recorded_run.judge_receipt.model_copy(
            update={"reviewed_packet_sha256": newer_packet_sha}
        ),
        rows=recorded_run.rows,
        audit=recorded_run.audit.model_copy(
            update={"recorded_at": datetime(2026, 9, 1, 10, 5, tzinfo=UTC)}
        ),
    )
    store.record_production_classification(newer_run)

    current = store.load_content_delivery_identity_record(created.binding.binding_id)
    assert current is not None
    assert current.binding == created.binding
    assert current.binding.status == "exact_current"
    assert current.current.current_status == "blocked"
    assert current.current.current_blocker is not None
    assert current.current.current_blocker.reason == "identity_classification_drift"


def test_store_blocks_historical_classification_when_work_item_collides(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "historical-collision.sqlite3")
    current = exact_public_bdo_run()
    historical = production_module._build_run(
        input_receipt=current.input.model_copy(
            update={
                "policy_id": "content_production_wave0_keep_packet_v1",
                "policy_digest": production_module.canonical_json_digest(
                    production_module.WAVE0_PRODUCTION_ACCEPTANCE_POLICY.model_dump(mode="json")
                ),
            }
        ),
        counts=current.counts,
        freshness=current.freshness,
        source_receipts=current.source_receipts,
        judge_receipt=current.judge_receipt,
        rows=current.rows,
        audit=current.audit,
    )
    store.record_production_classification(historical)

    result = store.record_content_delivery_identity(_command(retained=False, run=historical))

    assert historical.input.policy_id == "content_production_wave0_keep_packet_v1"
    assert result.binding.status == "blocked"
    assert result.binding.status != "exact_current"
    assert result.binding.blocker is not None
    assert result.binding.blocker.seam == "classification_identity"
    assert result.binding.blocker.reason == "classification_not_current"
    assert result.delivery_record.content_state == "identity_blocked"
    assert result.delivery_record.blocker_code == "classification_not_current"

    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM content_delivery_identity_bindings WHERE status = 'exact_current'"
        ).fetchone() == (0,)


def test_identity_binding_fails_closed_without_fuzzy_or_latest_fallback(tmp_path: Path) -> None:
    stores = [ContentWorkflowStore(tmp_path / f"state-{index}.sqlite3") for index in range(3)]
    for store in stores:
        store.record_production_classification(exact_public_bdo_run())

    wrong_row = (
        stores[0]
        .record_content_delivery_identity(
            _command(retained=False, classification_source_row_digest="f" * 64)
        )
        .binding
    )
    wrong_evidence = (
        stores[1]
        .record_content_delivery_identity(
            _command(
                retained=False,
                inventory_evidence_ids=("ev_unrelated",),
                inventory_evidence_digest=inventory_evidence_digest(("ev_unrelated",)),
            )
        )
        .binding
    )
    missing_exact_run = (
        stores[2]
        .record_content_delivery_identity(
            _command(retained=False, classification_run_digest="e" * 64)
        )
        .binding
    )

    assert wrong_row.blocker is not None
    assert wrong_row.blocker.reason == "classification_row_mismatch"
    assert wrong_evidence.blocker is not None
    assert wrong_evidence.blocker.reason == "inventory_evidence_not_classified"
    assert missing_exact_run.blocker is not None
    assert missing_exact_run.blocker.reason == "classification_run_mismatch"
    assert missing_exact_run.blocker.evidence_ids == ()

    missing_run = reconcile_content_delivery_identity(
        _command(retained=False, classification_run_id="missing_run"),
        ContentDeliveryClassificationLookup(row_status="run_missing"),
    )
    assert missing_run.blocker is not None
    assert missing_run.blocker.reason == "classification_run_missing"
    assert missing_run.blocker.evidence_ids == ()

    missing_row = reconcile_content_delivery_identity(
        _command(retained=False, current_work_item_id="missing_work_item"),
        ContentDeliveryClassificationLookup(row_status="missing"),
    )
    ambiguous_row = reconcile_content_delivery_identity(
        _command(retained=False),
        ContentDeliveryClassificationLookup(row_status="ambiguous"),
    )
    assert missing_row.blocker is not None
    assert missing_row.blocker.reason == "classification_row_missing"
    assert missing_row.blocker.evidence_ids == ()
    assert ambiguous_row.blocker is not None
    assert ambiguous_row.blocker.reason == "classification_row_ambiguous"
    assert ambiguous_row.blocker.evidence_ids == ()


def test_same_logical_context_conflicts_when_identity_evidence_changes(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    created = store.record_content_delivery_identity(_command(retained=False))

    conflict = store.record_content_delivery_identity(
        _command(
            retained=False,
            inventory_evidence_ids=("ev_unrelated",),
            inventory_evidence_digest=inventory_evidence_digest(("ev_unrelated",)),
        )
    )

    assert conflict.status == "conflict"
    assert conflict.binding.binding_id == created.binding.binding_id
    assert conflict.binding.binding_digest == created.binding.binding_digest


def test_identity_and_delivery_record_replacement_is_rejected(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "no-replace.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    created = store.record_content_delivery_identity(_command(retained=False))

    with store._connect() as connection, pytest.raises(
        sqlite3.IntegrityError, match="append-only"
    ):
        connection.execute(
            "INSERT OR REPLACE INTO content_delivery_identity_bindings "
            "(binding_id, binding_digest, canonical_path, public_url, current_work_item_id, "
            "retained_work_item_id, classification_run_id, classification_run_digest, "
            "classification_source_row_digest, inventory_evidence_digest, status, recorded_by, "
            "recorded_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                created.binding.binding_id,
                created.binding.binding_digest,
                created.binding.canonical_path,
                created.binding.public_url,
                created.binding.current_work_item_id,
                created.binding.retained_work_item_id,
                created.binding.classification_run_id,
                created.binding.classification_run_digest,
                created.binding.classification_source_row_digest,
                created.binding.inventory_evidence_digest,
                created.binding.status,
                "replacement_actor",
                created.binding.recorded_at.isoformat(),
                created.binding.model_dump_json(),
            ),
        )

    with store._connect() as connection, pytest.raises(
        sqlite3.IntegrityError, match="append-only"
    ):
        connection.execute(
            "INSERT OR REPLACE INTO content_delivery_records "
            "(record_id, record_digest, binding_id, binding_digest, final_disposition, "
            "content_state, delivery_status, robot_ready, blocker_code, payload_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                created.delivery_record.record_id,
                created.delivery_record.record_digest,
                created.delivery_record.binding_id,
                created.delivery_record.binding_digest,
                created.delivery_record.final_disposition,
                created.delivery_record.content_state,
                created.delivery_record.delivery_status,
                0,
                created.delivery_record.blocker_code,
                created.delivery_record.model_dump_json(),
            ),
        )

    unchanged = store.load_content_delivery_identity_record(created.binding.binding_id)
    assert unchanged is not None
    assert unchanged.binding == created.binding
    assert unchanged.delivery_record == created.delivery_record


def test_identity_record_rejects_a_classification_that_is_no_longer_latest(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "latest-classification.sqlite3")
    recorded_run = exact_public_bdo_run()
    store.record_production_classification(recorded_run)
    newer_packet_sha = "a" * 64
    newer_run = production_module._build_run(
        input_receipt=recorded_run.input.model_copy(update={"packet_sha256": newer_packet_sha}),
        counts=recorded_run.counts,
        freshness=recorded_run.freshness,
        source_receipts=recorded_run.source_receipts,
        judge_receipt=recorded_run.judge_receipt.model_copy(
            update={"reviewed_packet_sha256": newer_packet_sha}
        ),
        rows=recorded_run.rows,
        audit=recorded_run.audit.model_copy(
            update={"recorded_at": datetime(2026, 9, 11, 10, 5, tzinfo=UTC)}
        ),
    )
    store.record_production_classification(newer_run)

    result = store.record_content_delivery_identity(_command(retained=False, run=recorded_run))

    assert result.binding.status == "blocked"
    assert result.binding.blocker is not None
    assert result.binding.blocker.reason == "classification_not_current"
    assert result.delivery_record.content_state == "identity_blocked"


def test_recorded_at_is_aware_and_normalized_to_utc() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _command(retained=False, recorded_at=datetime(2026, 9, 10, 10, 0))

    first = _command(retained=False)
    same_instant = _command(
        retained=False,
        recorded_at=datetime.fromisoformat("2026-09-10T12:00:00+02:00"),
    )
    assert same_instant.recorded_at == first.recorded_at


def test_persisted_audit_actor_tampering_fails_closed(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    created = store.record_content_delivery_identity(_command(retained=False))

    with sqlite3.connect(store.path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("DROP TRIGGER content_delivery_identity_bindings_no_update")
        row = connection.execute(
            "SELECT payload_json FROM content_delivery_identity_bindings WHERE binding_id = ?",
            (created.binding.binding_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row["payload_json"])
        payload["recorded_by"] = "forged_actor"
        connection.execute(
            "UPDATE content_delivery_identity_bindings SET payload_json = ? WHERE binding_id = ?",
            (json.dumps(payload), created.binding.binding_id),
        )

    with pytest.raises(ValueError, match="scalars do not match payload"):
        store.load_content_delivery_identity(created.binding.binding_id)


def test_legacy_identity_table_migrates_actor_and_restores_append_only_guards(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    created = store.record_content_delivery_identity(_command(retained=False))
    _downgrade_identity_table_without_actor(store.path)

    reopened = ContentWorkflowStore(store.path)
    binding = reopened.load_content_delivery_identity(created.binding.binding_id)

    assert binding is not None
    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT recorded_by, payload_json FROM content_delivery_identity_bindings"
        ).fetchone()
        assert row is not None
        assert row[0] == json.loads(row[1])["recorded_by"] == "content_delivery_test"
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE content_delivery_identity_bindings SET recorded_by = 'forged'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM content_delivery_identity_bindings")


def test_legacy_identity_actor_migration_rolls_back_safely_on_malformed_payload(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    store.record_production_classification(exact_public_bdo_run())
    store.record_content_delivery_identity(_command(retained=False))
    _downgrade_identity_table_without_actor(store.path, remove_payload_actor=True)

    with pytest.raises(ValueError, match="no valid audit actor"):
        ContentWorkflowStore(store.path).load_content_delivery_identity("unused")

    with sqlite3.connect(store.path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(content_delivery_identity_bindings)")
        }
        assert "recorded_by" not in columns
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE content_delivery_identity_bindings SET status = 'blocked'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM content_delivery_identity_bindings")


def _downgrade_identity_table_without_actor(
    path: Path,
    *,
    remove_payload_actor: bool = False,
) -> None:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM content_delivery_identity_bindings").fetchone()
        assert row is not None
        payload = json.loads(row["payload_json"])
        if remove_payload_actor:
            payload.pop("recorded_by")
        connection.executescript(
            """
            DROP TRIGGER content_delivery_identity_bindings_no_update;
            DROP TRIGGER content_delivery_identity_bindings_no_delete;
            ALTER TABLE content_delivery_identity_bindings RENAME TO old_identity_bindings;
            CREATE TABLE content_delivery_identity_bindings (
              binding_id TEXT PRIMARY KEY, binding_digest TEXT NOT NULL UNIQUE,
              canonical_path TEXT NOT NULL, public_url TEXT NOT NULL,
              current_work_item_id TEXT NOT NULL, retained_work_item_id TEXT,
              classification_run_id TEXT NOT NULL, classification_run_digest TEXT NOT NULL,
              classification_source_row_digest TEXT NOT NULL,
              inventory_evidence_digest TEXT NOT NULL,
              status TEXT NOT NULL, recorded_at TEXT NOT NULL, payload_json TEXT NOT NULL
            );
            DROP TABLE old_identity_bindings;
            CREATE TRIGGER content_delivery_identity_bindings_no_update
            BEFORE UPDATE ON content_delivery_identity_bindings BEGIN
              SELECT RAISE(ABORT, 'content delivery identity bindings are append-only');
            END;
            CREATE TRIGGER content_delivery_identity_bindings_no_delete
            BEFORE DELETE ON content_delivery_identity_bindings BEGIN
              SELECT RAISE(ABORT, 'content delivery identity bindings are append-only');
            END;
            """
        )
        connection.execute(
            """
            INSERT INTO content_delivery_identity_bindings
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["binding_id"],
                row["binding_digest"],
                row["canonical_path"],
                row["public_url"],
                row["current_work_item_id"],
                row["retained_work_item_id"],
                row["classification_run_id"],
                row["classification_run_digest"],
                row["classification_source_row_digest"],
                row["inventory_evidence_digest"],
                row["status"],
                row["recorded_at"],
                json.dumps(payload),
            ),
        )
