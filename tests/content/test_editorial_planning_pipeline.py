import json
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

import wilq.content.workflow.decisions.inventory_binding as inventory_binding
from tests.content.dynamic_planning_test_support import PlanningClient, configure_planning_harness
from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.workflow.workspace.catalog import inventory_work_item_id

ARTICLE_URL = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
WORK_ITEM_ID = inventory_work_item_id(ARTICLE_URL)


class EditorialPlanningClient(PlanningClient):
    def run_structured_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
    ) -> CodexAppServerTurnResult:
        context = json.loads(request.untrusted_context)
        planning_input = context.get("planning_input")
        if isinstance(planning_input, dict) and planning_input.get("content_kind") == "editorial":
            planning_input.setdefault("confirmed_service_card_id", None)
            planning_input.setdefault("service_label", None)
            request = replace(
                request,
                untrusted_context=json.dumps(context, ensure_ascii=False),
            )
        result = super().run_structured_turn(request)
        if result.output_text is None:
            return result
        output = json.loads(result.output_text)
        output["content_kind"] = "editorial"
        output["service_card_id"] = None
        return replace(result, output_text=json.dumps(output, ensure_ascii=False))


def _editorial_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> tuple[TestClient, EditorialPlanningClient]:
    client, _service_runtime = configure_planning_harness(monkeypatch, tmp_path)
    runtime = EditorialPlanningClient()
    monkeypatch.setattr(
        "apps.api.wilq_api.routers.content_codex_runtime.content_codex_app_server_client",
        lambda: runtime,
    )
    catalog = inventory_binding.build_content_inventory_catalog()
    monkeypatch.setattr(
        inventory_binding,
        "build_content_inventory_catalog",
        lambda: catalog.model_copy(
            update={
                "items": [
                    item.model_copy(update={"content_type": "post"})
                    if item.work_item_id == WORK_ITEM_ID
                    else item
                    for item in catalog.items
                ]
            }
        ),
    )
    return client, runtime


def test_editorial_request_generates_persists_and_reads_without_service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    client, runtime = _editorial_harness(monkeypatch, tmp_path)

    before = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals")
    assert before.status_code == 200
    assert before.json()["content_kind"] == "editorial"
    assert before.json()["service_card_id"] is None

    stale = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": "editorial",
            "service_card_id": None,
            "expected_planning_input_digest": "0" * 64,
            "requested_by": "wilku",
        },
    )
    assert stale.status_code == 409
    assert stale.json()["status"] == "stale"
    assert stale.json()["content_kind"] == "editorial"

    response = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": "editorial",
            "service_card_id": None,
            "expected_planning_input_digest": before.json()["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    for _ in range(200):
        if response.json().get("status") != "generating":
            break
        time.sleep(0.05)
        response = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals")

    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "idempotent"}, response.json().get(
        "blockers"
    )
    assert response.json()["content_kind"] == "editorial"
    assert response.json()["proposal"]["content_kind"] == "editorial"
    assert response.json()["proposal"]["service_card_id"] is None
    assert runtime.calls == 1

    repeated = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": "editorial",
            "service_card_id": None,
            "expected_planning_input_digest": before.json()["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["content_kind"] == "editorial"
    assert runtime.calls == 1


def test_editorial_terminal_failure_preserves_content_kind(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    client, runtime = _editorial_harness(monkeypatch, tmp_path)
    runtime.fail = True
    before = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals")

    response = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals",
        json={
            "content_kind": "editorial",
            "service_card_id": None,
            "expected_planning_input_digest": before.json()["planning_input_digest"],
            "requested_by": "wilku",
        },
    )
    for _ in range(200):
        if response.json().get("status") != "generating":
            break
        time.sleep(0.05)
        response = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/planning-proposals")

    assert response.json()["status"] == "failed"
    assert response.json()["content_kind"] == "editorial"
    assert response.json()["service_card_id"] is None
