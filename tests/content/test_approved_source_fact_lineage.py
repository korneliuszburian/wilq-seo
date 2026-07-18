from __future__ import annotations

from wilq.content.knowledge.source_facts import ContentSourceFact, ContentSourceFactRegistry
from wilq.content.workflow import decision_mapping
from wilq.content.workflow.decision_mapping import content_sales_brief_seed_from_decision
from wilq.schemas import ContentDecisionItem


def _fact(source_id: str, review_status: str) -> ContentSourceFact:
    return ContentSourceFact(
        source_id=source_id,
        source_type="reviewed_internal",
        privacy_class="redacted_only",
        source_url_or_path="internal://approved-material",
        extracted_fact="Fakt źródłowy.",
        scope="service",
        freshness_date="2026-07-18",
        confidence=0.9,
        review_status=review_status,
        reviewer="wilku" if review_status == "approved" else None,
        evidence_ids=["ev_shared"],
        source_connectors=["approved_materials"],
        blocked_claims=["brak gwarancji"] if review_status != "approved" else [],
        target_card_id="ekologus_service_lineage",
        target_card_type="service",
        target_card_title="Usługa testowa",
        evidence_requirements=["review"] if review_status != "approved" else [],
        usage_notes=["review first"] if review_status != "approved" else [],
    )


def test_decision_mapping_excludes_unapproved_source_fact_ids(monkeypatch) -> None:
    registry = ContentSourceFactRegistry(
        facts=[
            _fact("approved_material", "approved"),
            _fact("pending_material", "review_required"),
        ],
        fact_count=2,
    )
    monkeypatch.setattr(decision_mapping, "ekologus_source_fact_registry", lambda: registry)
    decision = ContentDecisionItem(
        id="lineage",
        decision_type="refresh_or_merge",
        title="Usługa testowa",
        queries=["usługa testowa"],
        evidence_ids=["ev_shared"],
        source_connectors=["approved_materials"],
        rationale="Sprawdzenie lineage.",
        next_step="Review.",
        source_public_url="https://www.ekologus.pl/usluga-testowa/",
        final_canonical_url="https://www.ekologus.pl/usluga-testowa/",
        intended_final_url="https://www.ekologus.pl/usluga-testowa/",
        inventory_gate_status="confirmed_current_inventory",
        duplicate_gate_status="checked",
    )

    seed = content_sales_brief_seed_from_decision(decision)

    assert seed.source_facts[0].source_fact_ids == ["approved_material"]
