from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedger, ContentClaimLedgerEntry
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality import deterministic_revision_gate, semantic_review_service
from wilq.content.quality.deterministic_revision_gate import (
    ContentDeterministicRevisionGate,
    build_content_deterministic_revision_gate,
)
from wilq.content.quality.semantic_review_contracts import ContentSemanticReviewRequest
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionFaqItem,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionSection,
    ContentDraftRevisionSourceProvenance,
)


def _source_fact(
    *,
    source_id: str = "fact_public",
    privacy_class: str = "commit_safe",
    review_status: str = "approved",
    source_type: str = "public_site",
) -> ContentSourceFact:
    return ContentSourceFact.model_construct(
        source_id=source_id,
        source_type=source_type,
        privacy_class=privacy_class,
        source_url_or_path="https://www.ekologus.pl/source",
        extracted_fact="Ekologus porządkuje dokumentację środowiskową.",
        scope="service",
        freshness_date="2026-09-01",
        confidence=1.0,
        review_status=review_status,
        reviewer="wilku",
        evidence_ids=["ev_source"],
        source_connectors=["public_site"],
        target_card_id="service_card",
        target_card_type="service",
        target_card_title="Doradztwo",
    )


def _item() -> ContentWorkItem:
    return ContentWorkItem.model_construct(
        id="work_item_gate",
        topic="Dokumentacja środowiskowa",
        evidence_ids=["ev_source"],
        source_connectors=["public_site"],
        duplicate_status="checked",
        measurement_window_status="planned",
        measurement_window_id="measurement_gate",
    )


def _revision(*, title: str = "Zakres dokumentacji") -> ContentDraftRevision:
    return ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        revision_id="revision_gate",
        work_item_id="work_item_gate",
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="draft_gate",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        planning_input_digest="d" * 64,
        title=title,
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title=title,
            meta_title="Dokumentacja środowiskowa — Ekologus",
            meta_description="Sprawdź zakres dokumentacji środowiskowej.",
            h1=title,
            lead="Opisujemy bezpieczny następny krok dla firmy.",
            byline="Ekologus — lab-test",
        ),
        sections=[
            ContentDraftRevisionSection(
                section_id="section_gate",
                heading="Zakres dokumentacji",
                body_markdown=(
                    "Dokumentacja środowiskowa porządkuje obowiązki firmy i wskazuje "
                    "kolejne kroki do sprawdzenia przed zleceniem prac i rozmową z doradcą."
                ),
                evidence_ids=["ev_source"],
            )
        ],
        source_provenance=[
            ContentDraftRevisionSourceProvenance(
                source_fact_id="fact_public",
                source_url_or_path="https://www.ekologus.pl/source",
                freshness_date="2026-09-01",
                reviewer="wilku",
                evidence_ids=["ev_source"],
            )
        ],
        claim_ledger=None,
        created_by="wilku",
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
    )


def _brief() -> ContentSalesBrief:
    return ContentSalesBrief.model_construct(
        id="brief_gate",
        work_item_id="work_item_gate",
        topic="Dokumentacja środowiskowa",
        final_canonical_url="https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/",
        service_fit="Dopasowanie do usługi Ekologus.",
        search_intent="Firma chce sprawdzić zakres dokumentacji.",
        buyer_problem="Brak pewności, jakie dokumenty przygotować.",
        signal_quality=SimpleNamespace(status="strong"),
    )


def _gate(
    *,
    revision: ContentDraftRevision,
    facts: list[ContentSourceFact],
    claim_ledger: ContentClaimLedger | None = None,
):
    return build_content_deterministic_revision_gate(
        item=_item(),
        revision=revision,
        draft_package=None,
        claim_ledger=claim_ledger
        or ContentClaimLedger.model_construct(
            id="ledger_gate", work_item_id="work_item_gate", entries=[]
        ),
        sales_brief=_brief(),
        duplicate_risk="clear",
        source_facts=facts,
    )


def test_gate_passes_and_exposes_exact_binding_without_mutating_byline() -> None:
    revision = _revision()
    gate = _gate(revision=revision, facts=[_source_fact()])

    assert gate.status == "passed"
    assert gate.revision_id == revision.revision_id
    assert gate.revision_digest == revision.content_digest
    assert gate.byline == "Ekologus — lab-test"
    assert gate.byline_review == "lab_test"
    assert revision.page_assets is not None
    assert revision.page_assets.byline == "Ekologus — lab-test"


def test_unapproved_private_source_blocks_before_any_judge() -> None:
    source = _source_fact(privacy_class="private_local", review_status="review_required")
    gate = _gate(revision=_revision(), facts=[source])

    assert gate.status == "blocked"
    codes = {finding.code for finding in gate.findings}
    assert {"source_fact_not_approved", "source_fact_privacy_blocked"}.issubset(codes)


def test_unsupported_superlative_heading_blocks_without_evidenced_claim() -> None:
    gate = _gate(
        revision=_revision(title="Najlepsza dokumentacja środowiskowa"),
        facts=[_source_fact()],
    )

    assert gate.status == "blocked"
    assert "unsupported_superlative_heading" in {
        finding.code for finding in gate.findings
    }


@pytest.mark.parametrize(
    "title",
    [
        "Najwyższa jakość dokumentacji",
        "Najszybsza realizacja",
        "Najlepiej przygotowana dokumentacja",
    ],
)
def test_adopted_heading_exaggeration_stems_block(title: str) -> None:
    gate = _gate(revision=_revision(title=title), facts=[_source_fact()])

    assert gate.status == "blocked"
    assert "unsupported_superlative_heading" in {
        finding.code for finding in gate.findings
    }


def test_heading_support_requires_the_same_unblocked_claim_binding() -> None:
    revision = _revision()
    section = revision.sections[0].model_copy(
        update={
            "heading": "Najlepsza dokumentacja środowiskowa",
            "claim_ids": ["claim_supported"],
        }
    )
    assert revision.page_assets is not None
    revision = revision.model_copy(
        update={
            "sections": [section],
            "page_assets": revision.page_assets.model_copy(
                update={
                    "wordpress_title": "Dokumentacja środowiskowa",
                    "meta_title": "Dokumentacja środowiskowa — Ekologus",
                    "h1": "Dokumentacja środowiskowa",
                }
            ),
        }
    )
    ledger = ContentClaimLedger.model_construct(
        id="ledger_gate",
        work_item_id="work_item_gate",
        entries=[
            ContentClaimLedgerEntry.model_construct(
                id="claim_supported",
                claim_text="Najlepsza dokumentacja środowiskowa",
                claim_type="service_claim",
                status="allowed_with_evidence",
                evidence_ids=["ev_source"],
                source_connectors=["public_site"],
                reason="Testowy claim z dowodem.",
            )
        ],
    )

    gate = _gate(revision=revision, facts=[_source_fact()], claim_ledger=ledger)

    assert "unsupported_superlative_heading" not in {
        finding.code for finding in gate.findings
    }


def test_heading_support_does_not_use_unbound_or_inconsistent_claim() -> None:
    revision = _revision(title="Najlepsza dokumentacja środowiskowa")
    ledger = ContentClaimLedger.model_construct(
        id="ledger_gate",
        work_item_id="work_item_gate",
        entries=[
            ContentClaimLedgerEntry.model_construct(
                id="claim_unbound",
                claim_text="Najlepsza dokumentacja środowiskowa",
                claim_type="service_claim",
                status="allowed_with_evidence",
                evidence_ids=["ev_source"],
                source_connectors=[],
                reason="Brakuje źródła danych.",
            )
        ],
    )

    gate = _gate(revision=revision, facts=[_source_fact()], claim_ledger=ledger)

    assert gate.status == "blocked"
    assert "unsupported_superlative_heading" in {
        finding.code for finding in gate.findings
    }


def test_faq_question_is_scanned_for_heading_exaggeration() -> None:
    revision = _revision().model_copy(
        update={
            "faq": [
                ContentDraftRevisionFaqItem.model_construct(
                    faq_id="faq_gate",
                    question="Najlepsze szkolenia BDO?",
                    answer_markdown="Sprawdź zakres szkolenia z doradcą.",
                    evidence_ids=["ev_source"],
                    claim_ids=[],
                )
            ]
        }
    )

    gate = _gate(revision=revision, facts=[_source_fact()])

    assert gate.status == "blocked"
    faq_findings = [
        finding
        for finding in gate.findings
        if finding.code == "unsupported_superlative_heading"
    ]
    assert any(finding.affected_target == "faq:faq_gate" for finding in faq_findings)


def test_every_exaggeration_term_requires_its_own_bound_claim() -> None:
    revision = _revision()
    section = revision.sections[0].model_copy(
        update={
            "heading": "Najlepsza i najszybsza dokumentacja",
            "claim_ids": ["claim_best"],
        }
    )
    assert revision.page_assets is not None
    revision = revision.model_copy(
        update={
            "sections": [section],
            "page_assets": revision.page_assets.model_copy(
                update={
                    "wordpress_title": "Dokumentacja środowiskowa",
                    "meta_title": "Dokumentacja środowiskowa — Ekologus",
                    "h1": "Dokumentacja środowiskowa",
                }
            ),
        }
    )
    ledger = ContentClaimLedger.model_construct(
        id="ledger_gate",
        work_item_id="work_item_gate",
        entries=[
            ContentClaimLedgerEntry.model_construct(
                id="claim_best",
                claim_text="Najlepsza dokumentacja",
                claim_type="service_claim",
                status="allowed_with_evidence",
                evidence_ids=["ev_source"],
                source_connectors=["public_site"],
                reason="Testowy claim z dowodem.",
            )
        ],
    )

    gate = _gate(revision=revision, facts=[_source_fact()], claim_ledger=ledger)

    findings = [
        finding
        for finding in gate.findings
        if finding.code == "unsupported_superlative_heading"
    ]
    assert gate.status == "blocked"
    assert any("najszybsza" in finding.reason.casefold() for finding in findings)


def test_gate_result_is_typed_contract() -> None:
    gate = _gate(revision=_revision(), facts=[_source_fact()])

    assert isinstance(gate, ContentDeterministicRevisionGate)
    assert gate.contract == "wilq_deterministic_revision_gate_v1"


def test_blocked_gate_stops_semantic_model_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    item = _item()
    revision = _revision()
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=item.id,
        planning_digest=revision.planning_digest,
        planning_input_digest=revision.planning_input_digest,
        content_kind="editorial",
        service_card_id=None,
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id=item.id,
        planning_input_digest=revision.planning_input_digest,
    )
    snapshot = SimpleNamespace(
        preflight=SimpleNamespace(item=item),
        revision_workspace=SimpleNamespace(latest_revision=revision, context_current=True),
        planning_workspace=SimpleNamespace(proposal=proposal),
        claim_ledger=ContentClaimLedger.model_construct(
            id="ledger_gate",
            work_item_id=item.id,
            entries=[],
        ),
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=None)
        ),
        sales_brief=SimpleNamespace(sales_brief_result=SimpleNamespace(brief=_brief())),
    )
    monkeypatch.setattr(
        semantic_review_service,
        "build_content_planning_input",
        lambda *_args, **_kwargs: SimpleNamespace(planning_input=planning_input, blockers=[]),
    )
    monkeypatch.setattr(
        deterministic_revision_gate,
        "ekologus_source_facts",
        lambda: [_source_fact(privacy_class="private_local", review_status="review_required")],
    )

    class Store:
        def for_revision(self, *_args):
            return None

        def write_ready(self):
            raise AssertionError("deterministic blocker must stop before storage/model")

    class Client:
        def run_structured_turn(self, *_args):
            raise AssertionError("deterministic blocker must stop before model")

    result = semantic_review_service.generate_content_semantic_review(
        snapshot=snapshot,
        revision_id=revision.revision_id,
        request=ContentSemanticReviewRequest(
            expected_revision_digest=revision.content_digest,
            requested_by="wilku",
        ),
        client=Client(),
        store=Store(),
        run_store=SimpleNamespace(),
    )

    assert result.status == "blocked"
    assert result.blockers[0].code == "deterministic_quality_gate_failed"
    assert "source_fact_not_approved" in result.blockers[0].source_codes
