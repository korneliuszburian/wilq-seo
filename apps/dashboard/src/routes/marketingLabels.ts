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
    recommendation_impact_preview: "impact preview rekomendacji",
    recommendation_apply_preview: "podgląd apply rekomendacji",
    human_strategy_review: "review strategii przez człowieka",
    change_history: "historia zmian",
    budget_pacing: "tempo wydawania budżetu",
    campaign_budget: "budżet kampanii",
    shared_budget_distribution: "podział shared budget",
    budget_target_or_seasonality: "cel budżetowy lub sezonowość",
    business_goal: "cel biznesowy",
    target_roas_or_cpa: "target ROAS albo CPA",
    profit_margin: "marża albo model rentowności",
    human_budget_goal: "cel budżetu od człowieka",
    account_currency: "waluta konta",
    pre_change_performance_window: "okno wyników przed zmianą",
    post_change_performance_window: "okno wyników po zmianie",
    human_change_impact_review: "ręczny review wpływu zmian",
    apply_preview: "podgląd wdrożenia",
    change_event_rows: "zdarzenia historii zmian",
    current_campaign_snapshot: "bieżący snapshot kampanii",
    impression_share: "udział w wyświetleniach",
    "keyword match context": "kontekst dopasowania słów kluczowych",
    keyword_match_context_read: "odczyt istniejących keywords i match types",
    "90_day_safety_check": "90-dniowa kontrola bezpieczeństwa",
    search_term_90d_read: "90-dniowy odczyt zapytań",
    human_intent_review: "ręczny review intencji",
    negative_keyword_payload_preview: "podgląd payloadu wykluczeń",
    ngram_to_negative_keyword_payload_preview:
      "podgląd payloadu wykluczeń z n-gramów",
    review_search_term_context: "sprawdzenie intencji zapytania",
    check_existing_keywords_and_match_types: "sprawdzenie słów i typów dopasowania",
    human_confirm_before_apply: "potwierdzenie człowieka przed wdrożeniem",
    google_ads_mutation_audit: "audyt mutacji Google Ads",
    keyword_planner_enrichment: "enrichment Keyword Planner",
    forecast_or_audience_size: "forecast albo audience size",
    "campaign activity": "aktywność kampanii",
    search_term_view: "widok zapytań użytkowników",
    zero_conversion_search_terms: "terminy z zerową konwersją"
  };
  return labels[value] ?? value;
}

export function adsBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    CPA: "CPA",
    ROAS: "ROAS",
    "search-term waste": "waste na zapytaniach",
    "wasted budget": "zmarnowany budżet",
    "wasted spend": "zmarnowany spend",
    "negative keyword candidates": "kandydaci do wykluczeń",
    "negative keyword apply": "wdrożenie wykluczeń",
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "budget apply": "zmiana budżetu",
    "margin verdict": "werdykt marży",
    "currency-formatted cost": "koszt w walucie konta",
    "budget mutation": "zmiana budżetu",
    "campaign mutation": "zmiana kampanii",
    "change history": "historia zmian",
    "change impact": "wpływ zmian",
    "campaign creation": "tworzenie kampanii",
    "impression share": "udział w wyświetleniach",
    "recommendation apply": "wdrożenie rekomendacji",
    "automatic recommendation accept": "automatyczne przyjęcie rekomendacji",
    "performance uplift": "wzrost performance",
    "budget scaling": "skalowanie budżetu",
    "budget amount": "kwota budżetu",
    "budget pacing": "tempo wydawania budżetu",
    profitability: "opłacalność",
    "conversion drop": "spadek konwersji",
    "conversion loss": "utrata konwersji",
    "search terms": "zapytania użytkowników",
    "campaign scaling": "skalowanie kampanii"
  };
  return labels[value] ?? value;
}

function marketerBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    CPA: "CPA",
    ROAS: "ROAS",
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "approval restored": "ponowne zatwierdzenie produktu",
    "automatic approval fix": "automatyczna naprawa zatwierdzenia",
    "automatic feed edit": "automatyczna zmiana feedu",
    "automatic recommendation accept": "automatyczne przyjęcie rekomendacji",
    "audience size": "rozmiar odbiorców",
    "budget apply": "wdrożenie zmiany budżetu",
    "budget scaling": "skalowanie budżetu",
    "campaign creation": "utworzenie kampanii",
    "campaign mutation": "zmiana kampanii",
    "campaign performance": "wynik kampanii",
    "change impact": "wpływ zmian",
    "content brief without relevance review": "brief treści bez review trafności",
    "conversion drop": "spadek konwersji",
    "conversion loss": "utrata konwersji",
    "conversion rate": "współczynnik konwersji",
    "conversion uplift": "wzrost konwersji",
    "CPA verdict": "werdykt CPA",
    "attribution verdict": "werdykt atrybucji",
    "authority improvement": "wzrost autorytetu",
    "competitor visibility": "widoczność konkurencji",
    "feed fix candidate": "kandydat naprawy feedu",
    "feed write": "zapis do feedu",
    "funnel diagnosis": "diagnoza lejka",
    "GA4 write": "zapis w GA4",
    "GBP performance": "wynik Google Business Profile",
    "lead quality": "jakość leadów",
    "lead uplift": "wzrost leadów",
    "local ranking": "lokalne pozycje",
    "local ranking uplift": "wzrost lokalnych pozycji",
    "local visibility uplift": "wzrost lokalnej widoczności",
    "margin verdict": "werdykt marży",
    "negative keyword apply": "wdrożenie wykluczeń",
    "negative keyword candidates": "kandydaci do wykluczeń",
    "new article without inventory check": "nowy artykuł bez sprawdzenia inventory",
    "off-topic content recommendation": "rekomendacja treści poza intencją",
    "performance uplift": "wzrost performance",
    profitability: "opłacalność",
    "primary feed overwrite": "nadpisanie głównego feedu",
    "profit uplift": "wzrost zysku",
    "product data mutation": "zmiana danych produktu",
    "product fix applied": "naprawa produktu wdrożona",
    "ranking guarantee": "gwarancja pozycji",
    "recommendation apply": "wdrożenie rekomendacji",
    revenue: "przychód",
    "revenue impact": "wpływ na przychód",
    "revenue recovered": "odzyskany przychód",
    "ROAS verdict": "werdykt ROAS",
    "search-term waste": "waste na zapytaniach",
    "targeting applied": "targetowanie wdrożone",
    "tracking fixed": "pomiar naprawiony",
    "traffic uplift": "wzrost ruchu",
    "wasted budget": "zmarnowany budżet",
    "wasted budget verdict": "werdykt przepalonego budżetu"
  };
  return labels[value] ?? value;
}
