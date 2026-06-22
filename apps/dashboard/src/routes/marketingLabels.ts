export function priorityLabel(priority: number) {
  if (priority <= 12) return "najpierw";
  if (priority <= 25) return "wysoki priorytet";
  if (priority <= 45) return "do sprawdzenia";
  return "niżej w kolejce";
}

export function marketerBlockedClaimLabels(claims: string[]) {
  return Array.from(new Set(claims.map(marketerBlockedClaimLabel)));
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
