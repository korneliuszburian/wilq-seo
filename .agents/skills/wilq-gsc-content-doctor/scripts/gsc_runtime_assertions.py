from __future__ import annotations

from collections.abc import Callable
from typing import Any


def validate_gsc_runtime(
    api_base: str,
    diagnostics: dict[str, Any],
    facts: list[dict[str, Any]],
    action_id: str,
    validate_action_ids: Callable[..., list[dict[str, Any]]],
) -> tuple[int, list[dict[str, Any]]]:
    query_page_count = sum(
        1
        for fact in facts
        if {"query", "page"}.issubset(set((fact.get("dimensions") or {}).keys()))
    )
    if query_page_count and not diagnostics.get("query_page_count"):
        raise SystemExit("GSC query/page facts exist but diagnostics query_page_count is zero")
    action_ids = diagnostics.get("action_ids") or []
    if diagnostics.get("live_data_available") is True and action_id not in action_ids:
        raise SystemExit("Live GSC diagnostics must expose content refresh action")
    return query_page_count, validate_action_ids(
        api_base, [action_id] if action_id in action_ids else [], label="GSC content"
    )
