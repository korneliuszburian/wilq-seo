from __future__ import annotations

from pathlib import Path

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client


def test_action_recommended_reasons_do_not_expose_route_slugs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/actions")

    assert response.status_code == 200
    actions = response.json()
    visible_copy = "\n".join(str(action.get("recommended_reason") or "") for action in actions)
    for route_slug in (
        "/merchant",
        "/content-workflow",
        "/ads-doctor",
        "/ga4",
        "/ads-doctor/demand-gen",
        "/localo",
        "/social-publisher",
    ):
        assert route_slug not in visible_copy
    for stale_term in ("evidence", "source connector", "blocked claims"):
        assert stale_term not in visible_copy
    assert "W widoku Merchant" in visible_copy
    assert "W widoku Treści" in visible_copy
    assert "W widoku GA4" in visible_copy
