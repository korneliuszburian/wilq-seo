from __future__ import annotations

import asyncio
import base64
import copy
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from apps.api.wilq_api.routers import content_production_classification as classification_api
from apps.api.wilq_api.routers.content_workflow import router as content_workflow_router
from tests.content.production_classification_synthetic import (
    PATHS,
    SyntheticInputs,
    build_inputs,
    resign,
    resign_judge,
    resign_raw,
)
from wilq.content.workflow.decisions.production import (
    WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
    ContentProductionClassificationRun,
    ContentProductionClassificationValidationError,
    canonical_json_digest,
    parse_content_production_classification,
)
from wilq.content.workflow.store.store import ContentWorkflowStore

AUDIT_TIME = datetime(2026, 8, 30, 10, 5, tzinfo=UTC)


def _parse(
    inputs: SyntheticInputs,
    *,
    recorded_at: datetime = AUDIT_TIME,
    recorded_by: str = "codex_w1_test",
    reviewed_by: str = "independent_test_judge",
) -> ContentProductionClassificationRun:
    return parse_content_production_classification(
        packet_bytes=inputs.packet_bytes,
        judge_bytes=inputs.judge_bytes,
        acceptance_policy=inputs.policy,
        recorded_by=recorded_by,
        reviewed_by=reviewed_by,
        recorded_at=recorded_at,
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


def _different_coherent_result(
    run: ContentProductionClassificationRun,
) -> ContentProductionClassificationRun:
    changed_row = run.rows[-1].model_copy(
        update={"rationale_pl": "Inny, lecz wewnętrznie spójny wynik klasyfikacji."}
    )
    provisional = run.model_copy(
        update={
            "rows": (*run.rows[:-1], changed_row),
            "run_digest": "0" * 64,
        }
    )
    run_digest = canonical_json_digest(
        provisional.model_dump(mode="json", exclude={"audit", "run_digest"})
    )
    return ContentProductionClassificationRun.model_validate(
        provisional.model_copy(update={"run_digest": run_digest})
    )


def _assert_signed_material_not_retained(
    store: ContentWorkflowStore,
    packet_bytes: bytes,
    judge_bytes: bytes,
) -> None:
    raw_materials = (packet_bytes, judge_bytes)
    encoded_materials = tuple(base64.b64encode(value) for value in raw_materials)
    with sqlite3.connect(store.path) as connection:
        persisted_rows = connection.execute(
            "SELECT * FROM content_production_classifications"
        ).fetchall()
    persisted_text = "\n".join(
        str(value) for row in persisted_rows for value in row if isinstance(value, str)
    )
    persisted_bytes = store.path.read_bytes()
    for raw, encoded in zip(raw_materials, encoded_materials, strict=True):
        assert raw.decode("utf-8") not in persisted_text
        assert encoded.decode("ascii") not in persisted_text
        assert raw not in persisted_bytes
        assert encoded not in persisted_bytes


def _classification_app() -> FastAPI:
    app = FastAPI()
    app.include_router(content_workflow_router)
    return app


def _asgi_request(
    app: FastAPI,
    method: str,
    path: str,
    *,
    body: object | None = None,
) -> httpx.Response:
    async def exercise() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await asyncio.wait_for(
                client.request(method, path, json=body),
                timeout=5,
            )

    return asyncio.run(exercise())


def _assert_classification_roundtrip(
    responses: tuple[httpx.Response, ...],
    inputs: SyntheticInputs,
    payload: dict[str, str],
) -> None:
    before, created, repeated, latest, projected, missing, conflicting = responses
    before_body = before.json()
    created_body = created.json()
    repeated_body = repeated.json()
    latest_body = latest.json()
    projected_body = projected.json()
    missing_body = missing.json()
    conflicting_body = conflicting.json()

    assert before.status_code == 200 and before_body == {"status": "missing", "run": None}
    assert created.status_code == 201 and created_body["status"] == "created"
    assert repeated.status_code == 200 and repeated_body["status"] == "idempotent"
    assert repeated_body["run"]["audit"] == created_body["run"]["audit"]
    assert repeated_body["run"]["run_digest"] == created_body["run"]["run_digest"]
    assert latest.status_code == 200 and latest_body["status"] == "available"
    assert latest_body["run"] == created_body["run"]
    assert projected.status_code == 200 and projected_body["status"] == "available"
    assert projected_body["projection"]["row"]["canonical_path"] == PATHS[0]
    assert missing.status_code == 200
    assert missing_body == {"status": "missing", "projection": None}
    assert conflicting.status_code == 409 and conflicting_body["status"] == "conflict"
    assert conflicting_body["run"] == created_body["run"]
    assert isinstance(created_body["run"]["audit"]["recorded_at"], str)

    serialized_responses = json.dumps(
        [response.json() for response in responses],
        ensure_ascii=False,
        sort_keys=True,
    )
    for forbidden in (
        inputs.packet_bytes.decode("utf-8"),
        inputs.judge_bytes.decode("utf-8"),
        payload["packet_base64"],
        payload["judge_base64"],
    ):
        assert forbidden not in serialized_responses


def test_parser_builds_one_immutable_unicode_aggregate_through_public_seam() -> None:
    inputs = build_inputs()
    run = _parse(inputs)

    assert run.input.packet_sha256 == canonical_json_digest(inputs.packet)
    assert run.input.decision_set_digest == canonical_json_digest(inputs.packet["rows"])
    assert run.counts.model_dump() == {
        "rows": 2,
        "reuse": 1,
        "refresh": 0,
        "write": 0,
        "blocked": 1,
        "generation_allowed": 0,
        "verified_current_actions": 1,
        "verified_current_drafts": 1,
    }
    assert run.rows[0].rationale_pl == "Zażółć gęślą 1."
    assert run.for_work_item("work_current_1") == run.rows[0]
    assert run.for_work_item("work_retained") == run.rows[0]
    with pytest.raises(ValidationError):
        run.audit.recorded_by = "mutated"  # type: ignore[misc]


def test_semantically_equal_whitespace_still_changes_exact_input_receipts() -> None:
    baseline = build_inputs()
    packet_changed = SyntheticInputs(
        baseline.packet,
        baseline.judge,
        baseline.packet_bytes + b" ",
        baseline.judge_bytes,
        baseline.policy,
    )
    judge_changed = SyntheticInputs(
        baseline.packet,
        baseline.judge,
        baseline.packet_bytes,
        baseline.judge_bytes + b" ",
        baseline.policy,
    )
    _expect_rejection(packet_changed, "packet_receipt_mismatch")
    _expect_rejection(judge_changed, "judge_receipt_mismatch")


@pytest.mark.parametrize(
    "packet_bytes",
    [
        b"\xff",
        b'{"duplicate":1,"duplicate":2}',
        b'{"not_finite":NaN}',
        b'{"not_finite":Infinity}',
        b'{"overflow":1e400}',
        b'{"negative_overflow":-1e400}',
    ],
    ids=[
        "invalid-utf8",
        "duplicate-key",
        "nan",
        "infinity",
        "positive-overflow",
        "negative-overflow",
    ],
)
def test_strict_json_boundary_rejects_malformed_signed_bytes(packet_bytes: bytes) -> None:
    _expect_rejection(resign_raw(build_inputs(), packet_bytes), "invalid_json")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("artifact", "/tmp/signed.json"),
        ("artifact", "/var/tmp/signed.json"),
        ("artifact", "/home/operator/signed.json"),
        ("artifact", "/mnt/storage/worktrees/signed.json"),
        ("artifact", "/root/.ssh/id_ed25519"),
        ("artifact", "/etc/passwd"),
        ("artifact", "/proc/self/environ"),
        ("artifact", "/run/secrets/service"),
        ("artifact", "/var/lib/private/state.json"),
        ("artifact", "/Users/operator/signed.json"),
        ("artifact", "/workspace/signed.json"),
        ("artifact", "/data/signed.json"),
        ("artifact", "/private/signed.json"),
        ("artifact", "/secrets/prod/service-token.txt"),
        ("artifact", "/github/workspace/.env"),
        ("artifact", "repo/.env"),
        ("artifact", "repo/.ssh/id_ed25519"),
        ("artifact", "repo/credentials.json"),
        ("artifact", "repo/id_rsa"),
        ("artifact", "file:///private/signed.json"),
        ("artifact", "smb://fileserver/private/credential.txt"),
        ("artifact", "nfs://fileserver/private/signed.json"),
        ("artifact", "ssh://fileserver/private/signed.json"),
        ("artifact", "scp://fileserver/private/signed.json"),
        ("artifact", "~/signed.json"),
        ("artifact", "$HOME/signed.json"),
        ("artifact", "${HOME}/signed.json"),
        ("artifact", r"%USERPROFILE%\signed.json"),
        ("artifact", r"$env:USERPROFILE\signed.json"),
        ("artifact", r"%HOMEDRIVE%%HOMEPATH%\signed.json"),
        ("artifact", "../signed.json"),
        ("artifact", "safe/../signed.json"),
        ("artifact", r"C:\Users\operator\signed.json"),
        ("artifact", "D:/private/signed.json"),
        ("artifact", r"\\fileserver\private\signed.json"),
        ("artifact", "receipt=[/tmp/signed.json]"),
        ("artifact", "token=value"),
        ("artifact", "password: value"),
        ("api_key", "ordinary-looking-value"),
        ("token", "ordinary-looking-value"),
        ("authorization", "ordinary-looking-value"),
        ("private", "ordinary-looking-value"),
        ("private_key", "ordinary-looking-value"),
        ("private-key", "ordinary-looking-value"),
        ("privateKey", "ordinary-looking-value"),
        ("artifact", "Bearer abcdefghijklmnopqrstuvwxyz"),
        ("artifact", "Bearer abc"),
        ("artifact", "Basic ZHVtbXk6c2VudGluZWw="),
        ("artifact", "Basic YTpi"),
        ("artifact", "https://writer:secret@example.test/public"),  # pragma: allowlist secret
        (
            "artifact",
            "postgresql://writer:secret@example.test/database",  # pragma: allowlist secret
        ),
        ("public_url", "/tmp/hidden.json"),
        ("canonical_path", "/tmp/hidden.json"),
        ("canonical_url", "/tmp/hidden.json"),
        ("bound_final_canonical_url", "/tmp/hidden.json"),
    ],
)
@pytest.mark.parametrize("signed_document", ["packet", "judge"])
def test_signed_input_rejects_private_paths_and_credential_like_material(
    key: str,
    value: str,
    signed_document: str,
) -> None:
    baseline = build_inputs()
    if signed_document == "packet":
        packet = copy.deepcopy(baseline.packet)
        packet["untrusted_extra"] = {key: value}
        unsafe = resign(packet, policy=baseline.policy)
    else:
        judge = copy.deepcopy(baseline.judge)
        judge["untrusted_extra"] = {key: value}
        unsafe = resign_judge(baseline, judge)
    _expect_rejection(unsafe, "unsafe_signed_material")


@pytest.mark.parametrize("canonical_path", ["/root/przewodnik", "/credentials"])
def test_signed_input_allows_sensitive_named_paths_only_at_exact_canonical_row_location(
    canonical_path: str,
) -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[0])
    public_url = f"https://www.ekologus.pl{canonical_path}/"
    row["path"] = canonical_path
    row["public_url"] = public_url
    state = cast(dict[str, object], row["draft_and_action_state"])
    action = cast(
        dict[str, object], cast(list[object], state["verified_current_action_bindings"])[0]
    )
    action["bound_final_canonical_url"] = public_url
    policy = baseline.policy.model_copy(
        update={
            "canonical_paths": (canonical_path, PATHS[1]),
            "protected_binding": baseline.policy.protected_binding.model_copy(
                update={"canonical_path": canonical_path}
            ),
        }
    )

    run = _parse(resign(packet, policy=policy, sync_policy_decision=True))

    assert run.rows[0].canonical_path == canonical_path
    assert run.rows[0].verified_actions[0].bound_final_canonical_url == public_url


@pytest.mark.parametrize("signed_document", ["packet", "judge"])
def test_signed_input_allows_https_urls_without_filesystem_false_positives(
    signed_document: str,
) -> None:
    baseline = build_inputs()
    if signed_document == "packet":
        packet = copy.deepcopy(baseline.packet)
        packet["untrusted_extra"] = {
            "reference": "https://public.example.test/guides/credentials.json"
        }
        inputs = resign(packet, policy=baseline.policy)
    else:
        judge = copy.deepcopy(baseline.judge)
        judge["untrusted_extra"] = {
            "reference": "https://public.example.test/guides/credentials.json"
        }
        inputs = resign_judge(baseline, judge)

    assert _parse(inputs).rows[0].canonical_path == PATHS[0]


@pytest.mark.parametrize(
    ("field", "unsafe_identity", "expected_code"),
    [
        ("recorded_by", "/etc/passwd", "unsafe_signed_material"),
        ("reviewed_by", r"C:\Users\reviewer\identity.txt", "unsafe_signed_material"),
        ("recorded_by", r"\\fileserver\private\identity.txt", "unsafe_signed_material"),
        ("reviewed_by", "Bearer abcdefghijklmnopqrstuvwxyz", "unsafe_signed_material"),
        ("reviewed_by", "Bearer abc", "unsafe_signed_material"),
        ("recorded_by", "Basic ZHVtbXk6c2VudGluZWw=", "unsafe_signed_material"),
        ("recorded_by", "Basic YTpi", "unsafe_signed_material"),
        ("recorded_by", "token=value", "unsafe_signed_material"),
        ("reviewed_by", "password: value", "unsafe_signed_material"),
        ("recorded_by", "$HOME/identity.txt", "unsafe_signed_material"),
        ("reviewed_by", r"%USERPROFILE%\identity.txt", "unsafe_signed_material"),
        ("recorded_by", "../identity.txt", "unsafe_signed_material"),
        ("reviewed_by", "reviewer|shell", "reviewed_by_invalid"),
        ("recorded_by", "operator/name", "recorded_by_invalid"),
        ("reviewed_by", "reviewer\nname", "reviewed_by_invalid"),
        ("recorded_by", "operator🙂", "recorded_by_invalid"),
        ("recorded_by", "   ", "recorded_by_invalid"),
    ],
)
def test_audit_identity_rejects_unsafe_material(
    field: str,
    unsafe_identity: str,
    expected_code: str,
) -> None:
    with pytest.raises(ContentProductionClassificationValidationError) as error:
        if field == "recorded_by":
            _parse(build_inputs(), recorded_by=unsafe_identity)
        else:
            _parse(build_inputs(), reviewed_by=unsafe_identity)

    assert error.value.code == expected_code
    assert str(error.value) == f"Production classification rejected: {expected_code}."


def test_audit_identity_allows_unicode_letters_digits_and_limited_punctuation() -> None:
    run = _parse(
        build_inputs(),
        recorded_by="Żaneta_2026 @ Ekologus:QA-1",
        reviewed_by="Łukasz.Recenzent_2@example.test",
    )

    assert run.audit.recorded_by == "Żaneta_2026 @ Ekologus:QA-1"
    assert run.audit.reviewed_by == "Łukasz.Recenzent_2@example.test"


def test_any_nested_generation_flag_must_remain_disabled() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    packet["untrusted_extra"] = {"new_generation_allowed": True}
    _expect_rejection(resign(packet, policy=baseline.policy), "generation_not_disabled")


@pytest.mark.parametrize(
    ("path", "replacement", "expected_code"),
    [
        (
            ("rows", 1, "typed_blockers", 0, "blocks_initial_generation"),
            1,
            "typed_classification_invalid",
        ),
        (
            ("rows", 0, "retained_revision_binding", "must_not_regenerate"),
            1,
            "typed_classification_invalid",
        ),
        (
            (
                "rows",
                0,
                "draft_and_action_state",
                "verified_current_action_bindings",
                0,
                "adapter_reached",
            ),
            1,
            "typed_classification_invalid",
        ),
        (
            (
                "rows",
                1,
                "evidence",
                "lineage_defects",
                0,
                "usable_as_decision_proof",
            ),
            0,
            "typed_classification_invalid",
        ),
        (
            (
                "rows",
                0,
                "source_packet_receipts",
                "classification_raw_artifact_retained",
            ),
            0,
            "typed_classification_invalid",
        ),
        (("counts", "rows"), 2.0, "count_invalid"),
    ],
    ids=["blocker", "retained-binding", "action", "evidence", "receipt", "count"],
)
def test_signed_json_nested_scalar_types_are_exact(
    path: tuple[str | int, ...],
    replacement: object,
    expected_code: str,
) -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    _set_nested_json_value(packet, path, replacement)
    tampered = resign(
        packet,
        policy=baseline.policy,
        sync_policy_decision=True,
    )

    _expect_rejection(tampered, expected_code)


def test_row_receipt_tamper_is_rejected_after_exact_bytes_are_resigned() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    receipt = cast(dict[str, object], row["source_packet_receipts"])
    receipt["classification_row_sha256"] = "f" * 64
    tampered = resign(
        packet,
        policy=baseline.policy,
        sync_policy_decision=True,
        repair_row_receipts=False,
    )
    _expect_rejection(tampered, "row_digest_mismatch")


def test_coherent_decision_tamper_still_fails_the_pinned_semantic_digest() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    row["decision"] = "write"
    counts = cast(dict[str, object], packet["counts"])
    counts["write"] = 1
    counts["blocked"] = 0
    _expect_rejection(resign(packet, policy=baseline.policy), "decision_set_digest_mismatch")


def test_exact_source_receipt_drift_is_rejected() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    sources = cast(dict[str, object], packet["source_file_receipts"])
    matched = cast(dict[str, object], sources["matched_classification"])
    matched["sha256"] = "c" * 64
    _expect_rejection(resign(packet, policy=baseline.policy), "source_receipt_mismatch")


def test_matched_unmatched_classifier_receipt_binding_cannot_drift() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    blocked = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    receipt = cast(dict[str, object], blocked["source_packet_receipts"])
    receipt["classification_source"] = "matched"
    tampered = resign(packet, policy=baseline.policy, sync_policy_decision=True)
    _expect_rejection(tampered, "classifier_receipt_binding_mismatch")


def test_invalid_legacy_evidence_cannot_be_promoted_to_proof() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    blocked = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    evidence = cast(dict[str, object], blocked["evidence"])
    cast(list[object], evidence["evidence_ids"]).append("ev_legacy_invalid")
    tampered = resign(packet, policy=baseline.policy, sync_policy_decision=True)
    _expect_rejection(tampered, "invalid_evidence_used_as_proof")


def test_protected_revision_action_draft_binding_drift_is_rejected() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[0])
    revision = cast(dict[str, object], row["revision"])
    binding = cast(dict[str, object], row["retained_revision_binding"])
    state = cast(dict[str, object], row["draft_and_action_state"])
    action = cast(
        dict[str, object], cast(list[object], state["verified_current_action_bindings"])[0]
    )
    draft = cast(dict[str, object], cast(list[object], state["verified_current_draft_bindings"])[0])
    for target, key in (
        (revision, "digest"),
        (binding, "retained_revision_digest"),
        (action, "bound_content_digest"),
        (draft, "revision_digest"),
    ):
        target[key] = "7" * 64
    tampered = resign(packet, policy=baseline.policy, sync_policy_decision=True)
    _expect_rejection(tampered, "protected_binding_drift")


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_exact_policy_path_scope_rejects_missing_extra_and_duplicate_paths(
    mutation: str,
) -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    rows = cast(list[object], packet["rows"])
    if mutation == "missing":
        rows.pop()
    else:
        row = cast(dict[str, object], rows[-1])
        row["path"] = "/extra" if mutation == "extra" else PATHS[0]
        row["public_url"] = f"https://www.ekologus.pl{row['path']}/"
    tampered = resign(packet, policy=baseline.policy, sync_policy_decision=True)
    _expect_rejection(tampered, "canonical_scope_mismatch")


def test_store_atomically_reads_projects_and_preserves_idempotent_audit(tmp_path: Path) -> None:
    inputs = build_inputs()
    run = _parse(inputs)
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")

    assert store.record_production_classification(run).status == "created"
    assert store.load_latest_production_classification() == run
    projection = store.load_production_classification_for_work_item("work_retained")
    assert projection is not None and projection.row.canonical_path == PATHS[0]
    assert store.record_production_classification(run).status == "idempotent"
    audit_only_retry = _parse(
        inputs,
        recorded_at=AUDIT_TIME + timedelta(seconds=1),
        recorded_by="different_valid_writer",
        reviewed_by="different_valid_reviewer",
    )
    assert audit_only_retry.audit != run.audit
    assert audit_only_retry.input_digest == run.input_digest
    assert audit_only_retry.run_digest == run.run_digest
    idempotent = store.record_production_classification(audit_only_retry)
    assert idempotent.status == "idempotent"
    assert idempotent.run.audit == run.audit

    different_result = _different_coherent_result(audit_only_retry)
    assert different_result.input == run.input
    assert different_result.run_id == run.run_id
    assert different_result.run_digest != run.run_digest
    conflict = store.record_production_classification(different_result)
    assert conflict.status == "conflict"
    assert conflict.run == run

    with sqlite3.connect(store.path) as connection:
        count, payload = connection.execute(
            "SELECT COUNT(*), payload_json FROM content_production_classifications"
        ).fetchone()
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(content_production_classifications)")
        }
    assert count == 1
    assert {"packet_base64", "judge_base64"}.isdisjoint(columns)
    assert "packet_base64" not in payload and "judge_base64" not in payload
    _assert_signed_material_not_retained(store, inputs.packet_bytes, inputs.judge_bytes)

    tampered_payload = json.loads(payload)
    tampered_payload["rows"][0]["rationale_pl"] = "Niezwiązana zmiana po zapisie."
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE content_production_classifications SET payload_json = ?",
            (json.dumps(tampered_payload),),
        )
    with pytest.raises(ValidationError):
        store.load_latest_production_classification()


def test_parent_router_asgi_roundtrip_records_reads_retries_and_conflicts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = build_inputs()
    store = ContentWorkflowStore(tmp_path / "api.sqlite3")
    monkeypatch.setattr(classification_api, "WAVE0_PRODUCTION_ACCEPTANCE_POLICY", inputs.policy)
    monkeypatch.setattr(classification_api, "content_workflow_store", lambda: store)
    payload = {
        "policy_selector": "wave0-production-classification-v1",
        "packet_base64": base64.b64encode(inputs.packet_bytes).decode(),
        "judge_base64": base64.b64encode(inputs.judge_bytes).decode(),
        "recorded_by": "codex_w1_test",
        "reviewed_by": "independent_test_judge",
        "recorded_at": AUDIT_TIME.isoformat(),
    }
    retry_payload = {
        **payload,
        "recorded_by": "different_valid_writer",
        "reviewed_by": "different_valid_reviewer",
        "recorded_at": (AUDIT_TIME + timedelta(seconds=1)).isoformat(),
    }
    different_result = _different_coherent_result(_parse(inputs))
    assert different_result.input == _parse(inputs).input
    app = _classification_app()
    before = _asgi_request(
        app,
        "GET",
        "/api/content/production-classifications/latest",
    )
    created = _asgi_request(
        app,
        "POST",
        "/api/content/production-classifications",
        body=payload,
    )
    repeated = _asgi_request(
        app,
        "POST",
        "/api/content/production-classifications",
        body=retry_payload,
    )
    latest = _asgi_request(
        app,
        "GET",
        "/api/content/production-classifications/latest",
    )
    projected = _asgi_request(
        app,
        "GET",
        "/api/content/production-classifications/work-items/work_retained",
    )
    missing = _asgi_request(
        app,
        "GET",
        "/api/content/production-classifications/work-items/missing",
    )

    def parse_different_result(**_: object) -> ContentProductionClassificationRun:
        return different_result

    monkeypatch.setattr(
        classification_api,
        "parse_content_production_classification",
        parse_different_result,
    )
    conflicting = _asgi_request(
        app,
        "POST",
        "/api/content/production-classifications",
        body=retry_payload,
    )
    _assert_classification_roundtrip(
        (before, created, repeated, latest, projected, missing, conflicting),
        inputs,
        payload,
    )


@pytest.mark.parametrize(
    ("packet_base64", "expected_detail"),
    [
        ("", "production_classification_size_invalid"),
        ("%%%%HOSTILE_MALFORMED_BASE64", "production_classification_base64_invalid"),
        (
            "A" * ((((1_048_576 + 2) // 3) * 4) + 1),
            "production_classification_size_invalid",
        ),
    ],
    ids=["empty", "invalid-base64", "oversized"],
)
def test_api_rejects_non_strict_or_oversized_base64_with_code_only_detail(
    packet_base64: str,
    expected_detail: str,
) -> None:
    inputs = build_inputs()
    judge_base64 = base64.b64encode(inputs.judge_bytes).decode()
    response = _asgi_request(
        _classification_app(),
        "POST",
        "/api/content/production-classifications",
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
    for forbidden in (packet_base64, judge_base64, inputs.judge_bytes.decode()):
        if forbidden:
            assert forbidden not in response.text


def test_openapi_documents_the_code_only_validation_error_contract() -> None:
    schema = _classification_app().openapi()
    error_response = schema["paths"]["/api/content/production-classifications"]["post"][
        "responses"
    ]["422"]

    assert error_response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ContentProductionClassificationErrorResponse"
    }
    detail_schema = schema["components"]["schemas"]["ContentProductionClassificationErrorResponse"][
        "properties"
    ]["detail"]
    assert detail_schema["type"] == "string"
    assert detail_schema["pattern"] == "^[a-z][a-z0-9_]*$"


def test_runtime_only_wave0_packet_smoke_reads_ephemeral_files(tmp_path: Path) -> None:
    packet_path = Path("/tmp/wave0-production-classification-v1.json")
    judge_path = Path("/tmp/wave0-production-classification-judge.json")
    if not packet_path.is_file() or not judge_path.is_file():
        pytest.skip("Runtime-only Wave0 packet is not present in this environment.")

    packet_bytes = packet_path.read_bytes()
    judge_bytes = judge_path.read_bytes()
    run = parse_content_production_classification(
        packet_bytes=packet_bytes,
        judge_bytes=judge_bytes,
        acceptance_policy=WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
        recorded_by="codex_w1_runtime_smoke",
        reviewed_by="owner_independent_judge",
        recorded_at=AUDIT_TIME,
    )
    store = ContentWorkflowStore(tmp_path / "runtime-wave0.sqlite3")
    assert store.record_production_classification(run).status == "created"
    _assert_signed_material_not_retained(store, packet_bytes, judge_bytes)
    bdo = run.for_work_item("content_work_item_inventory_5391632ca65d5e8714952a84")

    assert len(run.rows) == 57
    assert (run.counts.reuse, run.counts.refresh, run.counts.write, run.counts.blocked) == (
        13,
        19,
        0,
        25,
    )
    assert run.counts.generation_allowed == 0
    assert run.counts.verified_current_actions == run.counts.verified_current_drafts == 8
    identity_statuses = tuple(
        row.retained_binding.identity_reconciliation_status
        for row in run.rows
        if row.retained_binding is not None
    )
    assert identity_statuses.count("fork") == 11
    assert identity_statuses.count("retained_missing") == 2
    assert bdo is not None and bdo.retained_binding is not None
    assert bdo.decision == "reuse" and bdo.generation_allowed is False
    assert bdo.retained_binding.current_inventory_work_item_id == (
        "content_work_item_inventory_5391632ca65d5e8714952a84"
    )
    assert bdo.retained_binding.retained_work_item_id == (
        "content_work_item_content_decision_https___www_ekologus_pl_"
        "bdo_co_musi_wiedziec_przedsiebiorca"
    )
    assert bdo.retained_binding.retained_revision_id == (
        "content_revision_52d07d4011c04168842c87aeb26785a1"
    )
    assert (
        bdo.retained_binding.retained_revision_digest
        == (
            "a8f02b1b0223651e105ced3c7e38e506d77f7f8a543b6f5ccbda99f93874b6f8"  # pragma: allowlist secret  # noqa: E501
        )
    )
    assert bdo.retained_binding.verified_draft_action_ids == (
        "act_content_dev_draft_5a81402fb4b54897a8aee88832060a15",
    )
    assert bdo.retained_binding.verified_draft_post_ids == ("1991",)
    invalid_id = "ev_regulatory_source_review_"
    defects = [
        (row, defect)
        for row in run.rows
        for defect in row.lineage_defects
        if defect.evidence_id == invalid_id
    ]
    assert len(defects) == 1 and defects[0][1].status == "invalid_unusable"
    assert all(
        invalid_id not in (*row.primary_evidence_ids, *row.lineage_evidence_ids) for row in run.rows
    )
    assert any(blocker.code == "invalid_legacy_evidence_id" for blocker in defects[0][0].blockers)
