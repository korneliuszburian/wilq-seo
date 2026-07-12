"""Read-only audit history projections used by the action service."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from wilq.operator_labels import impact_comparison_summary_label
from wilq.schemas import ActionMutationAuditRecord, AuditEvent
from wilq.storage.local_state import local_state_store

_MAX_EVENTS_PER_ACTION = 10

StringList = Callable[[Any], list[str]]
OperatorItemLabel = Callable[[str], str]

RAW_AUDIT_IDENTIFIER_RE = re.compile(r"\baudit_[A-Za-z0-9_:-]+\b")
RAW_AUDIT_REFERENCE_CLAUSE_RE = re.compile(
    r"\s*(Audyt podglądu|ID audytu|Ślad audytu):\s*audit_[A-Za-z0-9_:-]+\.?\s*",
    flags=re.IGNORECASE,
)


def action_audit_summary_for_operator(event: AuditEvent) -> str:
    if event.event_type == "action_preview_generated":
        return operator_preview_summary_from_audit(event.summary)
    if event.event_type in {"action_apply_confirmed", "action_apply_confirmation_confirmed"}:
        return operator_audit_summary_text(event.summary) or (
            "Podgląd zmian potwierdzony. Nie zapisano zmian w zewnętrznych systemach."
        )
    if event.event_type in {"action_confirmation_blocked", "action_apply_confirmation_blocked"}:
        return operator_audit_summary_text(event.summary) or (
            "Potwierdzenie podglądu zablokowane. Nie zapisano zmian w zewnętrznych systemach."
        )
    if event.event_type in {"action_impact_check_completed", "action_impact_check_blocked"}:
        return operator_impact_summary_from_audit(event.summary)
    if event.event_type == "action_apply_blocked":
        return "Zapis zmian zablokowany przez warunki bezpieczeństwa WILQ."
    if event.event_type == "action_apply_completed":
        return "Zapis zmian wykonany i zapisany w audycie bezpieczeństwa."
    return operator_audit_summary_text(event.summary)


def operator_audit_summary_text(summary: str) -> str:
    clean_summary = str(summary or "").strip()
    if contains_raw_audit_contract_text(clean_summary):
        return "Historyczny ślad bezpieczeństwa. Nie zapisano zmian w zewnętrznych systemach."
    clean_summary = remove_raw_audit_identifiers(clean_summary)
    return normalize_operator_summary_text(clean_summary)


def remove_raw_audit_identifiers(summary: str) -> str:
    if not RAW_AUDIT_IDENTIFIER_RE.search(summary):
        return summary
    without_reference_clause = RAW_AUDIT_REFERENCE_CLAUSE_RE.sub(" ", summary)
    if RAW_AUDIT_IDENTIFIER_RE.search(without_reference_clause):
        return "Zdarzenie audytu zapisane. Szczegóły techniczne są dostępne w audycie."
    return " ".join(without_reference_clause.split())


def operator_note_sentence(notes: str) -> str:
    note = str(notes or "").strip().rstrip(".")
    note = re.sub(
        r"\s*Ten krok nie zapisuje zmian(?: w zewnętrznych systemach)?\.?$",
        "",
        note,
        flags=re.IGNORECASE,
    ).strip()
    if not note:
        return ""
    return f"Notatka: {note}. "


def normalize_operator_summary_text(summary: str) -> str:
    compact = " ".join(str(summary or "").split())
    compact = re.sub(r"\.{2,}", ".", compact)
    return re.sub(
        r"Ten krok nie zapisuje zmian\. (?=Ten krok nie zapisuje zmian w zewnętrznych systemach\.)",
        "",
        compact,
    )


def audit_event_has_raw_contract_text(event: AuditEvent) -> bool:
    if contains_raw_audit_contract_text(event.summary):
        return True
    return audit_detail_contains_raw_contract_text(event.details)


def audit_detail_contains_raw_contract_text(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            contains_raw_audit_contract_text(str(key))
            or audit_detail_contains_raw_contract_text(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(audit_detail_contains_raw_contract_text(item) for item in value)
    if isinstance(value, str):
        return contains_raw_audit_contract_text(value)
    return False


def audit_details_for_operator(
    details: dict[str, Any],
    *,
    string_list: StringList,
    review_summary_item: OperatorItemLabel,
    review_blocker_label: OperatorItemLabel,
) -> dict[str, Any]:
    operator_details: dict[str, Any] = {}
    for key, value in details.items():
        if contains_raw_audit_contract_text(str(key)):
            continue
        clean_value = _audit_detail_value_for_operator(value)
        if clean_value is not None:
            operator_details[str(key)] = clean_value
    checked_items = string_list(operator_details.get("checked_items"))
    if checked_items:
        operator_details["checked_items"] = [review_summary_item(item) for item in checked_items]
    blockers = string_list(operator_details.get("blockers"))
    if blockers:
        operator_details["blockers"] = [review_blocker_label(item) for item in blockers]
    return operator_details


def _audit_detail_value_for_operator(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if contains_raw_audit_contract_text(str(key)):
                continue
            clean_item = _audit_detail_value_for_operator(item)
            if clean_item is not None:
                clean[str(key)] = clean_item
        return clean or None
    if isinstance(value, list):
        clean_items = [
            clean_item
            for item in value
            if (clean_item := _audit_detail_value_for_operator(item)) is not None
        ]
        return clean_items or None
    if isinstance(value, str) and contains_raw_audit_contract_text(value):
        return None
    return value


def contains_raw_audit_contract_text(summary: str) -> bool:
    raw_fragments = (
        "blocked_claim:",
        "candidate:",
        "ekologus.dev.proudsite.pl",
        "mapping_",
        "payload_",
        "source_type:",
        "staging handoff",
        "target" "_site",
        "target" "_site" "_",
        "target" "_site" "_migration",
        "Explicit apply confirmation is required",
        "Action must be validated before apply",
        "Action mode must be apply before external execution",
    )
    return any(fragment in summary for fragment in raw_fragments)


def operator_preview_summary_from_audit(summary: str) -> str:
    item_summary = ""
    if "pozycje=" in summary:
        item_fragment = summary.split("pozycje=", 1)[1].split(",", 1)[0].split(".", 1)[0]
        if item_fragment:
            item_summary = f" Pokazano {item_fragment} pozycji do sprawdzenia."
    if "blocked" in summary or "zablokowany" in summary:
        return (
            "Podgląd zmian przygotowany, ale zapis zmian pozostaje zablokowany."
            f"{item_summary} Nie zapisano zmian w zewnętrznych systemach."
        )
    return f"Podgląd zmian przygotowany.{item_summary} Nie zapisano zmian w zewnętrznych systemach."


def operator_impact_summary_from_audit(summary: str) -> str:
    prefix = (
        "Sprawdzenie efektu zablokowane."
        if "status=blocked" in summary or "zablok" in summary
        else "Sprawdzenie efektu zapisane."
    )
    window_parts = [
        operator_impact_summary_part(part.strip())
        for part in summary.split(".")
        if part.strip().startswith(
            (
                "Okno przed zmianą",
                "Okno po zmianie",
                "Porównanie sprzed zmiany",
                "Porównanie po zmianie",
                "Metryki z dowodami",
            )
        )
    ]
    clean_parts = [prefix, *[f"{part}." for part in window_parts]]
    if "Ten krok nie zapisuje zmian" not in " ".join(clean_parts):
        clean_parts.append("Ten krok nie zapisuje zmian w zewnętrznych systemach.")
    return " ".join(clean_parts)


def operator_impact_summary_part(part: str) -> str:
    return impact_comparison_summary_label(part) or part


def audit_event_label(event_type: str) -> str:
    labels = {
        "action_preview_generated": "Podgląd zmian wygenerowany",
        "human_review_approved_for_prepare": "Przegląd operatora zapisany",
        "human_review_needs_changes": "Przegląd wymaga poprawek",
        "human_review_rejected": "Przegląd odrzucony",
        "human_review_deferred": "Przegląd odłożony",
        "action_apply_confirmed": "Podgląd potwierdzony",
        "action_confirmation_blocked": "Potwierdzenie zablokowane",
        "action_apply_confirmation_blocked": "Potwierdzenie zablokowane",
        "action_impact_check_completed": "Sprawdzenie efektu zapisane",
        "action_impact_check_blocked": "Sprawdzenie efektu zablokowane",
        "apply_confirmation_missing": "Zapis zmian zablokowany",
        "action_apply_blocked": "Zapis zmian zablokowany",
        "action_apply_completed": "Zapis zmian wykonany",
    }
    return labels.get(event_type, "Zdarzenie audytu")


def latest_preview_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type == "action_preview_generated":
            return event
    return None


def latest_action_confirmation_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type in {
            "action_apply_confirmed",
            "ads_target_guardrail_confirmed",
        }:
            return event
    return None


def latest_action_impact_check_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type in {"action_impact_check_completed", "action_impact_check_blocked"}:
            return event
    return None


def latest_mutation_audit(
    audits: list[ActionMutationAuditRecord],
) -> ActionMutationAuditRecord | None:
    if not audits:
        return None
    return sorted(audits, key=lambda item: item.created_at, reverse=True)[0]


def persisted_audit_events_by_action_id(action_ids: set[str]) -> dict[str, list[AuditEvent]]:
    if not action_ids:
        return {}
    events_by_action_id: dict[str, list[AuditEvent]] = {action_id: [] for action_id in action_ids}
    for event in local_state_store().list_audit_events():
        if event.action_id not in action_ids:
            continue
        action_events = events_by_action_id.setdefault(event.action_id, [])
        if len(action_events) < _MAX_EVENTS_PER_ACTION:
            action_events.append(event)
    return events_by_action_id


def persisted_audit_events_for_action(action_id: str) -> list[AuditEvent]:
    return local_state_store().list_audit_events(action_id=action_id)[:_MAX_EVENTS_PER_ACTION]


def persisted_mutation_audits_by_action_id(
    action_ids: set[str],
) -> dict[str, list[ActionMutationAuditRecord]]:
    if not action_ids:
        return {}
    audits_by_action_id: dict[str, list[ActionMutationAuditRecord]] = {
        action_id: [] for action_id in action_ids
    }
    for audit in local_state_store().list_action_mutation_audits():
        if audit.action_id not in action_ids:
            continue
        action_audits = audits_by_action_id.setdefault(audit.action_id, [])
        if len(action_audits) < _MAX_EVENTS_PER_ACTION:
            action_audits.append(audit)
    return audits_by_action_id


def persisted_mutation_audits_for_action(
    action_id: str,
) -> list[ActionMutationAuditRecord]:
    return local_state_store().list_action_mutation_audits(action_id=action_id)[
        :_MAX_EVENTS_PER_ACTION
    ]
