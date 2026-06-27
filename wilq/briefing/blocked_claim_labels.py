from __future__ import annotations

from collections.abc import Iterable

BLOCKED_CLAIM_LABELS: dict[str, str] = {
    "budget change": "zmiana budżetu",
    "budget optimization": "optymalizacja budżetu",
    "budget scaling": "skalowanie budżetu",
    "campaign creation": "utworzenie kampanii",
    "campaign mutation": "zmiana kampanii",
    "causal impact": "przyczynowy wpływ zmian",
    "client-ready report": "raport gotowy dla klienta",
    "CPA": "koszt pozyskania celu",
    "CPA verdict": "werdykt kosztu pozyskania celu",
    "CPC": "koszt kliknięcia",
    "CTR": "współczynnik kliknięć",
    "conversion drop": "spadek konwersji",
    "conversion rate": "współczynnik konwersji",
    "conversion setup applied": "wdrożona konfiguracja konwersji",
    "Demand Gen launch ready": "gotowość uruchomienia Demand Gen",
    "GBP performance verdict": "werdykt skuteczności profilu firmy",
    "GBP write": "zapis zmian w profilu firmy",
    "zapis zmian GBP": "zapis zmian w profilu firmy",
    "lead quality": "jakość leadów",
    "link acquisition impact": "wpływ pozyskanych linków",
    "local task completed": "ukończone zadanie lokalne",
    "local ranking uplift": "wzrost lokalnych pozycji",
    "local visibility uplift": "poprawa widoczności lokalnej",
    "monthly performance verdict": "miesięczny werdykt skuteczności",
    "negative keyword addition": "dodanie wykluczających słów kluczowych",
    "profitability": "opłacalność",
    "profitability verdict": "werdykt opłacalności",
    "profit uplift": "wzrost zysku",
    "recommendation applied": "wdrożona rekomendacja",
    "recommendation write": "zapis rekomendacji",
    "revenue": "przychód",
    "search-term waste": "marnowanie budżetu na zapytaniach",
    "search terms": "zapytania z reklam",
    "spend": "wydatki reklamowe",
    "tracking fixed": "naprawiony pomiar",
    "wasted budget": "zmarnowany budżet",
    "wasted budget verdict": "werdykt przepalonego budżetu",
}


def operator_blocked_claims(claims: Iterable[str]) -> list[str]:
    values: list[str] = []
    for claim in claims:
        label = BLOCKED_CLAIM_LABELS.get(claim, claim.replace("_", " "))
        if label and label not in values:
            values.append(label)
    return values
