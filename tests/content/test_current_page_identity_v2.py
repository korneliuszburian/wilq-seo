from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_current_page_evidence
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.workflow.current_disposition_authority import (
    ContentCurrentDispositionCandidate,
    ContentCurrentDispositionReceipt,
    build_current_disposition_action,
    build_current_disposition_snapshot,
)
from wilq.content.workflow.current_page_disposition_v2 import (
    CurrentPageDispositionV2Proposal,
    build_current_page_disposition_v2_proposal,
    build_current_page_disposition_v2_receipt,
)
from wilq.content.workflow.current_page_disposition_v2_action import (
    current_page_disposition_v2_action,
)
from wilq.content.workflow.current_page_evidence import (
    CurrentPageEvidenceBlockerCode,
    CurrentPageEvidenceResponse,
)
from wilq.content.workflow.store import store as workflow_store_module
from wilq.content.workflow.store.store import ContentWorkflowStore


def _evidence(
    work_item_id: str,
    digest: str,
    current_ids: list[str],
    catalog_ids: list[str],
    page_url: str | None = None,
) -> CurrentPageEvidenceResponse:
    page = "a" if work_item_id == "wi_a" else "b"
    return CurrentPageEvidenceResponse(
        status="reviewed_material_current",
        decision="Materiał ma aktualne review.",
        work_item_id=work_item_id,
        page_url=page_url or f"https://www.ekologus.pl/{page}/",
        material_meaning_digest=digest,
        current_evidence_ids=current_ids,
        catalog_evidence_ids=catalog_ids,
        safe_next_step="Sprawdź dokładny adres.",
    )


def _seed_approved_receipt(
    store: ContentWorkflowStore,
    proposal: CurrentPageDispositionV2Proposal,
) -> tuple[str, str]:
    action = current_page_disposition_v2_action(proposal)
    store.record_current_page_disposition_v2_proposal(proposal)
    receipt = build_current_page_disposition_v2_receipt(
        action=action,
        proposal=proposal,
        preview_audit_id=f"preview_{proposal.snapshot.work_item_id}",
        review_audit_id=f"review_{proposal.snapshot.work_item_id}",
        confirmation_audit_id=f"confirm_{proposal.snapshot.work_item_id}",
        impact_audit_id=f"impact_{proposal.snapshot.work_item_id}",
        reviewed_by="synthetic_wilku",
        confirmed_by="synthetic_wilku",
        verification_evidence_ids=("apply_catalog", "apply_wp"),
        verified_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    store.record_current_page_disposition_v2_receipt(receipt)
    return proposal.proposal_id, receipt.receipt_id


def _assert_v1_receipt_stays_on_v1_route(
    client: TestClient,
    store: ContentWorkflowStore,
    current: dict[str, CurrentPageEvidenceResponse],
) -> None:
    run = exact_public_bdo_run()
    store.record_production_classification(run)
    work_item_id = run.rows[0].current_work_item_id
    page_url = run.rows[0].public_url
    assert work_item_id is not None and page_url is not None
    candidate = ContentCurrentDispositionCandidate(
        current_work_item_id=work_item_id,
        proposed_final_disposition="keep",
    )
    proposal = store.record_content_current_disposition_proposal(candidate)
    snapshot = build_current_disposition_snapshot(store, candidate)
    receipt = ContentCurrentDispositionReceipt.create(
        action=build_current_disposition_action(snapshot),
        snapshot=snapshot,
        preview_audit_id="legacy_preview",
        review_audit_id="legacy_review",
        confirmation_audit_id="legacy_confirmation",
        impact_audit_id="legacy_impact",
        reviewed_by="synthetic_wilku",
        confirmed_by="synthetic_wilku",
    )
    store.record_content_current_disposition_receipt(receipt)
    legacy_read = client.get(
        f"/api/content/current-disposition-authorities/{proposal.action_id}"
    )
    assert legacy_read.status_code == 200
    assert legacy_read.json()["receipt"]["receipt_id"] == receipt.receipt_id
    current[work_item_id] = CurrentPageEvidenceResponse(
        status="reviewed_material_current",
        decision="Materiał ma aktualne review.",
        work_item_id=work_item_id,
        page_url=page_url,
        material_meaning_digest="d" * 64,
        current_evidence_ids=["legacy_wp"],
        catalog_evidence_ids=["legacy_catalog"],
        safe_next_step="Sprawdź dokładny adres.",
    )
    v2_read = client.get(f"/api/content/work-items/{work_item_id}/current-identity")
    assert v2_read.status_code == 200, v2_read.text
    assert v2_read.json()["blocker_code"] == "missing_approved_keep_receipt"


@pytest.fixture
def identity_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, ContentWorkflowStore, dict[str, CurrentPageEvidenceResponse]]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    current = {
        "wi_a": _evidence("wi_a", "a" * 64, ["wp_a_1"], ["catalog_1"]),
        "wi_b": _evidence("wi_b", "b" * 64, ["wp_b_1"], ["catalog_1"]),
    }
    monkeypatch.setattr(
        content_current_page_evidence,
        "read_current_page_evidence",
        lambda *, work_item_id: current[work_item_id],
    )
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    content_current_page_identity_v2 = sys.modules.get(
        "apps.api.wilq_api.routers.content_current_page_identity_v2"
    )
    if content_current_page_identity_v2 is not None:
        monkeypatch.setattr(
            content_current_page_identity_v2,
            "content_workflow_store",
            lambda: store,
        )
    from apps.api.wilq_api.routers import content_current_disposition_authority

    monkeypatch.setattr(
        content_current_disposition_authority,
        "content_workflow_store",
        lambda: store,
    )
    return TestClient(app), store, current


def test_public_identity_uses_latest_v2_receipt_and_exact_material(
    identity_runtime: tuple[
        TestClient,
        ContentWorkflowStore,
        dict[str, CurrentPageEvidenceResponse],
    ],
) -> None:
    client, store, current = identity_runtime
    initial = client.get("/api/content/work-items/wi_a/current-identity")
    assert initial.status_code == 200, initial.text
    assert initial.json()["status"] == "blocked"
    assert initial.json()["blocker_code"] == "missing_approved_keep_receipt"

    proposal_a = build_current_page_disposition_v2_proposal(current["wi_a"])
    store.record_current_page_disposition_v2_proposal(proposal_a)
    current["wi_a"] = _evidence("wi_a", "a" * 64, ["wp_a_rotated"], ["catalog_rotated"])
    pending = client.get("/api/content/work-items/wi_a/current-identity").json()
    assert pending["pending_action_id"] == proposal_a.proposal_id
    assert pending["safe_next_step"].startswith("Wilku:")
    _, receipt_a = _seed_approved_receipt(store, proposal_a)

    proposal_b = build_current_page_disposition_v2_proposal(current["wi_b"])
    _, receipt_b = _seed_approved_receipt(store, proposal_b)
    exact_a = client.get("/api/content/work-items/wi_a/current-identity")
    assert exact_a.status_code == 200, exact_a.text
    body_a = exact_a.json()
    assert body_a["status"] == "exact_current"
    assert body_a["canonical_path"] == "/a"
    assert body_a["receipt_id"] == receipt_a
    assert body_a["receipt_digest"]
    assert body_a["original_evidence_ids"] == ["catalog_1", "wp_a_1"]
    assert body_a["apply_evidence_ids"] == ["apply_catalog", "apply_wp"]
    assert body_a["current_evidence_ids"] == ["catalog_rotated", "wp_a_rotated"]
    assert body_a["generation_allowed"] is False

    current["wi_a"] = _evidence(
        "wi_a",
        "a" * 64,
        ["wp_a_rotated"],
        ["catalog_rotated"],
        page_url="https://www.ekologus.pl/a-moved/",
    )
    moved_a = client.get("/api/content/work-items/wi_a/current-identity").json()
    assert moved_a["status"] == "blocked"
    assert moved_a["blocker_code"] == "page_identity_changed"
    assert moved_a["blocker_owner"] == "WILQ content workflow"
    assert moved_a["material_meaning_digest"] == "a" * 64

    current["wi_b"] = _evidence("wi_b", "c" * 64, ["wp_b_changed"], ["catalog_2"])
    proposal_b_changed = build_current_page_disposition_v2_proposal(current["wi_b"])
    _, newest_receipt_b = _seed_approved_receipt(store, proposal_b_changed)
    current["wi_b"] = _evidence("wi_b", "b" * 64, ["wp_b_returned"], ["catalog_1"])
    stale_b = client.get("/api/content/work-items/wi_b/current-identity")
    assert stale_b.status_code == 200, stale_b.text
    body_b = stale_b.json()
    assert body_b["status"] == "blocked"
    assert body_b["blocker_code"] == "material_meaning_changed"
    assert body_b["receipt_id"] == newest_receipt_b
    assert body_b["receipt_id"] != receipt_b
    assert body_b["current_evidence_ids"] == ["catalog_1", "wp_b_returned"]

    source_blocked = CurrentPageEvidenceResponse(
        status="blocked",
        decision="Źródło wymaga odświeżenia.",
        work_item_id="wi_a",
        blocker_code="source_freshness_blocked",
        blocker_owner="WILQ WordPress connector",
        safe_next_step="Odśwież źródło WordPress.",
    )
    current["wi_a"] = source_blocked
    blocked_source = client.get("/api/content/work-items/wi_a/current-identity").json()
    assert blocked_source["blocker_code"] == "source_freshness_blocked"
    assert blocked_source["blocker_owner"] == "WILQ WordPress connector"
    assert blocked_source["safe_next_step"] == "Odśwież źródło WordPress."

    _assert_v1_receipt_stays_on_v1_route(client, store, current)


def test_observed_material_identity_links_existing_keep_preview(
    identity_runtime: tuple[
        TestClient,
        ContentWorkflowStore,
        dict[str, CurrentPageEvidenceResponse],
    ],
) -> None:
    client, store, current = identity_runtime
    current["wi_a"] = CurrentPageEvidenceResponse.model_validate(
        current["wi_a"].model_dump() | {"status": "observed_material_current"}
    )
    proposal = build_current_page_disposition_v2_proposal(current["wi_a"])
    store.record_current_page_disposition_v2_proposal(proposal)
    response = client.get("/api/content/work-items/wi_a/current-identity")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["pending_action_id"] == proposal.proposal_id
    assert body["blocker_code"] == "missing_approved_keep_receipt"


@pytest.mark.parametrize(
    "code", ["current_page_snapshot_unavailable", "current_page_snapshot_mismatch"]
)
def test_identity_preserves_automatic_observation_blocker(
    identity_runtime: tuple[
        TestClient,
        ContentWorkflowStore,
        dict[str, CurrentPageEvidenceResponse],
    ],
    code: str,
) -> None:
    client, _store, current = identity_runtime
    current["wi_a"] = CurrentPageEvidenceResponse(
        status="blocked",
        decision="Odczyt bieżącej strony zablokowany.",
        work_item_id="wi_a",
        blocker_code=cast(CurrentPageEvidenceBlockerCode, code),
        blocker_owner="WILQ WordPress connector",
        safe_next_step="Ponów dokładny odczyt bieżącej strony.",
    )
    response = client.get("/api/content/work-items/wi_a/current-identity")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["blocker_code"] == code
