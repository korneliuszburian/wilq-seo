from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.schemas import ActionPreviewCardViewModel, ActionPreviewRowViewModel

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
ValueLabel = Callable[[Any], str]
MoneyLabel = Callable[[Any], str]
StateLabel = Callable[[Any], str]


def search_term_ngram_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    plain_metric_value_label: ValueLabel,
    micros_money_label: MoneyLabel,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render search-term n-gram cards without exposing technical payloads."""
    preview_items = [item for item in payload.get("ngram_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        sample_terms = string_list(item.get("sample_search_terms"))
        rows = [
            preview_row("Temat", str(item.get("ngram") or "temat do sprawdzenia")),
            preview_row("Rozmiar", plain_metric_value_label(item.get("ngram_size"))),
            preview_row(
                "Zapytania użytkowników",
                plain_metric_value_label(item.get("source_search_term_count")),
            ),
            preview_row(
                "Przykłady",
                ", ".join(sample_terms[:3]) if sample_terms else "brak przykładów",
            ),
            preview_row("Kliknięcia", plain_metric_value_label(item.get("clicks"))),
            preview_row("Wyświetlenia", plain_metric_value_label(item.get("impressions"))),
            preview_row("Koszt", micros_money_label(item.get("cost_micros"))),
            preview_row("Konwersje", plain_metric_value_label(item.get("conversions"))),
        ]
        missing_read_contract_labels = string_list(item.get("missing_read_contract_labels"))
        if missing_read_contract_labels:
            rows.append(preview_row("Braki", ", ".join(missing_read_contract_labels[:4])))
        requirement_labels = string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_claim_labels = string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=str(item.get("id") or f"search_term_ngram_preview_{index}"),
                kind="google_ads_search_term_ngram_review",
                title_label="Temat zapytań do sprawdzenia",
                subtitle_label="ocena intencji zapytań bez zapisu zmian",
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards
