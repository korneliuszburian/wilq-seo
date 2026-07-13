from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client


def _payload_has_operator_preview_data(payload: dict[str, Any]) -> bool:
    preview_keys = (
        "payload_preview",
        "content_brief_preview",
        "wordpress_draft_payload_preview",
        "budget_payload_preview",
        "custom_segment_payload_preview",
        "negative_keyword_payload_preview",
        "change_history_preview",
        "ngram_preview",
        "source_inputs",
    )
    return any(
        isinstance(payload.get(key), (list, dict)) and bool(payload.get(key))
        for key in preview_keys
    )


def test_actions_with_operator_preview_data_expose_typed_preview_cards(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/actions")
    assert response.status_code == 200

    actions_with_preview_data = [
        action
        for action in response.json()
        if _payload_has_operator_preview_data(action.get("payload") or {})
    ]

    assert actions_with_preview_data
    assert all(action["preview_cards"] for action in actions_with_preview_data)
