from __future__ import annotations

from typing import Any


def validate_custom_segment_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not payload.get("terms"):
        errors.append("Custom segment payload requires real evidence-backed terms.")
    if payload.get("invented_terms") is True:
        errors.append("Custom segment payload must not contain invented terms.")
    if not payload.get("evidence_ids"):
        errors.append("Custom segment payload requires evidence IDs.")
    return errors
