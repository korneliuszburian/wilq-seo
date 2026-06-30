from __future__ import annotations

from wilq.content.claims.ledger import (
    ContentClaimLedger,
    ContentClaimLedgerEntry,
    claim_ledger_allows_draft,
    claim_ledger_blockers,
    claim_source_connectors_required,
    content_claim_entry,
    publish_ready_claims,
)


def _ledger(*entries: ContentClaimLedgerEntry) -> ContentClaimLedger:
    return ContentClaimLedger(
        id="claim_ledger_bdo",
        work_item_id="content_work_item_bdo",
        entries=list(entries),
    )


def test_guarantee_claim_is_blocked_from_publish_ready_language() -> None:
    entry = content_claim_entry(
        claim_id="claim_ranking_guarantee",
        claim_text="Gwarantujemy wzrost pozycji po publikacji.",
        claim_type="guarantee_claim",
    )
    ledger = _ledger(entry)

    assert entry.status == "blocked"
    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == ["blocked_claim"]
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)


def test_seo_and_business_outcome_claims_wait_for_measurement_window() -> None:
    ledger = _ledger(
        content_claim_entry(
            claim_id="claim_more_leads",
            claim_text="Ta treść zwiększy liczbę leadów.",
            claim_type="business_outcome_claim",
            evidence_ids=["ev_gsc_bdo"],
            measurement_window_ready=False,
        )
    )

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "blocked_until_measurement"
    ]
    assert not claim_ledger_allows_draft(ledger)


def test_legal_and_environmental_claims_need_human_review() -> None:
    ledger = _ledger(
        content_claim_entry(
            claim_id="claim_full_compliance",
            claim_text="Usługa zapewnia pełną zgodność z wymaganiami środowiskowymi.",
            claim_type="legal_requirement_claim",
            evidence_ids=["ev_service_note"],
        )
    )

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "needs_human_review"
    ]
    assert not claim_ledger_allows_draft(ledger)


def test_allowed_with_evidence_claim_can_be_used_in_draft() -> None:
    entry = content_claim_entry(
        claim_id="claim_service_scope",
        claim_text="Ekologus pomaga firmom w obowiązkach związanych z BDO.",
        claim_type="service_claim",
        evidence_ids=["ev_service_map_bdo"],
    )
    ledger = _ledger(entry)

    assert entry.status == "allowed_with_evidence"
    assert claim_ledger_blockers(ledger) == []
    assert claim_ledger_allows_draft(ledger)
    assert publish_ready_claims(ledger) == [entry]
    assert claim_source_connectors_required(ledger.entries)


def test_human_review_allows_legal_claim_only_when_supported() -> None:
    entry = content_claim_entry(
        claim_id="claim_environmental_reviewed",
        claim_text="Tekst opisuje ogólne ryzyka środowiskowe bez gwarancji zgodności.",
        claim_type="environmental_claim",
        evidence_ids=["ev_expert_note"],
        human_reviewed=True,
        reviewer_id="wilku",
    )
    ledger = _ledger(entry)

    assert entry.status == "allowed_with_evidence"
    assert entry.reviewer_id == "wilku"
    assert claim_ledger_blockers(ledger) == []


def test_allowed_with_evidence_status_without_evidence_blocks_draft() -> None:
    entry = ContentClaimLedgerEntry(
        id="claim_bad_status",
        claim_text="Ekologus ma potwierdzony fakt bez dowodu.",
        claim_type="service_claim",
        status="allowed_with_evidence",
        evidence_ids=[],
        reason="Błędny status testowy.",
    )
    ledger = _ledger(entry)

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "missing_evidence"
    ]
    assert not claim_ledger_allows_draft(ledger)
