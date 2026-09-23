from __future__ import annotations

import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import actions as actions_router
from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.actions import action_catalog
from wilq.actions import action_validation as action_validation_module
from wilq.actions import audit_store as action_audit_store
from wilq.actions import service as action_service
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow import current_page_evidence as current_evidence_domain
from wilq.content.workflow.current_page_disposition_v2 import (
    build_current_page_disposition_v2_proposal,
    build_current_page_disposition_v2_receipt,
)
from wilq.content.workflow.current_page_disposition_v2_action import (
    current_page_disposition_v2_action,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.store import store as workflow_store_module
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION


def _evidence(
    digest: str = "a" * 64, *, observation: str = "current"
) -> CurrentPageEvidenceResponse:
    return CurrentPageEvidenceResponse(
        status="reviewed_material_current",
        decision="Materiał ma aktualne review.",
        work_item_id="wi_source_authority_v2",
        page_url="https://www.ekologus.pl/authority-v2/",
        material_meaning_digest=digest,
        current_evidence_ids=[f"wp_{observation}"],
        catalog_evidence_ids=[f"catalog_{observation}"],
        safe_next_step="Sprawdź exact materiał.",
    )


def _fact(*, changed: bool = False) -> ContentSourceFact:
    return ContentSourceFact(
        source_id="approved_fact",
        source_type="public_site",
        privacy_class="commit_safe",
        source_url_or_path="https://www.ekologus.pl/authority-v2/",
        extracted_fact=("Changed approved fact." if changed else "Approved synthetic fact."),
        scope="service",
        freshness_date="2026-09-23",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["fact_evidence"],
        source_connectors=["wordpress_ekologus"],
        target_card_id="authority_v2_service",
        target_card_type="service",
        target_card_title="Authority v2 service",
    )


def _unrelated_fact() -> ContentSourceFact:
    return ContentSourceFact.model_validate(
        _fact().model_dump(mode="json")
        | {
            "source_id": "unrelated_fact",
            "source_url_or_path": "https://www.ekologus.pl/other/",
            "target_card_id": "other_service",
            "evidence_ids": ["unrelated_evidence"],
        }
    )


def _card() -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id="authority_v2_service",
        card_type="service",
        title="Synthetic exact service card",
        summary="Synthetic exact page binding.",
        service_binding_urls=["https://www.ekologus.pl/authority-v2/"],
        source_fact_ids=["approved_fact"],
        evidence_ids=["service_card_evidence"],
        source_connectors=["synthetic_service_card"],
        lifecycle_status="approved_current",
        confidence=0.9,
        freshness="2026-09-23",
    )


def _legal_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="unprofiled_legal_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://eli.gov.pl/act/synthetic",
        extracted_fact="Synthetic official requirement.",
        scope="claim_policy",
        freshness_date="2026-09-23",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["legal_fact_evidence"],
        source_connectors=["official_regulatory_review"],
        target_card_id="authority_v2_service",
        target_card_type="regulatory_source",
        target_card_title="Synthetic regulatory source",
        official_source=True,
        regulatory_profile_id="synthetic_regulatory_profile",
        regulatory_profile_version="synthetic-v1",
        regulatory_requirement_ids=["synthetic_requirement"],
        applicable_canonical_paths=["/authority-v2"],
    )


def _seed_keep(store: ContentWorkflowStore, evidence: CurrentPageEvidenceResponse) -> None:
    proposal = build_current_page_disposition_v2_proposal(evidence)
    store.record_current_page_disposition_v2_proposal(proposal)
    receipt = build_current_page_disposition_v2_receipt(
        action=current_page_disposition_v2_action(proposal),
        proposal=proposal,
        preview_audit_id="keep_preview",
        review_audit_id="keep_review",
        confirmation_audit_id="keep_confirm",
        impact_audit_id="keep_impact",
        reviewed_by="synthetic_wilku",
        confirmed_by="synthetic_wilku",
        verification_evidence_ids=("keep_apply_catalog", "keep_apply_wp"),
        verified_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    store.record_current_page_disposition_v2_receipt(receipt)


def _runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    TestClient,
    ContentWorkflowStore,
    LocalStateStore,
    dict[str, CurrentPageEvidenceResponse],
    dict[str, tuple[ContentSourceFact, ...]],
]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    current = {"evidence": _evidence()}
    facts: dict[str, tuple[ContentSourceFact, ...]] = {"value": (_fact(),)}
    monkeypatch.setattr(
        content_current_page_evidence,
        "read_current_page_evidence",
        lambda *, work_item_id: current["evidence"],
    )
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(action_catalog, "content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(action_audit_store, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(action_validation_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(actions_router, "local_state_store", lambda: audit_store)
    authority_router = sys.modules.get("apps.api.wilq_api.routers.content_source_fact_authority_v2")
    authority_module = sys.modules.get("wilq.content.workflow.source_fact_authority_v2")
    if authority_router is not None:
        monkeypatch.setattr(authority_router, "content_workflow_store", lambda: store)
    if authority_module is not None:
        monkeypatch.setattr(authority_module, "ekologus_source_facts", lambda: facts["value"])
        monkeypatch.setattr(
            authority_module, "ekologus_content_knowledge_cards", lambda: (_card(),)
        )
    monkeypatch.setattr(
        current_evidence_domain, "read_current_page_evidence_current", lambda _: current["evidence"]
    )
    _seed_keep(store, current["evidence"])
    return TestClient(app), store, audit_store, current, facts


def _preview(client: TestClient, store: ContentWorkflowStore) -> tuple[str, dict[str, Any]]:
    keep = store.load_latest_current_page_disposition_v2_receipt_for_work_item(
        "wi_source_authority_v2"
    )
    assert keep is not None
    response = client.post(
        "/api/content/source-fact-authorities/preview",
        json={
            "work_item_id": "wi_source_authority_v2",
            "expected_keep_receipt_id": keep.receipt_id,
            "expected_keep_receipt_digest": keep.receipt_digest,
            "expected_material_meaning_digest": keep.snapshot.material_meaning_digest,
            "source_fact_ids": ["approved_fact"],
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "preview_ready"
    return payload["action_id"], payload


def _run_lifecycle(client: TestClient, action_id: str) -> None:
    action_detail = client.get(f"/api/actions/{action_id}")
    assert action_detail.status_code == 200, action_detail.text
    validation = client.post(f"/api/actions/{action_id}/validate")
    assert validation.status_code == 200, validation.text
    assert validation.json()["valid"] is True, validation.text
    preview = client.post(f"/api/actions/{action_id}/preview", json={})
    assert preview.status_code == 200, preview.text
    review = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "synthetic_wilku",
            "notes": "Sprawdzono exact wybrane źródła.",
        },
    )
    assert review.status_code == 200, review.text
    confirmation = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "synthetic_wilku",
            "notes": "Potwierdzam lokalny receipt.",
            "preview_acknowledged": True,
        },
    )
    assert confirmation.status_code == 200, confirmation.text
    impact = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={"checked_by": "synthetic_wilku", "notes": "Sprawdzono wpływ lokalny."},
    )
    assert impact.status_code == 200, impact.text


@pytest.mark.parametrize(
    "drift",
    ["none", "evidence_rotation", "unrelated_registry", "material", "registry", "audit_binding"],
)
def test_public_v2_authority_requires_exact_keep_reviewed_facts_and_no_vendor_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    client, store, audit_store, current, facts = _runtime(tmp_path, monkeypatch)
    action_id, preview_payload = _preview(client, store)
    action = preview_payload["action"]
    assert action["payload"]["source_fact_authority_v2"]["snapshot"]["keep_receipt_id"]
    _run_lifecycle(client, action_id)

    if drift == "material":
        current["evidence"] = _evidence("c" * 64)
    elif drift == "registry":
        facts["value"] = (_fact(changed=True),)
    elif drift == "evidence_rotation":
        current["evidence"] = _evidence(observation="rotated")
        assert _preview(client, store)[0] == action_id
    elif drift == "unrelated_registry":
        facts["value"] = (_fact(), _unrelated_fact())
        assert _preview(client, store)[0] == action_id
    elif drift == "audit_binding":
        events = audit_store.list_audit_events(action_id=action_id)
        preview_event = next(
            event for event in events if event.event_type == "action_preview_generated"
        )
        preview_event.details["source_fact_authority_v2_action_payload_digest"] = "f" * 64
        audit_store.save_audit_event(preview_event)

    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic_wilku"},
    )
    receipt = store.load_source_fact_authority_v2_receipt(action_id)
    if drift in {"none", "evidence_rotation", "unrelated_registry"}:
        assert applied.status_code == 200, applied.text
        assert applied.json()["applied"] is True
        assert applied.json()["adapter_result"]["external_write_attempted"] is False
        assert receipt is not None
        if drift == "evidence_rotation":
            assert receipt.verification_evidence_ids == (
                "catalog_rotated",
                "wp_rotated",
            )
        if drift == "unrelated_registry":
            assert receipt.verification_registry_digest != receipt.snapshot.registry_digest
        assert (
            receipt.snapshot.keep_receipt_id
            == action["payload"]["source_fact_authority_v2"]["snapshot"]["keep_receipt_id"]
        )
        readback = client.get(f"/api/content/source-fact-authorities/{action_id}")
        assert readback.status_code == 200, readback.text
        assert readback.json()["status"] == "current"
        assert readback.json()["receipt"]["receipt_id"] == receipt.receipt_id
        assert len(audit_store.list_audit_events(action_id=action_id)) >= 5
        preview_event = next(
            event
            for event in audit_store.list_audit_events(action_id=action_id)
            if event.event_type == "action_preview_generated"
        )
        assert (
            preview_event.details["source_fact_authority_v2_snapshot_digest"]
            == action["payload"]["source_fact_authority_v2"]["snapshot"]["context_digest"]
        )
        assert preview_event.details["source_fact_authority_v2_action_payload_digest"]
        assert "snapshot" not in preview_event.details
    else:
        assert applied.status_code == 409, applied.text
        assert receipt is None
        assert "apply_blocked" in {
            event.event_type for event in audit_store.list_audit_events(action_id=action_id)
        }


def test_public_v2_authority_schema_migrates_v11_keep_readback_and_new_store(
    tmp_path: Path,
) -> None:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    evidence = _evidence()
    _seed_keep(store, evidence)
    with store._connect() as connection:
        trigger_names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND name LIKE 'content_source_fact_authority_v2_%'"
            )
        ]
        for trigger_name in trigger_names:
            connection.execute(f'DROP TRIGGER "{trigger_name}"')
        connection.execute("DROP TABLE content_source_fact_authority_v2_receipts")
        connection.execute("DROP TABLE content_source_fact_authority_v2_proposals")
        connection.execute("PRAGMA user_version = 11")
    reopened = ContentWorkflowStore(store.path)
    receipt = reopened.load_latest_current_page_disposition_v2_receipt_for_work_item(
        "wi_source_authority_v2"
    )
    assert receipt is not None
    assert receipt.snapshot.disposition == "keep"
    with reopened._connect() as connection:
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'content_source_fact_authority_v2_receipts'"
            ).fetchone()
            is not None
        )
        assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == SQLITE_SCHEMA_VERSION

    fresh = ContentWorkflowStore(tmp_path / "fresh.sqlite3")
    assert fresh.load_source_fact_authority_v2_proposal("absent") is None

    newer_path = tmp_path / "newer.sqlite3"
    with sqlite3.connect(newer_path) as connection:
        connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION + 1}")
    newer = ContentWorkflowStore(newer_path)
    with pytest.raises(RuntimeError, match="newer than supported"):
        newer._connect()
    with sqlite3.connect(newer_path) as connection:
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'content_source_fact_authority_v2_receipts'"
            ).fetchone()
            is None
        )


def test_public_legal_update_without_current_regulatory_profile_is_blocked_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, store, _, _, facts = _runtime(tmp_path, monkeypatch)
    facts["value"] = (_legal_fact(),)
    keep = store.load_latest_current_page_disposition_v2_receipt_for_work_item(
        "wi_source_authority_v2"
    )
    assert keep is not None
    response = client.post(
        "/api/content/source-fact-authorities/preview",
        json={
            "work_item_id": "wi_source_authority_v2",
            "expected_keep_receipt_id": keep.receipt_id,
            "expected_keep_receipt_digest": keep.receipt_digest,
            "expected_material_meaning_digest": keep.snapshot.material_meaning_digest,
            "source_fact_ids": ["unprofiled_legal_fact"],
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["status"] == "blocked"
    assert response.json()["blocker_code"] == "regulatory_source_policy_not_current"
    assert response.json()["blocker_owner"] == "WILQ content workflow"
    assert response.json()["blocker_evidence_ids"] == ["legal_fact_evidence"]
    assert "profil" in response.json()["safe_next_step"]
    with store._connect() as connection:
        proposals = connection.execute(
            "SELECT count(*) FROM content_source_fact_authority_v2_proposals"
        ).fetchone()[0]
        receipts = connection.execute(
            "SELECT count(*) FROM content_source_fact_authority_v2_receipts"
        ).fetchone()[0]
    assert proposals == 0
    assert receipts == 0


def test_public_scoped_fact_review_blocker_keeps_human_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, store, _, _, facts = _runtime(tmp_path, monkeypatch)
    facts["value"] = (
        ContentSourceFact.model_validate(
            _fact().model_dump(mode="json") | {"review_status": "review_required"}
        ),
    )
    keep = store.load_latest_current_page_disposition_v2_receipt_for_work_item(
        "wi_source_authority_v2"
    )
    assert keep is not None
    response = client.post(
        "/api/content/source-fact-authorities/preview",
        json={
            "work_item_id": "wi_source_authority_v2",
            "expected_keep_receipt_id": keep.receipt_id,
            "expected_keep_receipt_digest": keep.receipt_digest,
            "expected_material_meaning_digest": keep.snapshot.material_meaning_digest,
            "source_fact_ids": ["approved_fact"],
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["blocker_code"] == "source_fact_review_required"
    assert response.json()["blocker_owner"] == "Wilku"
    assert "fact_evidence" in response.json()["blocker_evidence_ids"]


@pytest.mark.parametrize("freshness_date", ["unknown", "2100-01-01"])
def test_public_invalid_or_future_source_freshness_blocks_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    freshness_date: str,
) -> None:
    client, store, _, _, facts = _runtime(tmp_path, monkeypatch)
    facts["value"] = (
        ContentSourceFact.model_validate(
            _fact().model_dump(mode="json") | {"freshness_date": freshness_date}
        ),
    )
    keep = store.load_latest_current_page_disposition_v2_receipt_for_work_item(
        "wi_source_authority_v2"
    )
    assert keep is not None
    response = client.post(
        "/api/content/source-fact-authorities/preview",
        json={
            "work_item_id": "wi_source_authority_v2",
            "expected_keep_receipt_id": keep.receipt_id,
            "expected_keep_receipt_digest": keep.receipt_digest,
            "expected_material_meaning_digest": keep.snapshot.material_meaning_digest,
            "source_fact_ids": ["approved_fact"],
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["blocker_code"] == "source_fact_freshness_invalid"
    assert response.json()["blocker_owner"] == "WILQ content workflow"
    assert "fact_evidence" in response.json()["blocker_evidence_ids"]
    assert "dat" in response.json()["safe_next_step"]
    assert store.load_latest_source_fact_authority_v2_receipt_for_work_item(
        "wi_source_authority_v2"
    ) is None
