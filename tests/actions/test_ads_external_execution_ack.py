from __future__ import annotations

from types import SimpleNamespace

from tests._contract_support.api_client import client


def test_ads_external_execution_acknowledgement_persists_exact_measurement_binding(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ack.sqlite3"))
    action_id = "act_prepare_ads_campaign_review_queue"
    plan_id = "ads_measurement_plan_campaign_change_review_v1"
    action = SimpleNamespace(
        id=action_id,
        payload={
            "action_type": "campaign_change_review",
            "measurement_plan": {
                "id": plan_id,
                "source_action_id": action_id,
                "baseline_evidence_ids": ["ev_ads_baseline"],
                "execution_acknowledgement_required": True,
                "observation_required": True,
            },
        },
    )

    import apps.api.wilq_api.routers.actions as actions_router

    monkeypatch.setattr(
        actions_router,
        "get_action",
        lambda requested_id: action if requested_id == action_id else None,
    )

    response = client.post(
        f"/api/actions/{action_id}/external-execution-acknowledgement",
        json={
            "measurement_plan_id": plan_id,
            "execution_status": "executed",
            "acknowledged_by": "Wilku",
            "executed_at": "2026-07-18T10:00:00Z",
            "notes": "Zmianę wykonano ręcznie w Google Ads.",
        },
    )
    assert response.status_code == 200, response.text
    event = response.json()
    assert event["event_type"] == "ads_external_execution_acknowledged"
    assert event["action_id"] == action_id
    assert event["evidence_ids"] == ["ev_ads_baseline"]
    assert event["details"]["measurement_plan_id"] == plan_id
    assert event["details"]["vendor_write_attempted"] is False
    assert event["details"]["success_claim_allowed"] is False

    observation = client.post(
        f"/api/actions/{action_id}/external-observation",
        json={
            "measurement_plan_id": plan_id,
            "acknowledgement_event_id": event["id"],
            "observation_status": "inconclusive",
            "observed_at": "2026-07-25T10:00:00Z",
            "evidence_ids": ["ev_refresh_refresh_google_ads_9cf9dfdb8f85"],
            "notes": "Okno obserwacji nie daje jeszcze jednoznacznego kierunku.",
        },
    )
    assert observation.status_code == 200, observation.text
    observation_event = observation.json()
    assert observation_event["event_type"] == "ads_external_observation_recorded"
    assert observation_event["details"]["acknowledgement_event_id"] == event["id"]
    assert observation_event["details"]["causal_claim_allowed"] is False

    mismatch = client.post(
        f"/api/actions/{action_id}/external-execution-acknowledgement",
        json={
            "measurement_plan_id": "ads_measurement_plan_stale",
            "execution_status": "executed",
            "acknowledged_by": "Wilku",
            "notes": "Nie powinno zostać zapisane.",
        },
    )
    assert mismatch.status_code == 409
