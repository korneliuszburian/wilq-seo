from __future__ import annotations

from collections.abc import Iterable

from wilq.briefing.ads_metric_utils import (
    format_money_micros as _format_money_micros,
)
from wilq.schemas import (
    ActionRisk,
    AdsBusinessContextReadContract,
    AdsDecisionItem,
    ConnectorRefreshRun,
    connector_refresh_run_status_label,
)

ADS_REVIEW_GATE_LABELS = {
    "human_strategy_review": "ocena strategii przez człowieka",
    "review_recommendation_type": "sprawdzenie typu rekomendacji",
    "review_impact_metrics": "sprawdzenie wpływu rekomendacji",
    "review_change_history": "sprawdzenie historii zmian",
    "review_business_goal": "sprawdzenie celu biznesowego",
    "configure_business_goal": "uzupełnienie celu biznesowego",
    "review_profit_margin_model": "sprawdzenie modelu marży",
    "configure_profit_margin_or_value_model": "uzupełnienie marży albo modelu wartości",
    "review_human_budget_goal": "sprawdzenie celu budżetu",
    "configure_human_budget_goal": "uzupełnienie celu budżetu",
    "confirm_target_roas_or_cpa": (
        "potwierdzenie docelowego zwrotu z reklam albo kosztu pozyskania celu"
    ),
    "review_target_fit": "sprawdzenie dopasowania do celu",
    "review_campaign_goal": "sprawdzenie celu kampanii",
    "review_conversion_quality": "sprawdzenie jakości konwersji",
    "review_budget_context": "sprawdzenie kontekstu budżetu",
    "review_search_terms_before_budget_decision": ("wyszukiwane hasła przed decyzją budżetową"),
    "review_campaign_activity": "sprawdzenie aktywności kampanii",
    "verify_account_currency": "sprawdzenie waluty konta",
    "budget_pacing": "tempo wydawania budżetu",
    "impression_share": "udział w wyświetleniach",
    "change_history": "historia zmian",
    "human_budget_goal": "cel budżetu od człowieka",
    "budget_apply_preview": "podgląd zmiany budżetu",
    "campaign_budget_apply_safety": "bezpieczeństwo zmiany budżetu",
    "campaign_budget_operation_preview": "sprawdzenie zapisu budżetu w Google Ads",
    "review_conversion_tracking": "sprawdzenie trackingu konwersji",
    "review_pmax_asset_feed_context": "sprawdzenie PMax, pliku produktowego i materiałów",
    "review_draft_campaign_status": "sprawdzenie statusu draftu",
    "recommendation_apply_preview": "podgląd zapisu rekomendacji",
    "google_ads_rmf_compliance_review": "ocena zgodności Google Ads RMF",
    "human_confirm_before_apply": "potwierdzenie człowieka przed zapisem",
    "negative_keyword_action_validation": "sprawdzenie w WILQ dla wykluczeń",
    "human_intent_review": "ocena intencji przez człowieka",
    "review_source_terms": "sprawdzenie haseł źródłowych",
    "reject_brand_or_low_intent_terms": "odrzucenie brand i niskiej intencji",
    "keyword_planner_enrichment": "wzbogacenie przez Keyword Planner",
    "forecast_or_audience_size": "prognoza albo rozmiar odbiorców",
    "custom_segment_operation_preview": "sprawdzenie zapisu zmian w Google Ads",
    "google_ads_mutation_audit": "audyt zapisu zmian w Google Ads",
    "mutation_audit": "audyt zapisu zmian",
    "review_search_term_context": "sprawdzenie intencji zapytania",
    "check_existing_keywords_and_match_types": (
        "sprawdzenie istniejących słów kluczowych i typów dopasowania"
    ),
    "90_day_safety_check": "90-dniowa kontrola bezpieczeństwa",
    "negative_keyword_change_preview": "podgląd zmian wykluczeń",
}


def _ads_review_gate_labels(gates: Iterable[object]) -> list[str]:
    return [
        ADS_REVIEW_GATE_LABELS.get(str(gate), "sprawdzenie przez operatora")
        for gate in gates
        if str(gate)
    ]


def _ads_business_use_labels(values: Iterable[object]) -> list[str]:
    labels = {
        "campaign_review_context": "kontekst oceny kampanii",
        "budget_review_context": "kontekst oceny budżetu",
        "human_strategy_review_context": "kontekst strategii człowieka",
        "margin_context": "kontekst marży",
        "business_goal_alignment": "dopasowanie do celu biznesowego",
        "budget_goal_guardrail": "zasada bezpieczeństwa celu budżetu",
        "target_roas_review_context": "kontekst docelowego zwrotu z reklam",
        "target_cpa_review_context": "kontekst docelowego kosztu pozyskania celu",
        "target_roas_review": "ocena docelowego zwrotu z reklam",
        "target_cpa_review": "ocena docelowego kosztu pozyskania celu",
        "profitability_verdict": "ocena opłacalności",
        "target_kpi_verdict": "ocena wskaźników względem celu",
        "budget_scaling": "skalowanie budżetu",
        "budget_apply": "zmiana budżetu",
        "recommendation_apply": "zapis rekomendacji",
        "wasted_budget_claim": "wniosek o zmarnowanym budżecie",
        "automatic_scaling": "automatyczne skalowanie",
        "profitability_verdict_without_value_model_review": (
            "ocena opłacalności bez sprawdzenia modelu wartości"
        ),
    }
    return [
        labels.get(str(value), "zastosowanie biznesowe do sprawdzenia")
        for value in values
        if str(value)
    ]


def _ads_strategy_review_status_label(status: object) -> str:
    labels = {
        "missing": "ocena strategii niepotwierdzona",
        "approved_for_prepare": "zatwierdzone do przygotowania",
        "needs_changes": "wymaga zmian",
        "rejected": "odrzucone",
        "deferred": "odroczone",
    }
    value = str(status)
    return labels.get(value, "status oceny strategii do sprawdzenia")


def _ads_allowed_metric_labels(metrics: Iterable[object]) -> list[str]:
    labels = {
        "change_event_available": "historia zmian dostępna",
        "change_event_changed_field_count": "liczba zmienionych pól",
        "current_campaign_clicks": "bieżące kliknięcia kampanii",
        "current_campaign_impressions": "bieżące wyświetlenia kampanii",
        "current_campaign_cost_micros": "bieżący koszt kampanii",
        "current_campaign_conversions": "bieżące konwersje kampanii",
        "current_campaign_conversion_value": "bieżąca wartość konwersji kampanii",
    }
    return [
        labels.get(str(metric), "metryka Google Ads do sprawdzenia")
        for metric in metrics
        if str(metric)
    ]


def _ads_confidence_label(confidence: object) -> str:
    labels = {
        "low": "niska",
        "medium": "średnia",
        "high": "wysoka",
    }
    value = str(confidence)
    return labels.get(value, "pewność do sprawdzenia")


def _ads_validation_status_label(status: object) -> str:
    labels = {
        "pending_validation": "do sprawdzenia",
        "blocked": "zablokowane",
    }
    value = str(status)
    return labels.get(value, "status sprawdzenia do sprawdzenia")


def _ads_missing_read_contract_labels(contracts: Iterable[object]) -> list[str]:
    labels = {
        "recommendations": "rekomendacje Google Ads",
        "recommendation_impact_preview": "podgląd wpływu rekomendacji",
        "recommendation_apply_preview": "podgląd zapisu rekomendacji",
        "human_strategy_review": "ocena strategii przez człowieka",
        "approved_human_strategy_review": "zatwierdzona ocena strategii",
        "change_history": "historia zmian",
        "budget_pacing": "tempo wydawania budżetu",
        "campaign_budget": "budżet kampanii",
        "recommended_budget_missing": "brak rekomendowanego budżetu z Google Ads",
        "shared_budget_distribution": "podział wspólnego budżetu",
        "budget_target_or_seasonality": "cel budżetowy albo sezonowość",
        "business_goal": "cel biznesowy",
        "target_roas_or_cpa": "docelowy zwrot z reklam albo koszt pozyskania celu",
        "profit_margin": "marża albo model rentowności",
        "human_budget_goal": "cel budżetu od człowieka",
        "account_currency": "waluta konta",
        "pre_change_performance_window": "wyniki sprzed zmiany",
        "post_change_performance_window": "wyniki po zmianie",
        "human_change_impact_review": "ręczna ocena wpływu zmian",
        "apply_preview": "podgląd zmian",
        "change_event_rows": "zdarzenia historii zmian",
        "current_campaign_snapshot": "bieżący odczyt kampanii",
        "impression_share": "udział w wyświetleniach",
        "keyword match context": "kontekst dopasowania słów kluczowych",
        "keyword_match_context_read": "odczyt słów kluczowych i typów dopasowania",
        "90_day_safety_check": "90-dniowa kontrola bezpieczeństwa",
        "search_term_90d_read": "90-dniowy odczyt zapytań",
        "human_intent_review": "ręczna ocena intencji",
        "negative_keyword_change_preview": "podgląd zmian wykluczeń",
        "ngram_to_negative_keyword_change_preview": ("podgląd zmian wykluczeń z tematów zapytań"),
        "review_search_term_context": "sprawdzenie intencji zapytania",
        "check_existing_keywords_and_match_types": ("sprawdzenie słów i typów dopasowania"),
        "human_confirm_before_apply": "potwierdzenie człowieka przed zapisem",
        "google_ads_mutation_audit": "sprawdzenie zapisu zmian w Google Ads",
        "mutation_audit": "audyt zapisu zmian",
        "keyword_planner_enrichment": "wzbogacenie przez Keyword Planner",
        "forecast_or_audience_size": "prognoza albo rozmiar odbiorców",
        "campaign activity": "aktywność kampanii",
        "search_term_view": "widok zapytań użytkowników",
        "zero_conversion_search_terms": "zapytania z zerową konwersją",
    }
    return [
        labels.get(str(contract), "brakujący odczyt Ads do sprawdzenia")
        for contract in contracts
        if str(contract)
    ]


def _ads_status_label(status: object) -> str:
    value = str(status)
    labels = {
        "ready": "gotowe",
        "preliminary": "wstępne",
        "blocked": "zablokowane",
        "missing": "zakres danych Ads niepotwierdzony",
    }
    return labels.get(value, "status Google Ads do sprawdzenia")


def _ads_decision_type_label(decision_type: object) -> str:
    labels = {
        "review_campaign_activity": "aktywność kampanii",
        "review_business_context": "kontekst biznesowy",
        "review_derived_kpi": "wyliczone wskaźniki",
        "review_budget_context": "kontekst budżetu",
        "review_recommendations": "rekomendacje",
        "review_impression_share": "udział w wyświetleniach",
        "review_change_history": "historia zmian",
        "review_search_term_safety": "bezpieczeństwo zapytań",
        "review_search_terms": "wyszukiwane hasła",
        "review_search_term_ngrams": "tematy zapytań",
        "review_negative_keyword_safety": "bezpieczeństwo wykluczeń",
        "prepare_custom_segments": "segmenty odbiorców",
        "block_write_actions": "blokada zapisu zmian",
        "fix_ads_access": "naprawa dostępu",
        "review_campaign_triage": "kolejność kampanii",
    }
    value = str(decision_type)
    return labels.get(value, "typ decyzji Google Ads do sprawdzenia")


def _ads_decision_start_here_summary(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> str:
    if decision.decision_type == "review_campaign_triage":
        campaign_count = len(decision.campaign_triage_rows) or len(decision.campaign_rows)
        return (
            f"{campaign_count} kampanii w kolejce oceny. Zacznij od celu, kosztu, "
            "konwersji, budżetu i haseł."
        )
    if decision.decision_type == "review_campaign_activity":
        cost = _format_money_micros(
            sum(row.cost_micros or 0 for row in decision.campaign_rows),
            currency_code,
        )
        return (
            f"{len(decision.campaign_rows)} kampanii z odczytem aktywności. "
            f"Koszt w tej karcie: {cost or 'brak'}."
        )
    if decision.decision_type == "review_business_context":
        return (
            "Najpierw potwierdź marżę, cel biznesowy, docelowy koszt pozyskania "
            "celu i docelowy zwrot z reklam, zanim ktokolwiek nazwie wynik opłacalnym."
        )
    if decision.decision_type == "review_derived_kpi":
        return (
            f"{len(decision.derived_kpi_rows)} wierszy wskaźników do oceny. "
            "To nadal sygnał do sprawdzenia, nie ocena kosztu pozyskania celu "
            "ani zwrotu z reklam."
        )
    if decision.decision_type == "review_budget_context":
        return (
            f"{len(decision.budget_rows)} budżetów do sprawdzenia. Nie skaluj "
            "ani nie tnij budżetu bez sprawdzenia w WILQ."
        )
    if decision.decision_type == "review_search_terms":
        return (
            f"{len(decision.search_term_rows)} haseł do oceny. Zacznij od kosztu "
            "i intencji, nie od automatycznego wykluczenia."
        )
    return decision.summary


def _ads_decision_measurement_plan(decision: AdsDecisionItem) -> str:
    if decision.decision_type == "review_campaign_activity":
        return (
            "Po sprawdzeniu kampanii zapisz baseline kosztu, kliknięć, konwersji "
            "i wartości konwersji. Dopiero osobne okno pre/post oraz historia zmian "
            "pozwolą mówić o efekcie."
        )
    if decision.decision_type == "review_campaign_triage":
        return (
            "Po przejściu kolejki kampanii zapisz, które kampanie wymagają ręcznej "
            "decyzji. Efekt sprawdzimy dopiero przez porównanie przed i po, historię "
            "zmian i ponowny odczyt Ads."
        )
    if decision.decision_type == "review_search_terms":
        return (
            "Po sprawdzeniu wyszukiwanych haseł zapisz akcje do sprawdzenia i blokady. "
            "Dopiero po potwierdzonej zmianie oraz porównaniu przed i po można oceniać "
            "wpływ na koszt, konwersje lub utratę ruchu."
        )
    if decision.decision_type in {
        "review_negative_keyword_safety",
        "review_search_term_ngrams",
    }:
        return (
            "Po sprawdzeniu wykluczeń sprawdź zapytania, koszt i konwersje przed "
            "i po zmianie. Bez sprawdzenia efektu WILQ nie twierdzi, że oszczędzono "
            "budżet albo uniknięto utraty konwersji."
        )
    if decision.decision_type == "review_recommendations":
        return (
            "Po sprawdzeniu rekomendacji zapisz, które rekomendacje odrzucono albo "
            "skierowano do sprawdzenia. Efekt można ocenić dopiero po audycie zmiany "
            "i porównaniu metryk w kolejnym oknie."
        )
    return (
        "Po decyzji zapisz przegląd akcji, punkt odniesienia i sprawdzenie efektu. "
        "Brak okna pomiarowego oznacza brak twierdzenia o poprawie wyniku."
    )


def _ads_business_context_status_label(contract: AdsBusinessContextReadContract) -> str:
    if contract.status == "blocked":
        return "blokada"
    if "target_roas_or_cpa" in contract.missing_read_contracts:
        return "wstępny"
    return "gotowe"


def _ads_priority_label(priority: int) -> str:
    if priority <= 12:
        return "najpierw"
    if priority <= 25:
        return "wysoki priorytet"
    if priority <= 45:
        return "do sprawdzenia"
    return "niżej w kolejce"


def _ads_risk_label(risk: object) -> str:
    value = str(risk.value if isinstance(risk, ActionRisk) else risk)
    labels = {
        "critical": "krytyczne",
        "high": "wysokie",
        "medium": "średnie",
        "low": "niskie",
    }
    return labels.get(value, "ryzyko Google Ads do sprawdzenia")


def _ads_connector_status_label(status: str) -> str:
    labels = {
        "configured": "dostęp skonfigurowany",
        "missing_credentials": "brakuje dostępu",
        "disabled": "źródło wyłączone",
    }
    return labels.get(status, "status dostępu Google Ads do sprawdzenia")


def _ads_refresh_status_label(run: ConnectorRefreshRun | object) -> str:
    if not isinstance(run, ConnectorRefreshRun):
        return "status odczytu Google Ads do sprawdzenia"
    return connector_refresh_run_status_label(run)


def _ads_live_data_status_label(live_data_available: bool) -> str:
    return "metryki Google Ads dostępne" if live_data_available else "brak metryk Google Ads"
