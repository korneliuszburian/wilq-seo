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
    monkeypatch.setattr(action_service, "_google_ads_registry_cache_key", lambda: None)
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
    monkeypatch.setattr(action_service, "_google_ads_registry_cache_key", lambda: None)
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


def test_action_detail_rebuilds_warm_registry_when_google_ads_read_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_ACTION_LIST_CACHE_SECONDS", "60")
    legacy_action = ActionObject(
        id="act_configure_google_ads_env",
        title="Odnow dostęp Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_cached"],
        human_diagnosis="Dawny odczyt nie był dostępny.",
        recommended_reason="Przygotuj naprawę dostępu.",
        payload={"action_type": "repair_google_ads_oauth"},
        validation_status="not_validated",
        created_by="test",
        created_at=datetime.now(UTC),
    )
    action_service._cached_action_list = action_service.ActionListCacheEntry(
        created_at=monotonic(),
        actions=[legacy_action],
        google_ads_registry_key=("refresh_before_live", "completed", False),
    )
    monkeypatch.setattr(
        action_service,
        "_google_ads_registry_cache_key",
        lambda: ("refresh_live", "completed", True),
    )
    rebuilds = 0

    def fresh_registry() -> dict[str, ActionObject]:
        nonlocal rebuilds
        rebuilds += 1
        return {}

    monkeypatch.setattr(action_service, "_action_registry", fresh_registry)

    assert action_service.get_action("act_configure_google_ads_env") is None
    assert rebuilds == 1
    action_service.clear_action_list_cache()


def test_action_list_cache_skips_unstable_google_ads_registry_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_ACTION_LIST_CACHE_SECONDS", "60")
    action_service.clear_action_list_cache()
    legacy_action = ActionObject(
        id="act_configure_google_ads_env",
        title="Odnow dostęp Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_cached"],
        human_diagnosis="Dawny odczyt nie był dostępny.",
        recommended_reason="Przygotuj naprawę dostępu.",
        payload={"action_type": "repair_google_ads_oauth"},
        validation_status="not_validated",
        created_by="test",
        created_at=datetime.now(UTC),
    )
    current_action = legacy_action.model_copy(
        update={"id": "act_confirm_ads_target_guardrails"}
    )
    before_live = ("refresh_before_live", "completed", False)
    live = ("refresh_live", "completed", True)
    keys = [before_live, live, live, live]
    monkeypatch.setattr(
        action_service,
        "_google_ads_registry_cache_key",
        lambda: keys.pop(0) if keys else live,
    )
    builds = 0

    def changing_registry() -> list[ActionObject]:
        nonlocal builds
        builds += 1
        return [legacy_action] if builds == 1 else [current_action]

    monkeypatch.setattr(action_service, "list_actions", changing_registry)

    actions = action_service.list_actions_cached()

    assert [action.id for action in actions] == ["act_confirm_ads_target_guardrails"]
    assert builds == 2
    assert action_service._cached_action_list is not None
    assert action_service._cached_action_list.google_ads_registry_key == live
    action_service.clear_action_list_cache()
