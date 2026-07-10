from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pytest

from tests._contract_support.ads_review_seed import (
    save_google_ads_recommendation_rows_for_context_pack,
    seed_google_ads_live_review_metric_facts,
)
from tests._contract_support.api_client import client
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.schemas import ActionObject


def test_ads_doctor_context_pack_uses_summary_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    captured_views: list[str] = []

    def recording_build_ads_diagnostics(
        actions: list[ActionObject] | None = None,
        *,
        view: Literal["full", "summary"] = "full",
    ) -> Any:
        captured_views.append(view)
        return build_ads_diagnostics(actions=actions, view=view)

    monkeypatch.setattr(
        "apps.api.wilq_api.context_skill.build_ads_diagnostics",
        recording_build_ads_diagnostics,
    )
    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )
    assert response.status_code == 200
    assert captured_views == ["summary"]


def test_ads_doctor_context_pack_preserves_recommendation_impact_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    save_google_ads_recommendation_rows_for_context_pack()

    ads_response = client.get("/api/ads/diagnostics")
    assert ads_response.status_code == 200
    ads_recommendations = ads_response.json()["recommendations_read_contract"]
    endpoint_impact_ids = [
        row["recommendation_id"]
        for row in ads_recommendations["recommendation_rows"]
        if row["impact_available"]
    ]

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )

    assert response.status_code == 200
    pack_recommendations = response.json()["ads_diagnostics"]["recommendations_read_contract"]
    pack_impact_ids = [
        row["recommendation_id"]
        for row in pack_recommendations["recommendation_rows"]
        if row["impact_available"]
    ]
    assert len(ads_recommendations["recommendation_rows"]) > 3
    assert endpoint_impact_ids == ["rec-a", "rec-d"]
    assert pack_impact_ids == endpoint_impact_ids
