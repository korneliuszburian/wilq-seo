from __future__ import annotations

import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from tests.content.test_source_fact_authority_v2 import (
    _card,
    _fact,
    _legal_fact,
    _preview,
    _run_lifecycle,
    _runtime,
    _unrelated_fact,
)
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import (
    OFFICIAL_GUIDANCE_TARGET_CARD_ID,
    OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
    OFFICIAL_GUIDANCE_TARGET_CARD_TYPE,
    ContentSourceFact,
)
from wilq.content.regulatory import policy as regulatory_policy
from wilq.content.regulatory.policy import (
    ContentRegulatoryProfile,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow import source_fact_authority_v2 as authority_module
from wilq.schemas import Evidence, FreshnessState


def _current_card() -> ContentKnowledgeCard:
    return ContentKnowledgeCard.model_validate(
        _card().model_dump(mode="json") | {"freshness": "reviewed_2026-09-23"}
    )


def _legal_packet_fact(*, changed: bool = False) -> ContentSourceFact:
    payload = _legal_fact().model_dump(mode="json") | {
        "source_id": "approved_fact",
        "applicable_service_card_ids": ["authority_v2_service"],
        "freshness_date": datetime.now(UTC).date().isoformat(),
    }
    if changed:
        payload["extracted_fact"] = "Changed synthetic official requirement."
    return ContentSourceFact.model_validate(payload)


def _enable_legal_packet(
    monkeypatch: pytest.MonkeyPatch,
    facts: dict[str, tuple[ContentSourceFact, ...]],
) -> None:
    facts["value"] = (_legal_packet_fact(),)
    profile = ContentRegulatoryProfile(
        id="synthetic_regulatory_profile",
        version="synthetic-v1",
        service_card_ids=["authority_v2_service"],
        canonical_paths=["/authority-v2"],
        official_source_hosts=["eli.gov.pl"],
        max_source_age_days=90,
        requirements=[
            ContentRegulatoryRequirement(
                id="synthetic_requirement",
                label="syntetyczny wymóg",
                reason="wymaga dokładnego źródła urzędowego",
            )
        ],
    )
    monkeypatch.setattr(regulatory_policy, "regulatory_content_profile", lambda **_: profile)

    def current_evidence(ids: list[str]) -> list[Evidence]:
        return [
            Evidence(
                id=fact.evidence_ids[0],
                source_connector="official_regulatory_review",
                source_type="official_regulatory_source_fact",
                source_id=fact.source_id,
                freshness=FreshnessState(state="fresh"),
                summary=fact.extracted_fact,
                raw_ref=fact.source_url_or_path,
            )
            for fact in facts["value"]
            if fact.source_type == "legal_update" and fact.evidence_ids[0] in ids
        ]

    monkeypatch.setattr(regulatory_policy, "list_evidence_by_ids", current_evidence)


def _patch_source_pack_router(
    monkeypatch: pytest.MonkeyPatch,
    store: object,
    facts: Mapping[str, tuple[ContentSourceFact, ...]],
) -> None:
    module = sys.modules.get("apps.api.wilq_api.routers.content_source_pack_v2")
    monkeypatch.setattr(
        authority_module, "ekologus_content_knowledge_cards", lambda: (_current_card(),)
    )
    if module is not None:
        monkeypatch.setattr(module, "content_workflow_store", lambda: store)
        monkeypatch.setattr(module, "ekologus_source_facts", lambda: facts["value"])
        monkeypatch.setattr(module, "ekologus_content_knowledge_cards", lambda: (_current_card(),))


def _source_pack(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/content/work-items/wi_source_authority_v2/source-pack-preview")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_public_source_pack_v2_is_exact_redacted_and_semantically_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, _, current, facts = _runtime(tmp_path, monkeypatch)
    _patch_source_pack_router(monkeypatch, store, facts)
    _enable_legal_packet(monkeypatch, facts)
    action_id, _ = _preview(client, store)
    _run_lifecycle(client, action_id)
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic_wilku"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["applied"] is True
    assert applied.json()["adapter_result"]["external_write_attempted"] is False

    ready = _source_pack(client)
    assert ready["status"] == "ready", ready["blocker"]
    assert ready["generation_allowed"] is False
    assert ready["source_pack_write_allowed"] is False
    assert ready["facts"][0]["text"] == "Synthetic official requirement."
    assert ready["service_binding"]["card_freshness"] == "reviewed_2026-09-23"
    assert ready["facts"][0]["source_reference"] == "https://eli.gov.pl/act/synthetic"
    from wilq.content.workflow.source_pack_v2 import SourcePackV2Preview

    tampered = dict(ready)
    tampered["facts"] = [dict(ready["facts"][0]) | {"text": "Unreviewed change."}]
    with pytest.raises(ValueError, match="Source pack identity"):
        SourcePackV2Preview.model_validate(tampered)
    tampered_card = dict(ready)
    tampered_card["service_binding"] = dict(ready["service_binding"]) | {
        "card_evidence_ids": ["unreviewed_card_evidence"]
    }
    with pytest.raises(ValueError, match="Source pack identity"):
        SourcePackV2Preview.model_validate(tampered_card)
    initial_hash = ready["source_pack_hash"]
    initial_registry_digest = ready["verification_registry_digest"]

    current["evidence"] = current["evidence"].model_copy(
        update={"current_evidence_ids": ["wp_rotated"], "catalog_evidence_ids": ["catalog_rotated"]}
    )
    facts["value"] = (_legal_packet_fact(), _unrelated_fact())
    rotated = _source_pack(client)
    assert rotated["source_pack_hash"] == initial_hash
    assert rotated["verification_registry_digest"] != initial_registry_digest

    facts["value"] = (
        ContentSourceFact.model_validate(
            _legal_packet_fact().model_dump(mode="json")
            | {"evidence_ids": ["legal_fact_evidence_rotated"]}
        ),
    )
    changed_fact_lineage = _source_pack(client)
    assert changed_fact_lineage["status"] == "blocked"
    assert changed_fact_lineage["blocker"]["code"] == "source_fact_authority_selection_changed"
    assert "Synthetic official requirement." not in str(changed_fact_lineage)

    facts["value"] = (_legal_packet_fact(),)
    from apps.api.wilq_api.routers import content_source_pack_v2 as pack_router

    changed_card = ContentKnowledgeCard.model_validate(
        _current_card().model_dump(mode="json")
        | {"evidence_ids": ["service_card_evidence_rotated"]}
    )
    monkeypatch.setattr(pack_router, "ekologus_content_knowledge_cards", lambda: (changed_card,))
    monkeypatch.setattr(
        authority_module, "ekologus_content_knowledge_cards", lambda: (changed_card,)
    )
    changed_card_lineage = _source_pack(client)
    assert changed_card_lineage["status"] == "blocked"
    assert changed_card_lineage["blocker"]["code"] == "source_fact_authority_selection_changed"
    assert "Synthetic official requirement." not in str(changed_card_lineage)
    monkeypatch.setattr(pack_router, "ekologus_content_knowledge_cards", lambda: (_current_card(),))
    monkeypatch.setattr(
        authority_module, "ekologus_content_knowledge_cards", lambda: (_current_card(),)
    )

    facts["value"] = (_legal_packet_fact(changed=True),)
    changed = _source_pack(client)
    assert changed["status"] == "blocked"
    assert changed["blocker"]["code"] == "source_fact_authority_selection_changed"
    assert "Changed synthetic official requirement." not in str(changed)

    facts["value"] = (_legal_packet_fact(),)
    current["evidence"] = current["evidence"].model_copy(
        update={"material_meaning_digest": "f" * 64}
    )
    material = _source_pack(client)
    assert material["status"] == "blocked"
    assert material["blocker"]["code"] == "material_meaning_changed"
    assert "Synthetic official requirement." not in str(material)


def test_public_source_pack_v2_requires_current_authority_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, _, _, facts = _runtime(tmp_path, monkeypatch)
    _patch_source_pack_router(monkeypatch, store, facts)
    response = client.get("/api/content/work-items/wi_source_authority_v2/source-pack-preview")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["blocker"]["code"] == "source_fact_authority_receipt_missing"


@pytest.mark.parametrize("case", ["private", "redaction"])
def test_public_source_pack_v2_rejects_unsafe_fact_text_without_exposure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    client, store, _, _, facts = _runtime(tmp_path, monkeypatch)
    _patch_source_pack_router(monkeypatch, store, facts)
    updates = (
        {
            "source_type": "reviewed_internal",
            "privacy_class": "private_local",
            "extracted_fact": "private credential secret text",
        }
        if case == "private"
        else {
            "source_url_or_path": ("https://www.ekologus.pl/authority-v2/?access_token=fakevalue")
        }
    )
    facts["value"] = (ContentSourceFact.model_validate(_fact().model_dump(mode="json") | updates),)
    action_id, _ = _preview(client, store)
    _run_lifecycle(client, action_id)
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic_wilku"},
    )
    assert applied.status_code == 200, applied.text
    packet = _source_pack(client)
    assert packet["status"] == "blocked"
    assert packet["facts"] == []
    assert packet["blocker"]["code"] == (
        "selected_source_fact_not_commit_safe"
        if case == "private"
        else "selected_source_fact_redaction_required"
    )
    assert "private credential secret text" not in str(packet)
    assert "access_token=fakevalue" not in str(packet)


@pytest.mark.parametrize("case", ["old_fact", "malformed_card", "no_expiry"])
def test_public_missing_source_currency_authority_blocks_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    client, store, _, _, facts = _runtime(tmp_path, monkeypatch)
    _patch_source_pack_router(monkeypatch, store, facts)
    if case == "old_fact":
        facts["value"] = (
            ContentSourceFact.model_validate(
                _fact().model_dump(mode="json") | {"freshness_date": "2020-01-01"}
            ),
        )
    elif case == "malformed_card":
        malformed = ContentKnowledgeCard.model_validate(
            _current_card().model_dump(mode="json") | {"freshness": "reviewed_bad-date"}
        )
        monkeypatch.setattr(
            authority_module, "ekologus_content_knowledge_cards", lambda: (malformed,)
        )
        pack_router = sys.modules.get("apps.api.wilq_api.routers.content_source_pack_v2")
        if pack_router is not None:
            monkeypatch.setattr(
                pack_router, "ekologus_content_knowledge_cards", lambda: (malformed,)
            )
    action_id, _ = _preview(client, store)
    _run_lifecycle(client, action_id)
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic_wilku"},
    )
    assert applied.status_code == 200, applied.text
    packet = _source_pack(client)
    assert packet["status"] == "blocked"
    assert packet["blocker"]["code"] == (
        "source_fact_older_than_current_service_card"
        if case == "old_fact"
        else "source_currency_policy_missing"
    )
    assert packet["blocker"]["owner"] == "WILQ content workflow"
    assert "fact_evidence" in packet["blocker"]["evidence_ids"]
    assert packet["facts"] == []


def test_public_official_guidance_without_exact_currency_policy_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, _, _, facts = _runtime(tmp_path, monkeypatch)
    _patch_source_pack_router(monkeypatch, store, facts)
    guidance = ContentSourceFact(
        source_id="official_guidance_fact",
        source_type="official_guidance",
        privacy_class="commit_safe",
        source_url_or_path="https://eur-lex.europa.eu/eli/reg/2025/40/oj/pol",
        extracted_fact="Synthetic guidance for one exact page.",
        scope="claim_policy",
        freshness_date="2026-09-23",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["guidance_evidence"],
        source_connectors=["official_guidance"],
        target_card_id=OFFICIAL_GUIDANCE_TARGET_CARD_ID,
        target_card_type=OFFICIAL_GUIDANCE_TARGET_CARD_TYPE,
        target_card_title=OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
        applicable_canonical_paths=["/authority-v2"],
    )
    facts["value"] = (guidance,)
    monkeypatch.setattr(authority_module, "ekologus_content_knowledge_cards", lambda: ())
    pack_router = sys.modules.get("apps.api.wilq_api.routers.content_source_pack_v2")
    if pack_router is not None:
        monkeypatch.setattr(pack_router, "ekologus_content_knowledge_cards", lambda: ())
    keep = store.load_latest_current_page_disposition_v2_receipt_for_work_item(
        "wi_source_authority_v2"
    )
    assert keep is not None
    preview = client.post(
        "/api/content/source-fact-authorities/preview",
        json={
            "work_item_id": "wi_source_authority_v2",
            "expected_keep_receipt_id": keep.receipt_id,
            "expected_keep_receipt_digest": keep.receipt_digest,
            "expected_material_meaning_digest": keep.snapshot.material_meaning_digest,
            "source_fact_ids": [guidance.source_id],
        },
    )
    assert preview.status_code == 200, preview.text
    action_id = preview.json()["action_id"]
    _run_lifecycle(client, action_id)
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic_wilku"},
    )
    assert applied.status_code == 200, applied.text
    packet = _source_pack(client)
    assert packet["status"] == "blocked"
    assert packet["blocker"]["code"] == "official_guidance_currency_policy_missing"
    assert packet["blocker"]["evidence_ids"] == ["guidance_evidence"]
    assert packet["facts"] == []
    assert "Synthetic guidance" not in str(packet)
