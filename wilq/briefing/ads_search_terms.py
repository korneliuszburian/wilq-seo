from __future__ import annotations

from wilq.actions.google_ads.custom_segments import CUSTOM_SEGMENT_ACTION_ID
from wilq.actions.google_ads.negative_keywords import NEGATIVE_KEYWORD_ACTION_ID
from wilq.schemas import (
    ActionRisk,
    AdsDiagnosticSection,
    AdsKeywordMatchContextReadContract,
    AdsSearchTermNgramReadContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermsReadContract,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"


def build_search_terms_section(
    search_terms_read_contract: AdsSearchTermsReadContract,
    action_ids: list[str],
) -> AdsDiagnosticSection:
    allowed_ids = {CUSTOM_SEGMENT_ACTION_ID, NEGATIVE_KEYWORD_ACTION_ID}
    filtered_action_ids = [action_id for action_id in action_ids if action_id in allowed_ids]
    if search_terms_read_contract.search_term_rows:
        metric_facts = [
            fact for row in search_terms_read_contract.search_term_rows for fact in row.metric_facts
        ]
        return AdsDiagnosticSection(
            id="ads_search_terms",
            title="Zapytania użytkowników Google Ads",
            status="ready",
            summary=search_terms_read_contract.summary,
            diagnosis=(
                "WILQ ma wiersze zapytań z Google Ads. To jeszcze nie "
                "odblokowuje wykluczeń: brakuje kontekstu dopasowania, 90-dniowego "
                "kontroli bezpieczeństwa i akcji do sprawdzenia."
            ),
            next_step=search_terms_read_contract.next_step,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=search_terms_read_contract.evidence_ids,
            metric_facts=metric_facts[:12],
            action_ids=filtered_action_ids,
            blocked_claims=search_terms_read_contract.blocked_claims,
            risk=ActionRisk.medium,
        )
    return AdsDiagnosticSection(
        id="ads_search_terms",
        title="Zapytania użytkowników Google Ads",
        status="blocked",
        summary=search_terms_read_contract.summary,
        diagnosis=(
            "Twarda ocena wymaga wyszukiwanych haseł, kosztu, konwersji i 90-dniowej kontroli "
            "ochronnej przed wykluczeniami. WILQ nie może z tego tworzyć propozycji "
            "wykluczających słów kluczowych bez kompletnych dowodów."
        ),
        next_step=search_terms_read_contract.next_step,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=search_terms_read_contract.evidence_ids,
        action_ids=filtered_action_ids,
        blocked_claims=search_terms_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_search_term_ngram_section(
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact for row in search_term_ngram_read_contract.ngram_rows for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_search_term_ngrams",
        title="N-gramy zapytań Google Ads",
        status=search_term_ngram_read_contract.status,
        summary=search_term_ngram_read_contract.summary,
        diagnosis=(
            "N-gramy kondensują powtarzające się tematy w wyszukiwanych hasłach. "
            "To pomaga szybciej znaleźć obszary do ręcznej oceny, ale nie jest "
            "oceną straty budżetu ani gotową zmianą wykluczeń."
        ),
        next_step=search_term_ngram_read_contract.next_step,
        source_connectors=search_term_ngram_read_contract.source_connectors,
        evidence_ids=search_term_ngram_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=search_term_ngram_read_contract.action_ids,
        blocked_claims=search_term_ngram_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_search_term_safety_section(
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact for row in search_term_safety_read_contract.safety_rows for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_search_term_safety",
        title="90-dniowy odczyt bezpieczeństwa zapytań",
        status=search_term_safety_read_contract.status,
        summary=search_term_safety_read_contract.summary,
        diagnosis=(
            "Ten kontrakt chroni przed pochopnym wykluczeniem zapytań. "
            "WILQ sprawdza dłuższe okno, ale nadal blokuje zapis zmian bez intencji, "
            "kontekstu dopasowania i podglądu zmian."
        ),
        next_step=search_term_safety_read_contract.next_step,
        source_connectors=search_term_safety_read_contract.source_connectors,
        evidence_ids=search_term_safety_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=[],
        blocked_claims=search_term_safety_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_keyword_match_context_section(
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for row in keyword_match_context_read_contract.context_rows
        for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_keyword_match_context",
        title="Kontekst dopasowań słów kluczowych",
        status=keyword_match_context_read_contract.status,
        summary=keyword_match_context_read_contract.summary,
        diagnosis=(
            "Ten kontrakt pokazuje istniejące słowa kluczowe i typy dopasowań w Google Ads. "
            "Pomaga zrozumieć, skąd mogło przyjść wyszukiwane hasło, ale nie jest zgodą "
            "na dodanie wykluczenia."
        ),
        next_step=keyword_match_context_read_contract.next_step,
        source_connectors=keyword_match_context_read_contract.source_connectors,
        evidence_ids=keyword_match_context_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=[],
        blocked_claims=keyword_match_context_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )
