from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from tests.content.test_delivery_identity_binding import _command as identity_command
from wilq.content.workflow.decisions.production import project_content_production_classification
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    ContentDeliveryIdentityBinding,
    reconcile_content_delivery_identity,
)
from wilq.content.workflow.source_pack_binding import (
    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    SOURCE_FACT_REGISTRY_ID,
    ContentSourceFactRegistryReceipt,
    ContentSourcePackBindingCommand,
    ContentSourcePackContextAttestation,
    content_source_pack_context_digest,
    evidence_ids_digest,
    reconcile_content_source_pack_binding,
    source_fact_ids_digest,
    source_fact_registry_digest,
)
from wilq.content.workflow.store.store import ContentWorkflowStore

SOURCE_PACK_ID = "source_pack_bdo_2026_09"
SOURCE_PACK_HASH = "a" * 64
RECORDED_AT = datetime.now(UTC)


def _setup_store(tmp_path: Path) -> tuple[ContentWorkflowStore, ContentDeliveryIdentityBinding]:
    store = ContentWorkflowStore(tmp_path / "state.sqlite3")
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    identity = store.record_content_delivery_identity(identity_command(retained=False)).binding
    return store, identity


def test_schema_v8_store_is_upgraded_before_source_pack_write(tmp_path: Path) -> None:
    path = tmp_path / "schema-v8.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE legacy_marker (id TEXT PRIMARY KEY)")
        connection.execute("PRAGMA user_version = 8")

    store = ContentWorkflowStore(path)
    assert store.load_content_source_pack_binding("missing") is None

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (10,)
        assert connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'content_source_pack_bindings'
            """
        ).fetchone() == (1,)
        assert connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'trigger'
              AND name = 'content_source_pack_bindings_no_update'
            """
        ).fetchone() == (1,)


def _source_command(
    identity: ContentDeliveryIdentityBinding,
    **updates: object,
) -> ContentSourcePackBindingCommand:
    context_attestation = ContentSourcePackContextAttestation(
        run_id=identity.classification_run_id,
        context_digest="1" * 64,
        checked_at=RECORDED_AT,
        source="content_delivery_identity_binding",
        evidence_ids=identity.inventory_evidence_ids,
    )
    context_digest = content_source_pack_context_digest(identity, context_attestation)
    context_attestation = context_attestation.model_copy(update={"context_digest": context_digest})
    payload: dict[str, object] = {
        "source_pack_id": SOURCE_PACK_ID,
        "source_pack_sha256": SOURCE_PACK_HASH,
        "identity_binding_id": identity.binding_id,
        "identity_binding_digest": identity.binding_digest,
        "current_work_item_id": identity.current_work_item_id,
        "source_fact_ids": (
            "ekologus_public_bdo_faq_2026_07_01",
            "ekologus_public_consulting_outsourcing_offer_2026_07_01",
        ),
        "evidence_ids": identity.inventory_evidence_ids,
        "fresh_context_digest": context_digest,
        "source_fact_registry_receipt": ContentSourceFactRegistryReceipt(
            registry_id=SOURCE_FACT_REGISTRY_ID,
            registry_digest=source_fact_registry_digest(),
            checked_at=RECORDED_AT,
            evidence_ids=tuple(
                sorted(
                    {
                        APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                        SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
                    }
                )
            ),
        ),
        "fresh_context_attestation": context_attestation,
        "recorded_by": "source_pack_test",
        "recorded_at": RECORDED_AT,
    }
    payload.update(updates)
    return ContentSourcePackBindingCommand.model_validate(payload)


def test_store_records_exact_redacted_source_pack_and_is_idempotent(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    command = _source_command(identity)

    created = store.record_content_source_pack_binding(command)
    retry = store.record_content_source_pack_binding(
        command.model_copy(
            update={
                "recorded_by": "retry_actor",
                "recorded_at": RECORDED_AT + timedelta(minutes=1),
            }
        )
    )

    assert created.status == "created"
    assert created.binding.status == "exact_current"
    assert created.binding.source_facts_digest == source_fact_ids_digest(command.source_fact_ids)
    assert created.binding.evidence_ids_digest == evidence_ids_digest(command.evidence_ids)
    assert retry.status == "idempotent"
    assert retry.binding == created.binding
    assert store.load_content_source_pack_binding(created.binding.binding_id) == created.binding

    with sqlite3.connect(store.path) as connection:
        row = connection.execute("SELECT payload_json FROM content_source_pack_bindings").fetchone()
        assert row is not None
        payload = json.loads(row[0])
        assert "raw_source_text" not in payload
        assert "ekologus_public_bdo_faq_2026_07_01" in payload["source_fact_ids"]
        assert payload["source_fact_registry_receipt"]["registry_id"] == SOURCE_FACT_REGISTRY_ID
        assert payload["fresh_context_attestation"][
            "checked_at"
        ] == RECORDED_AT.isoformat().replace("+00:00", "Z")
        assert connection.execute(
            "SELECT COUNT(*) FROM content_source_pack_bindings"
        ).fetchone() == (1,)


def test_source_pack_hash_mismatch_persists_typed_blocker(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    store.record_content_source_pack_binding(_source_command(identity))

    mismatch = store.record_content_source_pack_binding(
        _source_command(identity, source_pack_sha256="b" * 64)
    )

    assert mismatch.status == "conflict"
    assert mismatch.binding.status == "blocked"
    assert mismatch.binding.blocker is not None
    assert mismatch.binding.blocker.reason == "source_pack_hash_mismatch"
    assert store.load_content_source_pack_binding(mismatch.binding.binding_id) == mismatch.binding


def test_source_pack_rejects_unregistered_fact_and_zero_digest(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    blocked = store.record_content_source_pack_binding(
        _source_command(identity, source_fact_ids=("fact_not_in_registry",))
    )

    assert blocked.binding.status == "blocked"
    assert blocked.binding.blocker is not None
    assert blocked.binding.blocker.reason == "source_fact_not_registered"
    with sqlite3.connect(store.path) as connection:
        audit_payload = connection.execute(
            "SELECT payload_json FROM audit_events WHERE id = ?",
            (f"audit_{blocked.binding.binding_id}",),
        ).fetchone()[0]
    assert json.loads(audit_payload)["event_type_label"] == (
        "Zapisano zablokowane powiązanie paczki źródłowej"
    )

    with pytest.raises(ValidationError, match="zero digest"):
        _source_command(identity, fresh_context_digest="0" * 64)
    with pytest.raises(ValidationError, match="zero digest"):
        _source_command(
            identity,
            source_fact_registry_receipt=ContentSourceFactRegistryReceipt(
                registry_id=SOURCE_FACT_REGISTRY_ID,
                registry_digest="0" * 64,
                checked_at=RECORDED_AT,
                evidence_ids=(APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,),
            ),
        )


def test_source_pack_rejects_unapproved_fact_and_registry_digest_mismatch(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    unapproved = store.record_content_source_pack_binding(
        _source_command(
            identity,
            source_fact_ids=("ekologus_public_homepage_service_overview_2026_07_02",),
        )
    )
    assert unapproved.binding.blocker is not None
    assert unapproved.binding.blocker.reason == "source_fact_not_approved"

    registry_mismatch = store.record_content_source_pack_binding(
        _source_command(
            identity,
            source_fact_registry_receipt=ContentSourceFactRegistryReceipt(
                registry_id=SOURCE_FACT_REGISTRY_ID,
                registry_digest="a" * 64,
                checked_at=RECORDED_AT,
                evidence_ids=tuple(
                    sorted(
                        {
                            APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                            SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
                        }
                    )
                ),
            ),
        )
    )
    assert registry_mismatch.binding.blocker is not None
    assert registry_mismatch.binding.blocker.reason == "source_fact_registry_mismatch"


def test_source_pack_rejects_secret_like_identifiers_before_persisting(
    tmp_path: Path,
) -> None:
    _, identity = _setup_store(tmp_path)
    with pytest.raises(ValidationError, match="credential identifier"):
        _source_command(
            identity,
            source_pack_id="sk-" + "a" * 40,
        )


def test_source_pack_rejects_untrusted_exact_id_values_before_persisting(
    tmp_path: Path,
) -> None:
    _, identity = _setup_store(tmp_path)
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        _source_command(identity, identity_binding_id="private customer binding")
    with pytest.raises(ValidationError, match="Source fact IDs"):
        _source_command(identity, source_fact_ids=("fact with spaces",))
    with pytest.raises(ValidationError, match="Evidence IDs"):
        _source_command(identity, evidence_ids=("evidence with spaces",))


def test_source_pack_preserves_valid_long_identifiers_after_redaction(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    long_id = "pack-0123456789abcdefghijklmnopqrstuv"

    result = store.record_content_source_pack_binding(
        _source_command(identity, source_pack_id=long_id)
    )

    assert result.binding.status == "exact_current"
    assert result.binding.source_pack_id == long_id
    assert store.load_content_source_pack_binding(result.binding.binding_id) == result.binding


def test_source_pack_rejects_registry_receipt_with_arbitrary_evidence(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    blocked = store.record_content_source_pack_binding(
        _source_command(
            identity,
            source_fact_registry_receipt=ContentSourceFactRegistryReceipt(
                registry_id=SOURCE_FACT_REGISTRY_ID,
                registry_digest=source_fact_registry_digest(),
                checked_at=RECORDED_AT,
                evidence_ids=("ev_arbitrary",),
            ),
        )
    )

    assert blocked.binding.status == "blocked"
    assert blocked.binding.blocker is not None
    assert blocked.binding.blocker.reason == "source_fact_registry_mismatch"
    assert "ev_arbitrary" not in blocked.binding.evidence_ids
    assert "ev_arbitrary" not in blocked.binding.source_fact_registry_receipt.evidence_ids
    with sqlite3.connect(store.path) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload_json FROM content_source_pack_bindings WHERE binding_id = ?",
                (blocked.binding.binding_id,),
            ).fetchone()[0]
        )
    assert "ev_arbitrary" not in payload["source_fact_registry_receipt"]["evidence_ids"]


def test_source_pack_rejects_unbound_command_evidence(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    blocked = store.record_content_source_pack_binding(
        _source_command(identity, evidence_ids=(*identity.inventory_evidence_ids, "ev_unknown"))
    )

    assert blocked.binding.status == "blocked"
    assert blocked.binding.blocker is not None
    assert blocked.binding.blocker.reason == "evidence_not_bound"


def test_source_pack_rejects_stale_or_future_receipts(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    stale = _source_command(
        identity,
        source_fact_registry_receipt=ContentSourceFactRegistryReceipt(
            registry_id=SOURCE_FACT_REGISTRY_ID,
            registry_digest=source_fact_registry_digest(),
            checked_at=datetime.now(UTC) - timedelta(days=40),
            evidence_ids=tuple(
                sorted(
                    {
                        APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                        SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
                    }
                )
            ),
        ),
    )
    stale_result = store.record_content_source_pack_binding(stale)
    assert stale_result.binding.blocker is not None
    assert stale_result.binding.blocker.reason == "source_fact_registry_stale"

    future_attestation = ContentSourcePackContextAttestation(
        run_id=identity.classification_run_id,
        context_digest="1" * 64,
        checked_at=datetime.now(UTC) + timedelta(days=2),
        source="content_delivery_identity_binding",
        evidence_ids=identity.inventory_evidence_ids,
    )
    future_digest = content_source_pack_context_digest(identity, future_attestation)
    future_attestation = future_attestation.model_copy(update={"context_digest": future_digest})
    future_result = store.record_content_source_pack_binding(
        _source_command(
            identity,
            fresh_context_digest=future_digest,
            fresh_context_attestation=future_attestation,
        )
    )
    assert future_result.binding.blocker is not None
    assert future_result.binding.blocker.reason == "fresh_context_stale"


def test_source_pack_uses_server_owned_recorded_at(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    backdated = _source_command(
        identity,
        recorded_at=datetime.now(UTC) - timedelta(days=2),
    )

    result = store.record_content_source_pack_binding(backdated)

    assert result.binding.status == "exact_current"
    assert result.binding.recorded_at > datetime.now(UTC) - timedelta(minutes=1)


def test_source_pack_changed_fact_set_is_typed_conflict_and_audited(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    first = store.record_content_source_pack_binding(_source_command(identity))
    changed = store.record_content_source_pack_binding(
        _source_command(
            identity,
            source_fact_ids=("ekologus_public_bdo_faq_2026_07_01",),
        )
    )

    assert first.status == "created"
    assert changed.status == "conflict"
    assert changed.binding.status == "blocked"
    assert changed.binding.blocker is not None
    assert changed.binding.blocker.reason == "source_facts_mismatch"
    assert store.load_content_source_pack_binding(changed.binding.binding_id) == changed.binding
    assert store.load_content_source_pack_binding(first.binding.binding_id) == first.binding

    with sqlite3.connect(store.path) as connection:
        audit_row = connection.execute(
            "SELECT payload_json FROM audit_events WHERE id = ?",
            (f"audit_{first.binding.binding_id}",),
        ).fetchone()
    assert audit_row is not None
    audit = json.loads(audit_row[0])
    assert audit["event_type"] == "content_source_pack_binding_recorded"
    assert audit["details"]["adapter"] == "content_source_pack_binding_store"
    assert audit["details"]["trace"]["binding_digest"] == first.binding.binding_digest
    assert audit["details"]["external_write_attempted"] is False
    with sqlite3.connect(store.path) as connection:
        conflict_audit_rows = connection.execute(
            "SELECT payload_json FROM audit_events WHERE id LIKE 'audit_source_pack_conflict_%'"
        ).fetchall()
    assert len(conflict_audit_rows) == 1
    conflict_audit = json.loads(conflict_audit_rows[0][0])
    assert conflict_audit["event_type"] == "content_source_pack_binding_conflict"
    assert conflict_audit["details"]["external_write_attempted"] is False


def test_blocked_source_receipt_does_not_prevent_corrected_exact_receipt(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    stale = _source_command(
        identity,
        source_fact_registry_receipt=ContentSourceFactRegistryReceipt(
            registry_id=SOURCE_FACT_REGISTRY_ID,
            registry_digest=source_fact_registry_digest(),
            checked_at=datetime.now(UTC) - timedelta(days=40),
            evidence_ids=tuple(
                sorted(
                    {
                        APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                        SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
                    }
                )
            ),
        ),
    )
    blocked = store.record_content_source_pack_binding(stale)
    corrected = store.record_content_source_pack_binding(_source_command(identity))

    assert blocked.binding.status == "blocked"
    assert corrected.status == "created"
    assert corrected.binding.status == "exact_current"
    assert store.load_content_source_pack_binding(corrected.binding.binding_id) == corrected.binding
    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM content_source_pack_bindings WHERE status = 'blocked'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM content_source_pack_bindings WHERE status = 'exact_current'"
        ).fetchone() == (1,)


def test_source_pack_context_attestation_mismatch_is_typed_blocker() -> None:
    run = exact_public_bdo_run()
    row = run.rows[1]
    identity = reconcile_content_delivery_identity(
        identity_command(retained=False),
        ContentDeliveryClassificationLookup(
            row_status="exact",
            run=project_content_production_classification(run, row),
        ),
    )
    command = _source_command(
        identity,
        fresh_context_attestation=_source_command(identity).fresh_context_attestation.model_copy(
            update={"run_id": "other_run"}
        ),
    )

    blocked = reconcile_content_source_pack_binding(command, identity, now=RECORDED_AT)

    assert blocked.status == "blocked"
    assert blocked.blocker is not None
    assert blocked.blocker.reason == "fresh_context_mismatch"


def test_source_pack_context_evidence_and_work_item_mismatches_fail_closed() -> None:
    run = exact_public_bdo_run()
    row = run.rows[1]
    identity = reconcile_content_delivery_identity(
        identity_command(retained=False),
        ContentDeliveryClassificationLookup(
            row_status="exact",
            run=project_content_production_classification(run, row),
        ),
    )
    command = _source_command(identity)

    context_refresh = reconcile_content_source_pack_binding(command, identity, now=RECORDED_AT)
    evidence_mismatch = reconcile_content_source_pack_binding(
        command,
        identity,
        prior_evidence_sets=(("ev_old",),),
        now=RECORDED_AT,
    )
    work_item_mismatch = reconcile_content_source_pack_binding(
        command.model_copy(update={"current_work_item_id": "other_work_item"}),
        identity,
        now=RECORDED_AT,
    )

    assert evidence_mismatch.blocker is not None
    assert work_item_mismatch.blocker is not None
    assert context_refresh.blocker is None
    assert evidence_mismatch.blocker.reason == "evidence_set_mismatch"
    assert work_item_mismatch.blocker.reason == "work_item_mismatch"


def test_source_pack_requires_exact_identity_not_path_only() -> None:
    with pytest.raises(ValidationError, match="identity_binding_id"):
        ContentSourcePackBindingCommand.model_validate(
            {
                "source_pack_id": SOURCE_PACK_ID,
                "source_pack_sha256": SOURCE_PACK_HASH,
                "canonical_path": "/bdo",
                "current_work_item_id": "work_item",
                "source_fact_ids": ["fact"],
                "evidence_ids": ["evidence"],
                "fresh_context_digest": "c" * 64,
                "recorded_by": "source_pack_test",
                "recorded_at": RECORDED_AT,
            }
        )


def test_source_pack_hash_only_join_is_typed_blocked(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    blocked = store.record_content_source_pack_binding(
        _source_command(
            identity,
            identity_binding_id="missing_identity_binding",
            identity_binding_digest="d" * 64,
        )
    )

    assert blocked.status == "created"
    assert blocked.binding.status == "blocked"
    assert blocked.binding.blocker is not None
    assert blocked.binding.blocker.reason == "delivery_identity_missing"


def test_source_pack_tamper_and_sqlite_mutations_fail_closed(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    created = store.record_content_source_pack_binding(_source_command(identity))

    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE content_source_pack_bindings SET status = 'blocked'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM content_source_pack_bindings")
        connection.execute("DROP TRIGGER content_source_pack_bindings_no_update")
        payload_row = connection.execute(
            "SELECT payload_json FROM content_source_pack_bindings WHERE binding_id = ?",
            (created.binding.binding_id,),
        ).fetchone()
        assert payload_row is not None
        payload = json.loads(payload_row[0])
        payload["recorded_by"] = "forged_actor"
        connection.execute(
            "UPDATE content_source_pack_bindings SET payload_json = ? WHERE binding_id = ?",
            (json.dumps(payload), created.binding.binding_id),
        )

    with pytest.raises(ValueError, match="scalars do not match payload"):
        store.load_content_source_pack_binding(created.binding.binding_id)
