from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic

import pytest

import wilq.actions.service as action_service
from wilq.schemas import ActionMode, ActionObject, ActionRisk, ActionStatus, OpportunityDomain


def test_action_list_cache_reuses_one_registry_build_outside_test_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_ACTION_LIST_CACHE_SECONDS", "60")
    action_service.clear_action_list_cache()
    calls = 0
    sentinel: list[object] = []

    def fake_list_actions() -> list[object]:
        nonlocal calls
        calls += 1
        return sentinel

    monkeypatch.setattr(action_service, "list_actions", fake_list_actions)
    assert action_service.list_actions_cached() is sentinel
    assert action_service.list_actions_cached() is sentinel
    assert calls == 1
    action_service.clear_action_list_cache()
    assert action_service.list_actions_cached() is sentinel
    assert calls == 2


def test_action_detail_reuses_warm_registry_copy_and_keeps_fresh_gate_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_ACTION_LIST_CACHE_SECONDS", "60")
    cached_action = ActionObject(
        id="act_cached_localo",
        title="Cached Localo",
        domain=OpportunityDomain.localo,
        connector="localo",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_cached"],
        human_diagnosis="Diagnoza",
        recommended_reason="Powód",
        payload={"action_type": "local_visibility_task"},
        validation_status="not_validated",
        created_by="test",
        created_at=datetime.now(UTC),
    )
    action_service._cached_action_list = action_service.ActionListCacheEntry(
        created_at=monotonic(),
        actions=[cached_action],
    )
    monkeypatch.setattr(
        action_service,
        "seed_metric_action_candidates",
        lambda: (_ for _ in ()).throw(AssertionError("warm cache must avoid rebuilding metrics")),
    )
    monkeypatch.setattr(action_service, "_with_persisted_validation_state", lambda action: action)
    monkeypatch.setattr(action_service, "_with_review_gate", lambda action, *_args: action)

    result = action_service.get_action("act_cached_localo")

    assert result is not None
    assert result.id == "act_cached_localo"
    assert result is not cached_action
    action_service.clear_action_list_cache()
