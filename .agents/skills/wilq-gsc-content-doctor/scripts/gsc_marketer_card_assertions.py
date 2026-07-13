from __future__ import annotations

from typing import Any


def validate_marketer_decision_card(
    content_diagnostics: dict[str, Any],
    endpoint_decision_trace: list[dict[str, Any]],
    content_action_id: str,
) -> dict[str, Any] | None:
    if content_diagnostics.get("live_data_available") is not True:
        return None
    decision = content_diagnostics.get("marketer_decision")
    if not isinstance(decision, dict):
        raise SystemExit("Content diagnostics must expose marketer_decision")
    if decision.get("review_card_label") != "Karta decyzji dla Wilka":
        raise SystemExit("Content marketer decision must expose Wilku review card label")
    required = {
        "review_decision_after_review",
        "review_question_for_wilku",
        "review_next_safe_click",
    }
    missing = [field for field in sorted(required) if not str(decision.get(field) or "").strip()]
    if missing:
        raise SystemExit(
            "Content marketer decision missing Wilku review fields: " + ", ".join(missing)
        )
    if "publik" not in str(decision.get("review_next_safe_click") or "").lower():
        raise SystemExit("Wilku review next click must explicitly block publication")
    selected = next(
        (
            item
            for item in endpoint_decision_trace
            if item.get("id") == decision.get("technical_decision_id")
        ),
        None,
    )
    selected_action_ids = (selected or {}).get("action_ids") or []
    expected = [content_action_id] if content_action_id in selected_action_ids else []
    if decision.get("review_action_ids") != expected:
        raise SystemExit("Wilku review card action IDs must match the selected content decision")
    return decision
