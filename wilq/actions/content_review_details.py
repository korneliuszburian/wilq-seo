from __future__ import annotations

from wilq.actions.audit_store import audit_event_has_raw_contract_text
from wilq.schemas import AuditEvent


def is_raw_content_review_audit_event(action_id: str, event: AuditEvent) -> bool:
    if action_id != "act_prepare_content_refresh_queue":
        return False
    if not event.event_type.startswith("human_review_"):
        return False
    return audit_event_has_raw_contract_text(event)

def content_url_review_details(checked_items: list[str]) -> dict[str, str]:
    return _details_for_allowed_keys(
        checked_items,
        {"candidate", "url_review_outcome", "reviewed_url", "review_notes"},
    )


def draft_readiness_review_details(checked_items: list[str]) -> dict[str, str]:
    return _details_for_allowed_keys(
        checked_items,
        {
            "candidate",
            "draft_readiness_outcome",
            "canonical_review_outcome",
            "duplicate_review_outcome",
            "legal_factual_review_outcome",
            "human_review_outcome",
            "draft_readiness_notes",
        },
    )


def _details_for_allowed_keys(
    checked_items: list[str],
    allowed_keys: set[str],
) -> dict[str, str]:
    details: dict[str, str] = {}
    for item in checked_items:
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in allowed_keys and value:
            details[key] = value
    return details
