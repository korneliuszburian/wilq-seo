"""Receiptless candidate read must keep source-fact review and scope boundaries."""

import sys

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse


def _approved_fact(path: str = "/candidates") -> ContentSourceFact:
    return ContentSourceFact(
        source_id="synthetic_official_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://example.gov/exact-source",
        extracted_fact="Synthetic approved fact for the exact page.",
        scope="claim_policy",
        freshness_date="2026-09-24",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["ev_official_fact"],
        source_connectors=["official_regulatory_review"],
        target_card_id="synthetic_profile",
        target_card_type="regulatory_source",
        target_card_title="Synthetic profile",
        official_source=True,
        regulatory_profile_id="synthetic_profile",
        regulatory_profile_version="synthetic-v1",
        regulatory_requirement_ids=["requirement_exact"],
        applicable_canonical_paths=[path],
    )


def _exact_page_card() -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id="synthetic_profile",
        card_type="service",
        title="Synthetic exact service card",
        summary="Exact page binding for scope validation.",
        service_binding_urls=["https://www.ekologus.pl/candidates/"],
        source_fact_ids=["synthetic_official_fact"],
        evidence_ids=["ev_service_card"],
        source_connectors=["synthetic_card_connector"],
        lifecycle_status="approved_current",
        confidence=0.9,
        freshness="2026-09-24",
    )


def test_public_v3_candidates_use_exact_page_without_keep_and_require_approved_fact(
    monkeypatch,
) -> None:
    evidence = {
        "current": CurrentPageEvidenceResponse(
            status="observed_material_current",
            decision="Dokładny bieżący odczyt.",
            work_item_id="wi_candidates",
            page_url="https://www.ekologus.pl/candidates/",
            material_meaning_digest="a" * 64,
            current_evidence_ids=["ev_current_page"],
            catalog_evidence_ids=["ev_catalog"],
            safe_next_step="Sprawdź zatwierdzone źródła.",
        )
    }
    monkeypatch.setattr(
        content_current_page_evidence,
        "read_current_page_evidence",
        lambda *, work_item_id: evidence["current"],
    )
    candidate_router = sys.modules.get(
        "apps.api.wilq_api.routers.content_source_fact_candidate_v3"
    )
    if candidate_router is not None:
        monkeypatch.setattr(candidate_router, "ekologus_source_facts", lambda: (_approved_fact(),))
        monkeypatch.setattr(candidate_router, "ekologus_content_knowledge_cards", lambda: ())
    client = TestClient(app)
    path = "/api/content/work-items/wi_candidates/source-fact-candidates-v3"
    ready = client.get(path)
    assert ready.status_code == 200, ready.text
    payload = ready.json()
    assert payload["status"] == "eligible"
    assert payload["identity_digest"]
    assert payload["material_meaning_digest"] == "a" * 64
    assert payload["generation_allowed"] is False
    assert [item["source_fact_id"] for item in payload["candidates"]] == [
        "synthetic_official_fact"
    ]
    assert payload["candidates"][0]["evidence_ids"] == ["ev_official_fact"]

    if candidate_router is not None:
        pending = _approved_fact().model_copy(
            update={"review_status": "review_required", "reviewer": None}
        )
        monkeypatch.setattr(candidate_router, "ekologus_source_facts", lambda: (pending,))
    needs_review = client.get(path).json()
    assert needs_review["status"] == "blocked"
    assert needs_review["blocker_code"] == "source_fact_review_required"
    assert needs_review["blocker_owner"] == "Wilku"

    if candidate_router is not None:
        monkeypatch.setattr(
            candidate_router, "ekologus_source_facts", lambda: (_approved_fact("/other"),)
        )
        monkeypatch.setattr(
            candidate_router, "ekologus_content_knowledge_cards", lambda: (_exact_page_card(),)
        )
    wrong_path = client.get(path).json()
    assert wrong_path["status"] == "blocked"
    assert wrong_path["candidates"] == []
