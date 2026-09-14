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
    build_blocked_historical_protection_inputs,
    build_clean_current_all_blocked_inputs,
    build_inputs,
    build_missing_source_binding_inputs,
    build_present_source_binding_inputs,
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
HEAD_FORMAT_CLASSIFICATION_PAYLOAD = (
    r'{"audit":{"recorded_at":"2026-08-30T10:05:00Z","recorded_by":"codex_w1_test","reviewed_b'
    r'y":"independent_test_judge"},"counts":{"blocked":1,"generation_allowed":0,"refresh":0,"r'
    r'euse":1,"rows":2,"verified_current_actions":1,"verified_current_drafts":1,"write":0},"fr'
    r'eshness":{"checked_at":"2026-08-30T09:59:00Z","connector_ids":["gsc","wordpress"],"requi'
    r'res_refresh":false,"state":"fresh"},"input":{"base_revision":"11111111111111111111111111'
    r'11111111111111","decision_set_digest":"5d460357303b2c32ee8dec6a8e9bfd201543e4a7aa5002b27'
    r'6cfea8df845e35a","judge_sha256":"ec462c939f2c6d56844abcf47a979bd1b677e4fb436a8d52b60d224'
    r'858146604","packet_generated_at":"2026-08-30T10:00:00Z","packet_schema_version":"wilq_co'
    r'ntent_production_classification_v1","packet_sha256":"685f83ffb016dd1398d004a576d5fa16487'
    r'734d553e6edc70113834d7785d062","policy_digest":"49488f61677c1576d8f44b5392e5c66de370eddd'
    r'df82c0ddcf61ee7089763570","policy_id":"synthetic_v1"},"input_digest":"6926397089f45acb12'
    r'16e193382958e0bc5c844bf3c6033ba01b56297a9a3895","judge_receipt":{"generated_at":"2026-08'
    r'-30T10:01:00Z","reviewed_decision_set_digest":"5d460357303b2c32ee8dec6a8e9bfd201543e4a7a'
    r'a5002b276cfea8df845e35a","reviewed_packet_sha256":"685f83ffb016dd1398d004a576d5fa1648773'
    r'4d553e6edc70113834d7785d062","reviewer_role":"independent_judge","schema_version":"synth'
    r'etic_judge_v1","sha256":"ec462c939f2c6d56844abcf47a979bd1b677e4fb436a8d52b60d22485814660'
    r'4","verdict":"accept"},"rows":[{"blockers":[],"canonical_path":"/bdo-test","current_work'
    r'_item_id":"work_current_1","decision":"reuse","generation_allowed":false,"lineage_defect'
    r's":[],"lineage_evidence_ids":["lineage_1"],"next_step_pl":"Sprawdź bezpieczny krok.","pr'
    r'imary_evidence_ids":["ev_1"],"public_url":"https://www.ekologus.pl/bdo-test/","rationale'
    r'_pl":"Zażółć gęślą 1.","retained_binding":{"binding_basis":"exact_normalized_path_with_r'
    r'etained_revision_state","current_inventory_work_item_id":"work_current_1","identity_reco'
    r'nciliation_status":"fork","must_not_regenerate":true,"retained_revision_digest":"9999999'
    r'999999999999999999999999999999999999999999999999999999999","retained_revision_id":"conte'
    r'nt_revision_test","retained_work_item_id":"work_retained","verified_draft_action_ids":["'
    r'act_content_dev_draft_test"],"verified_draft_post_ids":["1991"]},"retained_work_item_id"'
    r':"work_retained","revision_approved":true,"revision_complete":true,"revision_digest":"99'
    r'99999999999999999999999999999999999999999999999999999999999999","revision_id":"content_r'
    r'evision_test","source_connectors":["gsc"],"source_packet_row_digest":"cb1a1198c24e5bb453'
    r'45740c93a0c86b9488580f5ae6822fce415a723e0bd9f9","source_receipt":{"authoring_inventory_r'
    r'ow_sha256":"1111111111111111111111111111111111111111111111111111111111111111","bound_mut'
    r'ation_audit_row_sha256":[],"canonical_ledger_row_sha256":"111111111111111111111111111111'
    r'1111111111111111111111111111111111","classification_artifact_reference":"matched.json","'
    r'classification_file_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    r'aaaaa","classification_raw_artifact_retained":false,"classification_retention_status":"e'
    r'xternal_ephemeral_receipt_only","classification_row_sha256":"111111111111111111111111111'
    r'1111111111111111111111111111111111111","classification_source":"matched","draft_row_sha2'
    r'56":[],"keep_eligibility_row_sha256":"11111111111111111111111111111111111111111111111111'
    r'11111111111111","lineage_defects_sha256":null,"source_pack_id":"pack_1","state_journal_u'
    r'rl_row_sha256":"1111111111111111111111111111111111111111111111111111111111111111","usabl'
    r'e_canonical_ledger_evidence_ids_sha256":null},"verified_actions":[{"action_id":"act_cont'
    r'ent_dev_draft_test","action_type":"content_dev_draft_create","adapter_reached":true,"bou'
    r'nd_content_digest":"9999999999999999999999999999999999999999999999999999999999999999","b'
    r'ound_final_canonical_url":"https://www.ekologus.pl/bdo-test/","bound_revision_id":"conte'
    r'nt_revision_test","bound_work_item_id":"work_retained","external_write_attempted":true,"'
    r'mutation_audit_id":"audit_test","status":"applied"}],"verified_drafts":[{"action_id":"ac'
    r't_content_dev_draft_test","apply_audit_id":"audit_test","post_id":"1991","readback_conte'
    r'nt_digest":"8888888888888888888888888888888888888888888888888888888888888888","readback_'
    r'status":"verified","revision_digest":"99999999999999999999999999999999999999999999999999'
    r'99999999999999","revision_id":"content_revision_test","state_class":"dev_draft_verified"'
    r',"wordpress_draft_status":"draft"}]},{"blockers":[{"blocks_initial_generation":true,"cod'
    r'e":"invalid_legacy_evidence_id","next_step_pl":"Napraw lineage przed pracą.","owner":"ow'
    r'ner_test","sources":["ledger"]}],"canonical_path":"/zablokowane","current_work_item_id":'
    r'"work_current_2","decision":"blocked","generation_allowed":false,"lineage_defects":[{"ev'
    r'idence_id":"ev_legacy_invalid","next_step_pl":"Napraw lineage.","owner":"owner_test","re'
    r'ason_pl":"Niepełny identyfikator.","source":"ledger","status":"invalid_unusable","usable'
    r'_as_decision_proof":false}],"lineage_evidence_ids":["lineage_2"],"next_step_pl":"Sprawdź'
    r' bezpieczny krok.","primary_evidence_ids":["ev_2"],"public_url":"https://www.ekologus.pl'
    r'/zablokowane/","rationale_pl":"Zażółć gęślą 2.","retained_binding":null,"retained_work_i'
    r'tem_id":null,"revision_approved":false,"revision_complete":false,"revision_digest":null,'
    r'"revision_id":null,"source_connectors":["gsc"],"source_packet_row_digest":"3048d88afaadf'
    r'2f126035808fa6ee9eef231cc78baaceb50f1d2d83cfbdadb25","source_receipt":{"authoring_invent'
    r'ory_row_sha256":"2222222222222222222222222222222222222222222222222222222222222222","boun'
    r'd_mutation_audit_row_sha256":[],"canonical_ledger_row_sha256":"2222222222222222222222222'
    r'222222222222222222222222222222222222222","classification_artifact_reference":"unmatched.'
    r'json","classification_file_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
    r'bbbbbbbbbbbb","classification_raw_artifact_retained":false,"classification_retention_sta'
    r'tus":"external_ephemeral_receipt_only","classification_row_sha256":"22222222222222222222'
    r'22222222222222222222222222222222222222222222","classification_source":"unmatched","draft'
    r'_row_sha256":[],"keep_eligibility_row_sha256":"22222222222222222222222222222222222222222'
    r'22222222222222222222222","lineage_defects_sha256":null,"source_pack_id":"pack_2","state_'
    r'journal_url_row_sha256":"222222222222222222222222222222222222222222222222222222222222222'
    r'2","usable_canonical_ledger_evidence_ids_sha256":null},"verified_actions":[],"verified_d'
    r'rafts":[]}],"run_digest":"eb736dd43001014d458647cf30b3772784b0edc9c1e920635ec10900051d33'
    r'ac","run_id":"content_production_classification_685f83ffb016dd1398d004a5","schema_versio'
    r'n":"wilq_content_production_classification_run_v1","source_receipts":[{"name":"matched_c'
    r'lassification","raw_artifact_retained":false,"reference":"matched.json","retention_statu'
    r's":"external_ephemeral_receipt_only","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    r'aaaaaaaaaaaaaaaaaaaaaaa"},{"name":"unmatched_classification","raw_artifact_retained":fal'
    r'se,"reference":"unmatched.json","retention_status":"external_ephemeral_receipt_only","sh'
    r'a256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}]}'
)


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


@pytest.mark.parametrize(
    "unsafe_identity",
    [
        "https://www.ekologus.pl/zablokowane/",
        "zablokowane",
        "1992",
    ],
    ids=["url", "slug", "post-id"],
)
def test_parser_rejects_non_work_item_identity_before_lookup(unsafe_identity: str) -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    blocked_row = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    identity = cast(dict[str, object], blocked_row["work_item_identity"])
    identity["current_inventory_work_item_id"] = unsafe_identity

    inputs = resign(packet, policy=baseline.policy, sync_policy_decision=True)

    _expect_rejection(inputs, "work_item_identity_invalid")


def test_parser_rejects_packet_that_requires_freshness_refresh() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    freshness = cast(dict[str, object], packet["wilq_diagnostic_freshness"])
    freshness["requires_refresh"] = True

    _expect_rejection(
        resign(packet, policy=baseline.policy),
        "freshness_requires_refresh",
    )


def test_parser_rejects_coherently_signed_blocked_row_without_typed_blocker() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    blocked_row = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    blocked_row["typed_blockers"] = []

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "typed_classification_invalid",
    )


def test_blocked_row_without_current_or_revision_identity_cannot_resolve_work_item() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    blocked_row = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    identity = cast(dict[str, object], blocked_row["work_item_identity"])
    identity["current_inventory_work_item_id"] = None

    run = _parse(resign(packet, policy=baseline.policy, sync_policy_decision=True))
    row = run.rows[1]

    assert row.decision == "blocked"
    assert row.current_work_item_id is None
    assert row.revision_id is None
    assert row.revision_digest is None
    assert row.retained_binding is None
    assert row.verified_actions == ()
    assert row.verified_drafts == ()
    assert len(row.blockers) == 1
    assert not row.protects_work_item("work_current_2")
    assert row.lookup_basis_for_work_item("work_current_2") is None
    assert run.for_work_item("work_current_2") is None
    assert row.reusable_work_item_id is None


def test_parser_accepts_signed_blocked_historical_protection_without_reuse() -> None:
    run = _parse(build_blocked_historical_protection_inputs())
    row = run.rows[0]

    assert row.decision == "blocked"
    assert row.blocked_historical_protection is not None
    assert row.blocked_historical_protection.historical_revision_id == (
        "content_revision_historical_blocked"
    )
    assert row.blocked_historical_protection.historical_revision_digest == "7" * 64
    assert row.blocked_historical_protection.current_verification_outcome == "drifted"
    assert row.blocked_historical_protection.current_verification_evidence_id == (
        "ev_current_historical_readback"
    )
    assert row.blocked_historical_protection.current_verification_connector == "wordpress"
    assert row.retained_work_item_id is None
    assert row.retained_binding is None
    assert row.revision_id is None
    assert row.revision_digest is None
    assert row.verified_actions == ()
    assert row.verified_drafts == ()
    assert row.reusable_work_item_id is None


def test_parser_accepts_clean_current_all_blocked_packet_without_invalid_evidence() -> None:
    run = _parse(build_clean_current_all_blocked_inputs())

    assert all(not row.lineage_defects for row in run.rows)
    assert run.rows[1].blockers[0].code == "current_source_evidence_gap"


def test_parser_rejects_injected_lineage_defect_when_policy_has_none() -> None:
    baseline = build_clean_current_all_blocked_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    evidence = cast(dict[str, object], row["evidence"])
    evidence["lineage_defects"] = [
        {
            "evidence_id": "ev_injected_invalid",
            "source": "ledger",
            "owner": "owner_test",
            "reason_pl": "Wstrzyknięta wada lineage.",
            "next_step_pl": "Napraw lineage.",
            "status": "invalid_unusable",
            "usable_as_decision_proof": False,
        }
    ]

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "invalid_evidence_used_as_proof",
    )


def test_parser_rejects_removed_lineage_defect_for_existing_invalid_evidence_policy() -> None:
    baseline = build_inputs()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    cast(dict[str, object], row["evidence"])["lineage_defects"] = []

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "invalid_evidence_used_as_proof",
    )


def test_parser_rejects_signed_promotion_of_historical_protection_to_reuse() -> None:
    baseline = build_blocked_historical_protection_inputs()
    packet = copy.deepcopy(baseline.packet)
    protected = cast(dict[str, object], cast(list[object], packet["rows"])[0])
    protected["decision"] = "reuse"

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "typed_classification_invalid",
    )


def test_parser_rejects_signed_historical_protection_outcome_mismatch() -> None:
    baseline = build_blocked_historical_protection_inputs()
    packet = copy.deepcopy(baseline.packet)
    protected = cast(dict[str, object], cast(list[object], packet["rows"])[0])
    history = cast(dict[str, object], protected["blocked_historical_protection"])
    history["current_verification_outcome"] = "unavailable"

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "protected_history_drift",
    )


def test_parser_rejects_unbound_second_historical_protection() -> None:
    baseline = build_blocked_historical_protection_inputs()
    packet = copy.deepcopy(baseline.packet)
    second = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    second["blocked_historical_protection"] = {
        "historical_revision_id": "content_revision_unbound",
        "historical_revision_digest": "6" * 64,
        "current_verification_outcome": "unavailable",
        "current_verification_evidence_id": "ev_unbound_readback",
        "current_verification_connector": "wordpress",
        "current_verification_checked_at": "2026-08-30T10:03:00Z",
        "must_not_regenerate": True,
    }

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "protected_history_scope_mismatch",
    )


def test_parser_accepts_signed_missing_source_binding_without_reusable_identity() -> None:
    inputs = build_missing_source_binding_inputs()
    run = _parse(inputs)
    row = run.rows[1]
    receipt = row.source_receipt

    assert receipt.binding_state == "missing"
    assert receipt.missing_sources == (
        "authoring_inventory_row",
        "source_pack_binding",
    )
    assert receipt.content_status_row_sha256 == "c" * 64
    assert receipt.wordpress_catalog_scope_sha256 == "d" * 64
    assert receipt.catalog_lookup_outcome == "exact_path_absent"
    assert row.decision == "blocked"
    assert row.generation_allowed is False
    assert len(row.blockers) == 1
    assert row.current_work_item_id is None
    assert row.retained_work_item_id is None
    assert row.revision_id is None
    assert row.revision_digest is None
    assert row.revision_approved is False
    assert row.revision_complete is False
    assert row.retained_binding is None
    assert row.verified_actions == ()
    assert row.verified_drafts == ()
    assert "source_pack_id" not in cast(dict[str, object], row_input(inputs))["evidence"]
    assert not row.protects_work_item("work_current_2")
    assert row.lookup_basis_for_work_item("work_current_2") is None
    assert run.for_work_item("work_current_2") is None
    assert row.reusable_work_item_id is None


def test_parser_accepts_signed_present_catalog_without_reusable_identity() -> None:
    inputs = build_present_source_binding_inputs()
    run = _parse(inputs)
    row = run.rows[1]
    receipt = row.source_receipt

    assert receipt.binding_state == "missing"
    assert receipt.missing_sources == (
        "delivery_identity_binding",
        "source_pack_binding",
    )
    assert receipt.content_status_row_sha256 == "c" * 64
    assert receipt.wordpress_catalog_scope_sha256 == "d" * 64
    assert receipt.catalog_lookup_outcome == "exact_path_present"
    assert row.decision == "blocked"
    assert row.generation_allowed is False
    assert len(row.blockers) == 1
    assert row.current_work_item_id is None
    assert row.retained_work_item_id is None
    assert row.revision_id is None
    assert row.revision_digest is None
    assert row.revision_approved is False
    assert row.revision_complete is False
    assert row.retained_binding is None
    assert row.verified_actions == ()
    assert row.verified_drafts == ()
    assert "source_pack_id" not in cast(dict[str, object], row_input(inputs))["evidence"]
    assert not row.protects_work_item("work_current_2")
    assert row.lookup_basis_for_work_item("work_current_2") is None
    assert run.for_work_item("work_current_2") is None
    assert row.reusable_work_item_id is None


@pytest.mark.parametrize(
    ("inputs_builder", "missing_sources", "catalog_lookup_outcome"),
    [
        (
            build_present_source_binding_inputs,
            ["authoring_inventory_row", "source_pack_binding"],
            "exact_path_present",
        ),
        (
            build_missing_source_binding_inputs,
            ["delivery_identity_binding", "source_pack_binding"],
            "exact_path_absent",
        ),
    ],
    ids=["present-with-authoring-gap", "absent-with-delivery-identity-gap"],
)
def test_missing_source_binding_rejects_catalog_gap_mismatch(
    inputs_builder: object,
    missing_sources: list[str],
    catalog_lookup_outcome: str,
) -> None:
    baseline = cast(SyntheticInputs, inputs_builder)()
    packet = copy.deepcopy(baseline.packet)
    row = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    receipt = cast(dict[str, object], row["source_packet_receipts"])
    receipt["missing_sources"] = missing_sources
    receipt["catalog_lookup_outcome"] = catalog_lookup_outcome

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "missing_source_binding_mismatch",
    )


def test_missing_source_binding_rejects_signed_current_work_item_identity() -> None:
    baseline = build_missing_source_binding_inputs()
    packet = copy.deepcopy(baseline.packet)
    missing = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    identity = cast(dict[str, object], missing["work_item_identity"])
    identity["current_inventory_work_item_id"] = "work_current_2"

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "missing_source_binding_mismatch",
    )


def test_missing_source_binding_rejects_signed_reuse_state() -> None:
    baseline = build_missing_source_binding_inputs()
    packet = copy.deepcopy(baseline.packet)
    missing = cast(dict[str, object], cast(list[object], packet["rows"])[1])
    exact = cast(dict[str, object], cast(list[object], build_inputs().packet["rows"])[0])
    missing["decision"] = "reuse"
    missing["work_item_identity"] = copy.deepcopy(exact["work_item_identity"])
    identity = cast(dict[str, object], missing["work_item_identity"])
    identity.update(
        {
            "current_inventory_work_item_id": "work_current_2",
            "retained_work_item_id": "work_retained_2",
        }
    )
    missing["revision"] = copy.deepcopy(exact["revision"])
    missing["retained_revision_binding"] = copy.deepcopy(exact["retained_revision_binding"])
    binding = cast(dict[str, object], missing["retained_revision_binding"])
    binding.update(
        {
            "current_inventory_work_item_id": "work_current_2",
            "retained_work_item_id": "work_retained_2",
            "verified_draft_action_ids": ["act_content_dev_draft_missing"],
            "verified_draft_post_ids": ["1992"],
        }
    )
    missing["draft_and_action_state"] = copy.deepcopy(exact["draft_and_action_state"])
    state = cast(dict[str, object], missing["draft_and_action_state"])
    action = cast(
        dict[str, object],
        cast(list[object], state["verified_current_action_bindings"])[0],
    )
    draft = cast(dict[str, object], cast(list[object], state["verified_current_draft_bindings"])[0])
    action.update(
        {
            "action_id": "act_content_dev_draft_missing",
            "bound_work_item_id": "work_retained_2",
            "bound_final_canonical_url": "https://www.ekologus.pl/zablokowane/",
        }
    )
    draft.update({"action_id": "act_content_dev_draft_missing", "post_id": "1992"})

    _expect_rejection(
        resign(packet, policy=baseline.policy, sync_policy_decision=True),
        "missing_source_binding_mismatch",
    )


def row_input(inputs: SyntheticInputs) -> object:
    return cast(list[object], inputs.packet["rows"])[1]


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


def test_public_wave0_route_is_historical_and_cannot_record_current_acceptance() -> None:
    inputs = build_inputs()
    response = _asgi_request(
        _classification_app(),
        body={
            "policy_selector": "wave0-production-classification-v1",
            "packet_base64": base64.b64encode(inputs.packet_bytes).decode(),
            "judge_base64": base64.b64encode(inputs.judge_bytes).decode(),
            "recorded_by": "codex_s0_test",
            "reviewed_by": "independent_test_judge",
            "recorded_at": AUDIT_TIME.isoformat(),
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "production_classification_historical_reference"
    }


def test_public_wave0_read_is_labeled_historical_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = build_inputs()
    store = ContentWorkflowStore(tmp_path / "historical-read.sqlite3")
    store.record_production_classification(_parse(inputs))
    monkeypatch.setattr(classification_api, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        classification_api,
        "HISTORICAL_PRODUCTION_POLICY_IDS",
        frozenset({inputs.policy.policy_id}),
    )

    async def read_latest() -> httpx.Response:
        transport = httpx.ASGITransport(app=_classification_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/api/content/production-classifications/latest")

    response = asyncio.run(read_latest())

    assert response.status_code == 200
    assert response.json()["status"] == "historical_reference"


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


def test_persisted_head_payload_without_optional_history_remains_readable_without_tampering(
    tmp_path: Path,
) -> None:
    current = _parse(build_inputs())
    legacy_json = HEAD_FORMAT_CLASSIFICATION_PAYLOAD
    legacy_payload = json.loads(legacy_json)
    assert all(
        "blocked_historical_protection" not in cast(dict[str, object], row)
        for row in cast(list[object], legacy_payload["rows"])
    )

    store = ContentWorkflowStore(tmp_path / "legacy-head-classification.sqlite3")
    assert store.record_production_classification(current).status == "created"
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE content_production_classifications SET run_digest = ?, payload_json = ?",
            (legacy_payload["run_digest"], legacy_json),
        )

    loaded = store.load_latest_production_classification_reference()

    assert loaded is not None
    assert all(row.blocked_historical_protection is None for row in loaded.rows)
    tampered_payload = copy.deepcopy(legacy_payload)
    cast(dict[str, object], cast(list[object], tampered_payload["rows"])[0])["rationale_pl"] = (
        "Tampered"
    )
    with pytest.raises(ValidationError):
        ContentProductionClassificationRun.model_validate_json(
            json.dumps(tampered_payload, ensure_ascii=False, sort_keys=True),
            strict=True,
        )


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
