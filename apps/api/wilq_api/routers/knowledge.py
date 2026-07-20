from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.knowledge.source_materials import ekologus_source_materials
from wilq.knowledge.compilers.playbook_compiler import (
    compile_playbook_cards,
    condense_playbooks,
    get_playbook,
    list_playbooks,
)
from wilq.knowledge.operating_map import build_knowledge_operating_map_cached
from wilq.knowledge.taxonomy import list_knowledge_taxonomy
from wilq.schemas import (
    KnowledgeCard,
    KnowledgeCompilerResult,
    KnowledgeOperatingMapResponse,
    KnowledgeSourceFactView,
    KnowledgeSourceMaterialReadiness,
    KnowledgeSourceMaterialView,
    KnowledgeTaxonomyEntry,
    MarketingPlaybook,
)

router = APIRouter()


@router.get("/api/knowledge/cards", response_model=list[KnowledgeCard])
def knowledge_cards() -> list[KnowledgeCard]:
    return compile_playbook_cards()


@router.get("/api/knowledge/source-facts", response_model=list[KnowledgeSourceFactView])
def knowledge_source_facts() -> list[KnowledgeSourceFactView]:
    """Expose the real, redacted source corpus separately from system playbooks."""
    return [
        KnowledgeSourceFactView(
            source_id=fact.source_id,
            source_type=fact.source_type,
            privacy_class=fact.privacy_class,
            source_url_or_path=fact.source_url_or_path,
            extracted_fact=fact.extracted_fact,
            scope=fact.scope,
            freshness_date=fact.freshness_date,
            confidence=fact.confidence,
            review_status=fact.review_status,
            generation_status=(
                "eligible"
                if fact.review_status == "approved"
                and (
                    fact.privacy_class == "commit_safe"
                    or (
                        fact.privacy_class == "redacted_only"
                        and fact.source_type == "reviewed_internal"
                    )
                )
                and fact.evidence_ids
                else "blocked_review_required"
            ),
            reviewer=fact.reviewer,
            evidence_ids=fact.evidence_ids,
            source_connectors=fact.source_connectors,
            target_card_id=fact.target_card_id,
            target_card_title=fact.target_card_title,
            blocked_claims=fact.blocked_claims,
            usage_notes=fact.usage_notes,
        )
        for fact in ekologus_source_facts()
    ]


@router.get("/api/knowledge/source-materials", response_model=list[KnowledgeSourceMaterialView])
def knowledge_source_materials() -> list[KnowledgeSourceMaterialView]:
    """Expose the approved-corpus manifest without copying private source text."""
    return [
        KnowledgeSourceMaterialView.model_validate(material.model_dump())
        for material in ekologus_source_materials()
    ]


@router.get(
    "/api/knowledge/source-materials/readiness",
    response_model=KnowledgeSourceMaterialReadiness,
)
def knowledge_source_material_readiness() -> KnowledgeSourceMaterialReadiness:
    """Expose the corpus gate without exposing source text or private payloads."""
    materials = ekologus_source_materials()
    counts = {status: 0 for status in ("imported", "import_pending", "excerpt_review_required")}
    for material in materials:
        counts[material.import_status] += 1
    imported = counts["imported"]
    pending = counts["import_pending"]
    excerpt_review = counts["excerpt_review_required"]
    imported_materials = [
        KnowledgeSourceMaterialView.model_validate(material.model_dump())
        for material in materials
        if material.import_status == "imported"
    ]
    pending_materials = [
        KnowledgeSourceMaterialView.model_validate(material.model_dump())
        for material in materials
        if material.import_status == "import_pending"
    ]
    excerpt_review_materials = [
        KnowledgeSourceMaterialView.model_validate(material.model_dump())
        for material in materials
        if material.import_status == "excerpt_review_required"
    ]
    if pending:
        return KnowledgeSourceMaterialReadiness(
            status="import_pending",
            total_count=len(materials),
            imported_count=imported,
            import_pending_count=pending,
            excerpt_review_required_count=excerpt_review,
            ready_for_generation=False,
            imported_materials=imported_materials,
            pending_materials=pending_materials,
            excerpt_review_materials=excerpt_review_materials,
            blocker=(
                f"Zaimportowano {imported} z {len(materials)} zatwierdzonych materiałów; "
                "pozostała część korpusu nie jest jeszcze dostępna dla generowania."
            ),
            next_step=(
                "Dla konkretnej strony używaj wyłącznie widocznych faktów z lineage; "
                "pozostałe redagowane excerpty aktywuj kontrolowanym importem po owner review."
            ),
        )
    if excerpt_review:
        return KnowledgeSourceMaterialReadiness(
            status="excerpt_review_required",
            total_count=len(materials),
            imported_count=imported,
            import_pending_count=pending,
            excerpt_review_required_count=excerpt_review,
            ready_for_generation=False,
            imported_materials=imported_materials,
            pending_materials=pending_materials,
            excerpt_review_materials=excerpt_review_materials,
            blocker=(
                "Część materiałów wymaga przeglądu redagowanych excerptów przed "
                "użyciem generatywnym."
            ),
            next_step="Zatwierdź excerpty i ich lineage dla konkretnych kart usług.",
        )
    return KnowledgeSourceMaterialReadiness(
        status="ready",
        total_count=len(materials),
        imported_count=imported,
        import_pending_count=pending,
        excerpt_review_required_count=excerpt_review,
        ready_for_generation=True,
        imported_materials=imported_materials,
        pending_materials=pending_materials,
        excerpt_review_materials=excerpt_review_materials,
        next_step="Można używać wyłącznie zaimportowanych faktów z zachowanym lineage.",
    )


@router.get("/api/knowledge/search")
def knowledge_search(q: str = "") -> list[dict[str, Any]]:
    query = q.lower()
    cards = compile_playbook_cards()
    if query:
        cards = [
            card for card in cards if query in card.title.lower() or query in card.summary.lower()
        ]
    return [card.model_dump(mode="json") for card in cards]


@router.get("/api/knowledge/taxonomy", response_model=list[KnowledgeTaxonomyEntry])
def knowledge_taxonomy() -> list[KnowledgeTaxonomyEntry]:
    return list(list_knowledge_taxonomy())


@router.get("/api/knowledge/playbooks", response_model=list[MarketingPlaybook])
def knowledge_playbooks() -> list[MarketingPlaybook]:
    return list(list_playbooks())


@router.get("/api/knowledge/playbooks/{playbook_id}", response_model=MarketingPlaybook)
def knowledge_playbook_detail(playbook_id: str) -> MarketingPlaybook:
    playbook = get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(status_code=404, detail=f"Unknown playbook: {playbook_id}")
    return playbook


@router.get("/api/knowledge/operating-map", response_model=KnowledgeOperatingMapResponse)
def knowledge_operating_map() -> KnowledgeOperatingMapResponse:
    return build_knowledge_operating_map_cached()


@router.post("/api/knowledge/condense", response_model=KnowledgeCompilerResult)
def knowledge_condense() -> KnowledgeCompilerResult:
    return condense_playbooks()
