from __future__ import annotations

from wilq.actions.google_ads.campaign_review import CAMPAIGN_REVIEW_ACTION_ID
from wilq.schemas import (
    ActionRisk,
    AdsBudgetPacingReadContract,
    AdsCampaignReadContract,
    AdsCampaignTriageReadContract,
    AdsChangeHistoryReadContract,
    AdsDecisionItem,
    AdsDerivedKpiReadContract,
    AdsImpressionShareReadContract,
    AdsRecommendationsReadContract,
    AdsSearchTermNgramReadContract,
    AdsSearchTermsReadContract,
)


def build_campaign_activity_decision(
    campaign_read_contract: AdsCampaignReadContract,
    *,
    action_ids: list[str],
    missing_read_contracts: list[str],
) -> AdsDecisionItem:
    metric_facts = [
        fact for row in campaign_read_contract.campaign_rows for fact in row.metric_facts
    ]
    campaign_review_action_ids = [
        action_id for action_id in action_ids if action_id == CAMPAIGN_REVIEW_ACTION_ID
    ]
    return AdsDecisionItem(
        id="ads_review_campaign_activity",
        decision_type="review_campaign_activity",
        status="ready",
        title="Przejrzyj aktywność kampanii Google Ads",
        summary=campaign_read_contract.summary,
        rationale=(
            "To jest uczciwy pierwszy przegląd kampanii: WILQ widzi kliknięcia, "
            "wyświetlenia, koszt, konwersje i wartość konwersji po kampaniach. "
            "Nie ma jeszcze pełnego kontraktu rekomendacji, impression share "
            "ani historii zmian."
        ),
        next_step=(
            "Sprawdź kampanie z największym kosztem i ruchem w tabeli dowodów. "
            "Nie podejmuj decyzji budżetowych bez brakujących danych."
        ),
        allowed_metrics=campaign_read_contract.allowed_metrics,
        missing_read_contracts=missing_read_contracts,
        source_connectors=campaign_read_contract.source_connectors,
        evidence_ids=campaign_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        campaign_rows=campaign_read_contract.campaign_rows,
        operator_review_gates=list(
            dict.fromkeys(
                gate
                for row in campaign_read_contract.campaign_rows
                for gate in row.human_review_gates
            )
        ),
        action_ids=campaign_review_action_ids,
        blocked_claims=campaign_read_contract.blocked_claims,
        risk=ActionRisk.low,
    )


def build_campaign_triage_decision(
    campaign_triage_read_contract: AdsCampaignTriageReadContract,
) -> AdsDecisionItem:
    return AdsDecisionItem(
        id="ads_review_campaign_triage",
        decision_type="review_campaign_triage",
        status="ready",
        title="Ustal kolejność oceny kampanii Ads",
        summary=campaign_triage_read_contract.summary,
        rationale=(
            "Ta kolejka łączy kampanie, wskaźniki, tempo wydawania budżetu, rekomendacje "
            "i udział w wyświetleniach w jeden widok decyzyjny. WILQ pokazuje, "
            "co sprawdzić najpierw, ale nadal blokuje ocenę strat budżetu, "
            "opłacalności, zapis zmian budżetu i zapis rekomendacji."
        ),
        next_step=campaign_triage_read_contract.next_step,
        allowed_metrics=campaign_triage_read_contract.allowed_metrics,
        missing_read_contracts=campaign_triage_read_contract.missing_read_contracts,
        source_connectors=campaign_triage_read_contract.source_connectors,
        evidence_ids=campaign_triage_read_contract.evidence_ids,
        campaign_triage_rows=campaign_triage_read_contract.triage_rows,
        operator_review_gates=list(
            dict.fromkeys(
                gate
                for row in campaign_triage_read_contract.triage_rows
                for gate in row.human_review_gates
            )
        ),
        action_ids=campaign_triage_read_contract.action_ids,
        blocked_claims=campaign_triage_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_derived_kpi_decision(
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    *,
    action_ids: list[str],
    missing_read_contracts: list[str],
) -> AdsDecisionItem:
    campaign_action_ids = [
        action_id for action_id in action_ids if action_id == CAMPAIGN_REVIEW_ACTION_ID
    ]
    return AdsDecisionItem(
        id="ads_review_derived_kpis",
        decision_type="review_derived_kpi",
        status="ready",
        title="Sprawdź wyliczone wskaźniki kampanii bez decyzji budżetowych",
        summary=derived_kpi_read_contract.summary,
        rationale=(
            "Koszt pozyskania celu i zwrot z reklam są tu wartościami obliczonymi z kosztu, "
            "konwersji i wartości konwersji w bieżących dowodach Google Ads. WILQ nadal "
            "blokuje wniosek o rentowności, stracie budżetu, skalowaniu budżetu i zapisie zmian."
        ),
        next_step=derived_kpi_read_contract.next_step,
        allowed_metrics=derived_kpi_read_contract.allowed_metrics,
        missing_read_contracts=missing_read_contracts,
        source_connectors=derived_kpi_read_contract.source_connectors,
        evidence_ids=derived_kpi_read_contract.evidence_ids,
        derived_kpi_rows=derived_kpi_read_contract.kpi_rows,
        action_ids=campaign_action_ids,
        blocked_claims=derived_kpi_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_budget_context_decision(
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    *,
    action_ids: list[str],
) -> AdsDecisionItem:
    metric_facts = [
        fact for row in budget_pacing_read_contract.budget_rows for fact in row.metric_facts
    ]
    campaign_action_ids = [
        action_id for action_id in action_ids if action_id == CAMPAIGN_REVIEW_ACTION_ID
    ]
    return AdsDecisionItem(
        id="ads_review_budget_context",
        decision_type="review_budget_context",
        status="ready",
        title="Sprawdź koszt kampanii względem budżetu dziennego",
        summary=budget_pacing_read_contract.summary,
        rationale=(
            "WILQ widzi campaign_budget amount i koszt z ostatnich 7 dni, więc może pokazać "
            "kontekst tempa wydawania. To nadal nie jest decyzja o skalowaniu: brakuje "
            "historii zmian, impression share, celu budżetowego i walidowanego podglądu zmian."
        ),
        next_step=budget_pacing_read_contract.next_step,
        allowed_metrics=budget_pacing_read_contract.allowed_metrics,
        missing_read_contracts=budget_pacing_read_contract.missing_read_contracts,
        source_connectors=budget_pacing_read_contract.source_connectors,
        evidence_ids=budget_pacing_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        budget_rows=budget_pacing_read_contract.budget_rows,
        shared_budget_distribution_rows=budget_pacing_read_contract.shared_budget_distribution_rows,
        budget_apply_preview=budget_pacing_read_contract.payload_preview,
        action_ids=campaign_action_ids,
        blocked_claims=budget_pacing_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_recommendations_decision(
    recommendations_read_contract: AdsRecommendationsReadContract,
    *,
    action_ids: list[str],
) -> AdsDecisionItem:
    metric_facts = [
        fact
        for row in recommendations_read_contract.recommendation_rows
        for fact in row.metric_facts
    ]
    recommendation_action_ids = [
        action_id
        for action_id in action_ids
        if action_id.startswith("act_prepare_google_ads_recommendation")
    ]
    return AdsDecisionItem(
        id="ads_review_recommendations",
        decision_type="review_recommendations",
        status="ready",
        title="Przejrzyj rekomendacje Google Ads bez zapisu zmian",
        summary=recommendations_read_contract.summary,
        rationale=(
            "Rekomendacje Google Ads są sygnałem do kontroli, nie automatyczną strategią. "
            "WILQ pokazuje typ rekomendacji i powiązanie z kampanią/budżetem, ale blokuje "
            "akceptację i zapis zmian bez strategii, oceny zgodności Google Ads, "
            "potwierdzenia i audytu."
        ),
        next_step=recommendations_read_contract.next_step,
        allowed_metrics=recommendations_read_contract.allowed_metrics,
        missing_read_contracts=recommendations_read_contract.missing_read_contracts,
        operator_review_gates=recommendations_read_contract.operator_review_gates,
        source_connectors=recommendations_read_contract.source_connectors,
        evidence_ids=recommendations_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        recommendation_rows=recommendations_read_contract.recommendation_rows,
        recommendation_apply_preview=recommendations_read_contract.payload_preview,
        action_ids=recommendation_action_ids,
        blocked_claims=recommendations_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_impression_share_decision(
    impression_share_read_contract: AdsImpressionShareReadContract,
) -> AdsDecisionItem:
    metric_facts = [
        fact
        for row in impression_share_read_contract.impression_share_rows
        for fact in row.metric_facts
    ]
    return AdsDecisionItem(
        id="ads_review_impression_share",
        decision_type="review_impression_share",
        status="ready",
        title="Sprawdź utracony udział w wyświetleniach",
        summary=impression_share_read_contract.summary,
        rationale=(
            "Impression share pokazuje, czy kampania traci ekspozycję przez budżet albo ranking. "
            "WILQ może to pokazać jako kontekst review, ale blokuje skalowanie budżetu i obietnice "
            "o marnowaniu budżetu bez historii zmian, celu biznesowego i podglądu zmian."
        ),
        next_step=impression_share_read_contract.next_step,
        allowed_metrics=impression_share_read_contract.allowed_metrics,
        missing_read_contracts=impression_share_read_contract.missing_read_contracts,
        source_connectors=impression_share_read_contract.source_connectors,
        evidence_ids=impression_share_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        impression_share_rows=impression_share_read_contract.impression_share_rows,
        action_ids=[],
        blocked_claims=impression_share_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_change_history_decision(
    change_history_read_contract: AdsChangeHistoryReadContract,
) -> AdsDecisionItem:
    metric_facts = [
        fact
        for row in change_history_read_contract.change_history_rows
        for fact in row.metric_facts
    ]
    has_change_rows = bool(change_history_read_contract.change_history_rows)
    return AdsDecisionItem(
        id="ads_review_change_history",
        decision_type="review_change_history",
        status="ready",
        title=(
            "Sprawdź historię zmian Google Ads"
            if has_change_rows
            else "Historia zmian: brak zdarzeń w ostatnich 14 dniach"
        ),
        summary=change_history_read_contract.summary,
        rationale=(
            "Historia zmian mówi, co ostatnio zmieniano w koncie. Jeśli Google Ads nie zwrócił "
            "żadnych zdarzeń, sam odczyt jest poprawny, ale nie wolno przypisywać wyników "
            "kampanii do zmian. Jeśli zdarzenia istnieją, WILQ nadal blokuje obietnice o wpływie "
            "zmian na wynik bez porównania przed/po i sprawdzenia przez człowieka."
        ),
        next_step=change_history_read_contract.next_step,
        allowed_metrics=change_history_read_contract.allowed_metrics,
        missing_read_contracts=change_history_read_contract.missing_read_contracts,
        source_connectors=change_history_read_contract.source_connectors,
        evidence_ids=change_history_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        change_history_rows=change_history_read_contract.change_history_rows,
        action_ids=change_history_read_contract.action_ids,
        blocked_claims=change_history_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_search_terms_decision(
    search_terms_read_contract: AdsSearchTermsReadContract,
    *,
    action_ids: list[str],
) -> AdsDecisionItem:
    metric_facts = [
        fact for row in search_terms_read_contract.search_term_rows for fact in row.metric_facts
    ]
    allowed_action_ids = {
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
    }
    filtered_action_ids = [
        action_id for action_id in action_ids if action_id in allowed_action_ids
    ]
    return AdsDecisionItem(
        id="ads_review_search_terms",
        decision_type="review_search_terms",
        status="ready",
        title="Przejrzyj zapytania z reklam bez automatycznych wykluczeń",
        summary=search_terms_read_contract.summary,
        rationale=(
            "WILQ widzi zapytania, kampanie, grupy reklam, koszt, kliknięcia i konwersje. "
            "To pozwala zrobić kontrolę jakości zapytań, ale nie wystarcza do obietnic o "
            "marnowaniu budżetu ani do zapisu wykluczeń."
        ),
        next_step=(
            "Przejrzyj zapytania z najwyższym kosztem. Jeśli chcesz wykluczenia, najpierw dodaj "
            "kontekst dopasowania, 90-dniową kontrolę bezpieczeństwa i akcję tylko do "
            "przygotowania."
        ),
        allowed_metrics=search_terms_read_contract.allowed_metrics,
        missing_read_contracts=search_terms_read_contract.missing_read_contracts,
        operator_review_gates=search_terms_read_contract.operator_review_gates,
        source_connectors=search_terms_read_contract.source_connectors,
        evidence_ids=search_terms_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        search_term_rows=search_terms_read_contract.search_term_rows,
        action_ids=filtered_action_ids,
        blocked_claims=search_terms_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def build_search_term_ngram_decision(
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
) -> AdsDecisionItem:
    metric_facts = [
        fact for row in search_term_ngram_read_contract.ngram_rows for fact in row.metric_facts
    ]
    top_rows = search_term_ngram_read_contract.ngram_rows[:8]
    return AdsDecisionItem(
        id="ads_review_search_term_ngrams",
        decision_type="review_search_term_ngrams",
        status="ready",
        title="Sprawdź powtarzające się tematy w zapytaniach",
        summary=search_term_ngram_read_contract.summary,
        rationale=(
            "N-gramy pokazują, które słowa i frazy powtarzają się w wyszukiwanych hasłach "
            "oraz jaki mają koszt, kliknięcia i konwersje w dowodach. To skraca ocenę, "
            "ale nadal wymaga ręcznego sprawdzenia intencji i nie odblokowuje wykluczeń."
        ),
        next_step=search_term_ngram_read_contract.next_step,
        priority=42,
        metric_tiles={
            "n-gramy": len(search_term_ngram_read_contract.ngram_rows),
            "top koszt": sum(row.cost_micros or 0 for row in top_rows),
            "top kliknięcia": sum(row.clicks or 0 for row in top_rows),
        },
        allowed_metrics=search_term_ngram_read_contract.allowed_metrics,
        missing_read_contracts=search_term_ngram_read_contract.missing_read_contracts,
        operator_review_gates=search_term_ngram_read_contract.operator_review_gates,
        source_connectors=search_term_ngram_read_contract.source_connectors,
        evidence_ids=search_term_ngram_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        search_term_ngram_rows=top_rows,
        action_ids=search_term_ngram_read_contract.action_ids,
        blocked_claims=search_term_ngram_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )
