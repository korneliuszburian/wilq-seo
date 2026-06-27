from __future__ import annotations

from collections.abc import Iterable

BLOCKED_CLAIM_LABELS: dict[str, str] = {
    "budget change": "zmiana budżetu",
    "budget optimization": "optymalizacja budżetu",
    "skalowanie budżetu": "skalowanie budżetu",
    "campaign creation": "utworzenie kampanii",
    "zapis zmian kampanii": "zmiana kampanii",
    "causal impact": "przyczynowy wpływ zmian",
    "client-ready report": "raport gotowy dla klienta",
    "CPA": "koszt pozyskania celu",
    "ocena kosztu pozyskania celu": "ocena kosztu pozyskania celu",
    "CPC": "koszt kliknięcia",
    "CTR": "współczynnik kliknięć",
    "spadek konwersji": "spadek konwersji",
    "współczynnik konwersji": "współczynnik konwersji",
    "wdrożona konfiguracja konwersji": "wdrożona konfiguracja konwersji",
    "Demand Gen launch ready": "gotowość uruchomienia Demand Gen",
    "zapis zmian GBP": "zapis zmian w profilu firmy",
    "lead quality": "jakość leadów",
    "link acquisition impact": "wpływ pozyskanych linków",
    "monthly performance verdict": "miesięczny werdykt skuteczności",
    "negative keyword addition": "dodanie wykluczających słów kluczowych",
    "opłacalność": "opłacalność",
    "ocena opłacalności": "werdykt opłacalności",
    "profit uplift": "wzrost zysku",
    "recommendation applied": "wdrożona rekomendacja",
    "recommendation write": "zapis rekomendacji",
    "przychód": "przychód",
    "marnowanie budżetu na zapytaniach": "marnowanie budżetu na zapytaniach",
    "search terms": "zapytania z reklam",
    "spend": "wydatki reklamowe",
    "naprawiony pomiar": "naprawiony pomiar",
    "zmarnowany budżet": "zmarnowany budżet",
    "ocena zmarnowanego budżetu": "werdykt przepalonego budżetu",
}


def operator_blocked_claims(claims: Iterable[str]) -> list[str]:
    values: list[str] = []
    for claim in claims:
        label = BLOCKED_CLAIM_LABELS.get(claim, claim.replace("_", " "))
        if label and label not in values:
            values.append(label)
    return values
