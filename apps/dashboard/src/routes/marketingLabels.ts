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
    recommendation_apply_preview: "podgląd wdrożenia rekomendacji",
    human_strategy_review: "ocena strategii przez człowieka",
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
    human_change_impact_review: "ręczna ocena wpływu zmian",
    apply_preview: "podgląd wdrożenia",
    change_event_rows: "zdarzenia historii zmian",
    current_campaign_snapshot: "bieżący odczyt kampanii",
    impression_share: "udział w wyświetleniach",
    "keyword match context": "kontekst dopasowania słów kluczowych",
    keyword_match_context_read: "odczyt istniejących słów kluczowych i typów dopasowania",
    "90_day_safety_check": "90-dniowa kontrola bezpieczeństwa",
    search_term_90d_read: "90-dniowy odczyt zapytań",
    human_intent_review: "ręczna ocena intencji",
    negative_keyword_payload_preview: "podgląd zmian wykluczeń",
    ngram_to_negative_keyword_payload_preview:
      "podgląd zmian wykluczeń z tematów zapytań",
    review_search_term_context: "sprawdzenie intencji zapytania",
    check_existing_keywords_and_match_types: "sprawdzenie słów i typów dopasowania",
    human_confirm_before_apply: "potwierdzenie człowieka przed wdrożeniem",
    google_ads_mutation_audit: "audyt mutacji Google Ads",
    keyword_planner_enrichment: "wzbogacenie przez Keyword Planner",
    forecast_or_audience_size: "prognoza albo rozmiar odbiorców",
    "campaign activity": "aktywność kampanii",
    search_term_view: "widok zapytań użytkowników",
    zero_conversion_search_terms: "terminy z zerową konwersją"
  };
  return labels[value] ?? value;
}

export function adsBlockedClaimLabel(value: string) {
  const labels: Record<string, string> = {
    CPA: "CPA",
    "CPA verdict": "ocena CPA",
    ROAS: "ROAS",
    "ROAS verdict": "ocena ROAS",
    "audience size": "rozmiar odbiorców",
    "search-term waste": "marnowanie budżetu na zapytaniach",
    "wasted budget": "zmarnowany budżet",
    "wasted spend": "zmarnowany koszt",
    "negative keyword candidates": "kandydaci do wykluczeń",
    "negative keyword apply": "wdrożenie wykluczeń",
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "budget apply": "zmiana budżetu",
    "margin verdict": "ocena marży",
    "currency-formatted cost": "koszt w walucie konta",
    "budget mutation": "zmiana budżetu",
    "campaign mutation": "zmiana kampanii",
    "campaign performance": "wynik kampanii",
    "change history": "historia zmian",
    "change impact": "wpływ zmian",
    "campaign creation": "tworzenie kampanii",
    "impression share": "udział w wyświetleniach",
    "recommendation apply": "wdrożenie rekomendacji",
    "automatic recommendation accept": "automatyczne przyjęcie rekomendacji",
    "performance uplift": "wzrost wyniku kampanii",
    forecast: "prognoza",
    "conversion uplift": "wzrost konwersji",
    "targeting applied": "targetowanie wdrożone",
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
    "content brief without relevance review": "brief treści bez oceny trafności",
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
    "margin verdict": "ocena marży",
    "negative keyword apply": "wdrożenie wykluczeń",
    "negative keyword candidates": "kandydaci do wykluczeń",
    "new article without inventory check": "nowy artykuł bez sprawdzenia inventory",
    "off-topic content recommendation": "rekomendacja treści poza intencją",
    "performance uplift": "wzrost wyniku kampanii",
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
    "ROAS verdict": "ocena ROAS",
    "search-term waste": "marnowanie budżetu na zapytaniach",
    "targeting applied": "targetowanie wdrożone",
    "tracking fixed": "pomiar naprawiony",
    "traffic uplift": "wzrost ruchu",
    "wasted budget": "zmarnowany budżet",
    "wasted budget verdict": "werdykt przepalonego budżetu"
  };
  return labels[value] ?? value;
}

export function marketerBlockedClaimLabelText(value: string) {
  return marketerBlockedClaimLabel(value);
}

export function marketerOperatorCopy(value: string) {
  return value
    .replace(/\bActionObject review\b/gi, "przegląd akcji")
    .replace(/\bActionObjecty\b/g, "akcje do walidacji")
    .replace(/\bActionObject\b/g, "akcja do walidacji")
    .replace(/\bpayload preview\b/gi, "podgląd zmian")
    .replace(/\bpodgląd payloadu\b/gi, "podgląd zmian")
    .replace(/\bpayloady\b/gi, "dane akcji")
    .replace(/\bpayloadu\b/gi, "danych akcji")
    .replace(/\bpayload\b/gi, "dane akcji")
    .replace(/\breview-only\b/gi, "tylko do przeglądu")
    .replace(/\breview-safe\b/gi, "bezpieczne do przeglądu")
    .replace(/\breview\b/gi, "przegląd")
    .replace(/\bApply\b/g, "Wykonanie")
    .replace(/\bapply\b/g, "wykonanie")
    .replace(/\bwrite\b/gi, "zapisu")
    .replace(/\bvendorów\b/gi, "zewnętrznych systemów")
    .replace(/\bvendor\b/gi, "zewnętrzny system")
    .replace(/\bmutation audit\b/gi, "audyt zmiany")
    .replace(/\bmutation\b/gi, "zmiana")
    .replace(/\bmutacji\b/gi, "zmian")
    .replace(/\bmetric facts\b/gi, "metryki z dowodami")
    .replace(/\bimpact sanity check\b/gi, "sprawdzenie wpływu")
    .replace(/\bcontent queue\b/gi, "kolejkę treści")
    .replace(/\bprepare-only queue\b/gi, "kolejkę tylko do przygotowania")
    .replace(/\bqueue refresh\/create\/merge\/block\b/gi, "kolejkę: odśwież, utwórz, scal albo zablokuj")
    .replace(/\bqueue\b/gi, "kolejkę")
    .replace(/\blaunch\b/gi, "uruchomienie")
    .replace(/\bassetów\b/gi, "zasobów")
    .replace(/\blanding quality\b/gi, "jakości landing page")
    .replace(/\blanding\/source\/campaign breakdown\b/gi, "rozbicie landing page, źródeł i kampanii")
    .replace(/\bstaging handoff\b/gi, "przekazanie do wersji roboczej")
    .replace(/\bstaging\b/gi, "wersję roboczą")
    .replace(/\bclaimów\b/gi, "twierdzeń")
    .replace(/\bclaimować\b/gi, "twierdzić")
    .replace(/\bpause\b/gi, "pauzy")
    .replace(/\bbudget scaling\b/gi, "skalowania budżetu")
    .replace(/\bbieżącym evidence\b/gi, "bieżących dowodach")
    .replace(/\bevidence\b/gi, "dowody")
    .replace(/\bGSC demand\b/g, "popytu z GSC")
    .replace(/\binventory\b/gi, "istniejących treści")
    .replace(/\bcontent\b/gi, "treści")
    .replaceAll("/treści-planner", "/content-planner")
    .replace(/\bRMF\/compliance\b/g, "ryzyka i zgodności")
    .replace(/\bwstępnego przegląd\b/g, "wstępnego przeglądu")
    .replace(/\bwaliduj akcja do walidacji\b/g, "waliduj akcję do walidacji")
    .replaceAll("claimować", "twierdzić")
    .replaceAll("issue clusters", "grupy problemów")
    .replaceAll("refresh/merge", "odświeżenie albo scalenie")
    .replaceAll("draftu", "szkicu");
}
