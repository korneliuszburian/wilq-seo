from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import wilq.content.workflow.decisions.inventory_binding as inventory_binding
from tests.content.dynamic_planning_test_support import (
    PlanningClient,
    configure_planning_harness,
)
from wilq.content.planning import planning_generation_queue
from wilq.content.workflow.workspace.catalog import inventory_work_item_id

BDO_WORK_ITEM_ID = inventory_work_item_id(
    "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
)


@pytest.fixture
def planning_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, PlanningClient]:
    return configure_planning_harness(monkeypatch, tmp_path)


def test_selected_workspace_does_not_shadow_cold_live_planning(
    planning_harness: tuple[TestClient, PlanningClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _runtime = planning_harness
    live_material_reads: list[str] = []
    live_material = inventory_binding.read_content_inventory_material

    def record_live_material(url: str, **kwargs: Any) -> Any:
        live_material_reads.append(url)
        return live_material(url, **kwargs)

    monkeypatch.setattr(
        inventory_binding,
        "read_content_inventory_material",
        record_live_material,
    )

    selected = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/selected-workspace"
    )

    assert selected.status_code == 200
    selected_source = selected.json()["workspace"]["source_snapshot"]
    assert selected_source["status_label"].startswith("materiał zapisany")
    assert "zapisan" in selected_source["reason"]
    assert any("Aktualność materiału" in caveat for caveat in selected_source["caveats"])
    assert live_material_reads == []

    planning = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    )

    assert planning.status_code == 200
    planning_payload = planning.json()
    planning_input_digest = planning_payload["planning_input_digest"]
    assert planning_input_digest is not None
    assert any("bdo-co-musi-wiedziec-przedsiebiorca" in url for url in live_material_reads)

    class HoldingExecutor:
        def submit(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    monkeypatch.setattr(
        planning_generation_queue,
        "_PLANNING_GENERATION_EXECUTOR",
        HoldingExecutor(),
    )
    posted = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": planning_payload["service_card_id"],
            "expected_planning_input_digest": planning_input_digest,
            "operator_hint": "Odpowiedz najpierw na najważniejsze pytanie czytelnika.",
            "requested_by": "wilku",
        },
    )

    assert posted.status_code == 200
    assert posted.json()["status"] == "generating"
    assert posted.json()["planning_input_digest"] == planning_input_digest
