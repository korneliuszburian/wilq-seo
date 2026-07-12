from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.actions.gate_labels import action_gate_labels
from wilq.operator_labels import source_connector_labels
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionReviewGate,
    ActionRisk,
    ActionStatus,
    AuditEvent,
)

ConnectorLabel = Callable[[str], str]
EvidenceSummaryLabel = Callable[[list[str]], str]
ValidationStatusLabel = Callable[[str], str]
ReviewGateProjection = Callable[[ActionReviewGate], ActionReviewGate]
PreviewCards = Callable[[ActionObject], list[ActionPreviewCardViewModel]]
AuditEventProjection = Callable[[AuditEvent], AuditEvent]


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


def action_with_operator_labels(
    action: ActionObject,
    *,
    connector_label: ConnectorLabel,
    evidence_summary_label: EvidenceSummaryLabel,
    validation_status_label: ValidationStatusLabel,
    review_gate: ReviewGateProjection,
    preview_cards: PreviewCards,
    audit_event: AuditEventProjection,
) -> ActionObject:
    return action.model_copy(
        update={
            "connector_label": connector_label(action.connector),
            "mode_label": action_mode_label(action.mode),
            "risk_label": action_risk_label(action.risk),
            "status_label": action_status_label(action.status),
            "evidence_summary_label": evidence_summary_label(action.evidence_ids),
            "validation_status_label": validation_status_label(action.validation_status),
            "review_gate": review_gate(action.review_gate),
            "preview_cards": preview_cards(action),
            "audit_events": [audit_event(event) for event in action.audit_events],
        }
    )


def review_gate_with_operator_labels(
    gate: ActionReviewGate,
    *,
    review_outcome_label: Callable[[str], str],
    blocker_count_label: Callable[[list[str]], str],
) -> ActionReviewGate:
    return gate.model_copy(
        update={
            "status_label": action_review_gate_status_label(gate.status),
            "apply_blocker_summary_label": blocker_count_label(
                gate.apply_blocker_labels or gate.apply_blockers
            ),
            "last_mutation_blocker_summary_label": blocker_count_label(
                gate.last_mutation_blocker_labels or gate.last_mutation_blockers
            ),
            "last_review_outcome_label": review_outcome_label(gate.last_review_outcome)
            if gate.last_review_outcome
            else None,
            "last_impact_check_status_label": action_result_status_label(
                gate.last_impact_check_status
            )
            if gate.last_impact_check_status
            else None,
            "last_mutation_audit_status_label": action_mutation_audit_status_label(
                gate.last_mutation_audit_status
            )
            if gate.last_mutation_audit_status
            else None,
            "last_mutation_attempted_label": action_mutation_attempted_label(
                gate.last_mutation_attempted
            ),
            "last_mutation_adapter_reached_label": action_mutation_adapter_reached_label(
                gate.last_mutation_adapter_reached
            ),
            "last_external_write_attempted_label": action_mutation_attempted_label(
                gate.last_external_write_attempted
            ),
            "last_mutation_adapter_label": action_mutation_adapter_label(
                gate.last_mutation_adapter
            ),
            "last_mutation_audit_trace_label": action_mutation_audit_trace_label(
                gate.last_mutation_audit_event_id
            ),
        }
    )


def operator_state_label(value: str) -> str:
    labels = {
        "blocked": "zablokowane",
        "ready": "gotowe",
        "allowed": "dopuszczone",
        "missing": "status niepotwierdzony",
        "pending_validation": "czeka na sprawdzenie",
        "validated_prepare_only": "kontrola WILQ poprawna",
        "ready_to_apply": "gotowe do potwierdzenia",
        "blocked_apply": "zapis zmian zablokowany",
    }
    return labels.get(value, "do sprawdzenia")


def ads_recommendation_type_label(value: str) -> str:
    labels = {
        "CAMPAIGN_BUDGET": "budżet kampanii",
        "KEYWORD": "słowa kluczowe",
        "RESPONSIVE_SEARCH_AD": "elastyczna reklama w wyszukiwarce",
        "TARGET_CPA_OPT_IN": "strategia kosztu pozyskania celu",
        "TARGET_ROAS_OPT_IN": "strategia zwrotu z reklam",
        "MAXIMIZE_CONVERSIONS_OPT_IN": "maksymalizacja konwersji",
        "MAXIMIZE_CONVERSION_VALUE_OPT_IN": "maksymalizacja wartości konwersji",
        "IMPROVE_PERFORMANCE_MAX_AD_STRENGTH": "jakość zasobów Performance Max",
        "DISPLAY_EXPANSION_OPT_IN": "rozszerzenie kampanii na sieć reklamową",
        "DYNAMIC_IMAGE_EXTENSION_OPT_IN": "dynamiczne rozszerzenia graficzne",
        "SEARCH_PARTNERS_OPT_IN": "rozszerzenie kampanii na partnerów wyszukiwania",
        "UNKNOWN": "typ rekomendacji nieznany",
        "UNSPECIFIED": "typ rekomendacji nieokreślony",
    }
    return labels.get(value, "typ rekomendacji do sprawdzenia")


def ads_keyword_match_type_label(value: str) -> str:
    labels = {
        "BROAD": "dopasowanie przybliżone",
        "PHRASE": "dopasowanie do wyrażenia",
        "EXACT": "dopasowanie ścisłe",
        "UNKNOWN": "dopasowanie nieznane",
        "UNSPECIFIED": "dopasowanie nieokreślone",
    }
    return labels.get(value, "dopasowanie do sprawdzenia")


def ads_negative_keyword_level_label(value: str) -> str:
    labels = {
        "ad_group": "grupa reklam",
        "campaign_review_required": "poziom kampanii wymaga sprawdzenia",
    }
    return labels.get(value, "poziom do sprawdzenia")


def wordpress_post_status_label(value: str) -> str:
    labels = {
        "draft": "szkic",
        "pending": "czeka na sprawdzenie",
        "private": "prywatny",
        "publish": "opublikowany",
    }
    return labels.get(value, "status wpisu do sprawdzenia")


def payload_with_operator_labels(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    _hydrate_operator_labels_recursive(enriched)
    return enriched


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _hydrate_operator_labels_recursive(value: Any) -> None:
    if isinstance(value, dict):
        _hydrate_operator_label_fields(value)
        for item in value.values():
            _hydrate_operator_labels_recursive(item)
    elif isinstance(value, list):
        for item in value:
            _hydrate_operator_labels_recursive(item)


def _hydrate_operator_label_fields(item: dict[str, Any]) -> None:
    if item.get("status_label") in (None, "") and isinstance(item.get("status"), str):
        item["status_label"] = operator_state_label(item["status"])
    if item.get("post_status_label") in (None, "") and isinstance(item.get("post_status"), str):
        item["post_status_label"] = wordpress_post_status_label(item["post_status"])
    label_fields = {
        "required_validation": "required_validation_labels",
        "operator_review_gates": "operator_review_gate_labels",
        "human_review_gates": "human_review_gate_labels",
        "draft_constraints": "draft_constraint_labels",
        "missing_read_contracts": "missing_read_contract_labels",
        "missing_requirements": "missing_requirement_labels",
        "required_google_ads_state": "required_google_ads_state_labels",
        "allowed_uses_after_confirmation": "allowed_uses_after_confirmation_labels",
        "allowed_contracts": "allowed_contract_labels",
        "target_roas_or_cpa": "target_roas_or_cpa_labels",
        "blocked_claims": "blocked_claim_labels",
    }
    for source_key, label_key in label_fields.items():
        if _string_list(item.get(label_key)):
            continue
        source_values = _string_list(item.get(source_key))
        if source_values:
            item[label_key] = action_gate_labels(source_values)
    if item.get("recommendation_type_label") in (None, "") and isinstance(
        item.get("recommendation_type"),
        str,
    ):
        item["recommendation_type_label"] = ads_recommendation_type_label(
            item["recommendation_type"]
        )
    if item.get("match_type_label") in (None, "") and isinstance(item.get("match_type"), str):
        item["match_type_label"] = ads_keyword_match_type_label(item["match_type"])
    if item.get("level_label") in (None, "") and isinstance(item.get("level"), str):
        item["level_label"] = ads_negative_keyword_level_label(item["level"])
