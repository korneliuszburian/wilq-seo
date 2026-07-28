"""Fail-closed payload validation for a local new-page draft ActionObject."""

from __future__ import annotations

from typing import Any

from wilq.actions.validation_copy import missing, wrong
from wilq.content.workflow.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CONTRACT,
)


def validate_new_page_draft_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("mode") != "dev_draft_only":
        errors.append(wrong("Nowy szkic dev", "musi pozostać w trybie dev_draft_only"))
    if payload.get("preview_contract") != CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_CONTRACT:
        errors.append(missing("Nowy szkic dev", "kontraktu dokładnego podglądu"))
    binding = payload.get("new_page_draft_binding")
    if not isinstance(binding, dict):
        errors.append(missing("Nowy szkic dev", "exact bindingu strony"))
    else:
        for key in (
            "work_item_id",
            "brief_id",
            "brief_digest",
            "foundation_id",
            "service_card_id",
            "service_card_digest",
            "revision_id",
            "revision_digest",
            "authoring_profile_digest",
            "content_type",
        ):
            if not isinstance(binding.get(key), str) or not binding[key].strip():
                errors.append(missing("Nowy szkic dev", f"pola {key}"))
    preview = payload.get("payload_preview")
    if not isinstance(preview, list) or len(preview) != 1 or not isinstance(preview[0], dict):
        errors.append(missing("Nowy szkic dev", "jednej pozycji podglądu"))
    if payload.get("destructive") is not False:
        errors.append(wrong("Nowy szkic dev", "nie może być destrukcyjny"))
    return errors
