"""Public receiptless page identity must be bound to fresh exact material."""

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse


def test_public_receiptless_identity_tracks_exact_page_and_blocks_drift(monkeypatch) -> None:
    work_item_id = "content_work_item_exact_a"
    current = {
        "evidence": CurrentPageEvidenceResponse(
            status="observed_material_current",
            decision="Dokładny bieżący odczyt strony.",
            work_item_id=work_item_id,
            page_url="https://www.ekologus.pl/a/",
            material_meaning_digest="a" * 64,
            current_evidence_ids=["ev_current_a"],
            catalog_evidence_ids=["ev_catalog_a"],
            safe_next_step="Sprawdź źródła twierdzeń.",
        )
    }
    monkeypatch.setattr(
        content_current_page_evidence,
        "read_current_page_evidence",
        lambda *, work_item_id: current["evidence"],
    )
    client = TestClient(app)
    path = f"/api/content/work-items/{work_item_id}/current-identity-v3"
    exact_response = client.get(path)
    assert exact_response.status_code == 200, exact_response.text
    exact = exact_response.json()
    assert exact["status"] == "exact_current"
    assert exact["generation_allowed"] is False
    assert exact["page_url"] == "https://www.ekologus.pl/a/"
    assert exact["canonical_path"] == "/a"
    assert exact["material_meaning_digest"] == "a" * 64
    assert exact["current_evidence_ids"] == ["ev_current_a"]
    assert exact["catalog_evidence_ids"] == ["ev_catalog_a"]
    assert exact["identity_digest"]
    assert exact["evidence_digest"]

    stale = client.get(path, params={"expected_identity_digest": "f" * 64})
    assert stale.status_code == 200, stale.text
    assert stale.json()["status"] == "blocked"
    assert stale.json()["blocker_code"] == "page_identity_digest_stale"

    current["evidence"] = current["evidence"].model_copy(
        update={"current_evidence_ids": ["ev_current_a_rotated"]}
    )
    same_identity = client.get(path, params={"expected_identity_digest": exact["identity_digest"]})
    assert same_identity.json()["status"] == "exact_current"
    evidence_drift = client.get(path, params={
        "expected_identity_digest": exact["identity_digest"],
        "expected_evidence_digest": exact["evidence_digest"],
    })
    assert evidence_drift.status_code == 200, evidence_drift.text
    assert evidence_drift.json()["status"] == "blocked"
    assert evidence_drift.json()["blocker_code"] == "page_evidence_digest_stale"

    current["evidence"] = current["evidence"].model_copy(
        update={"material_meaning_digest": "b" * 64, "current_evidence_ids": ["ev_current_a"]}
    )
    changed = client.get(path, params={"expected_identity_digest": exact["identity_digest"]})
    assert changed.status_code == 200, changed.text
    assert changed.json()["blocker_code"] == "page_identity_digest_stale"

    current["evidence"] = current["evidence"].model_copy(
        update={"work_item_id": "content_work_item_other"}
    )
    wrong_subject = client.get(path)
    assert wrong_subject.status_code == 200, wrong_subject.text
    assert wrong_subject.json()["blocker_code"] == "page_identity_subject_mismatch"

    current["evidence"] = CurrentPageEvidenceResponse(
        status="blocked",
        decision="Brak świeżego odczytu.",
        work_item_id=work_item_id,
        blocker_code="source_freshness_blocked",
        blocker_owner="WILQ WordPress connector",
        safe_next_step="Odśwież źródło WordPress.",
    )
    blocked = client.get(path)
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["blocker_code"] == "source_freshness_blocked"
    assert blocked.json()["safe_next_step"] == "Odśwież źródło WordPress."
