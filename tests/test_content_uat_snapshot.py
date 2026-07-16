from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

UAT_PACKET_PATH = Path(
    ".agents/skills/wilq-content-operator/scripts/build_uat_packet.py"
)


def _load_uat_packet() -> ModuleType:
    spec = importlib.util.spec_from_file_location("content_uat_packet", UAT_PACKET_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_packet_item_uses_exact_snapshot_candidate_and_demand(
    monkeypatch: Any,
) -> None:
    uat_packet = _load_uat_packet()

    def fake_request_json(
        api_base: str,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        timeout: int = 180,
    ) -> dict[str, Any]:
        assert api_base == "http://example.test"
        assert method == "GET"
        assert body is None
        assert timeout == 180
        if path.endswith("/enrichment"):
            return {"enrichment": {"status": "ready"}, "blockers": []}
        if path.endswith("/snapshot"):
            return {
                "candidate": {
                    "work_item_id": "content_work_item_home",
                    "title": "Strona główna (29 zapytań)",
                    "recommended_mode": "refresh",
                    "recommended_mode_label": "odśwież istniejącą treść",
                    "status_label": "gotowe do planu",
                    "safe_next_step": "Sprawdź dokładne zapytania.",
                    "evidence_ids": ["ev_gsc_exact"],
                    "source_connectors": ["google_search_console"],
                    "final_canonical_url": "https://www.ekologus.pl/",
                    "blockers": [],
                },
                "planning_workspace": {
                    "proposal": {
                        "search_demand": {
                            "status": "available",
                            "gsc_query_rows": [
                                {"impressions": 19, "clicks": 3},
                                *[
                                    {"impressions": 1, "clicks": 0}
                                    for _ in range(28)
                                ],
                            ],
                            "safe_next_step": "Sprawdź dokładne zapytania.",
                        }
                    }
                },
            }
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(uat_packet, "request_json", fake_request_json)
    item = uat_packet.packet_item(
        "http://example.test",
        {
            "work_item_id": "content_work_item_home",
            "title": "Strona główna (31 zapytań)",
            "recommended_mode": "refresh",
            "evidence_ids": ["ev_compact_queue"],
            "source_connectors": ["google_search_console"],
            "blockers": [],
        },
    )

    assert item["title"] == "Strona główna (29 zapytań)"
    assert item["evidence_ids"] == ["ev_gsc_exact"]
    assert item["search_demand"] == {
        "status": "available",
        "gsc_query_count": 29,
        "gsc_impressions": 47,
        "gsc_clicks": 3,
        "safe_next_step": "Sprawdź dokładne zapytania.",
    }
    assert uat_packet.search_demand_from_snapshot({}) == {
        "status": "missing",
        "gsc_query_count": None,
    }
    assert uat_packet.matched_snapshot_for_work_item(
        {"candidate": {"work_item_id": "content_work_item_other"}},
        "content_work_item_home",
    ) == {}
