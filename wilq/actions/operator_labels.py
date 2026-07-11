from __future__ import annotations

from wilq.operator_labels import source_connector_labels
from wilq.schemas import ActionMode, ActionRisk, ActionStatus


def action_mode_label(value: ActionMode | str) -> str:
    labels = {
        "suggest": "propozycja",
        "prepare": "przygotowanie",
        "apply": "zapis zmian",
    }
    return labels.get(str(value), "tryb akcji")


def action_risk_label(value: ActionRisk | str) -> str:
    labels = {
        "low": "niskie ryzyko",
        "medium": "średnie ryzyko",
        "high": "wysokie ryzyko",
        "critical": "krytyczne ryzyko",
    }
    return labels.get(str(value), "ryzyko do sprawdzenia")


def action_status_label(value: ActionStatus | str) -> str:
    labels = {
        "new": "nowa",
        "ready": "gotowa do sprawdzenia",
        "needs_validation": "wymaga sprawdzenia w WILQ",
        "validation_failed": "sprawdzenie wykazało problem",
        "ready_to_apply": "gotowa do potwierdzenia zapisu",
        "applying": "zapis zmian w toku",
        "applied": "zmiany zapisane",
        "failed": "błąd zapisu",
        "dismissed": "odrzucona",
        "blocked": "zablokowana",
    }
    return labels.get(str(value), "status akcji do sprawdzenia")


def action_evidence_summary_label(evidence_ids: list[str]) -> str:
    count = len(evidence_ids)
    if count == 0:
        return "Nie ma dowodów źródłowych; nie traktuj tego jako rekomendacji"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def action_validation_status_label(value: str) -> str:
    labels = {
        "not_validated": "nie sprawdzono w WILQ",
        "valid": "kontrola WILQ poprawna",
        "invalid": "wymaga poprawek",
    }
    return labels.get(value, "status sprawdzenia")


def action_review_gate_status_label(value: str) -> str:
    labels = {
        "pending_validation": "czeka na sprawdzenie",
        "validated_prepare_only": "kontrola WILQ poprawna",
        "ready_to_apply": "gotowe do potwierdzenia",
        "blocked_apply": "zapis zmian zablokowany",
    }
    return labels.get(value, "status warunków")


def action_mutation_audit_status_label(value: str | None) -> str:
    labels = {
        "blocked": "zablokowany",
        "applied": "zapisany",
        "failed": "błąd",
    }
    return labels.get(value or "", "stan zapisu nieustalony")


def action_mutation_attempted_label(value: bool | None) -> str:
    if value is True:
        return "próbowano zapisu w systemie zewnętrznym"
    if value is False:
        return "nie próbowano zapisu w systemie zewnętrznym"
    return "brak informacji o próbie zapisu"


def action_mutation_adapter_reached_label(value: bool | None) -> str:
    if value is True:
        return "adapter wykonania został osiągnięty"
    if value is False:
        return "adapter wykonania nie został osiągnięty"
    return "brak informacji o adapterze wykonania"


def action_mutation_adapter_label(value: str | None) -> str:
    if not value:
        return "brak bezpiecznej ścieżki zapisu"
    labels = source_connector_labels([value])
    return labels[0] if labels else "system zewnętrzny wskazany"


def action_mutation_audit_trace_label(value: str | None) -> str:
    if value:
        return "ślad bezpieczeństwa zapisany"
    return "ślad bezpieczeństwa niepowiązany"


def action_result_status_label(value: str | None) -> str:
    labels = {
        "preview_ready": "podgląd gotowy",
        "generated": "wygenerowany",
        "confirmed": "potwierdzony",
        "recorded": "zapisane",
        "completed": "zapisane",
        "checked": "sprawdzone",
        "valid": "poprawna",
        "invalid": "wymaga poprawek",
        "applied": "zapisane",
        "blocked": "zablokowany",
        "failed": "błąd",
    }
    return labels.get(value or "", "zapisane")
