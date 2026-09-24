"""Read-only source pack from previously approved exact official facts."""

import sys

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryRequirement,
    ContentRegulatoryRequirementCoverage,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse


def _approved_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="synthetic_official_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://eli.gov.pl/acts/synthetic",
        extracted_fact="Synthetic approved legal fact for exact page.",
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
        applicable_canonical_paths=["/candidates"],
    )


def _coverage(fact: ContentSourceFact) -> ContentRegulatoryCoverage:
    return ContentRegulatoryCoverage(
        applicability_status="required",
        profile_id="synthetic_profile",
        profile_version="synthetic-v1",
        canonical_path="/candidates",
        requirements=[ContentRegulatoryRequirement(
            id="requirement_exact", label="Wymaganie", reason="Źródło urzędowe."
        )],
        requirement_coverage=[ContentRegulatoryRequirementCoverage(
            requirement_id="requirement_exact",
            source_fact_ids=[fact.source_id],
            evidence_ids=list(fact.evidence_ids),
        )],
        source_fact_ids=[fact.source_id],
        evidence_ids=list(fact.evidence_ids),
        source_facts=[fact],
    )


def _exact_card(evidence_id: str) -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id="synthetic_profile",
        card_type="service",
        title="Synthetic service card",
        summary="Exact page binding for source pack.",
        service_binding_urls=["https://www.ekologus.pl/candidates/"],
        source_fact_ids=["synthetic_official_fact"],
        evidence_ids=[evidence_id],
        source_connectors=["synthetic_card_connector"],
        lifecycle_status="approved_current",
        confidence=0.9,
        freshness="reviewed_2026-09-24",
    )


def _runtime(monkeypatch):
    source = {"fact": _approved_fact(), "extra": ()}
    coverage = {"override": None}
    cards = {"items": ()}
    evidence = {"current": CurrentPageEvidenceResponse(
        status="observed_material_current",
        decision="Dokładny bieżący odczyt.",
        work_item_id="wi_candidates",
        page_url="https://www.ekologus.pl/candidates/",
        material_meaning_digest="a" * 64,
        current_evidence_ids=["ev_current_page"],
        catalog_evidence_ids=["ev_catalog"],
        safe_next_step="Sprawdź źródła.",
    )}
    monkeypatch.setattr(
        content_current_page_evidence,
        "read_current_page_evidence",
        lambda *, work_item_id: evidence["current"],
    )
    pack_router = sys.modules.get("apps.api.wilq_api.routers.content_source_pack_v3")
    pack_domain = sys.modules.get("wilq.content.workflow.source_pack_v3")
    if pack_router is not None:
        monkeypatch.setattr(
            pack_router,
            "ekologus_source_facts",
            lambda: (source["fact"], *source["extra"]),
        )
        monkeypatch.setattr(pack_router, "ekologus_content_knowledge_cards", lambda: cards["items"])
    if pack_domain is not None:
        monkeypatch.setattr(
            pack_domain,
            "regulatory_content_coverage",
            lambda **_kwargs: coverage["override"] or _coverage(source["fact"]),
        )
    return TestClient(app), source, evidence, coverage, cards


def test_public_v3_pack_uses_only_current_approved_official_facts_without_keep(
    monkeypatch,
) -> None:
    client, source, evidence, _coverage_state, _cards = _runtime(monkeypatch)
    path = "/api/content/work-items/wi_candidates/source-pack-preview-v3"
    response = client.get(path)
    assert response.status_code == 200, response.text
    ready = response.json()
    assert ready["status"] == "ready"
    assert ready["source_pack_id"].startswith("source_pack_v3_")
    assert ready["generation_allowed"] is False
    assert ready["packet_write_allowed"] is False
    assert "keep_receipt_id" not in ready
    assert [fact["source_fact_id"] for fact in ready["facts"]] == ["synthetic_official_fact"]
    assert ready["facts"][0]["source_reference"] == "https://eli.gov.pl/acts/synthetic"
    assert ready["requirements"][0]["source_fact_ids"] == ["synthetic_official_fact"]

    evidence["current"] = evidence["current"].model_copy(
        update={"current_evidence_ids": ["ev_current_page_rotated"]}
    )
    rotated = client.get(path).json()
    assert rotated["status"] == "ready"
    assert rotated["source_pack_hash"] == ready["source_pack_hash"]
    assert rotated["verification_evidence_ids"] != ready["verification_evidence_ids"]

    source["extra"] = (ContentSourceFact.model_validate(
        _approved_fact().model_dump() | {
            "source_id": "unrelated_approved_fact",
            "applicable_canonical_paths": ["/other"],
        }
    ),)
    unrelated = client.get(path).json()
    assert unrelated["status"] == "ready"
    assert unrelated["source_pack_hash"] == ready["source_pack_hash"]
    assert unrelated["registry_digest"] != ready["registry_digest"]
    source["extra"] = ()

    evidence["current"] = evidence["current"].model_copy(
        update={"material_meaning_digest": "b" * 64}
    )
    changed_page = client.get(path).json()
    assert changed_page["status"] == "ready"
    assert changed_page["source_pack_hash"] != ready["source_pack_hash"]

    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {"extracted_fact": "Updated approved legal fact."}
    )
    changed_fact = client.get(path).json()
    assert changed_fact["status"] == "ready"
    assert changed_fact["source_pack_hash"] != ready["source_pack_hash"]

    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {"review_status": "review_required", "reviewer": None}
    )
    blocked = client.get(path).json()
    assert blocked["status"] == "blocked"
    assert blocked["blocker"]["code"] == "source_fact_review_required"
    assert blocked["facts"] == []


def test_public_v3_pack_blocks_missing_coverage_wrong_connector_and_private_fact(
    monkeypatch,
) -> None:
    client, source, _evidence, coverage, _cards = _runtime(monkeypatch)
    path = "/api/content/work-items/wi_candidates/source-pack-preview-v3"

    coverage["override"] = ContentRegulatoryCoverage()
    no_profile = client.get(path).json()
    assert no_profile["status"] == "blocked"
    assert no_profile["blocker"]["code"] == "official_regulatory_profile_missing"

    incomplete = _coverage(source["fact"])
    incomplete.requirements.append(ContentRegulatoryRequirement(
        id="requirement_missing", label="Brak", reason="Wymaga innego źródła."
    ))
    coverage["override"] = incomplete
    missing_requirement = client.get(path).json()
    assert missing_requirement["status"] == "blocked"
    assert missing_requirement["blocker"]["code"] == "legal_requirements_incomplete"

    foreign = _coverage(source["fact"])
    foreign.requirement_coverage[0].source_fact_ids = ["foreign_fact"]
    foreign.requirement_coverage[0].evidence_ids = ["ev_foreign"]
    coverage["override"] = foreign
    unbound_requirement = client.get(path).json()
    assert unbound_requirement["status"] == "blocked"
    assert unbound_requirement["blocker"]["code"] == "legal_requirement_lineage_mismatch"

    coverage["override"] = None
    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {"source_connectors": ["wordpress_ekologus"]}
    )
    wrong_connector = client.get(path).json()
    assert wrong_connector["status"] == "blocked"
    assert wrong_connector["blocker"]["code"] == "selected_source_fact_connector_invalid"

    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {
            "source_connectors": ["official_regulatory_review"],
            "privacy_class": "private_local",
        }
    )
    private = client.get(path).json()
    assert private["status"] == "blocked"
    assert private["blocker"]["code"] == "selected_source_fact_not_commit_safe"

    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {
            "privacy_class": "commit_safe",
            "extracted_fact": "Kontakt: test@example.com",
        }
    )
    redacted = client.get(path).json()
    assert redacted["status"] == "blocked"
    assert redacted["blocker"]["code"] == "selected_source_fact_redaction_required"


def test_public_v3_pack_binds_current_service_card_lineage(monkeypatch) -> None:
    client, _source, _evidence, _coverage_state, cards = _runtime(monkeypatch)
    path = "/api/content/work-items/wi_candidates/source-pack-preview-v3"
    cards["items"] = (_exact_card("ev_card_a"),)
    first = client.get(path).json()
    assert first["status"] == "ready"
    assert first["service_binding"]["card_id"] == "synthetic_profile"
    assert "ev_card_a" in first["verification_evidence_ids"]

    cards["items"] = (_exact_card("ev_card_b"),)
    changed_card = client.get(path).json()
    assert changed_card["status"] == "ready"
    assert changed_card["source_pack_hash"] != first["source_pack_hash"]
