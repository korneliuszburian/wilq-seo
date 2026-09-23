from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import (
    OFFICIAL_GUIDANCE_TARGET_CARD_ID,
    OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
    ContentKnowledgeLifecycleStatus,
    ContentSourceFact,
    SourceFactReviewStatus,
    SourceFactType,
)
from wilq.content.workflow.current_page_disposition_v2 import (
    CurrentPageDispositionV2Receipt,
    build_current_page_disposition_v2_proposal,
    build_current_page_disposition_v2_receipt,
)
from wilq.content.workflow.current_page_disposition_v2_action import (
    current_page_disposition_v2_action,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.store import store as workflow_store_module
from wilq.content.workflow.store.store import ContentWorkflowStore


def _evidence(digest: str) -> CurrentPageEvidenceResponse:
    return CurrentPageEvidenceResponse(
        status="reviewed_material_current",
        decision="Materiał ma aktualne review.",
        work_item_id="wi_candidates",
        page_url="https://www.ekologus.pl/candidates/",
        material_meaning_digest=digest,
        current_evidence_ids=["wp_current"],
        catalog_evidence_ids=["catalog_current"],
        safe_next_step="Sprawdź dokładny adres.",
    )


def _approved_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="synthetic_candidate_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://www.ekologus.pl/candidates/",
        extracted_fact="Synthetic reviewed fact for candidate projection.",
        scope="claim_policy",
        freshness_date="2026-09-23",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["evidence_candidate_fact"],
        source_connectors=["official_regulatory_review"],
        target_card_id="synthetic_candidate_profile",
        target_card_type="regulatory_source",
        target_card_title="Synthetic candidate profile",
        official_source=True,
        regulatory_profile_id="synthetic_candidate_profile",
        regulatory_profile_version="synthetic-v1",
        regulatory_requirement_ids=["candidate_requirement"],
        applicable_canonical_paths=["/candidates"],
    )


def _out_of_scope_official_guidance() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="synthetic_official_guidance",
        source_type="official_guidance",
        privacy_class="commit_safe",
        source_url_or_path="https://example.gov/guidance",
        extracted_fact="Guidance bound to another exact path.",
        scope="claim_policy",
        freshness_date="2026-09-23",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["evidence_official_guidance"],
        source_connectors=["official_guidance"],
        target_card_id=OFFICIAL_GUIDANCE_TARGET_CARD_ID,
        target_card_type="claim_policy",
        target_card_title=OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
        applicable_canonical_paths=["/other-path"],
    )


def _review_required_fact(
    *,
    lineage_bound: bool = True,
    review_status: SourceFactReviewStatus = "review_required",
    source_type: SourceFactType = "public_site",
    source_id: str = "synthetic_review_required_fact",
) -> ContentSourceFact:
    return ContentSourceFact(
        source_id=source_id,
        source_type=source_type,
        privacy_class="private_local" if source_type == "private_candidate" else "commit_safe",
        source_url_or_path="https://www.ekologus.pl/candidates/",
        extracted_fact="Synthetic scoped fact awaiting human review.",
        scope="service",
        freshness_date="2026-09-23",
        confidence=0.9,
        review_status=review_status,
        reviewer="synthetic_wilku",
        evidence_ids=["evidence_review_required_fact"] if lineage_bound else [],
        source_connectors=["wordpress_ekologus"] if lineage_bound else [],
        target_card_id=OFFICIAL_GUIDANCE_TARGET_CARD_ID,
        target_card_type="service",
        target_card_title="Synthetic exact service card",
    )


def _approved_card_fact() -> ContentSourceFact:
    return _review_required_fact(
        review_status="approved",
        source_id="synthetic_card_candidate_fact",
    )


def _exact_service_card(
    *, lifecycle_status: ContentKnowledgeLifecycleStatus = "approved_current"
) -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id=OFFICIAL_GUIDANCE_TARGET_CARD_ID,
        card_type="service",
        title="Synthetic exact service card",
        summary="Synthetic exact page binding for the selection guard.",
        service_binding_urls=["https://www.ekologus.pl/candidates/"],
        source_fact_ids=[
            "synthetic_official_guidance",
            "synthetic_card_candidate_fact",
            "synthetic_review_required_fact",
            "synthetic_untrusted_origin",
            "synthetic_card_review_fact",
            "synthetic_stale_fact",
        ],
        evidence_ids=["evidence_service_card"],
        source_connectors=["synthetic_card_connector"],
        lifecycle_status=lifecycle_status,
        confidence=0.9,
        freshness="2026-09-23",
    )


def _candidate_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[
    TestClient,
    ContentWorkflowStore,
    dict[str, CurrentPageEvidenceResponse],
    ModuleType | None,
]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    evidence = {"current": _evidence("a" * 64)}
    monkeypatch.setattr(
        content_current_page_evidence,
        "read_current_page_evidence",
        lambda *, work_item_id: evidence["current"],
    )
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    from apps.api.wilq_api.routers import content_current_page_identity_v2

    monkeypatch.setattr(content_current_page_identity_v2, "content_workflow_store", lambda: store)

    candidate_router = sys.modules.get(
        "apps.api.wilq_api.routers.content_source_fact_candidate_v2"
    )
    if candidate_router is not None:
        monkeypatch.setattr(candidate_router, "content_workflow_store", lambda: store)
        monkeypatch.setattr(
            candidate_router,
            "ekologus_source_facts",
            lambda: (
                _approved_fact(),
                _approved_card_fact(),
                _out_of_scope_official_guidance(),
            ),
        )
        monkeypatch.setattr(
            candidate_router,
            "ekologus_content_knowledge_cards",
            lambda: (_exact_service_card(),),
        )
    return TestClient(app), store, evidence, candidate_router


def _record_keep_receipt(
    store: ContentWorkflowStore, evidence: CurrentPageEvidenceResponse
) -> CurrentPageDispositionV2Receipt:
    proposal = build_current_page_disposition_v2_proposal(evidence)
    store.record_current_page_disposition_v2_proposal(proposal)
    receipt = build_current_page_disposition_v2_receipt(
        action=current_page_disposition_v2_action(proposal),
        proposal=proposal,
        preview_audit_id="preview_candidates",
        review_audit_id="review_candidates",
        confirmation_audit_id="confirm_candidates",
        impact_audit_id="impact_candidates",
        reviewed_by="synthetic_wilku",
        confirmed_by="synthetic_wilku",
        verification_evidence_ids=("apply_catalog", "apply_wp"),
        verified_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    store.record_current_page_disposition_v2_receipt(receipt)
    return receipt


def _assert_review_blocker(
    client: TestClient, path: str, candidate_router: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        candidate_router,
        "ekologus_source_facts",
        lambda: (_review_required_fact(),),
    )
    review_required = client.get(path)
    assert review_required.status_code == 200, review_required.text
    review_body = review_required.json()
    assert review_body["status"] == "blocked"
    assert review_body["candidates"] == []
    assert review_body["blocker_code"] == "source_fact_review_required"
    assert review_body["blocker_owner"] == "Wilku"
    assert review_body["blocker_evidence_ids"] == sorted(
        set(
            review_body["current_evidence_ids"]
            + review_body["original_evidence_ids"]
            + review_body["apply_evidence_ids"]
            + review_body["registry_evidence_ids"]
            + ["evidence_review_required_fact"]
            + _exact_service_card().evidence_ids
        )
    )
    assert review_body["safe_next_step"] == (
        "Wilku: sprawdź i zatwierdź exact source fact przed ponownym odczytem kandydatów."
    )
    assert review_body["generation_allowed"] is False
    assert review_body["source_pack_write_allowed"] is False

    monkeypatch.setattr(
        candidate_router,
        "ekologus_source_facts",
        lambda: (_review_required_fact(lineage_bound=False),),
    )
    missing_lineage = client.get(path)
    assert missing_lineage.status_code == 200, missing_lineage.text
    lineage_body = missing_lineage.json()
    assert lineage_body["status"] == "blocked"
    assert lineage_body["candidates"] == []
    assert lineage_body["blocker_code"] == "source_fact_lineage_missing"
    assert lineage_body["blocker_owner"] == "WILQ content workflow"
    assert lineage_body["blocker_evidence_ids"] == sorted(
        set(
            lineage_body["current_evidence_ids"]
            + lineage_body["original_evidence_ids"]
            + lineage_body["apply_evidence_ids"]
            + lineage_body["registry_evidence_ids"]
            + _exact_service_card().evidence_ids
        )
    )
    assert lineage_body["safe_next_step"] == (
        "Uzupełnij evidence i source connector "
        "exact source factu, a następnie ponów odczyt kandydatów."
    )


def _assert_exact_candidate(
    client: TestClient, path: str, receipt: CurrentPageDispositionV2Receipt
) -> None:
    current = client.get(path)
    assert current.status_code == 200, current.text
    body = current.json()
    assert body["status"] == "eligible"
    assert body["receipt_id"] == receipt.receipt_id
    assert body["receipt_digest"] == receipt.receipt_digest
    assert body["material_meaning_digest"] == "a" * 64
    assert body["work_item_id"] == "wi_candidates"
    assert body["canonical_path"] == "/candidates"
    assert body["generation_allowed"] is False
    assert body["source_pack_write_allowed"] is False
    assert body["registry_digest"]
    assert body["registry_evidence_ids"]
    assert [item["source_fact_id"] for item in body["candidates"]] == [
        "synthetic_candidate_fact",
        "synthetic_card_candidate_fact",
    ]
    assert body["candidates"][0]["evidence_ids"] == ["evidence_candidate_fact"]
    assert body["candidates"][0]["source_connectors"] == ["official_regulatory_review"]
    assert body["candidates"][1]["deterministic_origin"] == "exact_service_card_binding"
    assert body["service_binding"]["status"] == "exact_bound"
    assert body["service_binding"]["card_id"] == OFFICIAL_GUIDANCE_TARGET_CARD_ID
    assert body["service_binding"]["card_status"] == "approved_current"
    assert body["service_binding"]["card_evidence_ids"] == ["evidence_service_card"]
    assert body["service_binding"]["card_source_connectors"] == ["synthetic_card_connector"]
    assert body["service_binding"]["card_freshness"] == "2026-09-23"
    assert all(
        item["source_fact_id"] != "synthetic_official_guidance"
        for item in body["candidates"]
    )


def test_public_v2_source_fact_candidates_require_exact_current_keep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, evidence, candidate_router = _candidate_runtime(tmp_path, monkeypatch)

    path = "/api/content/work-items/wi_candidates/source-fact-candidates"
    missing = client.get(path)
    assert missing.status_code == 200, missing.text
    assert candidate_router is not None
    missing_body = missing.json()
    assert missing_body["status"] == "blocked"
    assert missing_body["blocker_code"] == "missing_approved_keep_receipt"
    assert missing_body["blocker_owner"] == "WILQ content workflow"
    assert missing_body["blocker_evidence_ids"] == sorted(
        set(
            missing_body["current_evidence_ids"]
            + missing_body["original_evidence_ids"]
            + missing_body["apply_evidence_ids"]
        )
    )
    assert missing_body["generation_allowed"] is False

    receipt = _record_keep_receipt(store, evidence["current"])
    _assert_exact_candidate(client, path, receipt)
    _assert_missing_candidate_evidence(client, path, monkeypatch, candidate_router)
    _assert_review_blocker(client, path, candidate_router, monkeypatch)
    _assert_specific_review_blockers(client, path, monkeypatch, candidate_router)

    evidence["current"] = _evidence("b" * 64)
    drifted = client.get(path)
    assert drifted.status_code == 200, drifted.text
    drifted_body = drifted.json()
    assert drifted_body["status"] == "blocked"
    assert drifted_body["blocker_code"] == "material_meaning_changed"
    assert drifted_body["receipt_id"] == receipt.receipt_id
    assert drifted_body["blocker_evidence_ids"] == sorted(
        set(
            drifted_body["current_evidence_ids"]
            + drifted_body["original_evidence_ids"]
            + drifted_body["apply_evidence_ids"]
        )
    )
    assert drifted_body["generation_allowed"] is False


def _assert_missing_candidate_evidence(
    client: TestClient, path: str, monkeypatch: pytest.MonkeyPatch, candidate_router: ModuleType
) -> None:
    monkeypatch.setattr(candidate_router, "ekologus_source_facts", lambda: ())
    missing = client.get(path)
    assert missing.status_code == 200, missing.text
    body = missing.json()
    assert body["status"] == "blocked"
    assert body["blocker_code"] == "approved_source_fact_candidate_missing"
    assert body["blocker_owner"] == "WILQ content workflow"
    assert body["candidates"] == []
    assert body["blocker_evidence_ids"] == sorted(
        set(
            body["current_evidence_ids"]
            + body["original_evidence_ids"]
            + body["apply_evidence_ids"]
            + body["registry_evidence_ids"]
            + _exact_service_card().evidence_ids
        )
    )
    assert body["generation_allowed"] is False
    assert body["source_pack_write_allowed"] is False


def _assert_specific_review_blockers(
    client: TestClient, path: str, monkeypatch: pytest.MonkeyPatch, candidate_router: ModuleType
) -> None:
    cases: tuple[
        tuple[ContentSourceFact, ContentKnowledgeLifecycleStatus, str, str, str], ...
    ] = (
        (
            _review_required_fact(
                source_type="private_candidate",
                source_id="synthetic_untrusted_origin",
            ),
            "approved_current",
            "source_fact_source_ineligible",
            "WILQ content workflow",
            "WILQ content workflow: zweryfikuj pochodzenie i prywatność źródła, "
            "a następnie zastąp je kwalifikowanym faktem.",
        ),
        (
            _review_required_fact(
                review_status="approved",
                source_id="synthetic_card_review_fact",
            ),
            "source_backed_review_required",
            "service_card_review_required",
            "Wilku",
            "Wilku: sprawdź i zatwierdź dokładną kartę usługi przed ponownym odczytem kandydatów.",
        ),
        (
            _review_required_fact(
                review_status="stale",
                source_id="synthetic_stale_fact",
            ),
            "approved_current",
            "source_fact_stale",
            "WILQ content workflow",
            "Odśwież źródło i ponownie sprawdź exact source fact.",
        ),
    )
    for fact, card_status, code, owner, next_step in cases:
        monkeypatch.setattr(candidate_router, "ekologus_source_facts", lambda fact=fact: (fact,))
        monkeypatch.setattr(
            candidate_router,
            "ekologus_content_knowledge_cards",
            lambda card_status=card_status: (_exact_service_card(lifecycle_status=card_status),),
        )
        response = client.get(path)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "blocked"
        assert body["candidates"] == []
        assert body["blocker_code"] == code
        assert body["blocker_owner"] == owner
        assert body["blocker_evidence_ids"] == sorted(
            set(
                body["current_evidence_ids"]
                + body["original_evidence_ids"]
                + body["apply_evidence_ids"]
                + body["registry_evidence_ids"]
                + fact.evidence_ids
                + _exact_service_card(lifecycle_status=card_status).evidence_ids
            )
        )
        assert body["safe_next_step"] == next_step
        assert body["generation_allowed"] is False
        assert body["source_pack_write_allowed"] is False
