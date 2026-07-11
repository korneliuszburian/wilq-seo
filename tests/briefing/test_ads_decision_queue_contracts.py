from __future__ import annotations

from typing import Any, cast

from wilq.briefing.ads_decision_queue import decision_priority
from wilq.schemas import AdsDecisionItem


def _decision(decision_type: str) -> AdsDecisionItem:
    return AdsDecisionItem(
        id=f"decision_{decision_type}",
        decision_type=cast(Any, decision_type),
        status="ready",
        title="Decyzja Ads",
        summary="Podsumowanie decyzji Ads.",
        rationale="Powód do sprawdzenia.",
        next_step="Sprawdź dowody.",
    )


def test_decision_priority_keeps_safety_and_review_order() -> None:
    assert decision_priority(_decision("fix_ads_access")) == 5
    assert decision_priority(_decision("block_write_actions")) == 10
    assert decision_priority(_decision("review_campaign_activity")) == 20
    assert decision_priority(_decision("review_change_history")) == 65
