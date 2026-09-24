from __future__ import annotations

import importlib
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.actions import create_actions_router
from apps.api.wilq_api.routers.content_planning_generation_intent import (
    register_content_planning_generation_intent_routes,
)
from tests.content.test_material_review_action_v2 import _configure_local_action_runtime
from tests.content.test_research_packet_v2_preview import _ready_inputs
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generation_intent import PlanningGenerationIntentSnapshot
from wilq.content.planning.input_sources import ContentPlanningInventory, ContentPlanningSourceFact
from wilq.content.planning.packet_input_binding import bind_packet_identity_to_planning_input
from wilq.content.planning.source_pack_projection import project_research_packet_v2_facts
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v2_preview import (
    ResearchPacketV2Preview,
    build_research_packet_v2_preview,
)
from wilq.content.workflow.research_packet_v2_receipt import (
    ResearchPacketV2ApprovalReceipt,
    ResearchPacketV2PreviewRecord,
)
from wilq.content.workflow.source_pack_v2 import SourcePackV2Fact, SourcePackV2Preview
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


def _approved_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="fact_exact",
        source_type="public_site",
        privacy_class="commit_safe",
        source_url_or_path="https://example.test/source",
        extracted_fact="Zatwierdzony fakt.",
        scope="service",
        freshness_date="2026-09-23",
        confidence=0.95,
        review_status="approved",
        reviewer="synthetic-reviewer",
        evidence_ids=["ev_exact"],
        source_connectors=["official_regulatory_review"],
        target_card_id="card_exact",
        target_card_type="service",
        target_card_title="Exact service",
    )


def _packet_fixture(
    store: ContentWorkflowStore,
) -> tuple[ResearchPacketV2Preview, ContentPlanningInput, ContentSourceFact]:
    source_pack, raw_input = _ready_inputs()
    raw_input = raw_input.model_copy(
        update={
            "confirmed_service_card_id": "card_exact",
            "source_facts": [
                ContentPlanningSourceFact(
                    fact_id="caller_fact",
                    summary="Caller supplied, unreviewed claim.",
                    source_connector="caller_connector",
                    evidence_ids=["ev_caller_only"],
                    source_fact_ids=["fact_unreviewed"],
                    source_material_ids=[],
                    regulatory_requirement_ids=[],
                )
            ],
            "evidence_ids": ["ev_exact", "ev_caller_only"],
            "source_connectors": ["caller_connector"],
            "inventory": ContentPlanningInventory(status="available"),
            "source_assessments": [],
            "query_portfolio": ContentSearchDemandEvidence(
                status="missing",
                optional_ads_status="not_exactly_mapped",
                safe_next_step="Use only exact packet facts.",
            ),
            "measurement_baseline_evidence_ids": [],
            "measurement_observation_rule": "Observe exact baseline.",
            "measurement_success_claim_rule": "Do not claim unmeasured impact.",
        }
    )
    fact = _approved_fact()
    source_fact = SourcePackV2Fact(
        source_fact_id=fact.source_id,
        fact_digest=canonical_json_digest(fact.model_dump(mode="json")),
        text=fact.extracted_fact,
        source_reference=fact.source_url_or_path,
        freshness_date=fact.freshness_date,
        source_type=fact.source_type,
        source_connectors=tuple(fact.source_connectors),
        evidence_ids=tuple(fact.evidence_ids),
    )
    semantic_seed = source_pack.model_copy(update={"facts": (source_fact,)})
    pack_digest = canonical_json_digest(semantic_seed.semantic_payload())
    source_pack = SourcePackV2Preview.model_validate(
        semantic_seed.model_dump(mode="python")
        | {"source_pack_id": f"source_pack_v2_{pack_digest}", "source_pack_hash": pack_digest}
    )
    preview = build_research_packet_v2_preview(
        "wi_exact", source_pack=source_pack, planning_input=raw_input
    )
    assert preview.status == "ready" and preview.preview_hash is not None, (
        None if preview.blocker is None else (preview.blocker.code, preview.blocker.owner)
    )
    record = ResearchPacketV2PreviewRecord.from_preview(preview)
    assert store.record_research_packet_v2_preview(record) == "created"
    receipt = ResearchPacketV2ApprovalReceipt.from_action_chain(
        preview_hash=preview.preview_hash,
        action_id=f"act_content_research_packet_v2_{preview.preview_hash}",
        action_payload_digest="1" * 64,
        preview_audit_event_id="synthetic-preview",
        review_audit_event_id="synthetic-review",
        confirmation_audit_event_id="synthetic-confirmation",
        impact_audit_event_id="synthetic-impact",
        review_actor="synthetic-reviewer",
        approved_at=datetime.now(UTC),
    )
    assert store._record_research_packet_v2_approval_receipt(receipt) == "created"
    return preview, raw_input, fact


def _client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[
    TestClient,
    ContentWorkflowStore,
    ResearchPacketV2Preview,
    ContentPlanningInput,
    dict[str, ContentSourceFact],
]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    preview, raw_input, fact = _packet_fixture(store)
    registry = {"fact": fact}
    generation = importlib.import_module("wilq.content.planning.generation_intent")
    resolver = importlib.import_module("wilq.content.planning.approved_packet_v2")
    real_resolver = resolver.resolve_approved_packet_v2_for_planning
    monkeypatch.setattr(generation, "ekologus_source_facts", lambda: (registry["fact"],))
    monkeypatch.setattr(generation, "current_planning_input", lambda *_args, **_kwargs: raw_input)

    def resolve_with_synthetic_current_preview(**kwargs: object) -> object:
        values = dict(kwargs)
        values["current_preview_loader"] = lambda _item, _input: preview
        return real_resolver(**values)

    monkeypatch.setattr(
        generation,
        "resolve_approved_packet_v2_for_planning",
        resolve_with_synthetic_current_preview,
    )
    actions_module = importlib.import_module("apps.api.wilq_api.routers.actions")
    monkeypatch.setattr(
        actions_module,
        "_planning_generation_snapshot_loader",
        lambda: cast(
            Callable[[str], ContentWorkItemWorkflowSnapshotResponse],
            lambda _work_item_id: None,
        ),
    )
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    _configure_local_action_runtime(monkeypatch, store, audit_store)
    app = FastAPI()
    register_content_planning_generation_intent_routes(
        app.router,
        snapshot_loader=cast(
            Callable[[str], ContentWorkItemWorkflowSnapshotResponse],
            lambda _work_item_id: None,
        ),
        store_factory=lambda: store,
        current_preview_loader=lambda _work_item_id: preview,
    )
    app.include_router(create_actions_router(lambda: None))
    return TestClient(app), store, preview, raw_input, registry


def _lifecycle(
    client: TestClient,
    action_id: str,
    *,
    before_apply: Callable[[], None] | None = None,
) -> dict[str, object]:
    validation = client.post(f"/api/actions/{action_id}/validate")
    assert validation.status_code == 200 and validation.json()["valid"] is True
    assert client.post(f"/api/actions/{action_id}/preview", json={}).status_code == 200
    review = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "synthetic-reviewer",
            "notes": "Synthetic exact intent review.",
            "checked_items": ["reviewed_exact_generation_intent"],
        },
    )
    assert review.status_code == 200, review.text
    confirmation = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "synthetic-reviewer",
            "notes": "Exact local intent.",
            "preview_acknowledged": True,
        },
    )
    assert confirmation.status_code == 200, confirmation.text
    impact = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={"checked_by": "synthetic-reviewer", "notes": "No external write."},
    )
    assert impact.status_code == 200, impact.text
    if before_apply is not None:
        before_apply()
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic-reviewer"},
    )
    assert applied.status_code in {200, 409}, applied.text
    payload = applied.json()
    return cast(dict[str, object], payload.get("detail", payload))


def _preview_digest(preview: ResearchPacketV2Preview) -> str:
    if preview.preview_hash is None:
        raise AssertionError("Synthetic fixture requires a ready packet preview.")
    return preview.preview_hash


def test_public_generation_intent_records_only_exact_local_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, preview, raw_input, registry = _client(tmp_path, monkeypatch)
    fact = registry["fact"]
    projected = project_research_packet_v2_facts(raw_input, preview.selected_facts, (fact,))
    bound = bind_packet_identity_to_planning_input(
        projected,
        work_item_id="wi_exact",
        packet_id=f"content_research_packet_v2_{_preview_digest(preview)[:24]}",
        packet_digest=_preview_digest(preview),
    )
    request = {
        "content_kind": "service",
        "service_card_id": "card_exact",
        "packet_id": f"content_research_packet_v2_{_preview_digest(preview)[:24]}",
        "packet_digest": _preview_digest(preview),
        "expected_raw_planning_input_digest": raw_input.planning_input_digest,
        "expected_projected_planning_input_digest": bound.planning_input_digest,
    }
    prepared = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent/preview", json=request
    )
    assert prepared.status_code == 200, prepared.text
    action_id = prepared.json()["action_id"]
    assert prepared.json()["snapshot"]["schema_version"] == (
        "wilq_planning_generation_intent_snapshot_v2"
    )
    assert prepared.json()["snapshot"]["dispatch_after_apply_audit"] is True
    assert prepared.json()["action"]["payload"]["dispatch_after_apply_audit"] is True
    assert prepared.json()["action"]["payload"]["model_enqueued_at_apply"] is False
    legacy_snapshot = dict(prepared.json()["snapshot"])
    legacy_snapshot["schema_version"] = "wilq_planning_generation_intent_snapshot_v1"
    legacy_snapshot.pop("dispatch_after_apply_audit")
    with pytest.raises(ValueError):
        PlanningGenerationIntentSnapshot.model_validate(legacy_snapshot)
    assert prepared.json()["generation_performed"] is False
    assert prepared.json()["model_enqueued"] is False
    assert "Zatwierdzony fakt." not in prepared.text
    readback = client.get(
        f"/api/content/work-items/wi_exact/planning-generation-intent/{action_id}"
    )
    assert readback.status_code == 200, readback.text
    applied = _lifecycle(client, action_id)
    assert applied["applied"] is True, applied
    adapter_result = applied["adapter_result"]
    assert isinstance(adapter_result, dict)
    assert adapter_result["generation_performed"] is False
    assert adapter_result["model_enqueued"] is False
    assert adapter_result["external_write_attempted"] is False
    receipt = store.load_planning_generation_intent_receipt(action_id)
    assert receipt is not None
    assert receipt.snapshot.packet_digest == preview.preview_hash
    assert receipt.snapshot.raw_planning_input_digest == raw_input.planning_input_digest
    assert receipt.snapshot.projected_planning_input_digest == bound.planning_input_digest
    assert receipt.created_at.tzinfo is not None
    assert store.record_planning_generation_intent_receipt(receipt) == "idempotent"


def test_public_generation_intent_blocks_arbitrary_unapproved_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, _preview, raw_input, _registry = _client(tmp_path, monkeypatch)
    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent/preview",
        json={
            "content_kind": "service",
            "service_card_id": "card_exact",
            "packet_id": "content_research_packet_v2_" + "a" * 24,
            "packet_digest": "a" * 64,
            "expected_raw_planning_input_digest": raw_input.planning_input_digest,
            "expected_projected_planning_input_digest": "c" * 64,
        },
    )
    assert response.status_code == 409
    assert response.json()["blocker_code"] == "research_packet_v2_approval_missing"
    assert (
        store.load_planning_generation_intent_receipt("act_content_planning_generation_intent_bad")
        is None
    )


def test_public_generation_intent_stale_selected_fact_blocks_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, preview, raw_input, registry = _client(tmp_path, monkeypatch)
    current_fact = registry["fact"]
    projected = project_research_packet_v2_facts(raw_input, preview.selected_facts, (current_fact,))
    bound = bind_packet_identity_to_planning_input(
        projected,
        work_item_id="wi_exact",
        packet_id=f"content_research_packet_v2_{_preview_digest(preview)[:24]}",
        packet_digest=_preview_digest(preview),
    )
    prepared = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent/preview",
        json={
            "content_kind": "service",
            "service_card_id": "card_exact",
            "packet_id": f"content_research_packet_v2_{_preview_digest(preview)[:24]}",
            "packet_digest": _preview_digest(preview),
            "expected_raw_planning_input_digest": raw_input.planning_input_digest,
            "expected_projected_planning_input_digest": bound.planning_input_digest,
        },
    )
    assert prepared.status_code == 200, prepared.text
    action_id = prepared.json()["action_id"]

    def drift_selected_fact() -> None:
        registry["fact"] = current_fact.model_copy(
            update={"extracted_fact": "Changed source text."}
        )

    applied = _lifecycle(client, action_id, before_apply=drift_selected_fact)
    assert applied["applied"] is False
    blocked_result = applied["adapter_result"]
    assert isinstance(blocked_result, dict)
    blocker = blocked_result["blocker"]
    assert isinstance(blocker, dict)
    assert blocker["code"] == "selected_packet_fact_not_current"
    assert blocker["owner"] == "WILQ content workflow"
    assert blocker["evidence_ids"] == ["ev_caller_only", "ev_exact"]
    assert blocker["safe_next_step"]
    assert blocker["external_write_attempted"] is False
    assert store.load_planning_generation_intent_receipt(action_id) is None


def test_generation_intent_schema_migrates_v13_and_refuses_newer_db(tmp_path: Path) -> None:
    store = ContentWorkflowStore(tmp_path / "migration.sqlite3")
    connection = store._connect()
    try:
        triggers = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' "
            "AND name LIKE 'content_planning_generation_intent_%'"
        ).fetchall()
        for (name,) in triggers:
            connection.execute(f'DROP TRIGGER "{name}"')
        connection.execute("DROP TABLE content_planning_generation_intent_receipts")
        connection.execute("DROP TABLE content_planning_generation_intent_proposals")
        connection.execute("PRAGMA user_version = 13")
    finally:
        connection.close()

    migrated = store._connect()
    try:
        tables = {
            row[0]
            for row in migrated.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        version = migrated.execute("PRAGMA user_version").fetchone()[0]
    finally:
        migrated.close()
    assert version == 14
    assert "content_planning_generation_intent_proposals" in tables
    assert "content_planning_generation_intent_receipts" in tables

    newer_path = tmp_path / "newer.sqlite3"
    with sqlite3.connect(newer_path) as newer:
        newer.execute("PRAGMA user_version = 15")
    with pytest.raises(RuntimeError, match="newer than supported"):
        ContentWorkflowStore(newer_path)._connect()
    with sqlite3.connect(newer_path) as newer:
        assert newer.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'content_planning_generation_intent_proposals'"
        ).fetchone() is None
