from __future__ import annotations

from collections.abc import Iterable

from wilq.briefing.blocked_claim_labels import operator_blocked_claims

ACTION_GATE_LABELS: dict[str, str] = {
    "action_mode_prepare_only": "tryb przygotowania bez zapisu zmian",
    "action_validation_required": "wymagane sprawdzenie w WILQ",
    "payload_apply_allowed_false": "podgląd zmian nie pozwala na zapis",
    "destructive_actions_blocked": "destrukcyjne zmiany zablokowane",
    "preview_acknowledgement_required": "wymagane potwierdzenie podglądu zmian",
    "dry_run_preview_required": "wymagany wcześniejszy podgląd zmian",
    "action_confirmation_required": "wymagane potwierdzenie podglądu zmian",
    "metric_facts_required": "wymagane metryki z dowodami",
    "evidence_ids_required": "wymagane dowody źródłowe",
    "impact_sanity_check_required": "wymagane sprawdzenie efektu",
    "vendor_mutation_adapter_required": "brak bezpiecznej ścieżki zapisu w zewnętrznym systemie",
    "validate_action_object": "sprawdzenie akcji",
    "human_review_before_apply": "sprawdzenie przez człowieka przed zapisem",
    "human_confirm_before_apply": "potwierdzenie człowieka przed zapisem",
    "compare_90_day_safety_read": "porównaj z 90-dniową kontrolą bezpieczeństwa",
    "confirm_developer_access_approval": "potwierdź akceptację dostępu deweloperskiego",
    "review_campaign_activity": "sprawdź aktywność kampanii",
    "verify_account_currency": "sprawdź walutę konta",
    "budget_pacing": "sprawdź tempo wydawania budżetu",
    "impression_share": "sprawdź udział w wyświetleniach",
    "budget_apply_preview": "sprawdź podgląd zmiany budżetu",
    "campaign_budget_apply_safety": "sprawdź bezpieczeństwo zmiany budżetu",
    "campaign_budget_operation_preview": "sprawdź operację budżetu",
    "budget_delta_limit_30_percent": "sprawdź limit zmiany budżetu do 30%",
    "budget_delta_percent": "sprawdź procent zmiany budżetu",
    "budget_target_or_seasonality": "sprawdź cel budżetu albo sezonowość",
    "human_budget_goal": "potwierdź cel budżetu",
    "content_url_preflight_review": "potwierdzenie publicznego URL-a",
    "final_canonical_review": "kontrola URL-a kanonicznego",
    "canonical_review": "kontrola URL-a kanonicznego",
    "canonical_review_outcome": "wynik kontroli URL-a kanonicznego",
    "duplicate_or_cannibalization_check": "kontrola duplikacji i kanibalizacji",
    "duplicate_review_outcome": "wynik kontroli duplikacji",
    "legal_factual_review": "kontrola prawna i faktograficzna",
    "legal_factual_review_outcome": "wynik kontroli prawnej i faktograficznej",
    "content_draft_readiness_review": "kontrola gotowości szkicu",
    "wordpress_draft_payload_preview": "podgląd wpisu WordPress",
    "wordpress_draft_preview_review": "podgląd wpisu WordPress",
    "human_confirm_before_wordpress_write": "potwierdzenie człowieka przed zapisem WordPress",
    "gsc_query_page_check": "sprawdzenie zapytań i URL-i z GSC",
    "wordpress_inventory_check": "sprawdzenie spisu treści WordPress",
    "review_recommendation_type": "sprawdź typ rekomendacji",
    "review_impact_metrics": "sprawdź metryki wpływu",
    "review_change_history": "sprawdź historię zmian",
    "review_business_goal": "sprawdź cel biznesowy",
    "recommendation_apply_preview": "sprawdź podgląd rekomendacji",
    "recommendations": "sprawdź rekomendacje Google Ads",
    "profit_margin_or_value_model": "sprawdź marżę albo model wartości",
    "google_ads_rmf_compliance_review": "sprawdź zgodność Google Ads",
    "review_issue_type_and_attribute": "sprawdź typ problemu i atrybut pliku produktowego",
    "review_reporting_context": "sprawdź kontekst raportowania",
    "group_issue_reasons": "pogrupuj powody problemów",
    "identify_disapproved_products": "ustal produkty i zgłoszenia do sprawdzenia",
    "mutation_audit_required": "wymagany ślad bezpieczeństwa",
    "mutation_audit": "ślad bezpieczeństwa zapisu",
    "negative_keyword_action_validation": "sprawdzenie w WILQ dla wykluczeń",
    "prepare_feed_fix_preview": "przygotuj podgląd zmian pliku produktowego",
    "require_human_confirm_before_apply": "człowiek potwierdza przed zapisem",
    "require_human_confirm_before_any_write": "człowiek potwierdza przed każdym zapisem",
    "reject_brand_or_low_intent_terms": "odrzuć brandowe lub niskointencyjne frazy",
    "rerun_google_ads_data_read": "uruchom ponowny odczyt Google Ads",
    "review_ads_campaign_channel_context": "sprawdź kanały kampanii Ads",
    "review_campaign_goal": "sprawdź cel kampanii",
    "review_campaign_name_dimension": "sprawdź nazwę kampanii",
    "review_conversion_quality": "sprawdź jakość konwersji",
    "review_conversion_or_key_event_mapping": (
        "sprawdź powiązanie konwersji lub zdarzenia kluczowego"
    ),
    "review_budget_context": "sprawdź kontekst budżetu",
    "review_demand_gen_missing_contracts": "sprawdź braki danych Demand Gen",
    "review_ga4_landing_source_campaign_context": "sprawdź stronę wejścia, źródło i kampanię w GA4",
    "review_human_budget_goal": "sprawdź cel budżetu od człowieka",
    "review_landing_page_dimension": "sprawdź stronę wejścia",
    "review_local_rankings_aggregate": "sprawdź zbiorcze dane lokalnych pozycji",
    "review_ngram_intent": "sprawdź intencję tematu zapytań",
    "review_place_inventory": "sprawdź listę lokalizacji",
    "review_profit_margin_model": "sprawdź model marży",
    "review_reviews_aggregate": "sprawdź zbiorcze dane opinii",
    "review_search_term_context": "sprawdź kontekst wyszukiwanego hasła",
    "review_search_terms_before_budget_decision": (
        "sprawdź wyszukiwane hasła przed decyzją budżetową"
    ),
    "review_source_medium_dimension": "sprawdź źródło i medium ruchu",
    "review_source_search_terms": "sprawdź źródłowe wyszukiwane hasła",
    "review_source_terms": "sprawdź źródłowe hasła",
    "review_target_fit": "sprawdź dopasowanie do celu",
    "review_conversion_tracking": "sprawdź pomiar konwersji",
    "review_pmax_asset_feed_context": "sprawdź kontekst zasobów i pliku produktowego PMax",
    "check_existing_keywords_and_match_types": "sprawdź istniejące słowa kluczowe i dopasowania",
    "90_day_safety_check": "sprawdź bezpieczeństwo z 90 dni",
    "negative_keyword_change_preview": "sprawdź podgląd wykluczenia słowa",
    "change_history": "sprawdź historię zmian",
    "forecast_or_audience_size": "sprawdź prognozę albo wielkość odbiorców",
    "custom_segment_operation_preview": "sprawdź podgląd segmentu odbiorców",
    "google_ads_mutation_audit": "sprawdzenie zapisu zmian w Google Ads",
    "human_strategy_review": "człowiek sprawdza strategię",
    "human_intent_review": "człowiek sprawdza intencję",
    "human_confirm_before_tracking_change": "człowiek potwierdza przed zmianą pomiaru",
    "keyword_planner_enrichment": "wzbogać dane przez Keyword Planner",
    "ngram_to_negative_keyword_change_preview": "podgląd przejścia z tematu zapytań do wykluczenia",
    "block_local_tasks_without_contract": "blokuj lokalne zadania bez kontraktu",
    "demand_gen_landing_quality_by_campaign": "jakość stron wejścia Demand Gen według kampanii",
    "demand_gen_campaign_mode_review": "kontrola trybu kampanii Demand Gen",
    "demand_gen_ad_group_ad_rows": "wiersze grup reklam Demand Gen",
    "demand_gen_creative_asset_rows": "wiersze kreacji i zasobów Demand Gen",
    "place_inventory": "lista lokalizacji",
    "local_tasks": "lokalne zadania do wykonania",
    "local_rankings": "lokalne pozycje",
    "reviews": "opinie",
    "gbp_visibility": "widoczność Google Business Profile",
    "competitor_visibility": "widoczność konkurencji",
    "use_only_wilq_evidence": "użyj tylko dowodów z WILQ",
    "write_in_polish": "pisz po polsku",
    "no_performance_claims_without_source_metric": (
        "bez obietnic skuteczności bez metryk źródłowych"
    ),
    "no_publishing_without_connector_credentials": "bez publikacji bez danych dostępowych źródła",
    "require_social_history_duplicate_review": (
        "sprawdź historię postów przed twierdzeniem, że temat się nie powtarza"
    ),
    "require_human_review_before_apply": "człowiek sprawdza przed zapisem",
    "confirm_target_roas_or_cpa": "potwierdź docelowy zwrot z reklam albo koszt pozyskania celu",
    "target_roas_or_cpa_required": "podaj docelowy zwrot z reklam albo koszt pozyskania celu",
    "exactly_one_target_guardrail_allowed": "podaj tylko jeden cel Ads do sprawdzenia",
    "record_human_strategy_review_outcome": "zapisz wynik sprawdzenia strategii przez człowieka",
    "WILQ_ADS_TARGET_ROAS": "docelowy zwrot z reklam",
    "WILQ_ADS_TARGET_CPA_MICROS": "docelowy koszt pozyskania celu",
    "target_metrics_review": "przegląd wskaźników względem celu",
    "campaign_review_context": "kontekst przeglądu kampanii",
    "budget_review_context": "kontekst przeglądu budżetu",
    "recommended_budget_missing": "brak proponowanego budżetu",
    "target_roas_or_cpa": "docelowy zwrot z reklam albo koszt pozyskania celu",
    "developer_access_approved_for_keyword_planner": (
        "dostęp deweloperski zatwierdzony dla Keyword Plannera"
    ),
    "keyword_planner_generate_ideas_allowed": "Keyword Planner może generować propozycje",
    "verify_keyword_planner_idea_rows": "sprawdź wiersze Keyword Planner",
}


def action_gate_label(value: str) -> str | None:
    if value.startswith("blocked_claim:"):
        claim_labels = operator_blocked_claims([value.removeprefix("blocked_claim:")])
        claim_label = claim_labels[0] if claim_labels else "ryzykowna obietnica"
        return f"nie wolno twierdzić: {claim_label}"
    if value in ACTION_GATE_LABELS:
        return ACTION_GATE_LABELS[value]
    if " " in value and "_" not in value:
        return value
    return None


def action_gate_labels(values: Iterable[str]) -> list[str]:
    return [label for value in values if (label := action_gate_label(value))]
