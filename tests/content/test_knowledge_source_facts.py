from apps.api.wilq_api.routers.knowledge import (
    knowledge_source_facts,
    knowledge_source_material_readiness,
    knowledge_source_materials,
)
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards


def test_knowledge_surface_exposes_real_redacted_source_facts_not_playbook_claims() -> None:
    facts = knowledge_source_facts()

    assert len(facts) == 21
    public = next(item for item in facts if item.source_id == "ekologus_public_bdo_faq_2026_07_01")
    assert public.extracted_fact.startswith("Publiczny artykuł Ekologus omawia BDO")
    assert public.source_url_or_path.startswith("https://www.ekologus.pl/")
    assert public.evidence_ids == ["ev_content_service_profile_source_facts"]
    assert public.generation_status == "eligible"

    private = next(item for item in facts if "review_candidate" in item.source_id)
    assert private.privacy_class == "redacted_only"
    assert private.review_status == "review_required"
    assert private.evidence_ids == []
    assert private.generation_status == "blocked_review_required"


def test_knowledge_source_material_manifest_is_metadata_only_and_complete() -> None:
    materials = knowledge_source_materials()

    assert len(materials) == 15
    assert sum(item.import_status == "imported" for item in materials) == 7
    assert sum(item.import_status == "import_pending" for item in materials) == 8
    assert all(item.privacy_class == "redacted_only" for item in materials)
    assert all(item.source_path.startswith("materials_clean/approved/") for item in materials)


def test_knowledge_source_material_readiness_blocks_pending_corpus_without_exposing_text() -> None:
    readiness = knowledge_source_material_readiness()

    assert readiness.status == "import_pending"
    assert readiness.total_count == 15
    assert readiness.imported_count == 7
    assert readiness.import_pending_count == 8
    assert readiness.ready_for_generation is False
    assert readiness.blocker
    assert "excerpt" in readiness.next_step


def test_imported_material_facts_preserve_card_lineage() -> None:
    cards = ekologus_content_knowledge_cards()

    audit = next(card for card in cards if card.id == "ekologus_service_compliance_audit")
    assert audit.source_material_ids == ["ekologus_material_kb003"]
    assert audit.evidence_ids == ["ev_content_approved_source_materials_manifest"]
