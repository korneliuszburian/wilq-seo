export function priorityLabel(priority: number) {
  if (priority <= 12) return "najpierw";
  if (priority <= 25) return "wysoki priorytet";
  if (priority <= 45) return "do sprawdzenia";
  return "niżej w kolejce";
}

export function marketerBlockedClaimLabels(claims: string[]) {
  return Array.from(new Set(claims.map(marketerBlockedClaimLabel)));
}

export function adsMissingReadContractLabel(value: string) {
  const labels: Record<string, string> = {
    recommendations: "rekomendacje Google Ads",
    recommendation_impact_preview: "podgląd wpływu rekomendacji",
    recommendation_apply_preview: "podgląd zapisu rekomendacji",
    human_strategy_review: "ocena strategii przez człowieka",
    change_history: "historia zmian",
    budget_pacing: "tempo wydawania budżetu",
    campaign_budget: "budżet kampanii",
    shared_budget_distribution: "podział shared budget",
    budget_target_or_seasonality: "cel budżetowy lub sezonowość",
    business_goal: "cel biznesowy",
    target_roas_or_cpa: "docelowy zwrot z reklam albo koszt pozyskania celu",
    profit_margin: "marża albo model rentowności",
    human_budget_goal: "cel budżetu od człowieka",
    account_currency: "waluta konta",
    pre_change_performance_window: "okno wyników przed zmianą",
    post_change_performance_window: "okno wyników po zmianie",
    human_change_impact_review: "ręczna ocena wpływu zmian",
    apply_preview: "podgląd zmian",
    change_event_rows: "zdarzenia historii zmian",
    current_campaign_snapshot: "bieżący odczyt kampanii",
    impression_share: "udział w wyświetleniach",
    "keyword match context": "kontekst dopasowania słów kluczowych",
    keyword_match_context_read: "odczyt istniejących słów kluczowych i typów dopasowania",
    "90_day_safety_check": "90-dniowa kontrola bezpieczeństwa",
    search_term_90d_read: "90-dniowy odczyt zapytań",
    human_intent_review: "ręczna ocena intencji",
    negative_keyword_change_preview: "podgląd zmian wykluczeń",
    ngram_to_negative_keyword_change_preview:
      "podgląd zmian wykluczeń z tematów zapytań",
    review_search_term_context: "sprawdzenie intencji zapytania",
    check_existing_keywords_and_match_types: "sprawdzenie słów i typów dopasowania",
    human_confirm_before_apply: "potwierdzenie człowieka przed zapisem",
    google_ads_mutation_audit: "sprawdzenie zapisu zmian w Google Ads",
    keyword_planner_enrichment: "wzbogacenie przez Keyword Planner",
    forecast_or_audience_size: "prognoza albo rozmiar odbiorców",
    "campaign activity": "aktywność kampanii",
    search_term_view: "widok zapytań użytkowników",
    zero_conversion_search_terms: "terminy z zerową konwersją",
    gbp_visibility: "widoczność Google Business Profile",
    competitor_visibility: "widoczność konkurencji",
    local_tasks: "lokalne zadania do wykonania",
    place_inventory: "spis miejsc",
    local_rankings: "lokalne pozycje",
    reviews: "opinie"
  };
  return labels[value] ?? value;
}

export function adsBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    CPA: "CPA",
    "ocena kosztu pozyskania celu": "ocena kosztu pozyskania celu",
    "werdykt zwrotu z reklam": "ocena zwrotu z reklam",
    "marnowanie budżetu na zapytaniach": "marnowanie budżetu na zapytaniach",
    "zmarnowany budżet": "zmarnowany budżet",
    "zmarnowany koszt": "zmarnowany koszt",
    "propozycje wykluczeń": "propozycje wykluczeń",
    "zapis wykluczeń": "zapis wykluczeń",
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "zmiana budżetu": "zmiana budżetu",
    "ocena marży": "ocena marży",
    "currency-formatted cost": "koszt w walucie konta",
    "zapis zmian budżetu": "zmiana budżetu",
    "zapis zmian kampanii": "zmiana kampanii",
    "change history": "historia zmian",
    "wpływ zmian": "wpływ zmian",
    "campaign creation": "tworzenie kampanii",
    "impression share": "udział w wyświetleniach",
    "zapis rekomendacji": "zapis rekomendacji",
    "automatyczne przyjęcie rekomendacji": "automatyczne przyjęcie rekomendacji",
    "obietnica poprawy wyniku": "obietnica poprawy wyniku",
    forecast: "prognoza",
    "skalowanie budżetu": "skalowanie budżetu",
    "budget amount": "kwota budżetu",
    "budget pacing": "tempo wydawania budżetu",
    opłacalność: "opłacalność",
    "spadek konwersji": "spadek konwersji",
    "utrata konwersji": "utrata konwersji",
    "search terms": "zapytania użytkowników",
    "campaign scaling": "skalowanie kampanii"
  };
  return labels[value] ?? value;
}

function marketerBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    CPA: "CPA",
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "automatyczne przyjęcie rekomendacji": "automatyczne przyjęcie rekomendacji",
    "zmiana budżetu": "zapis zmiany budżetu",
    "skalowanie budżetu": "skalowanie budżetu",
    "campaign creation": "utworzenie kampanii",
    "zapis zmian kampanii": "zmiana kampanii",
    "wpływ zmian": "wpływ zmian",
    "content brief without relevance review": "brief treści bez oceny trafności",
    "spadek konwersji": "spadek konwersji",
    "utrata konwersji": "utrata konwersji",
    "współczynnik konwersji": "współczynnik konwersji",
    "ocena kosztu pozyskania celu": "ocena kosztu pozyskania celu",
    "ocena atrybucji": "ocena atrybucji",
    "feed fix candidate": "propozycja naprawy feedu",
    "diagnoza lejka": "diagnoza lejka",
    "zapis w GA4": "zapis w GA4",
    "lead quality": "jakość leadów",
    "ocena marży": "ocena marży",
    "zapis wykluczeń": "zapis wykluczeń",
    "propozycje wykluczeń": "propozycje wykluczeń",
    "obietnica poprawy wyniku": "obietnica poprawy wyniku",
    opłacalność: "opłacalność",
    "ocena opłacalności": "ocena opłacalności",
    "zapis rekomendacji": "zapis rekomendacji",
    przychód: "przychód",
    "werdykt zwrotu z reklam": "ocena zwrotu z reklam",
    "marnowanie budżetu na zapytaniach": "marnowanie budżetu na zapytaniach",
    "ocena KPI względem celu przed potwierdzeniem": "ocena KPI względem celu przed potwierdzeniem",
    "naprawiony pomiar": "pomiar naprawiony",
    "zmarnowany budżet": "zmarnowany budżet",
    "ocena zmarnowanego budżetu": "ocena zmarnowanego budżetu",
    wordpress_publish: "publikacja WordPress",
    wordpress_draft_write: "zapis szkicu WordPress",
    production_wordpress_write: "zapis na produkcyjnym WordPressie"
  };
  return labels[value] ?? value;
}

export function marketerBlockedClaimLabelText(value: string) {
  return marketerBlockedClaimLabel(value);
}
