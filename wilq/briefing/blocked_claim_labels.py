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
    "CPA": "werdykt kosztu pozyskania celu",
    "ocena kosztu pozyskania celu": "werdykt kosztu pozyskania celu",
    "CPC": "koszt kliknięcia",
    "CTR": "współczynnik kliknięć",
    "spadek konwersji": "werdykt spadku konwersji",
    "współczynnik konwersji": "werdykt współczynnika konwersji",
    "wdrożona konfiguracja konwersji": "wdrożona konfiguracja konwersji",
    "Demand Gen launch ready": "gotowość uruchomienia Demand Gen",
    "zapis zmian GBP": "zapis zmian w profilu firmy",
    "lead quality": "jakość leadów",
    "link acquisition impact": "wpływ pozyskanych linków",
    "monthly performance verdict": "miesięczny werdykt skuteczności",
    "negative keyword addition": "dodanie wykluczających słów kluczowych",
    "opłacalność": "werdykt opłacalności",
    "ocena opłacalności": "werdykt opłacalności",
    "recommendation applied": "wdrożona rekomendacja",
    "recommendation write": "zapis rekomendacji",
    "przychód": "twierdzenie o przychodzie",
    "marnowanie budżetu na zapytaniach": "werdykt marnowania budżetu na zapytaniach",
    "spend": "wydatki reklamowe",
    "naprawiony pomiar": "twierdzenie o naprawionym pomiarze",
    "zmarnowany budżet": "werdykt przepalonego budżetu",
    "wpływ na przychód": "twierdzenie o wpływie na przychód",
    "wzrost konwersji": "obietnica wzrostu konwersji",
    "zwrot z reklam": "werdykt zwrotu z reklam",
    "ocena zmarnowanego budżetu": "werdykt przepalonego budżetu",
}


def operator_blocked_claims(claims: Iterable[str]) -> list[str]:
    values: list[str] = []
    for claim in claims:
        label = BLOCKED_CLAIM_LABELS.get(claim, claim.replace("_", " "))
        if label and label not in values:
            values.append(label)
    return values
