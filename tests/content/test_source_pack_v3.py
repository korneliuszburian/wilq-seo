"""Read-only source pack from previously approved exact official facts."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import (
    content_current_page_evidence,
    content_per_url_delivery_identity_authority,
    content_per_url_disposition_authority,
)
from tests.content.test_per_url_decision_authority import _identity, _policy_facts
from tests.content.test_per_url_disposition_authority import _run_public_lifecycle
from wilq.actions import service as action_service
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryRequirement,
    ContentRegulatoryRequirementCoverage,
)
from wilq.content.workflow import per_url_decision_authority
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.per_url_decision_authority import (
    ContentPerUrlDecisionObservation,
    build_content_per_url_decision_observation,
)
from wilq.content.workflow.store import store as workflow_store_module
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


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


def _current_per_url_identity_action(
    client: TestClient,
    store: ContentWorkflowStore,
    evidence: CurrentPageEvidenceResponse,
) -> str:
    observation = _record_policy_observation(
        store,
        work_item_id=evidence.work_item_id,
        path="/candidates/",
        material_digest=evidence.material_meaning_digest or "0" * 64,
        fact_digest="a" * 64,
        evidence_suffix="source_pack",
        wave_id="source_pack_wave_a",
    )

    disposition_preview = client.post(
        "/api/content/per-url-disposition-authorities/preview",
        json={"observation_id": observation.observation_id},
    )
    assert disposition_preview.status_code == 200, disposition_preview.text
    disposition_action_id = disposition_preview.json()["action"]["id"]
    _run_public_lifecycle(client, disposition_action_id)

    identity_preview = client.post(
        "/api/content/per-url-delivery-identity-authorities/preview",
        json={"disposition_action_id": disposition_action_id},
    )
    assert identity_preview.status_code == 200, identity_preview.text
    identity_action_id = identity_preview.json()["action"]["id"]
    _run_public_lifecycle(client, identity_action_id)
    return identity_action_id


def _record_policy_observation(
    store: ContentWorkflowStore,
    *,
    work_item_id: str,
    path: str,
    material_digest: str,
    fact_digest: str,
    evidence_suffix: str,
    wave_id: str,
) -> ContentPerUrlDecisionObservation:
    observed_at = datetime.now(UTC)
    page_identity = _identity(
        work_item_id,
        path,
        material_digest,
        evidence_suffix=evidence_suffix,
    )
    policy_facts = _policy_facts(
        per_url_decision_authority,
        page_identity,
        fact_digest=fact_digest,
        evidence_suffix=evidence_suffix,
        checked_at=observed_at,
    )
    observation = build_content_per_url_decision_observation(
        page_identity,
        policy_facts,
        observed_at=observed_at,
        source_wave_id=wave_id,
    )
    status, recorded = store.record_content_per_url_decision_observation(observation)
    assert status == "created"
    return recorded


def _per_url_runtime_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> ContentWorkflowStore:
    database = tmp_path / "source-pack-v3-workflow.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(database))
    store = ContentWorkflowStore(database)
    audit = LocalStateStore(database)
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        content_per_url_disposition_authority,
        "content_workflow_store",
        lambda: store,
    )
    monkeypatch.setattr(
        content_per_url_delivery_identity_authority,
        "content_workflow_store",
        lambda: store,
    )
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    pack_router = sys.modules.get("apps.api.wilq_api.routers.content_source_pack_v3")
    if pack_router is not None:
        monkeypatch.setattr(
            pack_router,
            "content_workflow_store",
            lambda: store,
            raising=False,
        )
    return store


def test_public_v3_pack_requires_exact_per_url_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _source, evidence, _coverage_state, _cards = _runtime(monkeypatch)
    store = _per_url_runtime_store(tmp_path, monkeypatch)
    path = "/api/content/work-items/wi_candidates/source-pack-preview-v3"
    missing_identity = client.get(path)
    assert missing_identity.status_code == 200, missing_identity.text
    blocked = missing_identity.json()
    assert blocked["status"] == "blocked"
    assert blocked["blocker"]["code"] == "per_url_delivery_identity_required"
    assert blocked["source_pack_id"] is None
    assert blocked["source_pack_hash"] is None
    assert blocked["facts"] == []
    packet = client.get(
        "/api/content/work-items/wi_candidates/research-packet-v3-preview"
    )
    assert packet.status_code == 200, packet.text
    assert packet.json()["status"] == "blocked"
    assert packet.json()["blocker"]["code"] == "per_url_delivery_identity_required"
    assert packet.json()["selected_facts"] == []

    identity_action_id = _current_per_url_identity_action(
        client, store, evidence["current"]
    )
    params = {"per_url_delivery_identity_action_id": identity_action_id}
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    ready = response.json()
    assert ready["status"] == "ready"
    assert ready["source_pack_id"].startswith("source_pack_v3_")
    assert ready["per_url_identity"]["action_id"] == identity_action_id
    assert ready["per_url_identity"]["binding_id"]
    assert ready["per_url_identity"]["binding_digest"]
    assert ready["per_url_identity"]["semantic_row_digest"]
    assert ready["generation_allowed"] is False
    assert ready["packet_write_allowed"] is False
    assert [fact["source_fact_id"] for fact in ready["facts"]] == ["synthetic_official_fact"]
    assert ready["facts"][0]["source_reference"] == "https://eli.gov.pl/acts/synthetic"
    assert ready["requirements"][0]["source_fact_ids"] == ["synthetic_official_fact"]


def test_public_v3_pack_hash_ignores_unrelated_page_and_current_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, source, evidence, _coverage_state, _cards = _runtime(monkeypatch)
    store = _per_url_runtime_store(tmp_path, monkeypatch)
    identity_action_id = _current_per_url_identity_action(
        client, store, evidence["current"]
    )
    path = "/api/content/work-items/wi_candidates/source-pack-preview-v3"
    params = {"per_url_delivery_identity_action_id": identity_action_id}
    initial = client.get(path, params=params).json()
    assert initial["status"] == "ready"

    evidence["current"] = evidence["current"].model_copy(
        update={"current_evidence_ids": ["ev_current_page_rotated"]}
    )
    rotated = client.get(path, params=params).json()
    assert rotated["status"] == "ready"
    assert rotated["source_pack_hash"] == initial["source_pack_hash"]
    assert rotated["verification_evidence_ids"] != initial["verification_evidence_ids"]

    source["extra"] = (ContentSourceFact.model_validate(
        _approved_fact().model_dump() | {
            "source_id": "unrelated_approved_fact",
            "applicable_canonical_paths": ["/other"],
        }
    ),)
    unrelated = client.get(path, params=params).json()
    assert unrelated["status"] == "ready"
    assert unrelated["source_pack_hash"] == initial["source_pack_hash"]
    assert unrelated["registry_digest"] != initial["registry_digest"]
    _record_policy_observation(
        store,
        work_item_id="wi_unrelated",
        path="/unrelated/",
        material_digest="b" * 64,
        fact_digest="c" * 64,
        evidence_suffix="unrelated",
        wave_id="source_pack_wave_unrelated",
    )
    unrelated_page = client.get(path, params=params).json()
    assert unrelated_page["status"] == "ready"
    assert unrelated_page["source_pack_hash"] == initial["source_pack_hash"]


def test_public_v3_pack_blocks_identity_drift_and_tracks_source_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, source, evidence, _coverage_state, _cards = _runtime(monkeypatch)
    store = _per_url_runtime_store(tmp_path, monkeypatch)
    identity_action_id = _current_per_url_identity_action(
        client, store, evidence["current"]
    )
    path = "/api/content/work-items/wi_candidates/source-pack-preview-v3"
    params = {"per_url_delivery_identity_action_id": identity_action_id}
    initial = client.get(path, params=params).json()
    assert initial["status"] == "ready"

    evidence["current"] = evidence["current"].model_copy(
        update={"material_meaning_digest": "b" * 64}
    )
    changed_page = client.get(path, params=params).json()
    assert changed_page["status"] == "blocked"
    assert changed_page["blocker"]["code"] == "per_url_delivery_identity_page_changed"
    assert changed_page["source_pack_hash"] is None
    assert changed_page["facts"] == []

    evidence["current"] = evidence["current"].model_copy(
        update={"material_meaning_digest": "a" * 64}
    )

    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {"extracted_fact": "Updated approved legal fact."}
    )
    changed_fact = client.get(path, params=params).json()
    assert changed_fact["status"] == "ready"
    assert changed_fact["source_pack_hash"] != initial["source_pack_hash"]

    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {"review_status": "review_required", "reviewer": None}
    )
    blocked_fact = client.get(path, params=params).json()
    assert blocked_fact["status"] == "blocked"
    assert blocked_fact["blocker"]["code"] == "source_fact_review_required"
    assert blocked_fact["facts"] == []

    source["fact"] = _approved_fact()
    _record_policy_observation(
        store,
        work_item_id="wi_candidates",
        path="/candidates/",
        material_digest="a" * 64,
        fact_digest="d" * 64,
        evidence_suffix="source_pack_changed",
        wave_id="source_pack_wave_changed",
    )
    changed_semantics = client.get(path, params=params).json()
    assert changed_semantics["status"] == "blocked"
    assert changed_semantics["blocker"]["code"] == "per_url_delivery_identity_not_current"
    assert changed_semantics["source_pack_id"] is None
    assert changed_semantics["source_pack_hash"] is None
    assert changed_semantics["facts"] == []


def test_public_v3_pack_blocks_missing_coverage_wrong_connector_and_private_fact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, source, _evidence, coverage, _cards = _runtime(monkeypatch)
    store = _per_url_runtime_store(tmp_path, monkeypatch)
    identity_action_id = _current_per_url_identity_action(
        client,
        store,
        CurrentPageEvidenceResponse(
            status="observed_material_current",
            decision="Dokładny bieżący odczyt.",
            work_item_id="wi_candidates",
            page_url="https://www.ekologus.pl/candidates/",
            material_meaning_digest="a" * 64,
            current_evidence_ids=["ev_current_page"],
            catalog_evidence_ids=["ev_catalog"],
            safe_next_step="Sprawdź źródła.",
        ),
    )
    path = "/api/content/work-items/wi_candidates/source-pack-preview-v3"
    params = {"per_url_delivery_identity_action_id": identity_action_id}

    coverage["override"] = ContentRegulatoryCoverage()
    no_profile = client.get(path, params=params).json()
    assert no_profile["status"] == "blocked"
    assert no_profile["blocker"]["code"] == "official_regulatory_profile_missing"

    incomplete = _coverage(source["fact"])
    incomplete.requirements.append(ContentRegulatoryRequirement(
        id="requirement_missing", label="Brak", reason="Wymaga innego źródła."
    ))
    coverage["override"] = incomplete
    missing_requirement = client.get(path, params=params).json()
    assert missing_requirement["status"] == "blocked"
    assert missing_requirement["blocker"]["code"] == "legal_requirements_incomplete"

    foreign = _coverage(source["fact"])
    foreign.requirement_coverage[0].source_fact_ids = ["foreign_fact"]
    foreign.requirement_coverage[0].evidence_ids = ["ev_foreign"]
    coverage["override"] = foreign
    unbound_requirement = client.get(path, params=params).json()
    assert unbound_requirement["status"] == "blocked"
    assert unbound_requirement["blocker"]["code"] == "legal_requirement_lineage_mismatch"

    coverage["override"] = None
    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {"source_connectors": ["wordpress_ekologus"]}
    )
    wrong_connector = client.get(path, params=params).json()
    assert wrong_connector["status"] == "blocked"
    assert wrong_connector["blocker"]["code"] == "selected_source_fact_connector_invalid"

    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {
            "source_connectors": ["official_regulatory_review"],
            "privacy_class": "private_local",
        }
    )
    private = client.get(path, params=params).json()
    assert private["status"] == "blocked"
    assert private["blocker"]["code"] == "selected_source_fact_not_commit_safe"

    source["fact"] = ContentSourceFact.model_validate(
        source["fact"].model_dump() | {
            "privacy_class": "commit_safe",
            "extracted_fact": "Kontakt: test@example.com",
        }
    )
    redacted = client.get(path, params=params).json()
    assert redacted["status"] == "blocked"
    assert redacted["blocker"]["code"] == "selected_source_fact_redaction_required"


def test_public_v3_pack_binds_current_service_card_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _source, evidence, _coverage_state, cards = _runtime(monkeypatch)
    store = _per_url_runtime_store(tmp_path, monkeypatch)
    identity_action_id = _current_per_url_identity_action(
        client, store, evidence["current"]
    )
    path = "/api/content/work-items/wi_candidates/source-pack-preview-v3"
    params = {"per_url_delivery_identity_action_id": identity_action_id}
    cards["items"] = (_exact_card("ev_card_a"),)
    first = client.get(path, params=params).json()
    assert first["status"] == "ready"
    assert first["service_binding"]["card_id"] == "synthetic_profile"
    assert "ev_card_a" in first["verification_evidence_ids"]

    cards["items"] = (_exact_card("ev_card_b"),)
    changed_card = client.get(path, params=params).json()
    assert changed_card["status"] == "ready"
    assert changed_card["source_pack_hash"] != first["source_pack_hash"]
