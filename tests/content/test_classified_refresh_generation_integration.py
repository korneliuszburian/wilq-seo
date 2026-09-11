from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import wilq.content.workflow.decisions.production as production_module
import wilq.content.workflow.workspace.api as workflow_api
from apps.api.wilq_api.routers.content_initial_draft import register_content_initial_draft_route
from apps.api.wilq_api.routers.content_planning_proposals import (
    register_content_planning_proposal_routes,
)
from apps.api.wilq_api.routers.content_refresh_preparation import (
    register_content_refresh_preparation_routes,
)
from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from tests.content import dynamic_planning_test_support as planning_support
from tests.content.dynamic_planning_test_support import configure_planning_harness
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.planning import planning_generation_queue
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    classification_counts,
)
from wilq.content.workflow.documents.revision_children import build_child_draft_revision_command
from wilq.content.workflow.refresh_preparation import ContentRefreshPreparationAuthority
from wilq.content.workflow.store.refresh_preparation_atomic import RefreshPreparationAtomicityError
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.workspace.catalog import inventory_work_item_id
from wilq.storage.local_state import local_state_store

BDO_URL = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
BDO_WORK_ITEM_ID = inventory_work_item_id(BDO_URL)
BDO_SERVICE_CARD_ID = "ekologus_service_bdo_reporting"


def test_classified_refresh_generates_one_bound_plan_and_revision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    authority = _authority(store)
    client = _app_client(authority)

    authorization = _authorize(client)
    proposal = _generate_authorized_plan(client, authorization)
    initial = _generate_authorized_initial_draft(client, proposal, authorization)
    repeated = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_request(proposal, authorization),
    )
    status = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft")

    assert initial.status_code == repeated.status_code == status.status_code == 200
    assert (
        initial.json()["status"]
        == repeated.json()["status"]
        == status.json()["status"]
        == "created"
    )
    stored_proposal = content_planning_proposal_store().latest(BDO_WORK_ITEM_ID)
    revision = store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision
    assert stored_proposal is not None and revision is not None
    assert stored_proposal.refresh_preparation_binding is not None
    assert stored_proposal.refresh_preparation_binding == revision.refresh_preparation_binding
    assert revision.proposal_metadata is not None
    assert (
        revision.proposal_metadata.refresh_preparation_binding
        == revision.refresh_preparation_binding
    )
    assert runtime.calls == 2


def test_refresh_initial_draft_status_is_not_masked_as_generation_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    client = _app_client(_authority(store))

    status = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft")

    assert status.status_code == 200, status.text
    assert status.json()["status"] == "blocked"
    assert status.json()["blockers"][0]["code"] != "production_generation_disabled"
    assert runtime.calls == 0


def test_post_model_classification_drift_persists_no_authorized_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    run = _refresh_run()
    store.record_production_classification(run)
    authority = _authority(store)
    client = _app_client(authority)
    authorization = _authorize(client)
    original_turn = runtime.run_structured_turn

    def drift_after_model(request: Any) -> Any:
        result = original_turn(request)
        _replace_latest_classification(store, _drifted_run(run))
        return result

    monkeypatch.setattr(runtime, "run_structured_turn", drift_after_model)
    preview = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    ).json()
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": preview["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    terminal = _wait_for_plan(client, response)
    queued = content_planning_proposal_store().queued_response(
        BDO_WORK_ITEM_ID,
        BDO_SERVICE_CARD_ID,
        preview["planning_input_digest"],
    )

    assert terminal.status_code == 200
    assert terminal.json()["status"] == "blocked"
    assert terminal.json()["blockers"][0]["code"] == "refresh_preparation_authorization_stale"
    assert queued is not None
    assert queued.status == "blocked"
    assert queued.planning_input_digest == preview["planning_input_digest"]
    assert queued.input_summary is not None
    assert queued.input_summary.model_dump(mode="json") == response.json()["input_summary"]
    assert queued.refresh_preparation_binding is not None
    assert queued.refresh_preparation_binding.authorization_id == authorization["authorization_id"]
    assert _planning_job_status(tmp_path) == "blocked"
    assert _planning_claim_status(tmp_path) == "failed"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is None
    assert store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision is None
    assert runtime.calls == 1


def test_worker_pre_model_refresh_drift_persists_bound_blocked_job(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    run = _refresh_run()
    store.record_production_classification(run)
    authority = _authority(store)
    client = _app_client(authority)
    authorization = _authorize(client)
    preview = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    ).json()

    class HoldingExecutor:
        worker: Any | None = None
        arguments: tuple[Any, ...] = ()

        def submit(self, worker: Any, *arguments: Any, **_kwargs: Any) -> None:
            self.worker = worker
            self.arguments = arguments

    executor = HoldingExecutor()
    monkeypatch.setattr(planning_generation_queue, "_PLANNING_GENERATION_EXECUTOR", executor)
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": preview["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    queued_before_drift = content_planning_proposal_store().queued_response(
        BDO_WORK_ITEM_ID,
        BDO_SERVICE_CARD_ID,
        preview["planning_input_digest"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "generating"
    assert executor.worker is not None
    assert queued_before_drift is not None
    assert queued_before_drift.input_summary is not None
    _replace_latest_classification(store, _drifted_run(run))
    terminal = executor.worker(*executor.arguments)
    queued = content_planning_proposal_store().queued_response(
        BDO_WORK_ITEM_ID,
        BDO_SERVICE_CARD_ID,
        preview["planning_input_digest"],
    )
    status = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals")

    assert terminal.status == "blocked"
    assert terminal.blockers[0].code == "refresh_preparation_authorization_stale"
    assert terminal.planning_input_digest == preview["planning_input_digest"]
    assert terminal.input_summary == queued_before_drift.input_summary
    assert terminal.refresh_preparation_binding == queued_before_drift.refresh_preparation_binding
    assert queued == terminal
    assert _planning_job_status(tmp_path) == "blocked"
    assert _planning_claim_status(tmp_path) == "failed"
    assert status.status_code == 200
    assert status.json()["status"] == "blocked"
    assert status.json()["blockers"][0]["code"] == "refresh_preparation_authorization_stale"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is None
    assert store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision is None
    assert runtime.calls == 0


def test_post_model_draft_drift_persists_no_revision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    run = _refresh_run()
    store.record_production_classification(run)
    authority = _authority(store)
    client = _app_client(authority)
    authorization = _authorize(client)
    proposal = _generate_authorized_plan(client, authorization)
    original_turn = runtime.run_structured_turn

    def drift_after_draft_model(request: Any) -> Any:
        result = original_turn(request)
        if runtime.calls == 2:
            _replace_latest_classification(store, _drifted_run(run))
        return result

    monkeypatch.setattr(runtime, "run_structured_turn", drift_after_draft_model)
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_request(proposal, authorization),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["blockers"][0]["code"] == "refresh_preparation_authorization_stale"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is not None
    assert store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision is None
    assert runtime.calls == 2


def test_atomic_store_rejects_unbound_legacy_same_input_before_idempotence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, _runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    authority = _authority(store)
    client = _app_client(authority)
    authorization = _authorize(client)
    _generate_authorized_plan(client, authorization)
    proposal = content_planning_proposal_store().latest(BDO_WORK_ITEM_ID)
    assert proposal is not None and proposal.codex_run_id is not None
    completed_run = local_state_store().get_codex_run(proposal.codex_run_id)
    assert completed_run is not None

    with pytest.raises(RefreshPreparationAtomicityError):
        content_planning_proposal_store().save_generated(
            proposal.model_copy(update={"refresh_preparation_binding": None}),
            completed_run,
        )


def test_atomic_store_rejects_receipt_scalar_path_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, _runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    authority = _authority(store)
    client = _app_client(authority)
    authorization = _authorize(client)
    _generate_authorized_plan(client, authorization)
    proposal = content_planning_proposal_store().latest(BDO_WORK_ITEM_ID)
    assert proposal is not None and proposal.codex_run_id is not None
    completed_run = local_state_store().get_codex_run(proposal.codex_run_id)
    assert completed_run is not None
    with cast(Any, store)._connect() as connection:
        connection.execute(
            """
            UPDATE content_refresh_preparation_authorizations
            SET canonical_path = '/inny-adres'
            WHERE authorization_id = ?
            """,
            (proposal.refresh_preparation_binding.authorization_id,),
        )

    with pytest.raises(RefreshPreparationAtomicityError):
        content_planning_proposal_store().save_generated(proposal, completed_run)


def test_atomic_revision_append_rejects_unbound_refresh_child(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _unused, _runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = content_workflow_store()
    store.record_production_classification(_refresh_run())
    authority = _authority(store)
    client = _app_client(authority)
    authorization = _authorize(client)
    proposal = _generate_authorized_plan(client, authorization)
    _generate_authorized_initial_draft(client, proposal, authorization)
    revision = store.load_draft_revision_state(BDO_WORK_ITEM_ID).latest_revision
    assert revision is not None and revision.proposal_metadata is not None
    child = build_child_draft_revision_command(
        revision,
        sections=revision.sections,
        proposal_metadata=revision.proposal_metadata,
        created_by="wilku",
    )
    assert child.refresh_preparation_binding == revision.refresh_preparation_binding
    assert child.proposal_metadata is not None
    assert (
        child.proposal_metadata.refresh_preparation_binding
        == revision.refresh_preparation_binding
    )
    unbound_metadata = revision.proposal_metadata.model_copy(
        update={"refresh_preparation_binding": None}
    )
    unbound = child.model_copy(
        update={
            "refresh_preparation_binding": None,
            "proposal_metadata": unbound_metadata,
        }
    )

    with pytest.raises(RefreshPreparationAtomicityError):
        store.append_draft_revision(unbound)


def _authority(store: object) -> ContentRefreshPreparationAuthority:
    def service_snapshot(work_item_id: str, service_card_id: str | None):
        baseline = snapshot_for_work_item_or_404(work_item_id)
        return workflow_api.build_content_work_item_snapshot_response_from_selected_decision(
            planning_support._synthetic_planning_decision(BDO_URL),  # noqa: SLF001
            freshness_assessment=baseline.freshness_assessment,
            service_card_id_override=service_card_id,
        )

    return ContentRefreshPreparationAuthority(
        store=cast(Any, store),
        snapshot_loader=service_snapshot,
        proposal_store=content_planning_proposal_store(),
        content_kind_inventory_loader=lambda work_item_id: ContentKindInventoryBinding(
            work_item_id=work_item_id,
            canonical_path="/bdo-co-musi-wiedziec-przedsiebiorca",
            public_url=BDO_URL,
            wordpress_content_type="uslugi",
            content_kind="service",
            inventory_evidence_ids=("ev_connector_wordpress_ekologus_status",),
            trusted=True,
        ),
    )


def _app_client(authority: ContentRefreshPreparationAuthority) -> TestClient:
    app = FastAPI()
    router = APIRouter()
    register_content_refresh_preparation_routes(router, authority_factory=lambda: authority)
    register_content_planning_proposal_routes(
        router,
        snapshot_loader=lambda work_item_id: authority._snapshot_loader(  # noqa: SLF001
            work_item_id, None
        ),
        refresh_authority_factory=lambda: authority,
    )
    register_content_initial_draft_route(
        router,
        snapshot_loader=lambda work_item_id: authority._snapshot_loader(  # noqa: SLF001
            work_item_id, None
        ),
        refresh_authority_factory=lambda: authority,
    )
    app.include_router(router)
    return TestClient(app)


def _authorize(client: TestClient) -> dict[str, str]:
    ready = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    )
    assert ready.status_code == 200, ready.text
    body = cast(dict[str, Any], ready.json())
    assert body["status"] == "ready_to_authorize", body.get("blockers", body)
    classification = cast(dict[str, Any], body["classification"])
    authorized = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation/authorizations",
        json={
            "expected_production_classification_run_digest": classification[
                "classification_run_digest"
            ],
            "expected_production_classification_decision_set_digest": classification[
                "decision_set_digest"
            ],
            "expected_production_classification_source_packet_row_digest": classification[
                "source_packet_row_digest"
            ],
            "expected_planning_input_digest": body["planning_input_digest"],
            "service_card_id": BDO_SERVICE_CARD_ID,
            "authorized_by": "wilku",
            "acknowledged_classification_blocker_codes": classification[
                "classification_blocker_codes"
            ],
        },
    )
    assert authorized.status_code == 201, authorized.text
    return cast(dict[str, str], authorized.json()["authorization"])


def _generate_authorized_plan(
    client: TestClient,
    authorization: dict[str, str],
) -> dict[str, Any]:
    preview = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/refresh-preparation",
        params={"service_card_id": BDO_SERVICE_CARD_ID},
    ).json()
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json={
            "service_card_id": BDO_SERVICE_CARD_ID,
            "expected_planning_input_digest": preview["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    terminal = _wait_for_plan(client, response)
    assert terminal.status_code == 200, terminal.text
    body = cast(dict[str, Any], terminal.json())
    assert body["status"] in {"created", "idempotent", "ready"}, body
    return cast(dict[str, Any], body["proposal"])


def _generate_authorized_initial_draft(
    client: TestClient,
    proposal: dict[str, Any],
    authorization: dict[str, str],
) -> Any:
    response = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_request(proposal, authorization),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "created", response.json()
    return response


def _initial_request(proposal: dict[str, Any], authorization: dict[str, str]) -> dict[str, str]:
    return {
        "expected_proposal_id": proposal["proposal_id"],
        "expected_planning_digest": proposal["planning_digest"],
        "expected_planning_input_digest": proposal["planning_input_digest"],
        "requested_by": "wilku",
        "refresh_preparation_authorization_id": authorization["authorization_id"],
        "expected_refresh_preparation_authorization_digest": authorization[
            "authorization_digest"
        ],
    }


def _wait_for_plan(client: TestClient, response: Any) -> Any:
    for _ in range(100):
        if response.status_code != 200 or response.json().get("status") != "generating":
            return response
        time.sleep(0.02)
        response = client.get(f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals")
    return response


def _refresh_run():
    run = exact_public_bdo_run()
    payload = run.rows[0].model_dump(mode="python")
    payload.update(
        {
            "decision": "refresh",
            "retained_work_item_id": None,
            "revision_id": None,
            "revision_digest": None,
            "revision_approved": False,
            "revision_complete": False,
            "retained_binding": None,
            "verified_actions": (),
            "verified_drafts": (),
        }
    )
    row = ContentProductionClassificationRow.model_validate(payload)
    return production_module._build_run(
        input_receipt=run.input,
        counts=classification_counts((row, run.rows[1])),
        freshness=run.freshness,
        source_receipts=run.source_receipts,
        judge_receipt=run.judge_receipt,
        rows=(row, run.rows[1]),
        audit=run.audit,
    )


def _drifted_run(run: object):
    payload = cast(Any, run).rows[0].model_dump(mode="python")
    payload["source_packet_row_digest"] = "f" * 64
    row = ContentProductionClassificationRow.model_validate(payload)
    return production_module._build_run(
        input_receipt=cast(Any, run).input,
        counts=classification_counts((row, cast(Any, run).rows[1])),
        freshness=cast(Any, run).freshness,
        source_receipts=cast(Any, run).source_receipts,
        judge_receipt=cast(Any, run).judge_receipt,
        rows=(row, cast(Any, run).rows[1]),
        audit=cast(Any, run).audit,
    )


def _replace_latest_classification(store: object, run: object) -> None:
    with cast(Any, store)._connect() as connection:
        connection.execute("DELETE FROM content_production_classifications")
    cast(Any, store).record_production_classification(run)


def _planning_job_status(tmp_path: Path) -> str | None:
    with sqlite3.connect(tmp_path / "wilq.sqlite3") as connection:
        row = connection.execute(
            "SELECT status FROM content_planning_generation_jobs ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    return None if row is None else cast(str, row[0])


def _planning_claim_status(tmp_path: Path) -> str | None:
    with sqlite3.connect(tmp_path / "wilq.sqlite3") as connection:
        row = connection.execute(
            "SELECT status FROM content_planning_generation_claims ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    return None if row is None else cast(str, row[0])
