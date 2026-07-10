from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from wilq.schemas import DailyCheckItem, DailyCheckResult, FreshnessState


def test_daily_check_result_requires_traceable_operator_items() -> None:
    traced_item = DailyCheckItem(
        id="daily_check_merchant_review",
        category="safe_next_action",
        title="Przejrzyj kolejkę Merchant",
        status="review_required",
        priority=1,
        summary="Merchant ma zgłoszenia wymagające ręcznego review.",
        next_step="Otwórz Merchant i sprawdź akcję review.",
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_refresh_merchant"],
        expert_rule_ids=["merchant_feed_rules_v1"],
        freshness=FreshnessState(state="fresh"),
        action_ids=["act_review_merchant_feed_issues"],
        blocked_claims=["revenue_recovery"],
    )
    result = DailyCheckResult(
        workspace_id="ekologus",
        date=date(2026, 7, 7),
        status="review_ready",
        checked_connectors=[
            {
                "connector_id": "google_merchant_center",
                "status": "checked",
                "freshness": {"state": "fresh"},
                "reason": "latest vendor read available",
            }
        ],
        safe_next_actions=[traced_item],
        freshness=FreshnessState(state="fresh"),
    )

    assert result.evidence_ids == ["ev_refresh_merchant"]
    assert result.source_connectors == ["google_merchant_center"]
    assert result.expert_rules_used == ["merchant_feed_rules_v1"]

    with pytest.raises(ValidationError):
        DailyCheckItem(
            id="daily_check_generic_advice",
            category="safe_next_action",
            title="Zrób ogólną optymalizację",
            status="review_required",
            priority=1,
            summary="Brakuje dowodów i reguły.",
            next_step="Nie powinno przejść.",
        )
