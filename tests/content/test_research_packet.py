from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_research_packet as route_module
from apps.api.wilq_api.main import app
from tests.content.test_delivery_identity_binding import _command as identity_command
from tests.content.test_source_pack_binding import _setup_store, _source_command
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.research_packet import (
    ContentResearchPacket,
    ContentResearchPacketCommand,
    ContentResearchPacketContextReceipt,
    ContentResearchPacketFreshness,
    ContentResearchPacketInternalLink,
    research_packet_digest,
    research_packet_logical_id,
)
from wilq.content.workflow.research_packet_preparation_receipt import (
    build_research_packet_preparation_receipt,
)
from wilq.content.workflow.source_pack_binding import (
    ContentSourcePackBinding,
    content_source_pack_binding_digest,
    content_source_pack_binding_logical_id,
    evidence_ids_digest,
    source_fact_ids_digest,
)
from wilq.content.workflow.store.store_source_pack_binding import _insert_source_pack_binding
from wilq.security.redaction import redact_mapping
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION


def _packet_command(
    store,
    identity,
    *,
    now: datetime | None = None,
    legacy_exact: bool = False,
    **updates: object,
):
    source_pack = (
        legacy_exact_source_pack_fixture(store, identity)
        if legacy_exact
        else store.record_content_source_pack_binding(_source_command(identity)).binding
    )
    timestamp = now or datetime.now(UTC)
    facts = {fact.source_id: fact for fact in ekologus_source_facts()}
    blocked_claims = tuple(
        sorted(
            {
                claim
                for source_id in source_pack.source_fact_ids
                for claim in facts[source_id].blocked_claims
            }
        )
    )
    payload: dict[str, object] = {
        "source_pack_binding_id": source_pack.binding_id,
        "source_pack_binding_digest": source_pack.binding_digest,
        "identity_binding_id": identity.binding_id,
        "identity_binding_digest": identity.binding_digest,
        "current_work_item_id": identity.current_work_item_id,
        "content_kind": "service",
        "intent": "bdo compliance reporting",
        "query_cluster": tuple(sorted(("bdo", "sprawozdawczość bdo"))),
        "canonical_owner": identity.canonical_path,
        "target_audience": "przedsiębiorca",
        "buyer_problem": "brak pewności obowiązków",
        "buyer_trigger": "zbliżający się termin",
        "approved_source_fact_ids": source_pack.source_fact_ids,
        "blocked_claims": blocked_claims,
        "evidence_ids": source_pack.evidence_ids,
        "freshness": tuple(
            ContentResearchPacketFreshness(
                source_id=source_id,
                evidence_ids=source_pack.evidence_ids,
                checked_at=timestamp,
                status="fresh",
            )
            for source_id in source_pack.source_fact_ids
        ),
        "legal_source_requirements": ("none_identified",),
        "cta_destination": "/kontakt/",
        "internal_links": (
            ContentResearchPacketInternalLink(
                destination_path="/kontakt/",
                anchor_text="Skontaktuj się",
                relation="next_step",
                verification="exact_verified",
            ),
        ),
        "recorded_by": "research_packet_test",
        "recorded_at": timestamp,
    }
    payload["context_receipt"] = ContentResearchPacketContextReceipt(
        classification_run_id=identity.classification_run_id,
        classification_run_digest=identity.classification_run_digest,
        classification_source_row_digest=identity.classification_source_row_digest,
        identity_binding_id=identity.binding_id,
        identity_binding_digest=identity.binding_digest,
        service_semantic_digest="1" * 64,
        brief_semantic_digest="2" * 64,
        demand_evidence_digest="3" * 64,
        verified_links_digest="4" * 64,
        regulatory_coverage_digest="5" * 64,
        freshness_digest="6" * 64,
        cta_destination="/kontakt/",
        evidence_ids=source_pack.evidence_ids,
    )
    payload.update(updates)
    command = ContentResearchPacketCommand.model_validate(payload)
    if legacy_exact:
        receipt = build_research_packet_preparation_receipt(
            command,
            recorded_at=timestamp,
        )
        store._record_content_research_packet_preparation_receipt(receipt)
        command = command.model_copy(
            update={
                "preparation_receipt_id": receipt.receipt_id,
                "preparation_receipt_digest": receipt.receipt_digest,
            }
        )
    return command, source_pack


def legacy_exact_source_pack_fixture(store, identity) -> ContentSourcePackBinding:
    """Seed compatibility-only history; this is never a current public writer."""

    command = _source_command(identity)
    payload: dict[str, object] = {
        "schema_version": "wilq_content_source_pack_binding_v1",
        "status": "exact_current",
        "source_pack_id": command.source_pack_id,
        "source_pack_sha256": command.source_pack_sha256,
        "identity_binding_id": command.identity_binding_id,
        "identity_binding_digest": command.identity_binding_digest,
        "current_work_item_id": command.current_work_item_id,
        "source_fact_ids": command.source_fact_ids,
        "evidence_ids": command.evidence_ids,
        "source_facts_digest": source_fact_ids_digest(command.source_fact_ids),
        "evidence_ids_digest": evidence_ids_digest(command.evidence_ids),
        "fresh_context_digest": command.fresh_context_digest,
        "source_fact_registry_receipt": command.source_fact_registry_receipt.model_dump(
            mode="json"
        ),
        "fresh_context_attestation": command.fresh_context_attestation.model_dump(mode="json"),
        "blocker": None,
        "recorded_by": "legacy_exact_source_pack_fixture",
        "recorded_at": command.recorded_at.isoformat(),
    }
    binding_digest = content_source_pack_binding_digest(payload)
    logical_id = content_source_pack_binding_logical_id(payload)
    binding = ContentSourcePackBinding.model_validate(
        {
            "binding_id": f"content_source_pack_binding_{logical_id[:24]}",
            "binding_digest": binding_digest,
            **payload,
        }
    )
    with store._connect() as connection:
        _insert_source_pack_binding(connection, binding)
    return binding


def _with_preparation_receipt(store, command: ContentResearchPacketCommand):
    receipt = build_research_packet_preparation_receipt(
        command,
        recorded_at=command.recorded_at,
    )
    store._record_content_research_packet_preparation_receipt(receipt)
    return command.model_copy(
        update={
            "preparation_receipt_id": receipt.receipt_id,
            "preparation_receipt_digest": receipt.receipt_digest,
        }
    )


def test_schema_v9_store_upgrades_research_packet_table(tmp_path: Path) -> None:
    path = tmp_path / "schema-v9.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE legacy_marker (id TEXT PRIMARY KEY)")
        connection.execute("PRAGMA user_version = 9")

    from wilq.content.workflow.store.store import ContentWorkflowStore

    store = ContentWorkflowStore(path)
    assert store.load_content_research_packet("missing") is None

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (
            SQLITE_SCHEMA_VERSION,
        )
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'content_research_packets'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'trigger' AND name = 'content_research_packets_no_update'"
        ).fetchone() == (1,)


def test_exact_packet_is_redacted_immutable_and_idempotent(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, source_pack = _packet_command(store, identity, legacy_exact=True)

    created = store.record_content_research_packet(command)
    retry = store.record_content_research_packet(
        command.model_copy(update={"recorded_by": "retry_actor"})
    )

    assert created.status == "created"
    assert created.packet.status == "exact_current"
    assert created.packet.source_pack_binding_id == source_pack.binding_id
    assert retry.status == "idempotent"
    assert retry.packet == created.packet
    assert store.load_content_research_packet(created.packet.packet_id) == created.packet

    with sqlite3.connect(store.path) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload_json FROM content_research_packets WHERE packet_id = ?",
                (created.packet.packet_id,),
            ).fetchone()[0]
        )
        assert "extracted_fact" not in json.dumps(payload)
        assert "source_url_or_path" not in json.dumps(payload)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE content_research_packets SET status = 'blocked' WHERE packet_id = ?",
                (created.packet.packet_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM content_research_packets WHERE packet_id = ?",
                (created.packet.packet_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                """
                INSERT OR REPLACE INTO content_research_packets
                SELECT * FROM content_research_packets WHERE packet_id = ?
                """,
                (created.packet.packet_id,),
            )


def test_preparation_receipt_readback_rejects_payload_tamper(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    receipt_id = command.preparation_receipt_id
    assert receipt_id is not None

    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "DROP TRIGGER content_research_packet_preparation_receipts_no_update"
        )
        row = connection.execute(
            "SELECT payload_json FROM content_research_packet_preparation_receipts "
            "WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        payload["input_digest"] = "f" * 64
        connection.execute(
            "UPDATE content_research_packet_preparation_receipts "
            "SET payload_json = ? WHERE receipt_id = ?",
            (json.dumps(payload, ensure_ascii=False), receipt_id),
        )

    with pytest.raises(ValueError, match="ID/digest"):
        store._load_content_research_packet_preparation_receipt(receipt_id)


def test_preparation_receipt_readback_rejects_scalar_tamper(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    receipt_id = command.preparation_receipt_id
    assert receipt_id is not None

    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "DROP TRIGGER content_research_packet_preparation_receipts_no_update"
        )
        connection.execute(
            "UPDATE content_research_packet_preparation_receipts "
            "SET input_digest = ? WHERE receipt_id = ?",
            ("f" * 64, receipt_id),
        )

    with pytest.raises(ValueError, match="scalars do not match payload"):
        store._load_content_research_packet_preparation_receipt(receipt_id)


def test_preparation_receipt_replay_from_another_command_is_blocked(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    replay = command.model_copy(update={"buyer_problem": "Inny problem."})

    result = store.record_content_research_packet(replay)

    assert result.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "preparation_receipt_mismatch"
    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM content_research_packets"
        ).fetchone() == (0,)


def test_preparation_receipt_is_readable_from_an_independent_store_instance(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    receipt_id = command.preparation_receipt_id
    assert receipt_id is not None

    independent_store = type(store)(store.path)
    receipt = independent_store._load_content_research_packet_preparation_receipt(receipt_id)

    assert receipt is not None
    assert receipt.receipt_id == receipt_id
    assert receipt.receipt_digest == command.preparation_receipt_digest


def test_preparation_receipt_replay_is_idempotent(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    receipt_id = command.preparation_receipt_id
    assert receipt_id is not None
    receipt = store._load_content_research_packet_preparation_receipt(receipt_id)
    assert receipt is not None

    replay = store._record_content_research_packet_preparation_receipt(receipt)

    assert replay.status == "idempotent"
    assert replay.receipt == receipt


def test_direct_store_requires_a_server_owned_preparation_receipt(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    command = command.model_copy(
        update={"preparation_receipt_id": None, "preparation_receipt_digest": None}
    )

    result = store.record_content_research_packet(command)

    assert result.status == "blocked"
    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "preparation_receipt_missing"
    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM content_research_packets"
        ).fetchone() == (0,)


def test_exact_packet_without_context_receipt_is_typed_blocker(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)

    result = store.record_content_research_packet(
        command.model_copy(update={"context_receipt": None})
    )

    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "context_receipt_missing"


def test_context_receipt_evidence_is_an_assertion_not_a_new_authority(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    command, source_pack = _packet_command(store, identity, legacy_exact=True)
    assert command.context_receipt is not None
    tampered_receipt = command.context_receipt.model_copy(
        update={
            "evidence_ids": tuple(
                sorted((*source_pack.evidence_ids, "ev_outside_context_receipt"))
            )
        }
    )

    result = store.record_content_research_packet(
        command.model_copy(update={"context_receipt": tampered_receipt})
    )

    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "evidence_not_bound"


def test_context_receipt_rejects_an_untrusted_typed_evidence_partition(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    command, source_pack = _packet_command(store, identity, legacy_exact=True)
    assert command.context_receipt is not None
    outside = "ev_outside_demand_partition"
    context = command.context_receipt.model_copy(
        update={
            "evidence_ids": tuple(sorted((*command.context_receipt.evidence_ids, outside))),
            "demand_evidence_ids": (outside,),
        }
    )
    result = store.record_content_research_packet(
        command.model_copy(
            update={
                "evidence_ids": tuple(sorted((*command.evidence_ids, outside))),
                "context_receipt": context,
            }
        )
    )

    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "evidence_not_bound"


def test_direct_reconciliation_rejects_context_cta_digest_drift(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _source_pack = _packet_command(store, identity, legacy_exact=True)
    assert command.context_receipt is not None
    tampered_receipt = command.context_receipt.model_copy(
        update={"cta_destination": "/inna/"}
    )

    result = store.record_content_research_packet(
        command.model_copy(update={"context_receipt": tampered_receipt})
    )

    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "context_receipt_mismatch"


def test_exact_packet_rejects_canonical_path_public_url_drift(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    packet = store.record_content_research_packet(command).packet
    payload = packet.model_dump(mode="json")
    payload.update({"canonical_path": "/inna-strona", "canonical_owner": "/inna-strona"})
    payload["packet_digest"] = research_packet_digest(payload)
    payload["packet_id"] = f"content_research_packet_{research_packet_logical_id(payload)[:24]}"

    with pytest.raises(ValueError, match="canonical path"):
        ContentResearchPacket.model_validate(payload)


def test_stale_freshness_is_a_typed_blocker(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    stale = tuple(item.model_copy(update={"status": "stale"}) for item in command.freshness)

    result = store.record_content_research_packet(
        _with_preparation_receipt(store, command.model_copy(update={"freshness": stale}))
    )

    assert result.status == "created"
    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "freshness_stale"


def test_missing_semantic_material_is_a_typed_blocker(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)

    result = store.record_content_research_packet(
        _with_preparation_receipt(store, command.model_copy(update={"intent": ""}))
    )

    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "intent_missing"


def test_unbound_source_fact_and_identity_mismatch_fail_closed(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    unbound = command.model_copy(
        update={
            "approved_source_fact_ids": tuple(
                sorted((*command.approved_source_fact_ids, "ekologus_missing_fact"))
            )
        }
    )
    identity_mismatch = command.model_copy(update={"identity_binding_digest": "a" * 64})

    unbound_result = store.record_content_research_packet(
        _with_preparation_receipt(store, unbound)
    )
    identity_result = store.record_content_research_packet(identity_mismatch)

    assert unbound_result.packet.blocker is not None
    assert unbound_result.packet.blocker.reason == "source_fact_not_bound"
    assert identity_result.packet.blocker is not None
    assert identity_result.packet.blocker.reason == "source_pack_identity_mismatch"


def test_source_pack_from_another_identity_is_a_typed_blocker(tmp_path: Path) -> None:
    store, first_identity = _setup_store(tmp_path)
    second_identity = store.record_content_delivery_identity(
        identity_command(retained=True)
    ).binding
    first_command, first_pack = _packet_command(store, first_identity)
    second_command, _ = _packet_command(store, second_identity)
    mixed = second_command.model_copy(
        update={
            "source_pack_binding_id": first_pack.binding_id,
            "source_pack_binding_digest": first_pack.binding_digest,
        }
    )

    result = store.record_content_research_packet(mixed)

    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "source_pack_identity_mismatch"
    assert first_command.source_pack_binding_id != second_command.source_pack_binding_id


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "//evil.example/path",
        "/%2e%2e/private/",
        "/%252e%252e/private/",
        "/%252f%252fevil.example/x",
    ],
)
def test_internal_link_rejects_protocol_relative_and_encoded_traversal(
    unsafe_path: str,
) -> None:
    with pytest.raises(ValueError, match="safe absolute path"):
        ContentResearchPacketInternalLink(
            destination_path=unsafe_path,
            anchor_text="Kontakt",
            relation="next_step",
            verification="exact_verified",
        )


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "//evil.example/path",
        "/%2e%2e/private/",
        "/%252e%252e/private/",
        "/%252f%252fevil.example/x",
    ],
)
def test_cta_rejects_protocol_relative_and_encoded_traversal(
    unsafe_path: str,
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)

    with pytest.raises(ValueError, match="safe absolute path"):
        ContentResearchPacketCommand.model_validate(
            command.model_dump(mode="json") | {"cta_destination": unsafe_path}
        )


def test_redaction_happens_before_packet_digesting(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)

    result = store.record_content_research_packet(
        _with_preparation_receipt(store, command.model_copy(update={"buyer_problem": "X" * 32}))
    )

    assert result.status == "created"
    assert result.packet.status == "exact_current"
    assert result.packet.buyer_problem == "[REDACTED]"


def test_redaction_preserves_safe_long_internal_path(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    long_path = "/oferta/" + "A" * 32 + "/"
    command, _ = _packet_command(
        store,
        identity,
        internal_links=(
            ContentResearchPacketInternalLink(
                destination_path=long_path,
                anchor_text="Oferta",
                relation="supporting",
                verification="exact_verified",
            ),
        ),
    )

    result = store.record_content_research_packet(command)

    assert result.status == "created"
    assert result.packet.internal_links[0].destination_path == long_path


def test_credential_like_packet_identifier_is_rejected_before_redaction(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity)
    payload = command.model_dump(mode="json")
    payload["recorded_by"] = "sk-" + "a" * 24

    with pytest.raises(ValueError, match="credential"):
        ContentResearchPacketCommand.model_validate(payload)


def test_credential_like_fact_and_freshness_ids_are_rejected() -> None:
    token = "gho_" + "a" * 24

    with pytest.raises(ValueError, match="credential"):
        ContentResearchPacketFreshness(
            source_id=token,
            evidence_ids=("ev_1",),
            checked_at=datetime.now(UTC),
            status="fresh",
        )
    assert redact_mapping({"source_id": token})["source_id"] == "[REDACTED]"


def test_long_approved_fact_identifier_survives_redaction_boundary(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity, legacy_exact=True)
    long_fact_id = "ekologus_" + "a" * 32 + "-v1"
    payload = command.model_dump(mode="json")
    payload["approved_source_fact_ids"] = sorted(
        (*command.approved_source_fact_ids, long_fact_id)
    )

    result = store.record_content_research_packet(
        _with_preparation_receipt(
            store,
            ContentResearchPacketCommand.model_validate(payload),
        )
    )

    assert result.status == "created"
    assert result.packet.status == "blocked"
    assert long_fact_id in result.packet.approved_source_fact_ids
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "source_fact_not_bound"


def test_packet_command_rejects_raw_payload_fields() -> None:
    with pytest.raises(ValueError):
        ContentResearchPacketCommand.model_validate(
            {
                "source_pack_binding_id": "pack",
                "source_pack_binding_digest": "a" * 64,
                "identity_binding_id": "identity",
                "identity_binding_digest": "b" * 64,
                "current_work_item_id": "work-item",
                "content_kind": "service",
                "recorded_by": "test_actor",
                "recorded_at": datetime.now(UTC),
                "extracted_fact": "raw vendor response",
            }
        )


def test_research_packet_routes_are_read_only_and_preserve_exact_get(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity)
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    client = TestClient(app)

    stored = store.record_content_research_packet(command)
    packet = stored.packet.model_dump(mode="json")
    assert stored.packet.status == "blocked"
    assert stored.packet.blocker is not None
    assert stored.packet.blocker.reason == "source_pack_binding_blocked"
    created = client.post(
        "/api/content/research-packets",
        json=command.model_dump(mode="json"),
    )
    assert created.status_code in {404, 405}
    readback = client.get(f"/api/content/research-packets/{packet['packet_id']}")

    assert readback.status_code == 200
    readback_payload = readback.json()
    assert readback_payload["status"] == "found"
    assert readback_payload["packet"] == packet
    assert readback_payload["current"]["status"] == "blocked"
    assert readback_payload["current"]["packet_id"] == packet["packet_id"]
    assert readback_payload["current"]["packet_digest"] == packet["packet_digest"]
    missing = client.get("/api/content/research-packets/content_research_packet_missing")
    assert missing.status_code == 404
    openapi = client.get("/openapi.json").json()
    assert "/api/content/research-packets" not in openapi["paths"]
    assert "get" in openapi["paths"]["/api/content/research-packets/{packet_id}"]
