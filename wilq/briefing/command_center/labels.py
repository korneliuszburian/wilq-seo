from __future__ import annotations

from wilq.operator_labels import route_cta_label, route_operator_label, source_connector_label
from wilq.schemas import ConnectorStatus, DecisionState


def _decision_state_label(state: DecisionState) -> str:
    return {
        "ready": "gotowe",
        "stale": "do odświeżenia",
        "blocked": "zablokowane",
        "missing": "dane niepotwierdzone",
        "unknown": "status niepotwierdzony",
    }.get(state, "status niepotwierdzony")


def _priority_label(priority: int) -> str:
    if priority <= 12:
        return "najpierw"
    if priority <= 25:
        return "wysoki priorytet"
    if priority <= 45:
        return "do sprawdzenia"
    return "niżej w kolejce"


def _connector_label_map(connectors: list[ConnectorStatus]) -> dict[str, str]:
    return {connector.id: connector.label for connector in connectors if connector.label}


def _connector_label(connector_id: str, labels: dict[str, str]) -> str:
    return labels.get(connector_id) or source_connector_label(connector_id)


def _route_label(route: str) -> str:
    return route_operator_label(route)


def _route_cta_label(route: str) -> str:
    return route_cta_label(route)


def _skill_label(skill_id: str | None) -> str | None:
    if not skill_id:
        return None
    return {
        "wilq-ads-doctor": "diagnostyka Ads",
        "wilq-ahrefs-gap-finder": "luki SEO Ahrefs",
        "wilq-campaign-builder": "plan kampanii",
        "wilq-content-strategist": "strategia treści",
        "wilq-custom-segments": "segmenty Ads",
        "wilq-daily-command": "plan dnia",
        "wilq-demand-gen-operator": "Demand Gen",
        "wilq-ga4-analyst": "analiza GA4",
        "wilq-gsc-content-doctor": "GSC i treści",
        "wilq-localo-operator": "widoczność lokalna",
        "wilq-merchant-feed-operator": "plik produktowy Merchant",
        "wilq-social-publisher": "treści social",
    }.get(skill_id, "workflow WILQ")


def _evidence_count_summary(count: int) -> str:
    if count == 0:
        return "brak potwierdzonych śladów w WILQ"
    if count == 1:
        return "1 potwierdzony ślad w WILQ"
    return f"{count} potwierdzonych śladów w WILQ"


def _action_count_summary(count: int) -> str:
    if count == 0:
        return "brak bezpiecznej akcji na pierwszym ekranie"
    if count == 1:
        return "1 bezpieczna akcja do sprawdzenia"
    return f"{count} bezpiecznych akcji do sprawdzenia"


def _localo_contracts_phrase(contracts: list[str]) -> str:
    labels = {
        "place_inventory": "miejsca i profile",
        "local_rankings": "lokalne rankingi",
        "gbp_visibility": "profil firmy w Google",
        "competitor_visibility": "konkurencję",
        "reviews": "recenzje",
        "local_tasks": "zadania lokalne",
    }
    values = [labels.get(contract, "zakres danych Localo do sprawdzenia") for contract in contracts]
    if not values:
        return "żaden zakres danych Localo nie jest brakujący"
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} i {values[-1]}"


def _localo_claims_phrase(claims: list[str]) -> str:
    labels = {
        "lokalne rankingi": "lokalne rankingi",
        "wyniki profilu firmy w Google": "wyniki profilu firmy w Google",
        "widoczność konkurencji": "widoczność konkurencji",
        "tempo nowych opinii": "tempo nowych opinii",
        "ukończone zadanie lokalne": "ukończone zadanie lokalne",
        "zapis zmian w profilu firmy": "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej": "poprawa widoczności lokalnej",
    }
    values = [labels.get(claim, claim) for claim in claims]
    if not values:
        return "niepotwierdzone obietnice"
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} i {values[-1]}"


def _metric_tiles_sentence(metric_tiles: dict[str, float | int | str]) -> str:
    return ", ".join(_metric_tile_phrase(label, value) for label, value in metric_tiles.items())


def _metric_tile_phrase(label: str, value: float | int | str) -> str:
    if label == "produkty":
        return _count_phrase(value, "produkt", "produkty", "produktów")
    if label == "typy problemów":
        return _count_phrase(value, "typ problemu", "typy problemów", "typów problemów")
    if label == "zgłoszenia":
        return _count_phrase(
            value, "zgłoszenie problemu", "zgłoszenia problemów", "zgłoszeń problemów"
        )
    if label == "decyzje":
        return _count_phrase(value, "decyzja", "decyzje", "decyzji")
    if label == "blokady":
        return _count_phrase(value, "blokada", "blokady", "blokad")
    if label == "zapytania i adresy z GSC":
        return _count_phrase(
            value, "zapytanie i adres z GSC", "zapytania i adresy z GSC", "zapytań i adresów z GSC"
        )
    if label == "dopasowania WordPress":
        return _count_phrase(
            value, "dopasowanie WordPress", "dopasowania WordPress", "dopasowań WordPress"
        )
    if label == "wyświetlenia":
        return _count_phrase(value, "wyświetlenie", "wyświetlenia", "wyświetleń")
    if label == "kliknięcia":
        return _count_phrase(value, "kliknięcie", "kliknięcia", "kliknięć")
    if label == "ocena Ahrefs":
        return _count_phrase(value, "ocena Ahrefs", "oceny Ahrefs", "ocen Ahrefs")
    if label == "rekordy Ahrefs":
        return _count_phrase(value, "rekord Ahrefs", "rekordy Ahrefs", "rekordów Ahrefs")
    if label == "luki Ahrefs":
        return _count_phrase(value, "luka Ahrefs", "luki Ahrefs", "luk Ahrefs")
    if label == "luki linków":
        return _count_phrase(value, "luka linków", "luki linków", "luk linków")
    if label == "kampanie":
        return _count_phrase(value, "kampania", "kampanie", "kampanii")
    if label == "zapytania":
        return _count_phrase(value, "wyszukiwane hasło", "wyszukiwane hasła", "wyszukiwanych haseł")
    if label == "koszt":
        return f"koszt {value}"
    if label == "konwersje":
        return _count_phrase(value, "konwersja", "konwersje", "konwersji")
    if label == "wartość konwersji":
        return f"wartość konwersji {value}"
    if label == "podgląd budżetu":
        return _count_phrase(
            value, "budżet do sprawdzenia", "budżety do sprawdzenia", "budżetów do sprawdzenia"
        )
    if label == "rekomendacje":
        return _count_phrase(value, "rekomendacja", "rekomendacje", "rekomendacji")
    if label == "wykluczenia":
        return _count_phrase(value, "wykluczenie", "wykluczenia", "wykluczeń")
    if label == "segmenty":
        return _count_phrase(value, "segment", "segmenty", "segmentów")
    if label == "wskaźniki do sprawdzenia":
        return _count_phrase(
            value,
            "wiersz wskaźników kampanii",
            "wiersze wskaźników kampanii",
            "wierszy wskaźników kampanii",
        )
    if label == "wiersze kosztu pozyskania celu":
        return _count_phrase(
            value,
            "wiersz kosztu pozyskania celu",
            "wiersze kosztu pozyskania celu",
            "wierszy kosztu pozyskania celu",
        )
    if label == "wiersze zwrotu z reklam":
        return _count_phrase(
            value, "wiersz zwrotu z reklam", "wiersze zwrotu z reklam", "wierszy zwrotu z reklam"
        )
    return f"{label}: {value}"


def _count_phrase(value: float | int | str, one: str, few: str, many: str) -> str:
    if not isinstance(value, int | float):
        return f"{value} {many}"
    number = int(value)
    if isinstance(value, float) and not value.is_integer():
        return f"{value} {many}"
    if number == 1:
        word = one
    elif 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
        word = few
    else:
        word = many
    return f"{number} {word}"
