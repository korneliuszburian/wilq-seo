from __future__ import annotations

import asyncio
import base64
import copy
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import get_ident
from typing import cast

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from apps.api.wilq_api.routers import content_production_classification as classification_api
from apps.api.wilq_api.routers.content_workflow import router as content_workflow_router
from tests.content.production_classification_synthetic import (
    ACTION_ID,
    SyntheticInputs,
    build_inputs,
    resign,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRecordResult,
    ContentProductionClassificationRun,
    ContentProductionClassificationValidationError,
    parse_content_production_classification,
)
from wilq.content.workflow.store.store import ContentWorkflowStore

AUDIT_TIME = datetime(2026, 8, 30, 10, 5, tzinfo=UTC)


def _parse(inputs: SyntheticInputs) -> ContentProductionClassificationRun:
    return parse_content_production_classification(
        packet_bytes=inputs.packet_bytes,
        judge_bytes=inputs.judge_bytes,
        acceptance_policy=inputs.policy,
        recorded_by="codex_w1_test",
        reviewed_by="independent_test_judge",
        recorded_at=AUDIT_TIME,
    )


def _expect_rejection(inputs: SyntheticInputs, code: str) -> None:
    with pytest.raises(ContentProductionClassificationValidationError) as error:
        _parse(inputs)
    assert error.value.code == code
    assert str(error.value) == f"Production classification rejected: {code}."


def _set_nested_json_value(
    value: object,
    path: tuple[str | int, ...],
    replacement: object,
) -> None:
    target = value
    for component in path[:-1]:
        if isinstance(component, int):
            target = cast(list[object], target)[component]
        else:
            target = cast(dict[str, object], target)[component]
    final = path[-1]
    if isinstance(final, int):
        cast(list[object], target)[final] = replacement
    else:
        cast(dict[str, object], target)[final] = replacement


def _classification_app() -> FastAPI:
    app = FastAPI()
    app.include_router(content_workflow_router)
    return app


def _asgi_request(app: FastAPI, *, body: object) -> httpx.Response:
    async def exercise() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await asyncio.wait_for(
                client.post("/api/content/production-classifications", json=body),
                timeout=5,
            )

    return asyncio.run(exercise())


@pytest.mark.parametrize(
    ("path", "unsafe_value"),
    [
        (("rows", 0, "rationale_pl"), "/workspace/private-rationale.txt"),
        (
            (
                "rows",
                0,
                "draft_and_action_state",
                "verified_current_action_bindings",
                0,
                "mutation_audit_id",
            ),
            "password: signed-audit-value",
        ),
        (
            (
                "rows",
                0,
                "source_packet_receipts",
                "classification_artifact_reference",
            ),
            "$HOME/private-artifact.json",
        ),
        (
            ("rows", 0, "rationale_pl"),
            "https://writer:secret@example.test/public",  # pragma: allowlist secret
        ),
    ],
    ids=["rationale", "audit", "artifact", "credential-uri"],
)
def test_typed_persisted_fields_reject_unsafe_material(
    path: tuple[str | int, ...],
    unsafe_value: str,
) -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    _set_nested_json_value(packet, path, unsafe_value)

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "unsafe_signed_material",
    )


def test_coherently_resigned_fork_action_cannot_bind_to_unrelated_work_item() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[0])
    state = cast(dict[str, object], row["draft_and_action_state"])
    action = cast(
        dict[str, object], cast(list[object], state["verified_current_action_bindings"])[0]
    )
    action["bound_work_item_id"] = "unrelated_work_item"

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "typed_classification_invalid",
    )


def test_retained_missing_allows_one_signed_historical_action_owner() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[0])
    identity = cast(dict[str, object], row["work_item_identity"])
    binding = cast(dict[str, object], row["retained_revision_binding"])
    state = cast(dict[str, object], row["draft_and_action_state"])
    action = cast(
        dict[str, object], cast(list[object], state["verified_current_action_bindings"])[0]
    )
    identity["retained_work_item_id"] = None
    binding["retained_work_item_id"] = None
    binding["identity_reconciliation_status"] = "retained_missing"
    action["bound_work_item_id"] = "signed_historical_work_item"
    policy = baseline.policy.model_copy(
        update={
            "protected_binding": baseline.policy.protected_binding.model_copy(
                update={
                    "retained_work_item_id": None,
                    "identity_status": "retained_missing",
                }
            )
        }
    )

    run = _parse(resign(packet, policy=policy, sync_policy_decision=True))

    assert run.rows[0].retained_work_item_id is None
    assert run.rows[0].retained_binding is not None
    assert run.rows[0].retained_binding.identity_reconciliation_status == "retained_missing"
    assert {item.bound_work_item_id for item in run.rows[0].verified_actions} == {
        "signed_historical_work_item"
    }
    assert run.for_work_item("signed_historical_work_item") == run.rows[0]


def test_action_owner_cannot_collide_with_another_rows_current_work_item() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[0])
    identity = cast(dict[str, object], row["work_item_identity"])
    binding = cast(dict[str, object], row["retained_revision_binding"])
    state = cast(dict[str, object], row["draft_and_action_state"])
    action = cast(
        dict[str, object], cast(list[object], state["verified_current_action_bindings"])[0]
    )
    identity["retained_work_item_id"] = None
    binding["retained_work_item_id"] = None
    binding["identity_reconciliation_status"] = "retained_missing"
    action["bound_work_item_id"] = "work_current_2"
    policy = baseline.policy.model_copy(
        update={
            "protected_binding": baseline.policy.protected_binding.model_copy(
                update={
                    "retained_work_item_id": None,
                    "identity_status": "retained_missing",
                }
            )
        }
    )

    _expect_rejection(
        resign(packet, policy=policy, sync_policy_decision=True),
        "typed_classification_invalid",
    )


def test_retained_missing_rejects_disagreeing_historical_action_owners() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[0])
    identity = cast(dict[str, object], row["work_item_identity"])
    binding = cast(dict[str, object], row["retained_revision_binding"])
    state = cast(dict[str, object], row["draft_and_action_state"])
    actions = cast(list[object], state["verified_current_action_bindings"])
    drafts = cast(list[object], state["verified_current_draft_bindings"])
    first_action = cast(dict[str, object], actions[0])
    first_draft = cast(dict[str, object], drafts[0])
    first_action["bound_work_item_id"] = "signed_historical_work_item"
    second_action = copy.deepcopy(first_action)
    second_action.update(
        {
            "action_id": "act_content_dev_draft_second",
            "mutation_audit_id": "audit_second",
            "bound_work_item_id": "different_historical_work_item",
        }
    )
    second_draft = copy.deepcopy(first_draft)
    second_draft.update(
        {
            "action_id": "act_content_dev_draft_second",
            "apply_audit_id": "audit_second",
            "post_id": "1992",
        }
    )
    actions.append(second_action)
    drafts.append(second_draft)
    identity["retained_work_item_id"] = None
    binding["retained_work_item_id"] = None
    binding["identity_reconciliation_status"] = "retained_missing"
    binding["verified_draft_action_ids"] = [ACTION_ID, "act_content_dev_draft_second"]
    binding["verified_draft_post_ids"] = ["1991", "1992"]
    counts = cast(dict[str, object], packet["counts"])
    counts["verified_current_actions"] = 2
    counts["verified_current_drafts"] = 2
    policy = baseline.policy.model_copy(
        update={
            "expected_counts": baseline.policy.expected_counts.model_copy(
                update={"verified_current_actions": 2, "verified_current_drafts": 2}
            ),
            "protected_binding": baseline.policy.protected_binding.model_copy(
                update={
                    "retained_work_item_id": None,
                    "identity_status": "retained_missing",
                    "action_ids": (ACTION_ID, "act_content_dev_draft_second"),
                    "draft_post_ids": ("1991", "1992"),
                }
            ),
        }
    )

    _expect_rejection(
        resign(packet, policy=policy, sync_policy_decision=True),
        "typed_classification_invalid",
    )


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("counts", "rows"), "2"),
        (("freshness", "requires_refresh"), "false"),
        (("rows", 0, "revision_approved"), "true"),
    ],
    ids=["count", "freshness", "revision-approved"],
)
def test_store_strictly_rejects_coercible_persisted_scalar_tampering(
    tmp_path: Path,
    path: tuple[str | int, ...],
    replacement: str,
) -> None:
    store = ContentWorkflowStore(tmp_path / "strict-read.sqlite3")
    assert store.record_production_classification(_parse(build_inputs())).status == "created"
    with sqlite3.connect(store.path) as connection:
        payload = cast(
            str,
            connection.execute(
                "SELECT payload_json FROM content_production_classifications"
            ).fetchone()[0],
        )
        tampered_payload = json.loads(payload)
        _set_nested_json_value(tampered_payload, path, replacement)
        connection.execute(
            "UPDATE content_production_classifications SET payload_json = ?",
            (json.dumps(tampered_payload),),
        )

    with pytest.raises(ValidationError):
        store.load_latest_production_classification()


def test_store_strictly_rejects_coercible_aggregate_on_ingress(tmp_path: Path) -> None:
    run = _parse(build_inputs())
    unsafe_counts = run.counts.model_copy(update={"rows": "2"})
    unsafe_run = run.model_copy(update={"counts": unsafe_counts})
    store = ContentWorkflowStore(tmp_path / "strict-ingress.sqlite3")

    with (
        pytest.warns(UserWarning, match="Pydantic serializer warnings"),
        pytest.raises(ValidationError),
    ):
        store.record_production_classification(unsafe_run)

    assert not store.path.exists()


@pytest.mark.parametrize(
    "case",
    [
        "policy-selector-wrong-type",
        "packet-base64-wrong-type",
        "judge-base64-wrong-type",
        "recorded-by-wrong-type",
        "reviewed-by-wrong-type",
        "recorded-at-wrong-type",
        "policy-selector-invalid",
        "extra-field",
        "recorded-by-overlong",
        "reviewed-by-overlong",
        "recorded-at-invalid",
    ],
)
def test_classification_request_validation_is_code_only_and_never_echoes_input(
    case: str,
) -> None:
    inputs = build_inputs()
    packet_text = inputs.packet_bytes.decode()
    judge_text = inputs.judge_bytes.decode()
    packet_base64 = base64.b64encode(inputs.packet_bytes).decode()
    judge_base64 = base64.b64encode(inputs.judge_bytes).decode()
    sentinel = f"HOSTILE_NO_ECHO_{case}"
    payload: dict[str, object] = {
        "policy_selector": "wave0-production-classification-v1",
        "packet_base64": packet_base64,
        "judge_base64": judge_base64,
        "recorded_by": "codex_w1_test",
        "reviewed_by": "independent_test_judge",
        "recorded_at": AUDIT_TIME.isoformat(),
    }
    mutations: dict[str, tuple[str, object]] = {
        "policy-selector-wrong-type": ("policy_selector", {"sentinel": sentinel}),
        "packet-base64-wrong-type": (
            "packet_base64",
            {"sentinel": sentinel, "raw_packet": packet_text},
        ),
        "judge-base64-wrong-type": (
            "judge_base64",
            [sentinel, judge_text],
        ),
        "recorded-by-wrong-type": ("recorded_by", {"sentinel": sentinel}),
        "reviewed-by-wrong-type": ("reviewed_by", [sentinel]),
        "recorded-at-wrong-type": ("recorded_at", {"sentinel": sentinel}),
        "policy-selector-invalid": ("policy_selector", sentinel),
        "recorded-by-overlong": ("recorded_by", sentinel + "x" * 160),
        "reviewed-by-overlong": ("reviewed_by", sentinel + "x" * 160),
        "recorded-at-invalid": ("recorded_at", f"not-a-time-{sentinel}"),
    }
    if case == "extra-field":
        payload["unexpected_field"] = {"sentinel": sentinel}
    else:
        field, replacement = mutations[case]
        payload[field] = replacement

    response = _asgi_request(_classification_app(), body=payload)

    assert response.status_code == 422
    assert response.json() == {"detail": "production_classification_request_invalid"}
    for forbidden in (sentinel, packet_text, judge_text, packet_base64, judge_base64):
        assert forbidden not in response.text


@pytest.mark.parametrize(
    ("changed_receipt", "expected_detail"),
    [
        ("packet", "packet_receipt_mismatch"),
        ("judge", "judge_receipt_mismatch"),
    ],
)
def test_classification_api_returns_only_the_wrong_receipt_code(
    monkeypatch: pytest.MonkeyPatch,
    changed_receipt: str,
    expected_detail: str,
) -> None:
    inputs = build_inputs()
    monkeypatch.setattr(classification_api, "WAVE0_PRODUCTION_ACCEPTANCE_POLICY", inputs.policy)
    packet_bytes = inputs.packet_bytes + (b" " if changed_receipt == "packet" else b"")
    judge_bytes = inputs.judge_bytes + (b" " if changed_receipt == "judge" else b"")
    packet_base64 = base64.b64encode(packet_bytes).decode()
    judge_base64 = base64.b64encode(judge_bytes).decode()

    response = _asgi_request(
        _classification_app(),
        body={
            "policy_selector": "wave0-production-classification-v1",
            "packet_base64": packet_base64,
            "judge_base64": judge_base64,
            "recorded_by": "codex_w1_test",
            "reviewed_by": "independent_test_judge",
            "recorded_at": AUDIT_TIME.isoformat(),
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": expected_detail}
    for forbidden in (
        packet_bytes.decode(),
        judge_bytes.decode(),
        packet_base64,
        judge_base64,
    ):
        assert forbidden not in response.text


@pytest.mark.parametrize(
    ("field", "unsafe_identity"),
    [
        ("recorded_by", "token=HOSTILE_RECORDED_IDENTITY"),
        ("reviewed_by", "/workspace/HOSTILE_REVIEWED_IDENTITY"),
    ],
)
def test_classification_api_rejects_unsafe_identity_without_echo(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    unsafe_identity: str,
) -> None:
    inputs = build_inputs()
    monkeypatch.setattr(classification_api, "WAVE0_PRODUCTION_ACCEPTANCE_POLICY", inputs.policy)
    payload = {
        "policy_selector": "wave0-production-classification-v1",
        "packet_base64": base64.b64encode(inputs.packet_bytes).decode(),
        "judge_base64": base64.b64encode(inputs.judge_bytes).decode(),
        "recorded_by": "codex_w1_test",
        "reviewed_by": "independent_test_judge",
        "recorded_at": AUDIT_TIME.isoformat(),
    }
    payload[field] = unsafe_identity

    response = _asgi_request(_classification_app(), body=payload)

    assert response.status_code == 422
    assert response.json() == {"detail": "unsafe_signed_material"}
    assert unsafe_identity not in response.text
    assert inputs.packet_bytes.decode() not in response.text
    assert inputs.judge_bytes.decode() not in response.text
    assert payload["packet_base64"] not in response.text
    assert payload["judge_base64"] not in response.text


def test_classification_asgi_offloads_parser_hash_and_sqlite_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = build_inputs()
    store = ContentWorkflowStore(tmp_path / "offloaded.sqlite3")
    caller_thread = get_ident()
    worker_threads: dict[str, int] = {}
    original_parse = classification_api.parse_content_production_classification
    original_record = store.record_production_classification

    def parse_on_worker(**kwargs: object) -> ContentProductionClassificationRun:
        worker_threads["parse"] = get_ident()
        return original_parse(**kwargs)  # type: ignore[arg-type]

    def record_on_worker(
        run: ContentProductionClassificationRun,
    ) -> ContentProductionClassificationRecordResult:
        worker_threads["sqlite"] = get_ident()
        return original_record(run)

    monkeypatch.setattr(classification_api, "WAVE0_PRODUCTION_ACCEPTANCE_POLICY", inputs.policy)
    monkeypatch.setattr(
        classification_api,
        "parse_content_production_classification",
        parse_on_worker,
    )
    monkeypatch.setattr(classification_api, "content_workflow_store", lambda: store)
    monkeypatch.setattr(store, "record_production_classification", record_on_worker)
    response = _asgi_request(
        _classification_app(),
        body={
            "policy_selector": "wave0-production-classification-v1",
            "packet_base64": base64.b64encode(inputs.packet_bytes).decode(),
            "judge_base64": base64.b64encode(inputs.judge_bytes).decode(),
            "recorded_by": "codex_w1_test",
            "reviewed_by": "independent_test_judge",
            "recorded_at": AUDIT_TIME.isoformat(),
        },
    )

    assert response.status_code == 201
    assert set(worker_threads) == {"parse", "sqlite"}
    assert all(thread_id != caller_thread for thread_id in worker_threads.values())
