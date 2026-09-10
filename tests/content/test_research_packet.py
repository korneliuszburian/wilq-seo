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
    ContentResearchPacketCommand,
    ContentResearchPacketFreshness,
    ContentResearchPacketInternalLink,
)
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION


def _packet_command(store, identity, *, now: datetime | None = None, **updates: object):
    source_pack = store.record_content_source_pack_binding(_source_command(identity)).binding
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
    payload.update(updates)
    return ContentResearchPacketCommand.model_validate(payload), source_pack


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
    command, source_pack = _packet_command(store, identity)

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


def test_stale_freshness_is_a_typed_blocker(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity)
    stale = tuple(item.model_copy(update={"status": "stale"}) for item in command.freshness)

    result = store.record_content_research_packet(command.model_copy(update={"freshness": stale}))

    assert result.status == "created"
    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "freshness_stale"


def test_missing_semantic_material_is_a_typed_blocker(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity)

    result = store.record_content_research_packet(command.model_copy(update={"intent": ""}))

    assert result.packet.status == "blocked"
    assert result.packet.blocker is not None
    assert result.packet.blocker.reason == "intent_missing"


def test_unbound_source_fact_and_identity_mismatch_fail_closed(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity)
    unbound = command.model_copy(
        update={
            "approved_source_fact_ids": tuple(
                sorted((*command.approved_source_fact_ids, "ekologus_missing_fact"))
            )
        }
    )
    identity_mismatch = command.model_copy(update={"identity_binding_digest": "a" * 64})

    unbound_result = store.record_content_research_packet(unbound)
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
    command, _ = _packet_command(store, identity)

    with pytest.raises(ValueError, match="safe absolute path"):
        ContentResearchPacketCommand.model_validate(
            command.model_dump(mode="json") | {"cta_destination": unsafe_path}
        )


def test_redaction_happens_before_packet_digesting(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity)

    result = store.record_content_research_packet(
        command.model_copy(update={"buyer_problem": "X" * 32})
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


def test_long_approved_fact_identifier_survives_redaction_boundary(tmp_path: Path) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity)
    long_fact_id = "ekologus_" + "a" * 32 + "-v1"
    payload = command.model_dump(mode="json")
    payload["approved_source_fact_ids"] = sorted(
        (*command.approved_source_fact_ids, long_fact_id)
    )

    result = store.record_content_research_packet(
        ContentResearchPacketCommand.model_validate(payload)
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


def test_research_packet_routes_record_and_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    command, _ = _packet_command(store, identity)
    monkeypatch.setattr(route_module, "content_workflow_store", lambda: store)
    client = TestClient(app)

    created = client.post(
        "/api/content/research-packets",
        json=command.model_dump(mode="json"),
    )
    assert created.status_code == 201
    packet = created.json()["packet"]
    readback = client.get(f"/api/content/research-packets/{packet['packet_id']}")

    assert readback.status_code == 200
    assert readback.json() == {"status": "found", "packet": packet}
    missing = client.get("/api/content/research-packets/content_research_packet_missing")
    assert missing.status_code == 404
    openapi = client.get("/openapi.json").json()
    post_response = openapi["paths"]["/api/content/research-packets"]["post"]["responses"]["201"]
    assert post_response["content"]["application/json"]["schema"]["$ref"].endswith(
        "ContentResearchPacketRecordResult"
    )
