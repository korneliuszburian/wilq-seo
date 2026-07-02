from __future__ import annotations

from _marketer_language import assert_marketer_text_has_no_workflow_jargon

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
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in claim_ledger_blockers(ledger)
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
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
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in claim_ledger_blockers(ledger)
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
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
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in claim_ledger_blockers(ledger)
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
    assert not claim_ledger_allows_draft(ledger)


def test_allowed_with_evidence_claim_can_be_used_in_draft() -> None:
    entry = content_claim_entry(
        claim_id="claim_service_scope",
        claim_text="Ekologus pomaga firmom w obowiązkach związanych z BDO.",
        claim_type="service_claim",
        evidence_ids=["ev_service_map_bdo"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
        strength="weak",
        required=True,
    )
    ledger = _ledger(entry)

    assert entry.status == "allowed_with_evidence"
    assert entry.strength == "weak"
    assert entry.required is True
    assert entry.source_connectors == ["google_search_console", "wordpress_ekologus"]
    assert claim_ledger_blockers(ledger) == []
    assert claim_ledger_allows_draft(ledger)
    assert publish_ready_claims(ledger) == [entry]
    assert claim_source_connectors_required(ledger.entries)


def test_blocked_claims_do_not_block_draft_when_safe_claim_exists() -> None:
    safe = content_claim_entry(
        claim_id="claim_content_source",
        claim_text="WILQ ma dowody źródłowe, że istniejąca treść wymaga odświeżenia.",
        claim_type="service_claim",
        evidence_ids=["ev_gsc_bdo"],
        source_connectors=["google_search_console", "wordpress_ekologus"],
    )
    blocked = content_claim_entry(
        claim_id="claim_more_leads",
        claim_text="Ta treść zwiększy liczbę leadów.",
        claim_type="business_outcome_claim",
        evidence_ids=["ev_gsc_bdo"],
        source_connectors=["google_search_console"],
    )
    ledger = _ledger(safe, blocked)

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "blocked_until_measurement"
    ]
    assert publish_ready_claims(ledger) == [safe]
    assert claim_ledger_allows_draft(ledger)


def test_service_claim_without_evidence_cannot_be_publish_ready() -> None:
    entry = content_claim_entry(
        claim_id="claim_unsourced_service",
        claim_text="Ekologus pomaga firmom w obowiązkach środowiskowych.",
        claim_type="service_claim",
    )
    ledger = _ledger(entry)

    assert entry.status == "allowed_general"
    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "missing_evidence"
    ]
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)


def test_human_review_allows_legal_claim_only_when_supported() -> None:
    entry = content_claim_entry(
        claim_id="claim_environmental_reviewed",
        claim_text="Tekst opisuje ogólne ryzyka środowiskowe bez gwarancji zgodności.",
        claim_type="environmental_claim",
        evidence_ids=["ev_expert_note"],
        source_connectors=["reviewed_internal"],
        human_reviewed=True,
        reviewer_id="wilku",
    )
    ledger = _ledger(entry)

    assert entry.status == "allowed_with_evidence"
    assert entry.reviewer_id == "wilku"
    assert claim_ledger_blockers(ledger) == []


def test_human_review_does_not_replace_evidence_for_legal_claim() -> None:
    entry = content_claim_entry(
        claim_id="claim_reviewed_without_evidence",
        claim_text="Ekologus potwierdza pełną zgodność z wymaganiami środowiskowymi.",
        claim_type="legal_requirement_claim",
        human_reviewed=True,
        reviewer_id="wilku",
    )
    ledger = _ledger(entry)

    assert entry.status == "needs_human_review"
    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "missing_evidence"
    ]
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)


def test_forged_reviewed_environmental_claim_without_evidence_blocks_draft() -> None:
    entry = ContentClaimLedgerEntry(
        id="claim_forged_reviewed_environmental",
        claim_text="Ekologus zapewnia zgodność środowiskową po audycie.",
        claim_type="environmental_claim",
        status="allowed_general",
        evidence_ids=[],
        source_connectors=[],
        reason="Błędny ręczny wpis po review.",
        reviewer_id="wilku",
    )
    ledger = _ledger(entry)

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "missing_evidence"
    ]
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)


def test_allowed_with_evidence_status_without_source_connector_blocks_draft() -> None:
    entry = ContentClaimLedgerEntry(
        id="claim_missing_connector",
        claim_text="Ekologus ma potwierdzony fakt bez źródła danych.",
        claim_type="service_claim",
        status="allowed_with_evidence",
        evidence_ids=["ev_public_source"],
        source_connectors=[],
        reason="Błędny status testowy.",
    )
    ledger = _ledger(entry)

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "missing_source_connector"
    ]
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in claim_ledger_blockers(ledger)
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)


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
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in claim_ledger_blockers(ledger)
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
    assert not claim_ledger_allows_draft(ledger)


def test_product_claim_without_merchant_or_shop_evidence_blocks_draft() -> None:
    entry = content_claim_entry(
        claim_id="claim_product_offer_without_shop",
        claim_text="Kup sorbenty Ekologus jako sprawdzone rozwiązanie dla zakładu.",
        claim_type="product_claim",
        evidence_ids=["ev_public_article"],
        source_connectors=["wordpress_ekologus"],
    )
    ledger = _ledger(entry)

    assert entry.status == "allowed_with_evidence"
    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "missing_product_evidence"
    ]
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)


def test_product_claim_with_merchant_evidence_can_feed_draft() -> None:
    entry = content_claim_entry(
        claim_id="claim_product_offer_with_merchant",
        claim_text="Ekologus ma produkt sorpcyjny do sprawdzenia w sklepie.",
        claim_type="product_claim",
        evidence_ids=["ev_merchant_product"],
        source_connectors=["google_merchant_center"],
    )
    ledger = _ledger(entry)

    assert entry.status == "allowed_with_evidence"
    assert claim_ledger_blockers(ledger) == []
    assert publish_ready_claims(ledger) == [entry]
    assert claim_ledger_allows_draft(ledger)


def test_forged_guarantee_claim_cannot_be_marked_allowed() -> None:
    entry = ContentClaimLedgerEntry(
        id="claim_forged_guarantee",
        claim_text="Gwarantujemy pierwsze miejsce w Google.",
        claim_type="guarantee_claim",
        status="allowed_general",
        evidence_ids=[],
        reason="Błędny ręczny wpis.",
    )
    ledger = _ledger(entry)

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "blocked_claim"
    ]
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)


def test_forged_legal_claim_allowed_without_reviewer_blocks_draft() -> None:
    entry = ContentClaimLedgerEntry(
        id="claim_forged_legal",
        claim_text="Ekologus zapewnia pełną zgodność z aktualnym prawem.",
        claim_type="legal_requirement_claim",
        status="allowed_with_evidence",
        evidence_ids=["ev_public_source"],
        reason="Błędny ręczny wpis.",
    )
    ledger = _ledger(entry)

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "needs_human_review"
    ]
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)


def test_forged_measurement_claim_allowed_general_waits_for_measurement() -> None:
    entry = ContentClaimLedgerEntry(
        id="claim_forged_seo_result",
        claim_text="Ten szkic poprawi widoczność SEO.",
        claim_type="seo_claim",
        status="allowed_general",
        evidence_ids=[],
        reason="Błędny ręczny wpis.",
    )
    ledger = _ledger(entry)

    assert [blocker.code for blocker in claim_ledger_blockers(ledger)] == [
        "blocked_until_measurement"
    ]
    assert publish_ready_claims(ledger) == []
    assert not claim_ledger_allows_draft(ledger)
